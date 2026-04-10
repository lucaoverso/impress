import sqlite3
import uuid
import hashlib
import json
import os
import shutil
import unicodedata
from pathlib import Path
from security.nt_hash import generate_nt_hash
from services.ocorrencia_disciplina_service import ACAO_OCORRENCIA_VALIDAS
from services.preconselho_service import (
    STATUS_PERIODO_PRE_CONSELHO_ABERTO,
    catalogo_motivos_iniciais_pre_conselho,
    nome_periodo_pre_conselho,
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
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO jobs (
            usuario_id, arquivo, arquivo_path, copias, paginas_por_folha, duplex, orientacao,
            intervalo_paginas, cups_options, printer_name, paginas_totais, status, prioridade, criado_em
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDENTE', 0, datetime('now'))
    """, (
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
    ))

    job_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return job_id

def listar_jobs_ativos():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM jobs
        WHERE status NOT IN (?, ?)
        ORDER BY criado_em DESC
    """, (STATUS_CONCLUIDO, STATUS_FINALIZADO_LEGADO))

    rows = cursor.fetchall()
    conn.close()

    return [dict(r) for r in rows]

def listar_historico(data_inicio=None, data_fim=None, usuario_id=None):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT * FROM jobs
        WHERE status IN (?, ?)
    """

    params = [STATUS_CONCLUIDO, STATUS_FINALIZADO_LEGADO]

    if data_inicio:
        query += " AND criado_em >= ?"
        params.append(data_inicio)

    if data_fim:
        query += " AND criado_em <= ?"
        params.append(data_fim)

    if usuario_id:
        query += " AND usuario_id = ?"
        params.append(usuario_id)

    query += " ORDER BY criado_em DESC"

    cursor.execute(query, params)

    rows = cursor.fetchall()
    conn.close()

    return [dict(r) for r in rows]

def listar_jobs_por_usuario(usuario_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM jobs
        WHERE usuario_id = ?
        ORDER BY criado_em DESC
    """, (usuario_id,))

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
            ativo INTEGER NOT NULL DEFAULT 1,
            criado_em TEXT NOT NULL
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
            professor_nome TEXT,
            componente TEXT,
            turma TEXT,
            descricao_curta TEXT NOT NULL,
            observacoes TEXT,
            criado_por_usuario_id INTEGER,
            atualizado_por_usuario_id INTEGER,
            criado_em TEXT NOT NULL DEFAULT (datetime('now')),
            atualizado_em TEXT NOT NULL DEFAULT (datetime('now')),
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
            nome_estudante TEXT NOT NULL,
            estudante_id INTEGER,
            turma_id INTEGER NOT NULL,
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

    _garantir_colunas_usuarios(cursor)
    _garantir_colunas_tokens(cursor)
    _garantir_colunas_jobs(cursor)
    _garantir_colunas_agendamentos(cursor)
    _garantir_colunas_professores_carga(cursor)
    _garantir_colunas_cota_regras(cursor)
    _garantir_colunas_recursos(cursor)
    _garantir_colunas_turmas(cursor)
    _garantir_colunas_disciplinas(cursor)
    _garantir_colunas_estudantes(cursor)
    _garantir_colunas_pre_conselho_periodos(cursor)
    _garantir_colunas_pre_conselho_motivos(cursor)
    _garantir_colunas_pre_conselho_registros(cursor)
    _garantir_colunas_pre_conselho_registro_motivos(cursor)
    _garantir_colunas_ocorrencias(cursor)
    _garantir_colunas_ocorrencia_regimento_itens(cursor)
    _migrar_base_legal_legado(cursor)
    _garantir_view_radcheck(cursor)
    _seed_catalogos_academicos(cursor)
    _migrar_catalogos_academicos(cursor)
    _seed_pre_conselho_periodos(cursor)
    _seed_pre_conselho_motivos(cursor)
    _migrar_registros_pre_conselho_legado(cursor)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_jobs_status_prioridade_criado_em
        ON jobs(status, prioridade, criado_em)
    """)

    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_cotas_usuario_mes
        ON cotas(usuario_id, mes)
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

    cursor.execute("""
        INSERT OR IGNORE INTO cota_regras (
            id, base_paginas, paginas_por_aula, paginas_por_turma, cota_mensal_escola, atualizado_em
        )
        VALUES (1, ?, ?, ?, ?, datetime('now'))
    """, (
        COTA_BASE_PADRAO,
        COTA_POR_AULA_PADRAO,
        COTA_POR_TURMA_PADRAO,
        COTA_MENSAL_ESCOLA_PADRAO,
    ))

    conn.commit()
    conn.close()

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
    cursor.executemany("""
        INSERT OR IGNORE INTO turmas (nome, turno, quantidade_estudantes, ativo, criado_em)
        VALUES (?, '', 0, 1, datetime('now'))
    """, [(nome,) for nome in TURMAS_PADRAO])

    cursor.executemany("""
        INSERT OR IGNORE INTO disciplinas (nome, aulas_semanais, ativo, criado_em)
        VALUES (?, 0, 1, datetime('now'))
    """, [(nome,) for nome in DISCIPLINAS_PADRAO])

def _migrar_catalogos_academicos(cursor):
    cursor.execute("""
        SELECT COALESCE(turmas, '[]') AS turmas, COALESCE(disciplinas, '[]') AS disciplinas
        FROM professores_carga
    """)
    for row in cursor.fetchall():
        for turma in _desserializar_lista_texto(row["turmas"]):
            nome = _normalizar_nome_catalogo(turma)
            if nome:
                cursor.execute("""
                    INSERT OR IGNORE INTO turmas (nome, turno, quantidade_estudantes, ativo, criado_em)
                    VALUES (?, '', 0, 1, datetime('now'))
                """, (nome,))

        for disciplina in _desserializar_lista_texto(row["disciplinas"]):
            nome = _normalizar_nome_catalogo(disciplina)
            if nome:
                cursor.execute("""
                    INSERT OR IGNORE INTO disciplinas (nome, aulas_semanais, ativo, criado_em)
                    VALUES (?, 0, 1, datetime('now'))
                """, (nome,))

    cursor.execute("""
        SELECT DISTINCT turma
        FROM agendamentos
        WHERE turma IS NOT NULL AND TRIM(turma) <> ''
    """)
    for row in cursor.fetchall():
        nome = _normalizar_nome_catalogo(row["turma"])
        if nome:
            cursor.execute("""
                INSERT OR IGNORE INTO turmas (nome, turno, quantidade_estudantes, ativo, criado_em)
                VALUES (?, '', 0, 1, datetime('now'))
            """, (nome,))

def _seed_pre_conselho_periodos(cursor):
    for periodo in periodos_padrao_pre_conselho():
        cursor.execute("""
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
        """, (
            periodo["nome"],
            int(periodo["ano_letivo"]),
            int(periodo["etapa"]),
            periodo["data_inicio"],
            periodo["data_fim"],
            periodo["status"],
        ))


def _seed_pre_conselho_motivos(cursor):
    for motivo in catalogo_motivos_iniciais_pre_conselho():
        cursor.execute("""
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
        """, (
            motivo["categoria"],
            motivo["codigo"],
            motivo["descricao"],
            int(motivo.get("ordem") or 0),
        ))


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
        _normalizar_nome_catalogo(row["codigo"]): int(row["id"])
        for row in cursor.fetchall()
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
            cursor.execute("""
                UPDATE pre_conselho_registros
                SET periodo_id = ?
                WHERE id = ?
            """, (periodo_id, registro_id))

        if disciplina_id <= 0 and disciplina:
            disciplina_id = int(disciplinas_por_nome.get(disciplina.casefold()) or 0)
            if disciplina_id > 0:
                cursor.execute("""
                    UPDATE pre_conselho_registros
                    SET disciplina_id = ?
                    WHERE id = ?
                """, (disciplina_id, registro_id))

        if not observacao_professor and observacoes:
            cursor.execute("""
                UPDATE pre_conselho_registros
                SET observacao_professor = ?
                WHERE id = ?
            """, (observacoes, registro_id))

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM pre_conselho_registro_motivos
            WHERE registro_id = ?
        """, (registro_id,))
        total_motivos = int(cursor.fetchone()["total"] or 0)
        if total_motivos > 0:
            continue

        for codigo in _desserializar_lista_texto(registro["motivos"]):
            motivo_id = int(motivos_por_codigo.get(_normalizar_nome_catalogo(codigo)) or 0)
            if motivo_id <= 0:
                continue
            cursor.execute("""
                INSERT OR IGNORE INTO pre_conselho_registro_motivos (
                    registro_id,
                    motivo_id,
                    criado_em
                )
                VALUES (?, ?, datetime('now'))
            """, (registro_id, motivo_id))

