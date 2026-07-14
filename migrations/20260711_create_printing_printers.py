import sqlite3


def upgrade(conn: sqlite3.Connection):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS printing_printers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL COLLATE NOCASE UNIQUE,
            active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0, 1)),
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.commit()


def downgrade(conn: sqlite3.Connection):
    conn.execute("DROP TABLE IF EXISTS printing_printers")
    conn.commit()
