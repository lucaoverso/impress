import sqlite3
import uuid
import hashlib
import json
import os
import shutil
import unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path
from db.schema_migrations import apply_pending_migrations
from security.nt_hash import generate_nt_hash
from services.ocorrencia_disciplina_service import ACAO_OCORRENCIA_VALIDAS
from services.preconselho_service import (
    STATUS_PERIODO_PRE_CONSELHO_ABERTO,
    catalogo_motivos_iniciais_pre_conselho,
    descrever_motivos_pos_pre_conselho,
    nome_periodo_pre_conselho,
    normalizar_status_pos_pre_conselho,
    periodos_padrao_pre_conselho,
)

STATUS_CONCLUIDO = "CONCLUIDO"
STATUS_FINALIZADO_LEGADO = "FINALIZADO"
STATUS_AGENDAMENTO_ATIVO = "ATIVO"
STATUS_AGENDAMENTO_CANCELADO = "CANCELADO"
STATUS_OCORRENCIA_REGISTRADO = "registrado"
STATUS_OCORRENCIA_EM_ACOMPANHAMENTO = "em_acompanhamento"
STATUS_OCORRENCIA_AGUARDANDO_RESPONSAVEL = "aguardando_responsavel"
STATUS_OCORRENCIA_RESOLVIDO = "resolvido"
STATUS_OCORRENCIA_VALIDOS = (
    STATUS_OCORRENCIA_REGISTRADO,
    STATUS_OCORRENCIA_EM_ACOMPANHAMENTO,
    STATUS_OCORRENCIA_AGUARDANDO_RESPONSAVEL,
    STATUS_OCORRENCIA_RESOLVIDO,
)
TIPO_REGISTRO_OCORRENCIA_ESTUDANTE = "estudante"
TIPO_REGISTRO_OCORRENCIA_PROFESSOR = "professor"
TIPO_REGISTRO_OCORRENCIA_GERAL = "geral"
TIPOS_REGISTRO_OCORRENCIA = (
    TIPO_REGISTRO_OCORRENCIA_ESTUDANTE,
    TIPO_REGISTRO_OCORRENCIA_PROFESSOR,
    TIPO_REGISTRO_OCORRENCIA_GERAL,
)
TIPO_BASE_LEGAL_ARTIGO = "artigo"
TIPO_BASE_LEGAL_INCISO = "inciso"
TIPO_BASE_LEGAL_ALINEA = "alinea"
BASE_LEGAL_ITEM_INCISO_OFFSET = 1_000_000_000
BASE_LEGAL_ITEM_ALINEA_OFFSET = 2_000_000_000
LEI_PADRAO_IMPORTACAO = "Base legal"
LEI_PADRAO_MIGRACAO = "Base legal migrada"
CARGO_ADMIN = "ADMIN"
CARGO_PROFESSOR = "PROFESSOR"
CARGO_COORDENADOR = "COORDENADOR"
COTA_BASE_PADRAO = 80
COTA_POR_AULA_PADRAO = 6
COTA_POR_TURMA_PADRAO = 12
COTA_MENSAL_ESCOLA_PADRAO = 4000
RESERVA_INSTITUCIONAL_PERCENTUAL = 10
RELATORIOS_CAPACIDADE_AULAS_DIA = 5
RELATORIOS_CAPACIDADE_AULAS_DIA_SALA_TECNOLOGIA = 10
RELATORIOS_INSIGHT_PAGINAS_ELEVADAS_MIN = 150
RELATORIOS_INSIGHT_PAGINAS_ELEVADAS_POR_DIA_UTIL = 10
RELATORIOS_INSIGHT_CONCENTRACAO_IMPRESSAO_PERCENTUAL = 50.0
RELATORIOS_INSIGHT_OCUPACAO_ALTA_PERCENTUAL = 60.0
RELATORIOS_INSIGHT_BAIXO_USO_PERCENTUAL = 10.0
DISCIPLINAS_MULTIPLICADOR_ALTO = {
    "lingua portuguesa",
    "portugues",
    "literatura",
    "leitura e producao textual",
}
DISCIPLINAS_MULTIPLICADOR_BAIXO = {
    "educacao fisica",
    "apoio e orientacao de estudos",
    "estudo orientado",
}
TOKEN_TTL_DIAS_PADRAO = 7
TURMAS_PADRAO = [
    "6º ano A",
    "6º ano B",
    "7º ano A",
    "7º ano B",
    "8º ano A",
    "8º ano B",
    "9º ano A",
    "9º ano B",
    "1 E.M A",
    "1 E.M B",
    "2 E.M A",
    "2 E.M B",
    "3 E.M A",
    "3 E.M B",
]
DISCIPLINAS_PADRAO = [
    "Português",
    "Matemática",
    "Ciências",
    "História",
    "Geografia",
    "Inglês",
    "Artes",
    "Educação Física",
    "Física",
    "Química",
    "Biologia",
    "Filosofia",
    "Sociologia",
]


def _normalizar_booleano_sql(valor) -> int:
    return 1 if bool(valor) else 0

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR_PADRAO = BASE_DIR.parent / "sistema-impress-data"
DB_PATH_PADRAO = DATA_DIR_PADRAO / "impressao.db"
DB_PATH_LEGADO = BASE_DIR / "impressao.db"

_db_path_env = os.getenv("DB_PATH", "").strip()
if _db_path_env:
    DB_PATH = Path(_db_path_env).expanduser()
    if not DB_PATH.is_absolute():
        DB_PATH = (BASE_DIR / DB_PATH).resolve()
else:
    DB_PATH = DB_PATH_PADRAO

_BANCO_PREPARADO = False


def _resolver_ttl_token_dias() -> int:
    valor_bruto = os.getenv("TOKEN_TTL_DIAS", str(TOKEN_TTL_DIAS_PADRAO)).strip()
    try:
        valor = int(valor_bruto)
    except ValueError:
        return TOKEN_TTL_DIAS_PADRAO
    return valor if valor in (7, 15) else TOKEN_TTL_DIAS_PADRAO


TOKEN_TTL_DIAS = _resolver_ttl_token_dias()


def _garantir_banco_preparado():
    global _BANCO_PREPARADO
    if _BANCO_PREPARADO:
        return

    try:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise RuntimeError(
            f"Não foi possível criar diretório do banco em {DB_PATH.parent}."
        ) from exc

    # Migração automática do banco legado na raiz do projeto para o novo caminho.
    if DB_PATH != DB_PATH_LEGADO and not DB_PATH.exists() and DB_PATH_LEGADO.exists():
        try:
            shutil.copy2(DB_PATH_LEGADO, DB_PATH)
        except OSError as exc:
            raise RuntimeError(
                "Falha ao migrar banco legado para o novo diretório de dados."
            ) from exc

    _BANCO_PREPARADO = True


def get_connection():
    _garantir_banco_preparado()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def criar_job(
    usuario_id: int,
    arquivo: str,
    arquivo_path: str,
    copias: int,
    paginas_totais: int,
    paginas_por_folha: int = 1,
    duplex: bool = False,
    orientacao: str = "retrato",
    intervalo_paginas: str = "",
    printer_name: str = "",
    cups_options: str = "{}",
    tags_json: str = "[]",
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO jobs (
            usuario_id, arquivo, arquivo_path, copias, paginas_por_folha, duplex, orientacao,
            intervalo_paginas, cups_options, printer_name, paginas_totais, tags_json, status, prioridade, criado_em
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDENTE', 0, datetime('now'))
    """,
        (
            usuario_id,
            arquivo,
            arquivo_path,
            copias,
            paginas_por_folha,
            int(bool(duplex)),
            orientacao,
            intervalo_paginas,
            cups_options,
            printer_name or None,
            paginas_totais,
            tags_json or "[]",
        ),
    )

    job_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return job_id


def listar_jobs_ativos():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT * FROM jobs
        WHERE status NOT IN (?, ?)
        ORDER BY criado_em DESC
    """,
        (STATUS_CONCLUIDO, STATUS_FINALIZADO_LEGADO),
    )

    rows = cursor.fetchall()
    conn.close()

    return [dict(r) for r in rows]


def listar_historico(data_inicio=None, data_fim=None, usuario_id=None):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT
            j.*,
            COALESCE(u.nome, '') AS usuario_nome
        FROM jobs j
        LEFT JOIN usuarios u ON u.id = j.usuario_id
        WHERE status IN (?, ?)
    """

    params = [STATUS_CONCLUIDO, STATUS_FINALIZADO_LEGADO]

    if data_inicio:
        query += " AND j.criado_em >= ?"
        params.append(data_inicio)

    if data_fim:
        query += " AND j.criado_em <= ?"
        params.append(data_fim)

    if usuario_id:
        query += " AND j.usuario_id = ?"
        params.append(usuario_id)

    query += " ORDER BY j.criado_em DESC"

    cursor.execute(query, params)

    rows = cursor.fetchall()
    conn.close()

    return [dict(r) for r in rows]


def listar_arquivo_paths_jobs_em_andamento():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT arquivo_path
        FROM jobs
        WHERE status IN ('PENDENTE', 'IMPRIMINDO')
          AND TRIM(COALESCE(arquivo_path, '')) <> ''
    """
    )

    rows = cursor.fetchall()
    conn.close()

    return [str(row["arquivo_path"]).strip() for row in rows if str(row["arquivo_path"] or "").strip()]


def normalizar_jobs_impressao_pendentes(
    *,
    tolerancia_futuro_segundos: int = 300,
) -> dict[str, int]:
    try:
        tolerancia = max(int(tolerancia_futuro_segundos), 0)
    except (TypeError, ValueError):
        tolerancia = 300

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE jobs
        SET status = 'PENDENTE'
        WHERE status = 'PROCESSANDO'
          AND finalizado_em IS NULL
    """
    )
    processando_normalizados = int(cursor.rowcount or 0)

    cursor.execute(
        """
        UPDATE jobs
        SET criado_em = datetime('now')
        WHERE status = 'PENDENTE'
          AND datetime(criado_em) > datetime('now', ?)
    """,
        (f"+{tolerancia} seconds",),
    )
    datas_normalizadas = int(cursor.rowcount or 0)

    conn.commit()
    conn.close()
    return {
        "processando_normalizados": processando_normalizados,
        "datas_normalizadas": datas_normalizadas,
    }


def listar_jobs_por_usuario(usuario_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT * FROM jobs
        WHERE usuario_id = ?
        ORDER BY criado_em DESC
    """,
        (usuario_id,),
    )

    rows = cursor.fetchall()
    conn.close()

    return [dict(r) for r in rows]


