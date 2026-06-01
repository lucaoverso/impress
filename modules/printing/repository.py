from db.catalogos import listar_turmas_ativas
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
