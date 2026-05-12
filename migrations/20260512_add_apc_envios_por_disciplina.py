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


def _criar_tabela_apc_envios(cursor: sqlite3.Cursor, tabela: str) -> None:
    cursor.execute(
        f"""
        CREATE TABLE {tabela} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            periodo_id INTEGER NOT NULL,
            professor_usuario_id INTEGER NOT NULL,
            turma_id INTEGER NOT NULL DEFAULT 0,
            disciplina_id INTEGER NOT NULL DEFAULT 0,
            arquivo_nome_original TEXT NOT NULL,
            arquivo_path TEXT NOT NULL,
            arquivo_tamanho INTEGER NOT NULL DEFAULT 0,
            arquivo_tipo TEXT NOT NULL DEFAULT '',
            enviado_em TEXT NOT NULL DEFAULT (datetime('now')),
            atualizado_em TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(periodo_id) REFERENCES apc_periodos(id),
            FOREIGN KEY(professor_usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY(turma_id) REFERENCES turmas(id),
            FOREIGN KEY(disciplina_id) REFERENCES disciplinas(id),
            UNIQUE(periodo_id, professor_usuario_id, turma_id, disciplina_id)
        )
        """
    )


def _copiar_envios(cursor: sqlite3.Cursor, origem: str, destino: str) -> None:
    colunas = _colunas_tabela(cursor, origem)
    turma_expr = "COALESCE(turma_id, 0)" if "turma_id" in colunas else "0"
    disciplina_expr = "COALESCE(disciplina_id, 0)" if "disciplina_id" in colunas else "0"
    cursor.execute(
        f"""
        INSERT OR IGNORE INTO {destino} (
            id,
            periodo_id,
            professor_usuario_id,
            turma_id,
            disciplina_id,
            arquivo_nome_original,
            arquivo_path,
            arquivo_tamanho,
            arquivo_tipo,
            enviado_em,
            atualizado_em
        )
        SELECT
            id,
            periodo_id,
            professor_usuario_id,
            {turma_expr},
            {disciplina_expr},
            arquivo_nome_original,
            arquivo_path,
            arquivo_tamanho,
            arquivo_tipo,
            COALESCE(NULLIF(TRIM(enviado_em), ''), datetime('now')),
            COALESCE(NULLIF(TRIM(atualizado_em), ''), datetime('now'))
        FROM {origem}
        ORDER BY id ASC
        """
    )


def _criar_indices(cursor: sqlite3.Cursor) -> None:
    cursor.execute("DROP INDEX IF EXISTS idx_apc_envios_periodo")
    cursor.execute("DROP INDEX IF EXISTS idx_apc_envios_professor")
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_apc_envios_periodo
        ON apc_envios(periodo_id, professor_usuario_id, turma_id, disciplina_id)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_apc_envios_professor
        ON apc_envios(professor_usuario_id, enviado_em)
        """
    )


def upgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()
    if not _tabela_existe(cursor, "apc_envios"):
        conn.commit()
        return

    conn.execute("PRAGMA foreign_keys = OFF")
    cursor.execute("DROP TABLE IF EXISTS apc_envios_por_disciplina")
    _criar_tabela_apc_envios(cursor, "apc_envios_por_disciplina")
    _copiar_envios(cursor, "apc_envios", "apc_envios_por_disciplina")
    cursor.execute("DROP TABLE apc_envios")
    cursor.execute("ALTER TABLE apc_envios_por_disciplina RENAME TO apc_envios")
    _criar_indices(cursor)
    conn.commit()
    conn.execute("PRAGMA foreign_keys = ON")


def downgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()
    if not _tabela_existe(cursor, "apc_envios"):
        conn.commit()
        return

    conn.execute("PRAGMA foreign_keys = OFF")
    cursor.execute("DROP TABLE IF EXISTS apc_envios_legado")
    cursor.execute(
        """
        CREATE TABLE apc_envios_legado (
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
    cursor.execute(
        """
        INSERT OR IGNORE INTO apc_envios_legado (
            id,
            periodo_id,
            professor_usuario_id,
            arquivo_nome_original,
            arquivo_path,
            arquivo_tamanho,
            arquivo_tipo,
            enviado_em,
            atualizado_em
        )
        SELECT
            id,
            periodo_id,
            professor_usuario_id,
            arquivo_nome_original,
            arquivo_path,
            arquivo_tamanho,
            arquivo_tipo,
            enviado_em,
            atualizado_em
        FROM apc_envios
        ORDER BY id ASC
        """
    )
    cursor.execute("DROP TABLE apc_envios")
    cursor.execute("ALTER TABLE apc_envios_legado RENAME TO apc_envios")
    cursor.execute("DROP INDEX IF EXISTS idx_apc_envios_periodo")
    cursor.execute("DROP INDEX IF EXISTS idx_apc_envios_professor")
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
    conn.execute("PRAGMA foreign_keys = ON")


def main():
    parser = argparse.ArgumentParser(
        description="Migration: ajusta APC para aceitar envios separados por disciplina."
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