def criar_tabelas():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            senha_hash TEXT NOT NULL,
            nt_hash CHAR(32),
            perfil TEXT NOT NULL,
            cargo TEXT NOT NULL DEFAULT 'PROFESSOR',
            acesso_coordenacao INTEGER NOT NULL DEFAULT 0,
            data_nascimento TEXT,
            ativo INTEGER NOT NULL DEFAULT 1
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tokens (
            token TEXT PRIMARY KEY,
            usuario_id INTEGER NOT NULL,
            criado_em TEXT NOT NULL DEFAULT '',
            expira_em TEXT NOT NULL DEFAULT ''
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            arquivo TEXT NOT NULL,
            arquivo_path TEXT,
            copias INTEGER NOT NULL,
            paginas_por_folha INTEGER NOT NULL DEFAULT 1,
            duplex INTEGER NOT NULL DEFAULT 0,
            orientacao TEXT NOT NULL DEFAULT 'retrato',
            intervalo_paginas TEXT NOT NULL DEFAULT '',
            cups_options TEXT NOT NULL DEFAULT '{}',
            printer_name TEXT,
            cups_job_id INTEGER,
            erro_mensagem TEXT,
            paginas_totais INTEGER NOT NULL DEFAULT 0,
            tags_json TEXT NOT NULL DEFAULT '[]',
            status TEXT NOT NULL,
            prioridade INTEGER NOT NULL,
            criado_em TEXT NOT NULL,
            finalizado_em TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cotas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            mes TEXT NOT NULL,
            limite_paginas INTEGER NOT NULL,
            usadas_paginas INTEGER NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS professores_carga (
            usuario_id INTEGER PRIMARY KEY,
            aulas_semanais INTEGER NOT NULL DEFAULT 0,
            turmas_quantidade INTEGER NOT NULL DEFAULT 0,
            turmas TEXT NOT NULL DEFAULT '[]',
            disciplinas TEXT NOT NULL DEFAULT '[]',
            atualizado_em TEXT NOT NULL,
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS professores_turmas_disciplinas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            professor_usuario_id INTEGER NOT NULL,
            turma_id INTEGER NOT NULL,
            disciplina_id INTEGER NOT NULL,
            criado_em TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(professor_usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY(turma_id) REFERENCES turmas(id),
            FOREIGN KEY(disciplina_id) REFERENCES disciplinas(id),
            UNIQUE(professor_usuario_id, turma_id, disciplina_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cota_regras (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            base_paginas INTEGER NOT NULL,
            paginas_por_aula INTEGER NOT NULL,
            paginas_por_turma INTEGER NOT NULL,
            cota_mensal_escola INTEGER NOT NULL DEFAULT 4000,
            atualizado_em TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS impressao_status (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            sem_papel INTEGER NOT NULL DEFAULT 0,
            mensagem TEXT NOT NULL DEFAULT '',
            atualizado_em TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recursos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL,
            tipo TEXT NOT NULL,
            descricao TEXT,
            quantidade_itens INTEGER NOT NULL DEFAULT 1,
            ativo INTEGER NOT NULL DEFAULT 1
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS turmas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL,
            turno TEXT NOT NULL DEFAULT '',
            quantidade_estudantes INTEGER NOT NULL DEFAULT 0,
            ativo INTEGER NOT NULL DEFAULT 1,
            criado_em TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS disciplinas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL,
            aulas_semanais INTEGER NOT NULL DEFAULT 0,
            tem_apc INTEGER NOT NULL DEFAULT 0,
            tem_prova_bimestral INTEGER NOT NULL DEFAULT 0,
            ativo INTEGER NOT NULL DEFAULT 1,
            criado_em TEXT NOT NULL
        )
    """)

    cursor.execute("""
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
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS estudantes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            turma_id INTEGER NOT NULL,
            ativo INTEGER NOT NULL DEFAULT 1,
            criado_em TEXT NOT NULL DEFAULT (datetime('now')),
            atualizado_em TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(turma_id) REFERENCES turmas(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agendamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recurso_id INTEGER NOT NULL,
            usuario_id INTEGER NOT NULL,
            data TEXT NOT NULL,
            turno TEXT NOT NULL DEFAULT 'MATUTINO',
            aula TEXT NOT NULL,
            faixa_global INTEGER NOT NULL DEFAULT 0,
            turma TEXT NOT NULL DEFAULT '',
            tema_aula TEXT NOT NULL DEFAULT '',
            observacao TEXT,
            status TEXT NOT NULL DEFAULT 'ATIVO',
            criado_em TEXT NOT NULL,
            cancelado_em TEXT,
            FOREIGN KEY(recurso_id) REFERENCES recursos(id),
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pcpi_registros_manuais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL,
            turno TEXT NOT NULL,
            tipo_acao TEXT NOT NULL,
            origem TEXT NOT NULL DEFAULT 'MANUAL',
            agendamento_id INTEGER,
            acao_realizada TEXT,
            professor_nome TEXT,
            componente TEXT,
            turma TEXT,
            descricao_curta TEXT NOT NULL,
            resultado TEXT,
            observacoes TEXT,
            criado_por_usuario_id INTEGER,
            atualizado_por_usuario_id INTEGER,
            criado_em TEXT NOT NULL DEFAULT (datetime('now')),
            atualizado_em TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(agendamento_id) REFERENCES agendamentos(id),
            FOREIGN KEY(criado_por_usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY(atualizado_por_usuario_id) REFERENCES usuarios(id)
        )
    """)

    cursor.execute("""
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
    """)

    cursor.execute("""
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
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pre_conselho_registros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            periodo_id INTEGER,
            disciplina_id INTEGER,
            professor_usuario_id INTEGER NOT NULL,
            turma_id INTEGER NOT NULL,
            estudante_id INTEGER NOT NULL,
            nivel_atencao TEXT,
            disciplina TEXT NOT NULL DEFAULT '',
            ano_letivo INTEGER NOT NULL DEFAULT 0,
            bimestre INTEGER NOT NULL DEFAULT 0,
            motivos TEXT NOT NULL DEFAULT '[]',
            observacoes TEXT NOT NULL DEFAULT '',
            observacao_professor TEXT NOT NULL DEFAULT '',
            pos_preconselho_recuperado INTEGER,
            pos_preconselho_motivos TEXT NOT NULL DEFAULT '[]',
            pos_preconselho_observacao TEXT NOT NULL DEFAULT '',
            texto_gerado TEXT NOT NULL DEFAULT '',
            criado_em TEXT NOT NULL DEFAULT (datetime('now')),
            atualizado_em TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(periodo_id) REFERENCES pre_conselho_periodos(id),
            FOREIGN KEY(disciplina_id) REFERENCES disciplinas(id),
            FOREIGN KEY(professor_usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY(turma_id) REFERENCES turmas(id),
            FOREIGN KEY(estudante_id) REFERENCES estudantes(id),
            UNIQUE(professor_usuario_id, estudante_id, disciplina, ano_letivo, bimestre)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pre_conselho_registro_motivos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            registro_id INTEGER NOT NULL,
            motivo_id INTEGER NOT NULL,
            criado_em TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(registro_id) REFERENCES pre_conselho_registros(id) ON DELETE CASCADE,
            FOREIGN KEY(motivo_id) REFERENCES pre_conselho_motivos(id),
            UNIQUE(registro_id, motivo_id)
        )
    """)

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS ocorrencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo_registro TEXT NOT NULL DEFAULT '{TIPO_REGISTRO_OCORRENCIA_ESTUDANTE}' CHECK (tipo_registro IN {TIPOS_REGISTRO_OCORRENCIA}),
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
            acao_aplicada TEXT NOT NULL CHECK (acao_aplicada IN {ACAO_OCORRENCIA_VALIDAS}),
            status TEXT NOT NULL DEFAULT '{STATUS_OCORRENCIA_REGISTRADO}' CHECK (status IN {STATUS_OCORRENCIA_VALIDOS}),
            criado_em TEXT NOT NULL DEFAULT (datetime('now')),
            atualizado_em TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(estudante_id) REFERENCES estudantes(id),
            FOREIGN KEY(turma_id) REFERENCES turmas(id),
            FOREIGN KEY(professor_requerente_id) REFERENCES usuarios(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS artigos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lei_id INTEGER NOT NULL,
            numero TEXT NOT NULL,
            descricao TEXT NOT NULL,
            FOREIGN KEY(lei_id) REFERENCES leis(id),
            UNIQUE(lei_id, numero)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incisos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            artigo_id INTEGER NOT NULL,
            numero TEXT NOT NULL,
            descricao TEXT NOT NULL,
            FOREIGN KEY(artigo_id) REFERENCES artigos(id),
            UNIQUE(artigo_id, numero)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alineas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inciso_id INTEGER NOT NULL,
            identificador TEXT NOT NULL,
            descricao TEXT NOT NULL,
            FOREIGN KEY(inciso_id) REFERENCES incisos(id),
            UNIQUE(inciso_id, identificador)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ocorrencia_regimento_itens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ocorrencia_id INTEGER NOT NULL,
            regimento_item_id INTEGER,
            artigo_id INTEGER,
            inciso_id INTEGER,
            alinea_id INTEGER,
            lei_nome TEXT,
            artigo_numero TEXT,
            artigo_descricao TEXT,
            inciso_numero TEXT,
            inciso_descricao TEXT,
            alinea_identificador TEXT,
            alinea_descricao TEXT,
            artigo TEXT NOT NULL,
            descricao TEXT NOT NULL,
            ordem INTEGER NOT NULL DEFAULT 0,
            criado_em TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(ocorrencia_id) REFERENCES ocorrencias(id),
            FOREIGN KEY(artigo_id) REFERENCES artigos(id),
            FOREIGN KEY(inciso_id) REFERENCES incisos(id),
            FOREIGN KEY(alinea_id) REFERENCES alineas(id)
        )
    """)

    _aplicar_migracoes_versionadas(conn)
    _aplicar_compatibilidade_schema_legada(cursor)
    _criar_indices_schema(cursor)
    _aplicar_seeds_iniciais(cursor)

    conn.commit()
    conn.close()


def _aplicar_migracoes_versionadas(conn):
    apply_pending_migrations(conn)


def _aplicar_compatibilidade_schema_legada(cursor):
    # Backstop temporário enquanto migramos totalmente a evolução de schema
    # para arquivos versionados em `migrations/`.
    _garantir_colunas_usuarios(cursor)
    _garantir_colunas_tokens(cursor)
    _garantir_colunas_jobs(cursor)
    _garantir_colunas_agendamentos(cursor)
    _garantir_colunas_pcpi_registros_manuais(cursor)
    _garantir_colunas_professores_carga(cursor)
    _garantir_colunas_professores_turmas_disciplinas(cursor)
    _garantir_colunas_cota_regras(cursor)
    _garantir_colunas_recursos(cursor)
    _garantir_colunas_turmas(cursor)
    _garantir_colunas_disciplinas(cursor)
    _garantir_colunas_turmas_disciplinas(cursor)
    _garantir_colunas_estudantes(cursor)
    _garantir_colunas_pre_conselho_periodos(cursor)
    _garantir_colunas_pre_conselho_motivos(cursor)
    _garantir_colunas_pre_conselho_registros(cursor)
    _garantir_colunas_pre_conselho_registro_motivos(cursor)
    _garantir_colunas_ocorrencias(cursor)
    _garantir_tabelas_ocorrencia_vinculados(cursor)
    _garantir_colunas_ocorrencia_regimento_itens(cursor)
    _migrar_base_legal_legado(cursor)
    _garantir_view_radcheck(cursor)
    _migrar_catalogos_academicos(cursor)
    _migrar_turmas_disciplinas_legado(cursor)
    _migrar_registros_pre_conselho_legado(cursor)


def _criar_indices_schema(cursor):
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_jobs_status_prioridade_criado_em
        ON jobs(status, prioridade, criado_em)
    """)

    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_cotas_usuario_mes
        ON cotas(usuario_id, mes)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_professores_turmas_disciplinas_professor
        ON professores_turmas_disciplinas(professor_usuario_id, turma_id, disciplina_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_professores_turmas_disciplinas_turma
        ON professores_turmas_disciplinas(turma_id, disciplina_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_turmas_disciplinas_turma
        ON turmas_disciplinas(turma_id, disciplina_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_turmas_disciplinas_professor
        ON turmas_disciplinas(professor_usuario_id, disciplina_id, turma_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_tokens_usuario_id
        ON tokens(usuario_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_tokens_expira_em
        ON tokens(expira_em)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS ix_usuarios_nt_hash
        ON usuarios(nt_hash)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_agendamentos_data_recurso_aula_status
        ON agendamentos(data, recurso_id, aula, status)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_agendamentos_data_recurso_turno_aula_status
        ON agendamentos(data, recurso_id, turno, aula, status)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_agendamentos_data_recurso_faixa_status
        ON agendamentos(data, recurso_id, faixa_global, status)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_agendamentos_usuario_data
        ON agendamentos(usuario_id, data)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_pcpi_registros_manuais_data_turno
        ON pcpi_registros_manuais(data, turno)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_pcpi_registros_manuais_agendamento
        ON pcpi_registros_manuais(agendamento_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_pcpi_registros_manuais_tipo_acao
        ON pcpi_registros_manuais(tipo_acao)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_pcpi_registros_manuais_criado_por
        ON pcpi_registros_manuais(criado_por_usuario_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_pre_conselho_periodos_ano_etapa
        ON pre_conselho_periodos(ano_letivo, etapa, status)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_pre_conselho_motivos_categoria_ordem
        ON pre_conselho_motivos(categoria, ativo, ordem)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_pre_conselho_professor_periodo
        ON pre_conselho_registros(professor_usuario_id, periodo_id, turma_id, disciplina_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_pre_conselho_turma_disciplina
        ON pre_conselho_registros(periodo_id, turma_id, disciplina_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_pre_conselho_estudante
        ON pre_conselho_registros(estudante_id)
    """)

    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_pre_conselho_registro_unico
        ON pre_conselho_registros(periodo_id, turma_id, disciplina_id, professor_usuario_id, estudante_id)
        WHERE periodo_id IS NOT NULL AND disciplina_id IS NOT NULL
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_pre_conselho_registro_motivos_registro
        ON pre_conselho_registro_motivos(registro_id, motivo_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ocorrencias_status
        ON ocorrencias(status)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ocorrencias_tipo_registro
        ON ocorrencias(tipo_registro)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ocorrencias_turma_id
        ON ocorrencias(turma_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ocorrencias_estudante_id
        ON ocorrencias(estudante_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ocorrencias_professor_requerente_id
        ON ocorrencias(professor_requerente_id)
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

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_leis_nome
        ON leis(nome)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_artigos_lei_id
        ON artigos(lei_id, id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_incisos_artigo_id
        ON incisos(artigo_id, id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_alineas_inciso_id
        ON alineas(inciso_id, id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ocorrencia_regimento_ocorrencia
        ON ocorrencia_regimento_itens(ocorrencia_id, ordem)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ocorrencia_regimento_item
        ON ocorrencia_regimento_itens(regimento_item_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ocorrencia_regimento_artigo_id
        ON ocorrencia_regimento_itens(artigo_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ocorrencia_regimento_inciso_id
        ON ocorrencia_regimento_itens(inciso_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ocorrencia_regimento_alinea_id
        ON ocorrencia_regimento_itens(alinea_id)
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

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_estudantes_nome
        ON estudantes(nome)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_estudantes_turma_id
        ON estudantes(turma_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_estudantes_ativo
        ON estudantes(ativo)
    """)


def _aplicar_seeds_iniciais(cursor):
    _seed_catalogos_academicos(cursor)
    _seed_pre_conselho_periodos(cursor)
    _seed_pre_conselho_motivos(cursor)

    cursor.execute(
        """
        INSERT OR IGNORE INTO cota_regras (
            id, base_paginas, paginas_por_aula, paginas_por_turma, cota_mensal_escola, atualizado_em
        )
        VALUES (1, ?, ?, ?, ?, datetime('now'))
    """,
        (
            COTA_BASE_PADRAO,
            COTA_POR_AULA_PADRAO,
            COTA_POR_TURMA_PADRAO,
            COTA_MENSAL_ESCOLA_PADRAO,
        ),
    )

    cursor.execute(
        """
        INSERT OR IGNORE INTO impressao_status (
            id, sem_papel, mensagem, atualizado_em
        )
        VALUES (1, 0, '', datetime('now'))
        """
    )


def _normalizar_nome_catalogo(nome: str) -> str:
    return str(nome or "").strip()


def _cargo_padrao_por_perfil(perfil: str) -> str:
    perfil_limpo = str(perfil or "").strip().lower()
    if perfil_limpo == "admin":
        return CARGO_ADMIN
    if perfil_limpo == "coordenador":
        return CARGO_COORDENADOR
    return CARGO_PROFESSOR


def _seed_catalogos_academicos(cursor):
    cursor.executemany(
        """
        INSERT OR IGNORE INTO turmas (nome, turno, quantidade_estudantes, ativo, criado_em)
        VALUES (?, '', 0, 1, datetime('now'))
    """,
        [(nome,) for nome in TURMAS_PADRAO],
    )

    cursor.executemany(
        """
        INSERT OR IGNORE INTO disciplinas (nome, aulas_semanais, ativo, criado_em)
        VALUES (?, 0, 1, datetime('now'))
    """,
        [(nome,) for nome in DISCIPLINAS_PADRAO],
    )


def _migrar_catalogos_academicos(cursor):
    cursor.execute("""
        SELECT COALESCE(turmas, '[]') AS turmas, COALESCE(disciplinas, '[]') AS disciplinas
        FROM professores_carga
    """)
    for row in cursor.fetchall():
        for turma in _desserializar_lista_texto(row["turmas"]):
            nome = _normalizar_nome_catalogo(turma)
            if nome:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO turmas (nome, turno, quantidade_estudantes, ativo, criado_em)
                    VALUES (?, '', 0, 1, datetime('now'))
                """,
                    (nome,),
                )

        for disciplina in _desserializar_lista_texto(row["disciplinas"]):
            nome = _normalizar_nome_catalogo(disciplina)
            if nome:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO disciplinas (nome, aulas_semanais, ativo, criado_em)
                    VALUES (?, 0, 1, datetime('now'))
                """,
                    (nome,),
                )

    cursor.execute("""
        SELECT DISTINCT turma
        FROM agendamentos
        WHERE turma IS NOT NULL AND TRIM(turma) <> ''
    """)
    for row in cursor.fetchall():
        nome = _normalizar_nome_catalogo(row["turma"])
        if nome:
            cursor.execute(
                """
                INSERT OR IGNORE INTO turmas (nome, turno, quantidade_estudantes, ativo, criado_em)
                VALUES (?, '', 0, 1, datetime('now'))
            """,
                (nome,),
            )


def _migrar_turmas_disciplinas_legado(cursor):
    cursor.execute("""
        SELECT
            ptd.turma_id,
            ptd.disciplina_id,
            ptd.professor_usuario_id,
            COALESCE(d.aulas_semanais, 0) AS carga_horaria_padrao
        FROM professores_turmas_disciplinas ptd
        INNER JOIN disciplinas d ON d.id = ptd.disciplina_id
        ORDER BY ptd.id ASC
    """)
    for row in cursor.fetchall():
        turma_id = int(row["turma_id"] or 0)
        disciplina_id = int(row["disciplina_id"] or 0)
        professor_id = int(row["professor_usuario_id"] or 0)
        carga_horaria = int(row["carga_horaria_padrao"] or 0)

        cursor.execute(
            """
            SELECT id, professor_usuario_id, carga_horaria
            FROM turmas_disciplinas
            WHERE turma_id = ? AND disciplina_id = ?
            LIMIT 1
        """,
            (turma_id, disciplina_id),
        )
        existente = cursor.fetchone()

        if not existente:
            cursor.execute(
                """
                INSERT INTO turmas_disciplinas (
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
                    turma_id,
                    disciplina_id,
                    carga_horaria,
                    professor_id if professor_id > 0 else None,
                ),
            )
            continue

        professor_existente = int(existente["professor_usuario_id"] or 0)
        carga_existente = int(existente["carga_horaria"] or 0)
        if professor_existente <= 0 and professor_id > 0:
            cursor.execute(
                """
                UPDATE turmas_disciplinas
                SET professor_usuario_id = ?,
                    atualizado_em = datetime('now')
                WHERE id = ?
            """,
                (professor_id, int(existente["id"])),
            )
        if carga_existente <= 0 and carga_horaria > 0:
            cursor.execute(
                """
                UPDATE turmas_disciplinas
                SET carga_horaria = ?,
                    atualizado_em = datetime('now')
                WHERE id = ?
            """,
                (carga_horaria, int(existente["id"])),
            )


def _seed_pre_conselho_periodos(cursor):
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


def _seed_pre_conselho_motivos(cursor):
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


def _migrar_registros_pre_conselho_legado(cursor):
    cursor.execute("""
        SELECT id, ano_letivo, bimestre, disciplina, observacoes, observacao_professor, motivos, periodo_id, disciplina_id
        FROM pre_conselho_registros
    """)
    registros = cursor.fetchall()
    if not registros:
        return

    cursor.execute("""
        SELECT id, ano_letivo, etapa
        FROM pre_conselho_periodos
    """)
    periodos_por_chave = {
        (int(row["ano_letivo"] or 0), int(row["etapa"] or 0)): int(row["id"])
        for row in cursor.fetchall()
    }

    cursor.execute("""
        SELECT id, nome
        FROM disciplinas
    """)
    disciplinas_por_nome = {
        _normalizar_nome_catalogo(row["nome"]).casefold(): int(row["id"])
        for row in cursor.fetchall()
    }

    cursor.execute("""
        SELECT id, codigo
        FROM pre_conselho_motivos
    """)
    motivos_por_codigo = {
        _normalizar_nome_catalogo(row["codigo"]): int(row["id"]) for row in cursor.fetchall()
    }

    for registro in registros:
        registro_id = int(registro["id"])
        ano_letivo = int(registro["ano_letivo"] or 0)
        etapa = int(registro["bimestre"] or 0)
        periodo_id = int(registro["periodo_id"] or 0)
        disciplina_id = int(registro["disciplina_id"] or 0)
        disciplina = _normalizar_nome_catalogo(registro["disciplina"])
        observacoes = _normalizar_nome_catalogo(registro["observacoes"])
        observacao_professor = _normalizar_nome_catalogo(registro["observacao_professor"])

        if periodo_id <= 0 and (ano_letivo, etapa) in periodos_por_chave:
            periodo_id = int(periodos_por_chave[(ano_letivo, etapa)])
            cursor.execute(
                """
                UPDATE pre_conselho_registros
                SET periodo_id = ?
                WHERE id = ?
            """,
                (periodo_id, registro_id),
            )

        if disciplina_id <= 0 and disciplina:
            disciplina_id = int(disciplinas_por_nome.get(disciplina.casefold()) or 0)
            if disciplina_id > 0:
                cursor.execute(
                    """
                    UPDATE pre_conselho_registros
                    SET disciplina_id = ?
                    WHERE id = ?
                """,
                    (disciplina_id, registro_id),
                )

        if not observacao_professor and observacoes:
            cursor.execute(
                """
                UPDATE pre_conselho_registros
                SET observacao_professor = ?
                WHERE id = ?
            """,
                (observacoes, registro_id),
            )

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM pre_conselho_registro_motivos
            WHERE registro_id = ?
        """,
            (registro_id,),
        )
        total_motivos = int(cursor.fetchone()["total"] or 0)
        if total_motivos > 0:
            continue

        for codigo in _desserializar_lista_texto(registro["motivos"]):
            motivo_id = int(motivos_por_codigo.get(_normalizar_nome_catalogo(codigo)) or 0)
            if motivo_id <= 0:
                continue
            cursor.execute(
                """
                INSERT OR IGNORE INTO pre_conselho_registro_motivos (
                    registro_id,
                    motivo_id,
                    criado_em
                )
                VALUES (?, ?, datetime('now'))
            """,
                (registro_id, motivo_id),
            )


def _garantir_colunas_usuarios(cursor):
    cursor.execute("PRAGMA table_info(usuarios)")
    colunas = {row["name"] for row in cursor.fetchall()}

    if "cargo" not in colunas:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN cargo TEXT NOT NULL DEFAULT ''")
    if "acesso_coordenacao" not in colunas:
        cursor.execute(
            "ALTER TABLE usuarios ADD COLUMN acesso_coordenacao INTEGER NOT NULL DEFAULT 0"
        )
    if "data_nascimento" not in colunas:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN data_nascimento TEXT")
    if "nt_hash" not in colunas:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN nt_hash CHAR(32)")
    if "ativo" not in colunas:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN ativo INTEGER NOT NULL DEFAULT 1")

    # Backfill de cargo para bancos legados baseando-se no perfil existente.
    cursor.execute("""
        UPDATE usuarios
        SET cargo = UPPER(TRIM(cargo))
        WHERE TRIM(COALESCE(cargo, '')) <> ''
    """)
    cursor.execute(
        """
        UPDATE usuarios
        SET cargo = (
            CASE
                WHEN LOWER(TRIM(COALESCE(perfil, ''))) = 'admin' THEN ?
                WHEN LOWER(TRIM(COALESCE(perfil, ''))) = 'coordenador' THEN ?
                ELSE ?
            END
        )
        WHERE TRIM(COALESCE(cargo, '')) = ''
    """,
        (CARGO_ADMIN, CARGO_COORDENADOR, CARGO_PROFESSOR),
    )

    cursor.execute("""
        UPDATE usuarios
        SET nt_hash = LOWER(TRIM(nt_hash))
        WHERE TRIM(COALESCE(nt_hash, '')) <> ''
    """)
    cursor.execute("""
        UPDATE usuarios
        SET ativo = 1
        WHERE ativo IS NULL
           OR TRIM(COALESCE(CAST(ativo AS TEXT), '')) = ''
    """)
    cursor.execute("""
        UPDATE usuarios
        SET acesso_coordenacao = 0
        WHERE acesso_coordenacao IS NULL
           OR TRIM(COALESCE(CAST(acesso_coordenacao AS TEXT), '')) = ''
    """)


def _clausula_usuario_ativo(alias: str = "") -> str:
    prefixo = ""
    if alias:
        prefixo = alias if alias.endswith(".") else f"{alias}."
    return (
        f"(COALESCE({prefixo}ativo, 1) = 1 "
        f"OR LOWER(CAST(COALESCE({prefixo}ativo, 1) AS TEXT)) = 'true')"
    )


def _garantir_colunas_tokens(cursor):
    cursor.execute("PRAGMA table_info(tokens)")
    colunas = {row["name"] for row in cursor.fetchall()}

    if "criado_em" not in colunas:
        cursor.execute("ALTER TABLE tokens ADD COLUMN criado_em TEXT NOT NULL DEFAULT ''")
    if "expira_em" not in colunas:
        cursor.execute("ALTER TABLE tokens ADD COLUMN expira_em TEXT NOT NULL DEFAULT ''")

    cursor.execute("""
        UPDATE tokens
        SET criado_em = datetime('now')
        WHERE TRIM(COALESCE(criado_em, '')) = ''
    """)
    cursor.execute(
        """
        UPDATE tokens
        SET expira_em = datetime('now', ?)
        WHERE TRIM(COALESCE(expira_em, '')) = ''
    """,
        (f"+{TOKEN_TTL_DIAS} days",),
    )

    cursor.execute("""
        DELETE FROM tokens
        WHERE expira_em <= datetime('now')
    """)


def _garantir_colunas_jobs(cursor):
    cursor.execute("PRAGMA table_info(jobs)")
    colunas = {row["name"] for row in cursor.fetchall()}

    if "paginas_por_folha" not in colunas:
        cursor.execute("ALTER TABLE jobs ADD COLUMN paginas_por_folha INTEGER NOT NULL DEFAULT 1")
    if "duplex" not in colunas:
        cursor.execute("ALTER TABLE jobs ADD COLUMN duplex INTEGER NOT NULL DEFAULT 0")
    if "orientacao" not in colunas:
        cursor.execute("ALTER TABLE jobs ADD COLUMN orientacao TEXT NOT NULL DEFAULT 'retrato'")
    if "paginas_totais" not in colunas:
        cursor.execute("ALTER TABLE jobs ADD COLUMN paginas_totais INTEGER NOT NULL DEFAULT 0")
    if "arquivo_path" not in colunas:
        cursor.execute("ALTER TABLE jobs ADD COLUMN arquivo_path TEXT")
    if "intervalo_paginas" not in colunas:
        cursor.execute("ALTER TABLE jobs ADD COLUMN intervalo_paginas TEXT NOT NULL DEFAULT ''")
    if "cups_options" not in colunas:
        cursor.execute("ALTER TABLE jobs ADD COLUMN cups_options TEXT NOT NULL DEFAULT '{}'")
    if "printer_name" not in colunas:
        cursor.execute("ALTER TABLE jobs ADD COLUMN printer_name TEXT")
    if "cups_job_id" not in colunas:
        cursor.execute("ALTER TABLE jobs ADD COLUMN cups_job_id INTEGER")
    if "erro_mensagem" not in colunas:
        cursor.execute("ALTER TABLE jobs ADD COLUMN erro_mensagem TEXT")
    if "tags_json" not in colunas:
        cursor.execute("ALTER TABLE jobs ADD COLUMN tags_json TEXT NOT NULL DEFAULT '[]'")
    if "finalizado_em" not in colunas:
        cursor.execute("ALTER TABLE jobs ADD COLUMN finalizado_em TEXT")


def _garantir_colunas_agendamentos(cursor):
    cursor.execute("PRAGMA table_info(agendamentos)")
    colunas = {row["name"] for row in cursor.fetchall()}

    if "turno" not in colunas:
        cursor.execute("ALTER TABLE agendamentos ADD COLUMN turno TEXT NOT NULL DEFAULT 'MATUTINO'")
    if "turma" not in colunas:
        cursor.execute("ALTER TABLE agendamentos ADD COLUMN turma TEXT NOT NULL DEFAULT ''")
    if "status" not in colunas:
        cursor.execute("ALTER TABLE agendamentos ADD COLUMN status TEXT NOT NULL DEFAULT 'ATIVO'")
    if "cancelado_em" not in colunas:
        cursor.execute("ALTER TABLE agendamentos ADD COLUMN cancelado_em TEXT")
    if "faixa_global" not in colunas:
        cursor.execute(
            "ALTER TABLE agendamentos ADD COLUMN faixa_global INTEGER NOT NULL DEFAULT 0"
        )
    if "tema_aula" not in colunas:
        cursor.execute("ALTER TABLE agendamentos ADD COLUMN tema_aula TEXT NOT NULL DEFAULT ''")

    # Faixa global padroniza simultaneidade entre turnos:
    # MATUTINO inicia na faixa 1.
    # INTEGRAL usa 1-5 e depois 7-9 (pulando a faixa 6).
    # VESPERTINO/VESPERTINO_EM iniciam na faixa 6.
    cursor.execute("""
        UPDATE agendamentos
        SET faixa_global = (
            CASE
                WHEN UPPER(COALESCE(turno, '')) = 'MATUTINO' THEN CAST(COALESCE(NULLIF(TRIM(aula), ''), '0') AS INTEGER)
                WHEN UPPER(COALESCE(turno, '')) = 'INTEGRAL' THEN (
                    CAST(COALESCE(NULLIF(TRIM(aula), ''), '0') AS INTEGER)
                    + CASE
                        WHEN CAST(COALESCE(NULLIF(TRIM(aula), ''), '0') AS INTEGER) > 5 THEN 1
                        ELSE 0
                      END
                )
                WHEN UPPER(COALESCE(turno, '')) IN ('VESPERTINO', 'VESPERTINO_EM') THEN CAST(COALESCE(NULLIF(TRIM(aula), ''), '0') AS INTEGER) + 5
                ELSE CAST(COALESCE(NULLIF(TRIM(aula), ''), '0') AS INTEGER)
            END
        )
    """)


def _garantir_colunas_pcpi_registros_manuais(cursor):
    cursor.execute("PRAGMA table_info(pcpi_registros_manuais)")
    colunas = {row["name"] for row in cursor.fetchall()}

    if "origem" not in colunas:
        cursor.execute(
            "ALTER TABLE pcpi_registros_manuais ADD COLUMN origem TEXT NOT NULL DEFAULT 'MANUAL'"
        )
    if "agendamento_id" not in colunas:
        cursor.execute("ALTER TABLE pcpi_registros_manuais ADD COLUMN agendamento_id INTEGER")
    if "acao_realizada" not in colunas:
        cursor.execute("ALTER TABLE pcpi_registros_manuais ADD COLUMN acao_realizada TEXT")
    if "resultado" not in colunas:
        cursor.execute("ALTER TABLE pcpi_registros_manuais ADD COLUMN resultado TEXT")

    cursor.execute("""
        UPDATE pcpi_registros_manuais
        SET origem = 'MANUAL'
        WHERE COALESCE(TRIM(origem), '') = ''
    """)


def _garantir_colunas_professores_carga(cursor):
    cursor.execute("PRAGMA table_info(professores_carga)")
    colunas = {row["name"] for row in cursor.fetchall()}

    if "aulas_semanais" not in colunas:
        cursor.execute(
            "ALTER TABLE professores_carga ADD COLUMN aulas_semanais INTEGER NOT NULL DEFAULT 0"
        )
    if "turmas_quantidade" not in colunas:
        cursor.execute(
            "ALTER TABLE professores_carga ADD COLUMN turmas_quantidade INTEGER NOT NULL DEFAULT 0"
        )
    if "atualizado_em" not in colunas:
        cursor.execute(
            "ALTER TABLE professores_carga ADD COLUMN atualizado_em TEXT NOT NULL DEFAULT datetime('now')"
        )
    if "turmas" not in colunas:
        cursor.execute("ALTER TABLE professores_carga ADD COLUMN turmas TEXT NOT NULL DEFAULT '[]'")
    if "disciplinas" not in colunas:
        cursor.execute(
            "ALTER TABLE professores_carga ADD COLUMN disciplinas TEXT NOT NULL DEFAULT '[]'"
        )


def _garantir_colunas_professores_turmas_disciplinas(cursor):
    cursor.execute("PRAGMA table_info(professores_turmas_disciplinas)")
    colunas = {row["name"] for row in cursor.fetchall()}

    if not colunas:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS professores_turmas_disciplinas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                professor_usuario_id INTEGER NOT NULL,
                turma_id INTEGER NOT NULL,
                disciplina_id INTEGER NOT NULL,
                criado_em TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY(professor_usuario_id) REFERENCES usuarios(id),
                FOREIGN KEY(turma_id) REFERENCES turmas(id),
                FOREIGN KEY(disciplina_id) REFERENCES disciplinas(id),
                UNIQUE(professor_usuario_id, turma_id, disciplina_id)
            )
        """)
        return

    if "criado_em" not in colunas:
        cursor.execute(
            "ALTER TABLE professores_turmas_disciplinas ADD COLUMN criado_em TEXT NOT NULL DEFAULT ''"
        )
        cursor.execute("""
            UPDATE professores_turmas_disciplinas
            SET criado_em = datetime('now')
            WHERE TRIM(COALESCE(criado_em, '')) = ''
        """)


def _garantir_colunas_cota_regras(cursor):
    cursor.execute("PRAGMA table_info(cota_regras)")
    colunas = {row["name"] for row in cursor.fetchall()}

    if "cota_mensal_escola" not in colunas:
        cursor.execute(
            "ALTER TABLE cota_regras ADD COLUMN cota_mensal_escola INTEGER NOT NULL DEFAULT 4000"
        )


def _garantir_colunas_recursos(cursor):
    cursor.execute("PRAGMA table_info(recursos)")
    colunas = {row["name"] for row in cursor.fetchall()}

    if "quantidade_itens" not in colunas:
        cursor.execute(
            "ALTER TABLE recursos ADD COLUMN quantidade_itens INTEGER NOT NULL DEFAULT 1"
        )

    cursor.execute("""
        UPDATE recursos
        SET quantidade_itens = 1
        WHERE COALESCE(quantidade_itens, 0) < 1
    """)


def _garantir_colunas_turmas(cursor):
    cursor.execute("PRAGMA table_info(turmas)")
    colunas = {row["name"] for row in cursor.fetchall()}

    if "turno" not in colunas:
        cursor.execute("ALTER TABLE turmas ADD COLUMN turno TEXT NOT NULL DEFAULT ''")
    if "quantidade_estudantes" not in colunas:
        cursor.execute(
            "ALTER TABLE turmas ADD COLUMN quantidade_estudantes INTEGER NOT NULL DEFAULT 0"
        )


def _garantir_colunas_disciplinas(cursor):
    cursor.execute("PRAGMA table_info(disciplinas)")
    colunas = {row["name"] for row in cursor.fetchall()}

    if "aulas_semanais" not in colunas:
        cursor.execute(
            "ALTER TABLE disciplinas ADD COLUMN aulas_semanais INTEGER NOT NULL DEFAULT 0"
        )
    if "tem_apc" not in colunas:
        cursor.execute("ALTER TABLE disciplinas ADD COLUMN tem_apc INTEGER NOT NULL DEFAULT 0")
    if "tem_prova_bimestral" not in colunas:
        cursor.execute(
            "ALTER TABLE disciplinas ADD COLUMN tem_prova_bimestral INTEGER NOT NULL DEFAULT 0"
        )


def _garantir_colunas_turmas_disciplinas(cursor):
    cursor.execute("PRAGMA table_info(turmas_disciplinas)")
    colunas = {row["name"] for row in cursor.fetchall()}

    if not colunas:
        cursor.execute("""
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
        """)
        return

    if "carga_horaria" not in colunas:
        cursor.execute(
            "ALTER TABLE turmas_disciplinas ADD COLUMN carga_horaria INTEGER NOT NULL DEFAULT 0"
        )
    if "professor_usuario_id" not in colunas:
        cursor.execute("ALTER TABLE turmas_disciplinas ADD COLUMN professor_usuario_id INTEGER")
    if "criado_em" not in colunas:
        cursor.execute(
            "ALTER TABLE turmas_disciplinas ADD COLUMN criado_em TEXT NOT NULL DEFAULT ''"
        )
        cursor.execute("""
            UPDATE turmas_disciplinas
            SET criado_em = datetime('now')
            WHERE TRIM(COALESCE(criado_em, '')) = ''
        """)
    if "atualizado_em" not in colunas:
        cursor.execute(
            "ALTER TABLE turmas_disciplinas ADD COLUMN atualizado_em TEXT NOT NULL DEFAULT ''"
        )
        cursor.execute("""
            UPDATE turmas_disciplinas
            SET atualizado_em = datetime('now')
            WHERE TRIM(COALESCE(atualizado_em, '')) = ''
        """)

    cursor.execute("""
        UPDATE turmas_disciplinas
        SET professor_usuario_id = NULL
        WHERE COALESCE(professor_usuario_id, 0) <= 0
    """)


def _garantir_colunas_estudantes(cursor):
    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = 'estudantes'
    """)
    if not cursor.fetchone():
        return

    cursor.execute("PRAGMA table_info(estudantes)")
    colunas = {row["name"] for row in cursor.fetchall()}

    if "nome" not in colunas:
        cursor.execute("ALTER TABLE estudantes ADD COLUMN nome TEXT NOT NULL DEFAULT ''")
    if "turma_id" not in colunas:
        cursor.execute("ALTER TABLE estudantes ADD COLUMN turma_id INTEGER NOT NULL DEFAULT 0")
    if "ativo" not in colunas:
        cursor.execute("ALTER TABLE estudantes ADD COLUMN ativo INTEGER NOT NULL DEFAULT 1")
    if "criado_em" not in colunas:
        cursor.execute(
            "ALTER TABLE estudantes ADD COLUMN criado_em TEXT NOT NULL DEFAULT (datetime('now'))"
        )
    if "atualizado_em" not in colunas:
        cursor.execute(
            "ALTER TABLE estudantes ADD COLUMN atualizado_em TEXT NOT NULL DEFAULT (datetime('now'))"
        )

    cursor.execute("""
        UPDATE estudantes
        SET atualizado_em = datetime('now')
        WHERE TRIM(COALESCE(atualizado_em, '')) = ''
    """)
    cursor.execute("""
        UPDATE estudantes
        SET ativo = 1
        WHERE ativo IS NULL
    """)


def _garantir_colunas_pre_conselho_periodos(cursor):
    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = 'pre_conselho_periodos'
    """)
    if not cursor.fetchone():
        return

    cursor.execute("PRAGMA table_info(pre_conselho_periodos)")
    colunas = {row["name"] for row in cursor.fetchall()}

    if "nome" not in colunas:
        cursor.execute("ALTER TABLE pre_conselho_periodos ADD COLUMN nome TEXT NOT NULL DEFAULT ''")
    if "ano_letivo" not in colunas:
        cursor.execute(
            "ALTER TABLE pre_conselho_periodos ADD COLUMN ano_letivo INTEGER NOT NULL DEFAULT 0"
        )
    if "etapa" not in colunas:
        cursor.execute(
            "ALTER TABLE pre_conselho_periodos ADD COLUMN etapa INTEGER NOT NULL DEFAULT 0"
        )
    if "data_inicio" not in colunas:
        cursor.execute(
            "ALTER TABLE pre_conselho_periodos ADD COLUMN data_inicio TEXT NOT NULL DEFAULT ''"
        )
    if "data_fim" not in colunas:
        cursor.execute(
            "ALTER TABLE pre_conselho_periodos ADD COLUMN data_fim TEXT NOT NULL DEFAULT ''"
        )
    if "status" not in colunas:
        cursor.execute(
            "ALTER TABLE pre_conselho_periodos ADD COLUMN status TEXT NOT NULL DEFAULT 'FECHADO'"
        )
    if "criado_em" not in colunas:
        cursor.execute(
            "ALTER TABLE pre_conselho_periodos ADD COLUMN criado_em TEXT NOT NULL DEFAULT (datetime('now'))"
        )
    if "atualizado_em" not in colunas:
        cursor.execute(
            "ALTER TABLE pre_conselho_periodos ADD COLUMN atualizado_em TEXT NOT NULL DEFAULT (datetime('now'))"
        )


def _garantir_colunas_pre_conselho_motivos(cursor):
    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = 'pre_conselho_motivos'
    """)
    if not cursor.fetchone():
        return

    cursor.execute("PRAGMA table_info(pre_conselho_motivos)")
    colunas = {row["name"] for row in cursor.fetchall()}

    if "categoria" not in colunas:
        cursor.execute(
            "ALTER TABLE pre_conselho_motivos ADD COLUMN categoria TEXT NOT NULL DEFAULT ''"
        )
    if "codigo" not in colunas:
        cursor.execute(
            "ALTER TABLE pre_conselho_motivos ADD COLUMN codigo TEXT NOT NULL DEFAULT ''"
        )
    if "descricao" not in colunas:
        cursor.execute(
            "ALTER TABLE pre_conselho_motivos ADD COLUMN descricao TEXT NOT NULL DEFAULT ''"
        )
    if "ativo" not in colunas:
        cursor.execute(
            "ALTER TABLE pre_conselho_motivos ADD COLUMN ativo INTEGER NOT NULL DEFAULT 1"
        )
    if "ordem" not in colunas:
        cursor.execute(
            "ALTER TABLE pre_conselho_motivos ADD COLUMN ordem INTEGER NOT NULL DEFAULT 0"
        )
    if "criado_em" not in colunas:
        cursor.execute(
            "ALTER TABLE pre_conselho_motivos ADD COLUMN criado_em TEXT NOT NULL DEFAULT (datetime('now'))"
        )
    if "atualizado_em" not in colunas:
        cursor.execute(
            "ALTER TABLE pre_conselho_motivos ADD COLUMN atualizado_em TEXT NOT NULL DEFAULT (datetime('now'))"
        )

    cursor.execute("""
        UPDATE pre_conselho_motivos
        SET ativo = 1
        WHERE ativo IS NULL
    """)


def _garantir_colunas_pre_conselho_registros(cursor):
    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = 'pre_conselho_registros'
    """)
    if not cursor.fetchone():
        return

    cursor.execute("PRAGMA table_info(pre_conselho_registros)")
    colunas = {row["name"] for row in cursor.fetchall()}

    if "periodo_id" not in colunas:
        cursor.execute("ALTER TABLE pre_conselho_registros ADD COLUMN periodo_id INTEGER")
    if "disciplina_id" not in colunas:
        cursor.execute("ALTER TABLE pre_conselho_registros ADD COLUMN disciplina_id INTEGER")
    if "professor_usuario_id" not in colunas:
        cursor.execute(
            "ALTER TABLE pre_conselho_registros ADD COLUMN professor_usuario_id INTEGER NOT NULL DEFAULT 0"
        )
    if "turma_id" not in colunas:
        cursor.execute(
            "ALTER TABLE pre_conselho_registros ADD COLUMN turma_id INTEGER NOT NULL DEFAULT 0"
        )
    if "estudante_id" not in colunas:
        cursor.execute(
            "ALTER TABLE pre_conselho_registros ADD COLUMN estudante_id INTEGER NOT NULL DEFAULT 0"
        )
    if "disciplina" not in colunas:
        cursor.execute(
            "ALTER TABLE pre_conselho_registros ADD COLUMN disciplina TEXT NOT NULL DEFAULT ''"
        )
    if "ano_letivo" not in colunas:
        cursor.execute(
            "ALTER TABLE pre_conselho_registros ADD COLUMN ano_letivo INTEGER NOT NULL DEFAULT 0"
        )
    if "bimestre" not in colunas:
        cursor.execute(
            "ALTER TABLE pre_conselho_registros ADD COLUMN bimestre INTEGER NOT NULL DEFAULT 0"
        )
    if "nivel_atencao" not in colunas:
        cursor.execute("ALTER TABLE pre_conselho_registros ADD COLUMN nivel_atencao TEXT")
    if "motivos" not in colunas:
        cursor.execute(
            "ALTER TABLE pre_conselho_registros ADD COLUMN motivos TEXT NOT NULL DEFAULT '[]'"
        )
    if "observacoes" not in colunas:
        cursor.execute(
            "ALTER TABLE pre_conselho_registros ADD COLUMN observacoes TEXT NOT NULL DEFAULT ''"
        )
    if "criado_em" not in colunas:
        cursor.execute(
            "ALTER TABLE pre_conselho_registros ADD COLUMN criado_em TEXT NOT NULL DEFAULT (datetime('now'))"
        )
    if "atualizado_em" not in colunas:
        cursor.execute(
            "ALTER TABLE pre_conselho_registros ADD COLUMN atualizado_em TEXT NOT NULL DEFAULT (datetime('now'))"
        )
    if "observacao_professor" not in colunas:
        cursor.execute(
            "ALTER TABLE pre_conselho_registros ADD COLUMN observacao_professor TEXT NOT NULL DEFAULT ''"
        )
    if "pos_preconselho_recuperado" not in colunas:
        cursor.execute("ALTER TABLE pre_conselho_registros ADD COLUMN pos_preconselho_recuperado INTEGER")
    if "pos_preconselho_motivos" not in colunas:
        cursor.execute(
            "ALTER TABLE pre_conselho_registros ADD COLUMN pos_preconselho_motivos TEXT NOT NULL DEFAULT '[]'"
        )
    if "pos_preconselho_observacao" not in colunas:
        cursor.execute(
            "ALTER TABLE pre_conselho_registros ADD COLUMN pos_preconselho_observacao TEXT NOT NULL DEFAULT ''"
        )
    if "texto_gerado" not in colunas:
        cursor.execute(
            "ALTER TABLE pre_conselho_registros ADD COLUMN texto_gerado TEXT NOT NULL DEFAULT ''"
        )

    cursor.execute("""
        UPDATE pre_conselho_registros
        SET motivos = '[]'
        WHERE TRIM(COALESCE(motivos, '')) = ''
    """)
    cursor.execute("""
        UPDATE pre_conselho_registros
        SET observacoes = ''
        WHERE observacoes IS NULL
    """)
    cursor.execute("""
        UPDATE pre_conselho_registros
        SET observacao_professor = COALESCE(observacoes, '')
        WHERE TRIM(COALESCE(observacao_professor, '')) = ''
    """)
    cursor.execute("""
        UPDATE pre_conselho_registros
        SET pos_preconselho_motivos = '[]'
        WHERE TRIM(COALESCE(pos_preconselho_motivos, '')) = ''
    """)
    cursor.execute("""
        UPDATE pre_conselho_registros
        SET pos_preconselho_observacao = ''
        WHERE pos_preconselho_observacao IS NULL
    """)
    cursor.execute("""
        UPDATE pre_conselho_registros
        SET disciplina = ''
        WHERE disciplina IS NULL
    """)
    cursor.execute("""
        UPDATE pre_conselho_registros
        SET atualizado_em = datetime('now')
        WHERE TRIM(COALESCE(atualizado_em, '')) = ''
    """)


def _garantir_colunas_pre_conselho_registro_motivos(cursor):
    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = 'pre_conselho_registro_motivos'
    """)
    if not cursor.fetchone():
        return

    cursor.execute("PRAGMA table_info(pre_conselho_registro_motivos)")
    colunas = {row["name"] for row in cursor.fetchall()}

    if "registro_id" not in colunas:
        cursor.execute(
            "ALTER TABLE pre_conselho_registro_motivos ADD COLUMN registro_id INTEGER NOT NULL DEFAULT 0"
        )
    if "motivo_id" not in colunas:
        cursor.execute(
            "ALTER TABLE pre_conselho_registro_motivos ADD COLUMN motivo_id INTEGER NOT NULL DEFAULT 0"
        )
    if "criado_em" not in colunas:
        cursor.execute(
            "ALTER TABLE pre_conselho_registro_motivos ADD COLUMN criado_em TEXT NOT NULL DEFAULT (datetime('now'))"
        )


def _garantir_colunas_ocorrencias(cursor):
    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = 'ocorrencias'
    """)
    if not cursor.fetchone():
        return

    cursor.execute("PRAGMA table_info(ocorrencias)")
    info_colunas = cursor.fetchall()
    colunas = {row["name"] for row in info_colunas}

    if "tipo_registro" not in colunas:
        cursor.execute(
            "ALTER TABLE ocorrencias ADD COLUMN tipo_registro TEXT NOT NULL DEFAULT 'estudante'"
        )
    if "nome_estudante" not in colunas:
        cursor.execute("ALTER TABLE ocorrencias ADD COLUMN nome_estudante TEXT NOT NULL DEFAULT ''")
    if "estudante_id" not in colunas:
        cursor.execute("ALTER TABLE ocorrencias ADD COLUMN estudante_id INTEGER")
    if "turma_id" not in colunas:
        cursor.execute("ALTER TABLE ocorrencias ADD COLUMN turma_id INTEGER NOT NULL DEFAULT 0")
    if "professor_requerente" not in colunas:
        cursor.execute(
            "ALTER TABLE ocorrencias ADD COLUMN professor_requerente TEXT NOT NULL DEFAULT ''"
        )
    if "professor_requerente_id" not in colunas:
        cursor.execute("ALTER TABLE ocorrencias ADD COLUMN professor_requerente_id INTEGER")
    if "disciplina" not in colunas:
        cursor.execute("ALTER TABLE ocorrencias ADD COLUMN disciplina TEXT NOT NULL DEFAULT ''")
    if "data_ocorrencia" not in colunas:
        cursor.execute(
            "ALTER TABLE ocorrencias ADD COLUMN data_ocorrencia TEXT NOT NULL DEFAULT ''"
        )
    if "aula" not in colunas:
        cursor.execute("ALTER TABLE ocorrencias ADD COLUMN aula TEXT NOT NULL DEFAULT ''")
    if "horario_ocorrencia" not in colunas:
        cursor.execute(
            "ALTER TABLE ocorrencias ADD COLUMN horario_ocorrencia TEXT NOT NULL DEFAULT ''"
        )
    if "descricao" not in colunas:
        cursor.execute("ALTER TABLE ocorrencias ADD COLUMN descricao TEXT NOT NULL DEFAULT ''")
    if "acao_aplicada" not in colunas:
        cursor.execute("ALTER TABLE ocorrencias ADD COLUMN acao_aplicada TEXT NOT NULL DEFAULT ''")
    if "status" not in colunas:
        cursor.execute(
            "ALTER TABLE ocorrencias ADD COLUMN status TEXT NOT NULL DEFAULT 'registrado'"
        )
    if "criado_em" not in colunas:
        cursor.execute(
            "ALTER TABLE ocorrencias ADD COLUMN criado_em TEXT NOT NULL DEFAULT (datetime('now'))"
        )
    if "atualizado_em" not in colunas:
        cursor.execute(
            "ALTER TABLE ocorrencias ADD COLUMN atualizado_em TEXT NOT NULL DEFAULT (datetime('now'))"
        )

    cursor.execute(
        """
        UPDATE ocorrencias
        SET tipo_registro = ?
        WHERE TRIM(COALESCE(tipo_registro, '')) = ''
    """,
        (TIPO_REGISTRO_OCORRENCIA_ESTUDANTE,),
    )

    cursor.execute(
        """
        UPDATE ocorrencias
        SET status = ?
        WHERE TRIM(COALESCE(status, '')) = ''
    """,
        (STATUS_OCORRENCIA_REGISTRADO,),
    )

    cursor.execute("""
        UPDATE ocorrencias
        SET atualizado_em = datetime('now')
        WHERE TRIM(COALESCE(atualizado_em, '')) = ''
    """)

    _recriar_tabela_ocorrencias_se_necessario(cursor)


def _recriar_tabela_ocorrencias_se_necessario(cursor):
    cursor.execute("""
        SELECT sql
        FROM sqlite_master
        WHERE type = 'table'
          AND name = 'ocorrencias'
    """)
    row = cursor.fetchone()
    if not row:
        return

    sql_tabela = str(row["sql"] or "")
    precisa_recriar = not sql_tabela
    if sql_tabela:
        sql_tabela_upper = sql_tabela.upper()
        tem_acoes_atualizadas = all(acao in sql_tabela for acao in ACAO_OCORRENCIA_VALIDAS)
        tem_tipo_registro = "TIPO_REGISTRO" in sql_tabela_upper
        turma_aceita_nulo = "TURMA_ID INTEGER NOT NULL" not in sql_tabela_upper
        precisa_recriar = not (tem_acoes_atualizadas and tem_tipo_registro and turma_aceita_nulo)

    if not precisa_recriar:
        return

    cursor.execute("PRAGMA foreign_keys = OFF")
    cursor.execute("DROP TABLE IF EXISTS ocorrencias__tmp")
    cursor.execute(f"""
        CREATE TABLE ocorrencias__tmp (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo_registro TEXT NOT NULL DEFAULT '{TIPO_REGISTRO_OCORRENCIA_ESTUDANTE}' CHECK (tipo_registro IN {TIPOS_REGISTRO_OCORRENCIA}),
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
            acao_aplicada TEXT NOT NULL CHECK (acao_aplicada IN {ACAO_OCORRENCIA_VALIDAS}),
            status TEXT NOT NULL DEFAULT '{STATUS_OCORRENCIA_REGISTRADO}' CHECK (status IN {STATUS_OCORRENCIA_VALIDOS}),
            criado_em TEXT NOT NULL DEFAULT (datetime('now')),
            atualizado_em TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(estudante_id) REFERENCES estudantes(id),
            FOREIGN KEY(turma_id) REFERENCES turmas(id),
            FOREIGN KEY(professor_requerente_id) REFERENCES usuarios(id)
        )
    """)
    cursor.execute(
        """
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
                WHEN TRIM(COALESCE(tipo_registro, '')) IN {TIPOS_REGISTRO_OCORRENCIA}
                    THEN TRIM(tipo_registro)
                ELSE '{TIPO_REGISTRO_OCORRENCIA_ESTUDANTE}'
            END,
            COALESCE(nome_estudante, ''),
            estudante_id,
            turma_id,
            COALESCE(professor_requerente, ''),
            professor_requerente_id,
            COALESCE(disciplina, ''),
            COALESCE(data_ocorrencia, ''),
            COALESCE(aula, ''),
            COALESCE(horario_ocorrencia, ''),
            COALESCE(descricao, ''),
            CASE
                WHEN TRIM(COALESCE(acao_aplicada, '')) = '' THEN 'registro_informativo'
                ELSE TRIM(acao_aplicada)
            END,
            COALESCE(status, ?),
            COALESCE(criado_em, datetime('now')),
            COALESCE(atualizado_em, datetime('now'))
        FROM ocorrencias
    """,
        (STATUS_OCORRENCIA_REGISTRADO,),
    )
    cursor.execute("DROP TABLE ocorrencias")
    cursor.execute("ALTER TABLE ocorrencias__tmp RENAME TO ocorrencias")
    cursor.execute("PRAGMA foreign_keys = ON")


def _codificar_regimento_item_id(tipo: str, entidade_id: int) -> int:
    entidade_id_valor = int(entidade_id or 0)
    if entidade_id_valor <= 0:
        raise ValueError("Item de base legal invalido.")
    if tipo == TIPO_BASE_LEGAL_ARTIGO:
        return entidade_id_valor
    if tipo == TIPO_BASE_LEGAL_INCISO:
        return BASE_LEGAL_ITEM_INCISO_OFFSET + entidade_id_valor
    if tipo == TIPO_BASE_LEGAL_ALINEA:
        return BASE_LEGAL_ITEM_ALINEA_OFFSET + entidade_id_valor
    raise ValueError("Tipo de base legal invalido.")


def _decodificar_regimento_item_id(regimento_item_id: int) -> tuple[str, int]:
    item_id = int(regimento_item_id or 0)
    if item_id <= 0:
        raise ValueError("Item de base legal invalido.")
    if item_id >= BASE_LEGAL_ITEM_ALINEA_OFFSET:
        return TIPO_BASE_LEGAL_ALINEA, item_id - BASE_LEGAL_ITEM_ALINEA_OFFSET
    if item_id >= BASE_LEGAL_ITEM_INCISO_OFFSET:
        return TIPO_BASE_LEGAL_INCISO, item_id - BASE_LEGAL_ITEM_INCISO_OFFSET
    return TIPO_BASE_LEGAL_ARTIGO, item_id


def _formatar_numero_artigo(numero: str) -> str:
    texto = str(numero or "").strip()
    if not texto:
        return "Sem artigo"
    if texto.lower().startswith("art"):
        return texto
    return f"Art. {texto}"


def _montar_rotulo_base_legal(
    lei_nome: str,
    artigo_numero: str,
    inciso_numero: str | None = None,
    alinea_identificador: str | None = None,
) -> str:
    lei_limpa = str(lei_nome or "").strip()
    referencia = _formatar_numero_artigo(artigo_numero)
    if lei_limpa and lei_limpa != LEI_PADRAO_IMPORTACAO:
        referencia = f"{lei_limpa} - {referencia}"
    if str(inciso_numero or "").strip():
        referencia += f", inciso {str(inciso_numero).strip()}"
    if str(alinea_identificador or "").strip():
        referencia += f", alinea {str(alinea_identificador).strip()}"
    return referencia


def _descricao_item_base_legal(dados: dict | sqlite3.Row) -> str:
    dados_norm = dict(dados)
    if str(dados_norm.get("alinea_descricao") or "").strip():
        return str(dados_norm.get("alinea_descricao") or "").strip()
    if str(dados_norm.get("inciso_descricao") or "").strip():
        return str(dados_norm.get("inciso_descricao") or "").strip()
    return str(dados_norm.get("artigo_descricao") or "").strip()


def _montar_item_base_legal(row: sqlite3.Row | dict) -> dict:
    dados = dict(row)
    tipo = str(dados.get("tipo") or TIPO_BASE_LEGAL_ARTIGO).strip()
    entidade_id = int(dados.get("entidade_id") or 0)
    artigo_id = int(dados.get("artigo_id") or 0)
    inciso_id = int(dados["inciso_id"]) if dados.get("inciso_id") is not None else None
    alinea_id = int(dados["alinea_id"]) if dados.get("alinea_id") is not None else None
    referencia = _montar_rotulo_base_legal(
        dados.get("lei_nome") or "",
        dados.get("artigo_numero") or "",
        dados.get("inciso_numero"),
        dados.get("alinea_identificador"),
    )
    descricao = _descricao_item_base_legal(dados)
    return {
        "id": _codificar_regimento_item_id(tipo, entidade_id),
        "tipo": tipo,
        "lei_id": int(dados.get("lei_id") or 0),
        "lei_nome": str(dados.get("lei_nome") or "").strip(),
        "artigo_id": artigo_id if artigo_id > 0 else None,
        "artigo_numero": str(dados.get("artigo_numero") or "").strip(),
        "artigo_descricao": str(dados.get("artigo_descricao") or "").strip(),
        "inciso_id": inciso_id,
        "inciso_numero": str(dados.get("inciso_numero") or "").strip() or None,
        "inciso_descricao": str(dados.get("inciso_descricao") or "").strip() or None,
        "alinea_id": alinea_id,
        "alinea_identificador": str(dados.get("alinea_identificador") or "").strip() or None,
        "alinea_descricao": str(dados.get("alinea_descricao") or "").strip() or None,
        "artigo": referencia,
        "descricao": descricao,
        "ativo": 1,
        "criado_em": "",
        "atualizado_em": "",
    }


def _normalizar_campos_base_legal(
    *,
    lei_nome: str | None,
    artigo_numero: str | None,
    artigo_descricao: str | None,
    inciso_numero: str | None = None,
    inciso_descricao: str | None = None,
    alinea_identificador: str | None = None,
    alinea_descricao: str | None = None,
) -> dict:
    dados = {
        "lei_nome": str(lei_nome or "").strip() or LEI_PADRAO_IMPORTACAO,
        "artigo_numero": str(artigo_numero or "").strip(),
        "artigo_descricao": str(artigo_descricao or "").strip(),
        "inciso_numero": str(inciso_numero or "").strip(),
        "inciso_descricao": str(inciso_descricao or "").strip(),
        "alinea_identificador": str(alinea_identificador or "").strip(),
        "alinea_descricao": str(alinea_descricao or "").strip(),
    }
    if not dados["artigo_numero"]:
        raise ValueError("Numero do artigo e obrigatorio.")
    if not dados["artigo_descricao"]:
        raise ValueError("Descricao do artigo e obrigatoria.")
    if bool(dados["inciso_numero"]) != bool(dados["inciso_descricao"]):
        raise ValueError("Inciso e descricao do inciso devem ser informados juntos.")
    if dados["alinea_identificador"] and not dados["inciso_numero"]:
        raise ValueError("Informe um inciso antes de cadastrar uma alinea.")
    if bool(dados["alinea_identificador"]) != bool(dados["alinea_descricao"]):
        raise ValueError("Alinea e descricao da alinea devem ser informadas juntas.")
    return dados


def _obter_ou_criar_lei_cursor(cursor, nome: str) -> tuple[int, bool]:
    nome_limpo = str(nome or "").strip() or LEI_PADRAO_IMPORTACAO
    cursor.execute("SELECT id FROM leis WHERE nome = ? COLLATE NOCASE LIMIT 1", (nome_limpo,))
    row = cursor.fetchone()
    if row:
        return int(row["id"]), False
    cursor.execute("INSERT INTO leis (nome) VALUES (?)", (nome_limpo,))
    return int(cursor.lastrowid), True


def _obter_ou_criar_artigo_cursor(
    cursor,
    *,
    lei_id: int,
    numero: str,
    descricao: str,
) -> tuple[int, bool]:
    numero_limpo = str(numero or "").strip()
    descricao_limpa = str(descricao or "").strip()
    cursor.execute(
        """
        SELECT id
        FROM artigos
        WHERE lei_id = ?
          AND numero = ? COLLATE NOCASE
        LIMIT 1
    """,
        (int(lei_id), numero_limpo),
    )
    row = cursor.fetchone()
    if row:
        artigo_id = int(row["id"])
        cursor.execute(
            "UPDATE artigos SET descricao = ? WHERE id = ?",
            (descricao_limpa, artigo_id),
        )
        return artigo_id, False
    cursor.execute(
        """
        INSERT INTO artigos (lei_id, numero, descricao)
        VALUES (?, ?, ?)
    """,
        (int(lei_id), numero_limpo, descricao_limpa),
    )
    return int(cursor.lastrowid), True


def _obter_ou_criar_inciso_cursor(
    cursor,
    *,
    artigo_id: int,
    numero: str,
    descricao: str,
) -> tuple[int, bool]:
    numero_limpo = str(numero or "").strip()
    descricao_limpa = str(descricao or "").strip()
    cursor.execute(
        """
        SELECT id
        FROM incisos
        WHERE artigo_id = ?
          AND numero = ? COLLATE NOCASE
        LIMIT 1
    """,
        (int(artigo_id), numero_limpo),
    )
    row = cursor.fetchone()
    if row:
        inciso_id = int(row["id"])
        cursor.execute(
            "UPDATE incisos SET descricao = ? WHERE id = ?",
            (descricao_limpa, inciso_id),
        )
        return inciso_id, False
    cursor.execute(
        """
        INSERT INTO incisos (artigo_id, numero, descricao)
        VALUES (?, ?, ?)
    """,
        (int(artigo_id), numero_limpo, descricao_limpa),
    )
    return int(cursor.lastrowid), True


def _obter_ou_criar_alinea_cursor(
    cursor,
    *,
    inciso_id: int,
    identificador: str,
    descricao: str,
) -> tuple[int, bool]:
    identificador_limpo = str(identificador or "").strip()
    descricao_limpa = str(descricao or "").strip()
    cursor.execute(
        """
        SELECT id
        FROM alineas
        WHERE inciso_id = ?
          AND identificador = ? COLLATE NOCASE
        LIMIT 1
    """,
        (int(inciso_id), identificador_limpo),
    )
    row = cursor.fetchone()
    if row:
        alinea_id = int(row["id"])
        cursor.execute(
            "UPDATE alineas SET descricao = ? WHERE id = ?",
            (descricao_limpa, alinea_id),
        )
        return alinea_id, False
    cursor.execute(
        """
        INSERT INTO alineas (inciso_id, identificador, descricao)
        VALUES (?, ?, ?)
    """,
        (int(inciso_id), identificador_limpo, descricao_limpa),
    )
    return int(cursor.lastrowid), True


def _buscar_item_base_legal_por_tipo_cursor(cursor, tipo: str, entidade_id: int) -> dict | None:
    entidade_id_valor = int(entidade_id or 0)
    if entidade_id_valor <= 0:
        return None

    if tipo == TIPO_BASE_LEGAL_ARTIGO:
        cursor.execute(
            """
            SELECT
                ? AS tipo,
                l.id AS lei_id,
                l.nome AS lei_nome,
                a.id AS entidade_id,
                a.id AS artigo_id,
                a.numero AS artigo_numero,
                a.descricao AS artigo_descricao,
                NULL AS inciso_id,
                NULL AS inciso_numero,
                NULL AS inciso_descricao,
                NULL AS alinea_id,
                NULL AS alinea_identificador,
                NULL AS alinea_descricao
            FROM artigos a
            INNER JOIN leis l ON l.id = a.lei_id
            WHERE a.id = ?
        """,
            (TIPO_BASE_LEGAL_ARTIGO, entidade_id_valor),
        )
    elif tipo == TIPO_BASE_LEGAL_INCISO:
        cursor.execute(
            """
            SELECT
                ? AS tipo,
                l.id AS lei_id,
                l.nome AS lei_nome,
                i.id AS entidade_id,
                a.id AS artigo_id,
                a.numero AS artigo_numero,
                a.descricao AS artigo_descricao,
                i.id AS inciso_id,
                i.numero AS inciso_numero,
                i.descricao AS inciso_descricao,
                NULL AS alinea_id,
                NULL AS alinea_identificador,
                NULL AS alinea_descricao
            FROM incisos i
            INNER JOIN artigos a ON a.id = i.artigo_id
            INNER JOIN leis l ON l.id = a.lei_id
            WHERE i.id = ?
        """,
            (TIPO_BASE_LEGAL_INCISO, entidade_id_valor),
        )
    elif tipo == TIPO_BASE_LEGAL_ALINEA:
        cursor.execute(
            """
            SELECT
                ? AS tipo,
                l.id AS lei_id,
                l.nome AS lei_nome,
                al.id AS entidade_id,
                a.id AS artigo_id,
                a.numero AS artigo_numero,
                a.descricao AS artigo_descricao,
                i.id AS inciso_id,
                i.numero AS inciso_numero,
                i.descricao AS inciso_descricao,
                al.id AS alinea_id,
                al.identificador AS alinea_identificador,
                al.descricao AS alinea_descricao
            FROM alineas al
            INNER JOIN incisos i ON i.id = al.inciso_id
            INNER JOIN artigos a ON a.id = i.artigo_id
            INNER JOIN leis l ON l.id = a.lei_id
            WHERE al.id = ?
        """,
            (TIPO_BASE_LEGAL_ALINEA, entidade_id_valor),
        )
    else:
        return None

    row = cursor.fetchone()
    return _montar_item_base_legal(row) if row else None


def _listar_itens_base_legal_cursor(cursor) -> list[dict]:
    itens = []

    cursor.execute(
        """
        SELECT
            ? AS tipo,
            l.id AS lei_id,
            l.nome AS lei_nome,
            a.id AS entidade_id,
            a.id AS artigo_id,
            a.numero AS artigo_numero,
            a.descricao AS artigo_descricao,
            NULL AS inciso_id,
            NULL AS inciso_numero,
            NULL AS inciso_descricao,
            NULL AS alinea_id,
            NULL AS alinea_identificador,
            NULL AS alinea_descricao
        FROM artigos a
        INNER JOIN leis l ON l.id = a.lei_id
        ORDER BY LOWER(l.nome), a.id
    """,
        (TIPO_BASE_LEGAL_ARTIGO,),
    )
    itens.extend(_montar_item_base_legal(row) for row in cursor.fetchall())

    cursor.execute(
        """
        SELECT
            ? AS tipo,
            l.id AS lei_id,
            l.nome AS lei_nome,
            i.id AS entidade_id,
            a.id AS artigo_id,
            a.numero AS artigo_numero,
            a.descricao AS artigo_descricao,
            i.id AS inciso_id,
            i.numero AS inciso_numero,
            i.descricao AS inciso_descricao,
            NULL AS alinea_id,
            NULL AS alinea_identificador,
            NULL AS alinea_descricao
        FROM incisos i
        INNER JOIN artigos a ON a.id = i.artigo_id
        INNER JOIN leis l ON l.id = a.lei_id
        ORDER BY LOWER(l.nome), a.id, i.id
    """,
        (TIPO_BASE_LEGAL_INCISO,),
    )
    itens.extend(_montar_item_base_legal(row) for row in cursor.fetchall())

    cursor.execute(
        """
        SELECT
            ? AS tipo,
            l.id AS lei_id,
            l.nome AS lei_nome,
            al.id AS entidade_id,
            a.id AS artigo_id,
            a.numero AS artigo_numero,
            a.descricao AS artigo_descricao,
            i.id AS inciso_id,
            i.numero AS inciso_numero,
            i.descricao AS inciso_descricao,
            al.id AS alinea_id,
            al.identificador AS alinea_identificador,
            al.descricao AS alinea_descricao
        FROM alineas al
        INNER JOIN incisos i ON i.id = al.inciso_id
        INNER JOIN artigos a ON a.id = i.artigo_id
        INNER JOIN leis l ON l.id = a.lei_id
        ORDER BY LOWER(l.nome), a.id, i.id, al.id
    """,
        (TIPO_BASE_LEGAL_ALINEA,),
    )
    itens.extend(_montar_item_base_legal(row) for row in cursor.fetchall())

    ordem_tipo = {
        TIPO_BASE_LEGAL_ARTIGO: 0,
        TIPO_BASE_LEGAL_INCISO: 1,
        TIPO_BASE_LEGAL_ALINEA: 2,
    }
    itens.sort(
        key=lambda item: (
            str(item.get("lei_nome") or "").lower(),
            int(item.get("artigo_id") or 0),
            int(item.get("inciso_id") or 0),
            int(item.get("alinea_id") or 0),
            ordem_tipo.get(str(item.get("tipo") or ""), 9),
            int(item.get("id") or 0),
        )
    )
    return itens


def _garantir_colunas_ocorrencia_regimento_itens(cursor):
    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = 'ocorrencia_regimento_itens'
    """)
    if not cursor.fetchone():
        return

    cursor.execute("PRAGMA table_info(ocorrencia_regimento_itens)")
    colunas = {row["name"] for row in cursor.fetchall()}
    if "artigo_id" not in colunas:
        cursor.execute("ALTER TABLE ocorrencia_regimento_itens ADD COLUMN artigo_id INTEGER")
    if "inciso_id" not in colunas:
        cursor.execute("ALTER TABLE ocorrencia_regimento_itens ADD COLUMN inciso_id INTEGER")
    if "alinea_id" not in colunas:
        cursor.execute("ALTER TABLE ocorrencia_regimento_itens ADD COLUMN alinea_id INTEGER")
    if "lei_nome" not in colunas:
        cursor.execute("ALTER TABLE ocorrencia_regimento_itens ADD COLUMN lei_nome TEXT")
    if "artigo_numero" not in colunas:
        cursor.execute("ALTER TABLE ocorrencia_regimento_itens ADD COLUMN artigo_numero TEXT")
    if "artigo_descricao" not in colunas:
        cursor.execute("ALTER TABLE ocorrencia_regimento_itens ADD COLUMN artigo_descricao TEXT")
    if "inciso_numero" not in colunas:
        cursor.execute("ALTER TABLE ocorrencia_regimento_itens ADD COLUMN inciso_numero TEXT")
    if "inciso_descricao" not in colunas:
        cursor.execute("ALTER TABLE ocorrencia_regimento_itens ADD COLUMN inciso_descricao TEXT")
    if "alinea_identificador" not in colunas:
        cursor.execute(
            "ALTER TABLE ocorrencia_regimento_itens ADD COLUMN alinea_identificador TEXT"
        )
    if "alinea_descricao" not in colunas:
        cursor.execute("ALTER TABLE ocorrencia_regimento_itens ADD COLUMN alinea_descricao TEXT")

    # Bancos antigos vinculavam regimento_item_id a regimento_itens; os IDs atuais
    # codificam artigos/incisos/alineas e precisam de um snapshot sem essa FK legada.
    if _ocorrencia_regimento_itens_tem_fk_legada(cursor):
        _recriar_tabela_ocorrencia_regimento_itens_sem_fk_legada(cursor)


def _garantir_tabelas_ocorrencia_vinculados(cursor):
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
    _migrar_vinculos_ocorrencias_legados(cursor)


def _migrar_vinculos_ocorrencias_legados(cursor):
    cursor.execute("""
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
        WHERE o.tipo_registro = ?
          AND TRIM(COALESCE(o.nome_estudante, '')) <> ''
          AND NOT EXISTS (
              SELECT 1
              FROM ocorrencia_estudantes oe
              WHERE oe.ocorrencia_id = o.id
          )
    """, (TIPO_REGISTRO_OCORRENCIA_ESTUDANTE,))

    cursor.execute("""
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
        WHERE o.tipo_registro = ?
          AND TRIM(COALESCE(o.professor_requerente, '')) <> ''
          AND NOT EXISTS (
              SELECT 1
              FROM ocorrencia_professores op
              WHERE op.ocorrencia_id = o.id
          )
    """, (TIPO_REGISTRO_OCORRENCIA_PROFESSOR,))


def _ocorrencia_regimento_itens_tem_fk_legada(cursor) -> bool:
    cursor.execute("PRAGMA foreign_key_list(ocorrencia_regimento_itens)")
    return any(
        str(row["from"] or "") == "regimento_item_id"
        and str(row["table"] or "") == "regimento_itens"
        for row in cursor.fetchall()
    )


def _recriar_tabela_ocorrencia_regimento_itens_sem_fk_legada(cursor):
    cursor.execute("DROP TABLE IF EXISTS ocorrencia_regimento_itens__tmp")
    cursor.execute("""
        CREATE TABLE ocorrencia_regimento_itens__tmp (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ocorrencia_id INTEGER NOT NULL,
            regimento_item_id INTEGER,
            artigo_id INTEGER,
            inciso_id INTEGER,
            alinea_id INTEGER,
            lei_nome TEXT,
            artigo_numero TEXT,
            artigo_descricao TEXT,
            inciso_numero TEXT,
            inciso_descricao TEXT,
            alinea_identificador TEXT,
            alinea_descricao TEXT,
            artigo TEXT NOT NULL,
            descricao TEXT NOT NULL,
            ordem INTEGER NOT NULL DEFAULT 0,
            criado_em TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(ocorrencia_id) REFERENCES ocorrencias(id),
            FOREIGN KEY(artigo_id) REFERENCES artigos(id),
            FOREIGN KEY(inciso_id) REFERENCES incisos(id),
            FOREIGN KEY(alinea_id) REFERENCES alineas(id)
        )
    """)
    cursor.execute("""
        INSERT INTO ocorrencia_regimento_itens__tmp (
            id,
            ocorrencia_id,
            regimento_item_id,
            artigo_id,
            inciso_id,
            alinea_id,
            lei_nome,
            artigo_numero,
            artigo_descricao,
            inciso_numero,
            inciso_descricao,
            alinea_identificador,
            alinea_descricao,
            artigo,
            descricao,
            ordem,
            criado_em
        )
        SELECT
            id,
            ocorrencia_id,
            regimento_item_id,
            CASE WHEN artigo_id IN (SELECT id FROM artigos) THEN artigo_id ELSE NULL END,
            CASE WHEN inciso_id IN (SELECT id FROM incisos) THEN inciso_id ELSE NULL END,
            CASE WHEN alinea_id IN (SELECT id FROM alineas) THEN alinea_id ELSE NULL END,
            lei_nome,
            artigo_numero,
            artigo_descricao,
            inciso_numero,
            inciso_descricao,
            alinea_identificador,
            alinea_descricao,
            COALESCE(NULLIF(TRIM(COALESCE(artigo, '')), ''), 'Base legal'),
            COALESCE(NULLIF(TRIM(COALESCE(descricao, '')), ''), 'Sem descricao.'),
            COALESCE(ordem, 0),
            COALESCE(NULLIF(TRIM(COALESCE(criado_em, '')), ''), datetime('now'))
        FROM ocorrencia_regimento_itens
        WHERE ocorrencia_id IN (SELECT id FROM ocorrencias)
    """)
    cursor.execute("DROP TABLE ocorrencia_regimento_itens")
    cursor.execute(
        "ALTER TABLE ocorrencia_regimento_itens__tmp RENAME TO ocorrencia_regimento_itens"
    )


def _migrar_base_legal_legado(cursor):
    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = 'regimento_itens'
    """)
    if not cursor.fetchone():
        return

    cursor.execute("""
        SELECT id, artigo, descricao
        FROM regimento_itens
        ORDER BY id ASC
    """)
    itens_legados = cursor.fetchall()
    if not itens_legados:
        return

    lei_id, _ = _obter_ou_criar_lei_cursor(cursor, LEI_PADRAO_MIGRACAO)
    mapa_ids_legados: dict[int, tuple[int, int]] = {}
    for row in itens_legados:
        artigo_id, _ = _obter_ou_criar_artigo_cursor(
            cursor,
            lei_id=lei_id,
            numero=str(row["artigo"] or "").strip() or f"Item {int(row['id'])}",
            descricao=str(row["descricao"] or "").strip() or "Sem descricao.",
        )
        mapa_ids_legados[int(row["id"])] = (
            _codificar_regimento_item_id(TIPO_BASE_LEGAL_ARTIGO, artigo_id),
            artigo_id,
        )

    for regimento_item_id_legado, (item_id_novo, artigo_id_novo) in mapa_ids_legados.items():
        cursor.execute(
            """
            UPDATE ocorrencia_regimento_itens
            SET regimento_item_id = ?,
                artigo_id = COALESCE(artigo_id, ?)
            WHERE regimento_item_id = ?
              AND (artigo_id IS NULL OR artigo_id <= 0)
        """,
            (item_id_novo, artigo_id_novo, regimento_item_id_legado),
        )


def _mapear_regimento_itens_por_ocorrencia(
    cursor, ocorrencia_ids: list[int]
) -> dict[int, list[dict]]:
    ids_validos = [int(ocorrencia_id) for ocorrencia_id in ocorrencia_ids if int(ocorrencia_id) > 0]
    if not ids_validos:
        return {}

    placeholders = ",".join(["?"] * len(ids_validos))
    cursor.execute(
        f"""
        SELECT
            ori.ocorrencia_id,
            ori.regimento_item_id,
            COALESCE(ori.artigo_id, a.id) AS artigo_id,
            COALESCE(ori.inciso_id, i.id) AS inciso_id,
            COALESCE(ori.alinea_id, al.id) AS alinea_id,
            CASE
                WHEN COALESCE(ori.alinea_id, al.id) IS NOT NULL THEN ?
                WHEN COALESCE(ori.inciso_id, i.id) IS NOT NULL THEN ?
                ELSE ?
            END AS tipo,
            COALESCE(NULLIF(TRIM(COALESCE(ori.lei_nome, '')), ''), l.nome, '') AS lei_nome,
            COALESCE(NULLIF(TRIM(COALESCE(ori.artigo_numero, '')), ''), a.numero, '') AS artigo_numero,
            COALESCE(NULLIF(TRIM(COALESCE(ori.artigo_descricao, '')), ''), a.descricao, '') AS artigo_descricao,
            COALESCE(NULLIF(TRIM(COALESCE(ori.inciso_numero, '')), ''), i.numero, '') AS inciso_numero,
            COALESCE(NULLIF(TRIM(COALESCE(ori.inciso_descricao, '')), ''), i.descricao, '') AS inciso_descricao,
            COALESCE(NULLIF(TRIM(COALESCE(ori.alinea_identificador, '')), ''), al.identificador, '') AS alinea_identificador,
            COALESCE(NULLIF(TRIM(COALESCE(ori.alinea_descricao, '')), ''), al.descricao, '') AS alinea_descricao,
            ori.artigo,
            ori.descricao,
            ori.ordem
        FROM ocorrencia_regimento_itens ori
        LEFT JOIN alineas al ON al.id = ori.alinea_id
        LEFT JOIN incisos i ON i.id = COALESCE(ori.inciso_id, al.inciso_id)
        LEFT JOIN artigos a ON a.id = COALESCE(ori.artigo_id, i.artigo_id)
        LEFT JOIN leis l ON l.id = a.lei_id
        WHERE ori.ocorrencia_id IN ({placeholders})
        ORDER BY ori.ocorrencia_id ASC, ori.ordem ASC, ori.id ASC
    """,
        [TIPO_BASE_LEGAL_ALINEA, TIPO_BASE_LEGAL_INCISO, TIPO_BASE_LEGAL_ARTIGO, *ids_validos],
    )

    mapa: dict[int, list[dict]] = {}
    for row in cursor.fetchall():
        ocorrencia_id = int(row["ocorrencia_id"])
        mapa.setdefault(ocorrencia_id, []).append(
            {
                "regimento_item_id": int(row["regimento_item_id"])
                if row["regimento_item_id"] is not None
                else None,
                "tipo": str(row["tipo"] or "").strip() or None,
                "artigo_id": int(row["artigo_id"]) if row["artigo_id"] is not None else None,
                "inciso_id": int(row["inciso_id"]) if row["inciso_id"] is not None else None,
                "alinea_id": int(row["alinea_id"]) if row["alinea_id"] is not None else None,
                "lei_nome": str(row["lei_nome"] or "").strip() or None,
                "artigo_numero": str(row["artigo_numero"] or "").strip() or None,
                "artigo_descricao": str(row["artigo_descricao"] or "").strip() or None,
                "inciso_numero": str(row["inciso_numero"] or "").strip() or None,
                "inciso_descricao": str(row["inciso_descricao"] or "").strip() or None,
                "alinea_identificador": str(row["alinea_identificador"] or "").strip() or None,
                "alinea_descricao": str(row["alinea_descricao"] or "").strip() or None,
                "artigo": str(row["artigo"] or "").strip(),
                "descricao": str(row["descricao"] or "").strip(),
                "ordem": int(row["ordem"] or 0),
            }
        )
    return mapa


def _anexar_regimento_itens_ocorrencias(cursor, ocorrencias: list[dict]) -> list[dict]:
    if not ocorrencias:
        return ocorrencias

    mapa = _mapear_regimento_itens_por_ocorrencia(
        cursor,
        [int(ocorrencia.get("id") or 0) for ocorrencia in ocorrencias],
    )
    for ocorrencia in ocorrencias:
        ocorrencia_id = int(ocorrencia.get("id") or 0)
        ocorrencia["regimento_itens"] = mapa.get(ocorrencia_id, [])
    return ocorrencias


def _mapear_estudantes_vinculados_por_ocorrencia(
    cursor, ocorrencia_ids: list[int]
) -> dict[int, list[dict]]:
    ids_validos = [int(ocorrencia_id) for ocorrencia_id in ocorrencia_ids if int(ocorrencia_id or 0) > 0]
    if not ids_validos:
        return {}

    placeholders = ",".join("?" for _ in ids_validos)
    cursor.execute(
        f"""
        SELECT
            oe.ocorrencia_id,
            oe.estudante_id,
            oe.nome_estudante,
            oe.turma_id,
            COALESCE(NULLIF(TRIM(COALESCE(oe.turma_nome, '')), ''), t.nome, '') AS turma_nome,
            oe.ordem
        FROM ocorrencia_estudantes oe
        LEFT JOIN turmas t ON t.id = oe.turma_id
        WHERE oe.ocorrencia_id IN ({placeholders})
        ORDER BY oe.ocorrencia_id ASC, oe.ordem ASC, oe.id ASC
    """,
        ids_validos,
    )

    mapa: dict[int, list[dict]] = {}
    for row in cursor.fetchall():
        ocorrencia_id = int(row["ocorrencia_id"] or 0)
        mapa.setdefault(ocorrencia_id, []).append(
            {
                "estudante_id": int(row["estudante_id"]) if row["estudante_id"] is not None else None,
                "nome": str(row["nome_estudante"] or "").strip(),
                "turma_id": int(row["turma_id"]) if row["turma_id"] is not None else None,
                "turma_nome": str(row["turma_nome"] or "").strip(),
            }
        )
    return mapa


def _mapear_professores_vinculados_por_ocorrencia(
    cursor, ocorrencia_ids: list[int]
) -> dict[int, list[dict]]:
    ids_validos = [int(ocorrencia_id) for ocorrencia_id in ocorrencia_ids if int(ocorrencia_id or 0) > 0]
    if not ids_validos:
        return {}

    placeholders = ",".join("?" for _ in ids_validos)
    cursor.execute(
        f"""
        SELECT
            op.ocorrencia_id,
            op.professor_usuario_id,
            op.nome_professor,
            COALESCE(NULLIF(TRIM(COALESCE(op.email_professor, '')), ''), u.email, '') AS email_professor,
            op.ordem
        FROM ocorrencia_professores op
        LEFT JOIN usuarios u ON u.id = op.professor_usuario_id
        WHERE op.ocorrencia_id IN ({placeholders})
        ORDER BY op.ocorrencia_id ASC, op.ordem ASC, op.id ASC
    """,
        ids_validos,
    )

    mapa: dict[int, list[dict]] = {}
    for row in cursor.fetchall():
        ocorrencia_id = int(row["ocorrencia_id"] or 0)
        mapa.setdefault(ocorrencia_id, []).append(
            {
                "professor_id": (
                    int(row["professor_usuario_id"])
                    if row["professor_usuario_id"] is not None
                    else None
                ),
                "nome": str(row["nome_professor"] or "").strip(),
                "email": str(row["email_professor"] or "").strip(),
            }
        )
    return mapa


def _anexar_vinculados_ocorrencias(cursor, ocorrencias: list[dict]) -> list[dict]:
    if not ocorrencias:
        return ocorrencias

    ocorrencia_ids = [int(ocorrencia.get("id") or 0) for ocorrencia in ocorrencias]
    mapa_estudantes = _mapear_estudantes_vinculados_por_ocorrencia(cursor, ocorrencia_ids)
    mapa_professores = _mapear_professores_vinculados_por_ocorrencia(cursor, ocorrencia_ids)

    for ocorrencia in ocorrencias:
        ocorrencia_id = int(ocorrencia.get("id") or 0)
        ocorrencia["estudantes_vinculados"] = mapa_estudantes.get(ocorrencia_id, [])
        ocorrencia["professores_vinculados"] = mapa_professores.get(ocorrencia_id, [])
    return ocorrencias


def _garantir_view_radcheck(cursor):
    # O sistema usa email como identificador de login para autenticação.
    # Se existir coluna `ativo`, a VIEW inclui apenas usuários ativos.
    cursor.execute("DROP VIEW IF EXISTS radcheck")
    cursor.execute("PRAGMA table_info(usuarios)")
    colunas = {row["name"] for row in cursor.fetchall()}
    filtro_ativo = ""
    if "ativo" in colunas:
        filtro_ativo = " AND (ativo = 1 OR LOWER(CAST(ativo AS TEXT)) = 'true')"

    cursor.execute(f"""
        CREATE VIEW radcheck AS
        SELECT
            email AS username,
            'NT-Password' AS attribute,
            ':=' AS op,
            nt_hash AS value
        FROM usuarios
        WHERE TRIM(COALESCE(email, '')) <> ''
          AND TRIM(COALESCE(nt_hash, '')) <> ''
          {filtro_ativo}
    """)


def salvar_token(token: str, usuario_id: int, expira_em: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO tokens (token, usuario_id, criado_em, expira_em)
        VALUES (?, ?, datetime('now'), ?)
    """,
        (token, usuario_id, expira_em),
    )

    conn.commit()
    conn.close()


def limpar_tokens_expirados():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM tokens
        WHERE TRIM(COALESCE(expira_em, '')) = ''
           OR expira_em <= datetime('now')
    """)

    conn.commit()
    conn.close()


def revogar_tokens_usuario(usuario_id: int) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        DELETE FROM tokens
        WHERE usuario_id = ?
    """,
        (usuario_id,),
    )
    removidos = cursor.rowcount
    conn.commit()
    conn.close()
    return removidos


def buscar_usuario_por_token(token: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"""
        SELECT u.id, u.nome, u.email, u.perfil, u.cargo, u.acesso_coordenacao
        FROM usuarios u
        JOIN tokens t ON u.id = t.usuario_id
        WHERE t.token = ?
          AND t.expira_em > datetime('now')
          AND {_clausula_usuario_ativo("u")}
    """,
        (token,),
    )

    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


# hash para senhas
def hash_senha(senha: str):
    return hashlib.sha256(senha.encode()).hexdigest()


def _normalizar_nt_hash(nt_hash: str | None) -> str | None:
    if nt_hash is None:
        return None
    valor = str(nt_hash).strip().lower()
    if len(valor) != 32:
        return None
    if any(char not in "0123456789abcdef" for char in valor):
        return None
    return valor


def criar_usuario(nome, email, senha, perfil, cargo: str = ""):
    conn = get_connection()
    cursor = conn.cursor()
    cargo_norm = str(cargo or "").strip().upper() or _cargo_padrao_por_perfil(perfil)
    nt_hash = generate_nt_hash(senha)

    cursor.execute(
        """
        INSERT INTO usuarios (nome, email, senha_hash, nt_hash, perfil, cargo)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
        (nome, email, hash_senha(senha), nt_hash, perfil, cargo_norm),
    )

    conn.commit()
    conn.close()


def buscar_usuario_por_email(email, incluir_inativos: bool = False):
    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM usuarios WHERE email = ?"
    if not incluir_inativos:
        query += f" AND {_clausula_usuario_ativo()}"

    cursor.execute(query, (email,))

    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def buscar_usuario_por_id(usuario_id: int, incluir_inativos: bool = False):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT id, nome, email, perfil, cargo, acesso_coordenacao, data_nascimento, ativo
        FROM usuarios
        WHERE id = ?
    """
    if not incluir_inativos:
        query += f" AND {_clausula_usuario_ativo()}"

    cursor.execute(query, (usuario_id,))

    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def criar_usuario_se_nao_existir(
    nome,
    email,
    senha_hash,
    perfil,
    cargo: str = "",
    senha_plana: str | None = None,
    nt_hash: str | None = None,
):
    usuario = buscar_usuario_por_email(email, incluir_inativos=True)
    if usuario:
        return

    conn = get_connection()
    cursor = conn.cursor()
    cargo_norm = str(cargo or "").strip().upper() or _cargo_padrao_por_perfil(perfil)
    nt_hash_final = _normalizar_nt_hash(nt_hash)
    if nt_hash_final is None and senha_plana is not None:
        nt_hash_final = generate_nt_hash(senha_plana)

    cursor.execute(
        """
        INSERT INTO usuarios (nome, email, senha_hash, nt_hash, perfil, cargo)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
        (nome, email, senha_hash, nt_hash_final, perfil, cargo_norm),
    )

    conn.commit()
    conn.close()


def _serializar_lista_texto(valores):
    if not valores:
        return "[]"

    normalizados = []
    for valor in valores:
        texto = str(valor).strip()
        if texto and texto not in normalizados:
            normalizados.append(texto)
    return json.dumps(normalizados, ensure_ascii=False)


def _desserializar_lista_texto(valor):
    if not valor:
        return []
    try:
        dados = json.loads(valor)
    except (TypeError, json.JSONDecodeError):
        return []
    if not isinstance(dados, list):
        return []

    normalizados = []
    for item in dados:
        texto = str(item).strip()
        if texto and texto not in normalizados:
            normalizados.append(texto)
    return normalizados


def _normalizar_booleano_tristate(valor):
    if valor is None:
        return None

    if isinstance(valor, bool):
        return valor

    texto = str(valor).strip().lower()
    if not texto:
        return None
    if texto in {"1", "true", "t", "sim"}:
        return True
    if texto in {"0", "false", "f", "nao", "não"}:
        return False

    try:
        return bool(int(valor))
    except (TypeError, ValueError):
        return None


def _normalizar_texto_chave(valor: str) -> str:
    texto = str(valor or "").strip().lower()
    sem_acentos = "".join(
        caractere
        for caractere in unicodedata.normalize("NFD", texto)
        if unicodedata.category(caractere) != "Mn"
    )
    return " ".join(sem_acentos.split())


def _obter_multiplicador_disciplina(nome_disciplina: str) -> float:
    chave = _normalizar_texto_chave(nome_disciplina)
    if chave in DISCIPLINAS_MULTIPLICADOR_ALTO:
        return 1.2
    if chave in DISCIPLINAS_MULTIPLICADOR_BAIXO:
        return 0.8
    return 1.0


def criar_professor(
    nome: str,
    email: str,
    senha_hash: str,
    nt_hash: str | None = None,
    data_nascimento: str = "",
    aulas_semanais: int = 0,
    turmas_quantidade: int = 0,
    turmas: list[str] = None,
    disciplinas: list[str] = None,
    acesso_coordenacao: bool = False,
):
    conn = get_connection()
    cursor = conn.cursor()

    turmas_json = _serializar_lista_texto(turmas)
    disciplinas_json = _serializar_lista_texto(disciplinas)
    nt_hash_final = _normalizar_nt_hash(nt_hash)

    cursor.execute(
        """
        INSERT INTO usuarios (
            nome,
            email,
            senha_hash,
            nt_hash,
            perfil,
            cargo,
            acesso_coordenacao,
            data_nascimento
        )
        VALUES (?, ?, ?, ?, 'professor', ?, ?, ?)
    """,
        (
            nome,
            email,
            senha_hash,
            nt_hash_final,
            CARGO_PROFESSOR,
            _normalizar_booleano_sql(acesso_coordenacao),
            data_nascimento or None,
        ),
    )

    usuario_id = cursor.lastrowid
    cursor.execute(
        """
        INSERT INTO professores_carga (
            usuario_id, aulas_semanais, turmas_quantidade, turmas, disciplinas, atualizado_em
        )
        VALUES (?, ?, ?, ?, ?, datetime('now'))
    """,
        (usuario_id, aulas_semanais, turmas_quantidade, turmas_json, disciplinas_json),
    )

    conn.commit()
    conn.close()
    return usuario_id


def atualizar_professor(
    usuario_id: int,
    nome: str,
    email: str,
    data_nascimento: str = "",
    aulas_semanais: int = 0,
    turmas_quantidade: int = 0,
    turmas: list[str] = None,
    disciplinas: list[str] = None,
    acesso_coordenacao: bool = False,
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id
        FROM usuarios
        WHERE id = ? AND perfil = 'professor'
    """,
        (usuario_id,),
    )
    if not cursor.fetchone():
        conn.close()
        return False

    turmas_json = _serializar_lista_texto(turmas)
    disciplinas_json = _serializar_lista_texto(disciplinas)

    cursor.execute(
        """
        UPDATE usuarios
        SET nome = ?, email = ?, cargo = ?, acesso_coordenacao = ?, data_nascimento = ?
        WHERE id = ?
    """,
        (
            nome,
            email,
            CARGO_PROFESSOR,
            _normalizar_booleano_sql(acesso_coordenacao),
            data_nascimento or None,
            usuario_id,
        ),
    )

    cursor.execute(
        """
        INSERT INTO professores_carga (
            usuario_id, aulas_semanais, turmas_quantidade, turmas, disciplinas, atualizado_em
        )
        VALUES (?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(usuario_id) DO UPDATE SET
            aulas_semanais = excluded.aulas_semanais,
            turmas_quantidade = excluded.turmas_quantidade,
            turmas = excluded.turmas,
            disciplinas = excluded.disciplinas,
            atualizado_em = datetime('now')
    """,
        (
            usuario_id,
            aulas_semanais,
            turmas_quantidade,
            turmas_json,
            disciplinas_json,
        ),
    )

    conn.commit()
    conn.close()
    return True


def criar_coordenador(
    nome: str,
    email: str,
    senha_hash: str,
    nt_hash: str | None = None,
    data_nascimento: str = "",
):
    conn = get_connection()
    cursor = conn.cursor()
    nt_hash_final = _normalizar_nt_hash(nt_hash)

    cursor.execute(
        """
        INSERT INTO usuarios (nome, email, senha_hash, nt_hash, perfil, cargo, data_nascimento)
        VALUES (?, ?, ?, ?, 'coordenador', ?, ?)
    """,
        (nome, email, senha_hash, nt_hash_final, CARGO_COORDENADOR, data_nascimento or None),
    )

    usuario_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return usuario_id


def promover_professor_para_coordenador(usuario_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id
        FROM usuarios
        WHERE id = ?
          AND perfil = 'professor'
          AND ativo = 1
    """,
        (usuario_id,),
    )
    if not cursor.fetchone():
        conn.close()
        return False

    cursor.execute(
        """
        UPDATE usuarios
        SET perfil = 'coordenador',
            cargo = ?,
            acesso_coordenacao = 0
        WHERE id = ?
    """,
        (CARGO_COORDENADOR, usuario_id),
    )

    conn.commit()
    conn.close()
    return cursor.rowcount > 0


def listar_coordenadores_admin():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"""
        SELECT id, nome, email, data_nascimento
        FROM usuarios
        WHERE UPPER(COALESCE(cargo, '')) = ?
          AND {_clausula_usuario_ativo()}
        ORDER BY nome ASC
    """,
        (CARGO_COORDENADOR,),
    )

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def atualizar_nt_hash_usuario(usuario_id: int, nt_hash: str):
    nt_hash_final = _normalizar_nt_hash(nt_hash)
    if not nt_hash_final:
        return False

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE usuarios
        SET nt_hash = ?
        WHERE id = ?
    """,
        (nt_hash_final, usuario_id),
    )
    alterado = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return alterado


def preencher_nt_hash_se_ausente(usuario_id: int, senha_em_texto: str):
    nt_hash = generate_nt_hash(senha_em_texto)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE usuarios
        SET nt_hash = ?
        WHERE id = ?
          AND TRIM(COALESCE(nt_hash, '')) = ''
    """,
        (nt_hash, usuario_id),
    )
    alterado = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return alterado


def atualizar_senha_usuario(usuario_id: int, senha_em_texto: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE usuarios
        SET senha_hash = ?, nt_hash = ?
        WHERE id = ?
    """,
        (hash_senha(senha_em_texto), generate_nt_hash(senha_em_texto), usuario_id),
    )
    alterado = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return alterado


def desativar_professor(usuario_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"""
        UPDATE usuarios
        SET ativo = 0
        WHERE id = ?
          AND perfil = 'professor'
          AND {_clausula_usuario_ativo()}
    """,
        (usuario_id,),
    )
    alterado = cursor.rowcount > 0

    if alterado:
        cursor.execute(
            """
            DELETE FROM tokens
            WHERE usuario_id = ?
        """,
            (usuario_id,),
        )

    conn.commit()
    conn.close()
    return alterado


def salvar_carga_professor(usuario_id: int, aulas_semanais: int, turmas_quantidade: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO professores_carga (usuario_id, aulas_semanais, turmas_quantidade, atualizado_em)
        VALUES (?, ?, ?, datetime('now'))
        ON CONFLICT(usuario_id) DO UPDATE SET
            aulas_semanais = excluded.aulas_semanais,
            turmas_quantidade = excluded.turmas_quantidade,
            atualizado_em = datetime('now')
    """,
        (usuario_id, aulas_semanais, turmas_quantidade),
    )

    conn.commit()
    conn.close()


def _normalizar_professor_usuario_id(valor) -> int | None:
    try:
        professor_id = int(valor or 0)
    except (TypeError, ValueError):
        return None
    return professor_id if professor_id > 0 else None


def _obter_carga_horaria_base_disciplina(cursor, disciplina_id: int) -> int:
    cursor.execute(
        """
        SELECT COALESCE(aulas_semanais, 0) AS aulas_semanais
        FROM disciplinas
        WHERE id = ?
    """,
        (int(disciplina_id),),
    )
    row = cursor.fetchone()
    return int((row["aulas_semanais"] if row else 0) or 0)


def _sincronizar_atribuicoes_docentes_por_turma_disciplina(
    cursor,
    *,
    turma_id: int,
    disciplina_id: int,
    professor_usuario_id: int | None,
):
    turma_id_valor = int(turma_id)
    disciplina_id_valor = int(disciplina_id)
    professor_id_valor = _normalizar_professor_usuario_id(professor_usuario_id)

    cursor.execute(
        """
        SELECT DISTINCT professor_usuario_id
        FROM professores_turmas_disciplinas
        WHERE turma_id = ?
          AND disciplina_id = ?
    """,
        (turma_id_valor, disciplina_id_valor),
    )
    professores_afetados = {
        int(row["professor_usuario_id"])
        for row in cursor.fetchall()
        if int(row["professor_usuario_id"] or 0) > 0
    }

    cursor.execute(
        """
        DELETE FROM professores_turmas_disciplinas
        WHERE turma_id = ?
          AND disciplina_id = ?
    """,
        (turma_id_valor, disciplina_id_valor),
    )

    if professor_id_valor is not None:
        cursor.execute(
            """
            INSERT OR IGNORE INTO professores_turmas_disciplinas (
                professor_usuario_id,
                turma_id,
                disciplina_id,
                criado_em
            )
            VALUES (?, ?, ?, datetime('now'))
        """,
            (professor_id_valor, turma_id_valor, disciplina_id_valor),
        )
        professores_afetados.add(professor_id_valor)

    for usuario_id in sorted(professores_afetados):
        _sincronizar_resumo_carga_professor(cursor, int(usuario_id))


def _upsert_turma_disciplina_cursor(
    cursor,
    *,
    turma_id: int,
    disciplina_id: int,
    carga_horaria: int | None = None,
    professor_usuario_id: int | None = None,
):
    turma_id_valor = int(turma_id)
    disciplina_id_valor = int(disciplina_id)
    professor_id_valor = _normalizar_professor_usuario_id(professor_usuario_id)

    cursor.execute(
        """
        SELECT id, carga_horaria, professor_usuario_id
        FROM turmas_disciplinas
        WHERE turma_id = ?
          AND disciplina_id = ?
        LIMIT 1
    """,
        (turma_id_valor, disciplina_id_valor),
    )
    existente = cursor.fetchone()

    if existente:
        carga_final = (
            int(carga_horaria)
            if carga_horaria is not None
            else int(existente["carga_horaria"] or 0)
        )
        if carga_horaria is None and carga_final <= 0:
            carga_final = _obter_carga_horaria_base_disciplina(cursor, disciplina_id_valor)
        cursor.execute(
            """
            UPDATE turmas_disciplinas
            SET carga_horaria = ?,
                professor_usuario_id = ?,
                atualizado_em = datetime('now')
            WHERE id = ?
        """,
            (carga_final, professor_id_valor, int(existente["id"])),
        )
        turma_disciplina_id = int(existente["id"])
        criado = False
    else:
        carga_final = (
            int(carga_horaria)
            if carga_horaria is not None
            else _obter_carga_horaria_base_disciplina(cursor, disciplina_id_valor)
        )
        cursor.execute(
            """
            INSERT INTO turmas_disciplinas (
                turma_id,
                disciplina_id,
                carga_horaria,
                professor_usuario_id,
                criado_em,
                atualizado_em
            )
            VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))
        """,
            (turma_id_valor, disciplina_id_valor, carga_final, professor_id_valor),
        )
        turma_disciplina_id = int(cursor.lastrowid)
        criado = True

    _sincronizar_atribuicoes_docentes_por_turma_disciplina(
        cursor,
        turma_id=turma_id_valor,
        disciplina_id=disciplina_id_valor,
        professor_usuario_id=professor_id_valor,
    )
    return turma_disciplina_id, criado


def _mapear_turma_disciplina_admin(row) -> dict:
    item = dict(row)
    professor_id = int(item.get("professor_usuario_id") or 0)
    return {
        "id": int(item["id"]),
        "turma_id": int(item["turma_id"]),
        "turma_nome": item.get("turma_nome", "") or "",
        "turno": item.get("turno", "") or "",
        "turma_ativa": bool(int(item.get("turma_ativa", 1) or 0)),
        "disciplina_id": int(item["disciplina_id"]),
        "disciplina_nome": item.get("disciplina_nome", "") or "",
        "disciplina_ativa": bool(int(item.get("disciplina_ativa", 1) or 0)),
        "tem_apc": bool(int(item.get("disciplina_tem_apc", 0) or 0)),
        "tem_prova_bimestral": bool(
            int(item.get("disciplina_tem_prova_bimestral", 0) or 0)
        ),
        "carga_horaria": int(item.get("carga_horaria") or 0),
        "carga_horaria_padrao": int(item.get("carga_horaria_padrao") or 0),
        "professor_id": professor_id if professor_id > 0 else None,
        "professor_nome": item.get("professor_nome", "") or "",
        "professor_email": item.get("professor_email", "") or "",
        "professor_ativo": bool(int(item.get("professor_ativo", 1) or 0))
        if professor_id > 0
        else True,
        "criado_em": item.get("criado_em", "") or "",
        "atualizado_em": item.get("atualizado_em", "") or "",
    }


def _consultar_turmas_disciplinas_admin(
    cursor,
    *,
    filtros_sql: list[str] | None = None,
    params: list | None = None,
    incluir_inativos: bool = False,
):
    where = list(filtros_sql or [])
    parametros = list(params or [])

    if not incluir_inativos:
        where.append("COALESCE(t.ativo, 1) = 1")
        where.append("COALESCE(d.ativo, 1) = 1")

    clausula_where = f"WHERE {' AND '.join(where)}" if where else ""
    cursor.execute(
        f"""
        SELECT
            td.id,
            td.turma_id,
            td.disciplina_id,
            td.carga_horaria,
            td.professor_usuario_id,
            td.criado_em,
            td.atualizado_em,
            t.nome AS turma_nome,
            t.turno AS turno,
            COALESCE(t.ativo, 1) AS turma_ativa,
            d.nome AS disciplina_nome,
            COALESCE(d.aulas_semanais, 0) AS carga_horaria_padrao,
            COALESCE(d.ativo, 1) AS disciplina_ativa,
            COALESCE(d.tem_apc, 0) AS disciplina_tem_apc,
            COALESCE(d.tem_prova_bimestral, 0) AS disciplina_tem_prova_bimestral,
            COALESCE(u.nome, '') AS professor_nome,
            COALESCE(u.email, '') AS professor_email,
            COALESCE(u.ativo, 1) AS professor_ativo
        FROM turmas_disciplinas td
        INNER JOIN turmas t ON t.id = td.turma_id
        INNER JOIN disciplinas d ON d.id = td.disciplina_id
        LEFT JOIN usuarios u ON u.id = td.professor_usuario_id
        {clausula_where}
        ORDER BY
            t.nome COLLATE NOCASE ASC,
            d.nome COLLATE NOCASE ASC,
            td.id ASC
        """,
        parametros,
    )
    return [_mapear_turma_disciplina_admin(row) for row in cursor.fetchall()]


def _mapear_atribuicao_docente(row) -> dict:
    item = dict(row)
    return {
        "id": int(item["id"]),
        "professor_id": int(item["professor_usuario_id"]),
        "professor_nome": item.get("professor_nome", "") or "",
        "professor_email": item.get("professor_email", "") or "",
        "professor_ativo": bool(int(item.get("professor_ativo", 1) or 0)),
        "turma_id": int(item["turma_id"]),
        "turma_nome": item.get("turma_nome", "") or "",
        "turno": item.get("turno", "") or "",
        "turma_ativa": bool(int(item.get("turma_ativa", 1) or 0)),
        "disciplina_id": int(item["disciplina_id"]),
        "disciplina_nome": item.get("disciplina_nome", "") or "",
        "disciplina_ativa": bool(int(item.get("disciplina_ativa", 1) or 0)),
        "criado_em": item.get("criado_em", "") or "",
    }


def _consultar_atribuicoes_docentes(
    cursor,
    *,
    filtros_sql: list[str] | None = None,
    params: list | None = None,
    incluir_inativos: bool = False,
):
    where = list(filtros_sql or [])
    parametros = list(params or [])

    if not incluir_inativos:
        where.append("COALESCE(u.ativo, 1) = 1")
        where.append("COALESCE(t.ativo, 1) = 1")
        where.append("COALESCE(d.ativo, 1) = 1")

    clausula_where = f"WHERE {' AND '.join(where)}" if where else ""
    cursor.execute(
        f"""
        SELECT
            ptd.id,
            ptd.professor_usuario_id,
            ptd.turma_id,
            ptd.disciplina_id,
            ptd.criado_em,
            u.nome AS professor_nome,
            u.email AS professor_email,
            COALESCE(u.ativo, 1) AS professor_ativo,
            t.nome AS turma_nome,
            t.turno AS turno,
            COALESCE(t.ativo, 1) AS turma_ativa,
            d.nome AS disciplina_nome,
            COALESCE(d.ativo, 1) AS disciplina_ativa
        FROM professores_turmas_disciplinas ptd
        JOIN usuarios u ON u.id = ptd.professor_usuario_id
        JOIN turmas t ON t.id = ptd.turma_id
        JOIN disciplinas d ON d.id = ptd.disciplina_id
        {clausula_where}
        ORDER BY
            u.nome COLLATE NOCASE ASC,
            t.nome COLLATE NOCASE ASC,
            d.nome COLLATE NOCASE ASC,
            ptd.id ASC
        """,
        parametros,
    )
    return [_mapear_atribuicao_docente(row) for row in cursor.fetchall()]


def _sincronizar_resumo_carga_professor(cursor, usuario_id: int):
    cursor.execute(
        """
        SELECT COALESCE(aulas_semanais, 0) AS aulas_semanais
        FROM professores_carga
        WHERE usuario_id = ?
        """,
        (int(usuario_id),),
    )
    row_carga = cursor.fetchone()
    aulas_semanais = int((dict(row_carga).get("aulas_semanais") if row_carga else 0) or 0)

    atribuicoes = _consultar_atribuicoes_docentes(
        cursor,
        filtros_sql=["ptd.professor_usuario_id = ?"],
        params=[int(usuario_id)],
        incluir_inativos=False,
    )

    turmas = []
    disciplinas = []
    for atribuicao in atribuicoes:
        turma_nome = str(atribuicao.get("turma_nome") or "").strip()
        disciplina_nome = str(atribuicao.get("disciplina_nome") or "").strip()
        if turma_nome and turma_nome not in turmas:
            turmas.append(turma_nome)
        if disciplina_nome and disciplina_nome not in disciplinas:
            disciplinas.append(disciplina_nome)

    cursor.execute(
        """
        INSERT INTO professores_carga (
            usuario_id,
            aulas_semanais,
            turmas_quantidade,
            turmas,
            disciplinas,
            atualizado_em
        )
        VALUES (?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(usuario_id) DO UPDATE SET
            aulas_semanais = excluded.aulas_semanais,
            turmas_quantidade = excluded.turmas_quantidade,
            turmas = excluded.turmas,
            disciplinas = excluded.disciplinas,
            atualizado_em = datetime('now')
        """,
        (
            int(usuario_id),
            aulas_semanais,
            len(turmas),
            json.dumps(turmas, ensure_ascii=False),
            json.dumps(disciplinas, ensure_ascii=False),
        ),
    )


def buscar_atribuicao_docente_por_id(atribuicao_id: int, incluir_inativos: bool = True):
    conn = get_connection()
    cursor = conn.cursor()
    itens = _consultar_atribuicoes_docentes(
        cursor,
        filtros_sql=["ptd.id = ?"],
        params=[int(atribuicao_id)],
        incluir_inativos=incluir_inativos,
    )
    conn.close()
    return itens[0] if itens else None


def listar_atribuicoes_docentes(
    professor_id: int | None = None,
    turma_id: int | None = None,
    disciplina_id: int | None = None,
    *,
    incluir_inativos: bool = True,
):
    conn = get_connection()
    cursor = conn.cursor()
    filtros = []
    params = []

    if professor_id is not None:
        filtros.append("ptd.professor_usuario_id = ?")
        params.append(int(professor_id))
    if turma_id is not None:
        filtros.append("ptd.turma_id = ?")
        params.append(int(turma_id))
    if disciplina_id is not None:
        filtros.append("ptd.disciplina_id = ?")
        params.append(int(disciplina_id))

    itens = _consultar_atribuicoes_docentes(
        cursor,
        filtros_sql=filtros,
        params=params,
        incluir_inativos=incluir_inativos,
    )
    conn.close()
    return itens


def listar_atribuicoes_docentes_por_usuario_ids(
    usuario_ids: list[int],
    *,
    incluir_inativos: bool = False,
):
    ids_unicos = []
    for usuario_id in usuario_ids or []:
        try:
            valor = int(usuario_id)
        except (TypeError, ValueError):
            continue
        if valor > 0 and valor not in ids_unicos:
            ids_unicos.append(valor)

    if not ids_unicos:
        return {}

    placeholders = ",".join("?" for _ in ids_unicos)
    conn = get_connection()
    cursor = conn.cursor()
    itens = _consultar_atribuicoes_docentes(
        cursor,
        filtros_sql=[f"ptd.professor_usuario_id IN ({placeholders})"],
        params=ids_unicos,
        incluir_inativos=incluir_inativos,
    )
    conn.close()

    atribuicoes = {usuario_id: [] for usuario_id in ids_unicos}
    for item in itens:
        atribuicoes.setdefault(int(item["professor_id"]), []).append(item)
    return atribuicoes


def listar_turmas_disciplinas_admin(
    *,
    turma_id: int | None = None,
    disciplina_id: int | None = None,
    professor_id: int | None = None,
    incluir_inativos: bool = True,
):
    conn = get_connection()
    cursor = conn.cursor()
    filtros = []
    params = []

    if turma_id is not None:
        filtros.append("td.turma_id = ?")
        params.append(int(turma_id))
    if disciplina_id is not None:
        filtros.append("td.disciplina_id = ?")
        params.append(int(disciplina_id))
    if professor_id is not None:
        filtros.append("COALESCE(td.professor_usuario_id, 0) = ?")
        params.append(int(professor_id))

    itens = _consultar_turmas_disciplinas_admin(
        cursor,
        filtros_sql=filtros,
        params=params,
        incluir_inativos=incluir_inativos,
    )
    conn.close()
    return itens


def buscar_turma_disciplina_por_id(turma_disciplina_id: int, *, incluir_inativos: bool = True):
    conn = get_connection()
    cursor = conn.cursor()
    itens = _consultar_turmas_disciplinas_admin(
        cursor,
        filtros_sql=["td.id = ?"],
        params=[int(turma_disciplina_id)],
        incluir_inativos=incluir_inativos,
    )
    conn.close()
    return itens[0] if itens else None


def criar_ou_atualizar_turma_disciplina(
    *,
    turma_id: int,
    disciplina_id: int,
    carga_horaria: int,
    professor_usuario_id: int | None = None,
):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        turma_disciplina_id, _ = _upsert_turma_disciplina_cursor(
            cursor,
            turma_id=int(turma_id),
            disciplina_id=int(disciplina_id),
            carga_horaria=int(carga_horaria),
            professor_usuario_id=professor_usuario_id,
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return buscar_turma_disciplina_por_id(turma_disciplina_id, incluir_inativos=True)


def atualizar_turma_disciplina(
    turma_disciplina_id: int,
    *,
    carga_horaria: int,
    professor_usuario_id: int | None = None,
):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT turma_id, disciplina_id
        FROM turmas_disciplinas
        WHERE id = ?
    """,
        (int(turma_disciplina_id),),
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None

    try:
        _upsert_turma_disciplina_cursor(
            cursor,
            turma_id=int(row["turma_id"]),
            disciplina_id=int(row["disciplina_id"]),
            carga_horaria=int(carga_horaria),
            professor_usuario_id=professor_usuario_id,
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return buscar_turma_disciplina_por_id(int(turma_disciplina_id), incluir_inativos=True)


def excluir_turma_disciplina(turma_disciplina_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT turma_id, disciplina_id
        FROM turmas_disciplinas
        WHERE id = ?
    """,
        (int(turma_disciplina_id),),
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False

    turma_id = int(row["turma_id"])
    disciplina_id = int(row["disciplina_id"])

    cursor.execute(
        """
        SELECT DISTINCT professor_usuario_id
        FROM professores_turmas_disciplinas
        WHERE turma_id = ?
          AND disciplina_id = ?
    """,
        (turma_id, disciplina_id),
    )
    professores_afetados = {
        int(item["professor_usuario_id"])
        for item in cursor.fetchall()
        if int(item["professor_usuario_id"] or 0) > 0
    }

    cursor.execute(
        """
        DELETE FROM turmas_disciplinas
        WHERE id = ?
    """,
        (int(turma_disciplina_id),),
    )
    alterado = cursor.rowcount > 0

    if alterado:
        cursor.execute(
            """
            DELETE FROM professores_turmas_disciplinas
            WHERE turma_id = ?
              AND disciplina_id = ?
        """,
            (turma_id, disciplina_id),
        )
        for professor_id in sorted(professores_afetados):
            _sincronizar_resumo_carga_professor(cursor, professor_id)

    conn.commit()
    conn.close()
    return alterado


def criar_atribuicao_docente(professor_id: int, turma_id: int, disciplina_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT professor_usuario_id
            FROM turmas_disciplinas
            WHERE turma_id = ?
              AND disciplina_id = ?
            LIMIT 1
        """,
            (int(turma_id), int(disciplina_id)),
        )
        row = cursor.fetchone()
        if row and int(row["professor_usuario_id"] or 0) == int(professor_id):
            raise sqlite3.IntegrityError(
                "A atribuicao docente ja existe para esta turma e disciplina."
            )

        _upsert_turma_disciplina_cursor(
            cursor,
            turma_id=int(turma_id),
            disciplina_id=int(disciplina_id),
            carga_horaria=None,
            professor_usuario_id=int(professor_id),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    itens = listar_atribuicoes_docentes(
        professor_id=int(professor_id),
        turma_id=int(turma_id),
        disciplina_id=int(disciplina_id),
        incluir_inativos=True,
    )
    return itens[0] if itens else None


def sincronizar_atribuicoes_docentes_professor_disciplina(
    professor_id: int,
    disciplina_id: int,
    turma_ids: list[int],
):
    professor_id_valor = int(professor_id)
    disciplina_id_valor = int(disciplina_id)
    turma_ids_unicos = []
    for turma_id in turma_ids or []:
        try:
            valor = int(turma_id)
        except (TypeError, ValueError):
            continue
        if valor > 0 and valor not in turma_ids_unicos:
            turma_ids_unicos.append(valor)

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT turma_id
            FROM turmas_disciplinas
            WHERE professor_usuario_id = ?
              AND disciplina_id = ?
            """,
            (professor_id_valor, disciplina_id_valor),
        )
        atuais_por_turma = {int(row["turma_id"]): True for row in cursor.fetchall()}

        novas_turmas = set(turma_ids_unicos)
        turmas_atuais = set(atuais_por_turma.keys())
        turmas_para_remover = sorted(turmas_atuais - novas_turmas)

        removidos = 0
        for turma_id in turmas_para_remover:
            cursor.execute(
                """
                UPDATE turmas_disciplinas
                SET professor_usuario_id = NULL,
                    atualizado_em = datetime('now')
                WHERE turma_id = ?
                  AND disciplina_id = ?
                  AND professor_usuario_id = ?
            """,
                (int(turma_id), disciplina_id_valor, professor_id_valor),
            )
            alterado = max(int(cursor.rowcount or 0), 0)
            if alterado > 0:
                _sincronizar_atribuicoes_docentes_por_turma_disciplina(
                    cursor,
                    turma_id=int(turma_id),
                    disciplina_id=disciplina_id_valor,
                    professor_usuario_id=None,
                )
            removidos += alterado

        criados = 0
        for turma_id in sorted(novas_turmas):
            cursor.execute(
                """
                SELECT professor_usuario_id
                FROM turmas_disciplinas
                WHERE turma_id = ?
                  AND disciplina_id = ?
                LIMIT 1
            """,
                (int(turma_id), disciplina_id_valor),
            )
            row = cursor.fetchone()
            professor_atual = int(row["professor_usuario_id"] or 0) if row else 0
            if professor_atual != professor_id_valor:
                criados += 1
            _upsert_turma_disciplina_cursor(
                cursor,
                turma_id=int(turma_id),
                disciplina_id=disciplina_id_valor,
                carga_horaria=None,
                professor_usuario_id=professor_id_valor,
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    atribuicoes = listar_atribuicoes_docentes(
        professor_id=professor_id_valor,
        disciplina_id=disciplina_id_valor,
        incluir_inativos=True,
    )
    return {
        "professor_id": professor_id_valor,
        "disciplina_id": disciplina_id_valor,
        "criados": criados,
        "removidos": removidos,
        "total_ativo": len(atribuicoes),
        "turma_ids": [int(item["turma_id"]) for item in atribuicoes],
        "atribuicoes": atribuicoes,
    }


def excluir_atribuicao_docente(atribuicao_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT professor_usuario_id, turma_id, disciplina_id
        FROM professores_turmas_disciplinas
        WHERE id = ?
        """,
        (int(atribuicao_id),),
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False

    professor_id = int(row["professor_usuario_id"])
    turma_id = int(row["turma_id"])
    disciplina_id = int(row["disciplina_id"])

    cursor.execute(
        """
        UPDATE turmas_disciplinas
        SET professor_usuario_id = NULL,
            atualizado_em = datetime('now')
        WHERE turma_id = ?
          AND disciplina_id = ?
          AND professor_usuario_id = ?
    """,
        (turma_id, disciplina_id, professor_id),
    )
    alterado = cursor.rowcount > 0
    if alterado:
        _sincronizar_atribuicoes_docentes_por_turma_disciplina(
            cursor,
            turma_id=turma_id,
            disciplina_id=disciplina_id,
            professor_usuario_id=None,
        )

    conn.commit()
    conn.close()
    return alterado


def obter_regras_cota():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT base_paginas, paginas_por_aula, paginas_por_turma, cota_mensal_escola, atualizado_em
        FROM cota_regras
        WHERE id = 1
    """)
    row = cursor.fetchone()
    conn.close()

    if not row:
        return {
            "base_paginas": COTA_BASE_PADRAO,
            "paginas_por_aula": COTA_POR_AULA_PADRAO,
            "paginas_por_turma": COTA_POR_TURMA_PADRAO,
            "cota_mensal_escola": COTA_MENSAL_ESCOLA_PADRAO,
            "atualizado_em": None,
        }
    return dict(row)


def obter_status_impressao():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT sem_papel, mensagem, atualizado_em
        FROM impressao_status
        WHERE id = 1
        """
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return {
            "sem_papel": False,
            "mensagem": "",
            "atualizado_em": "",
        }

    return {
        "sem_papel": bool(int(row["sem_papel"] or 0)),
        "mensagem": str(row["mensagem"] or "").strip(),
        "atualizado_em": str(row["atualizado_em"] or ""),
    }


def atualizar_status_impressao(
    *,
    sem_papel: bool,
    mensagem: str = "",
):
    conn = get_connection()
    cursor = conn.cursor()
    mensagem_limpa = str(mensagem or "").strip()

    cursor.execute(
        """
        INSERT INTO impressao_status (
            id, sem_papel, mensagem, atualizado_em
        )
        VALUES (1, ?, ?, datetime('now'))
        ON CONFLICT(id) DO UPDATE SET
            sem_papel = excluded.sem_papel,
            mensagem = excluded.mensagem,
            atualizado_em = excluded.atualizado_em
        """,
        (1 if sem_papel else 0, mensagem_limpa),
    )

    conn.commit()
    conn.close()
    return obter_status_impressao()


def atualizar_regras_cota(
    base_paginas: int,
    paginas_por_aula: int,
    paginas_por_turma: int,
    cota_mensal_escola: int,
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO cota_regras (
            id, base_paginas, paginas_por_aula, paginas_por_turma, cota_mensal_escola, atualizado_em
        )
        VALUES (1, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(id) DO UPDATE SET
            base_paginas = excluded.base_paginas,
            paginas_por_aula = excluded.paginas_por_aula,
            paginas_por_turma = excluded.paginas_por_turma,
            cota_mensal_escola = excluded.cota_mensal_escola,
            atualizado_em = datetime('now')
    """,
        (base_paginas, paginas_por_aula, paginas_por_turma, cota_mensal_escola),
    )

    conn.commit()
    conn.close()


def _calcular_total_distribuivel(cota_mensal_escola: int) -> int:
    cota_total = max(int(cota_mensal_escola or 0), 0)
    percentual_disponivel = max(0, 100 - RESERVA_INSTITUCIONAL_PERCENTUAL)
    return cota_total * percentual_disponivel // 100


def _calcular_peso_professor(
    professor: dict,
    alunos_por_turma: dict,
    aulas_por_disciplina: dict,
    atribuicoes_docentes: list[dict] | None = None,
) -> float:
    if atribuicoes_docentes:
        peso_total = 0.0
        for atribuicao in atribuicoes_docentes:
            chave_turma = _normalizar_texto_chave(atribuicao.get("turma_nome"))
            alunos_turma = max(int(alunos_por_turma.get(chave_turma, 0)), 0)
            if alunos_turma <= 0:
                continue

            disciplina_nome = atribuicao.get("disciplina_nome")
            chave_disciplina = _normalizar_texto_chave(disciplina_nome)
            aulas_disciplina = max(int(aulas_por_disciplina.get(chave_disciplina, 0)), 0)
            if aulas_disciplina <= 0:
                continue

            multiplicador = _obter_multiplicador_disciplina(disciplina_nome)
            peso_total += aulas_disciplina * alunos_turma * multiplicador
        return max(peso_total, 0.0)

    turmas_professor = _desserializar_lista_texto(professor.get("turmas"))
    disciplinas_professor = _desserializar_lista_texto(professor.get("disciplinas"))

    if not turmas_professor or not disciplinas_professor:
        return 0.0

    cargas_disciplina = []
    total_aulas_disciplinas = 0.0

    for disciplina in disciplinas_professor:
        chave_disciplina = _normalizar_texto_chave(disciplina)
        aulas_disciplina = max(int(aulas_por_disciplina.get(chave_disciplina, 0)), 0)
        cargas_disciplina.append((disciplina, float(aulas_disciplina)))
        total_aulas_disciplinas += aulas_disciplina

    aulas_semanais_professor = max(int(professor.get("aulas_semanais") or 0), 0)
    if total_aulas_disciplinas <= 0 and aulas_semanais_professor > 0:
        aulas_media = aulas_semanais_professor / len(cargas_disciplina)
        cargas_disciplina = [(disciplina, aulas_media) for disciplina, _ in cargas_disciplina]

    peso_total = 0.0

    for turma in turmas_professor:
        chave_turma = _normalizar_texto_chave(turma)
        alunos_turma = max(int(alunos_por_turma.get(chave_turma, 0)), 0)
        if alunos_turma <= 0:
            continue

        for disciplina, aulas_disciplina in cargas_disciplina:
            if aulas_disciplina <= 0:
                continue
            multiplicador = _obter_multiplicador_disciplina(disciplina)
            peso_total += aulas_disciplina * alunos_turma * multiplicador

    return max(peso_total, 0.0)


def calcular_cotas_mensais_professores():
    regras = obter_regras_cota()
    cota_distribuivel = _calcular_total_distribuivel(regras["cota_mensal_escola"])

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(f"""
        SELECT
            u.id,
            u.nome,
            COALESCE(pc.aulas_semanais, 0) AS aulas_semanais,
            COALESCE(pc.turmas, '[]') AS turmas,
            COALESCE(pc.disciplinas, '[]') AS disciplinas
        FROM usuarios u
        LEFT JOIN professores_carga pc ON pc.usuario_id = u.id
        WHERE u.perfil = 'professor'
          AND {_clausula_usuario_ativo("u")}
        ORDER BY u.nome COLLATE NOCASE ASC, u.id ASC
    """)
    professores_rows = cursor.fetchall()

    cursor.execute("""
        SELECT nome, quantidade_estudantes
        FROM turmas
        WHERE ativo = 1
    """)
    turmas_rows = cursor.fetchall()

    cursor.execute("""
        SELECT nome, aulas_semanais
        FROM disciplinas
        WHERE ativo = 1
    """)
    disciplinas_rows = cursor.fetchall()

    conn.close()

    if not professores_rows:
        return []

    atribuicoes_por_usuario = listar_atribuicoes_docentes_por_usuario_ids(
        [int(row["id"]) for row in professores_rows],
        incluir_inativos=False,
    )

    alunos_por_turma = {}
    for turma in turmas_rows:
        chave_turma = _normalizar_texto_chave(turma["nome"])
        alunos_por_turma[chave_turma] = max(int(turma["quantidade_estudantes"] or 0), 0)

    aulas_por_disciplina = {}
    for disciplina in disciplinas_rows:
        chave_disciplina = _normalizar_texto_chave(disciplina["nome"])
        aulas_por_disciplina[chave_disciplina] = max(int(disciplina["aulas_semanais"] or 0), 0)

    calculos = []
    total_pesos = 0.0

    for row in professores_rows:
        professor = dict(row)
        peso_total_individual = _calcular_peso_professor(
            professor=professor,
            alunos_por_turma=alunos_por_turma,
            aulas_por_disciplina=aulas_por_disciplina,
            atribuicoes_docentes=atribuicoes_por_usuario.get(int(professor["id"]), []),
        )

        calculos.append(
            {
                "usuario_id": int(professor["id"]),
                "professor": professor["nome"],
                "peso_total_individual": peso_total_individual,
                "cota_mensal_calculada": 0,
            }
        )
        total_pesos += peso_total_individual

    if total_pesos <= 0:
        cota_base = cota_distribuivel // len(calculos)
        sobra = cota_distribuivel % len(calculos)

        for indice, calculo in enumerate(calculos):
            calculo["cota_mensal_calculada"] = cota_base + (1 if indice < sobra else 0)
            calculo["peso_total_individual"] = round(calculo["peso_total_individual"], 2)
        return calculos

    distribuicao = []
    acumulado = 0
    indice_por_usuario = {}

    for indice, calculo in enumerate(calculos):
        quota_bruta = cota_distribuivel * calculo["peso_total_individual"] / total_pesos
        quota_inteira = int(quota_bruta)
        calculo["cota_mensal_calculada"] = quota_inteira
        acumulado += quota_inteira
        indice_por_usuario[calculo["usuario_id"]] = indice
        distribuicao.append((quota_bruta - quota_inteira, calculo["usuario_id"]))

    sobra = cota_distribuivel - acumulado
    if sobra > 0 and distribuicao:
        distribuicao.sort(key=lambda item: (-item[0], item[1]))
        for indice in range(sobra):
            usuario_id = distribuicao[indice % len(distribuicao)][1]
            calculos[indice_por_usuario[usuario_id]]["cota_mensal_calculada"] += 1

    for calculo in calculos:
        calculo["peso_total_individual"] = round(calculo["peso_total_individual"], 2)

    return calculos


def calcular_limites_cota_professores():
    calculos = calcular_cotas_mensais_professores()
    return {
        int(calculo["usuario_id"]): int(calculo["cota_mensal_calculada"]) for calculo in calculos
    }


def calcular_limite_cota_usuario(usuario_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT perfil
        FROM usuarios
        WHERE id = ?
    """,
        (usuario_id,),
    )
    row_usuario = cursor.fetchone()

    if not row_usuario:
        conn.close()
        return 0

    regras = obter_regras_cota()
    perfil = row_usuario["perfil"]

    if perfil != "professor":
        conn.close()
        return int(regras["base_paginas"])
    conn.close()
    limites = calcular_limites_cota_professores()
    return max(int(limites.get(int(usuario_id), 0)), 0)


def listar_professores_admin(mes: str = None):
    conn = get_connection()
    cursor = conn.cursor()

    query = f"""
        SELECT
            u.id,
            u.nome,
            u.email,
            u.data_nascimento,
            COALESCE(u.acesso_coordenacao, 0) AS acesso_coordenacao,
            COALESCE(pc.aulas_semanais, 0) AS aulas_semanais,
            COALESCE(pc.turmas_quantidade, 0) AS turmas_quantidade,
            COALESCE(pc.turmas, '[]') AS turmas,
            COALESCE(pc.disciplinas, '[]') AS disciplinas
        FROM usuarios u
        LEFT JOIN professores_carga pc ON pc.usuario_id = u.id
        WHERE u.perfil = 'professor'
          AND {_clausula_usuario_ativo("u")}
        ORDER BY u.nome ASC
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    professores = [dict(row) for row in rows]
    atribuicoes_por_usuario = listar_atribuicoes_docentes_por_usuario_ids(
        [int(professor["id"]) for professor in professores],
        incluir_inativos=True,
    )

    for professor in professores:
        professor["acesso_coordenacao"] = bool(int(professor.get("acesso_coordenacao") or 0))
        professor["turmas"] = _desserializar_lista_texto(professor.get("turmas"))
        professor["disciplinas"] = _desserializar_lista_texto(professor.get("disciplinas"))
        atribuicoes = atribuicoes_por_usuario.get(int(professor["id"]), [])
        professor["quantidade_atribuicoes_docentes"] = len(atribuicoes)
        if atribuicoes:
            turmas_operacionais = []
            disciplinas_operacionais = []
            for atribuicao in atribuicoes:
                turma_nome = str(atribuicao.get("turma_nome") or "").strip()
                disciplina_nome = str(atribuicao.get("disciplina_nome") or "").strip()
                if turma_nome and turma_nome not in turmas_operacionais:
                    turmas_operacionais.append(turma_nome)
                if disciplina_nome and disciplina_nome not in disciplinas_operacionais:
                    disciplinas_operacionais.append(disciplina_nome)
            professor["turmas_operacionais"] = turmas_operacionais
            professor["disciplinas_operacionais"] = disciplinas_operacionais
        else:
            professor["turmas_operacionais"] = list(professor["turmas"])
            professor["disciplinas_operacionais"] = list(professor["disciplinas"])

    if mes:
        for professor in professores:
            cursor.execute(
                """
                SELECT limite_paginas, usadas_paginas
                FROM cotas
                WHERE usuario_id = ? AND mes = ?
            """,
                (professor["id"], mes),
            )
            cota = cursor.fetchone()
            if cota:
                professor["cota_mes"] = dict(cota)
            else:
                professor["cota_mes"] = None

    conn.close()
    return professores


def listar_professores_agendamento():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"""
        SELECT id, nome, email
        FROM usuarios
        WHERE (
                UPPER(COALESCE(cargo, '')) = ?
                OR (
                TRIM(COALESCE(cargo, '')) = ''
                AND LOWER(COALESCE(perfil, '')) = 'professor'
                )
              )
          AND {_clausula_usuario_ativo()}
        ORDER BY nome COLLATE NOCASE ASC
    """,
        (CARGO_PROFESSOR,),
    )

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def listar_cargas_professores_por_usuario_ids(usuario_ids: list[int]):
    ids_unicos = []
    for usuario_id in usuario_ids or []:
        try:
            valor = int(usuario_id)
        except (TypeError, ValueError):
            continue
        if valor > 0 and valor not in ids_unicos:
            ids_unicos.append(valor)

    if not ids_unicos:
        return {}

    placeholders = ",".join("?" for _ in ids_unicos)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"""
        SELECT
            usuario_id,
            COALESCE(turmas, '[]') AS turmas,
            COALESCE(disciplinas, '[]') AS disciplinas
        FROM professores_carga
        WHERE usuario_id IN ({placeholders})
    """,
        ids_unicos,
    )

    rows = cursor.fetchall()
    conn.close()

    cargas = {}
    for row in rows:
        item = dict(row)
        cargas[int(item["usuario_id"])] = {
            "turmas": _desserializar_lista_texto(item.get("turmas")),
            "disciplinas": _desserializar_lista_texto(item.get("disciplinas")),
        }
    return cargas


def buscar_professor_por_id_ocorrencia(usuario_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"""
        SELECT id, nome, email
        FROM usuarios
        WHERE id = ?
          AND {_clausula_usuario_ativo()}
          AND (
              UPPER(COALESCE(cargo, '')) = ?
              OR (
                   TRIM(COALESCE(cargo, '')) = ''
                   AND LOWER(COALESCE(perfil, '')) = 'professor'
              )
          )
    """,
        (int(usuario_id), CARGO_PROFESSOR),
    )

    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def buscar_professores_ocorrencia(termo: str = "", limite: int = 20):
    conn = get_connection()
    cursor = conn.cursor()

    termo_limpo = _normalizar_nome_catalogo(termo).lower()
    limite_final = max(int(limite or 20), 1)

    query = f"""
        SELECT id, nome, email
        FROM usuarios
        WHERE {_clausula_usuario_ativo()}
          AND (
              UPPER(COALESCE(cargo, '')) = ?
              OR (
                  TRIM(COALESCE(cargo, '')) = ''
                  AND LOWER(COALESCE(perfil, '')) = 'professor'
              )
          )
    """
    params = [CARGO_PROFESSOR]

    if termo_limpo:
        query += """
            AND (
                LOWER(COALESCE(nome, '')) LIKE ?
                OR LOWER(COALESCE(email, '')) LIKE ?
            )
        """
        like = f"%{termo_limpo}%"
        params.extend([like, like])

    query += """
        ORDER BY nome COLLATE NOCASE ASC, id ASC
        LIMIT ?
    """
    params.append(limite_final)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def listar_estudantes(
    incluir_inativos: bool = False,
    nome: str = None,
    turma_id: int = None,
    limite: int = None,
):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT
            e.id,
            e.nome,
            e.turma_id,
            COALESCE(t.nome, '') AS turma_nome,
            e.ativo,
            e.criado_em,
            e.atualizado_em
        FROM estudantes e
        LEFT JOIN turmas t ON t.id = e.turma_id
        WHERE 1 = 1
    """
    params = []

    if not incluir_inativos:
        query += " AND e.ativo = 1"

    nome_limpo = _normalizar_nome_catalogo(nome).lower()
    if nome_limpo:
        query += " AND LOWER(COALESCE(e.nome, '')) LIKE ?"
        params.append(f"%{nome_limpo}%")

    if turma_id is not None:
        turma_id_valor = int(turma_id)
        if turma_id_valor > 0:
            query += " AND e.turma_id = ?"
            params.append(turma_id_valor)

    query += " ORDER BY e.nome COLLATE NOCASE ASC, e.id ASC"

    if limite is not None:
        limite_valor = max(int(limite or 0), 1)
        query += " LIMIT ?"
        params.append(limite_valor)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def buscar_estudante_por_id(estudante_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            e.id,
            e.nome,
            e.turma_id,
            COALESCE(t.nome, '') AS turma_nome,
            e.ativo,
            e.criado_em,
            e.atualizado_em
        FROM estudantes e
        LEFT JOIN turmas t ON t.id = e.turma_id
        WHERE e.id = ?
    """,
        (int(estudante_id),),
    )

    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def buscar_estudante_por_nome_turma(nome: str, turma_id: int):
    nome_limpo = _normalizar_nome_catalogo(nome)
    turma_id_valor = int(turma_id or 0)
    if not nome_limpo or turma_id_valor <= 0:
        return None

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            e.id,
            e.nome,
            e.turma_id,
            COALESCE(t.nome, '') AS turma_nome,
            e.ativo,
            e.criado_em,
            e.atualizado_em
        FROM estudantes e
        LEFT JOIN turmas t ON t.id = e.turma_id
        WHERE e.turma_id = ?
          AND COALESCE(e.nome, '') = ? COLLATE NOCASE
        ORDER BY e.id ASC
        LIMIT 1
    """,
        (turma_id_valor, nome_limpo),
    )

    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def criar_estudante(nome: str, turma_id: int, ativo: bool = True):
    nome_limpo = _normalizar_nome_catalogo(nome)
    turma_id_valor = int(turma_id or 0)
    if not nome_limpo:
        raise ValueError("Nome do estudante é obrigatório.")
    if turma_id_valor <= 0:
        raise ValueError("Turma inválida.")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO estudantes (nome, turma_id, ativo, criado_em, atualizado_em)
        VALUES (?, ?, ?, datetime('now'), datetime('now'))
    """,
        (nome_limpo, turma_id_valor, 1 if ativo else 0),
    )

    estudante_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return estudante_id


def criar_ou_atualizar_estudante_por_nome_turma(nome: str, turma_id: int, ativo: bool = True):
    existente = buscar_estudante_por_nome_turma(nome, turma_id)
    if existente:
        atualizar_estudante(
            estudante_id=int(existente["id"]),
            nome=nome,
            turma_id=turma_id,
            ativo=ativo,
        )
        return int(existente["id"]), False

    estudante_id = criar_estudante(nome=nome, turma_id=turma_id, ativo=ativo)
    return int(estudante_id), True


def atualizar_estudante(estudante_id: int, nome: str, turma_id: int, ativo: bool):
    nome_limpo = _normalizar_nome_catalogo(nome)
    turma_id_valor = int(turma_id or 0)
    if not nome_limpo:
        raise ValueError("Nome do estudante é obrigatório.")
    if turma_id_valor <= 0:
        raise ValueError("Turma inválida.")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE estudantes
        SET nome = ?, turma_id = ?, ativo = ?, atualizado_em = datetime('now')
        WHERE id = ?
    """,
        (nome_limpo, turma_id_valor, 1 if ativo else 0, int(estudante_id)),
    )

    alterado = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return alterado


def atualizar_status_estudante(estudante_id: int, ativo: bool):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE estudantes
        SET ativo = ?, atualizado_em = datetime('now')
        WHERE id = ?
    """,
        (1 if ativo else 0, int(estudante_id)),
    )

    alterado = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return alterado


def remover_estudante(estudante_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    estudante_id_valor = int(estudante_id)

    cursor.execute("SELECT 1 FROM estudantes WHERE id = ?", (estudante_id_valor,))
    if not cursor.fetchone():
        conn.close()
        return False, 0

    cursor.execute(
        """
        UPDATE ocorrencias
        SET estudante_id = NULL, atualizado_em = datetime('now')
        WHERE estudante_id = ?
    """,
        (estudante_id_valor,),
    )
    ocorrencias_desvinculadas = cursor.rowcount

    cursor.execute("DELETE FROM estudantes WHERE id = ?", (estudante_id_valor,))
    removido = cursor.rowcount > 0

    conn.commit()
    conn.close()
    return removido, ocorrencias_desvinculadas


def buscar_estudantes_ocorrencia(termo: str = "", turma_id: int = None, limite: int = 20):
    return listar_estudantes(
        incluir_inativos=False,
        nome=termo,
        turma_id=turma_id,
        limite=limite,
    )


def seed_recursos_padrao():
    recursos = [
        ("Notebook Carrinho 1", "Notebook", "Carrinho móvel com 30 notebooks.", 1),
        ("Projetor Sala Multiuso", "Projetor", "Projetor Epson da sala multiuso.", 1),
        ("Laboratório Maker", "Laboratório", "Laboratório com kits de robótica.", 1),
        ("Kit Tablets", "Tablet", "Conjunto de 25 tablets para aula interativa.", 1),
        ("Caixa de Som Bluetooth", "Áudio", "Caixa de som portátil para apresentações.", 1),
    ]

    conn = get_connection()
    cursor = conn.cursor()

    cursor.executemany(
        """
        INSERT OR IGNORE INTO recursos (nome, tipo, descricao, quantidade_itens, ativo)
        VALUES (?, ?, ?, ?, 1)
    """,
        recursos,
    )

    conn.commit()
    conn.close()


_HORARIO_FAIXA_GLOBAL_OFFSET_POR_TURNO = {
    "MATUTINO": 0,
    "INTEGRAL": 0,
    "VESPERTINO": 5,
    "VESPERTINO_EM": 5,
}


def _faixa_global_por_turno_e_aula_horario(turno: str, aula_numero: int) -> int:
    turno_norm = str(turno or "").strip().upper()
    aula = int(aula_numero or 0)
    if aula <= 0:
        return 0
    faixa = aula + int(_HORARIO_FAIXA_GLOBAL_OFFSET_POR_TURNO.get(turno_norm) or 0)
    if turno_norm == "INTEGRAL" and aula > 5:
        faixa += 1
    return faixa


def _expressao_sql_faixa_global_horario(alias_horario: str = "he", alias_turma: str = "t") -> str:
    aula_expr = f"CAST(COALESCE({alias_horario}.aula_numero, 0) AS INTEGER)"
    turno_expr = f"UPPER(COALESCE({alias_turma}.turno, ''))"
    return f"""
        COALESCE(
            NULLIF({alias_horario}.faixa_global, 0),
            CASE
                WHEN {turno_expr} IN ('VESPERTINO', 'VESPERTINO_EM') THEN {aula_expr} + 5
                WHEN {turno_expr} = 'INTEGRAL' THEN {aula_expr} + CASE WHEN {aula_expr} > 5 THEN 1 ELSE 0 END
                ELSE {aula_expr}
            END
        )
    """


def _resolver_faixa_global_registro_horario(
    cursor,
    *,
    turma_id: int,
    aula_numero: int,
    faixa_global: int | None = None,
) -> int:
    faixa_informada = int(faixa_global or 0)
    if faixa_informada > 0:
        return faixa_informada

    cursor.execute(
        """
        SELECT turno
        FROM turmas
        WHERE id = ?
        """,
        (int(turma_id),),
    )
    row = cursor.fetchone()
    turno = row["turno"] if row else ""
    return _faixa_global_por_turno_e_aula_horario(turno, aula_numero)


def _buscar_horario_escolar_conflito_professor_cursor(
    cursor,
    *,
    ano_letivo: int,
    professor_usuario_id: int,
    dia_semana: str,
    faixa_global: int,
    ignorar_registro_id: int | None = None,
):
    filtros = [
        "he.ano_letivo = ?",
        "he.professor_usuario_id = ?",
        "UPPER(he.dia_semana) = ?",
        f"{_expressao_sql_faixa_global_horario('he', 't')} = ?",
    ]
    params = [
        int(ano_letivo),
        int(professor_usuario_id),
        str(dia_semana or "").strip().upper(),
        int(faixa_global or 0),
    ]
    if ignorar_registro_id is not None:
        filtros.append("he.id <> ?")
        params.append(int(ignorar_registro_id))

    cursor.execute(
        f"""
        SELECT he.id
        FROM horarios_escolares he
        INNER JOIN turmas t ON t.id = he.turma_id
        WHERE {' AND '.join(filtros)}
        ORDER BY he.id ASC
        LIMIT 1
        """,
        params,
    )
    row = cursor.fetchone()
    return int(row["id"]) if row else None


def _recalcular_faixa_global_horarios_turma(cursor, turma_id: int, turno: str) -> None:
    turno_norm = str(turno or "").strip().upper()
    if turno_norm in {"VESPERTINO", "VESPERTINO_EM"}:
        expressao = "CAST(COALESCE(aula_numero, 0) AS INTEGER) + 5"
    elif turno_norm == "INTEGRAL":
        expressao = (
            "CAST(COALESCE(aula_numero, 0) AS INTEGER) + "
            "CASE WHEN CAST(COALESCE(aula_numero, 0) AS INTEGER) > 5 THEN 1 ELSE 0 END"
        )
    else:
        expressao = "CAST(COALESCE(aula_numero, 0) AS INTEGER)"

    cursor.execute(
        f"""
        UPDATE horarios_escolares
        SET faixa_global = {expressao}
        WHERE turma_id = ?
        """,
        (int(turma_id),),
    )


def _mapear_horario_escolar(row) -> dict:
    item = dict(row)
    return {
        "id": int(item["id"]),
        "ano_letivo": int(item["ano_letivo"]),
        "turma_id": int(item["turma_id"]),
        "turma_nome": item.get("turma_nome", "") or "",
        "turno": item.get("turno", "") or "",
        "disciplina_id": int(item["disciplina_id"]),
        "disciplina_nome": item.get("disciplina_nome", "") or "",
        "tem_apc": bool(int(item.get("disciplina_tem_apc", 0) or 0)),
        "tem_prova_bimestral": bool(
            int(item.get("disciplina_tem_prova_bimestral", 0) or 0)
        ),
        "professor_id": int(item["professor_usuario_id"]),
        "professor_nome": item.get("professor_nome", "") or "",
        "professor_email": item.get("professor_email", "") or "",
        "dia_semana": item.get("dia_semana", "") or "",
        "aula_numero": int(item.get("aula_numero") or 0),
        "faixa_global": int(item.get("faixa_global") or 0),
        "criado_em": item.get("criado_em", "") or "",
        "atualizado_em": item.get("atualizado_em", "") or "",
    }


def _consultar_horarios_escolares(cursor, *, filtros_sql=None, params=None):
    where = list(filtros_sql or [])
    parametros = list(params or [])
    clausula_where = f"WHERE {' AND '.join(where)}" if where else ""

    cursor.execute(
        f"""
        SELECT
            he.id,
            he.ano_letivo,
            he.turma_id,
            he.disciplina_id,
            he.professor_usuario_id,
            he.dia_semana,
            he.aula_numero,
            {_expressao_sql_faixa_global_horario('he', 't')} AS faixa_global,
            he.criado_em,
            he.atualizado_em,
            COALESCE(t.nome, '') AS turma_nome,
            COALESCE(t.turno, '') AS turno,
            COALESCE(d.nome, '') AS disciplina_nome,
            COALESCE(d.tem_apc, 0) AS disciplina_tem_apc,
            COALESCE(d.tem_prova_bimestral, 0) AS disciplina_tem_prova_bimestral,
            COALESCE(u.nome, '') AS professor_nome,
            COALESCE(u.email, '') AS professor_email
        FROM horarios_escolares he
        INNER JOIN turmas t ON t.id = he.turma_id
        INNER JOIN disciplinas d ON d.id = he.disciplina_id
        INNER JOIN usuarios u ON u.id = he.professor_usuario_id
        {clausula_where}
        ORDER BY
            he.ano_letivo DESC,
            t.nome COLLATE NOCASE ASC,
            he.dia_semana ASC,
            faixa_global ASC,
            he.aula_numero ASC,
            d.nome COLLATE NOCASE ASC,
            u.nome COLLATE NOCASE ASC,
            he.id ASC
        """,
        parametros,
    )
    return [_mapear_horario_escolar(row) for row in cursor.fetchall()]


def listar_anos_letivos_horario_escolar():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT DISTINCT ano_letivo
        FROM horarios_escolares
        ORDER BY ano_letivo ASC
        """
    )
    anos = [int(row[0]) for row in cursor.fetchall() if int(row[0] or 0) > 0]
    conn.close()
    return anos


def listar_horarios_escolares(
    *,
    ano_letivo: int | None = None,
    turma_id: int | None = None,
    disciplina_id: int | None = None,
    professor_id: int | None = None,
    dia_semana: str | None = None,
):
    conn = get_connection()
    cursor = conn.cursor()
    filtros = []
    params = []

    if ano_letivo is not None:
        filtros.append("he.ano_letivo = ?")
        params.append(int(ano_letivo))
    if turma_id is not None:
        filtros.append("he.turma_id = ?")
        params.append(int(turma_id))
    if disciplina_id is not None:
        filtros.append("he.disciplina_id = ?")
        params.append(int(disciplina_id))
    if professor_id is not None:
        filtros.append("he.professor_usuario_id = ?")
        params.append(int(professor_id))
    if str(dia_semana or "").strip():
        filtros.append("UPPER(he.dia_semana) = ?")
        params.append(str(dia_semana).strip().upper())

    itens = _consultar_horarios_escolares(cursor, filtros_sql=filtros, params=params)
    conn.close()
    return itens


def buscar_horario_escolar_por_id(registro_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    itens = _consultar_horarios_escolares(
        cursor,
        filtros_sql=["he.id = ?"],
        params=[int(registro_id)],
    )
    conn.close()
    return itens[0] if itens else None


def criar_horario_escolar(
    *,
    ano_letivo: int,
    turma_id: int,
    disciplina_id: int,
    professor_usuario_id: int,
    dia_semana: str,
    aula_numero: int,
    faixa_global: int | None = None,
):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        dia_semana_normalizado = str(dia_semana or "").strip().upper()
        faixa_global_resolvida = _resolver_faixa_global_registro_horario(
            cursor,
            turma_id=int(turma_id),
            aula_numero=int(aula_numero),
            faixa_global=faixa_global,
        )
        conflito_id = _buscar_horario_escolar_conflito_professor_cursor(
            cursor,
            ano_letivo=int(ano_letivo),
            professor_usuario_id=int(professor_usuario_id),
            dia_semana=dia_semana_normalizado,
            faixa_global=faixa_global_resolvida,
        )
        if conflito_id:
            raise sqlite3.IntegrityError("idx_horarios_escolares_professor_faixa_slot")

        cursor.execute(
            """
            INSERT INTO horarios_escolares (
                ano_letivo,
                turma_id,
                disciplina_id,
                professor_usuario_id,
                dia_semana,
                aula_numero,
                faixa_global,
                criado_em,
                atualizado_em
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            """,
            (
                int(ano_letivo),
                int(turma_id),
                int(disciplina_id),
                int(professor_usuario_id),
                dia_semana_normalizado,
                int(aula_numero),
                faixa_global_resolvida,
            ),
        )
        registro_id = int(cursor.lastrowid)
        conn.commit()
    finally:
        conn.close()
    return buscar_horario_escolar_por_id(registro_id)


def atualizar_horario_escolar(
    *,
    registro_id: int,
    ano_letivo: int,
    turma_id: int,
    disciplina_id: int,
    professor_usuario_id: int,
    dia_semana: str,
    aula_numero: int,
    faixa_global: int | None = None,
):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        dia_semana_normalizado = str(dia_semana or "").strip().upper()
        faixa_global_resolvida = _resolver_faixa_global_registro_horario(
            cursor,
            turma_id=int(turma_id),
            aula_numero=int(aula_numero),
            faixa_global=faixa_global,
        )
        conflito_id = _buscar_horario_escolar_conflito_professor_cursor(
            cursor,
            ano_letivo=int(ano_letivo),
            professor_usuario_id=int(professor_usuario_id),
            dia_semana=dia_semana_normalizado,
            faixa_global=faixa_global_resolvida,
            ignorar_registro_id=int(registro_id),
        )
        if conflito_id:
            raise sqlite3.IntegrityError("idx_horarios_escolares_professor_faixa_slot")

        cursor.execute(
            """
            UPDATE horarios_escolares
            SET ano_letivo = ?,
                turma_id = ?,
                disciplina_id = ?,
                professor_usuario_id = ?,
                dia_semana = ?,
                aula_numero = ?,
                faixa_global = ?,
                atualizado_em = datetime('now')
            WHERE id = ?
            """,
            (
                int(ano_letivo),
                int(turma_id),
                int(disciplina_id),
                int(professor_usuario_id),
                dia_semana_normalizado,
                int(aula_numero),
                faixa_global_resolvida,
                int(registro_id),
            ),
        )
        alterado = cursor.rowcount > 0
        conn.commit()
    finally:
        conn.close()
    if not alterado:
        return None
    return buscar_horario_escolar_por_id(registro_id)


def excluir_horario_escolar(registro_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        DELETE FROM horarios_escolares
        WHERE id = ?
        """,
        (int(registro_id),),
    )
    alterado = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return alterado


def _mapear_apc_periodo(row) -> dict:
    return {
        "id": int(row["id"]),
        "ano_letivo": int(row["ano_letivo"] or 0),
        "data_referencia": str(row["data_referencia"] or "").strip(),
        "prazo_envio": str(row["prazo_envio"] or "").strip(),
        "titulo": str(row["titulo"] or "").strip(),
        "observacao": str(row["observacao"] or "").strip(),
        "publico_alvo": str(row["publico_alvo"] or "").strip(),
        "tipo_entrega": str(row["tipo_entrega"] or "").strip(),
        "criado_por_usuario_id": int(row["criado_por_usuario_id"] or 0),
        "criado_em": str(row["criado_em"] or "").strip(),
        "atualizado_em": str(row["atualizado_em"] or "").strip(),
    }


def _consultar_apc_periodos(cursor, *, filtros_sql=None, params=None):
    where = list(filtros_sql or [])
    parametros = list(params or [])
    clausula_where = f"WHERE {' AND '.join(where)}" if where else ""

    cursor.execute(
        f"""
        SELECT
            id,
            ano_letivo,
            data_referencia,
            prazo_envio,
            titulo,
            observacao,
            publico_alvo,
            tipo_entrega,
            criado_por_usuario_id,
            criado_em,
            atualizado_em
        FROM apc_periodos
        {clausula_where}
        ORDER BY data_referencia ASC, id ASC
        """,
        parametros,
    )
    return [_mapear_apc_periodo(row) for row in cursor.fetchall()]


def listar_anos_letivos_apc():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT DISTINCT ano_letivo
        FROM apc_periodos
        ORDER BY ano_letivo ASC
        """
    )
    anos = [int(row[0]) for row in cursor.fetchall() if int(row[0] or 0) > 0]
    conn.close()
    return anos


def listar_apc_periodos(
    *,
    ano_letivo: int | None = None,
    data_inicio: str | None = None,
    data_fim: str | None = None,
):
    conn = get_connection()
    cursor = conn.cursor()
    filtros = []
    params = []

    if ano_letivo is not None:
        filtros.append("ano_letivo = ?")
        params.append(int(ano_letivo))
    if str(data_inicio or "").strip():
        filtros.append("data_referencia >= ?")
        params.append(str(data_inicio).strip())
    if str(data_fim or "").strip():
        filtros.append("data_referencia <= ?")
        params.append(str(data_fim).strip())

    itens = _consultar_apc_periodos(cursor, filtros_sql=filtros, params=params)
    conn.close()
    return itens


def buscar_apc_periodo_por_id(periodo_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    itens = _consultar_apc_periodos(
        cursor,
        filtros_sql=["id = ?"],
        params=[int(periodo_id)],
    )
    conn.close()
    return itens[0] if itens else None


def criar_apc_periodo(
    *,
    ano_letivo: int,
    data_referencia: str,
    prazo_envio: str,
    titulo: str,
    observacao: str,
    publico_alvo: str,
    tipo_entrega: str,
    criado_por_usuario_id: int,
):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO apc_periodos (
            ano_letivo,
            data_referencia,
            prazo_envio,
            titulo,
            observacao,
            publico_alvo,
            tipo_entrega,
            criado_por_usuario_id,
            criado_em,
            atualizado_em
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        """,
        (
            int(ano_letivo),
            str(data_referencia).strip(),
            str(prazo_envio).strip(),
            str(titulo or "").strip(),
            str(observacao or "").strip(),
            str(publico_alvo or "").strip().upper(),
            str(tipo_entrega or "").strip().upper(),
            int(criado_por_usuario_id),
        ),
    )
    periodo_id = int(cursor.lastrowid)
    conn.commit()
    conn.close()
    return buscar_apc_periodo_por_id(periodo_id)


def atualizar_apc_periodo(
    *,
    periodo_id: int,
    ano_letivo: int,
    data_referencia: str,
    prazo_envio: str,
    titulo: str,
    observacao: str,
    publico_alvo: str,
    tipo_entrega: str,
):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE apc_periodos
        SET ano_letivo = ?,
            data_referencia = ?,
            prazo_envio = ?,
            titulo = ?,
            observacao = ?,
            publico_alvo = ?,
            tipo_entrega = ?,
            atualizado_em = datetime('now')
        WHERE id = ?
        """,
        (
            int(ano_letivo),
            str(data_referencia).strip(),
            str(prazo_envio).strip(),
            str(titulo or "").strip(),
            str(observacao or "").strip(),
            str(publico_alvo or "").strip().upper(),
            str(tipo_entrega or "").strip().upper(),
            int(periodo_id),
        ),
    )
    alterado = cursor.rowcount > 0
    conn.commit()
    conn.close()
    if not alterado:
        return None
    return buscar_apc_periodo_por_id(periodo_id)


def excluir_apc_periodo(periodo_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        DELETE FROM apc_periodos
        WHERE id = ?
        """,
        (int(periodo_id),),
    )
    alterado = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return alterado


