import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def _get_legacy_config():
    return sys.modules.get("routers.config")


def get_spool_dir() -> str:
    legacy_config = _get_legacy_config()
    if legacy_config is not None and getattr(legacy_config, "SPOOL_DIR", None):
        return str(getattr(legacy_config, "SPOOL_DIR"))
    return os.getenv("SPOOL_DIR", str(BASE_DIR / "spool"))


def get_default_printer_name() -> str:
    legacy_config = _get_legacy_config()
    if legacy_config is not None and getattr(legacy_config, "DEFAULT_PRINTER_NAME", None) is not None:
        return str(getattr(legacy_config, "DEFAULT_PRINTER_NAME")).strip()
    return os.getenv("CUPS_PRINTER", "").strip()


def get_upload_formats_description() -> str:
    legacy_config = _get_legacy_config()
    if legacy_config is not None and getattr(legacy_config, "FORMATOS_UPLOAD_DESCRICAO", None):
        return str(getattr(legacy_config, "FORMATOS_UPLOAD_DESCRICAO"))
    return "PDF, DOCX, DOC, PNG, JPG ou JPEG"


SPOOL_DIR = get_spool_dir()
DEFAULT_PRINTER_NAME = get_default_printer_name()
FORMATOS_UPLOAD_DESCRICAO = get_upload_formats_description()

__all__ = [
    "BASE_DIR",
    "DEFAULT_PRINTER_NAME",
    "FORMATOS_UPLOAD_DESCRICAO",
    "SPOOL_DIR",
    "get_default_printer_name",
    "get_spool_dir",
    "get_upload_formats_description",
]