def _garantir_colunas_usuarios(cursor):
    cursor.execute("PRAGMA table_info(usuarios)")
    colunas = {row["name"] for row in cursor.fetchall()}

    if "cargo" not in colunas:
        cursor.execute(
            "ALTER TABLE usuarios ADD COLUMN cargo TEXT NOT NULL DEFAULT ''"
        )
    if "data_nascimento" not in colunas:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN data_nascimento TEXT")
    if "nt_hash" not in colunas:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN nt_hash CHAR(32)")
    if "ativo" not in colunas:
        cursor.execute(
            "ALTER TABLE usuarios ADD COLUMN ativo INTEGER NOT NULL DEFAULT 1"
        )

    # Backfill de cargo para bancos legados baseando-se no perfil existente.
    cursor.execute("""
        UPDATE usuarios
        SET cargo = UPPER(TRIM(cargo))
        WHERE TRIM(COALESCE(cargo, '')) <> ''
    """)
    cursor.execute("""
        UPDATE usuarios
        SET cargo = (
            CASE
                WHEN LOWER(TRIM(COALESCE(perfil, ''))) = 'admin' THEN ?
                WHEN LOWER(TRIM(COALESCE(perfil, ''))) = 'coordenador' THEN ?
                ELSE ?
            END
        )
        WHERE TRIM(COALESCE(cargo, '')) = ''
    """, (CARGO_ADMIN, CARGO_COORDENADOR, CARGO_PROFESSOR))

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
        cursor.execute(
            "ALTER TABLE tokens ADD COLUMN criado_em TEXT NOT NULL DEFAULT ''"
        )
    if "expira_em" not in colunas:
        cursor.execute(
            "ALTER TABLE tokens ADD COLUMN expira_em TEXT NOT NULL DEFAULT ''"
        )

    cursor.execute("""
        UPDATE tokens
        SET criado_em = datetime('now')
        WHERE TRIM(COALESCE(criado_em, '')) = ''
    """)
    cursor.execute("""
        UPDATE tokens
        SET expira_em = datetime('now', ?)
        WHERE TRIM(COALESCE(expira_em, '')) = ''
    """, (f"+{TOKEN_TTL_DIAS} days",))

    cursor.execute("""
        DELETE FROM tokens
        WHERE expira_em <= datetime('now')
    """)


def _garantir_colunas_jobs(cursor):
    cursor.execute("PRAGMA table_info(jobs)")
    colunas = {row["name"] for row in cursor.fetchall()}

    if "paginas_por_folha" not in colunas:
        cursor.execute(
            "ALTER TABLE jobs ADD COLUMN paginas_por_folha INTEGER NOT NULL DEFAULT 1"
        )
    if "duplex" not in colunas:
        cursor.execute("ALTER TABLE jobs ADD COLUMN duplex INTEGER NOT NULL DEFAULT 0")
    if "orientacao" not in colunas:
        cursor.execute(
            "ALTER TABLE jobs ADD COLUMN orientacao TEXT NOT NULL DEFAULT 'retrato'"
        )
    if "paginas_totais" not in colunas:
        cursor.execute(
            "ALTER TABLE jobs ADD COLUMN paginas_totais INTEGER NOT NULL DEFAULT 0"
        )
    if "arquivo_path" not in colunas:
        cursor.execute("ALTER TABLE jobs ADD COLUMN arquivo_path TEXT")
    if "intervalo_paginas" not in colunas:
        cursor.execute(
            "ALTER TABLE jobs ADD COLUMN intervalo_paginas TEXT NOT NULL DEFAULT ''"
        )
    if "cups_options" not in colunas:
        cursor.execute(
            "ALTER TABLE jobs ADD COLUMN cups_options TEXT NOT NULL DEFAULT '{}'"
        )
    if "printer_name" not in colunas:
        cursor.execute("ALTER TABLE jobs ADD COLUMN printer_name TEXT")
    if "cups_job_id" not in colunas:
        cursor.execute("ALTER TABLE jobs ADD COLUMN cups_job_id INTEGER")
    if "erro_mensagem" not in colunas:
        cursor.execute("ALTER TABLE jobs ADD COLUMN erro_mensagem TEXT")
    if "finalizado_em" not in colunas:
        cursor.execute("ALTER TABLE jobs ADD COLUMN finalizado_em TEXT")

