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


def _tabela_existe(cursor: sqlite3.Cursor, tabela: str) -> bool:
    cursor.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        LIMIT 1
        """,
        (tabela,),
    )
    return cursor.fetchone() is not None


def _colunas_tabela(cursor: sqlite3.Cursor, tabela: str) -> set[str]:
    cursor.execute(f"PRAGMA table_info({tabela})")
    return {row[1] for row in cursor.fetchall()}


def _adicionar_coluna_se_necessario(
    cursor: sqlite3.Cursor,
    tabela: str,
    coluna: str,
    definicao: str,
) -> None:
    if not _tabela_existe(cursor, tabela):
        return
    if coluna in _colunas_tabela(cursor, tabela):
        return
    cursor.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {definicao}")


def upgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()

    _adicionar_coluna_se_necessario(
        cursor,
        "disciplinas",
        "tem_apc",
        "INTEGER NOT NULL DEFAULT 0",
    )
    _adicionar_coluna_se_necessario(
        cursor,
        "disciplinas",
        "tem_prova_bimestral",
        "INTEGER NOT NULL DEFAULT 0",
    )
    if _tabela_existe(cursor, "disciplinas"):
        cursor.execute(
            """
            UPDATE disciplinas
            SET tem_apc = COALESCE(tem_apc, 0),
                tem_prova_bimestral = COALESCE(tem_prova_bimestral, 0)
            """
        )

    _adicionar_coluna_se_necessario(
        cursor,
        "apc_periodos",
        "tipo_entrega",
        "TEXT NOT NULL DEFAULT 'GERAL'",
    )
    if _tabela_existe(cursor, "apc_periodos"):
        cursor.execute(
            """
            UPDATE apc_periodos
            SET tipo_entrega = 'GERAL'
            WHERE TRIM(COALESCE(tipo_entrega, '')) = ''
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_apc_periodos_tipo_entrega
            ON apc_periodos(tipo_entrega, data_referencia)
            """
        )

    conn.commit()


def downgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("DROP INDEX IF EXISTS idx_apc_periodos_tipo_entrega")
    conn.commit()


def main():
    parser = argparse.ArgumentParser(
        description="Migration: adiciona flags de disciplina e tipo de entrega no APC."
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
