#!/usr/bin/env python3
import sqlite3


def _columns(cursor: sqlite3.Cursor) -> set[str]:
    cursor.execute("PRAGMA table_info(apc_envios)")
    return {str(row[1]) for row in cursor.fetchall()}


def upgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()
    columns = _columns(cursor)
    additions = {
        "review_status": "TEXT NOT NULL DEFAULT 'PENDENTE'",
        "review_message": "TEXT NOT NULL DEFAULT ''",
        "reviewed_by_user_id": "INTEGER",
        "reviewed_at": "TEXT",
    }
    for column, definition in additions.items():
        if column not in columns:
            cursor.execute(
                f"ALTER TABLE apc_envios ADD COLUMN {column} {definition}"
            )
    cursor.execute(
        """
        UPDATE apc_envios
        SET review_status = 'PENDENTE'
        WHERE TRIM(COALESCE(review_status, '')) = ''
        """
    )
    conn.commit()


def downgrade(conn: sqlite3.Connection):
    # SQLite legado nao permite remover colunas com seguranca sem recriar a tabela.
    conn.commit()