def _garantir_colunas_agendamentos(cursor):
    cursor.execute("PRAGMA table_info(agendamentos)")
    colunas = {row["name"] for row in cursor.fetchall()}

    if "turno" not in colunas:
        cursor.execute(
            "ALTER TABLE agendamentos ADD COLUMN turno TEXT NOT NULL DEFAULT 'MATUTINO'"
        )
    if "turma" not in colunas:
        cursor.execute(
            "ALTER TABLE agendamentos ADD COLUMN turma TEXT NOT NULL DEFAULT ''"
        )
    if "status" not in colunas:
        cursor.execute(
            "ALTER TABLE agendamentos ADD COLUMN status TEXT NOT NULL DEFAULT 'ATIVO'"
        )
    if "cancelado_em" not in colunas:
        cursor.execute("ALTER TABLE agendamentos ADD COLUMN cancelado_em TEXT")
    if "faixa_global" not in colunas:
        cursor.execute(
            "ALTER TABLE agendamentos ADD COLUMN faixa_global INTEGER NOT NULL DEFAULT 0"
        )
    if "tema_aula" not in colunas:
        cursor.execute(
            "ALTER TABLE agendamentos ADD COLUMN tema_aula TEXT NOT NULL DEFAULT ''"
        )

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
        cursor.execute(
            "ALTER TABLE professores_carga ADD COLUMN turmas TEXT NOT NULL DEFAULT '[]'"
        )
    if "disciplinas" not in colunas:
        cursor.execute(
            "ALTER TABLE professores_carga ADD COLUMN disciplinas TEXT NOT NULL DEFAULT '[]'"
        )


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
        cursor.execute(
            "ALTER TABLE turmas ADD COLUMN turno TEXT NOT NULL DEFAULT ''"
        )
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
        cursor.execute("ALTER TABLE pre_conselho_periodos ADD COLUMN ano_letivo INTEGER NOT NULL DEFAULT 0")
    if "etapa" not in colunas:
        cursor.execute("ALTER TABLE pre_conselho_periodos ADD COLUMN etapa INTEGER NOT NULL DEFAULT 0")
    if "data_inicio" not in colunas:
        cursor.execute("ALTER TABLE pre_conselho_periodos ADD COLUMN data_inicio TEXT NOT NULL DEFAULT ''")
    if "data_fim" not in colunas:
        cursor.execute("ALTER TABLE pre_conselho_periodos ADD COLUMN data_fim TEXT NOT NULL DEFAULT ''")
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
        cursor.execute("ALTER TABLE pre_conselho_motivos ADD COLUMN categoria TEXT NOT NULL DEFAULT ''")
    if "codigo" not in colunas:
        cursor.execute("ALTER TABLE pre_conselho_motivos ADD COLUMN codigo TEXT NOT NULL DEFAULT ''")
    if "descricao" not in colunas:
        cursor.execute("ALTER TABLE pre_conselho_motivos ADD COLUMN descricao TEXT NOT NULL DEFAULT ''")
    if "ativo" not in colunas:
        cursor.execute("ALTER TABLE pre_conselho_motivos ADD COLUMN ativo INTEGER NOT NULL DEFAULT 1")
    if "ordem" not in colunas:
        cursor.execute("ALTER TABLE pre_conselho_motivos ADD COLUMN ordem INTEGER NOT NULL DEFAULT 0")
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
        cursor.execute(
            "ALTER TABLE pre_conselho_registros ADD COLUMN periodo_id INTEGER"
        )
    if "disciplina_id" not in colunas:
        cursor.execute(
            "ALTER TABLE pre_conselho_registros ADD COLUMN disciplina_id INTEGER"
        )
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
        cursor.execute(
            "ALTER TABLE pre_conselho_registros ADD COLUMN nivel_atencao TEXT"
        )
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
    colunas = {row["name"] for row in cursor.fetchall()}

    if "nome_estudante" not in colunas:
        cursor.execute("ALTER TABLE ocorrencias ADD COLUMN nome_estudante TEXT NOT NULL DEFAULT ''")
    if "estudante_id" not in colunas:
        cursor.execute("ALTER TABLE ocorrencias ADD COLUMN estudante_id INTEGER")
    if "turma_id" not in colunas:
        cursor.execute("ALTER TABLE ocorrencias ADD COLUMN turma_id INTEGER NOT NULL DEFAULT 0")
    if "professor_requerente" not in colunas:
        cursor.execute("ALTER TABLE ocorrencias ADD COLUMN professor_requerente TEXT NOT NULL DEFAULT ''")
    if "professor_requerente_id" not in colunas:
        cursor.execute("ALTER TABLE ocorrencias ADD COLUMN professor_requerente_id INTEGER")
    if "disciplina" not in colunas:
        cursor.execute("ALTER TABLE ocorrencias ADD COLUMN disciplina TEXT NOT NULL DEFAULT ''")
    if "data_ocorrencia" not in colunas:
        cursor.execute("ALTER TABLE ocorrencias ADD COLUMN data_ocorrencia TEXT NOT NULL DEFAULT ''")
    if "aula" not in colunas:
        cursor.execute("ALTER TABLE ocorrencias ADD COLUMN aula TEXT NOT NULL DEFAULT ''")
    if "horario_ocorrencia" not in colunas:
        cursor.execute("ALTER TABLE ocorrencias ADD COLUMN horario_ocorrencia TEXT NOT NULL DEFAULT ''")
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

    cursor.execute("""
        UPDATE ocorrencias
        SET status = ?
        WHERE TRIM(COALESCE(status, '')) = ''
    """, (STATUS_OCORRENCIA_REGISTRADO,))

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
    if sql_tabela and all(acao in sql_tabela for acao in ACAO_OCORRENCIA_VALIDAS):
        return

    cursor.execute("PRAGMA foreign_keys = OFF")
    cursor.execute("DROP TABLE IF EXISTS ocorrencias__tmp")
    cursor.execute(f"""
        CREATE TABLE ocorrencias__tmp (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_estudante TEXT NOT NULL,
            estudante_id INTEGER,
            turma_id INTEGER NOT NULL,
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
        INSERT INTO ocorrencias__tmp (
            id,
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
            COALESCE(nome_estudante, ''),
            estudante_id,
            COALESCE(turma_id, 0),
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
    """, (STATUS_OCORRENCIA_REGISTRADO,))
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
    cursor.execute("""
        SELECT id
        FROM artigos
        WHERE lei_id = ?
          AND numero = ? COLLATE NOCASE
        LIMIT 1
    """, (int(lei_id), numero_limpo))
    row = cursor.fetchone()
    if row:
        artigo_id = int(row["id"])
        cursor.execute(
            "UPDATE artigos SET descricao = ? WHERE id = ?",
            (descricao_limpa, artigo_id),
        )
        return artigo_id, False
    cursor.execute("""
        INSERT INTO artigos (lei_id, numero, descricao)
        VALUES (?, ?, ?)
    """, (int(lei_id), numero_limpo, descricao_limpa))
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
    cursor.execute("""
        SELECT id
        FROM incisos
        WHERE artigo_id = ?
          AND numero = ? COLLATE NOCASE
        LIMIT 1
    """, (int(artigo_id), numero_limpo))
    row = cursor.fetchone()
    if row:
        inciso_id = int(row["id"])
        cursor.execute(
            "UPDATE incisos SET descricao = ? WHERE id = ?",
            (descricao_limpa, inciso_id),
        )
        return inciso_id, False
    cursor.execute("""
        INSERT INTO incisos (artigo_id, numero, descricao)
        VALUES (?, ?, ?)
    """, (int(artigo_id), numero_limpo, descricao_limpa))
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
    cursor.execute("""
        SELECT id
        FROM alineas
        WHERE inciso_id = ?
          AND identificador = ? COLLATE NOCASE
        LIMIT 1
    """, (int(inciso_id), identificador_limpo))
    row = cursor.fetchone()
    if row:
        alinea_id = int(row["id"])
        cursor.execute(
            "UPDATE alineas SET descricao = ? WHERE id = ?",
            (descricao_limpa, alinea_id),
        )
        return alinea_id, False
    cursor.execute("""
        INSERT INTO alineas (inciso_id, identificador, descricao)
        VALUES (?, ?, ?)
    """, (int(inciso_id), identificador_limpo, descricao_limpa))
    return int(cursor.lastrowid), True


def _buscar_item_base_legal_por_tipo_cursor(cursor, tipo: str, entidade_id: int) -> dict | None:
    entidade_id_valor = int(entidade_id or 0)
    if entidade_id_valor <= 0:
        return None

    if tipo == TIPO_BASE_LEGAL_ARTIGO:
        cursor.execute("""
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
        """, (TIPO_BASE_LEGAL_ARTIGO, entidade_id_valor))
    elif tipo == TIPO_BASE_LEGAL_INCISO:
        cursor.execute("""
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
        """, (TIPO_BASE_LEGAL_INCISO, entidade_id_valor))
    elif tipo == TIPO_BASE_LEGAL_ALINEA:
        cursor.execute("""
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
        """, (TIPO_BASE_LEGAL_ALINEA, entidade_id_valor))
    else:
        return None

    row = cursor.fetchone()
    return _montar_item_base_legal(row) if row else None


def _listar_itens_base_legal_cursor(cursor) -> list[dict]:
    itens = []

    cursor.execute("""
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
    """, (TIPO_BASE_LEGAL_ARTIGO,))
    itens.extend(_montar_item_base_legal(row) for row in cursor.fetchall())

    cursor.execute("""
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
    """, (TIPO_BASE_LEGAL_INCISO,))
    itens.extend(_montar_item_base_legal(row) for row in cursor.fetchall())

    cursor.execute("""
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
    """, (TIPO_BASE_LEGAL_ALINEA,))
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
        cursor.execute("ALTER TABLE ocorrencia_regimento_itens ADD COLUMN alinea_identificador TEXT")
    if "alinea_descricao" not in colunas:
        cursor.execute("ALTER TABLE ocorrencia_regimento_itens ADD COLUMN alinea_descricao TEXT")

    # Bancos antigos vinculavam regimento_item_id a regimento_itens; os IDs atuais
    # codificam artigos/incisos/alineas e precisam de um snapshot sem essa FK legada.
    if _ocorrencia_regimento_itens_tem_fk_legada(cursor):
        _recriar_tabela_ocorrencia_regimento_itens_sem_fk_legada(cursor)


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
        cursor.execute("""
            UPDATE ocorrencia_regimento_itens
            SET regimento_item_id = ?,
                artigo_id = COALESCE(artigo_id, ?)
            WHERE regimento_item_id = ?
              AND (artigo_id IS NULL OR artigo_id <= 0)
        """, (item_id_novo, artigo_id_novo, regimento_item_id_legado))


