"""Compatibilidade temporária para consumidores ainda fora de modules/scheduling."""

from modules.scheduling.repository import (
    cancel_reservation,
    count_active_reservations_in_slot,
    create_reservation,
    get_reservation,
    list_reservations,
)


def buscar_agendamento_por_id(agendamento_id: int):
    item = get_reservation(agendamento_id)
    return item.to_dict() if item else None


def cancelar_agendamento(agendamento_id: int):
    return cancel_reservation(agendamento_id)


def contar_agendamentos_ativos_faixa(recurso_id: int, data: str, faixa_global: int):
    return count_active_reservations_in_slot(recurso_id, data, faixa_global)


def criar_agendamento(**kwargs):
    return create_reservation(**kwargs)


def listar_agendamentos(**kwargs):
    return [item.to_dict() for item in list_reservations(**kwargs)]


__all__ = [
    "buscar_agendamento_por_id",
    "cancelar_agendamento",
    "contar_agendamentos_ativos_faixa",
    "criar_agendamento",
    "listar_agendamentos",
]
