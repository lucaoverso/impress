#!/usr/bin/env python3
import sqlite3


def upgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(estudante_laudos)")
    colunas = {str(row[1]) for row in cursor.fetchall()}
    if "relato_professora_apoio" not in colunas:
        cursor.execute("ALTER TABLE estudante_laudos ADD COLUMN relato_professora_apoio TEXT")
    if "recomendacoes_pedagogicas" not in colunas:
        cursor.execute("ALTER TABLE estudante_laudos ADD COLUMN recomendacoes_pedagogicas TEXT")
    conn.commit()


def downgrade(conn: sqlite3.Connection):
    conn.commit()
