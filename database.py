import sqlite3
import uuid
import hashlib
import json
import os
import shutil
from pathlib import Path

STATUS_CONCLUIDO = "CONCLUIDO"
STATUS_FINALIZADO_LEGADO = "FINALIZADO"
STATUS_AGENDAMENTO_ATIVO = "ATIVO"
STATUS_AGENDAMENTO_CANCELADO = "CANCELADO"
COTA_BASE_PADRAO = 80
COTA_POR_AULA_PADRAO = 6
COTA_POR_TURMA_PADRAO = 12
COTA_MENSAL_ESCOLA_PADRAO = 4000
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
            perfil TEXT NOT NULL,
            data_nascimento TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tokens (
            token TEXT PRIMARY KEY,
            usuario_id INTEGER NOT NULL
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
        CREATE TABLE IF NOT EXISTS agendamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recurso_id INTEGER NOT NULL,
            usuario_id INTEGER NOT NULL,
            data TEXT NOT NULL,
            turno TEXT NOT NULL DEFAULT 'MATUTINO',
            aula TEXT NOT NULL,
            turma TEXT NOT NULL DEFAULT '',
            observacao TEXT,
            status TEXT NOT NULL DEFAULT 'ATIVO',
            criado_em TEXT NOT NULL,
            cancelado_em TEXT,
            FOREIGN KEY(recurso_id) REFERENCES recursos(id),
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
        )
    """)

    _garantir_colunas_usuarios(cursor)
    _garantir_colunas_jobs(cursor)
    _garantir_colunas_agendamentos(cursor)
    _garantir_colunas_professores_carga(cursor)
    _garantir_colunas_cota_regras(cursor)
    _garantir_colunas_turmas(cursor)
    _garantir_colunas_disciplinas(cursor)
    _seed_catalogos_academicos(cursor)
    _migrar_catalogos_academicos(cursor)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_jobs_status_prioridade_criado_em
        ON jobs(status, prioridade, criado_em)
    """)

    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_cotas_usuario_mes
        ON cotas(usuario_id, mes)
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
        CREATE INDEX IF NOT EXISTS idx_agendamentos_usuario_data
        ON agendamentos(usuario_id, data)
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

def _garantir_colunas_usuarios(cursor):
    cursor.execute("PRAGMA table_info(usuarios)")
    colunas = {row["name"] for row in cursor.fetchall()}

    if "data_nascimento" not in colunas:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN data_nascimento TEXT")


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

def salvar_token(token: str, usuario_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO tokens (token, usuario_id)
        VALUES (?, ?)
    """, (token, usuario_id))

    conn.commit()
    conn.close()

def buscar_usuario_por_token(token: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT u.id, u.nome, u.email, u.perfil
        FROM usuarios u
        JOIN tokens t ON u.id = t.usuario_id
        WHERE t.token = ?
    """, (token,))

    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None

#hash para senhas
def hash_senha(senha: str):
    return hashlib.sha256(senha.encode()).hexdigest()

def criar_usuario(nome, email, senha, perfil):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO usuarios (nome, email, senha_hash, perfil)
        VALUES (?, ?, ?, ?)
    """, (
        nome,
        email,
        hash_senha(senha),
        perfil
    ))

    conn.commit()
    conn.close()

def buscar_usuario_por_email(email):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM usuarios WHERE email = ?",
        (email,)
    )

    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None

def buscar_usuario_por_id(usuario_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, nome, email, perfil, data_nascimento
        FROM usuarios
        WHERE id = ?
    """, (usuario_id,))

    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None

