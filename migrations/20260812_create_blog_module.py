import sqlite3


def upgrade(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS blog_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author_user_id INTEGER NOT NULL,
            title TEXT NOT NULL CHECK(length(trim(title)) BETWEEN 1 AND 180),
            slug TEXT NOT NULL UNIQUE CHECK(length(slug) BETWEEN 1 AND 180),
            summary TEXT NOT NULL DEFAULT '' CHECK(length(summary) <= 500),
            body_html TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'DRAFT'
                CHECK(status IN ('DRAFT', 'PUBLISHED', 'ARCHIVED')),
            published_at TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(author_user_id) REFERENCES usuarios(id) ON DELETE RESTRICT
        );

        CREATE INDEX IF NOT EXISTS idx_blog_posts_status_published
        ON blog_posts(status, published_at DESC, id DESC);

        CREATE INDEX IF NOT EXISTS idx_blog_posts_author_updated
        ON blog_posts(author_user_id, updated_at DESC, id DESC);

        CREATE TABLE IF NOT EXISTS blog_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            token TEXT NOT NULL UNIQUE CHECK(length(token) BETWEEN 1 AND 120),
            stored_name TEXT NOT NULL CHECK(length(stored_name) BETWEEN 1 AND 255),
            thumbnail_name TEXT NOT NULL DEFAULT '' CHECK(length(thumbnail_name) <= 255),
            alt_text TEXT NOT NULL DEFAULT '' CHECK(length(alt_text) <= 180),
            caption TEXT NOT NULL DEFAULT '' CHECK(length(caption) <= 500),
            width INTEGER NOT NULL DEFAULT 0 CHECK(width >= 0),
            height INTEGER NOT NULL DEFAULT 0 CHECK(height >= 0),
            is_cover INTEGER NOT NULL DEFAULT 0 CHECK(is_cover IN (0, 1)),
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(post_id) REFERENCES blog_posts(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_blog_images_post
        ON blog_images(post_id, id);

        CREATE UNIQUE INDEX IF NOT EXISTS uq_blog_images_post_cover
        ON blog_images(post_id)
        WHERE is_cover = 1;
        """
    )
    conn.commit()


def downgrade(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DROP INDEX IF EXISTS uq_blog_images_post_cover;
        DROP INDEX IF EXISTS idx_blog_images_post;
        DROP TABLE IF EXISTS blog_images;
        DROP INDEX IF EXISTS idx_blog_posts_author_updated;
        DROP INDEX IF EXISTS idx_blog_posts_status_published;
        DROP TABLE IF EXISTS blog_posts;
        """
    )
    conn.commit()
