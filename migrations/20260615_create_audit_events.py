#!/usr/bin/env python3
import sqlite3


def upgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            action TEXT NOT NULL,
            outcome TEXT NOT NULL,
            actor_user_id INTEGER,
            actor_name TEXT NOT NULL DEFAULT '',
            actor_email TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL,
            entity_type TEXT NOT NULL DEFAULT '',
            entity_id TEXT NOT NULL DEFAULT '',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(actor_user_id) REFERENCES usuarios(id) ON DELETE SET NULL
        )
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_audit_events_created_at
        ON audit_events(created_at DESC)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_audit_events_filters
        ON audit_events(category, outcome, actor_user_id, created_at DESC)
        """
    )
    conn.commit()


def downgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS audit_events")
    conn.commit()
