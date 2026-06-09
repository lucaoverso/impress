import os
import time
from datetime import datetime
from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
SPOOL_DIR = os.getenv("SPOOL_DIR", str(BASE_DIR / "spool"))
APC_DIR = os.getenv("APC_DIR", str(BASE_DIR / "spool" / "apc"))
DEFAULT_PRINTER_NAME = os.getenv("CUPS_PRINTER", "").strip()
ENABLE_EMBEDDED_WORKER = os.getenv("ENABLE_EMBEDDED_WORKER", "").strip().lower() in {
    "1",
    "true",
    "yes",
}
FORMATOS_UPLOAD_DESCRICAO = "PDF, DOCX, DOC, PNG, JPG ou JPEG"


def _resolver_asset_version() -> str:
    valor = os.getenv("STATIC_ASSET_VERSION", "").strip()
    if valor:
        return valor
    return str(int(datetime.now().timestamp()))


ASSET_VERSION = _resolver_asset_version()


def get_asset_version() -> str:
    if ASSET_VERSION.lower() == "dynamic":
        return str(time.time_ns())
    return ASSET_VERSION


def _resolver_janela_cancelamento() -> int:
    valor = os.getenv("PRINT_CANCEL_WINDOW_SECONDS", "15").strip()
    try:
        segundos = int(valor)
    except ValueError:
        return 15
    return max(segundos, 0)


PRINT_CANCEL_WINDOW_SECONDS = _resolver_janela_cancelamento()


def _resolver_radius_internal_secret() -> str:
    return os.getenv("RADIUS_INTERNAL_SECRET", "").strip()


RADIUS_INTERNAL_SECRET = _resolver_radius_internal_secret()
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.policies["json.dumps_kwargs"] = {"ensure_ascii": False}


def render_template_response(
    request: Request,
    template_name: str,
    extra_context: dict | None = None,
    *,
    cache_control: str | None = None,
):
    context = {"request": request}
    if extra_context:
        context.update(extra_context)
    context["asset_version"] = get_asset_version()

    response = templates.TemplateResponse(request, template_name, context)
    response.charset = "utf-8"
    if cache_control:
        response.headers["Cache-Control"] = cache_control
    return response
