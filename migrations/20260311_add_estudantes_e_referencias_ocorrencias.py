#!/usr/bin/env python3
import argparse
import os
import sqlite3
from pathlib import Path


def _default_db_path() -> str:
    env_path = os.getenv("DB_PATH", "").strip()
    if env_path:
        return env_path
    base_dir = Path(__file__).resolve().parents[1]
    return str(base_dir.parent / "sistema-impress-data" / "impressao.db")


def _listar_colunas(cursor, tabela: str) -> set[str]:
    cursor.execute(f"PRAGMA table_info({tabela})")
    return {str(row[1]) for row in cursor.fetchall()}


def upgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS estudantes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            turma_id INTEGER NOT NULL,
            ativo INTEGER NOT NULL DEFAULT 1,
            criado_em TEXT NOT NULL DEFAULT (datetime('now')),
            atualizado_em TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(turma_id) REFERENCES turmas(id)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_estudantes_nome
        ON estudantes(nome)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_estudantes_turma_id
        ON estudantes(turma_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_estudantes_ativo
        ON estudantes(ativo)
    """)

    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = 'ocorrencias'
    """)
    if cursor.fetchone():
        colunas = _listar_colunas(cursor, "ocorrencias")
        if "estudante_id" not in colunas:
            cursor.execute("ALTER TABLE ocorrencias ADD COLUMN estudante_id INTEGER")
        if "professor_requerente_id" not in colunas:
            cursor.execute("ALTER TABLE ocorrencias ADD COLUMN professor_requerente_id INTEGER")

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ocorrencias_estudante_id
            ON ocorrencias(estudante_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ocorrencias_professor_requerente_id
            ON ocorrencias(professor_requerente_id)
        """)

    conn.commit()


def downgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("DROP INDEX IF EXISTS idx_ocorrencias_professor_requerente_id")
    cursor.execute("DROP INDEX IF EXISTS idx_ocorrencias_estudante_id")
    cursor.execute("DROP INDEX IF EXISTS idx_estudantes_ativo")
    cursor.execute("DROP INDEX IF EXISTS idx_estudantes_turma_id")
    cursor.execute("DROP INDEX IF EXISTS idx_estudantes_nome")

    cursor.execute("PRAGMA foreign_keys = OFF")
    cursor.execute("DROP TABLE IF EXISTS estudantes")
    cursor.execute("PRAGMA foreign_keys = ON")
    conn.commit()


def main():
    parser = argparse.ArgumentParser(
        description="Migration: cria tabela estudantes e referências em ocorrencias"
    )
    parser.add_argument("action", choices=["upgrade", "downgrade"], help="Ação da migration.")
    parser.add_argument("--db", default=_default_db_path(), help="Caminho do banco SQLite.")
    args = parser.parse_args()

    db_path = Path(args.db).expanduser()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    try:
        if args.action == "upgrade":
            upgrade(conn)
        else:
            downgrade(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
