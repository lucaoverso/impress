import re
import sqlite3
from pathlib import Path
from uuid import uuid4

from . import repository
from .schemas import RecursoCreateIn, RecursoUpdateIn

IMAGE_EXTENSIONS = {".jpg": ".jpg", ".jpeg": ".jpg", ".png": ".png", ".webp": ".webp"}
IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
IMAGE_MAX_BYTES = 5 * 1024 * 1024


class ResourceConflictError(Exception):
    pass


class ResourceNotFoundError(Exception):
    pass


def list_resources(include_inactive: bool):
    return repository.listar_recursos(incluir_inativos=include_inactive)


def _resource_data(payload: RecursoCreateIn | RecursoUpdateIn) -> dict:
    data = {
        "nome": payload.nome.strip(),
        "tipo": payload.tipo.strip(),
        "descricao": (payload.descricao or "").strip(),
        "quantidade_itens": int(payload.quantidade_itens),
        "imagem_capa": str(payload.imagem_capa or "").strip(),
    }
    if not data["nome"]:
        raise ValueError("Nome do recurso é obrigatório.")
    if not data["tipo"]:
        raise ValueError("Tipo do recurso é obrigatório.")
    if data["quantidade_itens"] < 1:
        raise ValueError("Quantidade de itens deve ser no mínimo 1.")
    return data


def create_resource(payload: RecursoCreateIn) -> int:
    try:
        return repository.criar_recurso(**_resource_data(payload))
    except sqlite3.IntegrityError as exc:
        raise ResourceConflictError("Já existe um recurso com este nome.") from exc


def update_resource(resource_id: int, payload: RecursoUpdateIn) -> None:
    try:
        changed = repository.atualizar_recurso_dados(recurso_id=resource_id, **_resource_data(payload))
    except sqlite3.IntegrityError as exc:
        raise ResourceConflictError("Já existe um recurso com este nome.") from exc
    if not changed:
        raise ResourceNotFoundError("Recurso não encontrado.")


def update_resource_status(resource_id: int, active: bool) -> None:
    if not repository.atualizar_status_recurso(resource_id, active):
        raise ResourceNotFoundError("Recurso não encontrado.")


def save_resource_image(filename: str, content_type: str, content: bytes, image_dir: Path) -> str:
    if not filename:
        raise ValueError("Imagem não enviada.")
    if content_type not in IMAGE_MIME_TYPES:
        raise ValueError("Use uma imagem JPG, PNG ou WEBP.")
    if not content:
        raise ValueError("A imagem enviada está vazia.")
    if len(content) > IMAGE_MAX_BYTES:
        raise ValueError("A imagem deve ter no máximo 5 MB.")

    clean_name = Path(filename).name
    extension = IMAGE_EXTENSIONS.get(Path(clean_name).suffix.lower())
    if not extension:
        raise ValueError("Use uma imagem JPG, PNG ou WEBP.")
    stem = re.sub(r"[^a-z0-9]+", "-", Path(clean_name).stem.lower()).strip("-") or "recurso"
    saved_name = f"{stem}-{uuid4().hex[:10]}{extension}"
    image_dir.mkdir(parents=True, exist_ok=True)
    (image_dir / saved_name).write_bytes(content)
    return f"/static/img/resources/{saved_name}"
