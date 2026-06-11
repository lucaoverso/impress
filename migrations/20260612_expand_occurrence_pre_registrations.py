#!/usr/bin/env python3
import sqlite3


def _column_exists(cursor: sqlite3.Cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    return column in {str(row[1]) for row in cursor.fetchall()}


def upgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()
    if not _column_exists(cursor, "occurrence_pre_registrations", "discipline"):
        cursor.execute(
            "ALTER TABLE occurrence_pre_registrations ADD COLUMN discipline TEXT NOT NULL DEFAULT ''"
        )
    if not _column_exists(cursor, "occurrence_pre_registrations", "lesson"):
        cursor.execute(
            "ALTER TABLE occurrence_pre_registrations ADD COLUMN lesson TEXT NOT NULL DEFAULT ''"
        )
    if not _column_exists(cursor, "occurrence_pre_registrations", "occurred_at"):
        cursor.execute(
            "ALTER TABLE occurrence_pre_registrations ADD COLUMN occurred_at TEXT NOT NULL DEFAULT ''"
        )
        cursor.execute(
            """
            UPDATE occurrence_pre_registrations
            SET occurred_at = created_at
            WHERE TRIM(COALESCE(occurred_at, '')) = ''
            """
        )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS occurrence_pre_registration_students (
            pre_registration_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            position INTEGER NOT NULL DEFAULT 1,
            PRIMARY KEY (pre_registration_id, student_id),
            FOREIGN KEY(pre_registration_id)
                REFERENCES occurrence_pre_registrations(id) ON DELETE CASCADE,
            FOREIGN KEY(student_id) REFERENCES estudantes(id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS occurrence_pre_registration_reasons (
            pre_registration_id INTEGER NOT NULL,
            reason_id INTEGER NOT NULL,
            position INTEGER NOT NULL DEFAULT 1,
            PRIMARY KEY (pre_registration_id, reason_id),
            FOREIGN KEY(pre_registration_id)
                REFERENCES occurrence_pre_registrations(id) ON DELETE CASCADE,
            FOREIGN KEY(reason_id) REFERENCES occurrence_reasons(id)
        )
        """
    )
    cursor.execute(
        """
        INSERT OR IGNORE INTO occurrence_pre_registration_students (
            pre_registration_id, student_id, position
        )
        SELECT id, student_id, 1
        FROM occurrence_pre_registrations
        """
    )
    cursor.execute(
        """
        INSERT OR IGNORE INTO occurrence_pre_registration_reasons (
            pre_registration_id, reason_id, position
        )
        SELECT id, reason_id, 1
        FROM occurrence_pre_registrations
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_pre_registration_students_student
        ON occurrence_pre_registration_students(student_id, pre_registration_id)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_pre_registration_reasons_reason
        ON occurrence_pre_registration_reasons(reason_id, pre_registration_id)
        """
    )
    conn.commit()


def downgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS occurrence_pre_registration_reasons")
    cursor.execute("DROP TABLE IF EXISTS occurrence_pre_registration_students")
    conn.commit()
