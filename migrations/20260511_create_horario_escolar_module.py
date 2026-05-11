#!/usr/bin/env python3
import argparse
import os
import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


def _default_db_path() -> str:
    env_path = os.getenv("DB_PATH", "").strip()
    if env_path:
        return env_path
    return str(BASE_DIR.parent / "sistema-impress-data" / "impressao.db")


def _colunas_tabela(cursor: sqlite3.Cursor, tabela: str) -> set[str]:
    cursor.execute(f"PRAGMA table_info({tabela})")
    return {row[1] for row in cursor.fetchall()}


def _adicionar_coluna_se_necessario(
    cursor: sqlite3.Cursor, tabela: str, coluna: str, definicao: str
):
    if coluna in _colunas_tabela(cursor, tabela):
        return
    cursor.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {definicao}")


def upgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS horarios_escolares (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ano_letivo INTEGER NOT NULL,
            turma_id INTEGER NOT NULL,
            disciplina_id INTEGER NOT NULL,
            professor_usuario_id INTEGER NOT NULL,
            dia_semana TEXT NOT NULL,
            aula_numero INTEGER NOT NULL DEFAULT 1,
            criado_em TEXT NOT NULL DEFAULT (datetime('now')),
            atualizado_em TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(turma_id) REFERENCES turmas(id),
            FOREIGN KEY(disciplina_id) REFERENCES disciplinas(id),
            FOREIGN KEY(professor_usuario_id) REFERENCES usuarios(id)
        )
        """
    )

    _adicionar_coluna_se_necessario(
        cursor, "horarios_escolares", "ano_letivo", "INTEGER NOT NULL DEFAULT 0"
    )
    _adicionar_coluna_se_necessario(
        cursor, "horarios_escolares", "turma_id", "INTEGER NOT NULL DEFAULT 0"
    )
    _adicionar_coluna_se_necessario(
        cursor, "horarios_escolares", "disciplina_id", "INTEGER NOT NULL DEFAULT 0"
    )
    _adicionar_coluna_se_necessario(
        cursor, "horarios_escolares", "professor_usuario_id", "INTEGER NOT NULL DEFAULT 0"
    )
    _adicionar_coluna_se_necessario(
        cursor, "horarios_escolares", "dia_semana", "TEXT NOT NULL DEFAULT ''"
    )
    _adicionar_coluna_se_necessario(
        cursor, "horarios_escolares", "aula_numero", "INTEGER NOT NULL DEFAULT 1"
    )
    _adicionar_coluna_se_necessario(
        cursor, "horarios_escolares", "criado_em", "TEXT NOT NULL DEFAULT ''"
    )
    _adicionar_coluna_se_necessario(
        cursor, "horarios_escolares", "atualizado_em", "TEXT NOT NULL DEFAULT ''"
    )

    cursor.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_horarios_escolares_turma_slot
        ON horarios_escolares(ano_letivo, turma_id, dia_semana, aula_numero)
        """
    )
    cursor.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_horarios_escolares_professor_slot
        ON horarios_escolares(ano_letivo, professor_usuario_id, dia_semana, aula_numero)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_horarios_escolares_professor_lookup
        ON horarios_escolares(ano_letivo, professor_usuario_id, dia_semana)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_horarios_escolares_turma_lookup
        ON horarios_escolares(ano_letivo, turma_id, dia_semana)
        """
    )

    conn.commit()


def downgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("DROP INDEX IF EXISTS idx_horarios_escolares_turma_lookup")
    cursor.execute("DROP INDEX IF EXISTS idx_horarios_escolares_professor_lookup")
    cursor.execute("DROP INDEX IF EXISTS idx_horarios_escolares_professor_slot")
    cursor.execute("DROP INDEX IF EXISTS idx_horarios_escolares_turma_slot")
    cursor.execute("DROP TABLE IF EXISTS horarios_escolares")
    conn.commit()


def main():
    parser = argparse.ArgumentParser(
        description="Migration: cria a estrutura do modulo de horario escolar"
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
