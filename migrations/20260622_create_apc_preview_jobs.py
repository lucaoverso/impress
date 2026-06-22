#!/usr/bin/env python3
import sqlite3


def _table_exists(cursor: sqlite3.Cursor, table: str) -> bool:
    cursor.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        LIMIT 1
        """,
        (table,),
    )
    return cursor.fetchone() is not None


def upgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()
    if not _table_exists(cursor, "apc_envios"):
        conn.commit()
        return

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS apc_preview_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            envio_id INTEGER NOT NULL UNIQUE,
            arquivo_path TEXT NOT NULL DEFAULT '',
            arquivo_nome_original TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'PENDENTE',
            preview_pdf_path TEXT NOT NULL DEFAULT '',
            erro_mensagem TEXT NOT NULL DEFAULT '',
            tentativas INTEGER NOT NULL DEFAULT 0,
            criado_em TEXT NOT NULL DEFAULT (datetime('now')),
            atualizado_em TEXT NOT NULL DEFAULT (datetime('now')),
            processado_em TEXT,
            FOREIGN KEY(envio_id) REFERENCES apc_envios(id) ON DELETE CASCADE
        )
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_apc_preview_jobs_status
        ON apc_preview_jobs(status, atualizado_em, id)
        """
    )
    conn.commit()


def downgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("DROP INDEX IF EXISTS idx_apc_preview_jobs_status")
    cursor.execute("DROP TABLE IF EXISTS apc_preview_jobs")
    conn.commit()
