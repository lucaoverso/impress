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
        CREATE TABLE IF NOT EXISTS apc_periodos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ano_letivo INTEGER NOT NULL,
            data_referencia TEXT NOT NULL,
            prazo_envio TEXT NOT NULL,
            titulo TEXT NOT NULL DEFAULT 'APC',
            observacao TEXT NOT NULL DEFAULT '',
            criado_por_usuario_id INTEGER NOT NULL,
            criado_em TEXT NOT NULL DEFAULT (datetime('now')),
            atualizado_em TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(criado_por_usuario_id) REFERENCES usuarios(id),
            UNIQUE(ano_letivo, data_referencia)
        )
        """
    )

    _adicionar_coluna_se_necessario(
        cursor, "apc_periodos", "ano_letivo", "INTEGER NOT NULL DEFAULT 0"
    )
    _adicionar_coluna_se_necessario(
        cursor, "apc_periodos", "data_referencia", "TEXT NOT NULL DEFAULT ''"
    )
    _adicionar_coluna_se_necessario(
        cursor, "apc_periodos", "prazo_envio", "TEXT NOT NULL DEFAULT ''"
    )
    _adicionar_coluna_se_necessario(
        cursor, "apc_periodos", "titulo", "TEXT NOT NULL DEFAULT 'APC'"
    )
    _adicionar_coluna_se_necessario(
        cursor, "apc_periodos", "observacao", "TEXT NOT NULL DEFAULT ''"
    )
    _adicionar_coluna_se_necessario(
        cursor, "apc_periodos", "criado_por_usuario_id", "INTEGER NOT NULL DEFAULT 0"
    )
    _adicionar_coluna_se_necessario(
        cursor, "apc_periodos", "criado_em", "TEXT NOT NULL DEFAULT ''"
    )
    _adicionar_coluna_se_necessario(
        cursor, "apc_periodos", "atualizado_em", "TEXT NOT NULL DEFAULT ''"
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS apc_envios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            periodo_id INTEGER NOT NULL,
            professor_usuario_id INTEGER NOT NULL,
            arquivo_nome_original TEXT NOT NULL,
            arquivo_path TEXT NOT NULL,
            arquivo_tamanho INTEGER NOT NULL DEFAULT 0,
            arquivo_tipo TEXT NOT NULL DEFAULT '',
            enviado_em TEXT NOT NULL DEFAULT (datetime('now')),
            atualizado_em TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(periodo_id) REFERENCES apc_periodos(id),
            FOREIGN KEY(professor_usuario_id) REFERENCES usuarios(id),
            UNIQUE(periodo_id, professor_usuario_id)
        )
        """
    )

    _adicionar_coluna_se_necessario(
        cursor, "apc_envios", "periodo_id", "INTEGER NOT NULL DEFAULT 0"
    )
    _adicionar_coluna_se_necessario(
        cursor, "apc_envios", "professor_usuario_id", "INTEGER NOT NULL DEFAULT 0"
    )
    _adicionar_coluna_se_necessario(
        cursor, "apc_envios", "arquivo_nome_original", "TEXT NOT NULL DEFAULT ''"
    )
    _adicionar_coluna_se_necessario(
        cursor, "apc_envios", "arquivo_path", "TEXT NOT NULL DEFAULT ''"
    )
    _adicionar_coluna_se_necessario(
        cursor, "apc_envios", "arquivo_tamanho", "INTEGER NOT NULL DEFAULT 0"
    )
    _adicionar_coluna_se_necessario(
        cursor, "apc_envios", "arquivo_tipo", "TEXT NOT NULL DEFAULT ''"
    )
    _adicionar_coluna_se_necessario(
        cursor, "apc_envios", "enviado_em", "TEXT NOT NULL DEFAULT ''"
    )
    _adicionar_coluna_se_necessario(
        cursor, "apc_envios", "atualizado_em", "TEXT NOT NULL DEFAULT ''"
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_apc_periodos_data
        ON apc_periodos(ano_letivo, data_referencia)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_apc_envios_periodo
        ON apc_envios(periodo_id, professor_usuario_id)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_apc_envios_professor
        ON apc_envios(professor_usuario_id, enviado_em)
        """
    )

    conn.commit()


def downgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("DROP INDEX IF EXISTS idx_apc_envios_professor")
    cursor.execute("DROP INDEX IF EXISTS idx_apc_envios_periodo")
    cursor.execute("DROP INDEX IF EXISTS idx_apc_periodos_data")
    cursor.execute("DROP TABLE IF EXISTS apc_envios")
    cursor.execute("DROP TABLE IF EXISTS apc_periodos")
    conn.commit()


def main():
    parser = argparse.ArgumentParser(description="Migration: cria a estrutura do modulo APC")
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
