import importlib.util
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from modules.blog.models import BlogPostStatus
from modules.blog.schemas import BlogImageCreateIn, BlogPostCreateIn, BlogPostUpdateIn
from modules.blog.service import BlogValidationError
from modules.blog import service


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1] / "migrations" / "20260812_create_blog_module.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location("test_blog_service_migration", MIGRATION_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Nao foi possivel carregar a migration do Blog.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BlogServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "blog-service.db"
        self.image_dir = Path(self.temp_dir.name) / "images"
        self.image_dir.mkdir()
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
    def _payload(title: str) -> BlogPostCreateIn:
        return BlogPostCreateIn(
            title=title,
            summary="Noticia sobre a escola",
            body_html="<p>Conteudo do artigo.</p>",
        )

    def _add_stored_image(self, post_id: int, *, token: str, alt_text: str, is_cover: bool) -> dict:
        stored_name = f"{token}.webp"
        thumbnail_name = f"{token}-thumb.webp"
        (self.image_dir / stored_name).write_bytes(b"imagem")
        (self.image_dir / thumbnail_name).write_bytes(b"miniatura")
        return service.add_image(
            post_id,
            BlogImageCreateIn(
                token=token,
                stored_name=stored_name,
                thumbnail_name=thumbnail_name,
                alt_text=alt_text,
                is_cover=is_cover,
            ),
        )

    def test_generates_unique_accent_free_slugs(self):
        first = service.create_post(author_user_id=7, payload=self._payload("Ação da Escola"))
        second = service.create_post(author_user_id=7, payload=self._payload("Ação da Escola"))

        self.assertEqual(first["slug"], "acao-da-escola")
        self.assertEqual(second["slug"], "acao-da-escola-2")

    def test_slug_changes_while_draft_and_is_stable_after_first_publication(self):
        post = service.create_post(author_user_id=7, payload=self._payload("Titulo inicial"))
        post = service.update_post(
            post["id"], BlogPostUpdateIn(**self._payload("Novo titulo").model_dump())
        )
        self.assertEqual(post["slug"], "novo-titulo")

        self._add_stored_image(
            post["id"],
            token="a" * 32,
            alt_text="Fachada da escola",
            is_cover=True,
        )
        published = service.publish_post(post["id"], image_dir=self.image_dir)
        updated = service.update_post(
            post["id"], BlogPostUpdateIn(**self._payload("Titulo publicado alterado").model_dump())
        )

        self.assertEqual(published["status"], BlogPostStatus.PUBLISHED.value)
        self.assertEqual(updated["slug"], "novo-titulo")
        service.unpublish_post(post["id"])
        updated_again = service.update_post(
            post["id"], BlogPostUpdateIn(**self._payload("Outra mudanca").model_dump())
        )
        self.assertEqual(updated_again["slug"], "novo-titulo")

    def test_publication_requires_cover_and_alt_text(self):
        post = service.create_post(author_user_id=7, payload=self._payload("Artigo incompleto"))
        with self.assertRaisesRegex(BlogValidationError, "imagem de capa"):
            service.publish_post(post["id"])

        self._add_stored_image(post["id"], token="b" * 32, alt_text="", is_cover=True)
        with self.assertRaisesRegex(BlogValidationError, "texto alternativo"):
            service.publish_post(post["id"])

    def test_public_queries_never_return_drafts_or_archived_posts(self):
        post = service.create_post(author_user_id=7, payload=self._payload("Noticia publica"))
        self._add_stored_image(
            post["id"],
            token="c" * 32,
            alt_text="Evento escolar",
            is_cover=True,
        )
        service.publish_post(post["id"], image_dir=self.image_dir)
        self.assertEqual([item["id"] for item in service.list_public_posts()], [post["id"]])

        service.archive_post(post["id"])
        self.assertEqual(service.list_public_posts(), [])


if __name__ == "__main__":
    unittest.main()
