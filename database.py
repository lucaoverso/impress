import sqlite3
import uuid
import hashlib

STATUS_CONCLUIDO = "CONCLUIDO"
STATUS_FINALIZADO_LEGADO = "FINALIZADO"
STATUS_AGENDAMENTO_ATIVO = "ATIVO"
STATUS_AGENDAMENTO_CANCELADO = "CANCELADO"
COTA_BASE_PADRAO = 80
COTA_POR_AULA_PADRAO = 6
COTA_POR_TURMA_PADRAO = 12

DB_NAME = "impressao.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def criar_job(
    usuario_id: int,
    arquivo: str,
    copias: int,
    paginas_totais: int,
    paginas_por_folha: int = 1,
    duplex: bool = False,
    orientacao: str = "retrato",
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO jobs (
            usuario_id, arquivo, copias, paginas_por_folha, duplex, orientacao,
            paginas_totais, status, prioridade, criado_em
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDENTE', 0, datetime('now'))
    """, (
        usuario_id,
        arquivo,
        copias,
        paginas_por_folha,
        int(bool(duplex)),
        orientacao,
        paginas_totais,
    ))

    conn.commit()
    conn.close()

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
            perfil TEXT NOT NULL
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
            copias INTEGER NOT NULL,
            paginas_por_folha INTEGER NOT NULL DEFAULT 1,
            duplex INTEGER NOT NULL DEFAULT 0,
            orientacao TEXT NOT NULL DEFAULT 'retrato',
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

    _garantir_colunas_jobs(cursor)
    _garantir_colunas_agendamentos(cursor)
    _garantir_colunas_professores_carga(cursor)

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
            id, base_paginas, paginas_por_aula, paginas_por_turma, atualizado_em
        )
        VALUES (1, ?, ?, ?, datetime('now'))
    """, (
        COTA_BASE_PADRAO,
        COTA_POR_AULA_PADRAO,
        COTA_POR_TURMA_PADRAO,
    ))

    conn.commit()
    conn.close()

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
        SELECT id, nome, email, perfil
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

def criar_professor(
    nome: str,
    email: str,
    senha_hash: str,
    aulas_semanais: int = 0,
    turmas_quantidade: int = 0,
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO usuarios (nome, email, senha_hash, perfil)
        VALUES (?, ?, ?, 'professor')
    """, (nome, email, senha_hash))

    usuario_id = cursor.lastrowid
    cursor.execute("""
        INSERT INTO professores_carga (usuario_id, aulas_semanais, turmas_quantidade, atualizado_em)
        VALUES (?, ?, ?, datetime('now'))
    """, (usuario_id, aulas_semanais, turmas_quantidade))

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
        SELECT base_paginas, paginas_por_aula, paginas_por_turma, atualizado_em
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
            "atualizado_em": None,
        }
    return dict(row)

def atualizar_regras_cota(base_paginas: int, paginas_por_aula: int, paginas_por_turma: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO cota_regras (
            id, base_paginas, paginas_por_aula, paginas_por_turma, atualizado_em
        )
        VALUES (1, ?, ?, ?, datetime('now'))
        ON CONFLICT(id) DO UPDATE SET
            base_paginas = excluded.base_paginas,
            paginas_por_aula = excluded.paginas_por_aula,
            paginas_por_turma = excluded.paginas_por_turma,
            atualizado_em = datetime('now')
    """, (base_paginas, paginas_por_aula, paginas_por_turma))

    conn.commit()
    conn.close()

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
        return COTA_BASE_PADRAO

    regras = obter_regras_cota()
    perfil = row_usuario["perfil"]

    if perfil != "professor":
        conn.close()
        return int(regras["base_paginas"])

    cursor.execute("""
        SELECT aulas_semanais, turmas_quantidade
        FROM professores_carga
        WHERE usuario_id = ?
    """, (usuario_id,))
    carga = cursor.fetchone()
    conn.close()

    aulas_semanais = int(carga["aulas_semanais"]) if carga else 0
    turmas_quantidade = int(carga["turmas_quantidade"]) if carga else 0

    limite = (
        int(regras["base_paginas"])
        + aulas_semanais * int(regras["paginas_por_aula"])
        + turmas_quantidade * int(regras["paginas_por_turma"])
    )
    return max(limite, 0)

def listar_professores_admin(mes: str = None):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT
            u.id,
            u.nome,
            u.email,
            COALESCE(pc.aulas_semanais, 0) AS aulas_semanais,
            COALESCE(pc.turmas_quantidade, 0) AS turmas_quantidade
        FROM usuarios u
        LEFT JOIN professores_carga pc ON pc.usuario_id = u.id
        WHERE u.perfil = 'professor'
        ORDER BY u.nome ASC
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    professores = [dict(row) for row in rows]

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
            SET status = ?, finalizado_em = datetime('now')
            WHERE id = ?
        """, (status, job_id))
    else:
        cursor.execute("""
            UPDATE jobs
            SET status = ?
            WHERE id = ?
        """, (status, job_id))

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
    for professor in professores:
        limite = calcular_limite_cota_usuario(professor["id"])
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
