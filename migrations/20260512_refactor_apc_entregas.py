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


def _criar_tabela_apc_periodos_refatorada(cursor: sqlite3.Cursor, tabela: str) -> None:
    cursor.execute(
        f"""
        CREATE TABLE {tabela} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ano_letivo INTEGER NOT NULL,
            data_referencia TEXT NOT NULL,
            prazo_envio TEXT NOT NULL,
            titulo TEXT NOT NULL DEFAULT 'Documento',
            observacao TEXT NOT NULL DEFAULT '',
            publico_alvo TEXT NOT NULL DEFAULT 'TODOS_PROFESSORES',
            criado_por_usuario_id INTEGER NOT NULL,
            criado_em TEXT NOT NULL DEFAULT (datetime('now')),
            atualizado_em TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(criado_por_usuario_id) REFERENCES usuarios(id),
            UNIQUE(ano_letivo, data_referencia, titulo, publico_alvo)
        )
        """
    )


def _copiar_periodos_legados(cursor: sqlite3.Cursor, origem: str, destino: str) -> None:
    colunas = _colunas_tabela(cursor, origem)
    publico_expr = (
        "COALESCE(NULLIF(TRIM(publico_alvo), ''), 'HORARIO_DIA')"
        if "publico_alvo" in colunas
        else "'HORARIO_DIA'"
    )
    cursor.execute(
        f"""
        INSERT INTO {destino} (
            id,
            ano_letivo,
            data_referencia,
            prazo_envio,
            titulo,
            observacao,
            publico_alvo,
            criado_por_usuario_id,
            criado_em,
            atualizado_em
        )
        SELECT
            id,
            ano_letivo,
            data_referencia,
            prazo_envio,
            COALESCE(NULLIF(TRIM(titulo), ''), 'Documento'),
            COALESCE(observacao, ''),
            {publico_expr},
            criado_por_usuario_id,
            COALESCE(NULLIF(TRIM(criado_em), ''), datetime('now')),
            COALESCE(NULLIF(TRIM(atualizado_em), ''), datetime('now'))
        FROM {origem}
        ORDER BY id ASC
        """
    )


def _criar_indices_apc_periodos(cursor: sqlite3.Cursor) -> None:
    cursor.execute("DROP INDEX IF EXISTS idx_apc_periodos_data")
    cursor.execute("DROP INDEX IF EXISTS idx_apc_periodos_publico")
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_apc_periodos_data
        ON apc_periodos(ano_letivo, data_referencia, prazo_envio)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_apc_periodos_publico
        ON apc_periodos(publico_alvo, data_referencia)
        """
    )


def upgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()
    if not _tabela_existe(cursor, "apc_periodos"):
        conn.commit()
        return

    conn.execute("PRAGMA foreign_keys = OFF")
    cursor.execute("DROP TABLE IF EXISTS apc_periodos_refatorado")
    _criar_tabela_apc_periodos_refatorada(cursor, "apc_periodos_refatorado")
    _copiar_periodos_legados(cursor, "apc_periodos", "apc_periodos_refatorado")
    cursor.execute("DROP TABLE apc_periodos")
    cursor.execute("ALTER TABLE apc_periodos_refatorado RENAME TO apc_periodos")
    _criar_indices_apc_periodos(cursor)
    conn.commit()
    conn.execute("PRAGMA foreign_keys = ON")


def downgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()
    if not _tabela_existe(cursor, "apc_periodos"):
        conn.commit()
        return

    conn.execute("PRAGMA foreign_keys = OFF")
    cursor.execute("DROP TABLE IF EXISTS apc_periodos_legado")
    cursor.execute(
        """
        CREATE TABLE apc_periodos_legado (
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
    cursor.execute(
        """
        INSERT OR IGNORE INTO apc_periodos_legado (
            id,
            ano_letivo,
            data_referencia,
            prazo_envio,
            titulo,
            observacao,
            criado_por_usuario_id,
            criado_em,
            atualizado_em
        )
        SELECT
            id,
            ano_letivo,
            data_referencia,
            prazo_envio,
            COALESCE(NULLIF(TRIM(titulo), ''), 'APC'),
            COALESCE(observacao, ''),
            criado_por_usuario_id,
            criado_em,
            atualizado_em
        FROM apc_periodos
        ORDER BY id ASC
        """
    )
    cursor.execute("DROP TABLE apc_periodos")
    cursor.execute("ALTER TABLE apc_periodos_legado RENAME TO apc_periodos")
    cursor.execute("DROP INDEX IF EXISTS idx_apc_periodos_publico")
    cursor.execute("DROP INDEX IF EXISTS idx_apc_periodos_data")
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_apc_periodos_data
        ON apc_periodos(ano_letivo, data_referencia)
        """
    )
    conn.commit()
    conn.execute("PRAGMA foreign_keys = ON")


def main():
    parser = argparse.ArgumentParser(
        description="Migration: refatora o modulo de APC para entregas com multiplas solicitacoes."
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