def _mapear_apc_destinatario(row) -> dict:
    return {
        "id": int(row["id"]),
        "periodo_id": int(row["periodo_id"] or 0),
        "professor_id": int(row["professor_usuario_id"] or 0),
        "professor_nome": str(row["professor_nome"] or "").strip(),
        "professor_email": str(row["professor_email"] or "").strip(),
        "turma_id": int(row["turma_id"] or 0),
        "turma_nome": str(row["turma_nome"] or "").strip(),
        "disciplina_id": int(row["disciplina_id"] or 0),
        "disciplina_nome": str(row["disciplina_nome"] or "").strip(),
    }


def _consultar_apc_destinatarios(cursor, *, filtros_sql=None, params=None):
    where = list(filtros_sql or [])
    parametros = list(params or [])
    clausula_where = f"WHERE {' AND '.join(where)}" if where else ""

    cursor.execute(
        f"""
        SELECT
            ad.id,
            ad.periodo_id,
            ad.professor_usuario_id,
            ad.turma_id,
            ad.disciplina_id,
            COALESCE(u.nome, '') AS professor_nome,
            COALESCE(u.email, '') AS professor_email,
            COALESCE(t.nome, '') AS turma_nome,
            COALESCE(d.nome, '') AS disciplina_nome
        FROM apc_periodo_destinatarios ad
        INNER JOIN usuarios u ON u.id = ad.professor_usuario_id
        LEFT JOIN turmas t ON t.id = ad.turma_id
        LEFT JOIN disciplinas d ON d.id = ad.disciplina_id
        {clausula_where}
        ORDER BY
            u.nome COLLATE NOCASE ASC,
            t.nome COLLATE NOCASE ASC,
            d.nome COLLATE NOCASE ASC,
            ad.id ASC
        """,
        parametros,
    )
    return [_mapear_apc_destinatario(row) for row in cursor.fetchall()]


