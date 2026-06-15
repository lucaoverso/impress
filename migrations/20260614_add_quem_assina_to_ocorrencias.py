#!/usr/bin/env python3
import argparse
import os
import sqlite3
from pathlib import Path


QUEM_ASSINA_VALIDOS = ("estudante", "responsavel")


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
    cursor.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = 'ocorrencias'
    """
    )
    if not cursor.fetchone():
        conn.commit()
        return

    colunas = _listar_colunas(cursor, "ocorrencias")
    if "quem_assina" not in colunas:
        cursor.execute("ALTER TABLE ocorrencias ADD COLUMN quem_assina TEXT")

    placeholders = ",".join("?" for _ in QUEM_ASSINA_VALIDOS)
    cursor.execute(
        f"""
        UPDATE ocorrencias
        SET quem_assina = NULL
        WHERE TRIM(COALESCE(quem_assina, '')) <> ''
          AND TRIM(COALESCE(quem_assina, '')) NOT IN ({placeholders})
    """,
        QUEM_ASSINA_VALIDOS,
    )
    conn.commit()


def downgrade(conn: sqlite3.Connection):
    conn.commit()


def main():
    parser = argparse.ArgumentParser(
        description="Migration: adiciona campo quem_assina em ocorrencias"
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
