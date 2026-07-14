#!/usr/bin/env python3
import sqlite3


def upgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(estudantes)")
    colunas = {str(row[1]) for row in cursor.fetchall()}
    if "sexo" not in colunas:
        cursor.execute(
            "ALTER TABLE estudantes ADD COLUMN sexo TEXT "
            "CHECK (sexo IS NULL OR sexo IN ('M', 'F'))"
        )
    conn.commit()


def downgrade(conn: sqlite3.Connection):
    conn.commit()