def _mapear_regimento_itens_por_ocorrencia(cursor, ocorrencia_ids: list[int]) -> dict[int, list[dict]]:
    ids_validos = [int(ocorrencia_id) for ocorrencia_id in ocorrencia_ids if int(ocorrencia_id) > 0]
    if not ids_validos:
        return {}

    placeholders = ",".join(["?"] * len(ids_validos))
    cursor.execute(f"""
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
    """, [TIPO_BASE_LEGAL_ALINEA, TIPO_BASE_LEGAL_INCISO, TIPO_BASE_LEGAL_ARTIGO, *ids_validos])

    mapa: dict[int, list[dict]] = {}
    for row in cursor.fetchall():
        ocorrencia_id = int(row["ocorrencia_id"])
        mapa.setdefault(ocorrencia_id, []).append(
            {
                "regimento_item_id": int(row["regimento_item_id"]) if row["regimento_item_id"] is not None else None,
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

    cursor.execute("""
        INSERT INTO tokens (token, usuario_id, criado_em, expira_em)
        VALUES (?, ?, datetime('now'), ?)
    """, (token, usuario_id, expira_em))

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
    cursor.execute("""
        DELETE FROM tokens
        WHERE usuario_id = ?
    """, (usuario_id,))
    removidos = cursor.rowcount
    conn.commit()
    conn.close()
    return removidos

def buscar_usuario_por_token(token: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(f"""
        SELECT u.id, u.nome, u.email, u.perfil, u.cargo
        FROM usuarios u
        JOIN tokens t ON u.id = t.usuario_id
        WHERE t.token = ?
          AND t.expira_em > datetime('now')
          AND {_clausula_usuario_ativo('u')}
    """, (token,))

    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None

#hash para senhas
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

    cursor.execute("""
        INSERT INTO usuarios (nome, email, senha_hash, nt_hash, perfil, cargo)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        nome,
        email,
        hash_senha(senha),
        nt_hash,
        perfil,
        cargo_norm
    ))

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
        SELECT id, nome, email, perfil, cargo, data_nascimento, ativo
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

    cursor.execute("""
        INSERT INTO usuarios (nome, email, senha_hash, nt_hash, perfil, cargo)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (nome, email, senha_hash, nt_hash_final, perfil, cargo_norm))

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
):
    conn = get_connection()
    cursor = conn.cursor()

    turmas_json = _serializar_lista_texto(turmas)
    disciplinas_json = _serializar_lista_texto(disciplinas)
    nt_hash_final = _normalizar_nt_hash(nt_hash)

    cursor.execute("""
        INSERT INTO usuarios (nome, email, senha_hash, nt_hash, perfil, cargo, data_nascimento)
        VALUES (?, ?, ?, ?, 'professor', ?, ?)
    """, (nome, email, senha_hash, nt_hash_final, CARGO_PROFESSOR, data_nascimento or None))

    usuario_id = cursor.lastrowid
    cursor.execute("""
        INSERT INTO professores_carga (
            usuario_id, aulas_semanais, turmas_quantidade, turmas, disciplinas, atualizado_em
        )
        VALUES (?, ?, ?, ?, ?, datetime('now'))
    """, (usuario_id, aulas_semanais, turmas_quantidade, turmas_json, disciplinas_json))

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
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id
        FROM usuarios
        WHERE id = ? AND perfil = 'professor'
    """, (usuario_id,))
    if not cursor.fetchone():
        conn.close()
        return False

    turmas_json = _serializar_lista_texto(turmas)
    disciplinas_json = _serializar_lista_texto(disciplinas)

    cursor.execute("""
        UPDATE usuarios
        SET nome = ?, email = ?, cargo = ?, data_nascimento = ?
        WHERE id = ?
    """, (nome, email, CARGO_PROFESSOR, data_nascimento or None, usuario_id))

    cursor.execute("""
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
    """, (
        usuario_id,
        aulas_semanais,
        turmas_quantidade,
        turmas_json,
        disciplinas_json,
    ))

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

    cursor.execute("""
        INSERT INTO usuarios (nome, email, senha_hash, nt_hash, perfil, cargo, data_nascimento)
        VALUES (?, ?, ?, ?, 'coordenador', ?, ?)
    """, (nome, email, senha_hash, nt_hash_final, CARGO_COORDENADOR, data_nascimento or None))

    usuario_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return usuario_id

def listar_coordenadores_admin():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(f"""
        SELECT id, nome, email, data_nascimento
        FROM usuarios
        WHERE UPPER(COALESCE(cargo, '')) = ?
          AND {_clausula_usuario_ativo()}
        ORDER BY nome ASC
    """, (CARGO_COORDENADOR,))

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def atualizar_nt_hash_usuario(usuario_id: int, nt_hash: str):
    nt_hash_final = _normalizar_nt_hash(nt_hash)
    if not nt_hash_final:
        return False

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE usuarios
        SET nt_hash = ?
        WHERE id = ?
    """, (nt_hash_final, usuario_id))
    alterado = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return alterado

def preencher_nt_hash_se_ausente(usuario_id: int, senha_em_texto: str):
    nt_hash = generate_nt_hash(senha_em_texto)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE usuarios
        SET nt_hash = ?
        WHERE id = ?
          AND TRIM(COALESCE(nt_hash, '')) = ''
    """, (nt_hash, usuario_id))
    alterado = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return alterado

def atualizar_senha_usuario(usuario_id: int, senha_em_texto: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE usuarios
        SET senha_hash = ?, nt_hash = ?
        WHERE id = ?
    """, (
        hash_senha(senha_em_texto),
        generate_nt_hash(senha_em_texto),
        usuario_id
    ))
    alterado = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return alterado


def desativar_professor(usuario_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(f"""
        UPDATE usuarios
        SET ativo = 0
        WHERE id = ?
          AND perfil = 'professor'
          AND {_clausula_usuario_ativo()}
    """, (usuario_id,))
    alterado = cursor.rowcount > 0

    if alterado:
        cursor.execute("""
            DELETE FROM tokens
            WHERE usuario_id = ?
        """, (usuario_id,))

    conn.commit()
    conn.close()
    return alterado

def salvar_carga_professor(usuario_id: int, aulas_semanais: int, turmas_quantidade: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO professores_carga (usuario_id, aulas_semanais, turmas_quantidade, atualizado_em)
        VALUES (?, ?, ?, datetime('now'))
        ON CONFLICT(usuario_id) DO UPDATE SET
            aulas_semanais = excluded.aulas_semanais,
            turmas_quantidade = excluded.turmas_quantidade,
            atualizado_em = datetime('now')
    """, (usuario_id, aulas_semanais, turmas_quantidade))

    conn.commit()
    conn.close()

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

def atualizar_regras_cota(
    base_paginas: int,
    paginas_por_aula: int,
    paginas_por_turma: int,
    cota_mensal_escola: int,
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
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
    """, (base_paginas, paginas_por_aula, paginas_por_turma, cota_mensal_escola))

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
) -> float:
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
          AND {_clausula_usuario_ativo('u')}
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
        )

        calculos.append({
            "usuario_id": int(professor["id"]),
            "professor": professor["nome"],
            "peso_total_individual": peso_total_individual,
            "cota_mensal_calculada": 0,
        })
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
        int(calculo["usuario_id"]): int(calculo["cota_mensal_calculada"])
        for calculo in calculos
    }

