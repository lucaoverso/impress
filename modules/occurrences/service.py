from datetime import datetime

from fastapi import HTTPException

from routers.common import usuario_eh_gestor, usuario_eh_professor

from . import catalog_repository, repository


RESPONSIBLE_CONTACTS = {"none", "communicate", "summon"}
WEEKDAYS = ("SEGUNDA", "TERCA", "QUARTA", "QUINTA", "SEXTA", "SABADO", "DOMINGO")


def _user_id(user: dict) -> int:
    try:
        user_id = int(user.get("id") or 0)
    except (TypeError, ValueError):
        user_id = 0
    if user_id <= 0:
        raise HTTPException(401, "Usuario autenticado invalido.")
    return user_id


def require_occurrences_access(user: dict) -> None:
    if not (usuario_eh_professor(user) or usuario_eh_gestor(user)):
        raise HTTPException(403, "Acesso negado.")


def require_manager(user: dict) -> None:
    if not usuario_eh_gestor(user):
        raise HTTPException(403, "Acesso restrito a gestao.")


def context(user: dict) -> dict:
    require_occurrences_access(user)
    manager = usuario_eh_gestor(user)
    return {
        "is_manager": manager,
        "is_teacher": usuario_eh_professor(user),
        "reasons": catalog_repository.list_reasons(include_inactive=manager),
    }


def search_students(user: dict, term: str, limit: int) -> list[dict]:
    require_occurrences_access(user)
    clean_term = str(term or "").strip()
    safe_limit = min(max(int(limit or 20), 1), 50)
    students = catalog_repository.search_students(clean_term, safe_limit)
    return [
        {
            **student,
            "label": f"{student['nome']} ({student.get('turma_nome') or 'Sem turma'})",
        }
        for student in students
    ]


def create_reason(user: dict, name: str) -> dict:
    require_manager(user)
    clean_name = str(name or "").strip()
    if len(clean_name) < 3:
        raise HTTPException(400, "Informe um motivo com pelo menos 3 caracteres.")
    if len(clean_name) > 180:
        raise HTTPException(400, "O motivo excede 180 caracteres.")
    try:
        return catalog_repository.create_reason(clean_name)
    except Exception as exc:
        if "UNIQUE" in str(exc).upper():
            raise HTTPException(400, "Este motivo ja esta cadastrado.") from exc
        raise


def update_reason(user: dict, reason_id: int, *, name: str | None, active: bool | None) -> dict:
    require_manager(user)
    clean_name = None
    if name is not None:
        clean_name = str(name).strip()
        if len(clean_name) < 3 or len(clean_name) > 180:
            raise HTTPException(400, "Informe um motivo entre 3 e 180 caracteres.")
    try:
        reason = catalog_repository.update_reason(reason_id, name=clean_name, active=active)
    except Exception as exc:
        if "UNIQUE" in str(exc).upper():
            raise HTTPException(400, "Este motivo ja esta cadastrado.") from exc
        raise
    if not reason:
        raise HTTPException(404, "Motivo nao encontrado.")
    return reason


def create_pre_registration(
    user: dict,
    *,
    student_ids: list[int],
    reason_ids: list[int],
    responsible_contact: str,
) -> dict:
    if not usuario_eh_professor(user):
        raise HTTPException(403, "Apenas professores podem criar pre-registros.")
    normalized_student_ids = _normalize_ids(student_ids, "estudante")
    students = catalog_repository.get_students(normalized_student_ids)
    if len(students) != len(normalized_student_ids) or any(
        not bool(item.get("ativo")) for item in students
    ):
        raise HTTPException(400, "Um ou mais estudantes nao foram encontrados ou estao inativos.")
    normalized_reason_ids = _normalize_ids(reason_ids, "motivo")
    reasons = catalog_repository.get_reasons(normalized_reason_ids)
    if len(reasons) != len(normalized_reason_ids) or any(
        not bool(item.get("active")) for item in reasons
    ):
        raise HTTPException(400, "Um ou mais motivos nao foram encontrados ou estao inativos.")
    contact = str(responsible_contact or "").strip()
    if contact not in RESPONSIBLE_CONTACTS:
        raise HTTPException(400, "Opcao de contato com responsavel invalida.")
    occurred_at = datetime.now()
    class_context = _resolve_class_context(
        _user_id(user),
        students,
        occurred_at,
    )
    return repository.create_pre_registration(
        student_ids=normalized_student_ids,
        reason_ids=normalized_reason_ids,
        professor_id=_user_id(user),
        responsible_contact=contact,
        discipline=class_context["discipline"],
        lesson=class_context["lesson"],
        occurred_at=occurred_at.strftime("%Y-%m-%d %H:%M:%S"),
    )


