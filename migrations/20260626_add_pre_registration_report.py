#!/usr/bin/env python3
import sqlite3


def _column_exists(cursor: sqlite3.Cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    return column in {str(row[1]) for row in cursor.fetchall()}


def upgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()
    if not _column_exists(cursor, "occurrence_pre_registrations", "complementary_report"):
        cursor.execute(
            "ALTER TABLE occurrence_pre_registrations ADD COLUMN complementary_report TEXT NOT NULL DEFAULT ''"
        )
    conn.commit()


def downgrade(conn: sqlite3.Connection):
    conn.commit()