def calcular_limite_cota_usuario(usuario_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT perfil
        FROM usuarios
        WHERE id = ?
    """, (usuario_id,))
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
            COALESCE(pc.aulas_semanais, 0) AS aulas_semanais,
            COALESCE(pc.turmas_quantidade, 0) AS turmas_quantidade,
            COALESCE(pc.turmas, '[]') AS turmas,
            COALESCE(pc.disciplinas, '[]') AS disciplinas
        FROM usuarios u
        LEFT JOIN professores_carga pc ON pc.usuario_id = u.id
        WHERE u.perfil = 'professor'
          AND {_clausula_usuario_ativo('u')}
        ORDER BY u.nome ASC
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    professores = [dict(row) for row in rows]

    for professor in professores:
        professor["turmas"] = _desserializar_lista_texto(professor.get("turmas"))
        professor["disciplinas"] = _desserializar_lista_texto(professor.get("disciplinas"))

    if mes:
        for professor in professores:
            cursor.execute("""
                SELECT limite_paginas, usadas_paginas
                FROM cotas
                WHERE usuario_id = ? AND mes = ?
            """, (professor["id"], mes))
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

    cursor.execute(f"""
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
    """, (CARGO_PROFESSOR,))

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

    cursor.execute(f"""
        SELECT
            usuario_id,
            COALESCE(turmas, '[]') AS turmas,
            COALESCE(disciplinas, '[]') AS disciplinas
        FROM professores_carga
        WHERE usuario_id IN ({placeholders})
    """, ids_unicos)

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

    cursor.execute(f"""
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
    """, (int(usuario_id), CARGO_PROFESSOR))

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

    cursor.execute("""
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
    """, (int(estudante_id),))

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

    cursor.execute("""
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
    """, (turma_id_valor, nome_limpo))

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
    cursor.execute("""
        INSERT INTO estudantes (nome, turma_id, ativo, criado_em, atualizado_em)
        VALUES (?, ?, ?, datetime('now'), datetime('now'))
    """, (nome_limpo, turma_id_valor, 1 if ativo else 0))

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
    cursor.execute("""
        UPDATE estudantes
        SET nome = ?, turma_id = ?, ativo = ?, atualizado_em = datetime('now')
        WHERE id = ?
    """, (nome_limpo, turma_id_valor, 1 if ativo else 0, int(estudante_id)))

    alterado = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return alterado

def atualizar_status_estudante(estudante_id: int, ativo: bool):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE estudantes
        SET ativo = ?, atualizado_em = datetime('now')
        WHERE id = ?
    """, (1 if ativo else 0, int(estudante_id)))

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

    cursor.execute("""
        UPDATE ocorrencias
        SET estudante_id = NULL, atualizado_em = datetime('now')
        WHERE estudante_id = ?
    """, (estudante_id_valor,))
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

    cursor.executemany("""
        INSERT OR IGNORE INTO recursos (nome, tipo, descricao, quantidade_itens, ativo)
        VALUES (?, ?, ?, ?, 1)
    """, recursos)

    conn.commit()
    conn.close()

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

    cursor.execute("""
        SELECT id, nome, turno, quantidade_estudantes, ativo, criado_em
        FROM turmas
        WHERE id = ?
    """, (int(turma_id),))

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

    cursor.execute("""
        INSERT INTO turmas (nome, turno, quantidade_estudantes, ativo, criado_em)
        VALUES (?, ?, ?, 1, datetime('now'))
    """, (nome_limpo, turno_limpo, quantidade_estudantes_valor))

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

    cursor.execute("""
        UPDATE turmas
        SET turno = ?, quantidade_estudantes = ?
        WHERE id = ?
    """, (turno_limpo, quantidade_estudantes_valor, turma_id))

    alterado = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return alterado

def atualizar_status_turma(turma_id: int, ativo: bool):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE turmas
        SET ativo = ?
        WHERE id = ?
    """, (1 if ativo else 0, turma_id))

    alterado = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return alterado

def listar_disciplinas(incluir_inativas: bool = False):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT id, nome, aulas_semanais, ativo, criado_em
        FROM disciplinas
    """
    params = []

    if not incluir_inativas:
        query += " WHERE ativo = 1"

    query += " ORDER BY nome COLLATE NOCASE ASC"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]

def listar_disciplinas_ativas():
    return listar_disciplinas(incluir_inativas=False)

def buscar_disciplina_por_id(disciplina_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, nome, aulas_semanais, ativo, criado_em
        FROM disciplinas
        WHERE id = ?
    """, (int(disciplina_id),))

    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def buscar_disciplina_por_nome(nome: str, incluir_inativas: bool = True):
    nome_limpo = _normalizar_nome_catalogo(nome)
    if not nome_limpo:
        return None

    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT id, nome, aulas_semanais, ativo, criado_em
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
    return dict(row) if row else None

def criar_disciplina(nome: str, aulas_semanais: int = 0):
    nome_limpo = _normalizar_nome_catalogo(nome)
    if not nome_limpo:
        raise ValueError("Nome da disciplina é obrigatório.")
    aulas_semanais_valor = int(aulas_semanais or 0)
    if aulas_semanais_valor < 0:
        raise ValueError("Aulas semanais não pode ser negativo.")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO disciplinas (nome, aulas_semanais, ativo, criado_em)
        VALUES (?, ?, 1, datetime('now'))
    """, (nome_limpo, aulas_semanais_valor))

    disciplina_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return disciplina_id

def atualizar_disciplina_dados(disciplina_id: int, aulas_semanais: int):
    aulas_semanais_valor = int(aulas_semanais or 0)
    if aulas_semanais_valor < 0:
        raise ValueError("Aulas semanais não pode ser negativo.")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE disciplinas
        SET aulas_semanais = ?
        WHERE id = ?
    """, (aulas_semanais_valor, disciplina_id))

    alterado = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return alterado

def atualizar_status_disciplina(disciplina_id: int, ativo: bool):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE disciplinas
        SET ativo = ?
        WHERE id = ?
    """, (1 if ativo else 0, disciplina_id))

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

    cursor.execute(
        "SELECT * FROM jobs WHERE id = ?",
        (job_id,)
    )

    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None

def cancelar_job(job_id, estornar_cota: bool = True):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT usuario_id, paginas_totais, criado_em
        FROM jobs
        WHERE id = ?
    """, (job_id,))
    job = cursor.fetchone()

    if not job:
        conn.close()
        return {
            "encontrado": False,
            "cancelado": False,
            "paginas_estornadas": 0,
        }

    cursor.execute("""
        UPDATE jobs
        SET status = 'CANCELADO'
        WHERE id = ? AND status = 'PENDENTE'
    """, (job_id,))
    cancelado = cursor.rowcount > 0

    paginas_estornadas = 0
    if cancelado and estornar_cota:
        usuario_id_raw = job["usuario_id"]
        usuario_id = int(usuario_id_raw) if usuario_id_raw is not None else None
        paginas = max(int(job["paginas_totais"] or 0), 0)
        mes_referencia = str(job["criado_em"] or "")[:7]

        if paginas > 0 and usuario_id is not None and len(mes_referencia) == 7:
            cursor.execute("""
                UPDATE cotas
                SET usadas_paginas = MAX(usadas_paginas - ?, 0)
                WHERE usuario_id = ? AND mes = ?
            """, (paginas, usuario_id, mes_referencia))
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

    cursor.execute("""
        UPDATE jobs
        SET prioridade = ?
        WHERE id = ? AND status = 'PENDENTE'
    """, (prioridade, job_id))

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
        cursor.execute("""
            SELECT * FROM jobs
            WHERE status = 'PENDENTE'
              AND datetime(criado_em) <= datetime('now', ?)
            ORDER BY prioridade DESC, criado_em ASC
            LIMIT 1
        """, (f"-{atraso_minimo} seconds",))
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
        cursor.execute("""
            UPDATE jobs
            SET status = ?, finalizado_em = datetime('now'), erro_mensagem = NULL
            WHERE id = ?
        """, (status, job_id))
    elif status == "ERRO":
        cursor.execute("""
            UPDATE jobs
            SET status = ?
            WHERE id = ?
        """, (status, job_id))
    else:
        cursor.execute("""
            UPDATE jobs
            SET status = ?, erro_mensagem = NULL
            WHERE id = ?
        """, (status, job_id))

    conn.commit()
    conn.close()

def atualizar_job_cups(job_id, cups_job_id, printer_name):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE jobs
        SET cups_job_id = ?, printer_name = ?
        WHERE id = ?
    """, (cups_job_id, printer_name or None, job_id))

    conn.commit()
    conn.close()

