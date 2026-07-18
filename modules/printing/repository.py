from db.catalogos import listar_turmas_ativas
from db.core import get_connection
from db.impressao import (
    alterar_prioridade,
    buscar_cota,
    buscar_cota_do_usuario,
    buscar_job,
    cancelar_job,
    consumir_cota,
    criar_cota,
    criar_job,
    listar_fila,
    listar_jobs_por_usuario,
    obter_regras_cota,
    obter_status_impressao,
)


def list_active_classes():
    return listar_turmas_ativas()


def count_active_students_by_class():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            turma_id,
            SUM(CASE WHEN ativo = 1 THEN 1 ELSE 0 END) AS total
        FROM estudantes
        WHERE turma_id > 0
        GROUP BY turma_id
    """
    )
    rows = cursor.fetchall()
    conn.close()
    return {int(row["turma_id"]): int(row["total"] or 0) for row in rows}


def create_job(**kwargs):
    return criar_job(**kwargs)


def get_job(job_id: int):
    return buscar_job(job_id)


def list_queue():
    return listar_fila()


def list_jobs_by_user(usuario_id: int):
    return listar_jobs_por_usuario(usuario_id)


def cancel_job(job_id: int, *, estornar_cota: bool = True):
    return cancelar_job(job_id, estornar_cota=estornar_cota)


def update_job_priority(job_id: int, urgente: bool):
    return alterar_prioridade(job_id, urgente)


def get_print_status():
    return obter_status_impressao()


def get_quota_rules():
    return obter_regras_cota()


def get_quota(usuario_id: int, mes: str):
    return buscar_cota(usuario_id, mes)


def get_user_quota(usuario_id: int, mes: str):
    return buscar_cota_do_usuario(usuario_id, mes)


def create_quota(usuario_id: int, mes: str, limite: int):
    return criar_cota(usuario_id, mes, limite)


def consume_quota(cota_id: int, paginas: int):
    return consumir_cota(cota_id, paginas)


def list_printers(*, include_inactive: bool = False):
    conn = get_connection()
    try:
        query = "SELECT id, name, active, created_at FROM printing_printers"
        if not include_inactive:
            query += " WHERE active = 1"
        rows = conn.execute(query + " ORDER BY name COLLATE NOCASE").fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_printer_by_name(name: str):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, name, active, created_at FROM printing_printers WHERE name = ? COLLATE NOCASE",
            (name,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def create_printer(name: str):
    conn = get_connection()
    try:
        cursor = conn.execute("INSERT INTO printing_printers (name) VALUES (?)", (name,))
        conn.commit()
        row = conn.execute(
            "SELECT id, name, active, created_at FROM printing_printers WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
        return dict(row)
    finally:
        conn.close()


def update_printer_status(printer_id: int, active: bool):
    conn = get_connection()
    try:
        cursor = conn.execute(
            "UPDATE printing_printers SET active = ? WHERE id = ?",
            (int(active), printer_id),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def delete_printer(printer_id: int):
    conn = get_connection()
    try:
        cursor = conn.execute("DELETE FROM printing_printers WHERE id = ?", (printer_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()
