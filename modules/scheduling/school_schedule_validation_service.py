from datetime import datetime
from sqlite3 import IntegrityError

from fastapi import HTTPException

from modules.scheduling.school_schedule_data_service import (
    buscar_disciplina_por_id,
    buscar_turma_por_id,
    buscar_usuario_por_id,
    listar_atribuicoes_docentes,
    listar_cargas_professores_por_usuario_ids,
    listar_configuracoes_aulas,
    listar_turmas_disciplinas_admin,
)
from modules.scheduling.school_schedule_service import (
    normalizar_dia_semana,
    validar_ano_letivo,
    validar_aula_numero,
)
from routers.common import CARGO_PROFESSOR, normalizar_cargo_usuario


def validate_iso_date(value: str, field: str = "Data") -> str:
    text = str(value or "").strip()
    if not text:
        raise HTTPException(400, f"{field} inválida. Use o formato YYYY-MM-DD.")
    try:
        return datetime.strptime(text, "%Y-%m-%d").date().isoformat()
    except ValueError as exc:
        raise HTTPException(400, f"{field} inválida. Use o formato YYYY-MM-DD.") from exc


def translate_integrity_error(exc: IntegrityError) -> str:
    text = str(exc).lower()
    if "idx_aulas_atividade_professor_slot" in text:
        return "O professor já possui uma aula ou aula atividade nessa faixa e nesse dia."
    if "idx_horarios_escolares_professor_faixa_slot" in text:
        return "O professor já possui aula cadastrada nessa faixa e nesse dia."
    if "idx_horarios_escolares_professor_slot" in text:
        return "O professor já possui aula cadastrada nesse dia e horário."
    if "idx_horarios_escolares_turma_slot" in text:
        return "Já existe aula cadastrada para essa turma nesse dia e horário."
    if "professor_usuario_id" in text and "dia_semana" in text and "aula_numero" in text:
        return "O professor já possui aula cadastrada nesse dia e horário."
    if "turma_id" in text and "dia_semana" in text and "aula_numero" in text:
        return "Já existe aula cadastrada para essa turma nesse dia e horário."
    return "Conflito ao salvar o horário escolar."


def validate_active_teacher(teacher_id: int) -> dict:
    teacher = buscar_usuario_por_id(int(teacher_id))
    if not teacher or normalizar_cargo_usuario(teacher) != CARGO_PROFESSOR:
        raise HTTPException(404, "Professor não encontrado.")
    if not bool(int(teacher.get("ativo", 1) or 0)):
        raise HTTPException(400, "Professor selecionado esta inativo.")
    return teacher


def _validate_teaching_assignment(teacher: dict, classroom: dict, discipline: dict):
    teacher_id = int(teacher["id"])
    classroom_id = int(classroom["id"])
    discipline_id = int(discipline["id"])
    if listar_atribuicoes_docentes(
        professor_id=teacher_id,
        turma_id=classroom_id,
        disciplina_id=discipline_id,
        incluir_inativos=False,
    ):
        return
    if listar_turmas_disciplinas_admin(
        turma_id=classroom_id,
        disciplina_id=discipline_id,
        professor_id=teacher_id,
        incluir_inativos=False,
    ):
        return

    workload = listar_cargas_professores_por_usuario_ids([teacher_id]).get(teacher_id, {})
    classrooms = {str(item).strip().casefold() for item in workload.get("turmas", []) if str(item).strip()}
    disciplines = {
        str(item).strip().casefold()
        for item in workload.get("disciplinas", [])
        if str(item).strip()
    }
    if (
        str(classroom.get("nome") or "").strip().casefold() in classrooms
        and str(discipline.get("nome") or "").strip().casefold() in disciplines
    ):
        return
    raise HTTPException(
        400,
        "O professor selecionado não possui vínculo com a turma e disciplina informadas.",
    )


def validate_school_schedule_payload(payload) -> dict:
    lesson_configurations = listar_configuracoes_aulas(incluir_inativas=False)
    try:
        school_year = validar_ano_letivo(payload.ano_letivo)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    classroom = buscar_turma_por_id(int(payload.turma_id))
    if not classroom:
        raise HTTPException(404, "Turma não encontrada.")
    discipline = buscar_disciplina_por_id(int(payload.disciplina_id))
    if not discipline:
        raise HTTPException(404, "Disciplina não encontrada.")
    teacher = validate_active_teacher(int(payload.professor_id))
    try:
        weekday = normalizar_dia_semana(payload.dia_semana)
        lesson_number = validar_aula_numero(
            payload.aula_numero,
            classroom,
            configuracoes_aulas=lesson_configurations,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    _validate_teaching_assignment(teacher, classroom, discipline)
    return {
        "ano_letivo": school_year,
        "turma_id": int(classroom["id"]),
        "disciplina_id": int(discipline["id"]),
        "professor_id": int(teacher["id"]),
        "dia_semana": weekday,
        "aula_numero": lesson_number,
    }
