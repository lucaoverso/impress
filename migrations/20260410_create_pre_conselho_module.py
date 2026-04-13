#!/usr/bin/env python3
import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from services.preconselho_service import (
    catalogo_motivos_iniciais_pre_conselho,
    periodos_padrao_pre_conselho,
)


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


def _adicionar_coluna_se_necessario(
    cursor: sqlite3.Cursor, tabela: str, coluna: str, definicao: str
):
    if coluna in _colunas_tabela(cursor, tabela):
        return
    cursor.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {definicao}")


def _seed_periodos(cursor: sqlite3.Cursor):
    for periodo in periodos_padrao_pre_conselho():
        cursor.execute(
            """
            INSERT OR IGNORE INTO pre_conselho_periodos (
                nome,
                ano_letivo,
                etapa,
                data_inicio,
                data_fim,
                status,
                criado_em,
                atualizado_em
            )
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            """,
            (
                periodo["nome"],
                int(periodo["ano_letivo"]),
                int(periodo["etapa"]),
                periodo["data_inicio"],
                periodo["data_fim"],
                periodo["status"],
            ),
        )


def _seed_motivos(cursor: sqlite3.Cursor):
    for motivo in catalogo_motivos_iniciais_pre_conselho():
        cursor.execute(
            """
            INSERT OR IGNORE INTO pre_conselho_motivos (
                categoria,
                codigo,
                descricao,
                ativo,
                ordem,
                criado_em,
                atualizado_em
            )
            VALUES (?, ?, ?, 1, ?, datetime('now'), datetime('now'))
            """,
            (
                motivo["categoria"],
                motivo["codigo"],
                motivo["descricao"],
                int(motivo.get("ordem") or 0),
            ),
        )


