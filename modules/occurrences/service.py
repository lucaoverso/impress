from fastapi import HTTPException

from routers.common import usuario_eh_gestor, usuario_eh_professor

from . import repository


RESPONSIBLE_CONTACTS = {"none", "communicate", "summon"}


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
        "reasons": repository.list_reasons(include_inactive=manager),
    }


def search_students(user: dict, term: str, limit: int) -> list[dict]:
    require_occurrences_access(user)
    clean_term = str(term or "").strip()
    safe_limit = min(max(int(limit or 20), 1), 50)
    students = repository.search_students(clean_term, safe_limit)
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
        return repository.create_reason(clean_name)
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
        reason = repository.update_reason(reason_id, name=clean_name, active=active)
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
    student_id: int,
    reason_id: int,
    responsible_contact: str,
) -> dict:
    if not usuario_eh_professor(user):
        raise HTTPException(403, "Apenas professores podem criar pre-registros.")
    student = repository.get_student(student_id)
    if not student or not bool(student.get("ativo")):
        raise HTTPException(400, "Estudante nao encontrado ou inativo.")
    reason = repository.get_reason(reason_id)
    if not reason or not bool(reason.get("active")):
        raise HTTPException(400, "Motivo nao encontrado ou inativo.")
    contact = str(responsible_contact or "").strip()
    if contact not in RESPONSIBLE_CONTACTS:
        raise HTTPException(400, "Opcao de contato com responsavel invalida.")
    return repository.create_pre_registration(
        student_id=int(student_id),
        reason_id=int(reason_id),
        professor_id=_user_id(user),
        responsible_contact=contact,
    )


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
    student_id: int | None,
) -> dict:
    require_manager(user)
    current = repository.get_pre_registration(pre_registration_id)
    if not current:
        raise HTTPException(404, "Pre-registro nao encontrado.")
    if current["status"] != "pending":
        raise HTTPException(409, "Este pre-registro nao esta pendente.")
    if int(student_id or 0) != int(current["student_id"]):
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
    if int(occurrence.get("estudante_id") or 0) != int(current["student_id"]):
        raise HTTPException(
            400,
            "A ocorrencia deve pertencer ao mesmo estudante do pre-registro.",
        )
    completed = repository.complete_pre_registration(pre_registration_id, occurrence_id)
    if not completed:
        raise HTTPException(400, "Ocorrencia informada nao foi encontrada.")
    return completed