def listar_apc_destinatarios(
    *,
    periodo_id: int | None = None,
    professor_id: int | None = None,
):
    conn = get_connection()
    cursor = conn.cursor()
    filtros = []
    params = []

    if periodo_id is not None:
        filtros.append("ad.periodo_id = ?")
        params.append(int(periodo_id))
    if professor_id is not None:
        filtros.append("ad.professor_usuario_id = ?")
        params.append(int(professor_id))

    itens = _consultar_apc_destinatarios(cursor, filtros_sql=filtros, params=params)
    conn.close()
    return itens


def buscar_apc_destinatario_por_chave(
    periodo_id: int,
    professor_id: int,
    turma_id: int = 0,
    disciplina_id: int = 0,
):
    conn = get_connection()
    cursor = conn.cursor()
    itens = _consultar_apc_destinatarios(
        cursor,
        filtros_sql=[
            "ad.periodo_id = ?",
            "ad.professor_usuario_id = ?",
            "COALESCE(ad.turma_id, 0) = ?",
            "COALESCE(ad.disciplina_id, 0) = ?",
        ],
        params=[
            int(periodo_id),
            int(professor_id),
            int(turma_id or 0),
            int(disciplina_id or 0),
        ],
    )
    conn.close()
    return itens[0] if itens else None


