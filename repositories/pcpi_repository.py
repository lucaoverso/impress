from db.agendamento import listar_agendamentos as _listar_agendamentos
from db.pcpi import (
    buscar_registro_pcpi_manual_por_id as _buscar_registro_pcpi_manual_por_id,
    criar_registro_pcpi_manual as _criar_registro_pcpi_manual,
    listar_registros_pcpi_manuais as _listar_registros_pcpi_manuais,
)
from db.usuarios import (
    listar_cargas_professores_por_usuario_ids as _listar_cargas_professores_por_usuario_ids,
)


def listar_agendamentos_pcpi_por_data(data: str):
    return _listar_agendamentos(data_inicio=data, data_fim=data)


def listar_cargas_professores_pcpi_por_usuario_ids(usuario_ids: list[int]):
    ids_normalizados = []
    for valor in usuario_ids or []:
        try:
            usuario_id = int(valor or 0)
        except (TypeError, ValueError):
            continue
        if usuario_id > 0 and usuario_id not in ids_normalizados:
            ids_normalizados.append(usuario_id)
    return _listar_cargas_professores_por_usuario_ids(ids_normalizados)


def buscar_registro_pcpi_manual_por_id(registro_id: int):
    return _buscar_registro_pcpi_manual_por_id(registro_id)


def criar_registro_pcpi_manual(**dados):
    return _criar_registro_pcpi_manual(**dados)


def criar_e_buscar_registro_pcpi_manual(**dados):
    registro_id = criar_registro_pcpi_manual(**dados)
    return buscar_registro_pcpi_manual_por_id(registro_id)


def listar_registros_pcpi_manuais_por_data(*, data: str):
    return _listar_registros_pcpi_manuais(data=data)


__all__ = [
    "buscar_registro_pcpi_manual_por_id",
    "criar_e_buscar_registro_pcpi_manual",
    "criar_registro_pcpi_manual",
    "listar_agendamentos_pcpi_por_data",
    "listar_cargas_professores_pcpi_por_usuario_ids",
    "listar_registros_pcpi_manuais_por_data",
]
