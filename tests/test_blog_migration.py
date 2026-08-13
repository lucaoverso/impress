import sqlite3
import unittest

from tests.blog_test_support import apply_blog_migrations, load_blog_migration


class BlogMigrationTests(unittest.TestCase):
    def setUp(self):
        self.migration = load_blog_migration("20260812_create_blog_module.py")
        self.tags_migration = load_blog_migration("20260813_add_blog_tags.py")
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

    def test_tag_migration_preserves_posts_and_cascades_relations(self):
        apply_blog_migrations(self.conn)
        post_id = self.conn.execute(
            "INSERT INTO blog_posts (author_user_id, title, slug) VALUES (7, 'Projeto', 'projeto')"
        ).lastrowid
        tag_id = self.conn.execute(
            "INSERT INTO blog_tags (name, slug) VALUES ('Projetos', 'projetos')"
        ).lastrowid
        self.conn.execute(
            "INSERT INTO blog_post_tags (post_id, tag_id, position) VALUES (?, ?, 0)",
            (post_id, tag_id),
        )

        self.tags_migration.upgrade(self.conn)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM blog_posts").fetchone()[0], 1)
        self.conn.execute("DELETE FROM blog_posts WHERE id = ?", (post_id,))
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM blog_post_tags").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
