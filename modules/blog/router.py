from collections.abc import Callable
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse

from auth import get_usuario_logado
from routers.common import exigir_admin

from . import image_service, service
from .models import BlogPostStatus
from .schemas import (
    BlogImageOut,
    BlogImageUpdateIn,
    BlogPostCreateIn,
    BlogPostDetailsOut,
    BlogPostOut,
    BlogPostUpdateIn,
)

router = APIRouter(prefix="/api/admin/blog", tags=["Blog administrativo"])


def require_blog_admin(user=Depends(get_usuario_logado)) -> dict:
    return exigir_admin(user)


def _run(action: Callable[..., Any], *args, **kwargs):
    try:
        return action(*args, **kwargs)
    except service.BlogNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except service.BlogConflictError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except service.BlogValidationError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


@router.get("/posts", response_model=list[BlogPostOut])
def list_blog_posts(
    post_status: BlogPostStatus | None = Query(default=None, alias="status"),
    limit: int = 50,
    offset: int = 0,
    user=Depends(require_blog_admin),
):
    return _run(service.list_posts, status=post_status, limit=limit, offset=offset)


@router.post("/posts", response_model=BlogPostOut, status_code=status.HTTP_201_CREATED)
def create_blog_post(payload: BlogPostCreateIn, user=Depends(require_blog_admin)):
    return _run(service.create_post, author_user_id=int(user.get("id") or 0), payload=payload)


@router.get("/posts/{post_id}", response_model=BlogPostDetailsOut)
def get_blog_post(post_id: int, user=Depends(require_blog_admin)):
    return _run(service.get_post_details, post_id)


@router.put("/posts/{post_id}", response_model=BlogPostOut)
def update_blog_post(
    post_id: int,
    payload: BlogPostUpdateIn,
    user=Depends(require_blog_admin),
):
    return _run(service.update_post, post_id, payload)


@router.post("/posts/{post_id}/publish", response_model=BlogPostOut)
def publish_blog_post(post_id: int, user=Depends(require_blog_admin)):
    return _run(service.publish_post, post_id)


@router.post("/posts/{post_id}/unpublish", response_model=BlogPostOut)
def unpublish_blog_post(post_id: int, user=Depends(require_blog_admin)):
    return _run(service.unpublish_post, post_id)


@router.post("/posts/{post_id}/archive", response_model=BlogPostOut)
def archive_blog_post(post_id: int, user=Depends(require_blog_admin)):
    return _run(service.archive_post, post_id)


@router.post("/posts/{post_id}/restore", response_model=BlogPostOut)
def restore_blog_post(post_id: int, user=Depends(require_blog_admin)):
    return _run(service.restore_post, post_id)


@router.post(
    "/posts/{post_id}/images",
    response_model=BlogImageOut,
    status_code=status.HTTP_201_CREATED,
)
def upload_blog_image(
    post_id: int,
    file: UploadFile = File(...),
    alt_text: str = Form(default="", max_length=180),
    caption: str = Form(default="", max_length=500),
    is_cover: bool = Form(default=False),
    user=Depends(require_blog_admin),
):
    content = file.file.read(image_service.MAX_IMAGE_BYTES + 1)
    return _run(
        service.upload_image,
        post_id,
        content=content,
        content_type=file.content_type or "",
        original_filename=file.filename or "",
        alt_text=alt_text,
        caption=caption,
        is_cover=is_cover,
    )


@router.patch("/posts/{post_id}/images/{image_id}", response_model=BlogImageOut)
def update_blog_image(
    post_id: int,
    image_id: int,
    payload: BlogImageUpdateIn,
    user=Depends(require_blog_admin),
):
    return _run(service.update_image, post_id, image_id, payload)


@router.put("/posts/{post_id}/cover/{image_id}", response_model=BlogImageOut)
def set_blog_cover(post_id: int, image_id: int, user=Depends(require_blog_admin)):
    return _run(service.set_cover_image, post_id, image_id)


@router.delete(
    "/posts/{post_id}/images/{image_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_blog_image(post_id: int, image_id: int, user=Depends(require_blog_admin)):
    _run(service.remove_image, post_id, image_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/images/{token}", response_class=FileResponse)
def get_blog_image(
    token: str,
    thumbnail: bool = False,
    user=Depends(require_blog_admin),
):
    resolved = _run(service.resolve_image, token, public=False, thumbnail=thumbnail)
    return FileResponse(
        resolved["path"],
        media_type=resolved["media_type"],
        headers={"Cache-Control": "private, no-store"},
    )
