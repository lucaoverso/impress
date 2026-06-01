from db.agendamento import (
    buscar_agendamento_por_id,
    cancelar_agendamento,
    contar_agendamentos_ativos_faixa,
    criar_agendamento,
    listar_agendamentos,
)
from db.catalogos import buscar_recurso_por_id, listar_recursos_ativos, listar_turmas_ativas
from db.usuarios import listar_professores_agendamento


def get_reservation(agendamento_id: int):
    return buscar_agendamento_por_id(agendamento_id)


def cancel_reservation(agendamento_id: int):
    return cancelar_agendamento(agendamento_id)


def count_active_reservations_in_slot(recurso_id: int, data: str, faixa_global: int):
    return contar_agendamentos_ativos_faixa(recurso_id=recurso_id, data=data, faixa_global=faixa_global)


def create_reservation(
    *,
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
    return criar_agendamento(
        recurso_id=recurso_id,
        usuario_id=usuario_id,
        data=data,
        turno=turno,
        aula=aula,
        faixa_global=faixa_global,
        turma=turma,
        tema_aula=tema_aula,
        observacao=observacao,
    )


def list_reservations(
    *,
    data_inicio: str | None = None,
    data_fim: str | None = None,
    recurso_id: int | None = None,
    usuario_id: int | None = None,
    incluir_cancelados: bool = False,
):
    return listar_agendamentos(
        data_inicio=data_inicio,
        data_fim=data_fim,
        recurso_id=recurso_id,
        usuario_id=usuario_id,
        incluir_cancelados=incluir_cancelados,
    )


def get_resource(recurso_id: int):
    return buscar_recurso_por_id(recurso_id)


def list_active_resources():
    return listar_recursos_ativos()


def list_active_classes():
    return listar_turmas_ativas()


def list_scheduling_teachers():
    return listar_professores_agendamento()
