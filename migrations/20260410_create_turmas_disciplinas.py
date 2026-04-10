#!/usr/bin/env python3
import argparse
import os
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]


def _default_db_path() -> str:
    env_path = os.getenv("DB_PATH", "").strip()
    if env_path:
        return env_path
    return str(BASE_DIR.parent / "sistema-impress-data" / "impressao.db")


def _colunas_tabela(cursor: sqlite3.Cursor, tabela: str) -> set[str]:
    cursor.execute(f"PRAGMA table_info({tabela})")
    return {row[1] for row in cursor.fetchall()}


def _existe_tabela(cursor: sqlite3.Cursor, tabela: str) -> bool:
    cursor.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (tabela,),
    )
    return cursor.fetchone() is not None


def upgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS turmas_disciplinas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            turma_id INTEGER NOT NULL,
            disciplina_id INTEGER NOT NULL,
            carga_horaria INTEGER NOT NULL DEFAULT 0,
            professor_usuario_id INTEGER,
            criado_em TEXT NOT NULL DEFAULT (datetime('now')),
            atualizado_em TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(turma_id) REFERENCES turmas(id),
            FOREIGN KEY(disciplina_id) REFERENCES disciplinas(id),
            FOREIGN KEY(professor_usuario_id) REFERENCES usuarios(id),
            UNIQUE(turma_id, disciplina_id)
        )
        """
    )

    colunas = _colunas_tabela(cursor, "turmas_disciplinas")
    if "carga_horaria" not in colunas:
        cursor.execute(
            "ALTER TABLE turmas_disciplinas ADD COLUMN carga_horaria INTEGER NOT NULL DEFAULT 0"
        )
    if "professor_usuario_id" not in colunas:
        cursor.execute(
            "ALTER TABLE turmas_disciplinas ADD COLUMN professor_usuario_id INTEGER"
        )
    if "criado_em" not in colunas:
        cursor.execute(
            "ALTER TABLE turmas_disciplinas ADD COLUMN criado_em TEXT NOT NULL DEFAULT ''"
        )
        cursor.execute(
            """
            UPDATE turmas_disciplinas
            SET criado_em = datetime('now')
            WHERE TRIM(COALESCE(criado_em, '')) = ''
            """
        )
    if "atualizado_em" not in colunas:
        cursor.execute(
            "ALTER TABLE turmas_disciplinas ADD COLUMN atualizado_em TEXT NOT NULL DEFAULT ''"
        )
        cursor.execute(
            """
            UPDATE turmas_disciplinas
            SET atualizado_em = datetime('now')
            WHERE TRIM(COALESCE(atualizado_em, '')) = ''
            """
        )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_turmas_disciplinas_turma
        ON turmas_disciplinas(turma_id, disciplina_id)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_turmas_disciplinas_professor
        ON turmas_disciplinas(professor_usuario_id, disciplina_id, turma_id)
        """
    )

    if _existe_tabela(cursor, "professores_turmas_disciplinas"):
        cursor.execute(
            """
            SELECT
                ptd.turma_id,
                ptd.disciplina_id,
                ptd.professor_usuario_id,
                COALESCE(d.aulas_semanais, 0) AS carga_horaria_padrao
            FROM professores_turmas_disciplinas ptd
            INNER JOIN disciplinas d ON d.id = ptd.disciplina_id
            ORDER BY ptd.id ASC
            """
        )
        for turma_id, disciplina_id, professor_usuario_id, carga_horaria_padrao in cursor.fetchall():
            cursor.execute(
                """
                INSERT OR IGNORE INTO turmas_disciplinas (
                    turma_id,
                    disciplina_id,
                    carga_horaria,
                    professor_usuario_id,
                    criado_em,
                    atualizado_em
                )
                VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))
                """,
                (
                    int(turma_id),
                    int(disciplina_id),
                    int(carga_horaria_padrao or 0),
                    int(professor_usuario_id) if int(professor_usuario_id or 0) > 0 else None,
                ),
            )
            cursor.execute(
                """
                UPDATE turmas_disciplinas
                SET professor_usuario_id = COALESCE(professor_usuario_id, ?),
                    carga_horaria = CASE
                        WHEN COALESCE(carga_horaria, 0) <= 0 THEN ?
                        ELSE carga_horaria
                    END,
                    atualizado_em = datetime('now')
                WHERE turma_id = ?
                  AND disciplina_id = ?
                """,
                (
                    int(professor_usuario_id) if int(professor_usuario_id or 0) > 0 else None,
                    int(carga_horaria_padrao or 0),
                    int(turma_id),
                    int(disciplina_id),
                ),
            )

    cursor.execute(
        """
        UPDATE turmas_disciplinas
        SET professor_usuario_id = NULL
        WHERE COALESCE(professor_usuario_id, 0) <= 0
        """
    )

    conn.commit()


def downgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("DROP INDEX IF EXISTS idx_turmas_disciplinas_professor")
    cursor.execute("DROP INDEX IF EXISTS idx_turmas_disciplinas_turma")
    cursor.execute("DROP TABLE IF EXISTS turmas_disciplinas")
    conn.commit()


def main():
    parser = argparse.ArgumentParser(
        description="Migration: cria a estrutura turma x disciplina com carga horaria e professor vinculado"
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
