#!/usr/bin/env python3
import argparse
import os
import sqlite3
from pathlib import Path


ACOES_APLICADAS = (
    "orientacao_verbal",
    "advertencia",
    "chamada_responsavel",
    "encaminhamento_direcao",
    "registro_informativo",
)

STATUS_OCORRENCIA = (
    "registrado",
    "em_acompanhamento",
    "aguardando_responsavel",
    "resolvido",
)


def _default_db_path() -> str:
    env_path = os.getenv("DB_PATH", "").strip()
    if env_path:
        return env_path
    base_dir = Path(__file__).resolve().parents[1]
    return str(base_dir.parent / "sistema-impress-data" / "impressao.db")


def upgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS ocorrencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_estudante TEXT NOT NULL,
            turma_id INTEGER NOT NULL,
            professor_requerente TEXT NOT NULL,
            disciplina TEXT NOT NULL,
            data_ocorrencia TEXT NOT NULL,
            aula TEXT NOT NULL,
            horario_ocorrencia TEXT NOT NULL,
            descricao TEXT NOT NULL,
            acao_aplicada TEXT NOT NULL CHECK (acao_aplicada IN {ACOES_APLICADAS}),
            status TEXT NOT NULL DEFAULT 'registrado' CHECK (status IN {STATUS_OCORRENCIA}),
            criado_em TEXT NOT NULL DEFAULT (datetime('now')),
            atualizado_em TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(turma_id) REFERENCES turmas(id)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ocorrencias_status
        ON ocorrencias(status)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ocorrencias_turma_id
        ON ocorrencias(turma_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ocorrencias_data_ocorrencia
        ON ocorrencias(data_ocorrencia)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ocorrencias_nome_estudante
        ON ocorrencias(nome_estudante)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ocorrencias_data_criado
        ON ocorrencias(data_ocorrencia DESC, criado_em DESC)
    """)

    conn.commit()


def downgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("DROP INDEX IF EXISTS idx_ocorrencias_data_criado")
    cursor.execute("DROP INDEX IF EXISTS idx_ocorrencias_nome_estudante")
    cursor.execute("DROP INDEX IF EXISTS idx_ocorrencias_data_ocorrencia")
    cursor.execute("DROP INDEX IF EXISTS idx_ocorrencias_turma_id")
    cursor.execute("DROP INDEX IF EXISTS idx_ocorrencias_status")
    cursor.execute("DROP TABLE IF EXISTS ocorrencias")
    conn.commit()


def main():
    parser = argparse.ArgumentParser(description="Migration: cria/remove tabela ocorrencias")
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
