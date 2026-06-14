from db.agendamento import (
    buscar_agendamento_por_id,
    cancelar_agendamento,
    contar_agendamentos_ativos_faixa,
    criar_agendamento,
    listar_agendamentos,
)
from db.catalogos import buscar_recurso_por_id, listar_recursos_ativos, listar_turmas_ativas
from db.horario_escolar import (
    atualizar_configuracao_aula,
    buscar_configuracao_aula_por_id,
    criar_configuracao_aula,
    listar_configuracoes_aulas,
)
from db.usuarios import listar_professores_agendamento

from modules.scheduling.models import SchedulingReservation, SchedulingResource


def get_reservation(agendamento_id: int):
    return SchedulingReservation.from_dict(buscar_agendamento_por_id(agendamento_id))


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
    return [
        SchedulingReservation.from_dict(item)
        for item in listar_agendamentos(
            data_inicio=data_inicio,
            data_fim=data_fim,
            recurso_id=recurso_id,
            usuario_id=usuario_id,
            incluir_cancelados=incluir_cancelados,
        )
    ]


def get_resource(recurso_id: int):
    return SchedulingResource.from_dict(buscar_recurso_por_id(recurso_id))


def list_active_resources():
    return [
        SchedulingResource.from_dict(item)
        for item in listar_recursos_ativos()
    ]


def list_active_classes():
    return listar_turmas_ativas()


def list_lesson_configurations(*, include_inactive: bool = True):
    return listar_configuracoes_aulas(incluir_inativas=include_inactive)


def get_lesson_configuration(configuration_id: int):
    return buscar_configuracao_aula_por_id(configuration_id)


def create_lesson_configuration(
    *,
    visual_order: int,
    entry_type: str,
    lesson_number: int | None,
    name: str,
    start_time: str,
    end_time: str,
    active: bool = True,
):
    return criar_configuracao_aula(
        ordem_visual=visual_order,
        tipo=entry_type,
        aula_numero=lesson_number,
        nome=name,
        horario_inicio=start_time,
        horario_fim=end_time,
        ativo=active,
    )


def update_lesson_configuration(
    *,
    configuration_id: int,
    visual_order: int,
    entry_type: str,
    lesson_number: int | None,
    name: str,
    start_time: str,
    end_time: str,
    active: bool,
):
    return atualizar_configuracao_aula(
        configuracao_id=configuration_id,
        ordem_visual=visual_order,
        tipo=entry_type,
        aula_numero=lesson_number,
        nome=name,
        horario_inicio=start_time,
        horario_fim=end_time,
        ativo=active,
    )


def list_scheduling_teachers():
    return listar_professores_agendamento()
