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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ocorrencia_estudantes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ocorrencia_id INTEGER NOT NULL,
            estudante_id INTEGER,
            nome_estudante TEXT NOT NULL,
            turma_id INTEGER,
            turma_nome TEXT NOT NULL DEFAULT '',
            ordem INTEGER NOT NULL DEFAULT 0,
            criado_em TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(ocorrencia_id) REFERENCES ocorrencias(id),
            FOREIGN KEY(estudante_id) REFERENCES estudantes(id),
            FOREIGN KEY(turma_id) REFERENCES turmas(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ocorrencia_professores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ocorrencia_id INTEGER NOT NULL,
            professor_usuario_id INTEGER,
            nome_professor TEXT NOT NULL,
            email_professor TEXT NOT NULL DEFAULT '',
            ordem INTEGER NOT NULL DEFAULT 0,
            criado_em TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(ocorrencia_id) REFERENCES ocorrencias(id),
            FOREIGN KEY(professor_usuario_id) REFERENCES usuarios(id)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ocorrencia_estudantes_ocorrencia
        ON ocorrencia_estudantes(ocorrencia_id, ordem)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ocorrencia_estudantes_estudante
        ON ocorrencia_estudantes(estudante_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ocorrencia_professores_ocorrencia
        ON ocorrencia_professores(ocorrencia_id, ordem)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ocorrencia_professores_professor
        ON ocorrencia_professores(professor_usuario_id)
    """)

    cursor.execute(
        """
        INSERT INTO ocorrencia_estudantes (
            ocorrencia_id,
            estudante_id,
            nome_estudante,
            turma_id,
            turma_nome,
            ordem,
            criado_em
        )
        SELECT
            o.id,
            o.estudante_id,
            TRIM(COALESCE(o.nome_estudante, '')) AS nome_estudante,
            o.turma_id,
            COALESCE(t.nome, '') AS turma_nome,
            1,
            datetime('now')
        FROM ocorrencias o
        LEFT JOIN turmas t ON t.id = o.turma_id
        WHERE o.tipo_registro = 'estudante'
          AND TRIM(COALESCE(o.nome_estudante, '')) <> ''
          AND NOT EXISTS (
              SELECT 1
              FROM ocorrencia_estudantes oe
              WHERE oe.ocorrencia_id = o.id
          )
        """
    )

    cursor.execute(
        """
        INSERT INTO ocorrencia_professores (
            ocorrencia_id,
            professor_usuario_id,
            nome_professor,
            email_professor,
            ordem,
            criado_em
        )
        SELECT
            o.id,
            o.professor_requerente_id,
            TRIM(COALESCE(o.professor_requerente, '')) AS nome_professor,
            COALESCE(u.email, '') AS email_professor,
            1,
            datetime('now')
        FROM ocorrencias o
        LEFT JOIN usuarios u ON u.id = o.professor_requerente_id
        WHERE o.tipo_registro = 'professor'
          AND TRIM(COALESCE(o.professor_requerente, '')) <> ''
          AND NOT EXISTS (
              SELECT 1
              FROM ocorrencia_professores op
              WHERE op.ocorrencia_id = o.id
          )
        """
    )

    conn.commit()


def downgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM (
            SELECT ocorrencia_id
            FROM ocorrencia_estudantes
            GROUP BY ocorrencia_id
            HAVING COUNT(*) > 1
            UNION ALL
            SELECT ocorrencia_id
            FROM ocorrencia_professores
            GROUP BY ocorrencia_id
            HAVING COUNT(*) > 1
        )
    """)
    if int(cursor.fetchone()["total"] or 0) > 0:
        raise RuntimeError(
            "Nao e possivel remover os vinculos multiplos enquanto existirem registros com mais de um participante."
        )

    cursor.execute("DROP INDEX IF EXISTS idx_ocorrencia_professores_professor")
    cursor.execute("DROP INDEX IF EXISTS idx_ocorrencia_professores_ocorrencia")
    cursor.execute("DROP INDEX IF EXISTS idx_ocorrencia_estudantes_estudante")
    cursor.execute("DROP INDEX IF EXISTS idx_ocorrencia_estudantes_ocorrencia")
    cursor.execute("DROP TABLE IF EXISTS ocorrencia_professores")
    cursor.execute("DROP TABLE IF EXISTS ocorrencia_estudantes")
    conn.commit()


def main():
    parser = argparse.ArgumentParser(
        description="Migration: adiciona vinculos multiplos de estudantes e professores nas ocorrencias"
    )
    parser.add_argument("action", choices=["upgrade", "downgrade"], help="Acao da migration.")
    parser.add_argument("--db", default=_default_db_path(), help="Caminho do banco SQLite.")
    args = parser.parse_args()

    db_path = Path(args.db).expanduser()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        if args.action == "upgrade":
            upgrade(conn)
        else:
            downgrade(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
