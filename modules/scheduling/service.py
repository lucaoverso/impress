from datetime import datetime

from fastapi import HTTPException

from modules.scheduling import repository
from modules.scheduling.lesson_config import (
    find_lesson_by_number,
    list_global_lessons,
    list_lessons_for_class,
    normalize_schedule_entries,
    resolve_class_lesson_window,
    total_configured_lessons,
)
from modules.scheduling.models import SchedulingResource, SchedulingReservation


def _get_entity_value(entity, field, default=None):
    if isinstance(entity, dict):
        return entity.get(field, default)
    return getattr(entity, field, default)


def build_scheduling_options(
    turnos_config: dict,
    turmas_ativas: list[dict],
    grade_entries: list[dict] | None = None,
):
    grade_items = normalize_schedule_entries(grade_entries or [])
    global_lessons = list_global_lessons(grade_items, only_active=True)
    turnos = [
        {"id": turno_id, "nome": cfg["nome"], "aulas": cfg["aulas"]}
        for turno_id, cfg in turnos_config.items()
    ]

    turmas = []
    for turma in turmas_ativas:
        turno_turma = str(turma.get("turno") or "").strip().upper()
        config_turno = turnos_config.get(turno_turma)
        lessons_for_class = list_lessons_for_class(turma, grade_items)
        start_lesson, end_lesson = resolve_class_lesson_window(turma)
        total_lessons_class = len(lessons_for_class) if lessons_for_class else int(
            (config_turno or {}).get("aulas") or 0
        )
        turmas.append(
            {
                "nome": turma["nome"],
                "turno": turno_turma,
                "turno_nome": config_turno["nome"] if config_turno else "Turno não configurado",
                "aulas": total_lessons_class,
                "turno_valido": bool(config_turno) and (
                    bool(lessons_for_class) if grade_items else True
                ),
                "quantidade_estudantes": int(turma.get("quantidade_estudantes") or 0),
                "aula_inicial": int(start_lesson),
                "aula_final": int(end_lesson),
                "aulas_disponiveis": lessons_for_class,
            }
        )

    return {
        "turnos": turnos,
        "grade_aulas": grade_items,
        "aulas_globais": global_lessons,
        "turmas": turmas,
    }


def validate_scheduling_period(
    data_inicio: str | None,
    data_fim: str | None,
    validar_data_agendamento,
):
    data_inicio_norm = validar_data_agendamento(data_inicio) if data_inicio else None
    data_fim_norm = validar_data_agendamento(data_fim) if data_fim else None

    if data_inicio_norm and data_fim_norm and data_inicio_norm > data_fim_norm:
        raise HTTPException(400, "Período inválido: data inicial maior que data final.")

    return {
        "data_inicio": data_inicio_norm,
        "data_fim": data_fim_norm,
    }


def ensure_resource_is_active(recurso: SchedulingResource | dict | None):
    ativo = _get_entity_value(recurso, "ativo")
    if not recurso or ativo != 1 and ativo is not True:
        raise HTTPException(404, "Recurso não encontrado.")
    return recurso


def ensure_class_shift_is_configured(turma: dict, turnos_config: dict):
    turno = str(turma.get("turno") or "").strip().upper()
    if turno not in turnos_config:
        raise HTTPException(
            400,
            "Turma sem turno configurado. Atualize o cadastro da turma no painel admin.",
        )
    return turno


def ensure_class_lesson_window_is_configured(turma: dict, grade_entries: list[dict]):
    lessons_for_class = list_lessons_for_class(turma, grade_entries)
    if lessons_for_class:
        return lessons_for_class

    total_lessons = total_configured_lessons(grade_entries)
    if total_lessons <= 0:
        raise HTTPException(
            409,
            "Nenhuma aula global foi configurada. Cadastre os horarios no painel admin.",
        )

    raise HTTPException(
        400,
        "Turma sem janela de aulas configurada. Atualize o cadastro da turma no painel admin.",
    )


def ensure_slot_has_capacity(recurso: SchedulingResource | dict, reservas_ativas_faixa: int):
    capacidade_recurso = max(int(_get_entity_value(recurso, "quantidade_itens", 1) or 1), 1)
    if reservas_ativas_faixa >= capacidade_recurso:
        raise HTTPException(
            409,
            (
                "Capacidade máxima atingida para este recurso nesta faixa. "
                f"Reservas ativas: {reservas_ativas_faixa}/{capacidade_recurso}."
            ),
        )
    return capacidade_recurso


def build_reservation_creation_payload(
    *,
    payload,
    usuario: dict,
    recurso: dict,
    turnos_config: dict,
    grade_entries: list[dict] | None,
    validar_data_agendamento,
    validar_turma,
    validar_tema_aula,
    validar_aula,
    calcular_faixa_global,
    resolver_usuario_professor_selecionado,
):
    ensure_resource_is_active(recurso)
    data_reserva = validar_data_agendamento(payload.data)
    turma = validar_turma(payload.turma)
    tema_aula = validar_tema_aula(payload.tema_aula)
    turno = ensure_class_shift_is_configured(turma, turnos_config)
    if grade_entries:
        ensure_class_lesson_window_is_configured(turma, grade_entries)
        aula = validar_aula(payload.aula, turma)
        faixa_global = int(aula)
        lesson_entry = find_lesson_by_number(grade_entries, faixa_global)
    else:
        aula = validar_aula(payload.aula, turno)
        faixa_global = calcular_faixa_global(turno, aula)
        lesson_entry = None
    usuario_reserva = resolver_usuario_professor_selecionado(
        usuario,
        payload.professor_id,
        contexto="solicitante do agendamento",
    )

    return {
        "recurso_id": payload.recurso_id,
        "usuario_id": int(usuario_reserva["id"]),
        "data": data_reserva,
        "turno": turno,
        "aula": aula,
        "faixa_global": faixa_global,
        "aula_label": lesson_entry.get("label", "") if lesson_entry else "",
        "turma": turma["nome"],
        "tema_aula": tema_aula,
        "observacao": (payload.observacao or "").strip(),
    }


