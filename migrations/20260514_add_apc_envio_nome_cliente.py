#!/usr/bin/env python3
import sqlite3


def _colunas_tabela(cursor: sqlite3.Cursor, tabela: str) -> set[str]:
    cursor.execute(f"PRAGMA table_info({tabela})")
    return {str(row[1]) for row in cursor.fetchall()}


def upgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()
    colunas = _colunas_tabela(cursor, "apc_envios")

    if "arquivo_nome_cliente" not in colunas:
        cursor.execute(
            """
            ALTER TABLE apc_envios
            ADD COLUMN arquivo_nome_cliente TEXT NOT NULL DEFAULT ''
            """
        )

    cursor.execute(
        """
        UPDATE apc_envios
        SET arquivo_nome_cliente = arquivo_nome_original
        WHERE TRIM(COALESCE(arquivo_nome_cliente, '')) = ''
        """
    )
