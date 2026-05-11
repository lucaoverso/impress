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
    cursor: sqlite3.Cursor, tabela: str, coluna: str, definicao: str
) -> None:
    if coluna in _colunas_tabela(cursor, tabela):
        return
    cursor.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {definicao}")


def _atualizar_faixa_global(cursor: sqlite3.Cursor) -> None:
    cursor.execute(
        """
        UPDATE horarios_escolares
        SET faixa_global = COALESCE(
            (
                SELECT
                    CASE
                        WHEN UPPER(COALESCE(t.turno, '')) IN ('VESPERTINO', 'VESPERTINO_EM')
                            THEN CAST(COALESCE(horarios_escolares.aula_numero, 0) AS INTEGER) + 5
                        WHEN UPPER(COALESCE(t.turno, '')) = 'INTEGRAL'
                            THEN CAST(COALESCE(horarios_escolares.aula_numero, 0) AS INTEGER)
                                 + CASE
                                     WHEN CAST(COALESCE(horarios_escolares.aula_numero, 0) AS INTEGER) > 5
                                         THEN 1
                                     ELSE 0
                                   END
                        ELSE CAST(COALESCE(horarios_escolares.aula_numero, 0) AS INTEGER)
                    END
                FROM turmas t
                WHERE t.id = horarios_escolares.turma_id
            ),
            CAST(COALESCE(horarios_escolares.aula_numero, 0) AS INTEGER)
        )
        """
    )


def upgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()

    if not _tabela_existe(cursor, "horarios_escolares"):
        conn.commit()
        return

    _adicionar_coluna_se_necessario(
        cursor,
        "horarios_escolares",
        "faixa_global",
        "INTEGER NOT NULL DEFAULT 0",
    )
    _atualizar_faixa_global(cursor)

    cursor.execute("DROP INDEX IF EXISTS idx_horarios_escolares_professor_slot")
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_horarios_escolares_professor_faixa_lookup
        ON horarios_escolares(ano_letivo, professor_usuario_id, dia_semana, faixa_global)
        """
    )

    conn.commit()


def downgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()

    if not _tabela_existe(cursor, "horarios_escolares"):
        conn.commit()
        return

    cursor.execute("DROP INDEX IF EXISTS idx_horarios_escolares_professor_faixa_lookup")
    cursor.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_horarios_escolares_professor_slot
        ON horarios_escolares(ano_letivo, professor_usuario_id, dia_semana, aula_numero)
        """
    )

    conn.commit()


def main():
    parser = argparse.ArgumentParser(
        description="Migration: corrige conflito de horario escolar usando faixa global."
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
