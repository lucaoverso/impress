"""Coordena os dados usados pelas rotas de horário escolar."""

from db.catalogos import (
    buscar_disciplina_por_id,
    buscar_turma_por_id,
    listar_disciplinas_ativas,
    listar_turmas_ativas,
)
from db.docencia import listar_atribuicoes_docentes, listar_turmas_disciplinas_admin
from db.usuarios import buscar_usuario_por_id, listar_cargas_professores_por_usuario_ids
from modules.scheduling.repository import (
    list_lesson_configurations,
    list_scheduling_teachers as listar_professores_agendamento,
)
from modules.scheduling.school_schedule_repository import (
    create_school_schedule as criar_horario_escolar,
    delete_school_schedule as excluir_horario_escolar,
    get_school_schedule as buscar_horario_escolar_por_id,
    list_school_schedules as listar_horarios_escolares,
    list_school_years as listar_anos_letivos_horario_escolar,
    update_school_schedule as atualizar_horario_escolar,
)


def listar_configuracoes_aulas(incluir_inativas: bool = False):
    return list_lesson_configurations(include_inactive=incluir_inativas)
