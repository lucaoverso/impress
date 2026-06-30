from fastapi import APIRouter, Depends, Query

from auth import get_usuario_logado

from . import service
from .schemas import FollowupRecordCreate


router = APIRouter(prefix="/teacher-followup", tags=["teacher-followup"])


@router.get("/teachers")
def list_teachers(
    q: str = Query(default=""),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    user=Depends(get_usuario_logado),
):
    return service.list_teachers(user, q=q, date_from=date_from, date_to=date_to)


@router.get("/teachers/search")
def search_teachers(
    q: str = Query(default=""),
    user=Depends(get_usuario_logado),
):
    return service.search_teachers(user, q=q)


@router.get("/teachers/{teacher_id}")
def get_teacher_profile(
    teacher_id: int,
    type: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    user=Depends(get_usuario_logado),
):
    return service.get_profile(
        user,
        teacher_id=teacher_id,
        record_type=type,
        date_from=date_from,
        date_to=date_to,
    )


@router.post("/records")
def create_record(
    payload: FollowupRecordCreate,
    user=Depends(get_usuario_logado),
):
    return service.create_record(user, payload)