def substituir_apc_destinatarios(periodo_id: int, destinatarios: list[dict] | None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM apc_periodo_destinatarios WHERE periodo_id = ?",
        (int(periodo_id),),
    )

    for item in destinatarios or []:
        cursor.execute(
            """
            INSERT OR IGNORE INTO apc_periodo_destinatarios (
                periodo_id,
                professor_usuario_id,
                turma_id,
                disciplina_id,
                criado_em
            )
            VALUES (?, ?, ?, ?, datetime('now'))
            """,
            (
                int(periodo_id),
                int(item.get("professor_id") or 0),
                int(item.get("turma_id") or 0),
                int(item.get("disciplina_id") or 0),
            ),
        )

    conn.commit()
    conn.close()
    return listar_apc_destinatarios(periodo_id=int(periodo_id))


def _mapear_apc_envio(row) -> dict:
    arquivo_nome_original = str(row["arquivo_nome_original"] or "").strip()
    arquivo_nome_cliente = str(row["arquivo_nome_cliente"] or "").strip()
    return {
        "id": int(row["id"]),
        "periodo_id": int(row["periodo_id"] or 0),
        "professor_id": int(row["professor_usuario_id"] or 0),
        "turma_id": int(row["turma_id"] or 0),
        "turma_nome": str(row["turma_nome"] or "").strip(),
        "disciplina_id": int(row["disciplina_id"] or 0),
        "disciplina_nome": str(row["disciplina_nome"] or "").strip(),
        "arquivo_nome_cliente": arquivo_nome_cliente or arquivo_nome_original,
        "arquivo_nome_original": arquivo_nome_original,
        "arquivo_path": str(row["arquivo_path"] or "").strip(),
        "arquivo_tamanho": int(row["arquivo_tamanho"] or 0),
        "arquivo_tipo": str(row["arquivo_tipo"] or "").strip(),
        "enviado_em": str(row["enviado_em"] or "").strip(),
        "atualizado_em": str(row["atualizado_em"] or "").strip(),
        "professor_nome": str(row["professor_nome"] or "").strip(),
        "professor_email": str(row["professor_email"] or "").strip(),
    }


def _consultar_apc_envios(cursor, *, filtros_sql=None, params=None):
    where = list(filtros_sql or [])
    parametros = list(params or [])
    clausula_where = f"WHERE {' AND '.join(where)}" if where else ""

    cursor.execute(
        f"""
        SELECT
            ae.id,
            ae.periodo_id,
            ae.professor_usuario_id,
            ae.turma_id,
            ae.disciplina_id,
            ae.arquivo_nome_cliente,
            ae.arquivo_nome_original,
            ae.arquivo_path,
            ae.arquivo_tamanho,
            ae.arquivo_tipo,
            ae.enviado_em,
            ae.atualizado_em,
            COALESCE(u.nome, '') AS professor_nome,
            COALESCE(u.email, '') AS professor_email,
            COALESCE(t.nome, '') AS turma_nome,
            COALESCE(d.nome, '') AS disciplina_nome
        FROM apc_envios ae
        INNER JOIN usuarios u ON u.id = ae.professor_usuario_id
        LEFT JOIN turmas t ON t.id = ae.turma_id
        LEFT JOIN disciplinas d ON d.id = ae.disciplina_id
        {clausula_where}
        ORDER BY ae.enviado_em DESC, ae.id DESC
        """,
        parametros,
    )
    return [_mapear_apc_envio(row) for row in cursor.fetchall()]


def listar_apc_envios(
    *,
    periodo_id: int | None = None,
    professor_id: int | None = None,
    turma_id: int | None = None,
    disciplina_id: int | None = None,
):
    conn = get_connection()
    cursor = conn.cursor()
    filtros = []
    params = []

    if periodo_id is not None:
        filtros.append("ae.periodo_id = ?")
        params.append(int(periodo_id))
    if professor_id is not None:
        filtros.append("ae.professor_usuario_id = ?")
        params.append(int(professor_id))
    if turma_id is not None:
        filtros.append("ae.turma_id = ?")
        params.append(int(turma_id))
    if disciplina_id is not None:
        filtros.append("ae.disciplina_id = ?")
        params.append(int(disciplina_id))

    itens = _consultar_apc_envios(cursor, filtros_sql=filtros, params=params)
    conn.close()
    return itens


def buscar_apc_envio_por_id(envio_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    itens = _consultar_apc_envios(
        cursor,
        filtros_sql=["ae.id = ?"],
        params=[int(envio_id)],
    )
    conn.close()
    return itens[0] if itens else None


def buscar_apc_envio_por_periodo_e_professor(periodo_id: int, professor_id: int):
    return buscar_apc_envio_por_chave(periodo_id, professor_id, 0, 0)


def buscar_apc_envio_por_chave(
    periodo_id: int,
    professor_id: int,
    turma_id: int = 0,
    disciplina_id: int = 0,
):
    conn = get_connection()
    cursor = conn.cursor()
    itens = _consultar_apc_envios(
        cursor,
        filtros_sql=[
            "ae.periodo_id = ?",
            "ae.professor_usuario_id = ?",
            "ae.turma_id = ?",
            "ae.disciplina_id = ?",
        ],
        params=[
            int(periodo_id),
            int(professor_id),
            int(turma_id or 0),
            int(disciplina_id or 0),
        ],
    )
    conn.close()
    return itens[0] if itens else None


def criar_apc_envio(
    *,
    periodo_id: int,
    professor_usuario_id: int,
    turma_id: int = 0,
    disciplina_id: int = 0,
    arquivo_nome_cliente: str,
    arquivo_nome_original: str,
    arquivo_path: str,
    arquivo_tamanho: int,
    arquivo_tipo: str,
):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO apc_envios (
            periodo_id,
            professor_usuario_id,
            turma_id,
            disciplina_id,
            arquivo_nome_cliente,
            arquivo_nome_original,
            arquivo_path,
            arquivo_tamanho,
            arquivo_tipo,
            enviado_em,
            atualizado_em
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        """,
        (
            int(periodo_id),
            int(professor_usuario_id),
            int(turma_id or 0),
            int(disciplina_id or 0),
            str(arquivo_nome_cliente or "").strip(),
            str(arquivo_nome_original or "").strip(),
            str(arquivo_path or "").strip(),
            int(arquivo_tamanho or 0),
            str(arquivo_tipo or "").strip(),
        ),
    )
    envio_id = int(cursor.lastrowid)
    conn.commit()
    conn.close()
    return buscar_apc_envio_por_id(envio_id)


def atualizar_apc_envio(
    *,
    envio_id: int,
    arquivo_nome_cliente: str,
    arquivo_nome_original: str,
    arquivo_path: str,
    arquivo_tamanho: int,
    arquivo_tipo: str,
):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE apc_envios
        SET arquivo_nome_cliente = ?,
            arquivo_nome_original = ?,
            arquivo_path = ?,
            arquivo_tamanho = ?,
            arquivo_tipo = ?,
            enviado_em = datetime('now'),
            atualizado_em = datetime('now')
        WHERE id = ?
        """,
        (
            str(arquivo_nome_cliente or "").strip(),
            str(arquivo_nome_original or "").strip(),
            str(arquivo_path or "").strip(),
            int(arquivo_tamanho or 0),
            str(arquivo_tipo or "").strip(),
            int(envio_id),
        ),
    )
    alterado = cursor.rowcount > 0
    conn.commit()
    conn.close()
    if not alterado:
        return None
    return buscar_apc_envio_por_id(envio_id)


def excluir_apc_envio(envio_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM apc_envios WHERE id = ?", (int(envio_id),))
    removido = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return removido


def listar_turmas(incluir_inativas: bool = False):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT id, nome, turno, quantidade_estudantes, ativo, criado_em
        FROM turmas
    """
    params = []

    if not incluir_inativas:
        query += " WHERE ativo = 1"

    query += " ORDER BY nome COLLATE NOCASE ASC"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def listar_turmas_ativas():
    return listar_turmas(incluir_inativas=False)


def buscar_turma_por_id(turma_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, nome, turno, quantidade_estudantes, ativo, criado_em
        FROM turmas
        WHERE id = ?
    """,
        (int(turma_id),),
    )

    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def buscar_turma_por_nome(nome: str, incluir_inativas: bool = True):
    nome_limpo = _normalizar_nome_catalogo(nome)
    if not nome_limpo:
        return None

    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT id, nome, turno, quantidade_estudantes, ativo, criado_em
        FROM turmas
        WHERE nome = ? COLLATE NOCASE
    """
    params = [nome_limpo]
    if not incluir_inativas:
        query += " AND ativo = 1"
    query += " ORDER BY id ASC LIMIT 1"

    cursor.execute(query, params)
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def criar_turma(nome: str, turno: str = "", quantidade_estudantes: int = 0):
    nome_limpo = _normalizar_nome_catalogo(nome)
    if not nome_limpo:
        raise ValueError("Nome da turma é obrigatório.")
    turno_limpo = str(turno or "").strip().upper()
    quantidade_estudantes_valor = int(quantidade_estudantes or 0)
    if quantidade_estudantes_valor < 0:
        raise ValueError("Quantidade de estudantes não pode ser negativa.")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO turmas (nome, turno, quantidade_estudantes, ativo, criado_em)
        VALUES (?, ?, ?, 1, datetime('now'))
    """,
        (nome_limpo, turno_limpo, quantidade_estudantes_valor),
    )

    turma_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return turma_id


def atualizar_turma_dados(turma_id: int, turno: str, quantidade_estudantes: int):
    turno_limpo = str(turno or "").strip().upper()
    quantidade_estudantes_valor = int(quantidade_estudantes or 0)
    if quantidade_estudantes_valor < 0:
        raise ValueError("Quantidade de estudantes não pode ser negativa.")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE turmas
        SET turno = ?, quantidade_estudantes = ?
        WHERE id = ?
    """,
        (turno_limpo, quantidade_estudantes_valor, turma_id),
    )

    alterado = cursor.rowcount > 0
    if alterado:
        _recalcular_faixa_global_horarios_turma(cursor, int(turma_id), turno_limpo)
    conn.commit()
    conn.close()
    return alterado


def atualizar_status_turma(turma_id: int, ativo: bool):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE turmas
        SET ativo = ?
        WHERE id = ?
    """,
        (1 if ativo else 0, turma_id),
    )

    alterado = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return alterado


def _mapear_disciplina(row) -> dict:
    item = dict(row)
    return {
        "id": int(item["id"]),
        "nome": str(item.get("nome") or "").strip(),
        "aulas_semanais": int(item.get("aulas_semanais") or 0),
        "tem_apc": bool(int(item.get("tem_apc", 0) or 0)),
        "tem_prova_bimestral": bool(int(item.get("tem_prova_bimestral", 0) or 0)),
        "ativo": bool(int(item.get("ativo", 1) or 0)),
        "criado_em": str(item.get("criado_em") or "").strip(),
    }


def listar_disciplinas(incluir_inativas: bool = False):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT id, nome, aulas_semanais, tem_apc, tem_prova_bimestral, ativo, criado_em
        FROM disciplinas
    """
    params = []

    if not incluir_inativas:
        query += " WHERE ativo = 1"

    query += " ORDER BY nome COLLATE NOCASE ASC"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [_mapear_disciplina(row) for row in rows]


def listar_disciplinas_ativas():
    return listar_disciplinas(incluir_inativas=False)


def buscar_disciplina_por_id(disciplina_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, nome, aulas_semanais, tem_apc, tem_prova_bimestral, ativo, criado_em
        FROM disciplinas
        WHERE id = ?
    """,
        (int(disciplina_id),),
    )

    row = cursor.fetchone()
    conn.close()
    return _mapear_disciplina(row) if row else None


def buscar_disciplina_por_nome(nome: str, incluir_inativas: bool = True):
    nome_limpo = _normalizar_nome_catalogo(nome)
    if not nome_limpo:
        return None

    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT id, nome, aulas_semanais, tem_apc, tem_prova_bimestral, ativo, criado_em
        FROM disciplinas
        WHERE nome = ? COLLATE NOCASE
    """
    params = [nome_limpo]
    if not incluir_inativas:
        query += " AND ativo = 1"
    query += " ORDER BY id ASC LIMIT 1"

    cursor.execute(query, params)
    row = cursor.fetchone()
    conn.close()
    return _mapear_disciplina(row) if row else None


def criar_disciplina(
    nome: str,
    aulas_semanais: int = 0,
    *,
    tem_apc: bool = False,
    tem_prova_bimestral: bool = False,
):
    nome_limpo = _normalizar_nome_catalogo(nome)
    if not nome_limpo:
        raise ValueError("Nome da disciplina é obrigatório.")
    aulas_semanais_valor = int(aulas_semanais or 0)
    if aulas_semanais_valor < 0:
        raise ValueError("Aulas semanais não pode ser negativo.")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO disciplinas (
            nome,
            aulas_semanais,
            tem_apc,
            tem_prova_bimestral,
            ativo,
            criado_em
        )
        VALUES (?, ?, ?, ?, 1, datetime('now'))
    """,
        (
            nome_limpo,
            aulas_semanais_valor,
            _normalizar_booleano_sql(tem_apc),
            _normalizar_booleano_sql(tem_prova_bimestral),
        ),
    )

    disciplina_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return disciplina_id


def atualizar_disciplina_dados(
    disciplina_id: int,
    aulas_semanais: int,
    *,
    tem_apc: bool | None = None,
    tem_prova_bimestral: bool | None = None,
):
    aulas_semanais_valor = int(aulas_semanais or 0)
    if aulas_semanais_valor < 0:
        raise ValueError("Aulas semanais não pode ser negativo.")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE disciplinas
        SET aulas_semanais = ?,
            tem_apc = COALESCE(?, tem_apc),
            tem_prova_bimestral = COALESCE(?, tem_prova_bimestral)
        WHERE id = ?
    """,
        (
            aulas_semanais_valor,
            _normalizar_booleano_sql(tem_apc) if tem_apc is not None else None,
            _normalizar_booleano_sql(tem_prova_bimestral)
            if tem_prova_bimestral is not None
            else None,
            disciplina_id,
        ),
    )

    alterado = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return alterado


def atualizar_status_disciplina(disciplina_id: int, ativo: bool):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE disciplinas
        SET ativo = ?
        WHERE id = ?
    """,
        (1 if ativo else 0, disciplina_id),
    )

    alterado = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return alterado


def gerar_token():
    return str(uuid.uuid4())


def listar_fila():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM jobs
        ORDER BY prioridade DESC, criado_em ASC
    """)

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def buscar_job(job_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))

    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def cancelar_job(job_id, estornar_cota: bool = True):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT usuario_id, paginas_totais, criado_em
        FROM jobs
        WHERE id = ?
    """,
        (job_id,),
    )
    job = cursor.fetchone()

    if not job:
        conn.close()
        return {
            "encontrado": False,
            "cancelado": False,
            "paginas_estornadas": 0,
        }

    cursor.execute(
        """
        UPDATE jobs
        SET status = 'CANCELADO'
        WHERE id = ? AND status = 'PENDENTE'
    """,
        (job_id,),
    )
    cancelado = cursor.rowcount > 0

    paginas_estornadas = 0
    if cancelado and estornar_cota:
        usuario_id_raw = job["usuario_id"]
        usuario_id = int(usuario_id_raw) if usuario_id_raw is not None else None
        paginas = max(int(job["paginas_totais"] or 0), 0)
        mes_referencia = str(job["criado_em"] or "")[:7]

        if paginas > 0 and usuario_id is not None and len(mes_referencia) == 7:
            cursor.execute(
                """
                UPDATE cotas
                SET usadas_paginas = MAX(usadas_paginas - ?, 0)
                WHERE usuario_id = ? AND mes = ?
            """,
                (paginas, usuario_id, mes_referencia),
            )
            paginas_estornadas = paginas

    conn.commit()
    conn.close()
    return {
        "encontrado": True,
        "cancelado": cancelado,
        "paginas_estornadas": paginas_estornadas,
    }


def alterar_prioridade(job_id, urgente):
    prioridade = 1 if urgente else 0

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE jobs
        SET prioridade = ?
        WHERE id = ? AND status = 'PENDENTE'
    """,
        (prioridade, job_id),
    )

    conn.commit()
    conn.close()


# Para impressão automática, busca o próximo job pendente já elegível para iniciar.
def buscar_proximo_job(atraso_minimo_segundos: int = 0):
    try:
        atraso_minimo = max(int(atraso_minimo_segundos), 0)
    except (TypeError, ValueError):
        atraso_minimo = 0

    conn = get_connection()
    cursor = conn.cursor()

    if atraso_minimo > 0:
        cursor.execute(
            """
            SELECT * FROM jobs
            WHERE status = 'PENDENTE'
              AND datetime(criado_em) <= datetime('now', ?)
            ORDER BY prioridade DESC, criado_em ASC
            LIMIT 1
        """,
            (f"-{atraso_minimo} seconds",),
        )
    else:
        cursor.execute("""
            SELECT * FROM jobs
            WHERE status = 'PENDENTE'
            ORDER BY prioridade DESC, criado_em ASC
            LIMIT 1
        """)

    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def atualizar_status(job_id, status):
    conn = get_connection()
    cursor = conn.cursor()

    if status in (STATUS_CONCLUIDO, STATUS_FINALIZADO_LEGADO):
        cursor.execute(
            """
            UPDATE jobs
            SET status = ?, finalizado_em = datetime('now'), erro_mensagem = NULL
            WHERE id = ?
        """,
            (status, job_id),
        )
    elif status == "ERRO":
        cursor.execute(
            """
            UPDATE jobs
            SET status = ?
            WHERE id = ?
        """,
            (status, job_id),
        )
    else:
        cursor.execute(
            """
            UPDATE jobs
            SET status = ?, erro_mensagem = NULL
            WHERE id = ?
        """,
            (status, job_id),
        )

    conn.commit()
    conn.close()


def atualizar_job_cups(job_id, cups_job_id, printer_name):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE jobs
        SET cups_job_id = ?, printer_name = ?
        WHERE id = ?
    """,
        (cups_job_id, printer_name or None, job_id),
    )

    conn.commit()
    conn.close()


def atualizar_erro_job(job_id, erro_mensagem: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE jobs
        SET erro_mensagem = ?
        WHERE id = ?
    """,
        (str(erro_mensagem)[:1000], job_id),
    )

    conn.commit()
    conn.close()


def buscar_cota(usuario_id: int, mes: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM cotas
        WHERE usuario_id = ? AND mes = ?
    """,
        (usuario_id, mes),
    )

    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def criar_cota(usuario_id: int, mes: str, limite: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO cotas (usuario_id, mes, limite_paginas, usadas_paginas)
        VALUES (?, ?, ?, 0)
    """,
        (usuario_id, mes, limite),
    )

    conn.commit()
    conn.close()


def consumir_cota(cota_id: int, paginas: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE cotas
        SET usadas_paginas = usadas_paginas + ?
        WHERE id = ?
    """,
        (paginas, cota_id),
    )

    conn.commit()
    conn.close()


def buscar_cota_do_usuario(usuario_id: int, mes: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT limite_paginas, usadas_paginas
        FROM cotas
        WHERE usuario_id = ? AND mes = ?
    """,
        (usuario_id, mes),
    )

    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def atualizar_limite_cota_mes(usuario_id: int, mes: str, limite_paginas: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, usadas_paginas
        FROM cotas
        WHERE usuario_id = ? AND mes = ?
    """,
        (usuario_id, mes),
    )
    row = cursor.fetchone()

    if row:
        usadas = int(row["usadas_paginas"])
        limite_final = max(int(limite_paginas), usadas)
        cursor.execute(
            """
            UPDATE cotas
            SET limite_paginas = ?
            WHERE id = ?
        """,
            (limite_final, row["id"]),
        )
    else:
        limite_final = max(int(limite_paginas), 0)
        cursor.execute(
            """
            INSERT INTO cotas (usuario_id, mes, limite_paginas, usadas_paginas)
            VALUES (?, ?, ?, 0)
        """,
            (usuario_id, mes, limite_final),
        )

    conn.commit()
    conn.close()


def recalcular_cotas_mes(mes: str):
    professores = listar_professores_admin()
    limites = calcular_limites_cota_professores()
    for professor in professores:
        limite = int(limites.get(int(professor["id"]), 0))
        atualizar_limite_cota_mes(professor["id"], mes, limite)


def gerar_relatorio_consumo():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            u.id AS usuario_id,
            u.nome,
            COALESCE(SUM(j.paginas_totais), 0) AS total_paginas
        FROM usuarios u
        LEFT JOIN jobs j
            ON j.usuario_id = u.id
           AND j.status IN (?, ?)
        GROUP BY u.id, u.nome
        ORDER BY total_paginas DESC, u.nome ASC
    """,
        (STATUS_CONCLUIDO, STATUS_FINALIZADO_LEGADO),
    )

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def gerar_relatorio_impressao(data_inicio: str = None, data_fim: str = None):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT
            u.id AS usuario_id,
            u.nome,
            COUNT(j.id) AS total_jobs,
            COALESCE(SUM(j.paginas_totais), 0) AS total_paginas
        FROM usuarios u
        LEFT JOIN jobs j
            ON j.usuario_id = u.id
           AND j.status IN (?, ?)
        WHERE u.perfil = 'professor'
    """
    params = [STATUS_CONCLUIDO, STATUS_FINALIZADO_LEGADO]

    if data_inicio:
        query += " AND date(j.criado_em) >= ?"
        params.append(data_inicio)

    if data_fim:
        query += " AND date(j.criado_em) <= ?"
        params.append(data_fim)

    query += """
        GROUP BY u.id, u.nome
        ORDER BY total_paginas DESC, total_jobs DESC, u.nome ASC
    """

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def _normalizar_tags_job(tags_json: str | None) -> list[str]:
    try:
        tags_brutas = json.loads(str(tags_json or "[]"))
    except (TypeError, ValueError, json.JSONDecodeError):
        return []

    if not isinstance(tags_brutas, list):
        return []

    tags_normalizadas = []
    vistos = set()
    for item in tags_brutas:
        tag = str(item or "").strip()
        if not tag:
            continue
        chave = tag.casefold()
        if chave in vistos:
            continue
        vistos.add(chave)
        tags_normalizadas.append(tag)
    return tags_normalizadas


