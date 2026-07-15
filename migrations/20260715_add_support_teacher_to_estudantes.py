#!/usr/bin/env python3
import sqlite3


def upgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(estudantes)")
    colunas = {str(row[1]) for row in cursor.fetchall()}
    if "possui_professor_apoio" not in colunas:
        cursor.execute(
            "ALTER TABLE estudantes ADD COLUMN possui_professor_apoio "
            "INTEGER NOT NULL DEFAULT 0 CHECK (possui_professor_apoio IN (0, 1))"
        )
    conn.commit()


def downgrade(conn: sqlite3.Connection):
    conn.commit()
