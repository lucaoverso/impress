#!/usr/bin/env python3
import sqlite3


def upgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS estudante_laudos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            estudante_id INTEGER NOT NULL,
            cid TEXT,
            titulo TEXT NOT NULL,
            observacoes TEXT,
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            criado_em TEXT NOT NULL DEFAULT (datetime('now')),
            atualizado_em TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(estudante_id) REFERENCES estudantes(id) ON DELETE CASCADE
        )
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_estudante_laudos_estudante_id
        ON estudante_laudos(estudante_id)
        """
    )

    cursor.execute("PRAGMA table_info(estudantes)")
    colunas = {str(row[1]) for row in cursor.fetchall()}
    if "necessidade_especial" in colunas:
        cursor.execute(
            """
            INSERT INTO estudante_laudos (
                estudante_id, cid, titulo, observacoes, ativo, criado_em, atualizado_em
            )
            SELECT e.id, NULL, TRIM(e.necessidade_especial),
                   'Migrado do cadastro anterior de necessidades especiais.', 1,
                   datetime('now'), datetime('now')
            FROM estudantes e
            WHERE TRIM(COALESCE(e.necessidade_especial, '')) <> ''
              AND NOT EXISTS (
                  SELECT 1 FROM estudante_laudos l
                  WHERE l.estudante_id = e.id
                    AND l.titulo = TRIM(e.necessidade_especial)
              )
            """
        )
    conn.commit()


def downgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS estudante_laudos")
    conn.commit()
