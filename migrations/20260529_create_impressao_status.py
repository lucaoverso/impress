#!/usr/bin/env python3
import sqlite3


def upgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS impressao_status (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            sem_papel INTEGER NOT NULL DEFAULT 0,
            mensagem TEXT NOT NULL DEFAULT '',
            atualizado_em TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    cursor.execute(
        """
        INSERT OR IGNORE INTO impressao_status (
            id, sem_papel, mensagem, atualizado_em
        )
        VALUES (1, 0, '', datetime('now'))
        """
    )
    conn.commit()


def downgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS impressao_status")
    conn.commit()
