import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SPOOL_DIR = os.getenv("SPOOL_DIR", str(BASE_DIR / "spool"))
DEFAULT_PRINTER_NAME = os.getenv("CUPS_PRINTER", "").strip()
FORMATOS_UPLOAD_DESCRICAO = "PDF, DOCX, DOC, PNG, JPG ou JPEG"

__all__ = [
    "BASE_DIR",
    "DEFAULT_PRINTER_NAME",
    "FORMATOS_UPLOAD_DESCRICAO",
    "SPOOL_DIR",
]
