import io
import re
from pathlib import Path
from uuid import uuid4

from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from .config import FINANCE_ATTACHMENT_DIR


MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 30_000_000
ALLOWED_IMAGE_FORMATS = {"JPEG": ("jpg", "image/jpeg"), "PNG": ("png", "image/png")}
STORED_FILE_RE = re.compile(r"^[a-f0-9]{32}\.(?:pdf|jpg|png)$")


class FinanceAttachmentValidationError(ValueError):
    pass


def attachment_directory(directory: Path | None = None) -> Path:
    target = Path(directory or FINANCE_ATTACHMENT_DIR).expanduser()
    target.mkdir(parents=True, exist_ok=True)
    return target


def _detect_file(content: bytes) -> tuple[str, str]:
    if content.startswith(b"%PDF-"):
        try:
            reader = PdfReader(io.BytesIO(content))
            if reader.is_encrypted or len(reader.pages) <= 0:
                raise FinanceAttachmentValidationError(
                    "O PDF deve estar desbloqueado e possuir ao menos uma pagina."
                )
        except FinanceAttachmentValidationError:
            raise
        except (PdfReadError, OSError, ValueError) as exc:
            raise FinanceAttachmentValidationError("O arquivo PDF esta corrompido.") from exc
        return "pdf", "application/pdf"
    try:
        with Image.open(io.BytesIO(content)) as image:
            if image.width * image.height > MAX_IMAGE_PIXELS:
                raise FinanceAttachmentValidationError(
                    "A imagem possui dimensoes maiores que o permitido."
                )
            image_format = str(image.format or "").upper()
            if image_format not in ALLOWED_IMAGE_FORMATS:
                raise FinanceAttachmentValidationError(
                    "O comprovante deve ser PDF, JPG, JPEG ou PNG."
                )
            image.verify()
            return ALLOWED_IMAGE_FORMATS[image_format]
    except FinanceAttachmentValidationError:
        raise
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError, ValueError) as exc:
        raise FinanceAttachmentValidationError(
            "O arquivo nao e um PDF ou uma imagem valida."
        ) from exc


def store_attachment(
    content: bytes,
    *,
    original_filename: str,
    directory: Path | None = None,
) -> dict:
    if not content:
        raise FinanceAttachmentValidationError("Selecione um comprovante.")
    if len(content) > MAX_ATTACHMENT_BYTES:
        raise FinanceAttachmentValidationError("O comprovante deve ter no maximo 10 MB.")

    extension, media_type = _detect_file(content)
    raw_name = str(original_filename or "comprovante").replace("\\", "/")
    original_name = Path(raw_name.rsplit("/", 1)[-1]).name.strip()[:255]
    if not original_name:
        original_name = f"comprovante.{extension}"

    token = uuid4().hex
    stored_name = f"{token}.{extension}"
    target_dir = attachment_directory(directory)
    target = target_dir / stored_name
    temporary = target_dir / f".{token}.tmp"
    try:
        temporary.write_bytes(content)
        temporary.replace(target)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        target.unlink(missing_ok=True)
        raise FinanceAttachmentValidationError(
            "Nao foi possivel armazenar o comprovante."
        ) from exc

    return {
        "token": token,
        "stored_name": stored_name,
        "original_name": original_name,
        "media_type": media_type,
        "size_bytes": len(content),
    }


def resolve_attachment(stored_name: str, *, directory: Path | None = None) -> Path | None:
    safe_name = str(stored_name or "").strip().lower()
    if not STORED_FILE_RE.fullmatch(safe_name):
        return None
    path = attachment_directory(directory) / safe_name
    return path if path.is_file() else None


def delete_attachment_file(stored_name: str, *, directory: Path | None = None) -> bool:
    path = resolve_attachment(stored_name, directory=directory)
    if not path:
        return False
    path.unlink()
    return True
