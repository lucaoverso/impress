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


def _table_exists(cursor: sqlite3.Cursor, table: str) -> bool:
    cursor.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        LIMIT 1
        """,
        (table,),
    )
    return cursor.fetchone() is not None


def _columns(cursor: sqlite3.Cursor, table: str) -> set[str]:
    cursor.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cursor.fetchall()}


def _add_column_if_needed(
    cursor: sqlite3.Cursor,
    table: str,
    column: str,
    definition: str,
) -> None:
    if column in _columns(cursor, table):
        return
    cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _lesson_window_from_turn(turn: str) -> tuple[int, int]:
    turn_norm = str(turn or "").strip().upper()
    if turn_norm == "VESPERTINO":
        return (6, 10)
    if turn_norm == "VESPERTINO_EM":
        return (6, 11)
    if turn_norm == "INTEGRAL":
        return (1, 8)
    return (1, 5)


def _backfill_turmas(cursor: sqlite3.Cursor) -> None:
    cursor.execute("SELECT id, turno, aula_inicial, aula_final FROM turmas")
    for turma_id, turn, start_lesson, end_lesson in cursor.fetchall():
        if int(start_lesson or 0) > 0 and int(end_lesson or 0) >= int(start_lesson or 0):
            continue
        start_default, end_default = _lesson_window_from_turn(turn)
        cursor.execute(
            """
            UPDATE turmas
            SET aula_inicial = ?, aula_final = ?
            WHERE id = ?
            """,
            (start_default, end_default, int(turma_id)),
        )


def _backfill_horarios(cursor: sqlite3.Cursor) -> None:
    if not _table_exists(cursor, "horarios_escolares"):
        return
    existing_columns = _columns(cursor, "horarios_escolares")
    if "aula_numero" not in existing_columns:
        return

    cursor.execute(
        """
        UPDATE horarios_escolares
        SET aula_numero = (
            CASE
                WHEN UPPER(COALESCE((
                    SELECT t.turno
                    FROM turmas t
                    WHERE t.id = horarios_escolares.turma_id
                ), '')) IN ('VESPERTINO', 'VESPERTINO_EM')
                    THEN CAST(COALESCE(NULLIF(horarios_escolares.faixa_global, 0), horarios_escolares.aula_numero, 0) AS INTEGER)
                ELSE CAST(COALESCE(horarios_escolares.aula_numero, 0) AS INTEGER)
            END
        )
        WHERE CAST(COALESCE(horarios_escolares.aula_numero, 0) AS INTEGER) > 0
        """
    )

    if "faixa_global" in existing_columns:
        cursor.execute(
            """
            UPDATE horarios_escolares
            SET faixa_global = CAST(COALESCE(aula_numero, 0) AS INTEGER)
            WHERE CAST(COALESCE(aula_numero, 0) AS INTEGER) > 0
            """
        )


def _backfill_agendamentos(cursor: sqlite3.Cursor) -> None:
    if not _table_exists(cursor, "agendamentos"):
        return
    existing_columns = _columns(cursor, "agendamentos")
    if "aula" not in existing_columns:
        return

    cursor.execute(
        """
        UPDATE agendamentos
        SET aula = (
            CASE
                WHEN UPPER(COALESCE(turno, '')) IN ('VESPERTINO', 'VESPERTINO_EM')
                    THEN CAST(COALESCE(NULLIF(faixa_global, 0), NULLIF(TRIM(aula), ''), '0') AS INTEGER)
                ELSE CAST(COALESCE(NULLIF(TRIM(aula), ''), '0') AS INTEGER)
            END
        )
        WHERE CAST(COALESCE(NULLIF(TRIM(aula), ''), '0') AS INTEGER) > 0
           OR CAST(COALESCE(faixa_global, 0) AS INTEGER) > 0
        """
    )

    if "faixa_global" in existing_columns:
        cursor.execute(
            """
            UPDATE agendamentos
            SET faixa_global = CAST(COALESCE(NULLIF(TRIM(aula), ''), '0') AS INTEGER)
            WHERE CAST(COALESCE(NULLIF(TRIM(aula), ''), '0') AS INTEGER) > 0
            """
        )


def upgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()

    if _table_exists(cursor, "turmas"):
        _add_column_if_needed(cursor, "turmas", "aula_inicial", "INTEGER NOT NULL DEFAULT 1")
        _add_column_if_needed(cursor, "turmas", "aula_final", "INTEGER NOT NULL DEFAULT 0")

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS configuracao_aulas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ordem_visual INTEGER NOT NULL DEFAULT 0,
            tipo TEXT NOT NULL DEFAULT 'AULA',
            aula_numero INTEGER,
            nome TEXT NOT NULL DEFAULT '',
            horario_inicio TEXT NOT NULL DEFAULT '',
            horario_fim TEXT NOT NULL DEFAULT '',
            ativo INTEGER NOT NULL DEFAULT 1,
            criado_em TEXT NOT NULL DEFAULT (datetime('now')),
            atualizado_em TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_configuracao_aulas_ordem_visual
        ON configuracao_aulas(ordem_visual, id)
        """
    )
    cursor.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_configuracao_aulas_numero_unico
        ON configuracao_aulas(aula_numero)
        WHERE aula_numero IS NOT NULL
        """
    )

    _backfill_turmas(cursor)
    _backfill_horarios(cursor)
    _backfill_agendamentos(cursor)

    conn.commit()


def downgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("DROP INDEX IF EXISTS idx_configuracao_aulas_numero_unico")
    cursor.execute("DROP INDEX IF EXISTS idx_configuracao_aulas_ordem_visual")
    cursor.execute("DROP TABLE IF EXISTS configuracao_aulas")
    conn.commit()


def main():
    parser = argparse.ArgumentParser(
        description="Migration: cria configuracao global de aulas e migra horarios para aula global."
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
