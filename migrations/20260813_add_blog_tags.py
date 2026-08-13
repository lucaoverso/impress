import sqlite3


def upgrade(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS blog_tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL CHECK(length(trim(name)) BETWEEN 1 AND 32),
            slug TEXT NOT NULL UNIQUE CHECK(length(slug) BETWEEN 1 AND 48),
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS blog_post_tags (
            post_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            position INTEGER NOT NULL DEFAULT 0 CHECK(position >= 0),
            PRIMARY KEY (post_id, tag_id),
            FOREIGN KEY(post_id) REFERENCES blog_posts(id) ON DELETE CASCADE,
            FOREIGN KEY(tag_id) REFERENCES blog_tags(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_blog_post_tags_tag
        ON blog_post_tags(tag_id, post_id);

        CREATE INDEX IF NOT EXISTS idx_blog_post_tags_post_position
        ON blog_post_tags(post_id, position);
        """
    )
    conn.commit()


def downgrade(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DROP INDEX IF EXISTS idx_blog_post_tags_post_position;
        DROP INDEX IF EXISTS idx_blog_post_tags_tag;
        DROP TABLE IF EXISTS blog_post_tags;
        DROP TABLE IF EXISTS blog_tags;
        """
    )
    conn.commit()