def gerar_relatorio_tags_impressao(data_inicio: str = None, data_fim: str = None):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT
            j.tags_json,
            j.paginas_totais
        FROM jobs j
        WHERE j.status IN (?, ?)
    """
    params = [STATUS_CONCLUIDO, STATUS_FINALIZADO_LEGADO]

    if data_inicio:
        query += " AND date(j.criado_em) >= ?"
        params.append(data_inicio)

    if data_fim:
        query += " AND date(j.criado_em) <= ?"
        params.append(data_fim)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    agregados = {}
    for row in rows:
        paginas_totais = max(int(row["paginas_totais"] or 0), 0)
        for tag in _normalizar_tags_job(row["tags_json"]):
            chave = tag.casefold()
            if chave not in agregados:
                agregados[chave] = {
                    "tag": tag,
                    "total_jobs": 0,
                    "total_paginas": 0,
                }
            agregados[chave]["total_jobs"] += 1
            agregados[chave]["total_paginas"] += paginas_totais

    return sorted(
        agregados.values(),
        key=lambda item: (
            -int(item.get("total_jobs") or 0),
            -int(item.get("total_paginas") or 0),
            str(item.get("tag") or "").casefold(),
        ),
    )


def _listar_datas_periodo(data_inicio: str, data_fim: str) -> list[str]:
    inicio = date.fromisoformat(str(data_inicio))
    fim = date.fromisoformat(str(data_fim))
    datas = []
    atual = inicio

    while atual <= fim:
        datas.append(atual.isoformat())
        atual += timedelta(days=1)

    return datas


def _contar_dias_uteis_periodo(datas_iso: list[str]) -> int:
    dias_uteis = 0
    for item in datas_iso:
        if date.fromisoformat(item).weekday() < 5:
            dias_uteis += 1
    return dias_uteis


def _rotulo_periodo_curto(data_iso: str) -> str:
    try:
        valor = date.fromisoformat(str(data_iso))
    except ValueError:
        return str(data_iso or "")
    return valor.strftime("%d/%m")


def _professor_top_por_campo(itens: list[dict], campo: str) -> dict:
    for item in itens or []:
        valor = int(item.get(campo) or 0)
        if valor > 0:
            return {
                "usuario_id": int(item.get("usuario_id") or 0),
                "nome": str(item.get("nome") or "").strip(),
                "valor": valor,
                "total_jobs": int(item.get("total_jobs") or 0),
                "total_paginas": int(item.get("total_paginas") or 0),
                "total_reservas": int(item.get("total_reservas") or 0),
            }
    return {
        "usuario_id": 0,
        "nome": "Sem dados",
        "valor": 0,
        "total_jobs": 0,
        "total_paginas": 0,
        "total_reservas": 0,
    }


def _recurso_top(itens: list[dict]) -> dict:
    for item in itens or []:
        total_reservas = int(item.get("total_reservas") or 0)
        if total_reservas > 0:
            return {
                "recurso_id": int(item.get("recurso_id") or 0),
                "recurso_nome": str(item.get("recurso_nome") or "").strip(),
                "recurso_tipo": str(item.get("recurso_tipo") or "").strip(),
                "total_reservas": total_reservas,
                "percentual_uso": float(item.get("percentual_uso") or 0),
            }
    return {
        "recurso_id": 0,
        "recurso_nome": "Sem dados",
        "recurso_tipo": "",
        "total_reservas": 0,
        "percentual_uso": 0.0,
    }


def _criar_insight_relatorio(
    insight_id: str,
    titulo: str,
    texto: str,
    tipo: str = "informativo",
) -> dict:
    return {
        "id": str(insight_id or "").strip(),
        "titulo": str(titulo or "").strip(),
        "texto": str(texto or "").strip(),
        "tipo": str(tipo or "informativo").strip(),
    }


def _recurso_parece_sala_tecnologia(nome_recurso: str) -> bool:
    chave = _normalizar_texto_chave(nome_recurso)
    return "sala de tecnologia" in chave or chave.startswith("ste ") or " ste " in f" {chave} "


def _capacidade_aulas_por_dia_recurso(nome_recurso: str) -> int:
    if _recurso_parece_sala_tecnologia(nome_recurso):
        return RELATORIOS_CAPACIDADE_AULAS_DIA_SALA_TECNOLOGIA
    return RELATORIOS_CAPACIDADE_AULAS_DIA


def _descricao_base_capacidade_relatorios() -> str:
    return (
        f"Base estimada por recurso: {RELATORIOS_CAPACIDADE_AULAS_DIA} uso(s) por dia util; "
        f"Sala de Tecnologia: {RELATORIOS_CAPACIDADE_AULAS_DIA_SALA_TECNOLOGIA}."
    )


def _parse_datetime_relatorios(valor: str):
    texto = str(valor or "").strip()
    if not texto:
        return None

    formatos = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d",
    )
    for formato in formatos:
        try:
            return datetime.strptime(texto, formato)
        except ValueError:
            continue
    return None


def _rotulo_situacao_relatorio_anexos(prazo_envio: str, envio: dict | None) -> dict:
    if not envio:
        return {"id": "pendente", "label": "Pendente", "ordem": 2}

    prazo_dt = _parse_datetime_relatorios(prazo_envio)
    enviado_dt = _parse_datetime_relatorios(envio.get("enviado_em"))
    if prazo_dt and enviado_dt and enviado_dt > prazo_dt:
        return {"id": "atrasado", "label": "Atrasado", "ordem": 1}
    return {"id": "no_prazo", "label": "No prazo", "ordem": 0}


def _descricao_documento_relatorio_anexos(periodo: dict, item: dict) -> str:
    titulo = str(periodo.get("titulo") or "Documento").strip() or "Documento"
    disciplina = str(item.get("disciplina_nome") or "").strip()
    turma = str(item.get("turma_nome") or "").strip()

    contexto = []
    if disciplina:
        contexto.append(disciplina)
    if turma:
        contexto.append(turma)

    if not contexto:
        return titulo
    return f"{titulo} | {' | '.join(contexto)}"


def _obter_elegiveis_periodo_apc_relatorios(periodo: dict) -> list[dict]:
    from services.apc_service import (
        APC_PUBLICO_ALVO_TODOS_PROFESSORES,
        APC_PUBLICO_ALVO_PROFESSORES_SELECIONADOS,
        agrupar_destinatarios_selecionados_apc,
        agrupar_horarios_professor_dia,
        agrupar_professores_elegiveis,
        enriquecer_periodo_apc,
        filtrar_horarios_por_tipo_entrega,
    )

    periodo_norm = enriquecer_periodo_apc(periodo)
    if periodo_norm["publico_alvo"] == APC_PUBLICO_ALVO_TODOS_PROFESSORES:
        return agrupar_professores_elegiveis(listar_professores_agendamento())
    if periodo_norm["publico_alvo"] == APC_PUBLICO_ALVO_PROFESSORES_SELECIONADOS:
        return agrupar_destinatarios_selecionados_apc(
            listar_apc_destinatarios(periodo_id=int(periodo_norm["id"]))
        )

    horarios = listar_horarios_escolares(
        ano_letivo=int(periodo_norm["ano_letivo"]),
        dia_semana=periodo_norm["dia_semana"],
    )
    horarios_filtrados = filtrar_horarios_por_tipo_entrega(
        horarios,
        periodo_norm["tipo_entrega"],
    )
    return agrupar_horarios_professor_dia(horarios_filtrados)


def gerar_relatorio_anexos(data_inicio: str | None = None, data_fim: str | None = None):
    from services.apc_service import enriquecer_periodo_apc, montar_painel_periodo_apc

    hoje = date.today()
    inicio_periodo = str(data_inicio or hoje.replace(day=1).isoformat())
    fim_periodo = str(data_fim or hoje.isoformat())

    if inicio_periodo > fim_periodo:
        raise ValueError("Periodo invalido: data inicial maior que data final.")

    datas_periodo = _listar_datas_periodo(inicio_periodo, fim_periodo)
    periodos = []
    try:
        periodos = [enriquecer_periodo_apc(item) for item in listar_apc_periodos(
            data_inicio=inicio_periodo,
            data_fim=fim_periodo,
        )]
    except sqlite3.OperationalError:
        periodos = []

    periodos_ids = [int(item.get("id") or 0) for item in periodos if int(item.get("id") or 0) > 0]
    envios_por_periodo: dict[int, list[dict]] = {}
    if periodos_ids:
        conn = None
        try:
            placeholders = ",".join("?" for _ in periodos_ids)
            conn = get_connection()
            cursor = conn.cursor()
            envios = _consultar_apc_envios(
                cursor,
                filtros_sql=[f"ae.periodo_id IN ({placeholders})"],
                params=periodos_ids,
            )
        except sqlite3.OperationalError:
            envios = []
        finally:
            if conn is not None:
                conn.close()

        for envio in envios:
            periodo_id = int(envio.get("periodo_id") or 0)
            envios_por_periodo.setdefault(periodo_id, []).append(envio)

    total_esperados = 0
    total_entregues = 0
    total_no_prazo = 0
    total_atrasadas = 0
    total_pendencias = 0
    contagem_por_tipo: dict[str, int] = {}
    itens_consolidados = []

    for periodo in periodos:
        try:
            elegiveis = _obter_elegiveis_periodo_apc_relatorios(periodo)
        except sqlite3.OperationalError:
            elegiveis = []

        painel = montar_painel_periodo_apc(
            periodo,
            elegiveis,
            envios_por_periodo.get(int(periodo.get("id") or 0), []),
        )
        periodo_painel = painel["periodo"]
        tipo_documento = str(periodo_painel.get("tipo_entrega_label") or "Nao informado").strip()

        total_esperados += int(painel.get("total_elegiveis") or 0)
        total_entregues += int(painel.get("total_enviados") or 0)
        total_pendencias += int(painel.get("total_pendentes") or 0)
        contagem_por_tipo[tipo_documento] = (
            int(contagem_por_tipo.get(tipo_documento) or 0)
            + int(painel.get("total_elegiveis") or 0)
        )

        for item in painel.get("itens") or []:
            envio = item.get("envio")
            situacao = _rotulo_situacao_relatorio_anexos(periodo_painel.get("prazo_envio"), envio)
            if situacao["id"] == "no_prazo":
                total_no_prazo += 1
            elif situacao["id"] == "atrasado":
                total_atrasadas += 1

            itens_consolidados.append(
                {
                    "periodo_id": int(periodo_painel.get("id") or 0),
                    "professor": str(item.get("professor_nome") or "").strip() or "Professor nao informado",
                    "documento": _descricao_documento_relatorio_anexos(periodo_painel, item),
                    "prazo": str(periodo_painel.get("prazo_envio") or "").strip(),
                    "data_envio": str((envio or {}).get("enviado_em") or "").strip(),
                    "situacao": situacao["label"],
                    "situacao_id": situacao["id"],
                    "situacao_ordem": int(situacao["ordem"] or 0),
                    "tipo_documento": tipo_documento,
                }
            )

    percentual_cumprimento_prazo = (
        round((total_no_prazo / total_esperados) * 100, 1) if total_esperados > 0 else 0.0
    )

    professores_pendencias = [
        {
            "professor": item["professor"],
            "documento": item["documento"],
            "prazo": item["prazo"],
            "situacao": item["situacao"],
        }
        for item in sorted(
            [item for item in itens_consolidados if item["situacao_id"] == "pendente"],
            key=lambda item: (
                _parse_datetime_relatorios(item.get("prazo")) or datetime.max,
                str(item.get("professor") or "").casefold(),
                str(item.get("documento") or "").casefold(),
            ),
        )
    ]

    entregas_recentes = [
        {
            "professor": item["professor"],
            "documento": item["documento"],
            "data_envio": item["data_envio"],
            "prazo": item["prazo"],
            "situacao": item["situacao"],
        }
        for item in sorted(
            itens_consolidados,
            key=lambda item: (
                _parse_datetime_relatorios(item.get("data_envio"))
                or _parse_datetime_relatorios(item.get("prazo"))
                or datetime.min,
                -int(item.get("situacao_ordem") or 0),
                str(item.get("professor") or "").casefold(),
            ),
            reverse=True,
        )
    ]

    tipos_ordenados = sorted(
        contagem_por_tipo.items(),
        key=lambda item: (-int(item[1] or 0), str(item[0] or "").casefold()),
    )

    cards = [
        {
            "id": "documentos_esperados",
            "titulo": "Documentos esperados",
            "valor": total_esperados,
            "descricao": f"{len(periodos)} solicitacao(oes) no periodo",
        },
        {
            "id": "documentos_entregues",
            "titulo": "Documentos entregues",
            "valor": total_entregues,
            "descricao": "Arquivos registrados na Central de Anexos",
        },
        {
            "id": "entregas_no_prazo",
            "titulo": "Entregas no prazo",
            "valor": total_no_prazo,
            "descricao": "Envios realizados dentro do prazo",
        },
        {
            "id": "entregas_atrasadas",
            "titulo": "Entregas atrasadas",
            "valor": total_atrasadas,
            "descricao": "Envios registrados apos o prazo",
        },
        {
            "id": "pendencias",
            "titulo": "Pendencias",
            "valor": total_pendencias,
            "descricao": "Documentos esperados ainda sem envio",
        },
        {
            "id": "cumprimento_no_prazo",
            "titulo": "Cumprimento no prazo",
            "valor": f"{percentual_cumprimento_prazo:.1f}%",
            "descricao": "Percentual calculado sobre os documentos esperados",
        },
    ]

    return {
        "periodo": {
            "data_inicio": inicio_periodo,
            "data_fim": fim_periodo,
            "dias_periodo": len(datas_periodo),
            "total_solicitacoes": len(periodos),
        },
        "cards": cards,
        "resumo": {
            "total_documentos_esperados": total_esperados,
            "total_documentos_entregues": total_entregues,
            "total_entregas_no_prazo": total_no_prazo,
            "total_entregas_atrasadas": total_atrasadas,
            "total_pendencias": total_pendencias,
            "percentual_cumprimento_prazo": percentual_cumprimento_prazo,
        },
        "tabelas": {
            "professores_pendencias": professores_pendencias,
            "entregas_recentes": entregas_recentes,
        },
        "graficos": {
            "situacao_entregas": {
                "labels": ["No prazo", "Atrasadas", "Pendentes"],
                "valores": [total_no_prazo, total_atrasadas, total_pendencias],
            },
            "documentos_por_tipo": {
                "labels": [item[0] for item in tipos_ordenados],
                "valores": [int(item[1] or 0) for item in tipos_ordenados],
            },
        },
    }


def _gerar_insights_gestao_relatorios(
    *,
    dias_uteis: int,
    total_paginas: int,
    total_reservas: int,
    total_professores_impressoes: int,
    top_impressao: dict,
    ranking_recursos_visiveis: list[dict],
) -> list[dict]:
    if total_paginas <= 0 and total_reservas <= 0:
        return [
            _criar_insight_relatorio(
                "dados_insuficientes",
                "Dados insuficientes",
                "Ainda não há dados suficientes para gerar insights neste período.",
                "informativo",
            )
        ]

    insights = []

    limite_paginas_elevadas = max(
        RELATORIOS_INSIGHT_PAGINAS_ELEVADAS_MIN,
        max(int(dias_uteis or 0), 1) * RELATORIOS_INSIGHT_PAGINAS_ELEVADAS_POR_DIA_UTIL,
    )
    if total_paginas >= limite_paginas_elevadas:
        insights.append(
            _criar_insight_relatorio(
                "volume_impressoes_elevado",
                "Volume de impressões elevado",
                (
                    "O volume de impressões no período está elevado. Recomenda-se acompanhar "
                    "o uso de papel e estimular alternativas digitais quando possível."
                ),
                "atencao",
            )
        )

    paginas_top_impressao = int(top_impressao.get("total_paginas") or 0)
    percentual_top_impressao = 0.0
    if total_paginas > 0:
        percentual_top_impressao = (paginas_top_impressao / total_paginas) * 100
    if (
        total_professores_impressoes >= 2
        and percentual_top_impressao >= RELATORIOS_INSIGHT_CONCENTRACAO_IMPRESSAO_PERCENTUAL
    ):
        insights.append(
            _criar_insight_relatorio(
                "concentracao_impressoes",
                "Concentração de impressões",
                "Há concentração significativa de impressões em poucos professores.",
                "atencao",
            )
        )

    if total_reservas > 0:
        recursos_alta_demanda = [
            item
            for item in ranking_recursos_visiveis
            if float(item.get("percentual_uso") or 0)
            >= RELATORIOS_INSIGHT_OCUPACAO_ALTA_PERCENTUAL
        ]
        if recursos_alta_demanda:
            recurso_alta_demanda = recursos_alta_demanda[0]
            nome_recurso = str(recurso_alta_demanda.get("recurso_nome") or "").strip()
            if _recurso_parece_sala_tecnologia(nome_recurso):
                titulo = "Alta demanda da Sala de Tecnologia"
                texto = "A Sala de Tecnologia apresentou alta demanda no período."
            else:
                titulo = "Recurso com alta ocupação"
                texto = f'O recurso "{nome_recurso}" apresentou alta demanda no período.'
            insights.append(
                _criar_insight_relatorio(
                    "alta_ocupacao_recurso",
                    titulo,
                    texto,
                    "observacao",
                )
            )

        recursos_baixo_uso = [
            item
            for item in ranking_recursos_visiveis
            if bool(item.get("ativo"))
            and float(item.get("percentual_uso") or 0) <= RELATORIOS_INSIGHT_BAIXO_USO_PERCENTUAL
        ]
        if len(ranking_recursos_visiveis) >= 2 and recursos_baixo_uso:
            insights.append(
                _criar_insight_relatorio(
                    "baixo_uso_recursos",
                    "Baixa utilização de recursos",
                    "Existem recursos tecnológicos com baixa utilização no período.",
                    "oportunidade",
                )
            )

    if insights:
        return insights

    return [
        _criar_insight_relatorio(
            "sem_alertas_relevantes",
            "Sem alertas relevantes",
            "Os indicadores atuais não apontam alertas relevantes neste período.",
            "informativo",
        )
    ]


def gerar_dashboard_relatorios(data_inicio: str | None = None, data_fim: str | None = None):
    hoje = date.today()
    inicio_periodo = str(data_inicio or hoje.replace(day=1).isoformat())
    fim_periodo = str(data_fim or hoje.isoformat())

    if inicio_periodo > fim_periodo:
        raise ValueError("Periodo invalido: data inicial maior que data final.")

    datas_periodo = _listar_datas_periodo(inicio_periodo, fim_periodo)
    dias_uteis = _contar_dias_uteis_periodo(datas_periodo)

    ranking_impressao = gerar_relatorio_impressao(inicio_periodo, fim_periodo)
    ranking_tags_impressao = gerar_relatorio_tags_impressao(inicio_periodo, fim_periodo)
    ranking_recursos = gerar_relatorio_uso_recursos(inicio_periodo, fim_periodo)
    ranking_recursos_professor = gerar_relatorio_uso_recursos_por_professor(
        inicio_periodo, fim_periodo
    )
    recursos_catalogo = {
        int(item["id"]): item for item in listar_recursos(incluir_inativos=True)
    }

    ranking_impressao_ativo = [
        {
            **item,
            "usuario_id": int(item.get("usuario_id") or 0),
            "nome": str(item.get("nome") or "").strip(),
            "total_jobs": int(item.get("total_jobs") or 0),
            "total_paginas": int(item.get("total_paginas") or 0),
        }
        for item in ranking_impressao
        if int(item.get("total_jobs") or 0) > 0 or int(item.get("total_paginas") or 0) > 0
    ]

    ranking_recursos_professor_ativo = [
        {
            **item,
            "usuario_id": int(item.get("usuario_id") or 0),
            "nome": str(item.get("nome") or "").strip(),
            "total_reservas": int(item.get("total_reservas") or 0),
        }
        for item in ranking_recursos_professor
        if int(item.get("total_reservas") or 0) > 0
    ]

    ranking_recursos_enriquecido = []
    for item in ranking_recursos:
        recurso_id = int(item.get("recurso_id") or 0)
        recurso_catalogo = recursos_catalogo.get(recurso_id, {})
        recurso_nome = str(item.get("recurso_nome") or "").strip()
        quantidade_itens = max(int(recurso_catalogo.get("quantidade_itens") or 1), 1)
        ativo = bool(int(recurso_catalogo.get("ativo", 1) or 0))
        total_reservas = int(item.get("total_reservas") or 0)
        capacidade_aulas_dia = _capacidade_aulas_por_dia_recurso(recurso_nome)
        capacidade_periodo = dias_uteis * capacidade_aulas_dia * quantidade_itens
        percentual_uso = 0.0
        if capacidade_periodo > 0:
            percentual_uso = round((total_reservas / capacidade_periodo) * 100, 1)

        ranking_recursos_enriquecido.append(
            {
                "recurso_id": recurso_id,
                "recurso_nome": recurso_nome,
                "recurso_tipo": str(item.get("recurso_tipo") or "").strip(),
                "total_reservas": total_reservas,
                "professores_distintos": int(item.get("professores_distintos") or 0),
                "quantidade_itens": quantidade_itens,
                "ativo": ativo,
                "capacidade_aulas_dia": capacidade_aulas_dia,
                "capacidade_periodo": capacidade_periodo,
                "percentual_uso": percentual_uso,
            }
        )

    ranking_recursos_visiveis = [
        item
        for item in ranking_recursos_enriquecido
        if item["ativo"] or item["total_reservas"] > 0
    ]
    ranking_recursos_visiveis = sorted(
        ranking_recursos_visiveis,
        key=lambda item: (
            -int(item.get("total_reservas") or 0),
            -float(item.get("percentual_uso") or 0),
            str(item.get("recurso_nome") or "").casefold(),
        ),
    )

    total_paginas = sum(int(item.get("total_paginas") or 0) for item in ranking_impressao_ativo)
    total_jobs = sum(int(item.get("total_jobs") or 0) for item in ranking_impressao_ativo)
    total_reservas = sum(int(item.get("total_reservas") or 0) for item in ranking_recursos_visiveis)
    total_professores_impressoes = len(ranking_impressao_ativo)
    total_professores_recursos = len(ranking_recursos_professor_ativo)
    total_recursos_utilizados = len(
        [item for item in ranking_recursos_visiveis if item["total_reservas"] > 0]
    )
    capacidade_total_recursos = sum(
        int(item.get("capacidade_periodo") or 0) for item in ranking_recursos_visiveis
    )
    taxa_uso_geral = 0.0
    if capacidade_total_recursos > 0:
        taxa_uso_geral = round((total_reservas / capacidade_total_recursos) * 100, 1)

    top_impressao = _professor_top_por_campo(ranking_impressao_ativo, "total_paginas")
    top_tag_impressao = (
        ranking_tags_impressao[0]
        if ranking_tags_impressao
        else {"tag": "Sem dados", "total_jobs": 0, "total_paginas": 0}
    )
    top_recurso_professor = _professor_top_por_campo(
        ranking_recursos_professor_ativo,
        "total_reservas",
    )
    top_recurso = _recurso_top(ranking_recursos_visiveis)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            date(j.criado_em) AS data,
            COUNT(j.id) AS total_jobs,
            COALESCE(SUM(j.paginas_totais), 0) AS total_paginas
        FROM jobs j
        WHERE j.status IN (?, ?)
          AND date(j.criado_em) >= ?
          AND date(j.criado_em) <= ?
        GROUP BY date(j.criado_em)
        ORDER BY date(j.criado_em) ASC
    """,
        (STATUS_CONCLUIDO, STATUS_FINALIZADO_LEGADO, inicio_periodo, fim_periodo),
    )
    serie_impressoes_rows = [dict(row) for row in cursor.fetchall()]

    cursor.execute(
        """
        SELECT
            a.data,
            COUNT(a.id) AS total_reservas
        FROM agendamentos a
        WHERE a.status = ?
          AND a.data >= ?
          AND a.data <= ?
        GROUP BY a.data
        ORDER BY a.data ASC
    """,
        (STATUS_AGENDAMENTO_ATIVO, inicio_periodo, fim_periodo),
    )
    serie_recursos_rows = [dict(row) for row in cursor.fetchall()]
    conn.close()

    serie_impressoes_por_data = {
        str(item.get("data") or ""): {
            "total_jobs": int(item.get("total_jobs") or 0),
            "total_paginas": int(item.get("total_paginas") or 0),
        }
        for item in serie_impressoes_rows
    }
    serie_recursos_por_data = {
        str(item.get("data") or ""): int(item.get("total_reservas") or 0)
        for item in serie_recursos_rows
    }

    labels_periodo = [_rotulo_periodo_curto(item) for item in datas_periodo]
    serie_paginas = []
    serie_jobs = []
    serie_reservas = []
    for data_iso in datas_periodo:
        registro_impressao = serie_impressoes_por_data.get(
            data_iso, {"total_jobs": 0, "total_paginas": 0}
        )
        serie_paginas.append(int(registro_impressao.get("total_paginas") or 0))
        serie_jobs.append(int(registro_impressao.get("total_jobs") or 0))
        serie_reservas.append(int(serie_recursos_por_data.get(data_iso) or 0))

    media_paginas_por_job = round((total_paginas / total_jobs), 1) if total_jobs > 0 else 0.0
    media_reservas_por_dia = (
        round((total_reservas / len(datas_periodo)), 1) if len(datas_periodo) > 0 else 0.0
    )

    cards = [
        {
            "id": "paginas_impressas",
            "titulo": "Paginas impressas",
            "valor": total_paginas,
            "descricao": f"{total_jobs} job(s) concluidos no periodo",
        },
        {
            "id": "reservas_recursos",
            "titulo": "Reservas de recursos",
            "valor": total_reservas,
            "descricao": f"{total_recursos_utilizados} recurso(s) com uso registrado",
        },
        {
            "id": "top_impressao",
            "titulo": "Professor que mais imprime",
            "valor": top_impressao["nome"],
            "descricao": f"{top_impressao['total_paginas']} pagina(s) no periodo",
        },
        {
            "id": "top_tag_impressao",
            "titulo": "Tipo mais impresso",
            "valor": top_tag_impressao["tag"],
            "descricao": f"{top_tag_impressao['total_jobs']} job(s) classificados no periodo",
        },
        {
            "id": "top_recurso_professor",
            "titulo": "Professor que mais usa recursos",
            "valor": top_recurso_professor["nome"],
            "descricao": f"{top_recurso_professor['total_reservas']} reserva(s) no periodo",
        },
        {
            "id": "recurso_top",
            "titulo": "Recurso tecnologico mais usado",
            "valor": top_recurso["recurso_nome"],
            "descricao": f"{top_recurso['total_reservas']} reserva(s) no periodo",
        },
        {
            "id": "taxa_uso_recursos",
            "titulo": "Capacidade de uso dos recursos",
            "valor": f"{taxa_uso_geral:.1f}%",
            "descricao": _descricao_base_capacidade_relatorios(),
        },
    ]
    insights_gestao = _gerar_insights_gestao_relatorios(
        dias_uteis=dias_uteis,
        total_paginas=total_paginas,
        total_reservas=total_reservas,
        total_professores_impressoes=total_professores_impressoes,
        top_impressao=top_impressao,
        ranking_recursos_visiveis=ranking_recursos_visiveis,
    )

    return {
        "periodo": {
            "data_inicio": inicio_periodo,
            "data_fim": fim_periodo,
            "dias_periodo": len(datas_periodo),
            "dias_uteis": dias_uteis,
            "capacidade_aulas_por_dia": RELATORIOS_CAPACIDADE_AULAS_DIA,
            "capacidade_aulas_por_dia_padrao": RELATORIOS_CAPACIDADE_AULAS_DIA,
            "capacidade_aulas_por_dia_sala_tecnologia": RELATORIOS_CAPACIDADE_AULAS_DIA_SALA_TECNOLOGIA,
            "descricao_capacidade": _descricao_base_capacidade_relatorios(),
        },
        "cards": cards,
        "dashboard_geral": {
            "insights": insights_gestao,
            "graficos": {
                "impressoes_por_professor": {
                    "labels": [item["nome"] for item in ranking_impressao_ativo[:7]],
                    "valores": [item["total_paginas"] for item in ranking_impressao_ativo[:7]],
                },
                "tags_impressao": {
                    "labels": [item["tag"] for item in ranking_tags_impressao[:7]],
                    "valores": [item["total_jobs"] for item in ranking_tags_impressao[:7]],
                },
                "reservas_por_recurso": {
                    "labels": [item["recurso_nome"] for item in ranking_recursos_visiveis[:7]],
                    "valores": [item["total_reservas"] for item in ranking_recursos_visiveis[:7]],
                },
                "movimento_periodo": {
                    "labels": labels_periodo,
                    "paginas": serie_paginas,
                    "reservas": serie_reservas,
                },
                "utilizacao_recursos": {
                    "labels": [item["recurso_nome"] for item in ranking_recursos_visiveis[:7]],
                    "valores": [item["percentual_uso"] for item in ranking_recursos_visiveis[:7]],
                },
            }
        },
        "impressoes": {
            "resumo": {
                "total_paginas": total_paginas,
                "total_jobs": total_jobs,
                "media_paginas_por_job": media_paginas_por_job,
                "professores_com_impressoes": total_professores_impressoes,
                "tags_utilizadas": len(ranking_tags_impressao),
                "tag_mais_frequente": top_tag_impressao["tag"],
            },
            "ranking_professores": ranking_impressao_ativo,
            "ranking_tags": ranking_tags_impressao,
            "serie_diaria": {
                "labels": labels_periodo,
                "paginas": serie_paginas,
                "jobs": serie_jobs,
            },
        },
        "recursos": {
            "resumo": {
                "total_reservas": total_reservas,
                "professores_com_reservas": total_professores_recursos,
                "recursos_utilizados": total_recursos_utilizados,
                "taxa_uso_geral": taxa_uso_geral,
                "media_reservas_por_dia": media_reservas_por_dia,
            },
            "ranking_recursos": ranking_recursos_visiveis,
            "ranking_professores": ranking_recursos_professor_ativo,
            "serie_diaria": {
                "labels": labels_periodo,
                "reservas": serie_reservas,
            },
        },
        "futuro": {
            "abas": [
                {"id": "dashboard", "label": "Dashboard Geral", "habilitado": True},
                {"id": "impressoes", "label": "Impressoes", "habilitado": True},
                {"id": "recursos", "label": "Recursos Tecnologicos", "habilitado": True},
                {"id": "anexos", "label": "Central de Anexos", "habilitado": True},
                {"id": "coordenacao", "label": "Coordenacao", "habilitado": False},
                {"id": "ocorrencias", "label": "Ocorrencias", "habilitado": False},
                {"id": "preconselho", "label": "Pre-Conselho", "habilitado": False},
            ],
            "exportacoes": [
                {"id": "pdf", "label": "PDF", "habilitado": False},
                {"id": "excel", "label": "Excel", "habilitado": False},
            ],
        },
    }


def gerar_relatorio_uso_recursos(data_inicio: str = None, data_fim: str = None):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT
            r.id AS recurso_id,
            r.nome AS recurso_nome,
            r.tipo AS recurso_tipo,
            COUNT(a.id) AS total_reservas,
            COUNT(DISTINCT a.usuario_id) AS professores_distintos
        FROM recursos r
        LEFT JOIN agendamentos a
            ON a.recurso_id = r.id
           AND a.status = ?
    """
    params = [STATUS_AGENDAMENTO_ATIVO]

    if data_inicio:
        query += " AND a.data >= ?"
        params.append(data_inicio)

    if data_fim:
        query += " AND a.data <= ?"
        params.append(data_fim)

    query += """
        GROUP BY r.id, r.nome, r.tipo
        ORDER BY total_reservas DESC, r.nome ASC
    """

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def gerar_relatorio_uso_recursos_por_professor(data_inicio: str = None, data_fim: str = None):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT
            u.id AS usuario_id,
            u.nome,
            COUNT(a.id) AS total_reservas
        FROM usuarios u
        LEFT JOIN agendamentos a
            ON a.usuario_id = u.id
           AND a.status = ?
        WHERE u.perfil = 'professor'
    """
    params = [STATUS_AGENDAMENTO_ATIVO]

    if data_inicio:
        query += " AND a.data >= ?"
        params.append(data_inicio)

    if data_fim:
        query += " AND a.data <= ?"
        params.append(data_fim)

    query += """
        GROUP BY u.id, u.nome
        ORDER BY total_reservas DESC, u.nome ASC
    """

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def listar_recursos_ativos():
    return listar_recursos(incluir_inativos=False)


def listar_recursos(incluir_inativos: bool = False):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT
            id,
            nome,
            tipo,
            COALESCE(descricao, '') AS descricao,
            CASE WHEN COALESCE(quantidade_itens, 1) < 1 THEN 1 ELSE quantidade_itens END AS quantidade_itens,
            ativo
        FROM recursos
    """
    params = []
    if not incluir_inativos:
        query += " WHERE ativo = 1"
    query += " ORDER BY nome ASC"

    cursor.execute(query, params)

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def criar_recurso(nome: str, tipo: str, descricao: str = "", quantidade_itens: int = 1):
    quantidade_itens_valor = max(int(quantidade_itens or 0), 1)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO recursos (nome, tipo, descricao, quantidade_itens, ativo)
        VALUES (?, ?, ?, ?, 1)
    """,
        (nome, tipo, descricao, quantidade_itens_valor),
    )

    recurso_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return recurso_id


def atualizar_recurso_dados(
    recurso_id: int, nome: str, tipo: str, descricao: str = "", quantidade_itens: int = 1
):
    quantidade_itens_valor = max(int(quantidade_itens or 0), 1)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE recursos
        SET nome = ?, tipo = ?, descricao = ?, quantidade_itens = ?
        WHERE id = ?
    """,
        (nome, tipo, descricao, quantidade_itens_valor, recurso_id),
    )

    alterados = cursor.rowcount
    conn.commit()
    conn.close()
    return alterados > 0


def atualizar_recurso_quantidade_itens(recurso_id: int, quantidade_itens: int):
    quantidade_itens_valor = max(int(quantidade_itens or 0), 1)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE recursos
        SET quantidade_itens = ?
        WHERE id = ?
    """,
        (quantidade_itens_valor, recurso_id),
    )

    alterados = cursor.rowcount
    conn.commit()
    conn.close()
    return alterados > 0


def atualizar_status_recurso(recurso_id: int, ativo: bool):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE recursos
        SET ativo = ?
        WHERE id = ?
    """,
        (1 if ativo else 0, recurso_id),
    )

    alterados = cursor.rowcount
    conn.commit()
    conn.close()
    return alterados > 0


def buscar_recurso_por_id(recurso_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            nome,
            tipo,
            COALESCE(descricao, '') AS descricao,
            CASE WHEN COALESCE(quantidade_itens, 1) < 1 THEN 1 ELSE quantidade_itens END AS quantidade_itens,
            ativo
        FROM recursos
        WHERE id = ?
    """,
        (recurso_id,),
    )

    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def listar_regimento_itens(incluir_inativos: bool = True):
    conn = get_connection()
    cursor = conn.cursor()
    rows = _listar_itens_base_legal_cursor(cursor)
    conn.close()
    return rows


def _montar_lei_base_legal(row: sqlite3.Row | dict) -> dict:
    dados = dict(row)
    nome = str(dados.get("nome") or "").strip()
    return {
        "id": int(dados.get("id") or 0),
        "nome": nome,
        "label": nome,
    }


def _montar_artigo_base_legal(row: sqlite3.Row | dict) -> dict:
    dados = dict(row)
    lei_nome = str(dados.get("lei_nome") or "").strip()
    numero = str(dados.get("numero") or "").strip()
    descricao = str(dados.get("descricao") or "").strip()
    referencia = _montar_rotulo_base_legal(lei_nome, numero)
    return {
        "id": int(dados.get("id") or 0),
        "lei_id": int(dados.get("lei_id") or 0),
        "lei_nome": lei_nome,
        "numero": numero,
        "descricao": descricao,
        "referencia": referencia,
        "label": referencia,
    }


def _montar_inciso_base_legal(row: sqlite3.Row | dict) -> dict:
    dados = dict(row)
    lei_nome = str(dados.get("lei_nome") or "").strip()
    artigo_numero = str(dados.get("artigo_numero") or "").strip()
    artigo_descricao = str(dados.get("artigo_descricao") or "").strip()
    numero = str(dados.get("numero") or "").strip()
    descricao = str(dados.get("descricao") or "").strip()
    referencia = _montar_rotulo_base_legal(lei_nome, artigo_numero, numero)
    return {
        "id": int(dados.get("id") or 0),
        "artigo_id": int(dados.get("artigo_id") or 0),
        "lei_id": int(dados.get("lei_id") or 0),
        "lei_nome": lei_nome,
        "artigo_numero": artigo_numero,
        "artigo_descricao": artigo_descricao,
        "numero": numero,
        "descricao": descricao,
        "referencia": referencia,
        "label": referencia,
    }


def _montar_alinea_base_legal(row: sqlite3.Row | dict) -> dict:
    dados = dict(row)
    lei_nome = str(dados.get("lei_nome") or "").strip()
    artigo_numero = str(dados.get("artigo_numero") or "").strip()
    inciso_numero = str(dados.get("inciso_numero") or "").strip()
    inciso_descricao = str(dados.get("inciso_descricao") or "").strip()
    identificador = str(dados.get("identificador") or "").strip()
    descricao = str(dados.get("descricao") or "").strip()
    referencia = _montar_rotulo_base_legal(lei_nome, artigo_numero, inciso_numero, identificador)
    return {
        "id": int(dados.get("id") or 0),
        "inciso_id": int(dados.get("inciso_id") or 0),
        "artigo_id": int(dados.get("artigo_id") or 0),
        "lei_id": int(dados.get("lei_id") or 0),
        "lei_nome": lei_nome,
        "artigo_numero": artigo_numero,
        "inciso_numero": inciso_numero,
        "inciso_descricao": inciso_descricao,
        "identificador": identificador,
        "descricao": descricao,
        "referencia": referencia,
        "label": referencia,
    }


def listar_leis():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, nome
        FROM leis
        ORDER BY LOWER(nome), id
    """)
    rows = [_montar_lei_base_legal(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def buscar_lei_por_id(lei_id: int):
    lei_id_valor = int(lei_id or 0)
    if lei_id_valor <= 0:
        return None
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, nome
        FROM leis
        WHERE id = ?
    """,
        (lei_id_valor,),
    )
    row = cursor.fetchone()
    conn.close()
    return _montar_lei_base_legal(row) if row else None


def criar_lei(nome: str):
    nome_limpo = _normalizar_nome_catalogo(nome)
    if not nome_limpo:
        raise ValueError("Nome da lei e obrigatorio.")

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO leis (nome) VALUES (?)", (nome_limpo,))
    except sqlite3.IntegrityError as exc:
        conn.close()
        raise ValueError("Ja existe uma lei com este nome.") from exc
    conn.commit()
    lei_id = int(cursor.lastrowid)
    conn.close()
    return lei_id