def _migrar_motivos_legados(cursor: sqlite3.Cursor):
    if not _existe_tabela(cursor, "pre_conselho_registros"):
        return

    cursor.execute("SELECT id, codigo FROM pre_conselho_motivos")
    motivos_por_codigo = {str(row[1] or "").strip(): int(row[0]) for row in cursor.fetchall()}

    cursor.execute(
        """
        SELECT id, motivos
        FROM pre_conselho_registros
        WHERE TRIM(COALESCE(motivos, '')) <> ''
        """
    )
    for registro_id, motivos_json in cursor.fetchall():
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM pre_conselho_registro_motivos
            WHERE registro_id = ?
            """,
            (int(registro_id),),
        )
        if int(cursor.fetchone()[0] or 0) > 0:
            continue

        try:
            codigos = json.loads(motivos_json or "[]")
        except json.JSONDecodeError:
            codigos = []

        for codigo in codigos:
            motivo_id = int(motivos_por_codigo.get(str(codigo or "").strip()) or 0)
            if motivo_id <= 0:
                continue
            cursor.execute(
                """
                INSERT OR IGNORE INTO pre_conselho_registro_motivos (registro_id, motivo_id, criado_em)
                VALUES (?, ?, datetime('now'))
                """,
                (int(registro_id), motivo_id),
            )


def upgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS pre_conselho_periodos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            ano_letivo INTEGER NOT NULL,
            etapa INTEGER NOT NULL,
            data_inicio TEXT NOT NULL,
            data_fim TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'FECHADO',
            criado_em TEXT NOT NULL DEFAULT (datetime('now')),
            atualizado_em TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(ano_letivo, etapa)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS pre_conselho_motivos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            categoria TEXT NOT NULL,
            codigo TEXT NOT NULL UNIQUE,
            descricao TEXT NOT NULL,
            ativo INTEGER NOT NULL DEFAULT 1,
            ordem INTEGER NOT NULL DEFAULT 0,
            criado_em TEXT NOT NULL DEFAULT (datetime('now')),
            atualizado_em TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS pre_conselho_registros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            periodo_id INTEGER,
            disciplina_id INTEGER,
            professor_usuario_id INTEGER NOT NULL DEFAULT 0,
            turma_id INTEGER NOT NULL DEFAULT 0,
            estudante_id INTEGER NOT NULL DEFAULT 0,
            nivel_atencao TEXT,
            disciplina TEXT NOT NULL DEFAULT '',
            ano_letivo INTEGER NOT NULL DEFAULT 0,
            bimestre INTEGER NOT NULL DEFAULT 0,
            motivos TEXT NOT NULL DEFAULT '[]',
            observacoes TEXT NOT NULL DEFAULT '',
            observacao_professor TEXT NOT NULL DEFAULT '',
            texto_gerado TEXT NOT NULL DEFAULT '',
            criado_em TEXT NOT NULL DEFAULT (datetime('now')),
            atualizado_em TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS pre_conselho_registro_motivos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            registro_id INTEGER NOT NULL,
            motivo_id INTEGER NOT NULL,
            criado_em TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(registro_id) REFERENCES pre_conselho_registros(id) ON DELETE CASCADE,
            FOREIGN KEY(motivo_id) REFERENCES pre_conselho_motivos(id),
            UNIQUE(registro_id, motivo_id)
        )
        """
    )

    _adicionar_coluna_se_necessario(
        cursor, "pre_conselho_periodos", "nome", "TEXT NOT NULL DEFAULT ''"
    )
    _adicionar_coluna_se_necessario(
        cursor, "pre_conselho_periodos", "ano_letivo", "INTEGER NOT NULL DEFAULT 0"
    )
    _adicionar_coluna_se_necessario(
        cursor, "pre_conselho_periodos", "etapa", "INTEGER NOT NULL DEFAULT 0"
    )
    _adicionar_coluna_se_necessario(
        cursor, "pre_conselho_periodos", "data_inicio", "TEXT NOT NULL DEFAULT ''"
    )
    _adicionar_coluna_se_necessario(
        cursor, "pre_conselho_periodos", "data_fim", "TEXT NOT NULL DEFAULT ''"
    )
    _adicionar_coluna_se_necessario(
        cursor, "pre_conselho_periodos", "status", "TEXT NOT NULL DEFAULT 'FECHADO'"
    )
    _adicionar_coluna_se_necessario(
        cursor, "pre_conselho_periodos", "criado_em", "TEXT NOT NULL DEFAULT ''"
    )
    _adicionar_coluna_se_necessario(
        cursor, "pre_conselho_periodos", "atualizado_em", "TEXT NOT NULL DEFAULT ''"
    )

    _adicionar_coluna_se_necessario(
        cursor, "pre_conselho_motivos", "categoria", "TEXT NOT NULL DEFAULT ''"
    )
    _adicionar_coluna_se_necessario(
        cursor, "pre_conselho_motivos", "codigo", "TEXT NOT NULL DEFAULT ''"
    )
    _adicionar_coluna_se_necessario(
        cursor, "pre_conselho_motivos", "descricao", "TEXT NOT NULL DEFAULT ''"
    )
    _adicionar_coluna_se_necessario(
        cursor, "pre_conselho_motivos", "ativo", "INTEGER NOT NULL DEFAULT 1"
    )
    _adicionar_coluna_se_necessario(
        cursor, "pre_conselho_motivos", "ordem", "INTEGER NOT NULL DEFAULT 0"
    )
    _adicionar_coluna_se_necessario(
        cursor, "pre_conselho_motivos", "criado_em", "TEXT NOT NULL DEFAULT ''"
    )
    _adicionar_coluna_se_necessario(
        cursor, "pre_conselho_motivos", "atualizado_em", "TEXT NOT NULL DEFAULT ''"
    )

    _adicionar_coluna_se_necessario(cursor, "pre_conselho_registros", "periodo_id", "INTEGER")
    _adicionar_coluna_se_necessario(cursor, "pre_conselho_registros", "disciplina_id", "INTEGER")
    _adicionar_coluna_se_necessario(
        cursor, "pre_conselho_registros", "professor_usuario_id", "INTEGER NOT NULL DEFAULT 0"
    )
    _adicionar_coluna_se_necessario(
        cursor, "pre_conselho_registros", "turma_id", "INTEGER NOT NULL DEFAULT 0"
    )
    _adicionar_coluna_se_necessario(
        cursor, "pre_conselho_registros", "estudante_id", "INTEGER NOT NULL DEFAULT 0"
    )
    _adicionar_coluna_se_necessario(
        cursor, "pre_conselho_registros", "disciplina", "TEXT NOT NULL DEFAULT ''"
    )
    _adicionar_coluna_se_necessario(
        cursor, "pre_conselho_registros", "ano_letivo", "INTEGER NOT NULL DEFAULT 0"
    )
    _adicionar_coluna_se_necessario(
        cursor, "pre_conselho_registros", "bimestre", "INTEGER NOT NULL DEFAULT 0"
    )
    _adicionar_coluna_se_necessario(cursor, "pre_conselho_registros", "nivel_atencao", "TEXT")
    _adicionar_coluna_se_necessario(
        cursor, "pre_conselho_registros", "motivos", "TEXT NOT NULL DEFAULT '[]'"
    )
    _adicionar_coluna_se_necessario(
        cursor, "pre_conselho_registros", "observacoes", "TEXT NOT NULL DEFAULT ''"
    )
    _adicionar_coluna_se_necessario(
        cursor, "pre_conselho_registros", "observacao_professor", "TEXT NOT NULL DEFAULT ''"
    )
    _adicionar_coluna_se_necessario(
        cursor, "pre_conselho_registros", "texto_gerado", "TEXT NOT NULL DEFAULT ''"
    )
    _adicionar_coluna_se_necessario(
        cursor, "pre_conselho_registros", "criado_em", "TEXT NOT NULL DEFAULT ''"
    )
    _adicionar_coluna_se_necessario(
        cursor, "pre_conselho_registros", "atualizado_em", "TEXT NOT NULL DEFAULT ''"
    )

    _adicionar_coluna_se_necessario(
        cursor, "pre_conselho_registro_motivos", "registro_id", "INTEGER NOT NULL DEFAULT 0"
    )
    _adicionar_coluna_se_necessario(
        cursor, "pre_conselho_registro_motivos", "motivo_id", "INTEGER NOT NULL DEFAULT 0"
    )
    _adicionar_coluna_se_necessario(
        cursor, "pre_conselho_registro_motivos", "criado_em", "TEXT NOT NULL DEFAULT ''"
    )

    cursor.execute(
        """
        UPDATE pre_conselho_registros
        SET observacao_professor = COALESCE(observacoes, '')
        WHERE TRIM(COALESCE(observacao_professor, '')) = ''
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_pre_conselho_periodos_ano_etapa
        ON pre_conselho_periodos(ano_letivo, etapa, status)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_pre_conselho_motivos_categoria_ordem
        ON pre_conselho_motivos(categoria, ativo, ordem)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_pre_conselho_professor_periodo
        ON pre_conselho_registros(professor_usuario_id, periodo_id, turma_id, disciplina_id)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_pre_conselho_turma_disciplina
        ON pre_conselho_registros(periodo_id, turma_id, disciplina_id)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_pre_conselho_estudante
        ON pre_conselho_registros(estudante_id)
        """
    )
    cursor.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_pre_conselho_registro_unico
        ON pre_conselho_registros(periodo_id, turma_id, disciplina_id, professor_usuario_id, estudante_id)
        WHERE periodo_id IS NOT NULL AND disciplina_id IS NOT NULL
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_pre_conselho_registro_motivos_registro
        ON pre_conselho_registro_motivos(registro_id, motivo_id)
        """
    )

    _seed_periodos(cursor)
    _seed_motivos(cursor)
    _migrar_motivos_legados(cursor)

    conn.commit()


def downgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()

    cursor.execute("DROP INDEX IF EXISTS idx_pre_conselho_registro_motivos_registro")
    cursor.execute("DROP INDEX IF EXISTS idx_pre_conselho_registro_unico")
    cursor.execute("DROP INDEX IF EXISTS idx_pre_conselho_estudante")
    cursor.execute("DROP INDEX IF EXISTS idx_pre_conselho_turma_disciplina")
    cursor.execute("DROP INDEX IF EXISTS idx_pre_conselho_professor_periodo")
    cursor.execute("DROP INDEX IF EXISTS idx_pre_conselho_motivos_categoria_ordem")
    cursor.execute("DROP INDEX IF EXISTS idx_pre_conselho_periodos_ano_etapa")
    cursor.execute("DROP TABLE IF EXISTS pre_conselho_registro_motivos")
    cursor.execute("DROP TABLE IF EXISTS pre_conselho_motivos")
    cursor.execute("DROP TABLE IF EXISTS pre_conselho_periodos")
    conn.commit()


def main():
    parser = argparse.ArgumentParser(
        description="Migration: cria a estrutura robusta do modulo de pre-conselho"
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
