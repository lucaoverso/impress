#!/usr/bin/env python3
import sqlite3


def upgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS occurrence_reasons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL COLLATE NOCASE UNIQUE,
            active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS occurrence_pre_registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            reason_id INTEGER NOT NULL,
            professor_id INTEGER NOT NULL,
            responsible_contact TEXT NOT NULL
                CHECK (responsible_contact IN ('none', 'communicate', 'summon')),
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'completed', 'cancelled')),
            occurrence_id INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            completed_at TEXT,
            FOREIGN KEY(student_id) REFERENCES estudantes(id),
            FOREIGN KEY(reason_id) REFERENCES occurrence_reasons(id),
            FOREIGN KEY(professor_id) REFERENCES usuarios(id),
            FOREIGN KEY(occurrence_id) REFERENCES ocorrencias(id)
        )
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_occurrence_pre_registrations_status
        ON occurrence_pre_registrations(status, created_at DESC)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_occurrence_pre_registrations_professor
        ON occurrence_pre_registrations(professor_id, created_at DESC)
        """
    )
    conn.commit()


def downgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS occurrence_pre_registrations")
    cursor.execute("DROP TABLE IF EXISTS occurrence_reasons")
    conn.commit()
