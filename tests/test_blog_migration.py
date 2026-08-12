import importlib.util
import sqlite3
import unittest
from pathlib import Path


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1] / "migrations" / "20260812_create_blog_module.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location("test_blog_migration_module", MIGRATION_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Nao foi possivel carregar a migration do Blog.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BlogMigrationTests(unittest.TestCase):
    def setUp(self):
        self.migration = _load_migration()
        self.conn = sqlite3.connect(":memory:")
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("CREATE TABLE usuarios (id INTEGER PRIMARY KEY)")
        self.conn.execute("INSERT INTO usuarios (id) VALUES (7)")

    def tearDown(self):
        self.conn.close()

    def test_upgrade_is_idempotent_and_creates_expected_indexes(self):
        self.migration.upgrade(self.conn)
        self.migration.upgrade(self.conn)

        tables = {
            row[0]
            for row in self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        indexes = {
            row[0]
            for row in self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index'"
            ).fetchall()
        }

        self.assertIn("blog_posts", tables)
        self.assertIn("blog_images", tables)
        self.assertIn("idx_blog_posts_status_published", indexes)
        self.assertIn("uq_blog_images_post_cover", indexes)

    def test_constraints_allow_only_one_cover_and_cascade_images(self):
        self.migration.upgrade(self.conn)
        post_id = self.conn.execute(
            """
            INSERT INTO blog_posts (author_user_id, title, slug)
            VALUES (7, 'Feira da escola', 'feira-da-escola')
            """
        ).lastrowid
        self.conn.execute(
            """
            INSERT INTO blog_images (post_id, token, stored_name, is_cover)
            VALUES (?, 'image-1', 'image-1.jpg', 1)
            """,
            (post_id,),
        )

        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                """
                INSERT INTO blog_images (post_id, token, stored_name, is_cover)
                VALUES (?, 'image-2', 'image-2.jpg', 1)
                """,
                (post_id,),
            )

        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("UPDATE blog_posts SET status = 'INVALID' WHERE id = ?", (post_id,))

        self.conn.execute("DELETE FROM blog_posts WHERE id = ?", (post_id,))
        image_count = self.conn.execute("SELECT COUNT(*) FROM blog_images").fetchone()[0]
        self.assertEqual(image_count, 0)

    def test_downgrade_removes_blog_tables(self):
        self.migration.upgrade(self.conn)
        self.migration.downgrade(self.conn)

        tables = {
            row[0]
            for row in self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        self.assertNotIn("blog_posts", tables)
        self.assertNotIn("blog_images", tables)


if __name__ == "__main__":
    unittest.main()
