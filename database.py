import sqlite3
import uuid
import hashlib
from datetime import datetime

DB_NAME = "impressao.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def criar_job(usuario_id: int, arquivo: str, copias: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO jobs (usuario_id, arquivo, copias, status, prioridade, criado_em)
        VALUES (?, ?, ?, 'PENDENTE', 0, datetime('now'))
    """, (usuario_id, arquivo, copias))

    conn.commit()
    conn.close()

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
            status TEXT NOT NULL,
            prioridade INTEGER NOT NULL,
            criado_em TEXT NOT NULL
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

    conn.commit()
    conn.close()

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
