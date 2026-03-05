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
    cursor.execute("PRAGMA table_info(usuarios)")
    colunas = {str(row[1]) for row in cursor.fetchall()}
    filtro_ativo = ""
    if "ativo" in colunas:
        filtro_ativo = " AND (ativo = 1 OR LOWER(CAST(ativo AS TEXT)) = 'true')"

    cursor.execute("DROP VIEW IF EXISTS radcheck")
    cursor.execute(f"""
        CREATE VIEW radcheck AS
        SELECT
            email AS username,
            'NT-Password' AS attribute,
            ':=' AS op,
            nt_hash AS value
        FROM usuarios
        WHERE TRIM(COALESCE(email, '')) <> ''
          AND TRIM(COALESCE(nt_hash, '')) <> ''
          {filtro_ativo}
    """)
    conn.commit()


def downgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("DROP VIEW IF EXISTS radcheck")
    conn.commit()


def main():
    parser = argparse.ArgumentParser(description="Migration: cria/remove view radcheck")
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
