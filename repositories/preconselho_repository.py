from db.preconselho import (
    atualizar_motivo_pre_conselho_dados as _atualizar_motivo_pre_conselho_dados,
    atualizar_periodo_pre_conselho_dados as _atualizar_periodo_pre_conselho_dados,
    atualizar_status_motivo_pre_conselho as _atualizar_status_motivo_pre_conselho,
    atualizar_status_periodo_pre_conselho as _atualizar_status_periodo_pre_conselho,
    buscar_motivo_pre_conselho_por_id as _buscar_motivo_pre_conselho_por_id,
    buscar_motivos_pre_conselho_por_ids as _buscar_motivos_pre_conselho_por_ids,
    buscar_periodo_pre_conselho_por_id as _buscar_periodo_pre_conselho_por_id,
    buscar_registro_pre_conselho_por_id as _buscar_registro_pre_conselho_por_id,
    contar_registros_pre_conselho_por_professor_periodo as _contar_registros_pre_conselho_por_professor_periodo,
    criar_motivo_pre_conselho as _criar_motivo_pre_conselho,
    criar_ou_atualizar_registro_pre_conselho as _criar_ou_atualizar_registro_pre_conselho,
    criar_periodo_pre_conselho as _criar_periodo_pre_conselho,
    excluir_registro_pre_conselho as _excluir_registro_pre_conselho,
    listar_estudantes_pre_conselho_painel as _listar_estudantes_pre_conselho_painel,
    listar_motivos_pre_conselho as _listar_motivos_pre_conselho,
    listar_periodos_pre_conselho as _listar_periodos_pre_conselho,
    listar_registros_pre_conselho as _listar_registros_pre_conselho,
)


def atualizar_motivo_pre_conselho_dados(motivo_id: int, **dados):
    return _atualizar_motivo_pre_conselho_dados(motivo_id, **dados)


def atualizar_periodo_pre_conselho_dados(periodo_id: int, **dados):
    return _atualizar_periodo_pre_conselho_dados(periodo_id, **dados)


def atualizar_status_motivo_pre_conselho(motivo_id: int, ativo: bool):
    return _atualizar_status_motivo_pre_conselho(motivo_id, ativo)


def atualizar_status_periodo_pre_conselho(periodo_id: int, status: str):
    return _atualizar_status_periodo_pre_conselho(periodo_id, status)


def buscar_motivo_pre_conselho_por_id(motivo_id: int):
    return _buscar_motivo_pre_conselho_por_id(motivo_id)


def buscar_motivos_pre_conselho_por_ids(motivo_ids: list[int]):
    return _buscar_motivos_pre_conselho_por_ids(motivo_ids)


def buscar_periodo_pre_conselho_por_id(periodo_id: int):
    return _buscar_periodo_pre_conselho_por_id(periodo_id)


def buscar_registro_pre_conselho_por_id(registro_id: int):
    return _buscar_registro_pre_conselho_por_id(registro_id)


def contar_registros_pre_conselho_por_professor_periodo(*, professor_id: int, periodo_id: int):
    return _contar_registros_pre_conselho_por_professor_periodo(
        professor_id=professor_id,
        periodo_id=periodo_id,
    )


def criar_motivo_pre_conselho(**dados):
    return _criar_motivo_pre_conselho(**dados)


def criar_ou_atualizar_registro_pre_conselho(**dados):
    return _criar_ou_atualizar_registro_pre_conselho(**dados)


def criar_periodo_pre_conselho(**dados):
    return _criar_periodo_pre_conselho(**dados)


def excluir_registro_pre_conselho(registro_id: int):
    return _excluir_registro_pre_conselho(registro_id)


def listar_estudantes_pre_conselho_painel(**filtros):
    return _listar_estudantes_pre_conselho_painel(**filtros)


def listar_motivos_pre_conselho(*, incluir_inativos: bool = False):
    return _listar_motivos_pre_conselho(incluir_inativos=incluir_inativos)


def listar_periodos_pre_conselho():
    return _listar_periodos_pre_conselho()


def listar_registros_pre_conselho(**filtros):
    return _listar_registros_pre_conselho(**filtros)


__all__ = [
    "atualizar_motivo_pre_conselho_dados",
    "atualizar_periodo_pre_conselho_dados",
    "atualizar_status_motivo_pre_conselho",
    "atualizar_status_periodo_pre_conselho",
    "buscar_motivo_pre_conselho_por_id",
    "buscar_motivos_pre_conselho_por_ids",
    "buscar_periodo_pre_conselho_por_id",
    "buscar_registro_pre_conselho_por_id",
    "contar_registros_pre_conselho_por_professor_periodo",
    "criar_motivo_pre_conselho",
    "criar_ou_atualizar_registro_pre_conselho",
    "criar_periodo_pre_conselho",
    "excluir_registro_pre_conselho",
    "listar_estudantes_pre_conselho_painel",
    "listar_motivos_pre_conselho",
    "listar_periodos_pre_conselho",
    "listar_registros_pre_conselho",
]
