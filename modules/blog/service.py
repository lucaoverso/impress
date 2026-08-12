import re
import sqlite3
import unicodedata
from html.parser import HTMLParser

from . import repository
from .models import BlogPostStatus
from .schemas import BlogImageCreateIn, BlogImageUpdateIn, BlogPostCreateIn, BlogPostUpdateIn


class BlogNotFoundError(ValueError):
    pass


class BlogConflictError(ValueError):
    pass


class BlogValidationError(ValueError):
    pass


class _VisibleTextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _clean_line(value) -> str:
    return " ".join(str(value or "").strip().split())


def _visible_text(value: str) -> str:
    parser = _VisibleTextParser()
    parser.feed(str(value or ""))
    parser.close()
    return _clean_line(" ".join(parser.parts))


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", _clean_line(value))
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")
    return slug[:180].rstrip("-") or "artigo"


def _unique_slug(title: str, *, exclude_post_id: int | None = None) -> str:
    base = slugify(title)
    candidate = base
    suffix = 2
    while repository.slug_exists(candidate, exclude_post_id=exclude_post_id):
        marker = f"-{suffix}"
        candidate = f"{base[: 180 - len(marker)].rstrip('-')}{marker}"
        suffix += 1
    return candidate


def _post_values(payload: BlogPostCreateIn | BlogPostUpdateIn) -> dict:
    title = _clean_line(payload.title)
    summary = _clean_line(payload.summary)
    body_html = str(payload.body_html or "").strip()
    if not title:
        raise BlogValidationError("Informe o titulo do artigo.")
    if len(title) > 180:
        raise BlogValidationError("O titulo deve ter no maximo 180 caracteres.")
    if len(summary) > 500:
        raise BlogValidationError("O resumo deve ter no maximo 500 caracteres.")
    if len(body_html) > 200_000:
        raise BlogValidationError("O conteudo do artigo excede o limite permitido.")
    return {"title": title, "summary": summary, "body_html": body_html}


def create_post(*, author_user_id: int, payload: BlogPostCreateIn) -> dict:
    if int(author_user_id or 0) <= 0:
        raise BlogValidationError("Autor invalido.")
    values = _post_values(payload)
    values["slug"] = _unique_slug(values["title"])
    try:
        return repository.create_post(author_user_id=int(author_user_id), **values)
    except sqlite3.IntegrityError as exc:
        raise BlogConflictError("Nao foi possivel criar o artigo com este identificador.") from exc


def get_post(post_id: int) -> dict:
    post = repository.get_post_by_id(post_id)
    if not post:
        raise BlogNotFoundError("Artigo nao encontrado.")
    return post


def list_posts(*, status: BlogPostStatus | None = None, limit: int = 50, offset: int = 0):
    return repository.list_posts(
        status=status.value if status else None,
        limit=min(100, max(1, int(limit))),
        offset=max(0, int(offset)),
    )


def update_post(post_id: int, payload: BlogPostUpdateIn) -> dict:
    current = get_post(post_id)
    values = _post_values(payload)
    if current.get("published_at"):
        values["slug"] = current["slug"]
    else:
        values["slug"] = _unique_slug(values["title"], exclude_post_id=int(post_id))
    try:
        updated = repository.update_post(int(post_id), **values)
    except sqlite3.IntegrityError as exc:
        raise BlogConflictError("Ja existe um artigo com este identificador.") from exc
    if not updated:
        raise BlogNotFoundError("Artigo nao encontrado.")
    return updated


def _validate_for_publication(post: dict) -> None:
    if not _clean_line(post.get("summary")):
        raise BlogValidationError("Informe o resumo antes de publicar.")
    if not _visible_text(post.get("body_html", "")):
        raise BlogValidationError("Informe o conteudo antes de publicar.")
    images = repository.list_images(int(post["id"]))
    if not any(bool(image.get("is_cover")) for image in images):
        raise BlogValidationError("Defina uma imagem de capa antes de publicar.")
    if any(not _clean_line(image.get("alt_text")) for image in images):
        raise BlogValidationError("Informe o texto alternativo de todas as imagens.")


def publish_post(post_id: int) -> dict:
    post = get_post(post_id)
    _validate_for_publication(post)
    return repository.set_post_status(int(post_id), BlogPostStatus.PUBLISHED.value) or post


def unpublish_post(post_id: int) -> dict:
    get_post(post_id)
    return repository.set_post_status(int(post_id), BlogPostStatus.DRAFT.value) or get_post(post_id)


def archive_post(post_id: int) -> dict:
    get_post(post_id)
    return repository.set_post_status(int(post_id), BlogPostStatus.ARCHIVED.value) or get_post(
        post_id
    )


def restore_post(post_id: int) -> dict:
    post = get_post(post_id)
    if post["status"] != BlogPostStatus.ARCHIVED.value:
        raise BlogValidationError("Somente artigos arquivados podem ser restaurados.")
    return repository.set_post_status(int(post_id), BlogPostStatus.DRAFT.value) or post


def add_image(post_id: int, payload: BlogImageCreateIn) -> dict:
    get_post(post_id)
    values = payload.model_dump()
    for key in ("token", "stored_name", "thumbnail_name", "alt_text", "caption"):
        values[key] = str(values.get(key) or "").strip()
    if not values["token"] or not values["stored_name"]:
        raise BlogValidationError("Dados da imagem invalidos.")
    try:
        return repository.create_image(int(post_id), values)
    except sqlite3.IntegrityError as exc:
        raise BlogConflictError("Esta imagem ja foi vinculada a um artigo.") from exc


def update_image(image_id: int, payload: BlogImageUpdateIn) -> dict:
    updated = repository.update_image(
        int(image_id), alt_text=_clean_line(payload.alt_text), caption=_clean_line(payload.caption)
    )
    if not updated:
        raise BlogNotFoundError("Imagem nao encontrada.")
    return updated


def set_cover_image(post_id: int, image_id: int) -> dict:
    get_post(post_id)
    image = repository.set_cover_image(int(post_id), int(image_id))
    if not image:
        raise BlogNotFoundError("Imagem nao encontrada neste artigo.")
    return image


def remove_image(post_id: int, image_id: int) -> dict:
    image = repository.get_image(image_id)
    if not image or int(image["post_id"]) != int(post_id):
        raise BlogNotFoundError("Imagem nao encontrada neste artigo.")
    return repository.delete_image(image_id) or image


def list_public_posts(*, limit: int = 20, offset: int = 0) -> list[dict]:
    return repository.list_public_posts(
        limit=min(50, max(1, int(limit))), offset=max(0, int(offset))
    )


def get_public_post(slug: str) -> dict:
    post = repository.get_public_post_by_slug(slugify(slug))
    if not post:
        raise BlogNotFoundError("Artigo nao encontrado.")
    return post
