import importlib.util
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from modules.blog import repository


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1] / "migrations" / "20260812_create_blog_module.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location("test_blog_repository_migration", MIGRATION_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Nao foi possivel carregar a migration do Blog.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BlogRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "blog.db"
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

    def _create_post(self, slug: str = "feira-da-escola") -> dict:
        return repository.create_post(
            author_user_id=7,
            title="Feira da escola",
            slug=slug,
            summary="Um resumo",
            body_html="<p>Conteudo</p>",
        )

    def test_post_crud_and_public_queries_are_status_scoped(self):
        draft = self._create_post()
        self.assertEqual(draft["status"], "DRAFT")
        self.assertEqual(repository.list_public_posts(), [])
        self.assertIsNone(repository.get_public_post_by_slug(draft["slug"]))

        updated = repository.update_post(
            draft["id"],
            title="Feira cultural",
            slug="feira-cultural",
            summary="Resumo atualizado",
            body_html="<p>Novo conteudo</p>",
        )
        self.assertEqual(updated["title"], "Feira cultural")
        published = repository.set_post_status(draft["id"], "PUBLISHED")

        self.assertIsNotNone(published["published_at"])
        self.assertEqual([item["id"] for item in repository.list_public_posts()], [draft["id"]])
        self.assertEqual(repository.get_public_post_by_slug("feira-cultural")["id"], draft["id"])

        repository.set_post_status(draft["id"], "DRAFT")
        self.assertEqual(repository.list_public_posts(), [])

    def test_image_metadata_maintains_a_single_cover(self):
        post = self._create_post()
        first = repository.create_image(
            post["id"],
            {
                "token": "first",
                "stored_name": "first.jpg",
                "thumbnail_name": "first-thumb.jpg",
                "alt_text": "Primeira imagem",
                "caption": "Legenda inicial",
                "width": 1200,
                "height": 800,
                "is_cover": True,
            },
        )
        second = repository.create_image(
            post["id"],
            {
                "token": "second",
                "stored_name": "second.jpg",
                "thumbnail_name": "second-thumb.jpg",
                "alt_text": "Segunda imagem",
                "caption": "",
                "width": 1200,
                "height": 800,
                "is_cover": False,
            },
        )

        repository.set_cover_image(post["id"], second["id"])
        images = repository.list_images(post["id"])
        covers = [image for image in images if image["is_cover"]]

        self.assertEqual([image["id"] for image in covers], [second["id"]])
        self.assertFalse(repository.get_image(first["id"])["is_cover"])


if __name__ == "__main__":
    unittest.main()
