from fastapi import APIRouter, Depends, Query

from auth import get_usuario_logado

from . import service
from .schemas import (
    FollowupCriterionCreate,
    FollowupCriterionUpdate,
    FollowupDimensionCreate,
    FollowupModelCreate,
    FollowupRecordCreate,
)


router = APIRouter(prefix="/teacher-followup", tags=["teacher-followup"])


@router.get("/catalog")
def get_catalog(user=Depends(get_usuario_logado)):
    return service.catalog(user)


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


@router.post("/dimensions")
def create_dimension(
    payload: FollowupDimensionCreate,
    user=Depends(get_usuario_logado),
):
    return service.create_dimension(user, payload)


@router.post("/criteria")
def create_criterion(
    payload: FollowupCriterionCreate,
    user=Depends(get_usuario_logado),
):
    return service.create_criterion(user, payload)


@router.patch("/criteria/{criterion_id}")
def update_criterion(
    criterion_id: int,
    payload: FollowupCriterionUpdate,
    user=Depends(get_usuario_logado),
):
    return service.update_criterion(user, criterion_id, payload)


@router.post("/models")
def create_model(
    payload: FollowupModelCreate,
    user=Depends(get_usuario_logado),
):
    return service.create_model(user, payload)
