import io
import os
import re
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageOps, UnidentifiedImageError


MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_DIMENSION = 2400
MAX_SOURCE_PIXELS = 25_000_000
IMAGE_TOKEN_RE = re.compile(r"^[a-f0-9]{32}\.(?:jpg|png)$")


def activity_image_directory() -> Path:
    default_apc_dir = Path(__file__).resolve().parents[2] / "spool" / "apc"
    directory = Path(os.getenv("APC_DIR", str(default_apc_dir))) / "activity_images"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def store_activity_image(content: bytes) -> dict:
    if not content:
        raise ValueError("Selecione uma imagem.")
    if len(content) > MAX_IMAGE_BYTES:
        raise ValueError("A imagem deve ter no maximo 5 MB.")
    try:
        with Image.open(io.BytesIO(content)) as source:
            if source.width * source.height > MAX_SOURCE_PIXELS:
                raise ValueError("A imagem possui dimensoes maiores que o permitido.")
            source.verify()
        with Image.open(io.BytesIO(content)) as source:
            image = ImageOps.exif_transpose(source)
            image.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION))
            has_alpha = image.mode in {"RGBA", "LA"} or "transparency" in image.info
            extension = "png" if has_alpha else "jpg"
            token = f"{uuid4().hex}.{extension}"
            destination = activity_image_directory() / token
            if has_alpha:
                image.convert("RGBA").save(destination, "PNG", optimize=True)
            else:
                image.convert("RGB").save(destination, "JPEG", quality=92, optimize=True)
            return {
                "token": token,
                "url": f"/apc/atividade/imagens/{token}",
                "width": int(image.width),
                "height": int(image.height),
            }
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValueError("O arquivo enviado nao e uma imagem valida.") from exc


def resolve_activity_image(token: str) -> Path | None:
    token = str(token or "").strip().lower()
    if not IMAGE_TOKEN_RE.fullmatch(token):
        return None
    path = activity_image_directory() / token
    return path if path.is_file() else None
