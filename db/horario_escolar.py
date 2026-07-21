from modules.scheduling.repository import (
    create_lesson_configuration,
    get_lesson_configuration,
    list_lesson_configurations,
    update_lesson_configuration,
)
from modules.scheduling.school_schedule_repository import (
    create_school_schedule,
    delete_school_schedule,
    get_school_schedule,
    list_school_schedules,
    list_school_years,
    update_school_schedule,
)

from ._proxy import proxy

buscar_horario_escolar_por_id = get_school_schedule
criar_horario_escolar = create_school_schedule
excluir_horario_escolar = delete_school_schedule
listar_anos_letivos_horario_escolar = list_school_years
listar_horarios_escolares = list_school_schedules
atualizar_horario_escolar = update_school_schedule


def listar_configuracoes_aulas(incluir_inativas: bool = False):
    return list_lesson_configurations(include_inactive=incluir_inativas)


def buscar_configuracao_aula_por_id(configuracao_id: int):
    return get_lesson_configuration(configuracao_id)


def criar_configuracao_aula(
    *, ordem_visual, tipo, aula_numero, nome, horario_inicio, horario_fim, ativo=True
):
    return create_lesson_configuration(
        visual_order=ordem_visual,
        entry_type=tipo,
        lesson_number=aula_numero,
        name=nome,
        start_time=horario_inicio,
        end_time=horario_fim,
        active=ativo,
    )


def atualizar_configuracao_aula(
    *, configuracao_id, ordem_visual, tipo, aula_numero, nome, horario_inicio, horario_fim, ativo
):
    return update_lesson_configuration(
        configuration_id=configuracao_id,
        visual_order=ordem_visual,
        entry_type=tipo,
        lesson_number=aula_numero,
        name=nome,
        start_time=horario_inicio,
        end_time=horario_fim,
        active=ativo,
    )

__all__ = [
    "atualizar_configuracao_aula",
    "buscar_horario_escolar_por_id",
    "buscar_configuracao_aula_por_id",
    "criar_horario_escolar",
    "criar_configuracao_aula",
    "excluir_horario_escolar",
    "listar_anos_letivos_horario_escolar",
    "listar_configuracoes_aulas",
    "listar_horarios_escolares",
    "atualizar_horario_escolar",
]