def atualizar_lei(lei_id: int, nome: str):
    lei_id_valor = int(lei_id or 0)
    if lei_id_valor <= 0:
        return False
    nome_limpo = _normalizar_nome_catalogo(nome)
    if not nome_limpo:
        raise ValueError("Nome da lei e obrigatorio.")

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE leis SET nome = ? WHERE id = ?",
            (nome_limpo, lei_id_valor),
        )
    except sqlite3.IntegrityError as exc:
        conn.close()
        raise ValueError("Ja existe uma lei com este nome.") from exc
    alterado = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return alterado


def listar_artigos(lei_id: int | None = None):
    conn = get_connection()
    cursor = conn.cursor()
    params: list[int] = []
    sql = """
        SELECT
            a.id,
            a.lei_id,
            l.nome AS lei_nome,
            a.numero,
            a.descricao
        FROM artigos a
        INNER JOIN leis l ON l.id = a.lei_id
    """
    if lei_id is not None:
        sql += "\nWHERE a.lei_id = ?"
        params.append(int(lei_id))
    sql += "\nORDER BY LOWER(l.nome), a.id"
    cursor.execute(sql, tuple(params))
    rows = [_montar_artigo_base_legal(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def buscar_artigo_por_id(artigo_id: int):
    artigo_id_valor = int(artigo_id or 0)
    if artigo_id_valor <= 0:
        return None
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            a.id,
            a.lei_id,
            l.nome AS lei_nome,
            a.numero,
            a.descricao
        FROM artigos a
        INNER JOIN leis l ON l.id = a.lei_id
        WHERE a.id = ?
    """,
        (artigo_id_valor,),
    )
    row = cursor.fetchone()
    conn.close()
    return _montar_artigo_base_legal(row) if row else None


def criar_artigo(*, lei_id: int, numero: str, descricao: str):
    lei_id_valor = int(lei_id or 0)
    numero_limpo = _normalizar_nome_catalogo(numero)
    descricao_limpa = _normalizar_nome_catalogo(descricao)
    if lei_id_valor <= 0:
        raise ValueError("Lei invalida.")
    if not numero_limpo:
        raise ValueError("Numero do artigo e obrigatorio.")
    if not descricao_limpa:
        raise ValueError("Descricao do artigo e obrigatoria.")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM leis WHERE id = ?", (lei_id_valor,))
    if not cursor.fetchone():
        conn.close()
        raise ValueError("Lei nao encontrada.")
    try:
        cursor.execute(
            """
            INSERT INTO artigos (lei_id, numero, descricao)
            VALUES (?, ?, ?)
        """,
            (lei_id_valor, numero_limpo, descricao_limpa),
        )
    except sqlite3.IntegrityError as exc:
        conn.close()
        raise ValueError("Ja existe um artigo com este numero para a lei informada.") from exc
    conn.commit()
    artigo_id = int(cursor.lastrowid)
    conn.close()
    return artigo_id


def atualizar_artigo(*, artigo_id: int, lei_id: int, numero: str, descricao: str):
    artigo_id_valor = int(artigo_id or 0)
    lei_id_valor = int(lei_id or 0)
    numero_limpo = _normalizar_nome_catalogo(numero)
    descricao_limpa = _normalizar_nome_catalogo(descricao)
    if artigo_id_valor <= 0:
        return False
    if lei_id_valor <= 0:
        raise ValueError("Lei invalida.")
    if not numero_limpo:
        raise ValueError("Numero do artigo e obrigatorio.")
    if not descricao_limpa:
        raise ValueError("Descricao do artigo e obrigatoria.")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM leis WHERE id = ?", (lei_id_valor,))
    if not cursor.fetchone():
        conn.close()
        raise ValueError("Lei nao encontrada.")
    try:
        cursor.execute(
            """
            UPDATE artigos
            SET lei_id = ?, numero = ?, descricao = ?
            WHERE id = ?
        """,
            (lei_id_valor, numero_limpo, descricao_limpa, artigo_id_valor),
        )
    except sqlite3.IntegrityError as exc:
        conn.close()
        raise ValueError("Ja existe um artigo com este numero para a lei informada.") from exc
    alterado = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return alterado


def listar_incisos(artigo_id: int | None = None):
    conn = get_connection()
    cursor = conn.cursor()
    params: list[int] = []
    sql = """
        SELECT
            i.id,
            i.artigo_id,
            a.lei_id,
            l.nome AS lei_nome,
            a.numero AS artigo_numero,
            a.descricao AS artigo_descricao,
            i.numero,
            i.descricao
        FROM incisos i
        INNER JOIN artigos a ON a.id = i.artigo_id
        INNER JOIN leis l ON l.id = a.lei_id
    """
    if artigo_id is not None:
        sql += "\nWHERE i.artigo_id = ?"
        params.append(int(artigo_id))
    sql += "\nORDER BY LOWER(l.nome), a.id, i.id"
    cursor.execute(sql, tuple(params))
    rows = [_montar_inciso_base_legal(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def buscar_inciso_por_id(inciso_id: int):
    inciso_id_valor = int(inciso_id or 0)
    if inciso_id_valor <= 0:
        return None
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            i.id,
            i.artigo_id,
            a.lei_id,
            l.nome AS lei_nome,
            a.numero AS artigo_numero,
            a.descricao AS artigo_descricao,
            i.numero,
            i.descricao
        FROM incisos i
        INNER JOIN artigos a ON a.id = i.artigo_id
        INNER JOIN leis l ON l.id = a.lei_id
        WHERE i.id = ?
    """,
        (inciso_id_valor,),
    )
    row = cursor.fetchone()
    conn.close()
    return _montar_inciso_base_legal(row) if row else None


def criar_inciso(*, artigo_id: int, numero: str, descricao: str):
    artigo_id_valor = int(artigo_id or 0)
    numero_limpo = _normalizar_nome_catalogo(numero)
    descricao_limpa = _normalizar_nome_catalogo(descricao)
    if artigo_id_valor <= 0:
        raise ValueError("Artigo invalido.")
    if not numero_limpo:
        raise ValueError("Numero do inciso e obrigatorio.")
    if not descricao_limpa:
        raise ValueError("Descricao do inciso e obrigatoria.")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM artigos WHERE id = ?", (artigo_id_valor,))
    if not cursor.fetchone():
        conn.close()
        raise ValueError("Artigo nao encontrado.")
    try:
        cursor.execute(
            """
            INSERT INTO incisos (artigo_id, numero, descricao)
            VALUES (?, ?, ?)
        """,
            (artigo_id_valor, numero_limpo, descricao_limpa),
        )
    except sqlite3.IntegrityError as exc:
        conn.close()
        raise ValueError("Ja existe um inciso com este numero para o artigo informado.") from exc
    conn.commit()
    inciso_id = int(cursor.lastrowid)
    conn.close()
    return inciso_id


def atualizar_inciso(*, inciso_id: int, artigo_id: int, numero: str, descricao: str):
    inciso_id_valor = int(inciso_id or 0)
    artigo_id_valor = int(artigo_id or 0)
    numero_limpo = _normalizar_nome_catalogo(numero)
    descricao_limpa = _normalizar_nome_catalogo(descricao)
    if inciso_id_valor <= 0:
        return False
    if artigo_id_valor <= 0:
        raise ValueError("Artigo invalido.")
    if not numero_limpo:
        raise ValueError("Numero do inciso e obrigatorio.")
    if not descricao_limpa:
        raise ValueError("Descricao do inciso e obrigatoria.")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM artigos WHERE id = ?", (artigo_id_valor,))
    if not cursor.fetchone():
        conn.close()
        raise ValueError("Artigo nao encontrado.")
    try:
        cursor.execute(
            """
            UPDATE incisos
            SET artigo_id = ?, numero = ?, descricao = ?
            WHERE id = ?
        """,
            (artigo_id_valor, numero_limpo, descricao_limpa, inciso_id_valor),
        )
    except sqlite3.IntegrityError as exc:
        conn.close()
        raise ValueError("Ja existe um inciso com este numero para o artigo informado.") from exc
    alterado = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return alterado


def listar_alineas(inciso_id: int | None = None):
    conn = get_connection()
    cursor = conn.cursor()
    params: list[int] = []
    sql = """
        SELECT
            al.id,
            al.inciso_id,
            i.artigo_id,
            a.lei_id,
            l.nome AS lei_nome,
            a.numero AS artigo_numero,
            i.numero AS inciso_numero,
            i.descricao AS inciso_descricao,
            al.identificador,
            al.descricao
        FROM alineas al
        INNER JOIN incisos i ON i.id = al.inciso_id
        INNER JOIN artigos a ON a.id = i.artigo_id
        INNER JOIN leis l ON l.id = a.lei_id
    """
    if inciso_id is not None:
        sql += "\nWHERE al.inciso_id = ?"
        params.append(int(inciso_id))
    sql += "\nORDER BY LOWER(l.nome), a.id, i.id, al.id"
    cursor.execute(sql, tuple(params))
    rows = [_montar_alinea_base_legal(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def buscar_alinea_por_id(alinea_id: int):
    alinea_id_valor = int(alinea_id or 0)
    if alinea_id_valor <= 0:
        return None
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            al.id,
            al.inciso_id,
            i.artigo_id,
            a.lei_id,
            l.nome AS lei_nome,
            a.numero AS artigo_numero,
            i.numero AS inciso_numero,
            i.descricao AS inciso_descricao,
            al.identificador,
            al.descricao
        FROM alineas al
        INNER JOIN incisos i ON i.id = al.inciso_id
        INNER JOIN artigos a ON a.id = i.artigo_id
        INNER JOIN leis l ON l.id = a.lei_id
        WHERE al.id = ?
    """,
        (alinea_id_valor,),
    )
    row = cursor.fetchone()
    conn.close()
    return _montar_alinea_base_legal(row) if row else None


def criar_alinea(*, inciso_id: int, identificador: str, descricao: str):
    inciso_id_valor = int(inciso_id or 0)
    identificador_limpo = _normalizar_nome_catalogo(identificador)
    descricao_limpa = _normalizar_nome_catalogo(descricao)
    if inciso_id_valor <= 0:
        raise ValueError("Inciso invalido.")
    if not identificador_limpo:
        raise ValueError("Identificador da alinea e obrigatorio.")
    if not descricao_limpa:
        raise ValueError("Descricao da alinea e obrigatoria.")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM incisos WHERE id = ?", (inciso_id_valor,))
    if not cursor.fetchone():
        conn.close()
        raise ValueError("Inciso nao encontrado.")
    try:
        cursor.execute(
            """
            INSERT INTO alineas (inciso_id, identificador, descricao)
            VALUES (?, ?, ?)
        """,
            (inciso_id_valor, identificador_limpo, descricao_limpa),
        )
    except sqlite3.IntegrityError as exc:
        conn.close()
        raise ValueError(
            "Ja existe uma alinea com este identificador para o inciso informado."
        ) from exc
    conn.commit()
    alinea_id = int(cursor.lastrowid)
    conn.close()
    return alinea_id


def atualizar_alinea(*, alinea_id: int, inciso_id: int, identificador: str, descricao: str):
    alinea_id_valor = int(alinea_id or 0)
    inciso_id_valor = int(inciso_id or 0)
    identificador_limpo = _normalizar_nome_catalogo(identificador)
    descricao_limpa = _normalizar_nome_catalogo(descricao)
    if alinea_id_valor <= 0:
        return False
    if inciso_id_valor <= 0:
        raise ValueError("Inciso invalido.")
    if not identificador_limpo:
        raise ValueError("Identificador da alinea e obrigatorio.")
    if not descricao_limpa:
        raise ValueError("Descricao da alinea e obrigatoria.")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM incisos WHERE id = ?", (inciso_id_valor,))
    if not cursor.fetchone():
        conn.close()
        raise ValueError("Inciso nao encontrado.")
    try:
        cursor.execute(
            """
            UPDATE alineas
            SET inciso_id = ?, identificador = ?, descricao = ?
            WHERE id = ?
        """,
            (inciso_id_valor, identificador_limpo, descricao_limpa, alinea_id_valor),
        )
    except sqlite3.IntegrityError as exc:
        conn.close()
        raise ValueError(
            "Ja existe uma alinea com este identificador para o inciso informado."
        ) from exc
    alterado = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return alterado


def _contar_relacoes_base_legal(cursor, tabela: str, coluna: str, valor_id: int) -> int:
    cursor.execute(
        f"SELECT COUNT(*) AS total FROM {tabela} WHERE {coluna} = ?",
        (int(valor_id),),
    )
    row = cursor.fetchone()
    return int(row["total"] or 0) if row else 0


def remover_lei(lei_id: int):
    lei_id_valor = int(lei_id or 0)
    if lei_id_valor <= 0:
        return False

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM leis WHERE id = ?", (lei_id_valor,))
    if not cursor.fetchone():
        conn.close()
        return False

    if _contar_relacoes_base_legal(cursor, "artigos", "lei_id", lei_id_valor) > 0:
        conn.close()
        raise ValueError("Nao e possivel excluir a lei porque existem artigos vinculados.")

    cursor.execute("DELETE FROM leis WHERE id = ?", (lei_id_valor,))
    removido = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return removido


def remover_artigo(artigo_id: int):
    artigo_id_valor = int(artigo_id or 0)
    if artigo_id_valor <= 0:
        return False

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM artigos WHERE id = ?", (artigo_id_valor,))
    if not cursor.fetchone():
        conn.close()
        return False

    if _contar_relacoes_base_legal(cursor, "incisos", "artigo_id", artigo_id_valor) > 0:
        conn.close()
        raise ValueError("Nao e possivel excluir o artigo porque existem incisos vinculados.")
    if (
        _contar_relacoes_base_legal(
            cursor, "ocorrencia_regimento_itens", "artigo_id", artigo_id_valor
        )
        > 0
    ):
        conn.close()
        raise ValueError(
            "Nao e possivel excluir o artigo porque ele ja foi vinculado a ocorrencias."
        )

    cursor.execute("DELETE FROM artigos WHERE id = ?", (artigo_id_valor,))
    removido = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return removido


def remover_inciso(inciso_id: int):
    inciso_id_valor = int(inciso_id or 0)
    if inciso_id_valor <= 0:
        return False

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM incisos WHERE id = ?", (inciso_id_valor,))
    if not cursor.fetchone():
        conn.close()
        return False

    if _contar_relacoes_base_legal(cursor, "alineas", "inciso_id", inciso_id_valor) > 0:
        conn.close()
        raise ValueError("Nao e possivel excluir o inciso porque existem alineas vinculadas.")
    if (
        _contar_relacoes_base_legal(
            cursor, "ocorrencia_regimento_itens", "inciso_id", inciso_id_valor
        )
        > 0
    ):
        conn.close()
        raise ValueError(
            "Nao e possivel excluir o inciso porque ele ja foi vinculado a ocorrencias."
        )

    cursor.execute("DELETE FROM incisos WHERE id = ?", (inciso_id_valor,))
    removido = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return removido


def remover_alinea(alinea_id: int):
    alinea_id_valor = int(alinea_id or 0)
    if alinea_id_valor <= 0:
        return False

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM alineas WHERE id = ?", (alinea_id_valor,))
    if not cursor.fetchone():
        conn.close()
        return False

    if (
        _contar_relacoes_base_legal(
            cursor, "ocorrencia_regimento_itens", "alinea_id", alinea_id_valor
        )
        > 0
    ):
        conn.close()
        raise ValueError(
            "Nao e possivel excluir a alinea porque ela ja foi vinculada a ocorrencias."
        )

    cursor.execute("DELETE FROM alineas WHERE id = ?", (alinea_id_valor,))
    removido = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return removido


def remover_regimento_item(regimento_item_id: int):
    try:
        tipo, entidade_id = _decodificar_regimento_item_id(regimento_item_id)
    except ValueError:
        return False

    if tipo == TIPO_BASE_LEGAL_ARTIGO:
        return remover_artigo(entidade_id)
    if tipo == TIPO_BASE_LEGAL_INCISO:
        return remover_inciso(entidade_id)
    if tipo == TIPO_BASE_LEGAL_ALINEA:
        return remover_alinea(entidade_id)
    return False


def buscar_regimento_item_por_id(regimento_item_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        tipo, entidade_id = _decodificar_regimento_item_id(regimento_item_id)
    except ValueError:
        conn.close()
        return None
    row = _buscar_item_base_legal_por_tipo_cursor(cursor, tipo, entidade_id)
    conn.close()
    return row


def buscar_regimento_item_por_artigo(artigo: str):
    artigo_limpo = _normalizar_nome_catalogo(artigo)
    if not artigo_limpo:
        return None

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            a.id AS artigo_id
        FROM artigos a
        WHERE a.numero = ? COLLATE NOCASE
        ORDER BY a.id ASC
        LIMIT 1
    """,
        (artigo_limpo,),
    )
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return buscar_regimento_item_por_id(
        _codificar_regimento_item_id(TIPO_BASE_LEGAL_ARTIGO, int(row["artigo_id"]))
    )


def buscar_regimento_itens_por_ids(regimento_item_ids: list[int]):
    ids_validos = []
    vistos = set()
    for regimento_item_id in regimento_item_ids or []:
        valor = int(regimento_item_id)
        if valor <= 0 or valor in vistos:
            continue
        vistos.add(valor)
        ids_validos.append(valor)

    if not ids_validos:
        return []

    itens = []
    for regimento_item_id in ids_validos:
        item = buscar_regimento_item_por_id(regimento_item_id)
        if item:
            itens.append(item)
    return itens


def criar_ou_atualizar_regimento_item(
    *,
    lei_nome: str,
    artigo_numero: str,
    artigo_descricao: str,
    inciso_numero: str | None = None,
    inciso_descricao: str | None = None,
    alinea_identificador: str | None = None,
    alinea_descricao: str | None = None,
) -> tuple[int, bool]:
    dados = _normalizar_campos_base_legal(
        lei_nome=lei_nome,
        artigo_numero=artigo_numero,
        artigo_descricao=artigo_descricao,
        inciso_numero=inciso_numero,
        inciso_descricao=inciso_descricao,
        alinea_identificador=alinea_identificador,
        alinea_descricao=alinea_descricao,
    )

    conn = get_connection()
    cursor = conn.cursor()
    lei_id, lei_criada = _obter_ou_criar_lei_cursor(cursor, dados["lei_nome"])
    artigo_id, artigo_criado = _obter_ou_criar_artigo_cursor(
        cursor,
        lei_id=lei_id,
        numero=dados["artigo_numero"],
        descricao=dados["artigo_descricao"],
    )

    tipo = TIPO_BASE_LEGAL_ARTIGO
    entidade_id = artigo_id
    criado = lei_criada or artigo_criado

    if dados["inciso_numero"]:
        inciso_id, inciso_criado = _obter_ou_criar_inciso_cursor(
            cursor,
            artigo_id=artigo_id,
            numero=dados["inciso_numero"],
            descricao=dados["inciso_descricao"],
        )
        tipo = TIPO_BASE_LEGAL_INCISO
        entidade_id = inciso_id
        criado = criado or inciso_criado

        if dados["alinea_identificador"]:
            alinea_id, alinea_criada = _obter_ou_criar_alinea_cursor(
                cursor,
                inciso_id=inciso_id,
                identificador=dados["alinea_identificador"],
                descricao=dados["alinea_descricao"],
            )
            tipo = TIPO_BASE_LEGAL_ALINEA
            entidade_id = alinea_id
            criado = criado or alinea_criada

    conn.commit()
    conn.close()
    return _codificar_regimento_item_id(tipo, entidade_id), bool(criado)


def criar_regimento_item(
    artigo: str | None = None,
    descricao: str | None = None,
    ativo: bool = True,
    *,
    lei_nome: str | None = None,
    artigo_numero: str | None = None,
    artigo_descricao: str | None = None,
    inciso_numero: str | None = None,
    inciso_descricao: str | None = None,
    alinea_identificador: str | None = None,
    alinea_descricao: str | None = None,
):
    regimento_item_id, _criado = criar_ou_atualizar_regimento_item(
        lei_nome=lei_nome or LEI_PADRAO_IMPORTACAO,
        artigo_numero=artigo_numero or artigo or "",
        artigo_descricao=artigo_descricao or descricao or "",
        inciso_numero=inciso_numero,
        inciso_descricao=inciso_descricao,
        alinea_identificador=alinea_identificador,
        alinea_descricao=alinea_descricao,
    )
    return regimento_item_id


def criar_ou_atualizar_regimento_item_por_artigo(
    artigo: str,
    descricao: str,
    ativo: bool = True,
):
    return criar_ou_atualizar_regimento_item(
        lei_nome=LEI_PADRAO_IMPORTACAO,
        artigo_numero=artigo,
        artigo_descricao=descricao,
    )


def atualizar_regimento_item(
    regimento_item_id: int,
    artigo: str | None = None,
    descricao: str | None = None,
    ativo: bool = True,
    *,
    lei_nome: str | None = None,
    artigo_numero: str | None = None,
    artigo_descricao: str | None = None,
    inciso_numero: str | None = None,
    inciso_descricao: str | None = None,
    alinea_identificador: str | None = None,
    alinea_descricao: str | None = None,
):
    atual = buscar_regimento_item_por_id(regimento_item_id)
    if not atual:
        return False

    lei_nome_valor = lei_nome or atual.get("lei_nome") or LEI_PADRAO_IMPORTACAO
    artigo_numero_valor = artigo_numero or artigo or atual.get("artigo_numero") or ""
    artigo_descricao_valor = artigo_descricao or descricao or atual.get("artigo_descricao") or ""

    if atual.get("tipo") == TIPO_BASE_LEGAL_ARTIGO:
        inciso_numero_valor = None
        inciso_descricao_valor = None
        alinea_identificador_valor = None
        alinea_descricao_valor = None
    elif atual.get("tipo") == TIPO_BASE_LEGAL_INCISO:
        inciso_numero_valor = inciso_numero or atual.get("inciso_numero") or ""
        inciso_descricao_valor = inciso_descricao or atual.get("inciso_descricao") or ""
        alinea_identificador_valor = None
        alinea_descricao_valor = None
    else:
        inciso_numero_valor = inciso_numero or atual.get("inciso_numero") or ""
        inciso_descricao_valor = inciso_descricao or atual.get("inciso_descricao") or ""
        alinea_identificador_valor = alinea_identificador or atual.get("alinea_identificador") or ""
        alinea_descricao_valor = alinea_descricao or atual.get("alinea_descricao") or ""

    dados = _normalizar_campos_base_legal(
        lei_nome=lei_nome_valor,
        artigo_numero=artigo_numero_valor,
        artigo_descricao=artigo_descricao_valor,
        inciso_numero=inciso_numero_valor,
        inciso_descricao=inciso_descricao_valor,
        alinea_identificador=alinea_identificador_valor,
        alinea_descricao=alinea_descricao_valor,
    )

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE leis SET nome = ? WHERE id = ?",
            (dados["lei_nome"], int(atual.get("lei_id") or 0)),
        )
        cursor.execute(
            """
            UPDATE artigos
            SET numero = ?, descricao = ?
            WHERE id = ?
        """,
            (
                dados["artigo_numero"],
                dados["artigo_descricao"],
                int(atual.get("artigo_id") or 0),
            ),
        )

        if atual.get("tipo") in {TIPO_BASE_LEGAL_INCISO, TIPO_BASE_LEGAL_ALINEA}:
            cursor.execute(
                """
                UPDATE incisos
                SET numero = ?, descricao = ?
                WHERE id = ?
            """,
                (
                    dados["inciso_numero"],
                    dados["inciso_descricao"],
                    int(atual.get("inciso_id") or 0),
                ),
            )

        if atual.get("tipo") == TIPO_BASE_LEGAL_ALINEA:
            cursor.execute(
                """
                UPDATE alineas
                SET identificador = ?, descricao = ?
                WHERE id = ?
            """,
                (
                    dados["alinea_identificador"],
                    dados["alinea_descricao"],
                    int(atual.get("alinea_id") or 0),
                ),
            )
    except sqlite3.IntegrityError as exc:
        conn.close()
        raise ValueError("Ja existe um item de base legal com esta referencia.") from exc

    conn.commit()
    conn.close()
    return True


def atualizar_status_regimento_item(regimento_item_id: int, ativo: bool):
    return buscar_regimento_item_por_id(regimento_item_id) is not None


def _normalizar_regimento_item_ids_banco(regimento_item_ids: list[int] | None) -> list[int]:
    ids_norm = []
    vistos = set()
    for regimento_item_id in regimento_item_ids or []:
        valor = int(regimento_item_id)
        if valor <= 0 or valor in vistos:
            continue
        vistos.add(valor)
        ids_norm.append(valor)
    return ids_norm


def _mapear_regimento_itens_por_ids_para_snapshot(ids_norm: list[int]) -> dict[int, dict]:
    itens = {int(item["id"]): item for item in buscar_regimento_itens_por_ids(ids_norm)}
    faltantes = [
        regimento_item_id for regimento_item_id in ids_norm if regimento_item_id not in itens
    ]
    if faltantes:
        raise ValueError("Um ou mais itens do regimento nao foram encontrados.")
    return itens


def _salvar_regimento_itens_ocorrencia_cursor(
    cursor,
    ocorrencia_id_valor: int,
    ids_norm: list[int],
    itens: dict[int, dict] | None = None,
):
    cursor.execute(
        "DELETE FROM ocorrencia_regimento_itens WHERE ocorrencia_id = ?",
        (ocorrencia_id_valor,),
    )

    if ids_norm:
        itens = itens or _mapear_regimento_itens_por_ids_para_snapshot(ids_norm)

        cursor.executemany(
            """
            INSERT INTO ocorrencia_regimento_itens (
                ocorrencia_id,
                regimento_item_id,
                artigo_id,
                inciso_id,
                alinea_id,
                lei_nome,
                artigo_numero,
                artigo_descricao,
                inciso_numero,
                inciso_descricao,
                alinea_identificador,
                alinea_descricao,
                artigo,
                descricao,
                ordem,
                criado_em
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """,
            [
                (
                    ocorrencia_id_valor,
                    regimento_item_id,
                    int(itens[regimento_item_id]["artigo_id"])
                    if itens[regimento_item_id].get("artigo_id") is not None
                    else None,
                    int(itens[regimento_item_id]["inciso_id"])
                    if itens[regimento_item_id].get("inciso_id") is not None
                    else None,
                    int(itens[regimento_item_id]["alinea_id"])
                    if itens[regimento_item_id].get("alinea_id") is not None
                    else None,
                    str(itens[regimento_item_id].get("lei_nome") or "").strip() or None,
                    str(itens[regimento_item_id].get("artigo_numero") or "").strip() or None,
                    str(itens[regimento_item_id].get("artigo_descricao") or "").strip() or None,
                    str(itens[regimento_item_id].get("inciso_numero") or "").strip() or None,
                    str(itens[regimento_item_id].get("inciso_descricao") or "").strip() or None,
                    str(itens[regimento_item_id].get("alinea_identificador") or "").strip() or None,
                    str(itens[regimento_item_id].get("alinea_descricao") or "").strip() or None,
                    str(itens[regimento_item_id]["artigo"] or "").strip(),
                    str(itens[regimento_item_id]["descricao"] or "").strip(),
                    ordem,
                )
                for ordem, regimento_item_id in enumerate(ids_norm, start=1)
            ],
        )


def salvar_regimento_itens_ocorrencia(ocorrencia_id: int, regimento_item_ids: list[int] | None):
    ocorrencia_id_valor = int(ocorrencia_id or 0)
    if ocorrencia_id_valor <= 0:
        raise ValueError("Ocorrencia invalida.")

    ids_norm = _normalizar_regimento_item_ids_banco(regimento_item_ids)

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT 1 FROM ocorrencias WHERE id = ?", (ocorrencia_id_valor,))
        if not cursor.fetchone():
            raise ValueError("Ocorrencia nao encontrada.")

        _salvar_regimento_itens_ocorrencia_cursor(cursor, ocorrencia_id_valor, ids_norm)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return True


def _normalizar_estudantes_vinculados_banco(
    estudantes_vinculados: list[dict] | None,
) -> list[dict]:
    itens_norm = []
    vistos = set()
    for item in estudantes_vinculados or []:
        if not isinstance(item, dict):
            continue
        estudante_id = item.get("estudante_id")
        estudante_id_valor = int(estudante_id) if estudante_id not in (None, "") else None
        if estudante_id_valor is not None and estudante_id_valor <= 0:
            raise ValueError("Estudante invalido.")

        nome = _normalizar_nome_catalogo(item.get("nome"))
        if not nome:
            raise ValueError("Nome do estudante e obrigatorio.")

        turma_id = item.get("turma_id")
        turma_id_valor = int(turma_id) if turma_id not in (None, "") else None
        if turma_id_valor is not None and turma_id_valor <= 0:
            raise ValueError("Turma invalida.")

        turma_nome = _normalizar_nome_catalogo(item.get("turma_nome")) or ""
        chave = f"id:{estudante_id_valor}" if estudante_id_valor else f"nome:{nome.lower()}"
        if chave in vistos:
            continue
        vistos.add(chave)
        itens_norm.append(
            {
                "estudante_id": estudante_id_valor,
                "nome": nome,
                "turma_id": turma_id_valor,
                "turma_nome": turma_nome,
            }
        )
    return itens_norm


def _normalizar_professores_vinculados_banco(
    professores_vinculados: list[dict] | None,
) -> list[dict]:
    itens_norm = []
    vistos = set()
    for item in professores_vinculados or []:
        if not isinstance(item, dict):
            continue
        professor_id = item.get("professor_id")
        professor_id_valor = int(professor_id) if professor_id not in (None, "") else None
        if professor_id_valor is not None and professor_id_valor <= 0:
            raise ValueError("Professor invalido.")

        nome = _normalizar_nome_catalogo(item.get("nome"))
        if not nome:
            raise ValueError("Nome do professor e obrigatorio.")

        email = _normalizar_nome_catalogo(item.get("email")) or ""
        chave = f"id:{professor_id_valor}" if professor_id_valor else f"nome:{nome.lower()}"
        if chave in vistos:
            continue
        vistos.add(chave)
        itens_norm.append(
            {
                "professor_id": professor_id_valor,
                "nome": nome,
                "email": email,
            }
        )
    return itens_norm


def _salvar_ocorrencia_estudantes_cursor(
    cursor,
    ocorrencia_id_valor: int,
    estudantes_vinculados: list[dict],
):
    cursor.execute(
        "DELETE FROM ocorrencia_estudantes WHERE ocorrencia_id = ?",
        (ocorrencia_id_valor,),
    )
    if not estudantes_vinculados:
        return

    cursor.executemany(
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
        VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
    """,
        [
            (
                ocorrencia_id_valor,
                item.get("estudante_id"),
                item.get("nome"),
                item.get("turma_id"),
                item.get("turma_nome") or "",
                ordem,
            )
            for ordem, item in enumerate(estudantes_vinculados, start=1)
        ],
    )


def _salvar_ocorrencia_professores_cursor(
    cursor,
    ocorrencia_id_valor: int,
    professores_vinculados: list[dict],
):
    cursor.execute(
        "DELETE FROM ocorrencia_professores WHERE ocorrencia_id = ?",
        (ocorrencia_id_valor,),
    )
    if not professores_vinculados:
        return

    cursor.executemany(
        """
        INSERT INTO ocorrencia_professores (
            ocorrencia_id,
            professor_usuario_id,
            nome_professor,
            email_professor,
            ordem,
            criado_em
        )
        VALUES (?, ?, ?, ?, ?, datetime('now'))
    """,
        [
            (
                ocorrencia_id_valor,
                item.get("professor_id"),
                item.get("nome"),
                item.get("email") or "",
                ordem,
            )
            for ordem, item in enumerate(professores_vinculados, start=1)
        ],
    )


def salvar_ocorrencia_estudantes_vinculados(
    ocorrencia_id: int,
    estudantes_vinculados: list[dict] | None,
):
    ocorrencia_id_valor = int(ocorrencia_id or 0)
    if ocorrencia_id_valor <= 0:
        raise ValueError("Ocorrencia invalida.")

    estudantes_norm = _normalizar_estudantes_vinculados_banco(estudantes_vinculados)
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT 1 FROM ocorrencias WHERE id = ?", (ocorrencia_id_valor,))
        if not cursor.fetchone():
            raise ValueError("Ocorrencia nao encontrada.")
        _salvar_ocorrencia_estudantes_cursor(cursor, ocorrencia_id_valor, estudantes_norm)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return True


def salvar_ocorrencia_professores_vinculados(
    ocorrencia_id: int,
    professores_vinculados: list[dict] | None,
):
    ocorrencia_id_valor = int(ocorrencia_id or 0)
    if ocorrencia_id_valor <= 0:
        raise ValueError("Ocorrencia invalida.")

    professores_norm = _normalizar_professores_vinculados_banco(professores_vinculados)
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT 1 FROM ocorrencias WHERE id = ?", (ocorrencia_id_valor,))
        if not cursor.fetchone():
            raise ValueError("Ocorrencia nao encontrada.")
        _salvar_ocorrencia_professores_cursor(cursor, ocorrencia_id_valor, professores_norm)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return True


def _validar_tipo_registro_banco(tipo_registro: str | None) -> str:
    tipo_norm = _normalizar_nome_catalogo(tipo_registro) or TIPO_REGISTRO_OCORRENCIA_ESTUDANTE
    if tipo_norm not in TIPOS_REGISTRO_OCORRENCIA:
        raise ValueError("Tipo de registro invalido.")
    return tipo_norm


def criar_ocorrencia(
    tipo_registro: str,
    nome_estudante: str,
    estudante_id: int | None,
    turma_id: int | None,
    professor_requerente: str,
    professor_requerente_id: int | None,
    disciplina: str | None,
    data_ocorrencia: str,
    aula: str | None,
    horario_ocorrencia: str,
    descricao: str,
    acao_aplicada: str,
    status: str = STATUS_OCORRENCIA_REGISTRADO,
    regimento_item_ids: list[int] | None = None,
    estudantes_vinculados: list[dict] | None = None,
    professores_vinculados: list[dict] | None = None,
):
    tipo_registro_limpo = _validar_tipo_registro_banco(tipo_registro)
    nome_estudante_limpo = _normalizar_nome_catalogo(nome_estudante)
    professor_requerente_limpo = _normalizar_nome_catalogo(professor_requerente)
    disciplina_limpa = _normalizar_nome_catalogo(disciplina)
    data_ocorrencia_limpa = _normalizar_nome_catalogo(data_ocorrencia)
    aula_limpa = _normalizar_nome_catalogo(aula)
    horario_ocorrencia_limpo = _normalizar_nome_catalogo(horario_ocorrencia)
    descricao_limpa = str(descricao or "").strip()
    acao_aplicada_limpa = _normalizar_nome_catalogo(acao_aplicada)
    status_limpo = _normalizar_nome_catalogo(status) or STATUS_OCORRENCIA_REGISTRADO
    turma_id_valor = int(turma_id) if turma_id not in (None, "") else None
    estudante_id_valor = int(estudante_id) if estudante_id is not None else None
    professor_requerente_id_valor = (
        int(professor_requerente_id) if professor_requerente_id is not None else None
    )
    estudantes_vinculados_norm = _normalizar_estudantes_vinculados_banco(estudantes_vinculados)
    professores_vinculados_norm = _normalizar_professores_vinculados_banco(professores_vinculados)

    if turma_id_valor is not None and turma_id_valor <= 0:
        raise ValueError("Turma invalida.")
    if estudante_id_valor is not None and estudante_id_valor <= 0:
        raise ValueError("Estudante invalido.")
    if professor_requerente_id_valor is not None and professor_requerente_id_valor <= 0:
        raise ValueError("Professor invalido.")

    if tipo_registro_limpo == TIPO_REGISTRO_OCORRENCIA_ESTUDANTE:
        if not estudantes_vinculados_norm and nome_estudante_limpo:
            estudantes_vinculados_norm = [
                {
                    "estudante_id": estudante_id_valor,
                    "nome": nome_estudante_limpo,
                    "turma_id": turma_id_valor,
                    "turma_nome": "",
                }
            ]
        if not estudantes_vinculados_norm:
            raise ValueError("Selecione ao menos um estudante.")
        nome_estudante_limpo = ", ".join(item["nome"] for item in estudantes_vinculados_norm)
        if estudante_id_valor is None:
            estudante_id_valor = estudantes_vinculados_norm[0].get("estudante_id")
        turma_ids_vinculados = sorted(
            {
                int(item["turma_id"])
                for item in estudantes_vinculados_norm
                if item.get("turma_id") is not None and int(item["turma_id"]) > 0
            }
        )
        if len(turma_ids_vinculados) == 1:
            turma_id_valor = turma_ids_vinculados[0]
        elif len(turma_ids_vinculados) > 1:
            turma_id_valor = None
        if not turma_ids_vinculados and (turma_id_valor is None or turma_id_valor <= 0):
            raise ValueError("Turma invalida.")
        if not professor_requerente_limpo:
            raise ValueError("Professor requerente e obrigatorio.")
        if not disciplina_limpa:
            raise ValueError("Disciplina e obrigatoria.")
    elif tipo_registro_limpo == TIPO_REGISTRO_OCORRENCIA_PROFESSOR:
        if not professores_vinculados_norm and professor_requerente_limpo:
            professores_vinculados_norm = [
                {
                    "professor_id": professor_requerente_id_valor,
                    "nome": professor_requerente_limpo,
                    "email": "",
                }
            ]
        if not professores_vinculados_norm:
            raise ValueError("Selecione ao menos um professor.")
        professor_requerente_limpo = ", ".join(item["nome"] for item in professores_vinculados_norm)
        if professor_requerente_id_valor is None:
            professor_requerente_id_valor = professores_vinculados_norm[0].get("professor_id")
        if not nome_estudante_limpo:
            nome_estudante_limpo = professor_requerente_limpo
        turma_id_valor = None
        aula_limpa = ""
    else:
        if not nome_estudante_limpo:
            raise ValueError("Titulo do registro geral e obrigatorio.")
        if not professor_requerente_limpo:
            professor_requerente_limpo = "Todos os professores"
        turma_id_valor = None
        aula_limpa = ""

    if not data_ocorrencia_limpa:
        raise ValueError("Data da ocorrencia e obrigatoria.")
    if (
        tipo_registro_limpo == TIPO_REGISTRO_OCORRENCIA_ESTUDANTE
        and turma_id_valor is not None
        and not aula_limpa
    ):
        raise ValueError("Aula e obrigatoria.")
    if not horario_ocorrencia_limpo:
        raise ValueError("Horario da ocorrencia e obrigatorio.")
    if not descricao_limpa:
        raise ValueError("Descricao e obrigatoria.")
    if acao_aplicada_limpa not in ACAO_OCORRENCIA_VALIDAS:
        raise ValueError("Acao aplicada invalida.")
    if status_limpo not in STATUS_OCORRENCIA_VALIDOS:
        raise ValueError("Status invalido.")

    ids_regimento_norm = None
    itens_regimento_snapshot = None
    if regimento_item_ids is not None:
        ids_regimento_norm = _normalizar_regimento_item_ids_banco(regimento_item_ids)
        if ids_regimento_norm:
            itens_regimento_snapshot = _mapear_regimento_itens_por_ids_para_snapshot(
                ids_regimento_norm
            )

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO ocorrencias (
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
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        """,
            (
                tipo_registro_limpo,
                nome_estudante_limpo,
                estudante_id_valor,
                turma_id_valor,
                professor_requerente_limpo,
                professor_requerente_id_valor,
                disciplina_limpa,
                data_ocorrencia_limpa,
                aula_limpa,
                horario_ocorrencia_limpo,
                descricao_limpa,
                acao_aplicada_limpa,
                status_limpo,
            ),
        )

        ocorrencia_id = cursor.lastrowid
        _salvar_ocorrencia_estudantes_cursor(
            cursor,
            int(ocorrencia_id),
            estudantes_vinculados_norm if tipo_registro_limpo == TIPO_REGISTRO_OCORRENCIA_ESTUDANTE else [],
        )
        _salvar_ocorrencia_professores_cursor(
            cursor,
            int(ocorrencia_id),
            professores_vinculados_norm if tipo_registro_limpo == TIPO_REGISTRO_OCORRENCIA_PROFESSOR else [],
        )
        if ids_regimento_norm is not None:
            _salvar_regimento_itens_ocorrencia_cursor(
                cursor,
                int(ocorrencia_id),
                ids_regimento_norm,
                itens_regimento_snapshot,
            )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return ocorrencia_id


def listar_ocorrencias(
    tipo_registro: str = None,
    status: str = None,
    turma_id: int = None,
    nome_estudante: str = None,
    data_inicial: str = None,
    data_final: str = None,
):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT
            o.id,
            o.tipo_registro,
            o.nome_estudante,
            o.estudante_id,
            o.turma_id,
            COALESCE(t.nome, '') AS turma_nome,
            o.professor_requerente,
            o.professor_requerente_id,
            o.disciplina,
            o.data_ocorrencia,
            o.aula,
            o.horario_ocorrencia,
            o.descricao,
            o.acao_aplicada,
            o.status,
            o.criado_em,
            o.atualizado_em
        FROM ocorrencias o
        LEFT JOIN turmas t ON t.id = o.turma_id
        WHERE 1 = 1
    """
    params = []

    tipo_registro_limpo = _normalizar_nome_catalogo(tipo_registro)
    if tipo_registro_limpo:
        query += " AND o.tipo_registro = ?"
        params.append(tipo_registro_limpo)

    status_limpo = _normalizar_nome_catalogo(status)
    if status_limpo:
        query += " AND o.status = ?"
        params.append(status_limpo)

    if turma_id is not None:
        turma_id_valor = int(turma_id)
        if turma_id_valor > 0:
            query += " AND o.turma_id = ?"
            params.append(turma_id_valor)

    nome_estudante_limpo = _normalizar_nome_catalogo(nome_estudante)
    if nome_estudante_limpo:
        query += " AND LOWER(o.nome_estudante) LIKE ?"
        params.append(f"%{nome_estudante_limpo.lower()}%")

    data_inicial_limpa = _normalizar_nome_catalogo(data_inicial)
    if data_inicial_limpa:
        query += " AND o.data_ocorrencia >= ?"
        params.append(data_inicial_limpa)

    data_final_limpa = _normalizar_nome_catalogo(data_final)
    if data_final_limpa:
        query += " AND o.data_ocorrencia <= ?"
        params.append(data_final_limpa)

    query += """
        ORDER BY
            o.data_ocorrencia DESC,
            o.criado_em DESC
    """

    cursor.execute(query, params)
    rows = cursor.fetchall()
    ocorrencias = [dict(row) for row in rows]
    _anexar_regimento_itens_ocorrencias(cursor, ocorrencias)
    _anexar_vinculados_ocorrencias(cursor, ocorrencias)
    conn.close()
    return ocorrencias


def buscar_ocorrencia_por_id(ocorrencia_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            o.id,
            o.tipo_registro,
            o.nome_estudante,
            o.estudante_id,
            o.turma_id,
            COALESCE(t.nome, '') AS turma_nome,
            o.professor_requerente,
            o.professor_requerente_id,
            o.disciplina,
            o.data_ocorrencia,
            o.aula,
            o.horario_ocorrencia,
            o.descricao,
            o.acao_aplicada,
            o.status,
            o.criado_em,
            o.atualizado_em
        FROM ocorrencias o
        LEFT JOIN turmas t ON t.id = o.turma_id
        WHERE o.id = ?
    """,
        (int(ocorrencia_id),),
    )

    row = cursor.fetchone()
    ocorrencia = dict(row) if row else None
    if ocorrencia:
        _anexar_regimento_itens_ocorrencias(cursor, [ocorrencia])
        _anexar_vinculados_ocorrencias(cursor, [ocorrencia])
    conn.close()
    return ocorrencia


