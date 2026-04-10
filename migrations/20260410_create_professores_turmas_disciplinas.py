#!/usr/bin/env python3
import argparse
import os
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]


def _default_db_path() -> str:
    env_path = os.getenv("DB_PATH", "").strip()
    if env_path:
        return env_path
    return str(BASE_DIR.parent / "sistema-impress-data" / "impressao.db")


def _colunas_tabela(cursor: sqlite3.Cursor, tabela: str) -> set[str]:
    cursor.execute(f"PRAGMA table_info({tabela})")
    return {row[1] for row in cursor.fetchall()}


def upgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS professores_turmas_disciplinas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            professor_usuario_id INTEGER NOT NULL,
            turma_id INTEGER NOT NULL,
            disciplina_id INTEGER NOT NULL,
            criado_em TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(professor_usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY(turma_id) REFERENCES turmas(id),
            FOREIGN KEY(disciplina_id) REFERENCES disciplinas(id),
            UNIQUE(professor_usuario_id, turma_id, disciplina_id)
        )
        """
    )

    colunas = _colunas_tabela(cursor, "professores_turmas_disciplinas")
    if "criado_em" not in colunas:
        cursor.execute(
            "ALTER TABLE professores_turmas_disciplinas ADD COLUMN criado_em TEXT NOT NULL DEFAULT ''"
        )
        cursor.execute(
            """
            UPDATE professores_turmas_disciplinas
            SET criado_em = datetime('now')
            WHERE TRIM(COALESCE(criado_em, '')) = ''
            """
        )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_professores_turmas_disciplinas_professor
        ON professores_turmas_disciplinas(professor_usuario_id, turma_id, disciplina_id)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_professores_turmas_disciplinas_turma
        ON professores_turmas_disciplinas(turma_id, disciplina_id)
        """
    )

    conn.commit()


def downgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("DROP INDEX IF EXISTS idx_professores_turmas_disciplinas_turma")
    cursor.execute("DROP INDEX IF EXISTS idx_professores_turmas_disciplinas_professor")
    cursor.execute("DROP TABLE IF EXISTS professores_turmas_disciplinas")
    conn.commit()


def main():
    parser = argparse.ArgumentParser(
        description="Migration: cria a tabela de atribuicoes exatas professor x turma x disciplina"
    )
    parser.add_argument("action", choices=["upgrade", "downgrade"], help="Acao da migration.")
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