def atualizar_erro_job(job_id, erro_mensagem: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE jobs
        SET erro_mensagem = ?
        WHERE id = ?
    """, (str(erro_mensagem)[:1000], job_id))

    conn.commit()
    conn.close()

def buscar_cota(usuario_id: int, mes: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM cotas
        WHERE usuario_id = ? AND mes = ?
    """, (usuario_id, mes))

    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def criar_cota(usuario_id: int, mes: str, limite: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO cotas (usuario_id, mes, limite_paginas, usadas_paginas)
        VALUES (?, ?, ?, 0)
    """, (usuario_id, mes, limite))

    conn.commit()
    conn.close()

def consumir_cota(cota_id: int, paginas: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE cotas
        SET usadas_paginas = usadas_paginas + ?
        WHERE id = ?
    """, (paginas, cota_id))

    conn.commit()
    conn.close()

def buscar_cota_do_usuario(usuario_id: int, mes: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT limite_paginas, usadas_paginas
        FROM cotas
        WHERE usuario_id = ? AND mes = ?
    """, (usuario_id, mes))

    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None

def atualizar_limite_cota_mes(usuario_id: int, mes: str, limite_paginas: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, usadas_paginas
        FROM cotas
        WHERE usuario_id = ? AND mes = ?
    """, (usuario_id, mes))
    row = cursor.fetchone()

    if row:
        usadas = int(row["usadas_paginas"])
        limite_final = max(int(limite_paginas), usadas)
        cursor.execute("""
            UPDATE cotas
            SET limite_paginas = ?
            WHERE id = ?
        """, (limite_final, row["id"]))
    else:
        limite_final = max(int(limite_paginas), 0)
        cursor.execute("""
            INSERT INTO cotas (usuario_id, mes, limite_paginas, usadas_paginas)
            VALUES (?, ?, ?, 0)
        """, (usuario_id, mes, limite_final))

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

    cursor.execute("""
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
    """, (STATUS_CONCLUIDO, STATUS_FINALIZADO_LEGADO))

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

    cursor.execute("""
        INSERT INTO recursos (nome, tipo, descricao, quantidade_itens, ativo)
        VALUES (?, ?, ?, ?, 1)
    """, (nome, tipo, descricao, quantidade_itens_valor))

    recurso_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return recurso_id

def atualizar_recurso_dados(
    recurso_id: int,
    nome: str,
    tipo: str,
    descricao: str = "",
    quantidade_itens: int = 1
):
    quantidade_itens_valor = max(int(quantidade_itens or 0), 1)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE recursos
        SET nome = ?, tipo = ?, descricao = ?, quantidade_itens = ?
        WHERE id = ?
    """, (nome, tipo, descricao, quantidade_itens_valor, recurso_id))

    alterados = cursor.rowcount
    conn.commit()
    conn.close()
    return alterados > 0

def atualizar_recurso_quantidade_itens(recurso_id: int, quantidade_itens: int):
    quantidade_itens_valor = max(int(quantidade_itens or 0), 1)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE recursos
        SET quantidade_itens = ?
        WHERE id = ?
    """, (quantidade_itens_valor, recurso_id))

    alterados = cursor.rowcount
    conn.commit()
    conn.close()
    return alterados > 0