def criar_usuario_se_nao_existir(nome, email, senha_hash, perfil):
    usuario = buscar_usuario_por_email(email)
    if usuario:
        return

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO usuarios (nome, email, senha_hash, perfil)
        VALUES (?, ?, ?, ?)
    """, (nome, email, senha_hash, perfil))

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

def criar_professor(
    nome: str,
    email: str,
    senha_hash: str,
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

    cursor.execute("""
        INSERT INTO usuarios (nome, email, senha_hash, perfil, data_nascimento)
        VALUES (?, ?, ?, 'professor', ?)
    """, (nome, email, senha_hash, data_nascimento or None))

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

def _calcular_peso_professor(
    regras: dict,
    aulas_semanais: int,
    turmas_quantidade: int,
):
    peso = (
        int(regras["base_paginas"])
        + int(aulas_semanais) * int(regras["paginas_por_aula"])
        + int(turmas_quantidade) * int(regras["paginas_por_turma"])
    )
    return max(peso, 0)

def calcular_limites_cota_professores():
    regras = obter_regras_cota()
    cota_total = max(int(regras["cota_mensal_escola"]), 0)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            u.id,
            COALESCE(pc.aulas_semanais, 0) AS aulas_semanais,
            COALESCE(pc.turmas_quantidade, 0) AS turmas_quantidade
        FROM usuarios u
        LEFT JOIN professores_carga pc ON pc.usuario_id = u.id
        WHERE u.perfil = 'professor'
        ORDER BY u.id ASC
    """)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return {}

    pesos = {}
    total_pesos = 0
    for row in rows:
        peso = _calcular_peso_professor(
            regras=regras,
            aulas_semanais=row["aulas_semanais"],
            turmas_quantidade=row["turmas_quantidade"]
        )
        pesos[int(row["id"])] = peso
        total_pesos += peso

    limites = {}

    if total_pesos <= 0:
        limite_base = cota_total // len(rows)
        sobra = cota_total % len(rows)
        for indice, row in enumerate(rows):
            limites[int(row["id"])] = limite_base + (1 if indice < sobra else 0)
        return limites

    distribuicao = []
    acumulado = 0
    for row in rows:
        usuario_id = int(row["id"])
        quota_bruta = cota_total * pesos[usuario_id] / total_pesos
        quota_inteira = int(quota_bruta)
        limites[usuario_id] = quota_inteira
        acumulado += quota_inteira
        distribuicao.append((quota_bruta - quota_inteira, usuario_id))

    sobra = cota_total - acumulado
    if sobra > 0:
        distribuicao.sort(key=lambda item: (-item[0], item[1]))
        for indice in range(sobra):
            usuario_id = distribuicao[indice % len(distribuicao)][1]
            limites[usuario_id] += 1

    return limites

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

    query = """
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

def seed_recursos_padrao():
    recursos = [
        ("Notebook Carrinho 1", "Notebook", "Carrinho móvel com 30 notebooks."),
        ("Projetor Sala Multiuso", "Projetor", "Projetor Epson da sala multiuso."),
        ("Laboratório Maker", "Laboratório", "Laboratório com kits de robótica."),
        ("Kit Tablets", "Tablet", "Conjunto de 25 tablets para aula interativa."),
        ("Caixa de Som Bluetooth", "Áudio", "Caixa de som portátil para apresentações."),
    ]

    conn = get_connection()
    cursor = conn.cursor()

    cursor.executemany("""
        INSERT OR IGNORE INTO recursos (nome, tipo, descricao, ativo)
        VALUES (?, ?, ?, 1)
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

def cancelar_job(job_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE jobs
        SET status = 'CANCELADO'
        WHERE id = ? AND status = 'PENDENTE'
    """, (job_id,))

    conn.commit()
    conn.close()

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

#para imprimir automáticamente, o sistema pode buscar o próximo job pendente
def buscar_proximo_job():
    conn = get_connection()
    cursor = conn.cursor()

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
        SELECT id, nome, tipo, COALESCE(descricao, '') AS descricao, ativo
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

def criar_recurso(nome: str, tipo: str, descricao: str = ""):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO recursos (nome, tipo, descricao, ativo)
        VALUES (?, ?, ?, 1)
    """, (nome, tipo, descricao))

    recurso_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return recurso_id

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
        SELECT id, nome, tipo, COALESCE(descricao, '') AS descricao, ativo
        FROM recursos
        WHERE id = ?
    """, (recurso_id,))

    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def buscar_agendamento_conflito(recurso_id: int, data: str, turno: str, aula: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id
        FROM agendamentos
        WHERE recurso_id = ?
          AND data = ?
          AND turno = ?
          AND aula = ?
          AND status = ?
        LIMIT 1
    """, (recurso_id, data, turno, aula, STATUS_AGENDAMENTO_ATIVO))

    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def criar_agendamento(
    recurso_id: int,
    usuario_id: int,
    data: str,
    turno: str,
    aula: str,
    turma: str,
    observacao: str = "",
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO agendamentos (
            recurso_id, usuario_id, data, turno, aula, turma, observacao, status, criado_em
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
    """, (
        recurso_id,
        usuario_id,
        data,
        turno,
        aula,
        turma,
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
            a.turma,
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
            CASE a.turno
                WHEN 'MATUTINO' THEN 1
                WHEN 'VESPERTINO' THEN 2
                WHEN 'VESPERTINO_EM' THEN 3
                WHEN 'INTEGRAL' THEN 4
                ELSE 5
            END ASC,
            CAST(a.aula AS INTEGER) ASC,
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
