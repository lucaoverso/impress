from datetime import datetime

from fastapi import HTTPException

from modules.scheduling import repository
from modules.scheduling.config import TURNOS_CONFIG
from modules.scheduling.lesson_config import (
    list_lessons_for_class,
    total_configured_lessons,
)


def validar_data_agendamento(data_txt: str) -> str:
    try:
        return datetime.strptime(data_txt, "%Y-%m-%d").date().isoformat()
    except ValueError as exc:
        raise HTTPException(400, "Data inválida. Use o formato YYYY-MM-DD.") from exc


def validar_turno(turno: str) -> str:
    turno_limpo = str(turno).strip().upper()
    if turno_limpo not in TURNOS_CONFIG:
        raise HTTPException(400, "Turno inválido.")
    return turno_limpo


def validar_aula(aula: str, turma_ou_turno) -> str:
    aula_limpa = str(aula).strip()
    if not aula_limpa.isdigit():
        raise HTTPException(400, "Aula inválida.")

    numero_aula = int(aula_limpa)
    if numero_aula <= 0:
        raise HTTPException(400, "Aula inválida.")

    if isinstance(turma_ou_turno, dict):
        grade_entries = repository.list_lesson_configurations(include_inactive=False)
        lessons_for_class = list_lessons_for_class(turma_ou_turno, grade_entries)
        if not lessons_for_class:
            total_lessons = total_configured_lessons(grade_entries)
            if total_lessons <= 0:
                raise HTTPException(
                    409,
                    "Nenhuma aula global foi configurada. Cadastre os horarios no painel admin.",
                )
            raise HTTPException(
                400,
                "A turma selecionada esta sem janela de aulas configurada. Atualize no painel admin.",
            )

        allowed_lessons = {int(item.get("aula_numero") or 0) for item in lessons_for_class}
        if numero_aula not in allowed_lessons:
            first_lesson = min(allowed_lessons)
            last_lesson = max(allowed_lessons)
            raise HTTPException(
                400,
                (
                    "Aula inválida para a turma selecionada. "
                    f"Essa turma utiliza as aulas {first_lesson} a {last_lesson}."
                ),
            )
        return str(numero_aula)

    turn = validar_turno(turma_ou_turno)
    config_turno = TURNOS_CONFIG.get(turn) or {}
    max_aulas_turno = int(config_turno.get("aulas") or 0)
    if numero_aula < 1 or (max_aulas_turno and numero_aula > max_aulas_turno):
        raise HTTPException(
            400,
            f"Aula inválida para o turno selecionado. Esse turno possui {max_aulas_turno} aulas.",
        )

    return str(numero_aula)


def calcular_faixa_global(turma_ou_turno, aula: str) -> int:
    return int(validar_aula(aula, turma_ou_turno))


def validar_turma(turma: str) -> dict:
    turma_limpa = str(turma).strip()
    if not turma_limpa:
        raise HTTPException(400, "Turma inválida.")

    for turma_db in repository.list_active_classes():
        nome_turma = str(turma_db.get("nome", "")).strip()
        if nome_turma == turma_limpa:
            return dict(turma_db)

    raise HTTPException(400, "Turma inválida.")


def validar_tema_aula(tema_aula: str) -> str:
    tema_limpo = str(tema_aula or "").strip()
    if not tema_limpo:
        raise HTTPException(400, "Tema da aula é obrigatório.")
    return tema_limpo


__all__ = [
    "calcular_faixa_global",
    "validar_aula",
    "validar_data_agendamento",
    "validar_tema_aula",
    "validar_turma",
    "validar_turno",
]