def atualizar_status_recurso(recurso_id: int, ativo: bool):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE recursos
        SET ativo = ?
        WHERE id = ?
    """, (1 if ativo else 0, recurso_id))

    alterados = cursor.rowcount
    conn.commit()
    conn.close()
    return alterados > 0

def buscar_recurso_por_id(recurso_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            nome,
            tipo,
            COALESCE(descricao, '') AS descricao,
            CASE WHEN COALESCE(quantidade_itens, 1) < 1 THEN 1 ELSE quantidade_itens END AS quantidade_itens,
            ativo
        FROM recursos
        WHERE id = ?
    """, (recurso_id,))

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
    cursor.execute("""
        SELECT id, nome
        FROM leis
        WHERE id = ?
    """, (lei_id_valor,))
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
    cursor.execute("""
        SELECT
            a.id,
            a.lei_id,
            l.nome AS lei_nome,
            a.numero,
            a.descricao
        FROM artigos a
        INNER JOIN leis l ON l.id = a.lei_id
        WHERE a.id = ?
    """, (artigo_id_valor,))
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
        cursor.execute("""
            INSERT INTO artigos (lei_id, numero, descricao)
            VALUES (?, ?, ?)
        """, (lei_id_valor, numero_limpo, descricao_limpa))
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
        cursor.execute("""
            UPDATE artigos
            SET lei_id = ?, numero = ?, descricao = ?
            WHERE id = ?
        """, (lei_id_valor, numero_limpo, descricao_limpa, artigo_id_valor))
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
    cursor.execute("""
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
    """, (inciso_id_valor,))
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
        cursor.execute("""
            INSERT INTO incisos (artigo_id, numero, descricao)
            VALUES (?, ?, ?)
        """, (artigo_id_valor, numero_limpo, descricao_limpa))
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
        cursor.execute("""
            UPDATE incisos
            SET artigo_id = ?, numero = ?, descricao = ?
            WHERE id = ?
        """, (artigo_id_valor, numero_limpo, descricao_limpa, inciso_id_valor))
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
    cursor.execute("""
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
    """, (alinea_id_valor,))
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
        cursor.execute("""
            INSERT INTO alineas (inciso_id, identificador, descricao)
            VALUES (?, ?, ?)
        """, (inciso_id_valor, identificador_limpo, descricao_limpa))
    except sqlite3.IntegrityError as exc:
        conn.close()
        raise ValueError("Ja existe uma alinea com este identificador para o inciso informado.") from exc
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
        cursor.execute("""
            UPDATE alineas
            SET inciso_id = ?, identificador = ?, descricao = ?
            WHERE id = ?
        """, (inciso_id_valor, identificador_limpo, descricao_limpa, alinea_id_valor))
    except sqlite3.IntegrityError as exc:
        conn.close()
        raise ValueError("Ja existe uma alinea com este identificador para o inciso informado.") from exc
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
    if _contar_relacoes_base_legal(cursor, "ocorrencia_regimento_itens", "artigo_id", artigo_id_valor) > 0:
        conn.close()
        raise ValueError("Nao e possivel excluir o artigo porque ele ja foi vinculado a ocorrencias.")

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
    if _contar_relacoes_base_legal(cursor, "ocorrencia_regimento_itens", "inciso_id", inciso_id_valor) > 0:
        conn.close()
        raise ValueError("Nao e possivel excluir o inciso porque ele ja foi vinculado a ocorrencias.")

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

    if _contar_relacoes_base_legal(cursor, "ocorrencia_regimento_itens", "alinea_id", alinea_id_valor) > 0:
        conn.close()
        raise ValueError("Nao e possivel excluir a alinea porque ela ja foi vinculada a ocorrencias.")

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
    cursor.execute("""
        SELECT
            a.id AS artigo_id
        FROM artigos a
        WHERE a.numero = ? COLLATE NOCASE
        ORDER BY a.id ASC
        LIMIT 1
    """, (artigo_limpo,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return buscar_regimento_item_por_id(_codificar_regimento_item_id(TIPO_BASE_LEGAL_ARTIGO, int(row["artigo_id"])))


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
        cursor.execute("""
            UPDATE artigos
            SET numero = ?, descricao = ?
            WHERE id = ?
        """, (
            dados["artigo_numero"],
            dados["artigo_descricao"],
            int(atual.get("artigo_id") or 0),
        ))

        if atual.get("tipo") in {TIPO_BASE_LEGAL_INCISO, TIPO_BASE_LEGAL_ALINEA}:
            cursor.execute("""
                UPDATE incisos
                SET numero = ?, descricao = ?
                WHERE id = ?
            """, (
                dados["inciso_numero"],
                dados["inciso_descricao"],
                int(atual.get("inciso_id") or 0),
            ))

        if atual.get("tipo") == TIPO_BASE_LEGAL_ALINEA:
            cursor.execute("""
                UPDATE alineas
                SET identificador = ?, descricao = ?
                WHERE id = ?
            """, (
                dados["alinea_identificador"],
                dados["alinea_descricao"],
                int(atual.get("alinea_id") or 0),
            ))
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
        regimento_item_id for regimento_item_id in ids_norm
        if regimento_item_id not in itens
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

        cursor.executemany("""
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
        """, [
            (
                ocorrencia_id_valor,
                regimento_item_id,
                int(itens[regimento_item_id]["artigo_id"]) if itens[regimento_item_id].get("artigo_id") is not None else None,
                int(itens[regimento_item_id]["inciso_id"]) if itens[regimento_item_id].get("inciso_id") is not None else None,
                int(itens[regimento_item_id]["alinea_id"]) if itens[regimento_item_id].get("alinea_id") is not None else None,
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
        ])


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

def criar_ocorrencia(
    nome_estudante: str,
    estudante_id: int | None,
    turma_id: int,
    professor_requerente: str,
    professor_requerente_id: int | None,
    disciplina: str,
    data_ocorrencia: str,
    aula: str,
    horario_ocorrencia: str,
    descricao: str,
    acao_aplicada: str,
    status: str = STATUS_OCORRENCIA_REGISTRADO,
    regimento_item_ids: list[int] | None = None,
):
    nome_estudante_limpo = _normalizar_nome_catalogo(nome_estudante)
    professor_requerente_limpo = _normalizar_nome_catalogo(professor_requerente)
    disciplina_limpa = _normalizar_nome_catalogo(disciplina)
    data_ocorrencia_limpa = _normalizar_nome_catalogo(data_ocorrencia)
    aula_limpa = _normalizar_nome_catalogo(aula)
    horario_ocorrencia_limpo = _normalizar_nome_catalogo(horario_ocorrencia)
    descricao_limpa = str(descricao or "").strip()
    acao_aplicada_limpa = _normalizar_nome_catalogo(acao_aplicada)
    status_limpo = _normalizar_nome_catalogo(status) or STATUS_OCORRENCIA_REGISTRADO
    turma_id_valor = int(turma_id or 0)
    estudante_id_valor = int(estudante_id) if estudante_id is not None else None
    professor_requerente_id_valor = (
        int(professor_requerente_id) if professor_requerente_id is not None else None
    )

    if turma_id_valor <= 0:
        raise ValueError("Turma inválida.")
    if estudante_id_valor is not None and estudante_id_valor <= 0:
        raise ValueError("Estudante inválido.")
    if professor_requerente_id_valor is not None and professor_requerente_id_valor <= 0:
        raise ValueError("Professor requerente inválido.")
    if not nome_estudante_limpo:
        raise ValueError("Nome do estudante é obrigatório.")
    if not professor_requerente_limpo:
        raise ValueError("Professor requerente é obrigatório.")
    if not disciplina_limpa:
        raise ValueError("Disciplina é obrigatória.")
    if not data_ocorrencia_limpa:
        raise ValueError("Data da ocorrência é obrigatória.")
    if not aula_limpa:
        raise ValueError("Aula é obrigatória.")
    if not horario_ocorrencia_limpo:
        raise ValueError("Horário da ocorrência é obrigatório.")
    if not descricao_limpa:
        raise ValueError("Descrição é obrigatória.")
    if acao_aplicada_limpa not in ACAO_OCORRENCIA_VALIDAS:
        raise ValueError("Ação aplicada inválida.")
    if status_limpo not in STATUS_OCORRENCIA_VALIDOS:
        raise ValueError("Status inválido.")

    ids_regimento_norm = None
    itens_regimento_snapshot = None
    if regimento_item_ids is not None:
        ids_regimento_norm = _normalizar_regimento_item_ids_banco(regimento_item_ids)
        if ids_regimento_norm:
            itens_regimento_snapshot = _mapear_regimento_itens_por_ids_para_snapshot(ids_regimento_norm)

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO ocorrencias (
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
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        """, (
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
        ))

        ocorrencia_id = cursor.lastrowid
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
    conn.close()
    return ocorrencias

def buscar_ocorrencia_por_id(ocorrencia_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            o.id,
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
    """, (int(ocorrencia_id),))

    row = cursor.fetchone()
    ocorrencia = dict(row) if row else None
    if ocorrencia:
        _anexar_regimento_itens_ocorrencias(cursor, [ocorrencia])
    conn.close()
    return ocorrencia

def atualizar_ocorrencia(ocorrencia_id: int, dados: dict):
    campos_permitidos = {
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

        if campo == "turma_id":
            valor_turma = int(valor or 0)
            if valor_turma <= 0:
                raise ValueError("Turma inválida.")
            atualizacoes.append("turma_id = ?")
            parametros.append(valor_turma)
            continue

        if campo == "estudante_id":
            valor_estudante = int(valor) if valor is not None else None
            if valor_estudante is not None and valor_estudante <= 0:
                raise ValueError("Estudante inválido.")
            atualizacoes.append("estudante_id = ?")
            parametros.append(valor_estudante)
            continue

        if campo == "professor_requerente_id":
            valor_professor = int(valor) if valor is not None else None
            if valor_professor is not None and valor_professor <= 0:
                raise ValueError("Professor requerente inválido.")
            atualizacoes.append("professor_requerente_id = ?")
            parametros.append(valor_professor)
            continue

        if campo == "acao_aplicada":
            valor_acao = _normalizar_nome_catalogo(valor)
            if valor_acao not in ACAO_OCORRENCIA_VALIDAS:
                raise ValueError("Ação aplicada inválida.")
            atualizacoes.append("acao_aplicada = ?")
            parametros.append(valor_acao)
            continue

        if campo == "status":
            valor_status = _normalizar_nome_catalogo(valor)
            if valor_status not in STATUS_OCORRENCIA_VALIDOS:
                raise ValueError("Status inválido.")
            atualizacoes.append("status = ?")
            parametros.append(valor_status)
            continue

        if campo == "descricao":
            valor_descricao = str(valor or "").strip()
            if not valor_descricao:
                raise ValueError("Descrição é obrigatória.")
            atualizacoes.append("descricao = ?")
            parametros.append(valor_descricao)
            continue

        valor_texto = _normalizar_nome_catalogo(valor)
        if not valor_texto:
            raise ValueError("Campos obrigatórios não podem ficar vazios.")
        atualizacoes.append(f"{campo} = ?")
        parametros.append(valor_texto)

    if not atualizacoes:
        return False

    atualizacoes.append("atualizado_em = datetime('now')")
    parametros.append(int(ocorrencia_id))

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"""
        UPDATE ocorrencias
        SET {", ".join(atualizacoes)}
        WHERE id = ?
    """, parametros)

    alterado = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return alterado

def remover_ocorrencia(ocorrencia_id: int):
    conn = get_connection()
    cursor = conn.cursor()
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

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM agendamentos
        WHERE recurso_id = ?
          AND data = ?
          AND faixa_global = ?
          AND status = ?
    """, (recurso_id, data, int(faixa_global), STATUS_AGENDAMENTO_ATIVO))

    row = cursor.fetchone()
    conn.close()
    return int(row["total"] if row else 0)

def buscar_agendamento_conflito(recurso_id: int, data: str, faixa_global: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id
        FROM agendamentos
        WHERE recurso_id = ?
          AND data = ?
          AND faixa_global = ?
          AND status = ?
        LIMIT 1
    """, (recurso_id, data, int(faixa_global), STATUS_AGENDAMENTO_ATIVO))

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

    cursor.execute("""
        INSERT INTO agendamentos (
            recurso_id, usuario_id, data, turno, aula, faixa_global, turma, tema_aula, observacao, status, criado_em
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
    """, (
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
    ))

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

    cursor.execute("""
        SELECT *
        FROM agendamentos
        WHERE id = ?
    """, (agendamento_id,))

    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def cancelar_agendamento(agendamento_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE agendamentos
        SET status = ?, cancelado_em = datetime('now')
        WHERE id = ?
          AND status = ?
    """, (
        STATUS_AGENDAMENTO_CANCELADO,
        agendamento_id,
        STATUS_AGENDAMENTO_ATIVO,
    ))

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
    professor_nome: str = "",
    componente: str = "",
    turma: str = "",
    observacoes: str = "",
    criado_por_usuario_id: int | None = None,
    atualizado_por_usuario_id: int | None = None,
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO pcpi_registros_manuais (
            data,
            turno,
            tipo_acao,
            professor_nome,
            componente,
            turma,
            descricao_curta,
            observacoes,
            criado_por_usuario_id,
            atualizado_por_usuario_id,
            criado_em,
            atualizado_em
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
    """, (
        data,
        turno,
        tipo_acao,
        professor_nome or None,
        componente or None,
        turma or None,
        descricao_curta,
        observacoes or None,
        criado_por_usuario_id,
        atualizado_por_usuario_id,
    ))

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
            COALESCE(professor_nome, '') AS professor_nome,
            COALESCE(componente, '') AS componente,
            COALESCE(turma, '') AS turma,
            descricao_curta,
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

    cursor.execute("""
        SELECT
            id,
            data,
            turno,
            tipo_acao,
            COALESCE(professor_nome, '') AS professor_nome,
            COALESCE(componente, '') AS componente,
            COALESCE(turma, '') AS turma,
            descricao_curta,
            COALESCE(observacoes, '') AS observacoes,
            criado_por_usuario_id,
            atualizado_por_usuario_id,
            criado_em,
            atualizado_em
        FROM pcpi_registros_manuais
        WHERE id = ?
    """, (int(registro_id),))

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
        WHERE id = ?
    """, (int(periodo_id),))

    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def buscar_periodo_pre_conselho_por_ano_etapa(ano_letivo: int, etapa: int):
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
        WHERE ano_letivo = ?
          AND etapa = ?
        LIMIT 1
    """, (int(ano_letivo), int(etapa)))

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

    cursor.execute("""
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
    """, (
        nome_final,
        int(ano_letivo),
        int(etapa),
        data_inicio,
        data_fim,
        status,
    ))

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

    cursor.execute("""
        UPDATE pre_conselho_periodos
        SET nome = ?,
            ano_letivo = ?,
            etapa = ?,
            data_inicio = ?,
            data_fim = ?,
            atualizado_em = datetime('now')
        WHERE id = ?
    """, (
        nome_final,
        int(ano_letivo),
        int(etapa),
        data_inicio,
        data_fim,
        int(periodo_id),
    ))

    alterado = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return alterado


def atualizar_status_periodo_pre_conselho(periodo_id: int, status: str):
    conn = get_connection()
    cursor = conn.cursor()

    if status == STATUS_PERIODO_PRE_CONSELHO_ABERTO:
        cursor.execute("""
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
        """, (int(periodo_id), int(periodo_id)))

    cursor.execute("""
        UPDATE pre_conselho_periodos
        SET status = ?,
            atualizado_em = datetime('now')
        WHERE id = ?
    """, (status, int(periodo_id)))

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

    cursor.execute("""
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
    """, (int(motivo_id),))

    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def buscar_motivo_pre_conselho_por_codigo(codigo: str):
    codigo_limpo = _normalizar_nome_catalogo(codigo)
    if not codigo_limpo:
        return None

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
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
    """, (codigo_limpo,))

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

    cursor.execute(f"""
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
    """, ids_validos)

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

    cursor.execute("""
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
    """, (
        categoria,
        codigo,
        descricao,
        int(ordem or 0),
    ))

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

    cursor.execute("""
        UPDATE pre_conselho_motivos
        SET categoria = ?,
            descricao = ?,
            ordem = ?,
            atualizado_em = datetime('now')
        WHERE id = ?
    """, (
        categoria,
        descricao,
        int(ordem or 0),
        int(motivo_id),
    ))

    alterado = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return alterado


def atualizar_status_motivo_pre_conselho(motivo_id: int, ativo: bool):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE pre_conselho_motivos
        SET ativo = ?,
            atualizado_em = datetime('now')
        WHERE id = ?
    """, (1 if ativo else 0, int(motivo_id)))

    alterado = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return alterado


