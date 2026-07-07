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
        "pre_conselho_registros",
        "rav_acoes",
        "TEXT NOT NULL DEFAULT ''",
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS pre_conselho_habilidades_rav (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            periodo_id INTEGER,
            disciplina_id INTEGER NOT NULL,
            codigo TEXT NOT NULL DEFAULT '',
            descricao TEXT NOT NULL,
            ativo INTEGER NOT NULL DEFAULT 1,
            ordem INTEGER NOT NULL DEFAULT 0,
            criado_em TEXT NOT NULL DEFAULT (datetime('now')),
            atualizado_em TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(periodo_id) REFERENCES pre_conselho_periodos(id),
            FOREIGN KEY(disciplina_id) REFERENCES disciplinas(id)
        )
        """
    )
    _adicionar_coluna_se_necessario(
        cursor,
        "pre_conselho_habilidades_rav",
        "periodo_id",
        "INTEGER",
    )
    _adicionar_coluna_se_necessario(
        cursor,
        "pre_conselho_habilidades_rav",
        "codigo",
        "TEXT NOT NULL DEFAULT ''",
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS pre_conselho_habilidade_rav_turmas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            habilidade_id INTEGER NOT NULL,
            turma_id INTEGER NOT NULL,
            criado_em TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(habilidade_id) REFERENCES pre_conselho_habilidades_rav(id) ON DELETE CASCADE,
            FOREIGN KEY(turma_id) REFERENCES turmas(id),
            UNIQUE(habilidade_id, turma_id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS pre_conselho_registro_habilidades_rav (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            registro_id INTEGER NOT NULL,
            habilidade_id INTEGER NOT NULL,
            criado_em TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(registro_id) REFERENCES pre_conselho_registros(id) ON DELETE CASCADE,
            FOREIGN KEY(habilidade_id) REFERENCES pre_conselho_habilidades_rav(id),
            UNIQUE(registro_id, habilidade_id)
        )
        """
    )
    conn.commit()


def downgrade(conn: sqlite3.Connection):
    conn.commit()


def main():
    parser = argparse.ArgumentParser(
        description="Migration: adiciona habilidades e acoes de RAV no pre-conselho."
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
