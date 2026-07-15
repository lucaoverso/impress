#!/usr/bin/env python3
import sqlite3


def upgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(estudante_laudos)")
    colunas = {str(row[1]) for row in cursor.fetchall()}
    novas_colunas = {
        "condicao_necessidade": "TEXT NOT NULL DEFAULT ''",
        "classificacao": "TEXT",
        "sistema_classificacao": "TEXT",
        "codigo_laudo": "TEXT",
        "descricao_laudo": "TEXT",
        "possui_laudo": "INTEGER NOT NULL DEFAULT 0 CHECK (possui_laudo IN (0, 1))",
        "data_laudo": "TEXT",
        "observacoes_restritas": "TEXT",
    }
    for nome, definicao in novas_colunas.items():
        if nome not in colunas:
            cursor.execute(f"ALTER TABLE estudante_laudos ADD COLUMN {nome} {definicao}")

    cursor.execute(
        """
        UPDATE estudante_laudos
        SET condicao_necessidade = COALESCE(NULLIF(condicao_necessidade, ''), titulo),
            codigo_laudo = COALESCE(codigo_laudo, cid),
            descricao_laudo = COALESCE(descricao_laudo, titulo),
            observacoes_restritas = COALESCE(observacoes_restritas, observacoes)
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS estudante_apoios_catalogo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL CHECK (tipo IN ('necessidade_pedagogica', 'recurso_acessibilidade')),
            nome TEXT NOT NULL,
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            criado_em TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(tipo, nome COLLATE NOCASE)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS estudante_laudo_apoios (
            laudo_id INTEGER NOT NULL,
            apoio_id INTEGER NOT NULL,
            PRIMARY KEY (laudo_id, apoio_id),
            FOREIGN KEY(laudo_id) REFERENCES estudante_laudos(id) ON DELETE CASCADE,
            FOREIGN KEY(apoio_id) REFERENCES estudante_apoios_catalogo(id)
        )
        """
    )
    conn.commit()


def downgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS estudante_laudo_apoios")
    cursor.execute("DROP TABLE IF EXISTS estudante_apoios_catalogo")
    conn.commit()