def contar_registros_pre_conselho_por_professor_periodo(periodo_id: int, professor_usuario_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            turma_id,
            disciplina_id,
            COUNT(*) AS total
        FROM pre_conselho_registros
        WHERE periodo_id = ?
          AND professor_usuario_id = ?
        GROUP BY turma_id, disciplina_id
    """, (int(periodo_id), int(professor_usuario_id)))

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
    cursor.execute("""
        SELECT id
        FROM pre_conselho_registros
        WHERE periodo_id = ?
          AND turma_id = ?
          AND disciplina_id = ?
          AND professor_usuario_id = ?
          AND estudante_id = ?
        LIMIT 1
    """, (
        int(periodo_id),
        int(turma_id),
        int(disciplina_id),
        int(professor_usuario_id),
        int(estudante_id),
    ))
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

    cursor.execute("""
        DELETE FROM pre_conselho_registro_motivos
        WHERE registro_id = ?
    """, (int(registro_id),))

    for motivo_id in ids_validos:
        cursor.execute("""
            INSERT OR IGNORE INTO pre_conselho_registro_motivos (
                registro_id,
                motivo_id,
                criado_em
            )
            VALUES (?, ?, datetime('now'))
        """, (int(registro_id), motivo_id))


def _carregar_motivos_pre_conselho_por_registro_ids(cursor, registro_ids: list[int]) -> dict[int, list[dict]]:
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
    cursor.execute(f"""
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
    """, ids_validos)

    mapa = {registro_id: [] for registro_id in ids_validos}
    for row in cursor.fetchall():
        item = dict(row)
        registro_id = int(item.pop("registro_id"))
        mapa.setdefault(registro_id, []).append(item)
    return mapa


def _normalizar_linha_registro_pre_conselho(item: dict, motivos_map: dict[int, list[dict]] | None = None) -> dict:
    registro_id = int(item["id"])
    motivos = list(motivos_map.get(registro_id, [])) if motivos_map else []
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
        cursor.execute("""
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
                texto_gerado = ?,
                atualizado_em = datetime('now')
            WHERE id = ?
        """, (
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
            texto_gerado_limpo,
            int(registro_id),
        ))
    else:
        cursor.execute("""
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
                texto_gerado,
                criado_em,
                atualizado_em
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        """, (
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
            texto_gerado_limpo,
        ))
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
    itens = [
        _normalizar_linha_registro_pre_conselho(dict(row), motivos_map)
        for row in rows
    ]
    conn.close()
    return itens


def buscar_registro_pre_conselho_por_id(registro_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
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
    """, (int(registro_id),))

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
