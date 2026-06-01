from datetime import datetime

from fastapi import HTTPException

from modules.scheduling.config import FAIXA_GLOBAL_OFFSET_POR_TURNO, TURNOS_CONFIG
from modules.scheduling import repository


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


def validar_aula(aula: str, turno: str) -> str:
    aula_limpa = str(aula).strip()
    if not aula_limpa.isdigit():
        raise HTTPException(400, "Aula inválida.")

    numero_aula = int(aula_limpa)
    max_aulas_turno = TURNOS_CONFIG[turno]["aulas"]
    if numero_aula < 1 or numero_aula > max_aulas_turno:
        raise HTTPException(
            400,
            f"Aula inválida para o turno selecionado. Esse turno possui {max_aulas_turno} aulas.",
        )

    return aula_limpa


def calcular_faixa_global(turno: str, aula: str) -> int:
    turno_limpo = validar_turno(turno)
    numero_aula = int(validar_aula(aula, turno_limpo))
    faixa_global = numero_aula + FAIXA_GLOBAL_OFFSET_POR_TURNO[turno_limpo]

    if turno_limpo == "INTEGRAL" and numero_aula > 5:
        faixa_global += 1

    return faixa_global


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
