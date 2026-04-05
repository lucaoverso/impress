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


def upgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pcpi_registros_manuais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL,
            turno TEXT NOT NULL,
            tipo_acao TEXT NOT NULL,
            professor_nome TEXT,
            componente TEXT,
            turma TEXT,
            descricao_curta TEXT NOT NULL,
            observacoes TEXT,
            criado_por_usuario_id INTEGER,
            atualizado_por_usuario_id INTEGER,
            criado_em TEXT NOT NULL DEFAULT (datetime('now')),
            atualizado_em TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(criado_por_usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY(atualizado_por_usuario_id) REFERENCES usuarios(id)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_pcpi_registros_manuais_data_turno
        ON pcpi_registros_manuais(data, turno)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_pcpi_registros_manuais_tipo_acao
        ON pcpi_registros_manuais(tipo_acao)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_pcpi_registros_manuais_criado_por
        ON pcpi_registros_manuais(criado_por_usuario_id)
    """)

    conn.commit()


def downgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("DROP INDEX IF EXISTS idx_pcpi_registros_manuais_criado_por")
    cursor.execute("DROP INDEX IF EXISTS idx_pcpi_registros_manuais_tipo_acao")
    cursor.execute("DROP INDEX IF EXISTS idx_pcpi_registros_manuais_data_turno")
    cursor.execute("DROP TABLE IF EXISTS pcpi_registros_manuais")
    conn.commit()


def main():
    parser = argparse.ArgumentParser(
        description="Migration: cria/remove tabela pcpi_registros_manuais"
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
