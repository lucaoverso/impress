from db.apc import listar_apc_destinatarios
from db.horario_escolar import listar_horarios_escolares
from db.usuarios import listar_professores_agendamento
from services.apc_service import (
    APC_PUBLICO_ALVO_PROFESSORES_SELECIONADOS,
    APC_PUBLICO_ALVO_TODOS_PROFESSORES,
    agrupar_destinatarios_selecionados_apc,
    agrupar_horarios_professor_dia,
    agrupar_professores_elegiveis,
    enriquecer_periodo_apc,
    filtrar_horarios_por_tipo_entrega,
)


def resolve_apc_recipients(period: dict, professor_id: int | None = None) -> list[dict]:
    normalized = enriquecer_periodo_apc(period)
    if normalized["publico_alvo"] == APC_PUBLICO_ALVO_TODOS_PROFESSORES:
        teachers = listar_professores_agendamento()
        if professor_id is not None:
            teachers = [
                item
                for item in teachers
                if int(item.get("id") or 0) == int(professor_id)
            ]
        return agrupar_professores_elegiveis(teachers)

    if normalized["publico_alvo"] == APC_PUBLICO_ALVO_PROFESSORES_SELECIONADOS:
        recipients = listar_apc_destinatarios(
            periodo_id=int(normalized["id"]),
            professor_id=int(professor_id) if professor_id is not None else None,
        )
        return agrupar_destinatarios_selecionados_apc(recipients)

    schedules = listar_horarios_escolares(
        ano_letivo=int(normalized["ano_letivo"]),
        professor_id=professor_id,
        dia_semana=normalized["dia_semana"],
    )
    filtered = filtrar_horarios_por_tipo_entrega(
        schedules, normalized["tipo_entrega"]
    )
    return agrupar_horarios_professor_dia(filtered)
