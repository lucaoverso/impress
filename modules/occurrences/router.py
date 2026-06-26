from fastapi import APIRouter, Depends, Query

from auth import get_usuario_logado

from . import service
from .schemas import (
    PreRegistrationComplete,
    PreRegistrationCreate,
    ReasonCreate,
    ReasonUpdate,
)


router = APIRouter(prefix="/occurrences", tags=["occurrences"])


@router.get("/context")
def get_context(user=Depends(get_usuario_logado)):
    return service.context(user)


@router.get("/students")
def get_students(
    q: str = Query(default=""),
    limit: int = Query(default=20),
    user=Depends(get_usuario_logado),
):
    return service.search_students(user, q, limit)


@router.get("/reasons")
def get_reasons(user=Depends(get_usuario_logado)):
    context = service.context(user)
    return context["reasons"]


@router.post("/reasons")
def post_reason(payload: ReasonCreate, user=Depends(get_usuario_logado)):
    return service.create_reason(user, payload.name)


@router.patch("/reasons/{reason_id}")
def patch_reason(
    reason_id: int,
    payload: ReasonUpdate,
    user=Depends(get_usuario_logado),
):
    return service.update_reason(
        user,
        reason_id,
        name=payload.name,
        active=payload.active,
    )


@router.get("/pre-registrations")
def get_pre_registrations(
    status: str | None = Query(default=None),
    user=Depends(get_usuario_logado),
):
    return service.list_pre_registrations(user, status)


@router.post("/pre-registrations")
def post_pre_registration(
    payload: PreRegistrationCreate,
    user=Depends(get_usuario_logado),
):
    return service.create_pre_registration(
        user,
        student_ids=payload.student_ids,
        reason_ids=payload.reason_ids,
        responsible_contact=payload.responsible_contact,
        discipline=payload.discipline,
        complementary_report=payload.complementary_report,
    )


@router.post("/pre-registrations/{pre_registration_id}/complete")
def complete_pre_registration(
    pre_registration_id: int,
    payload: PreRegistrationComplete,
    user=Depends(get_usuario_logado),
):
    return service.complete_pre_registration(
        user,
        pre_registration_id,
        payload.occurrence_id,
    )


@router.delete("/pre-registrations/{pre_registration_id}")
def delete_pre_registration(
    pre_registration_id: int,
    user=Depends(get_usuario_logado),
):
    return service.cancel_pre_registration(user, pre_registration_id)
