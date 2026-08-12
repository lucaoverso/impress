import importlib.util
import io
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from modules.blog import image_service, service
from modules.blog.schemas import BlogPostCreateIn
from modules.blog.service import BlogConflictError, BlogNotFoundError, BlogValidationError


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1] / "migrations" / "20260812_create_blog_module.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location("test_blog_image_migration", MIGRATION_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Nao foi possivel carregar a migration do Blog.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _image_bytes(
    *,
    size: tuple[int, int] = (1200, 800),
    image_format: str = "JPEG",
    with_exif: bool = False,
) -> bytes:
    mode = "RGBA" if image_format == "PNG" else "RGB"
    color = (20, 120, 180, 180) if mode == "RGBA" else (20, 120, 180)
    image = Image.new(mode, size, color)
    output = io.BytesIO()
    kwargs = {}
    if with_exif:
        exif = Image.Exif()
        exif[274] = 6
        exif[270] = "metadado privado"
        kwargs["exif"] = exif
    image.save(output, format=image_format, **kwargs)
    return output.getvalue()


class BlogImageProcessingTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.image_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_stores_oriented_webp_thumbnail_without_exif(self):
        stored = image_service.store_blog_image(
            _image_bytes(size=(3000, 1000), with_exif=True),
            content_type="image/jpeg",
            original_filename="../foto da escola.jpg",
            image_dir=self.image_dir,
        )

        main_path = self.image_dir / stored["stored_name"]
        thumb_path = self.image_dir / stored["thumbnail_name"]
        self.assertTrue(main_path.is_file())
        self.assertTrue(thumb_path.is_file())
        self.assertEqual((stored["width"], stored["height"]), (800, 2400))
        self.assertEqual(stored["original_filename"], "foto da escola.jpg")

        with Image.open(main_path) as main:
            self.assertEqual(main.format, "WEBP")
            self.assertEqual(main.size, (800, 2400))
            self.assertEqual(len(main.getexif()), 0)
        with Image.open(thumb_path) as thumbnail:
            self.assertLessEqual(max(thumbnail.size), image_service.THUMBNAIL_DIMENSION)
            self.assertEqual(len(thumbnail.getexif()), 0)

    def test_preserves_transparency_in_webp_output(self):
        stored = image_service.store_blog_image(
            _image_bytes(size=(300, 200), image_format="PNG"),
            content_type="image/png",
            image_dir=self.image_dir,
        )

        with Image.open(self.image_dir / stored["stored_name"]) as output:
            self.assertEqual(output.mode, "RGBA")

    def test_rejects_invalid_type_content_and_excessive_pixels(self):
        with self.assertRaises(image_service.BlogImageValidationError):
            image_service.store_blog_image(b"nao e imagem", image_dir=self.image_dir)
        with self.assertRaises(image_service.BlogImageValidationError):
            image_service.store_blog_image(
                _image_bytes(), content_type="application/pdf", image_dir=self.image_dir
            )
        with self.assertRaises(image_service.BlogImageValidationError):
            image_service.store_blog_image(
                b"x" * (image_service.MAX_IMAGE_BYTES + 1), image_dir=self.image_dir
            )
        with patch("modules.blog.image_service.MAX_SOURCE_PIXELS", 100):
            with self.assertRaises(image_service.BlogImageValidationError):
                image_service.store_blog_image(
                    _image_bytes(size=(20, 20), image_format="PNG"),
                    image_dir=self.image_dir,
                )

    def test_resolution_and_deletion_reject_path_traversal(self):
        stored = image_service.store_blog_image(_image_bytes(), image_dir=self.image_dir)

        self.assertIsNone(
            image_service.resolve_blog_image(
                "../" + stored["stored_name"], image_dir=self.image_dir
            )
        )
        self.assertIsNotNone(
            image_service.resolve_blog_image(stored["stored_name"], image_dir=self.image_dir)
        )
        deleted = image_service.delete_blog_image_files(
            stored["stored_name"], stored["thumbnail_name"], image_dir=self.image_dir
        )
        self.assertEqual(len(deleted), 2)
        self.assertEqual(list(self.image_dir.iterdir()), [])


class BlogImageAccessTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.temp_dir.name)
        self.db_path = self.base_dir / "blog-images.db"
        self.image_dir = self.base_dir / "images"
        conn = self._connect()
        conn.execute("CREATE TABLE usuarios (id INTEGER PRIMARY KEY)")
        conn.execute("INSERT INTO usuarios (id) VALUES (7)")
        _load_migration().upgrade(conn)
        conn.close()
        self.connection_patch = patch(
            "modules.blog.repository.get_connection", side_effect=self._connect
        )
        self.connection_patch.start()

    def tearDown(self):
        self.connection_patch.stop()
        self.temp_dir.cleanup()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @staticmethod
    def _post_payload() -> BlogPostCreateIn:
        return BlogPostCreateIn(
            title="Feira cultural",
            summary="Um evento da comunidade escolar",
            body_html="<p>Conteudo do artigo.</p>",
        )

    def test_draft_image_is_admin_only_until_post_is_published(self):
        post = service.create_post(author_user_id=7, payload=self._post_payload())
        image = service.upload_image(
            post["id"],
            content=_image_bytes(),
            content_type="image/jpeg",
            original_filename="feira.jpg",
            alt_text="Estudantes na feira cultural",
            caption="Apresentacao dos trabalhos",
            is_cover=True,
            image_dir=self.image_dir,
        )

        admin_file = service.resolve_image(image["token"], public=False, image_dir=self.image_dir)
        self.assertTrue(admin_file["path"].is_file())
        with self.assertRaises(BlogNotFoundError):
            service.resolve_image(image["token"], public=True, image_dir=self.image_dir)

        service.publish_post(post["id"], image_dir=self.image_dir)
        public_file = service.resolve_image(image["token"], public=True, image_dir=self.image_dir)
        thumbnail = service.resolve_image(
            image["token"], public=True, thumbnail=True, image_dir=self.image_dir
        )
        self.assertEqual(public_file["filename"], image["stored_name"])
        self.assertEqual(thumbnail["filename"], image["thumbnail_name"])

        service.archive_post(post["id"])
        with self.assertRaises(BlogNotFoundError):
            service.resolve_image(image["token"], public=True, image_dir=self.image_dir)

    def test_database_failure_removes_newly_written_files(self):
        post = service.create_post(author_user_id=7, payload=self._post_payload())
        with patch("modules.blog.service.add_image", side_effect=BlogConflictError("falha")):
            with self.assertRaises(BlogConflictError):
                service.upload_image(
                    post["id"],
                    content=_image_bytes(),
                    content_type="image/jpeg",
                    image_dir=self.image_dir,
                )

        self.assertEqual(list(self.image_dir.iterdir()), [])

    def test_publication_rejects_missing_physical_file(self):
        post = service.create_post(author_user_id=7, payload=self._post_payload())
        image = service.upload_image(
            post["id"],
            content=_image_bytes(),
            content_type="image/jpeg",
            alt_text="Imagem da escola",
            is_cover=True,
            image_dir=self.image_dir,
        )
        (self.image_dir / image["thumbnail_name"]).unlink()

        with self.assertRaisesRegex(BlogValidationError, "nao estao disponiveis"):
            service.publish_post(post["id"], image_dir=self.image_dir)

    def test_removing_metadata_also_removes_both_files(self):
        post = service.create_post(author_user_id=7, payload=self._post_payload())
        image = service.upload_image(
            post["id"],
            content=_image_bytes(),
            content_type="image/jpeg",
            alt_text="Imagem da escola",
            image_dir=self.image_dir,
        )

        service.remove_image(post["id"], image["id"], image_dir=self.image_dir)

        self.assertEqual(list(self.image_dir.iterdir()), [])
        with self.assertRaises(BlogNotFoundError):
            service.resolve_image(image["token"], public=False, image_dir=self.image_dir)


if __name__ == "__main__":
    unittest.main()