def _normalize_ids(values: list[int], label: str) -> list[int]:
    normalized = []
    for value in values or []:
        try:
            item_id = int(value)
        except (TypeError, ValueError):
            continue
        if item_id > 0 and item_id not in normalized:
            normalized.append(item_id)
    if not normalized:
        raise HTTPException(400, f"Selecione pelo menos um {label}.")
    return normalized


def _estimated_lesson(turn: str, moment: datetime) -> int:
    start_hour = 13 if str(turn or "").upper().startswith("VESPERTINO") else 7
    elapsed_minutes = (moment.hour * 60 + moment.minute) - start_hour * 60
    return max(1, min(12, elapsed_minutes // 50 + 1))


def _resolve_class_context(
    professor_id: int,
    students: list[dict],
    moment: datetime,
) -> dict:
    schedules = catalog_repository.list_teacher_schedule(
        professor_id,
        year=moment.year,
        weekday=WEEKDAYS[moment.weekday()],
        class_ids=[int(item.get("turma_id") or 0) for item in students],
    )
    if not schedules:
        return {"discipline": "", "lesson": ""}
    if len(schedules) == 1:
        selected = schedules[0]
    else:
        selected = min(
            schedules,
            key=lambda item: abs(
                int(item.get("aula_numero") or 0)
                - _estimated_lesson(item.get("turno", ""), moment)
            ),
        )
    return {
        "discipline": str(selected.get("disciplina_nome") or "").strip(),
        "lesson": str(selected.get("aula_numero") or "").strip(),
    }


def list_pre_registrations(user: dict, status: str | None = None) -> list[dict]:
    require_occurrences_access(user)
    professor_id = None if usuario_eh_gestor(user) else _user_id(user)
    clean_status = str(status or "").strip() or None
    if clean_status and clean_status not in {"pending", "completed", "cancelled"}:
        raise HTTPException(400, "Status de pre-registro invalido.")
    return repository.list_pre_registrations(
        professor_id=professor_id,
        status=clean_status,
    )


def validate_pre_registration_completion(
    user: dict,
    pre_registration_id: int,
    student_ids: list[int],
) -> dict:
    require_manager(user)
    current = repository.get_pre_registration(pre_registration_id)
    if not current:
        raise HTTPException(404, "Pre-registro nao encontrado.")
    if current["status"] != "pending":
        raise HTTPException(409, "Este pre-registro nao esta pendente.")
    expected_ids = {int(item) for item in current.get("student_ids") or []}
    received_ids = {int(item) for item in student_ids or [] if int(item) > 0}
    if received_ids != expected_ids:
        raise HTTPException(
            400,
            "A ocorrencia deve pertencer ao mesmo estudante do pre-registro.",
        )
    return current


def complete_pre_registration(
    user: dict,
    pre_registration_id: int,
    occurrence_id: int,
) -> dict:
    require_manager(user)
    current = repository.get_pre_registration(pre_registration_id)
    if not current:
        raise HTTPException(404, "Pre-registro nao encontrado.")
    if current["status"] == "completed":
        if int(current.get("occurrence_id") or 0) == int(occurrence_id):
            return current
        raise HTTPException(409, "Este pre-registro ja foi concluido.")
    occurrence = repository.get_occurrence(occurrence_id)
    if not occurrence:
        raise HTTPException(400, "Ocorrencia informada nao foi encontrada.")
    if set(occurrence.get("student_ids") or []) != set(current.get("student_ids") or []):
        raise HTTPException(
            400,
            "A ocorrencia deve pertencer ao mesmo estudante do pre-registro.",
        )
    completed = repository.complete_pre_registration(pre_registration_id, occurrence_id)
    if not completed:
        raise HTTPException(400, "Ocorrencia informada nao foi encontrada.")
    return completed
