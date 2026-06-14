from fastapi import APIRouter, Depends

from auth import get_usuario_logado
from modules.scheduling.dependencies import (
    TURNOS_CONFIG,
    require_admin_for_scheduling,
    resolve_scheduling_teacher,
    user_can_manage_scheduling,
    user_is_admin_for_scheduling,
    validar_aula,
    validar_data_agendamento,
    validar_tema_aula,
    validar_turma,
)
from modules.scheduling.repository import (
    list_active_classes as listar_turmas_ativas,
    list_lesson_configurations as listar_configuracoes_aulas,
    list_active_resources as listar_recursos_ativos,
    list_reservations as listar_agendamentos,
    list_scheduling_teachers as listar_professores_agendamento,
)
from modules.scheduling.schemas import (
    SchedulingOperationResponse,
    SchedulingOptionsOut,
    SchedulingReservationCreate,
    SchedulingReservationOut,
    SchedulingReservationResponse,
    SchedulingResourceOption,
    SchedulingTeacherOut,
)
from modules.scheduling.service import (
    build_scheduling_options,
    cancel_scheduling_reservation,
    create_scheduling_reservation,
    validate_scheduling_period,
)

router = APIRouter()


@router.get("/agendamento/recursos", response_model=list[SchedulingResourceOption])
def recursos_agendamento(_usuario=Depends(get_usuario_logado)):
    return listar_recursos_ativos()


@router.get("/agendamento/opcoes", response_model=SchedulingOptionsOut)
def opcoes_agendamento(_usuario=Depends(get_usuario_logado)):
    return build_scheduling_options(
        TURNOS_CONFIG,
        listar_turmas_ativas(),
        listar_configuracoes_aulas(include_inactive=False),
    )


@router.get("/agendamento/professores", response_model=list[SchedulingTeacherOut])
def professores_agendamento(usuario=Depends(get_usuario_logado)):
    if not user_can_manage_scheduling(usuario):
        require_admin_for_scheduling(usuario)
    return listar_professores_agendamento()


@router.get("/agendamento/reservas", response_model=list[SchedulingReservationOut])
def listar_reservas_agendamento(
    data_inicio: str = None,
    data_fim: str = None,
    recurso_id: int = None,
    _usuario=Depends(get_usuario_logado),
):
    periodo = validate_scheduling_period(data_inicio, data_fim, validar_data_agendamento)

    return listar_agendamentos(
        data_inicio=periodo["data_inicio"],
        data_fim=periodo["data_fim"],
        recurso_id=recurso_id,
    )


@router.post("/agendamento/reservas", response_model=SchedulingReservationResponse)
def criar_reserva_agendamento(
    payload: SchedulingReservationCreate,
    usuario=Depends(get_usuario_logado),
):
    return create_scheduling_reservation(
        payload=payload,
        usuario=usuario,
        turnos_config=TURNOS_CONFIG,
        grade_entries=listar_configuracoes_aulas(include_inactive=False),
        validar_data_agendamento=validar_data_agendamento,
        validar_turma=validar_turma,
        validar_tema_aula=validar_tema_aula,
        validar_aula=validar_aula,
        resolver_usuario_professor_selecionado=resolve_scheduling_teacher,
    )


@router.post("/agendamento/reservas/{agendamento_id}/cancelar", response_model=SchedulingOperationResponse)
def cancelar_reserva_agendamento(
    agendamento_id: int,
    usuario=Depends(get_usuario_logado),
):
    return cancel_scheduling_reservation(
        agendamento_id=agendamento_id,
        usuario=usuario,
        usuario_eh_admin=user_is_admin_for_scheduling,
    )
