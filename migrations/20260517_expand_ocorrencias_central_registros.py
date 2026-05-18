#!/usr/bin/env python3
import argparse
import os
import sqlite3
from pathlib import Path


ACOES_APLICADAS = (
    "advertencia_verbal",
    "retirada_sala_orientacao",
    "suspensao_extracurricular",
    "suspensao_orientada_2_dias",
    "suspensao_aulas_3_dias",
    "transferencia_compulsoria",
    "orientacao_verbal",
    "advertencia",
    "chamada_responsavel",
    "encaminhamento_direcao",
    "registro_informativo",
    "orientacao_professor",
    "reuniao_alinhamento",
    "orientacao_geral_docentes",
)

ACOES_APLICADAS_LEGADAS = (
    "advertencia_verbal",
    "retirada_sala_orientacao",
    "suspensao_extracurricular",
    "suspensao_orientada_2_dias",
    "suspensao_aulas_3_dias",
    "transferencia_compulsoria",
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

TIPOS_REGISTRO = (
    "estudante",
    "professor",
    "geral",
)


def _default_db_path() -> str:
    env_path = os.getenv("DB_PATH", "").strip()
    if env_path:
        return env_path
    base_dir = Path(__file__).resolve().parents[1]
    return str(base_dir.parent / "sistema-impress-data" / "impressao.db")


def _listar_colunas(cursor, tabela: str) -> list[sqlite3.Row]:
    cursor.execute(f"PRAGMA table_info({tabela})")
    return list(cursor.fetchall())


def _obter_sql_tabela(cursor, tabela: str) -> str:
    cursor.execute(
        """
        SELECT sql
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (tabela,),
    )
    row = cursor.fetchone()
    return str(row["sql"] or "") if row and row["sql"] else ""


def _coluna_aceita_nulo(cursor, tabela: str, coluna: str) -> bool:
    for row in _listar_colunas(cursor, tabela):
        if str(row["name"]) == coluna:
            return not bool(row["notnull"])
    return False


def _expressao_coluna(colunas: set[str], nome: str, padrao_sql: str) -> str:
    return nome if nome in colunas else padrao_sql


def _recriar_tabela_ocorrencias(cursor) -> None:
    colunas = {str(row["name"]) for row in _listar_colunas(cursor, "ocorrencias")}

    tipo_expr = _expressao_coluna(colunas, "tipo_registro", "'estudante'")
    nome_expr = _expressao_coluna(colunas, "nome_estudante", "''")
    estudante_expr = _expressao_coluna(colunas, "estudante_id", "NULL")
    turma_expr = _expressao_coluna(colunas, "turma_id", "NULL")
    professor_nome_expr = _expressao_coluna(colunas, "professor_requerente", "''")
    professor_id_expr = _expressao_coluna(colunas, "professor_requerente_id", "NULL")
    disciplina_expr = _expressao_coluna(colunas, "disciplina", "''")
    data_expr = _expressao_coluna(colunas, "data_ocorrencia", "''")
    aula_expr = _expressao_coluna(colunas, "aula", "''")
    horario_expr = _expressao_coluna(colunas, "horario_ocorrencia", "''")
    descricao_expr = _expressao_coluna(colunas, "descricao", "''")
    acao_expr = _expressao_coluna(colunas, "acao_aplicada", "'registro_informativo'")
    status_expr = _expressao_coluna(colunas, "status", "'registrado'")
    criado_em_expr = _expressao_coluna(colunas, "criado_em", "datetime('now')")
    atualizado_em_expr = _expressao_coluna(colunas, "atualizado_em", "datetime('now')")

    cursor.execute("PRAGMA foreign_keys = OFF")
    cursor.execute("DROP TABLE IF EXISTS ocorrencias__tmp")
    cursor.execute(f"""
        CREATE TABLE ocorrencias__tmp (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo_registro TEXT NOT NULL DEFAULT 'estudante' CHECK (tipo_registro IN {TIPOS_REGISTRO}),
            nome_estudante TEXT NOT NULL,
            estudante_id INTEGER,
            turma_id INTEGER,
            professor_requerente TEXT NOT NULL,
            professor_requerente_id INTEGER,
            disciplina TEXT NOT NULL,
            data_ocorrencia TEXT NOT NULL,
            aula TEXT NOT NULL,
            horario_ocorrencia TEXT NOT NULL,
            descricao TEXT NOT NULL,
            acao_aplicada TEXT NOT NULL CHECK (acao_aplicada IN {ACOES_APLICADAS}),
            status TEXT NOT NULL DEFAULT 'registrado' CHECK (status IN {STATUS_OCORRENCIA}),
            criado_em TEXT NOT NULL DEFAULT (datetime('now')),
            atualizado_em TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(estudante_id) REFERENCES estudantes(id),
            FOREIGN KEY(turma_id) REFERENCES turmas(id),
            FOREIGN KEY(professor_requerente_id) REFERENCES usuarios(id)
        )
    """)
    cursor.execute(
        f"""
        INSERT INTO ocorrencias__tmp (
            id,
            tipo_registro,
            nome_estudante,
            estudante_id,
            turma_id,
            professor_requerente,
            professor_requerente_id,
            disciplina,
            data_ocorrencia,
            aula,
            horario_ocorrencia,
            descricao,
            acao_aplicada,
            status,
            criado_em,
            atualizado_em
        )
        SELECT
            id,
            CASE
                WHEN TRIM(COALESCE({tipo_expr}, '')) IN {TIPOS_REGISTRO}
                    THEN TRIM({tipo_expr})
                ELSE 'estudante'
            END AS tipo_registro,
            TRIM(COALESCE({nome_expr}, '')) AS nome_estudante,
            {estudante_expr} AS estudante_id,
            CASE
                WHEN (
                    CASE
                        WHEN TRIM(COALESCE({tipo_expr}, '')) IN {TIPOS_REGISTRO}
                            THEN TRIM({tipo_expr})
                        ELSE 'estudante'
                    END
                ) = 'estudante' THEN {turma_expr}
                ELSE NULL
            END AS turma_id,
            CASE
                WHEN (
                    CASE
                        WHEN TRIM(COALESCE({tipo_expr}, '')) IN {TIPOS_REGISTRO}
                            THEN TRIM({tipo_expr})
                        ELSE 'estudante'
                    END
                ) = 'geral'
                AND TRIM(COALESCE({professor_nome_expr}, '')) = ''
                    THEN 'Todos os professores'
                ELSE TRIM(COALESCE({professor_nome_expr}, ''))
            END AS professor_requerente,
            {professor_id_expr} AS professor_requerente_id,
            TRIM(COALESCE({disciplina_expr}, '')) AS disciplina,
            TRIM(COALESCE({data_expr}, '')) AS data_ocorrencia,
            CASE
                WHEN (
                    CASE
                        WHEN TRIM(COALESCE({tipo_expr}, '')) IN {TIPOS_REGISTRO}
                            THEN TRIM({tipo_expr})
                        ELSE 'estudante'
                    END
                ) = 'estudante' THEN TRIM(COALESCE({aula_expr}, ''))
                ELSE ''
            END AS aula,
            TRIM(COALESCE({horario_expr}, '')) AS horario_ocorrencia,
            TRIM(COALESCE({descricao_expr}, '')) AS descricao,
            CASE
                WHEN TRIM(COALESCE({acao_expr}, '')) IN {ACOES_APLICADAS}
                    THEN TRIM({acao_expr})
                ELSE 'registro_informativo'
            END AS acao_aplicada,
            CASE
                WHEN TRIM(COALESCE({status_expr}, '')) IN {STATUS_OCORRENCIA}
                    THEN TRIM({status_expr})
                ELSE 'registrado'
            END AS status,
            COALESCE({criado_em_expr}, datetime('now')) AS criado_em,
            COALESCE({atualizado_em_expr}, COALESCE({criado_em_expr}, datetime('now'))) AS atualizado_em
        FROM ocorrencias
        """
    )
    cursor.execute("DROP TABLE ocorrencias")
    cursor.execute("ALTER TABLE ocorrencias__tmp RENAME TO ocorrencias")
    cursor.execute("PRAGMA foreign_keys = ON")


def upgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = 'ocorrencias'
        """
    )
    if not cursor.fetchone():
        cursor.execute(f"""
            CREATE TABLE ocorrencias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo_registro TEXT NOT NULL DEFAULT 'estudante' CHECK (tipo_registro IN {TIPOS_REGISTRO}),
                nome_estudante TEXT NOT NULL,
                estudante_id INTEGER,
                turma_id INTEGER,
                professor_requerente TEXT NOT NULL,
                professor_requerente_id INTEGER,
                disciplina TEXT NOT NULL,
                data_ocorrencia TEXT NOT NULL,
                aula TEXT NOT NULL,
                horario_ocorrencia TEXT NOT NULL,
                descricao TEXT NOT NULL,
                acao_aplicada TEXT NOT NULL CHECK (acao_aplicada IN {ACOES_APLICADAS}),
                status TEXT NOT NULL DEFAULT 'registrado' CHECK (status IN {STATUS_OCORRENCIA}),
                criado_em TEXT NOT NULL DEFAULT (datetime('now')),
                atualizado_em TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY(estudante_id) REFERENCES estudantes(id),
                FOREIGN KEY(turma_id) REFERENCES turmas(id),
                FOREIGN KEY(professor_requerente_id) REFERENCES usuarios(id)
            )
        """)
    else:
        sql_tabela = _obter_sql_tabela(cursor, "ocorrencias").upper()
        precisa_recriar = not (
            "TIPO_REGISTRO" in sql_tabela
            and "ORIENTACAO_PROFESSOR" in sql_tabela
            and "REUNIAO_ALINHAMENTO" in sql_tabela
            and "ORIENTACAO_GERAL_DOCENTES" in sql_tabela
            and _coluna_aceita_nulo(cursor, "ocorrencias", "turma_id")
        )
        if precisa_recriar:
            _recriar_tabela_ocorrencias(cursor)

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_ocorrencias_tipo_registro
        ON ocorrencias(tipo_registro)
        """
    )
    conn.commit()


def downgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("DROP INDEX IF EXISTS idx_ocorrencias_tipo_registro")

    sql_tabela = _obter_sql_tabela(cursor, "ocorrencias").upper()
    if "TIPO_REGISTRO" not in sql_tabela:
        conn.commit()
        return

    cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM ocorrencias
        WHERE TRIM(COALESCE(tipo_registro, 'estudante')) <> 'estudante'
        """
    )
    if int(cursor.fetchone()["total"] or 0) > 0:
        raise RuntimeError(
            "Nao e possivel fazer downgrade com registros de professor ou gerais cadastrados."
        )

    cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM ocorrencias
        WHERE turma_id IS NULL
        """
    )
    if int(cursor.fetchone()["total"] or 0) > 0:
        raise RuntimeError(
            "Nao e possivel fazer downgrade com registros sem turma vinculada."
        )

    cursor.execute("PRAGMA foreign_keys = OFF")
    cursor.execute("DROP TABLE IF EXISTS ocorrencias__tmp")
    cursor.execute(f"""
        CREATE TABLE ocorrencias__tmp (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_estudante TEXT NOT NULL,
            turma_id INTEGER NOT NULL,
            professor_requerente TEXT NOT NULL,
            disciplina TEXT NOT NULL,
            data_ocorrencia TEXT NOT NULL,
            aula TEXT NOT NULL,
            horario_ocorrencia TEXT NOT NULL,
            descricao TEXT NOT NULL,
            acao_aplicada TEXT NOT NULL CHECK (acao_aplicada IN {ACOES_APLICADAS_LEGADAS}),
            status TEXT NOT NULL DEFAULT 'registrado' CHECK (status IN {STATUS_OCORRENCIA}),
            criado_em TEXT NOT NULL DEFAULT (datetime('now')),
            atualizado_em TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(turma_id) REFERENCES turmas(id)
        )
    """)
    cursor.execute(
        f"""
        INSERT INTO ocorrencias__tmp (
            id,
            nome_estudante,
            turma_id,
            professor_requerente,
            disciplina,
            data_ocorrencia,
            aula,
            horario_ocorrencia,
            descricao,
            acao_aplicada,
            status,
            criado_em,
            atualizado_em
        )
        SELECT
            id,
            nome_estudante,
            turma_id,
            professor_requerente,
            disciplina,
            data_ocorrencia,
            aula,
            horario_ocorrencia,
            descricao,
            CASE
                WHEN TRIM(COALESCE(acao_aplicada, '')) IN {ACOES_APLICADAS_LEGADAS}
                    THEN TRIM(acao_aplicada)
                ELSE 'registro_informativo'
            END AS acao_aplicada,
            status,
            criado_em,
            atualizado_em
        FROM ocorrencias
        """
    )
    cursor.execute("DROP TABLE ocorrencias")
    cursor.execute("ALTER TABLE ocorrencias__tmp RENAME TO ocorrencias")
    cursor.execute("PRAGMA foreign_keys = ON")
    conn.commit()


def main():
    parser = argparse.ArgumentParser(
        description="Migration: expande ocorrencias para a central de registros da coordenacao"
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
