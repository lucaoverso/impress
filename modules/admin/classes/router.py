from fastapi import APIRouter, Depends, HTTPException

from auth import get_usuario_logado
from routers.common import exigir_gestor

from . import service
from .schemas import TurmaCreateIn, TurmaStatusIn, TurmaUpdateIn

router = APIRouter()


def _raise_http_error(exc: Exception):
    if isinstance(exc, service.ClassConflictError):
        raise HTTPException(409, str(exc)) from exc
    if isinstance(exc, service.ClassNotFoundError):
        raise HTTPException(404, str(exc)) from exc
    raise HTTPException(400, str(exc)) from exc


@router.get("/admin/turmas/dados")
def listar_turmas_admin_api(
    incluir_inativas: bool = True,
    usuario=Depends(get_usuario_logado),
):
    exigir_gestor(usuario)
    return service.list_classes(incluir_inativas)


@router.post("/admin/turmas")
def criar_turma_admin(payload: TurmaCreateIn, usuario=Depends(get_usuario_logado)):
    exigir_gestor(usuario)
    try:
        turma_id = service.create_class(payload)
    except (ValueError, service.ClassConflictError) as exc:
        _raise_http_error(exc)
    return {"mensagem": "Turma cadastrada com sucesso.", "turma_id": turma_id}


@router.put("/admin/turmas/{turma_id}")
def atualizar_turma_admin(
    turma_id: int,
    payload: TurmaUpdateIn,
    usuario=Depends(get_usuario_logado),
):
    exigir_gestor(usuario)
    try:
        service.update_class(turma_id, payload)
    except (ValueError, service.ClassNotFoundError) as exc:
        _raise_http_error(exc)
    return {"mensagem": "Dados da turma atualizados com sucesso."}


@router.put("/admin/turmas/{turma_id}/status")
def atualizar_status_turma_admin(
    turma_id: int,
    payload: TurmaStatusIn,
    usuario=Depends(get_usuario_logado),
):
    exigir_gestor(usuario)
    try:
        service.update_class_status(turma_id, payload.ativo)
    except service.ClassNotFoundError as exc:
        _raise_http_error(exc)
    return {"mensagem": "Status da turma atualizado com sucesso."}