def atualizar_ocorrencia(ocorrencia_id: int, dados: dict):
    campos_permitidos = {
        "tipo_registro",
        "nome_estudante",
        "estudante_id",
        "turma_id",
        "professor_requerente",
        "professor_requerente_id",
        "disciplina",
        "data_ocorrencia",
        "aula",
        "horario_ocorrencia",
        "descricao",
        "acao_aplicada",
        "status",
    }
    if not isinstance(dados, dict):
        return False

    atualizacoes = []
    parametros = []

    for campo, valor in dados.items():
        if campo not in campos_permitidos:
            continue

        if campo == "tipo_registro":
            atualizacoes.append("tipo_registro = ?")
            parametros.append(_validar_tipo_registro_banco(valor))
            continue

        if campo == "turma_id":
            valor_turma = int(valor) if valor not in (None, "") else None
            if valor_turma is not None and valor_turma <= 0:
                raise ValueError("Turma invalida.")
            atualizacoes.append("turma_id = ?")
            parametros.append(valor_turma)
            continue

        if campo == "estudante_id":
            valor_estudante = int(valor) if valor is not None else None
            if valor_estudante is not None and valor_estudante <= 0:
                raise ValueError("Estudante invalido.")
            atualizacoes.append("estudante_id = ?")
            parametros.append(valor_estudante)
            continue

        if campo == "professor_requerente_id":
            valor_professor = int(valor) if valor is not None else None
            if valor_professor is not None and valor_professor <= 0:
                raise ValueError("Professor invalido.")
            atualizacoes.append("professor_requerente_id = ?")
            parametros.append(valor_professor)
            continue

        if campo == "acao_aplicada":
            valor_acao = _normalizar_nome_catalogo(valor)
            if valor_acao not in ACAO_OCORRENCIA_VALIDAS:
                raise ValueError("Acao aplicada invalida.")
            atualizacoes.append("acao_aplicada = ?")
            parametros.append(valor_acao)
            continue

        if campo == "status":
            valor_status = _normalizar_nome_catalogo(valor)
            if valor_status not in STATUS_OCORRENCIA_VALIDOS:
                raise ValueError("Status invalido.")
            atualizacoes.append("status = ?")
            parametros.append(valor_status)
            continue

        if campo == "descricao":
            valor_descricao = str(valor or "").strip()
            if not valor_descricao:
                raise ValueError("Descricao e obrigatoria.")
            atualizacoes.append("descricao = ?")
            parametros.append(valor_descricao)
            continue

        if campo in {"disciplina", "aula"}:
            atualizacoes.append(f"{campo} = ?")
            parametros.append(_normalizar_nome_catalogo(valor))
            continue

        valor_texto = _normalizar_nome_catalogo(valor)
        if not valor_texto:
            raise ValueError("Campos obrigatorios nao podem ficar vazios.")
        atualizacoes.append(f"{campo} = ?")
        parametros.append(valor_texto)

    if not atualizacoes:
        return False

    atualizacoes.append("atualizado_em = datetime('now')")
    parametros.append(int(ocorrencia_id))

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"""
        UPDATE ocorrencias
        SET {", ".join(atualizacoes)}
        WHERE id = ?
    """,
        parametros,
    )

    alterado = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return alterado


def remover_ocorrencia(ocorrencia_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM ocorrencia_estudantes WHERE ocorrencia_id = ?",
        (int(ocorrencia_id),),
    )
    cursor.execute(
        "DELETE FROM ocorrencia_professores WHERE ocorrencia_id = ?",
        (int(ocorrencia_id),),
    )
    cursor.execute(
        "DELETE FROM ocorrencia_regimento_itens WHERE ocorrencia_id = ?",
        (int(ocorrencia_id),),
    )
    cursor.execute("DELETE FROM ocorrencias WHERE id = ?", (int(ocorrencia_id),))
    removido = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return removido


def contar_agendamentos_ativos_faixa(recurso_id: int, data: str, faixa_global: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM agendamentos
        WHERE recurso_id = ?
          AND data = ?
          AND faixa_global = ?
          AND status = ?
    """,
        (recurso_id, data, int(faixa_global), STATUS_AGENDAMENTO_ATIVO),
    )

    row = cursor.fetchone()
    conn.close()
    return int(row["total"] if row else 0)


def buscar_agendamento_conflito(recurso_id: int, data: str, faixa_global: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id
        FROM agendamentos
        WHERE recurso_id = ?
          AND data = ?
          AND faixa_global = ?
          AND status = ?
        LIMIT 1
    """,
        (recurso_id, data, int(faixa_global), STATUS_AGENDAMENTO_ATIVO),
    )

    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def criar_agendamento(
    recurso_id: int,
    usuario_id: int,
    data: str,
    turno: str,
    aula: str,
    faixa_global: int,
    turma: str,
    tema_aula: str,
    observacao: str = "",
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO agendamentos (
            recurso_id, usuario_id, data, turno, aula, faixa_global, turma, tema_aula, observacao, status, criado_em
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
    """,
        (
            recurso_id,
            usuario_id,
            data,
            turno,
            aula,
            int(faixa_global),
            turma,
            tema_aula,
            observacao,
            STATUS_AGENDAMENTO_ATIVO,
        ),
    )

    agendamento_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return agendamento_id


def listar_agendamentos(
    data_inicio: str = None,
    data_fim: str = None,
    recurso_id: int = None,
    usuario_id: int = None,
    incluir_cancelados: bool = False,
):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT
            a.id,
            a.recurso_id,
            r.nome AS recurso_nome,
            r.tipo AS recurso_tipo,
            a.usuario_id,
            u.nome AS professor_nome,
            a.data,
            a.turno,
            a.aula,
            a.faixa_global,
            a.turma,
            COALESCE(a.tema_aula, '') AS tema_aula,
            COALESCE(a.observacao, '') AS observacao,
            a.status,
            a.criado_em,
            a.cancelado_em
        FROM agendamentos a
        JOIN recursos r ON r.id = a.recurso_id
        JOIN usuarios u ON u.id = a.usuario_id
        WHERE 1 = 1
    """

    params = []

    if not incluir_cancelados:
        query += " AND a.status = ?"
        params.append(STATUS_AGENDAMENTO_ATIVO)

    if data_inicio:
        query += " AND a.data >= ?"
        params.append(data_inicio)

    if data_fim:
        query += " AND a.data <= ?"
        params.append(data_fim)

    if recurso_id:
        query += " AND a.recurso_id = ?"
        params.append(recurso_id)

    if usuario_id:
        query += " AND a.usuario_id = ?"
        params.append(usuario_id)

    query += """
        ORDER BY
            a.data ASC,
            CAST(a.faixa_global AS INTEGER) ASC,
            r.nome ASC
    """

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def buscar_agendamento_por_id(agendamento_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM agendamentos
        WHERE id = ?
    """,
        (agendamento_id,),
    )

    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def cancelar_agendamento(agendamento_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE agendamentos
        SET status = ?, cancelado_em = datetime('now')
        WHERE id = ?
          AND status = ?
    """,
        (
            STATUS_AGENDAMENTO_CANCELADO,
            agendamento_id,
            STATUS_AGENDAMENTO_ATIVO,
        ),
    )

    alterados = cursor.rowcount
    conn.commit()
    conn.close()
    return alterados > 0


def criar_registro_pcpi_manual(
    data: str,
    turno: str,
    tipo_acao: str,
    descricao_curta: str,
    *,
    origem: str = "MANUAL",
    agendamento_id: int | None = None,
    acao_realizada: str = "",
    professor_nome: str = "",
    componente: str = "",
    turma: str = "",
    resultado: str = "",
    observacoes: str = "",
    criado_por_usuario_id: int | None = None,
    atualizado_por_usuario_id: int | None = None,
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO pcpi_registros_manuais (
            data,
            turno,
            tipo_acao,
            origem,
            agendamento_id,
            acao_realizada,
            professor_nome,
            componente,
            turma,
            descricao_curta,
            resultado,
            observacoes,
            criado_por_usuario_id,
            atualizado_por_usuario_id,
            criado_em,
            atualizado_em
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
    """,
        (
            data,
            turno,
            tipo_acao,
            origem or "MANUAL",
            agendamento_id,
            acao_realizada or None,
            professor_nome or None,
            componente or None,
            turma or None,
            descricao_curta,
            resultado or None,
            observacoes or None,
            criado_por_usuario_id,
            atualizado_por_usuario_id,
        ),
    )

    registro_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return registro_id


def listar_registros_pcpi_manuais(
    *,
    data: str | None = None,
    turno: str | None = None,
):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT
            id,
            data,
            turno,
            tipo_acao,
            COALESCE(origem, 'MANUAL') AS origem,
            agendamento_id,
            COALESCE(acao_realizada, '') AS acao_realizada,
            COALESCE(professor_nome, '') AS professor_nome,
            COALESCE(componente, '') AS componente,
            COALESCE(turma, '') AS turma,
            descricao_curta,
            COALESCE(resultado, '') AS resultado,
            COALESCE(observacoes, '') AS observacoes,
            criado_por_usuario_id,
            atualizado_por_usuario_id,
            criado_em,
            atualizado_em
        FROM pcpi_registros_manuais
        WHERE 1 = 1
    """
    params = []

    if data:
        query += " AND data = ?"
        params.append(data)

    if turno:
        query += " AND turno = ?"
        params.append(turno)

    query += """
        ORDER BY
            data ASC,
            turno ASC,
            criado_em ASC,
            id ASC
    """

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def buscar_registro_pcpi_manual_por_id(registro_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            data,
            turno,
            tipo_acao,
            COALESCE(origem, 'MANUAL') AS origem,
            agendamento_id,
            COALESCE(acao_realizada, '') AS acao_realizada,
            COALESCE(professor_nome, '') AS professor_nome,
            COALESCE(componente, '') AS componente,
            COALESCE(turma, '') AS turma,
            descricao_curta,
            COALESCE(resultado, '') AS resultado,
            COALESCE(observacoes, '') AS observacoes,
            criado_por_usuario_id,
            atualizado_por_usuario_id,
            criado_em,
            atualizado_em
        FROM pcpi_registros_manuais
        WHERE id = ?
    """,
        (int(registro_id),),
    )

    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def listar_periodos_pre_conselho():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            nome,
            ano_letivo,
            etapa,
            data_inicio,
            data_fim,
            status,
            criado_em,
            atualizado_em
        FROM pre_conselho_periodos
        ORDER BY ano_letivo DESC, etapa ASC, id ASC
    """)

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def buscar_periodo_pre_conselho_por_id(periodo_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            nome,
            ano_letivo,
            etapa,
            data_inicio,
            data_fim,
            status,
            criado_em,
            atualizado_em
        FROM pre_conselho_periodos
        WHERE id = ?
    """,
        (int(periodo_id),),
    )

    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def buscar_periodo_pre_conselho_por_ano_etapa(ano_letivo: int, etapa: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            nome,
            ano_letivo,
            etapa,
            data_inicio,
            data_fim,
            status,
            criado_em,
            atualizado_em
        FROM pre_conselho_periodos
        WHERE ano_letivo = ?
          AND etapa = ?
        LIMIT 1
    """,
        (int(ano_letivo), int(etapa)),
    )

    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def criar_periodo_pre_conselho(
    *,
    nome: str,
    ano_letivo: int,
    etapa: int,
    data_inicio: str,
    data_fim: str,
    status: str,
):
    nome_final = _normalizar_nome_catalogo(nome) or nome_periodo_pre_conselho(ano_letivo, etapa)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO pre_conselho_periodos (
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
            nome_final,
            int(ano_letivo),
            int(etapa),
            data_inicio,
            data_fim,
            status,
        ),
    )

    periodo_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return periodo_id


def atualizar_periodo_pre_conselho_dados(
    periodo_id: int,
    *,
    nome: str,
    ano_letivo: int,
    etapa: int,
    data_inicio: str,
    data_fim: str,
):
    nome_final = _normalizar_nome_catalogo(nome) or nome_periodo_pre_conselho(ano_letivo, etapa)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE pre_conselho_periodos
        SET nome = ?,
            ano_letivo = ?,
            etapa = ?,
            data_inicio = ?,
            data_fim = ?,
            atualizado_em = datetime('now')
        WHERE id = ?
    """,
        (
            nome_final,
            int(ano_letivo),
            int(etapa),
            data_inicio,
            data_fim,
            int(periodo_id),
        ),
    )

    alterado = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return alterado


def atualizar_status_periodo_pre_conselho(periodo_id: int, status: str):
    conn = get_connection()
    cursor = conn.cursor()

    if status == STATUS_PERIODO_PRE_CONSELHO_ABERTO:
        cursor.execute(
            """
            UPDATE pre_conselho_periodos
            SET status = 'FECHADO',
                atualizado_em = datetime('now')
            WHERE id <> ?
              AND ano_letivo = (
                  SELECT ano_letivo
                  FROM pre_conselho_periodos
                  WHERE id = ?
                  LIMIT 1
              )
        """,
            (int(periodo_id), int(periodo_id)),
        )

    cursor.execute(
        """
        UPDATE pre_conselho_periodos
        SET status = ?,
            atualizado_em = datetime('now')
        WHERE id = ?
    """,
        (status, int(periodo_id)),
    )

    alterado = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return alterado


def listar_motivos_pre_conselho(*, incluir_inativos: bool = False):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT
            id,
            categoria,
            codigo,
            descricao,
            ativo,
            ordem,
            criado_em,
            atualizado_em
        FROM pre_conselho_motivos
    """
    if not incluir_inativos:
        query += " WHERE ativo = 1"
    query += " ORDER BY categoria ASC, ordem ASC, descricao COLLATE NOCASE ASC"

    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def buscar_motivo_pre_conselho_por_id(motivo_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            categoria,
            codigo,
            descricao,
            ativo,
            ordem,
            criado_em,
            atualizado_em
        FROM pre_conselho_motivos
        WHERE id = ?
    """,
        (int(motivo_id),),
    )

    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def buscar_motivo_pre_conselho_por_codigo(codigo: str):
    codigo_limpo = _normalizar_nome_catalogo(codigo)
    if not codigo_limpo:
        return None

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            categoria,
            codigo,
            descricao,
            ativo,
            ordem,
            criado_em,
            atualizado_em
        FROM pre_conselho_motivos
        WHERE codigo = ? COLLATE NOCASE
        LIMIT 1
    """,
        (codigo_limpo,),
    )

    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def buscar_motivos_pre_conselho_por_ids(motivo_ids: list[int]):
    ids_validos = []
    for motivo_id in motivo_ids or []:
        try:
            valor = int(motivo_id)
        except (TypeError, ValueError):
            continue
        if valor > 0 and valor not in ids_validos:
            ids_validos.append(valor)

    if not ids_validos:
        return []

    placeholders = ",".join("?" for _ in ids_validos)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"""
        SELECT
            id,
            categoria,
            codigo,
            descricao,
            ativo,
            ordem,
            criado_em,
            atualizado_em
        FROM pre_conselho_motivos
        WHERE id IN ({placeholders})
        ORDER BY categoria ASC, ordem ASC, descricao COLLATE NOCASE ASC
    """,
        ids_validos,
    )

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def criar_motivo_pre_conselho(
    *,
    categoria: str,
    codigo: str,
    descricao: str,
    ordem: int = 0,
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO pre_conselho_motivos (
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
            categoria,
            codigo,
            descricao,
            int(ordem or 0),
        ),
    )

    motivo_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return motivo_id


def atualizar_motivo_pre_conselho_dados(
    motivo_id: int,
    *,
    categoria: str,
    descricao: str,
    ordem: int = 0,
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE pre_conselho_motivos
        SET categoria = ?,
            descricao = ?,
            ordem = ?,
            atualizado_em = datetime('now')
        WHERE id = ?
    """,
        (
            categoria,
            descricao,
            int(ordem or 0),
            int(motivo_id),
        ),
    )

    alterado = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return alterado


def atualizar_status_motivo_pre_conselho(motivo_id: int, ativo: bool):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE pre_conselho_motivos
        SET ativo = ?,
            atualizado_em = datetime('now')
        WHERE id = ?
    """,
        (1 if ativo else 0, int(motivo_id)),
    )

    alterado = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return alterado


def contar_registros_pre_conselho_por_professor_periodo(periodo_id: int, professor_usuario_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            turma_id,
            disciplina_id,
            COUNT(*) AS total
        FROM pre_conselho_registros
        WHERE periodo_id = ?
          AND professor_usuario_id = ?
        GROUP BY turma_id, disciplina_id
    """,
        (int(periodo_id), int(professor_usuario_id)),
    )

    rows = cursor.fetchall()
    conn.close()
    return {
        (int(row["turma_id"]), int(row["disciplina_id"] or 0)): int(row["total"] or 0)
        for row in rows
    }


def _buscar_registro_pre_conselho_unico(
    cursor,
    *,
    periodo_id: int,
    turma_id: int,
    disciplina_id: int,
    professor_usuario_id: int,
    estudante_id: int,
):
    cursor.execute(
        """
        SELECT id
        FROM pre_conselho_registros
        WHERE periodo_id = ?
          AND turma_id = ?
          AND disciplina_id = ?
          AND professor_usuario_id = ?
          AND estudante_id = ?
        LIMIT 1
    """,
        (
            int(periodo_id),
            int(turma_id),
            int(disciplina_id),
            int(professor_usuario_id),
            int(estudante_id),
        ),
    )
    row = cursor.fetchone()
    return int(row["id"]) if row else None


def _sincronizar_motivos_registro_pre_conselho(cursor, registro_id: int, motivo_ids: list[int]):
    ids_validos = []
    for motivo_id in motivo_ids or []:
        try:
            valor = int(motivo_id)
        except (TypeError, ValueError):
            continue
        if valor > 0 and valor not in ids_validos:
            ids_validos.append(valor)

    cursor.execute(
        """
        DELETE FROM pre_conselho_registro_motivos
        WHERE registro_id = ?
    """,
        (int(registro_id),),
    )

    for motivo_id in ids_validos:
        cursor.execute(
            """
            INSERT OR IGNORE INTO pre_conselho_registro_motivos (
                registro_id,
                motivo_id,
                criado_em
            )
            VALUES (?, ?, datetime('now'))
        """,
            (int(registro_id), motivo_id),
        )


def _carregar_motivos_pre_conselho_por_registro_ids(
    cursor, registro_ids: list[int]
) -> dict[int, list[dict]]:
    ids_validos = []
    for registro_id in registro_ids or []:
        try:
            valor = int(registro_id)
        except (TypeError, ValueError):
            continue
        if valor > 0 and valor not in ids_validos:
            ids_validos.append(valor)

    if not ids_validos:
        return {}

    placeholders = ",".join("?" for _ in ids_validos)
    cursor.execute(
        f"""
        SELECT
            rm.registro_id,
            m.id,
            m.categoria,
            m.codigo,
            m.descricao,
            m.ativo,
            m.ordem,
            m.criado_em,
            m.atualizado_em
        FROM pre_conselho_registro_motivos rm
        INNER JOIN pre_conselho_motivos m ON m.id = rm.motivo_id
        WHERE rm.registro_id IN ({placeholders})
        ORDER BY m.categoria ASC, m.ordem ASC, m.descricao COLLATE NOCASE ASC
    """,
        ids_validos,
    )

    mapa = {registro_id: [] for registro_id in ids_validos}
    for row in cursor.fetchall():
        item = dict(row)
        registro_id = int(item.pop("registro_id"))
        mapa.setdefault(registro_id, []).append(item)
    return mapa


def _normalizar_campos_pos_preconselho(item: dict) -> dict:
    motivo_ids = _desserializar_lista_texto(item.get("pos_preconselho_motivos"))
    observacao = item.get("pos_preconselho_observacao", "") or ""
    recuperado = normalizar_status_pos_pre_conselho(
        _normalizar_booleano_tristate(item.get("pos_preconselho_recuperado")),
        motivo_ids,
        observacao,
    )
    return {
        "pos_preconselho_recuperado": recuperado,
        "pos_preconselho_motivo_ids": motivo_ids if recuperado is not None else [],
        "pos_preconselho_motivos": descrever_motivos_pos_pre_conselho(motivo_ids, recuperado),
        "pos_preconselho_observacao": observacao,
    }


def _normalizar_linha_registro_pre_conselho(
    item: dict, motivos_map: dict[int, list[dict]] | None = None
) -> dict:
    registro_id = int(item["id"])
    motivos = list(motivos_map.get(registro_id, [])) if motivos_map else []
    pos_preconselho = _normalizar_campos_pos_preconselho(item)
    return {
        "id": registro_id,
        "periodo_id": int(item.get("periodo_id") or 0) or None,
        "periodo_nome": item.get("periodo_nome", "") or "",
        "ano_letivo": int(item.get("ano_letivo") or 0),
        "etapa": int(item.get("etapa") or 0),
        "professor_id": int(item.get("professor_id") or item.get("professor_usuario_id") or 0),
        "professor_nome": item.get("professor_nome", "") or "",
        "turma_id": int(item.get("turma_id") or 0),
        "turma_nome": item.get("turma_nome", "") or "",
        "disciplina_id": int(item.get("disciplina_id") or 0) or None,
        "disciplina_nome": item.get("disciplina_nome", "") or "",
        "estudante_id": int(item.get("estudante_id") or 0),
        "estudante_nome": item.get("estudante_nome", "") or "",
        "nivel_atencao": item.get("nivel_atencao", "") or "",
        "observacao_professor": item.get("observacao_professor", "") or "",
        "texto_gerado": item.get("texto_gerado", "") or "",
        "criado_em": item.get("criado_em", "") or "",
        "atualizado_em": item.get("atualizado_em", "") or "",
        "motivo_ids": [int(motivo["id"]) for motivo in motivos],
        "motivos": motivos,
        "periodo_status": item.get("periodo_status", "") or "",
        **pos_preconselho,
    }


def criar_ou_atualizar_registro_pre_conselho(
    *,
    periodo_id: int,
    turma_id: int,
    disciplina_id: int,
    professor_usuario_id: int,
    estudante_id: int,
    ano_letivo: int,
    etapa: int,
    disciplina_nome: str,
    motivo_ids: list[int],
    texto_gerado: str,
    observacao_professor: str = "",
    nivel_atencao: str = "",
    pos_preconselho_recuperado: bool | None = None,
    pos_preconselho_motivo_ids: list[str] | None = None,
    pos_preconselho_observacao: str = "",
):
    conn = get_connection()
    cursor = conn.cursor()

    periodo_id_valor = int(periodo_id)
    turma_id_valor = int(turma_id)
    disciplina_id_valor = int(disciplina_id)
    professor_usuario_id_valor = int(professor_usuario_id)
    estudante_id_valor = int(estudante_id)
    ano_letivo_valor = int(ano_letivo)
    etapa_valor = int(etapa)
    disciplina_nome_limpo = _normalizar_nome_catalogo(disciplina_nome)
    observacao_limpa = _normalizar_nome_catalogo(observacao_professor)
    nivel_atencao_limpo = _normalizar_nome_catalogo(nivel_atencao) or None
    pos_preconselho_recuperado_limpo = normalizar_status_pos_pre_conselho(
        pos_preconselho_recuperado,
        pos_preconselho_motivo_ids,
        pos_preconselho_observacao,
    )
    pos_preconselho_motivos_json = _serializar_lista_texto(pos_preconselho_motivo_ids)
    pos_preconselho_observacao_limpa = _normalizar_nome_catalogo(pos_preconselho_observacao)
    texto_gerado_limpo = str(texto_gerado or "").strip()

    motivo_ids_validos = []
    for motivo_id in motivo_ids or []:
        try:
            valor = int(motivo_id)
        except (TypeError, ValueError):
            continue
        if valor > 0 and valor not in motivo_ids_validos:
            motivo_ids_validos.append(valor)

    motivos_json = _serializar_lista_texto(
        [
            str(motivo["codigo"])
            for motivo in buscar_motivos_pre_conselho_por_ids(motivo_ids_validos)
        ]
    )

    registro_id = _buscar_registro_pre_conselho_unico(
        cursor,
        periodo_id=periodo_id_valor,
        turma_id=turma_id_valor,
        disciplina_id=disciplina_id_valor,
        professor_usuario_id=professor_usuario_id_valor,
        estudante_id=estudante_id_valor,
    )

    if registro_id:
        cursor.execute(
            """
            UPDATE pre_conselho_registros
            SET periodo_id = ?,
                disciplina_id = ?,
                professor_usuario_id = ?,
                turma_id = ?,
                estudante_id = ?,
                nivel_atencao = ?,
                disciplina = ?,
                ano_letivo = ?,
                bimestre = ?,
                motivos = ?,
                observacoes = ?,
                observacao_professor = ?,
                pos_preconselho_recuperado = ?,
                pos_preconselho_motivos = ?,
                pos_preconselho_observacao = ?,
                texto_gerado = ?,
                atualizado_em = datetime('now')
            WHERE id = ?
        """,
            (
                periodo_id_valor,
                disciplina_id_valor,
                professor_usuario_id_valor,
                turma_id_valor,
                estudante_id_valor,
                nivel_atencao_limpo,
                disciplina_nome_limpo,
                ano_letivo_valor,
                etapa_valor,
                motivos_json,
                observacao_limpa,
                observacao_limpa,
                None if pos_preconselho_recuperado_limpo is None else int(pos_preconselho_recuperado_limpo),
                pos_preconselho_motivos_json,
                pos_preconselho_observacao_limpa,
                texto_gerado_limpo,
                int(registro_id),
            ),
        )
    else:
        cursor.execute(
            """
            INSERT INTO pre_conselho_registros (
                periodo_id,
                disciplina_id,
                professor_usuario_id,
                turma_id,
                estudante_id,
                nivel_atencao,
                disciplina,
                ano_letivo,
                bimestre,
                motivos,
                observacoes,
                observacao_professor,
                pos_preconselho_recuperado,
                pos_preconselho_motivos,
                pos_preconselho_observacao,
                texto_gerado,
                criado_em,
                atualizado_em
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        """,
            (
                periodo_id_valor,
                disciplina_id_valor,
                professor_usuario_id_valor,
                turma_id_valor,
                estudante_id_valor,
                nivel_atencao_limpo,
                disciplina_nome_limpo,
                ano_letivo_valor,
                etapa_valor,
                motivos_json,
                observacao_limpa,
                observacao_limpa,
                None if pos_preconselho_recuperado_limpo is None else int(pos_preconselho_recuperado_limpo),
                pos_preconselho_motivos_json,
                pos_preconselho_observacao_limpa,
                texto_gerado_limpo,
            ),
        )
        registro_id = int(cursor.lastrowid)

    _sincronizar_motivos_registro_pre_conselho(cursor, int(registro_id), motivo_ids_validos)
    conn.commit()
    conn.close()
    return int(registro_id)


def listar_registros_pre_conselho(
    *,
    periodo_id: int | None = None,
    turma_id: int | None = None,
    disciplina_id: int | None = None,
    professor_usuario_id: int | None = None,
    estudante_id: int | None = None,
):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT
            r.id,
            r.periodo_id,
            COALESCE(p.nome, '') AS periodo_nome,
            COALESCE(p.ano_letivo, r.ano_letivo, 0) AS ano_letivo,
            COALESCE(p.etapa, r.bimestre, 0) AS etapa,
            COALESCE(p.status, '') AS periodo_status,
            r.professor_usuario_id AS professor_id,
            COALESCE(u.nome, '') AS professor_nome,
            r.turma_id,
            COALESCE(t.nome, '') AS turma_nome,
            r.disciplina_id,
            COALESCE(d.nome, r.disciplina, '') AS disciplina_nome,
            r.estudante_id,
            COALESCE(e.nome, '') AS estudante_nome,
            COALESCE(r.nivel_atencao, '') AS nivel_atencao,
            COALESCE(r.observacao_professor, r.observacoes, '') AS observacao_professor,
            r.pos_preconselho_recuperado,
            COALESCE(r.pos_preconselho_motivos, '[]') AS pos_preconselho_motivos,
            COALESCE(r.pos_preconselho_observacao, '') AS pos_preconselho_observacao,
            COALESCE(r.texto_gerado, '') AS texto_gerado,
            r.criado_em,
            r.atualizado_em
        FROM pre_conselho_registros r
        LEFT JOIN pre_conselho_periodos p ON p.id = r.periodo_id
        LEFT JOIN usuarios u ON u.id = r.professor_usuario_id
        LEFT JOIN turmas t ON t.id = r.turma_id
        LEFT JOIN disciplinas d ON d.id = r.disciplina_id
        LEFT JOIN estudantes e ON e.id = r.estudante_id
        WHERE 1 = 1
    """
    params = []

    if periodo_id is not None and int(periodo_id or 0) > 0:
        query += " AND r.periodo_id = ?"
        params.append(int(periodo_id))
    if turma_id is not None and int(turma_id or 0) > 0:
        query += " AND r.turma_id = ?"
        params.append(int(turma_id))
    if disciplina_id is not None and int(disciplina_id or 0) > 0:
        query += " AND r.disciplina_id = ?"
        params.append(int(disciplina_id))
    if professor_usuario_id is not None and int(professor_usuario_id or 0) > 0:
        query += " AND r.professor_usuario_id = ?"
        params.append(int(professor_usuario_id))
    if estudante_id is not None and int(estudante_id or 0) > 0:
        query += " AND r.estudante_id = ?"
        params.append(int(estudante_id))

    query += """
        ORDER BY
            t.nome COLLATE NOCASE ASC,
            d.nome COLLATE NOCASE ASC,
            e.nome COLLATE NOCASE ASC,
            r.id ASC
    """

    cursor.execute(query, params)
    rows = cursor.fetchall()
    motivos_map = _carregar_motivos_pre_conselho_por_registro_ids(
        cursor,
        [int(row["id"]) for row in rows],
    )
    itens = [_normalizar_linha_registro_pre_conselho(dict(row), motivos_map) for row in rows]
    conn.close()
    return itens


def buscar_registro_pre_conselho_por_id(registro_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            r.id,
            r.periodo_id,
            COALESCE(p.nome, '') AS periodo_nome,
            COALESCE(p.ano_letivo, r.ano_letivo, 0) AS ano_letivo,
            COALESCE(p.etapa, r.bimestre, 0) AS etapa,
            COALESCE(p.status, '') AS periodo_status,
            r.professor_usuario_id AS professor_id,
            COALESCE(u.nome, '') AS professor_nome,
            r.turma_id,
            COALESCE(t.nome, '') AS turma_nome,
            r.disciplina_id,
            COALESCE(d.nome, r.disciplina, '') AS disciplina_nome,
            r.estudante_id,
            COALESCE(e.nome, '') AS estudante_nome,
            COALESCE(r.nivel_atencao, '') AS nivel_atencao,
            COALESCE(r.observacao_professor, r.observacoes, '') AS observacao_professor,
            r.pos_preconselho_recuperado,
            COALESCE(r.pos_preconselho_motivos, '[]') AS pos_preconselho_motivos,
            COALESCE(r.pos_preconselho_observacao, '') AS pos_preconselho_observacao,
            COALESCE(r.texto_gerado, '') AS texto_gerado,
            r.criado_em,
            r.atualizado_em
        FROM pre_conselho_registros r
        LEFT JOIN pre_conselho_periodos p ON p.id = r.periodo_id
        LEFT JOIN usuarios u ON u.id = r.professor_usuario_id
        LEFT JOIN turmas t ON t.id = r.turma_id
        LEFT JOIN disciplinas d ON d.id = r.disciplina_id
        LEFT JOIN estudantes e ON e.id = r.estudante_id
        WHERE r.id = ?
    """,
        (int(registro_id),),
    )

    row = cursor.fetchone()
    if not row:
        conn.close()
        return None

    motivos_map = _carregar_motivos_pre_conselho_por_registro_ids(cursor, [int(registro_id)])
    item = _normalizar_linha_registro_pre_conselho(dict(row), motivos_map)
    conn.close()
    return item


def listar_estudantes_pre_conselho_painel(
    *,
    periodo_id: int,
    turma_id: int,
    disciplina_id: int,
    professor_usuario_id: int,
    busca_nome: str = "",
    status: str = "todos",
):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT
            e.id AS estudante_id,
            e.nome,
            e.turma_id,
            COALESCE(t.nome, '') AS turma_nome,
            r.id AS registro_id,
            COALESCE(r.nivel_atencao, '') AS nivel_atencao,
            COALESCE(r.observacao_professor, r.observacoes, '') AS observacao_professor,
            r.pos_preconselho_recuperado,
            COALESCE(r.pos_preconselho_motivos, '[]') AS pos_preconselho_motivos,
            COALESCE(r.pos_preconselho_observacao, '') AS pos_preconselho_observacao,
            COALESCE(r.texto_gerado, '') AS texto_gerado
        FROM estudantes e
        LEFT JOIN turmas t ON t.id = e.turma_id
        LEFT JOIN pre_conselho_registros r
            ON r.estudante_id = e.id
           AND r.periodo_id = ?
           AND r.turma_id = e.turma_id
           AND r.disciplina_id = ?
           AND r.professor_usuario_id = ?
        WHERE e.ativo = 1
          AND e.turma_id = ?
    """
    params = [
        int(periodo_id),
        int(disciplina_id),
        int(professor_usuario_id),
        int(turma_id),
    ]

    nome_limpo = _normalizar_nome_catalogo(busca_nome).lower()
    if nome_limpo:
        query += " AND LOWER(COALESCE(e.nome, '')) LIKE ?"
        params.append(f"%{nome_limpo}%")

    status_limpo = _normalizar_nome_catalogo(status).lower()
    if status_limpo == "sinalizados":
        query += " AND r.id IS NOT NULL"
    elif status_limpo == "nao_sinalizados":
        query += " AND r.id IS NULL"

    query += " ORDER BY e.nome COLLATE NOCASE ASC, e.id ASC"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    registro_ids = [int(row["registro_id"]) for row in rows if row["registro_id"] is not None]
    motivos_map = _carregar_motivos_pre_conselho_por_registro_ids(cursor, registro_ids)
    conn.close()

    itens = []
    for row in rows:
        item = dict(row)
        registro_id = int(item["registro_id"]) if item["registro_id"] is not None else None
        motivos = list(motivos_map.get(int(registro_id), [])) if registro_id else []
        pos_preconselho = _normalizar_campos_pos_preconselho(item)
        itens.append(
            {
                "estudante_id": int(item["estudante_id"]),
                "nome": item["nome"],
                "turma_id": int(item["turma_id"]),
                "turma_nome": item["turma_nome"],
                "sinalizado": registro_id is not None,
                "registro_id": registro_id,
                "nivel_atencao": item.get("nivel_atencao", "") or "",
                "observacao_professor": item.get("observacao_professor", "") or "",
                "texto_gerado": item.get("texto_gerado", "") or "",
                "motivo_ids": [int(motivo["id"]) for motivo in motivos],
                "motivos": motivos,
                **pos_preconselho,
            }
        )
    return itens


def excluir_registro_pre_conselho(registro_id: int, *, professor_usuario_id: int | None = None):
    conn = get_connection()
    cursor = conn.cursor()

    query = "DELETE FROM pre_conselho_registros WHERE id = ?"
    params = [int(registro_id)]
    if professor_usuario_id is not None:
        query += " AND professor_usuario_id = ?"
        params.append(int(professor_usuario_id))

    cursor.execute(query, params)
    alterado = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return alterado
