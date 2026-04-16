#!/usr/bin/env python3
import sqlite3


def _colunas_tabela(cursor: sqlite3.Cursor, tabela: str) -> set[str]:
    cursor.execute(f"PRAGMA table_info({tabela})")
    return {str(row[1]) for row in cursor.fetchall()}


def upgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()
    if "acesso_coordenacao" not in _colunas_tabela(cursor, "usuarios"):
        cursor.execute(
            """
            ALTER TABLE usuarios
            ADD COLUMN acesso_coordenacao INTEGER NOT NULL DEFAULT 0
            """
        )