def ensure_reservation_can_be_cancelled(
    *,
    agendamento: SchedulingReservation | dict | None,
    usuario: dict,
    usuario_eh_admin,
):
    if not agendamento:
        raise HTTPException(404, "Agendamento não encontrado.")

    if _get_entity_value(agendamento, "status") != "ATIVO":
        raise HTTPException(400, "Este agendamento já foi cancelado.")

    try:
        data_reserva = datetime.strptime(
            str(_get_entity_value(agendamento, "data")), "%Y-%m-%d"
        ).date()
    except ValueError as exc:
        raise HTTPException(400, "Data do agendamento inválida.") from exc

    if data_reserva < datetime.now().date():
        raise HTTPException(409, "Não é possível cancelar agendamentos de datas passadas.")

    dono_reserva = _get_entity_value(agendamento, "usuario_id") == usuario["id"]
    if not dono_reserva and not usuario_eh_admin(usuario):
        raise HTTPException(403, "Você não pode cancelar este agendamento.")

    return agendamento


def create_scheduling_reservation(
    *,
    payload,
    usuario: dict,
    turnos_config: dict,
    grade_entries: list[dict] | None = None,
    validar_data_agendamento=None,
    validar_turma=None,
    validar_tema_aula=None,
    validar_aula=None,
    calcular_faixa_global=None,
    resolver_usuario_professor_selecionado=None,
    buscar_recurso_por_id=None,
    contar_agendamentos_ativos_faixa=None,
    criar_agendamento=None,
):
    buscar_recurso_por_id_fn = buscar_recurso_por_id or repository.get_resource
    contar_agendamentos_ativos_faixa_fn = (
        contar_agendamentos_ativos_faixa or repository.count_active_reservations_in_slot
    )
    criar_agendamento_fn = criar_agendamento or repository.create_reservation
    if validar_data_agendamento is None or validar_turma is None or validar_tema_aula is None:
        raise ValueError("As validacoes obrigatorias do agendamento nao foram informadas.")
    if validar_aula is None or resolver_usuario_professor_selecionado is None:
        raise ValueError("As dependencias obrigatorias do agendamento nao foram informadas.")

    recurso = buscar_recurso_por_id_fn(payload.recurso_id)
    dados_reserva = build_reservation_creation_payload(
        payload=payload,
        usuario=usuario,
        recurso=recurso,
        turnos_config=turnos_config,
        grade_entries=grade_entries,
        validar_data_agendamento=validar_data_agendamento,
        validar_turma=validar_turma,
        validar_tema_aula=validar_tema_aula,
        validar_aula=validar_aula,
        calcular_faixa_global=calcular_faixa_global
        or (lambda _turno, aula: int(aula)),
        resolver_usuario_professor_selecionado=resolver_usuario_professor_selecionado,
    )

    reservas_ativas_faixa = contar_agendamentos_ativos_faixa_fn(
        recurso_id=payload.recurso_id,
        data=dados_reserva["data"],
        faixa_global=dados_reserva["faixa_global"],
    )
    ensure_slot_has_capacity(recurso, reservas_ativas_faixa)

    agendamento_id = criar_agendamento_fn(
        recurso_id=dados_reserva["recurso_id"],
        usuario_id=dados_reserva["usuario_id"],
        data=dados_reserva["data"],
        turno=dados_reserva["turno"],
        aula=dados_reserva["aula"],
        faixa_global=dados_reserva["faixa_global"],
        turma=dados_reserva["turma"],
        tema_aula=dados_reserva["tema_aula"],
        observacao=dados_reserva["observacao"],
    )

    return {
        "mensagem": "Agendamento realizado com sucesso.",
        "agendamento_id": agendamento_id,
    }


def cancel_scheduling_reservation(
    *,
    agendamento_id: int,
    usuario: dict,
    usuario_eh_admin,
    buscar_agendamento_por_id=None,
    cancelar_agendamento=None,
):
    buscar_agendamento_por_id_fn = buscar_agendamento_por_id or repository.get_reservation
    cancelar_agendamento_fn = cancelar_agendamento or repository.cancel_reservation

    agendamento = buscar_agendamento_por_id_fn(agendamento_id)
    ensure_reservation_can_be_cancelled(
        agendamento=agendamento,
        usuario=usuario,
        usuario_eh_admin=usuario_eh_admin,
    )

    cancelado = cancelar_agendamento_fn(agendamento_id)
    if not cancelado:
        raise HTTPException(400, "Não foi possível cancelar o agendamento.")

    return {"mensagem": "Agendamento cancelado com sucesso."}
