import re
import sqlite3
import unicodedata
from html.parser import HTMLParser
from pathlib import Path

from . import image_service, repository
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


def get_post_details(post_id: int) -> dict:
    post = get_post(post_id)
    return {**post, "images": repository.list_images(int(post_id))}


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


def _validate_for_publication(post: dict, *, image_dir: Path | None = None) -> None:
    if not _clean_line(post.get("summary")):
        raise BlogValidationError("Informe o resumo antes de publicar.")
    if not _visible_text(post.get("body_html", "")):
        raise BlogValidationError("Informe o conteudo antes de publicar.")
    images = repository.list_images(int(post["id"]))
    if not any(bool(image.get("is_cover")) for image in images):
        raise BlogValidationError("Defina uma imagem de capa antes de publicar.")
    if any(not _clean_line(image.get("alt_text")) for image in images):
        raise BlogValidationError("Informe o texto alternativo de todas as imagens.")
    for image in images:
        stored = image_service.resolve_blog_image(
            str(image.get("stored_name") or ""), image_dir=image_dir
        )
        thumbnail = image_service.resolve_blog_image(
            str(image.get("thumbnail_name") or ""), image_dir=image_dir
        )
        if stored is None or thumbnail is None:
            raise BlogValidationError("Uma ou mais imagens do artigo nao estao disponiveis.")


def publish_post(post_id: int, *, image_dir: Path | None = None) -> dict:
    post = get_post(post_id)
    _validate_for_publication(post, image_dir=image_dir)
    return repository.set_post_status(int(post_id), BlogPostStatus.PUBLISHED.value) or post


def unpublish_post(post_id: int) -> dict:
    get_post(post_id)
    return repository.set_post_status(int(post_id), BlogPostStatus.DRAFT.value) or get_post(post_id)


def archive_post(post_id: int) -> dict:
    post = get_post(post_id)
    return repository.set_post_status(int(post_id), BlogPostStatus.ARCHIVED.value) or post


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


def upload_image(
    post_id: int,
    *,
    content: bytes,
    content_type: str = "",
    original_filename: str = "",
    alt_text: str = "",
    caption: str = "",
    is_cover: bool = False,
    image_dir: Path | None = None,
) -> dict:
    get_post(post_id)
    if len(repository.list_images(int(post_id))) >= 20:
        raise BlogValidationError("O artigo pode conter no maximo 20 imagens.")
    try:
        stored = image_service.store_blog_image(
            content,
            content_type=content_type,
            original_filename=original_filename,
            image_dir=image_dir,
        )
    except image_service.BlogImageValidationError as exc:
        raise BlogValidationError(str(exc)) from exc

    try:
        return add_image(
            int(post_id),
            BlogImageCreateIn(
                token=stored["token"],
                stored_name=stored["stored_name"],
                thumbnail_name=stored["thumbnail_name"],
                alt_text=_clean_line(alt_text),
                caption=_clean_line(caption),
                width=stored["width"],
                height=stored["height"],
                is_cover=is_cover,
            ),
        )
    except Exception:
        try:
            image_service.delete_blog_image_files(
                stored["stored_name"], stored["thumbnail_name"], image_dir=image_dir
            )
        except OSError:
            pass
        raise


def update_image(post_id: int, image_id: int, payload: BlogImageUpdateIn) -> dict:
    image = repository.get_image(image_id)
    if not image or int(image["post_id"]) != int(post_id):
        raise BlogNotFoundError("Imagem nao encontrada neste artigo.")
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


def remove_image(post_id: int, image_id: int, *, image_dir: Path | None = None) -> dict:
    image = repository.get_image(image_id)
    if not image or int(image["post_id"]) != int(post_id):
        raise BlogNotFoundError("Imagem nao encontrada neste artigo.")
    removed = repository.delete_image(image_id) or image
    image_service.delete_blog_image_files(
        removed["stored_name"], removed.get("thumbnail_name", ""), image_dir=image_dir
    )
    return removed


def resolve_image(
    token: str,
    *,
    public: bool,
    thumbnail: bool = False,
    image_dir: Path | None = None,
) -> dict:
    normalized_token = str(token or "").strip().lower()
    image = (
        repository.get_public_image_by_token(normalized_token)
        if public
        else repository.get_image_by_token(normalized_token)
    )
    if not image:
        raise BlogNotFoundError("Imagem nao encontrada.")
    filename = image.get("thumbnail_name") if thumbnail else image.get("stored_name")
    if thumbnail and not filename:
        filename = image.get("stored_name")
    path = image_service.resolve_blog_image(str(filename or ""), image_dir=image_dir)
    if path is None:
        raise BlogNotFoundError("Imagem nao encontrada.")
    return {
        "path": path,
        "filename": path.name,
        "media_type": "image/webp",
        "image": image,
    }


def list_public_posts(*, limit: int = 20, offset: int = 0) -> list[dict]:
    return repository.list_public_posts(
        limit=min(50, max(1, int(limit))), offset=max(0, int(offset))
    )


def get_public_post(slug: str) -> dict:
    post = repository.get_public_post_by_slug(slugify(slug))
    if not post:
        raise BlogNotFoundError("Artigo nao encontrado.")
    return post
