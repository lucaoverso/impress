"""Compatibilidade temporária; a implementação vive em modules.scheduling."""

from modules.scheduling.school_schedule_router import (
    atualizar_aula_atividade_professor_api,
    atualizar_horario_escolar_api,
    criar_aula_atividade_professor_api,
    criar_horario_escolar_api,
    excluir_aula_atividade_professor_api,
    excluir_horario_escolar_api,
    listar_horarios_escolares_api,
    listar_professores_do_dia_api,
    obter_contexto_horario_escolar_api,
    obter_matriz_horario_turma_api,
    router,
)

__all__ = [
    "atualizar_aula_atividade_professor_api",
    "atualizar_horario_escolar_api",
    "criar_aula_atividade_professor_api",
    "criar_horario_escolar_api",
    "excluir_aula_atividade_professor_api",
    "excluir_horario_escolar_api",
    "listar_horarios_escolares_api",
    "listar_professores_do_dia_api",
    "obter_contexto_horario_escolar_api",
    "obter_matriz_horario_turma_api",
    "router",
]
