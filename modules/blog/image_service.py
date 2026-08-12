import io
import re
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageOps, UnidentifiedImageError

from .config import BLOG_IMAGE_DIR


MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_IMAGE_DIMENSION = 2400
THUMBNAIL_DIMENSION = 720
MAX_SOURCE_PIXELS = 30_000_000
ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
STORED_IMAGE_RE = re.compile(r"^[a-f0-9]{32}(?:-thumb)?\.webp$")


class BlogImageValidationError(ValueError):
    pass


def blog_image_directory(image_dir: Path | None = None) -> Path:
    if image_dir is None:
        image_dir = BLOG_IMAGE_DIR
    directory = Path(image_dir).expanduser()
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _save_webp(image: Image.Image, destination: Path, *, quality: int) -> None:
    temporary = destination.with_name(f".{destination.stem}-{uuid4().hex}.tmp")
    try:
        image.save(temporary, format="WEBP", quality=quality, method=6)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def _normalized_image(content: bytes) -> Image.Image:
    try:
        with Image.open(io.BytesIO(content)) as source:
            if source.format not in ALLOWED_IMAGE_FORMATS:
                raise BlogImageValidationError("Use uma imagem JPG, PNG ou WEBP.")
            if source.width * source.height > MAX_SOURCE_PIXELS:
                raise BlogImageValidationError("A imagem possui dimensoes maiores que o permitido.")
            source.verify()

        with Image.open(io.BytesIO(content)) as source:
            source.seek(0)
            normalized = ImageOps.exif_transpose(source).copy()
    except BlogImageValidationError:
        raise
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError, ValueError) as exc:
        raise BlogImageValidationError("O arquivo enviado nao e uma imagem valida.") from exc

    has_alpha = normalized.mode in {"RGBA", "LA"} or "transparency" in normalized.info
    return normalized.convert("RGBA" if has_alpha else "RGB")


def store_blog_image(
    content: bytes,
    *,
    content_type: str = "",
    original_filename: str = "",
    image_dir: Path | None = None,
) -> dict:
    if not content:
        raise BlogImageValidationError("Selecione uma imagem.")
    if len(content) > MAX_IMAGE_BYTES:
        raise BlogImageValidationError("A imagem deve ter no maximo 8 MB.")
    normalized_type = str(content_type or "").strip().lower()
    if normalized_type and normalized_type not in ALLOWED_MIME_TYPES:
        raise BlogImageValidationError("Use uma imagem JPG, PNG ou WEBP.")

    image = _normalized_image(content)
    image.thumbnail(
        (MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION),
        Image.Resampling.LANCZOS,
    )
    thumbnail = image.copy()
    thumbnail.thumbnail(
        (THUMBNAIL_DIMENSION, THUMBNAIL_DIMENSION),
        Image.Resampling.LANCZOS,
    )

    token = uuid4().hex
    stored_name = f"{token}.webp"
    thumbnail_name = f"{token}-thumb.webp"
    directory = blog_image_directory(image_dir)
    stored_path = directory / stored_name
    thumbnail_path = directory / thumbnail_name
    try:
        _save_webp(image, stored_path, quality=88)
        _save_webp(thumbnail, thumbnail_path, quality=82)
    except (OSError, ValueError) as exc:
        stored_path.unlink(missing_ok=True)
        thumbnail_path.unlink(missing_ok=True)
        raise BlogImageValidationError("Nao foi possivel armazenar a imagem.") from exc

    return {
        "token": token,
        "stored_name": stored_name,
        "thumbnail_name": thumbnail_name,
        "width": int(image.width),
        "height": int(image.height),
        "media_type": "image/webp",
        "original_filename": Path(str(original_filename or "")).name[:255],
    }


def resolve_blog_image(filename: str, *, image_dir: Path | None = None) -> Path | None:
    safe_name = str(filename or "").strip().lower()
    if not STORED_IMAGE_RE.fullmatch(safe_name):
        return None
    path = blog_image_directory(image_dir) / safe_name
    return path if path.is_file() else None


def delete_blog_image_files(
    stored_name: str,
    thumbnail_name: str = "",
    *,
    image_dir: Path | None = None,
) -> list[Path]:
    directory = blog_image_directory(image_dir)
    deleted = []
    for filename in {str(stored_name or ""), str(thumbnail_name or "")}:
        safe_name = filename.strip().lower()
        if not STORED_IMAGE_RE.fullmatch(safe_name):
            continue
        path = directory / safe_name
        if path.is_file():
            path.unlink()
            deleted.append(path)
    return deleted
