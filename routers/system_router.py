from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse, RedirectResponse

from auth import get_usuario_logado
from db.core import get_connection
from db.schema_migrations import get_pending_migration_names
from models import RadiusEnsureNtHashIn
from services.radius_service import ensure_nt_hash_for_radius

from .common import modulos_por_cargo, normalizar_cargo_usuario, usuario_eh_admin, usuario_eh_gestor
from .config import ENABLE_EMBEDDED_WORKER, RADIUS_INTERNAL_SECRET

router = APIRouter()


@router.get("/")
def root():
    return RedirectResponse(url="/login-page", status_code=302)


def _serializar_datetime_iso(valor) -> str | None:
    if not isinstance(valor, datetime):
        return None
    return valor.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@router.get("/health")
def health(request: Request):
    started_at = getattr(request.app.state, "started_at", None)
    boot_status = getattr(request.app.state, "boot_status", "unknown")
    worker_mode = getattr(
        request.app.state,
        "worker_mode",
        "embedded" if ENABLE_EMBEDDED_WORKER else "external",
    )

    payload = {
        "status": "ok",
        "service": "api",
        "boot_status": boot_status,
        "worker_mode": worker_mode,
        "started_at": _serializar_datetime_iso(started_at),
        "uptime_seconds": None,
        "checks": {
            "database": "ok",
            "migrations": "ok",
        },
    }

    if isinstance(started_at, datetime):
        payload["uptime_seconds"] = max(
            int((datetime.now(timezone.utc) - started_at).total_seconds()),
            0,
        )

    try:
        conn = get_connection()
        try:
            conn.execute("SELECT 1")
            pending_migrations = get_pending_migration_names(conn)
        finally:
            conn.close()
    except Exception:
        payload["status"] = "error"
        payload["checks"]["database"] = "error"
        payload["checks"]["migrations"] = "unknown"
        return JSONResponse(status_code=503, content=payload)

    if pending_migrations:
        payload["status"] = "degraded"
        payload["checks"]["migrations"] = "pending"
        payload["pending_migrations"] = pending_migrations
        return JSONResponse(status_code=503, content=payload)

    if boot_status not in {"ready", "unknown"}:
        payload["status"] = "degraded"
        return JSONResponse(status_code=503, content=payload)

    return payload


@router.get("/me")
def eu(usuario=Depends(get_usuario_logado)):
    cargo = normalizar_cargo_usuario(usuario)
    dados = dict(usuario)
    dados["cargo"] = cargo
    dados["modulos"] = modulos_por_cargo(cargo)
    dados["eh_gestor"] = usuario_eh_gestor(usuario)
    dados["eh_admin"] = usuario_eh_admin(usuario)
    return dados


@router.post("/internal/radius/ensure-nt-hash", include_in_schema=False)
def internal_radius_ensure_nt_hash(
    payload: RadiusEnsureNtHashIn,
    x_radius_secret: str = Header(default="", alias="X-RADIUS-SECRET"),
):
    secret = RADIUS_INTERNAL_SECRET
    if not secret or x_radius_secret != secret:
        return JSONResponse(status_code=403, content={"ok": False})

    if not ensure_nt_hash_for_radius(payload.username, payload.password):
        return JSONResponse(status_code=401, content={"ok": False})

    return {"ok": True}
