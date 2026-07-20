from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from auth import get_usuario_logado
from routers.common import exigir_gestor
from routers.config import STATIC_DIR

from . import service
from .schemas import RecursoCreateIn, RecursoStatusIn, RecursoUpdateIn

router = APIRouter()
IMAGE_DIR = Path(STATIC_DIR) / "img" / "resources"


def _raise_http_error(exc: Exception):
    if isinstance(exc, service.ResourceConflictError):
        raise HTTPException(409, str(exc)) from exc
    if isinstance(exc, service.ResourceNotFoundError):
        raise HTTPException(404, str(exc)) from exc
    raise HTTPException(400, str(exc)) from exc


@router.get("/admin/recursos/dados")
def listar_recursos_admin_api(
    incluir_inativos: bool = True,
    usuario=Depends(get_usuario_logado),
):
    exigir_gestor(usuario)
    return service.list_resources(incluir_inativos)


@router.post("/admin/recursos/upload-imagem")
def upload_imagem_recurso_admin(
    arquivo: UploadFile = File(...),
    usuario=Depends(get_usuario_logado),
):
    exigir_gestor(usuario)
    try:
        image_path = service.save_resource_image(
            arquivo.filename or "",
            arquivo.content_type or "",
            arquivo.file.read(),
            IMAGE_DIR,
        )
    except ValueError as exc:
        _raise_http_error(exc)
    return {"mensagem": "Imagem enviada com sucesso.", "imagem_capa": image_path}


@router.post("/admin/recursos")
def criar_recurso_admin(payload: RecursoCreateIn, usuario=Depends(get_usuario_logado)):
    exigir_gestor(usuario)
    try:
        resource_id = service.create_resource(payload)
    except (ValueError, service.ResourceConflictError) as exc:
        _raise_http_error(exc)
    return {"mensagem": "Recurso criado com sucesso.", "recurso_id": resource_id}


@router.put("/admin/recursos/{recurso_id}")
def atualizar_recurso_admin(
    recurso_id: int,
    payload: RecursoUpdateIn,
    usuario=Depends(get_usuario_logado),
):
    exigir_gestor(usuario)
    try:
        service.update_resource(recurso_id, payload)
    except (ValueError, service.ResourceConflictError, service.ResourceNotFoundError) as exc:
        _raise_http_error(exc)
    return {"mensagem": "Recurso atualizado com sucesso."}


@router.put("/admin/recursos/{recurso_id}/status")
def atualizar_status_recurso_admin(
    recurso_id: int,
    payload: RecursoStatusIn,
    usuario=Depends(get_usuario_logado),
):
    exigir_gestor(usuario)
    try:
        service.update_resource_status(recurso_id, payload.ativo)
    except service.ResourceNotFoundError as exc:
        _raise_http_error(exc)
    return {"mensagem": "Status do recurso atualizado com sucesso."}
