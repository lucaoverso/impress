from modules.scheduling.config import TURNOS_CONFIG
from modules.scheduling.policies import (
    calcular_faixa_global,
    validar_aula,
    validar_data_agendamento,
    validar_tema_aula,
    validar_turma,
)
from routers.common import (
    exigir_admin as require_admin_for_scheduling,
    resolver_usuario_professor_selecionado as resolve_scheduling_teacher,
    usuario_eh_admin as user_is_admin_for_scheduling,
    usuario_pode_gerir_impressoes as user_can_manage_scheduling,
)

__all__ = [
    "TURNOS_CONFIG",
    "calcular_faixa_global",
    "require_admin_for_scheduling",
    "resolve_scheduling_teacher",
    "user_can_manage_scheduling",
    "user_is_admin_for_scheduling",
    "validar_aula",
    "validar_data_agendamento",
    "validar_tema_aula",
    "validar_turma",
]
