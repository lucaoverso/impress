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
    colunas = _listar_colunas(cursor, "usuarios")
    if "nt_hash" not in colunas:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN nt_hash CHAR(32)")
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_usuarios_nt_hash ON usuarios(nt_hash)")
    conn.commit()


def downgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("DROP INDEX IF EXISTS ix_usuarios_nt_hash")

    colunas = _listar_colunas(cursor, "usuarios")
    if "nt_hash" not in colunas:
        conn.commit()
        return

    cursor.execute("PRAGMA foreign_keys = OFF")
    cursor.execute("""
        CREATE TABLE usuarios__tmp (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            senha_hash TEXT NOT NULL,
            perfil TEXT NOT NULL,
            cargo TEXT NOT NULL DEFAULT 'PROFESSOR',
            data_nascimento TEXT
        )
    """)
    cursor.execute("""
        INSERT INTO usuarios__tmp (id, nome, email, senha_hash, perfil, cargo, data_nascimento)
        SELECT id, nome, email, senha_hash, perfil, cargo, data_nascimento
        FROM usuarios
    """)
    cursor.execute("DROP TABLE usuarios")
    cursor.execute("ALTER TABLE usuarios__tmp RENAME TO usuarios")
    cursor.execute("PRAGMA foreign_keys = ON")
    conn.commit()


def main():
    parser = argparse.ArgumentParser(description="Migration: adiciona/remove coluna usuarios.nt_hash")
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
