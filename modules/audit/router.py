from fastapi import APIRouter, Depends

from auth import get_usuario_logado
from modules.audit.schemas import AuditEventPage
from modules.audit.service import list_audit_events
from routers.common import exigir_admin

router = APIRouter(prefix="/admin/audit", tags=["audit"])


@router.get("/events", response_model=AuditEventPage)
def get_audit_events(
    date_from: str | None = None,
    date_to: str | None = None,
    category: str | None = None,
    outcome: str | None = None,
    actor_user_id: int | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 30,
    usuario=Depends(get_usuario_logado),
):
    exigir_admin(usuario)
    return list_audit_events(
        date_from=date_from,
        date_to=date_to,
        category=category,
        outcome=outcome,
        actor_user_id=actor_user_id,
        search=search,
        page=page,
        page_size=page_size,
    )
