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


def upgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS apc_periodo_destinatarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            periodo_id INTEGER NOT NULL,
            professor_usuario_id INTEGER NOT NULL,
            turma_id INTEGER NOT NULL DEFAULT 0,
            disciplina_id INTEGER NOT NULL DEFAULT 0,
            criado_em TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(periodo_id) REFERENCES apc_periodos(id) ON DELETE CASCADE,
            FOREIGN KEY(professor_usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY(turma_id) REFERENCES turmas(id),
            FOREIGN KEY(disciplina_id) REFERENCES disciplinas(id),
            UNIQUE(periodo_id, professor_usuario_id, turma_id, disciplina_id)
        )
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_apc_destinatarios_periodo
        ON apc_periodo_destinatarios(periodo_id, professor_usuario_id)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_apc_destinatarios_professor
        ON apc_periodo_destinatarios(professor_usuario_id, periodo_id)
        """
    )
    conn.commit()


def downgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("DROP INDEX IF EXISTS idx_apc_destinatarios_professor")
    cursor.execute("DROP INDEX IF EXISTS idx_apc_destinatarios_periodo")
    cursor.execute("DROP TABLE IF EXISTS apc_periodo_destinatarios")
    conn.commit()


def main():
    parser = argparse.ArgumentParser(
        description="Migration: adiciona destinatarios selecionados ao modulo APC."
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
