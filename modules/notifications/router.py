from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import FileResponse

from auth import get_usuario_logado
from routers.common import exigir_gestor
from routers.config import STATIC_DIR, render_template_response

from . import service
from .schemas import (
    BatchCreateIn,
    EstimateIn,
    PushSubscriptionDeleteIn,
    PushSubscriptionIn,
)

router = APIRouter()


@router.get("/notificacoes")
def notifications_page(request: Request):
    return render_template_response(
        request, "notifications/index.html", cache_control="no-store"
    )


@router.get("/notificacoes/gestao")
def notifications_management_page(request: Request):
    return render_template_response(
        request, "notifications/manage.html", cache_control="no-store"
    )


@router.get("/service-worker.js", include_in_schema=False)
def service_worker():
    return FileResponse(
        STATIC_DIR / "service-worker.js",
        media_type="application/javascript",
        headers={
            "Service-Worker-Allowed": "/",
            "Cache-Control": "no-cache",
        },
    )


@router.get("/notifications")
def get_notifications(
    filter: str = Query("all"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=5, le=50),
    user=Depends(get_usuario_logado),
):
    return service.list_inbox(
        int(user["id"]), filter_name=filter, page=page, page_size=page_size
    )


@router.get("/notifications/unread-count")
def get_unread_count(user=Depends(get_usuario_logado)):
    return service.get_unread_count(int(user["id"]))


@router.post("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: int, user=Depends(get_usuario_logado)
):
    return service.mark_one_read(notification_id, int(user["id"]))


@router.post("/notifications/read-all")
def mark_all_notifications_read(user=Depends(get_usuario_logado)):
    return service.mark_all_read(int(user["id"]))


@router.get("/notifications/push/config")
def get_push_config(user=Depends(get_usuario_logado)):
    return service.push_config(int(user["id"]))


@router.put("/notifications/push/subscriptions")
def put_push_subscription(
    payload: PushSubscriptionIn,
    request: Request,
    user=Depends(get_usuario_logado),
):
    return service.save_subscription(
        int(user["id"]),
        payload.endpoint,
        payload.keys.model_dump(),
        request.headers.get("user-agent", ""),
    )


@router.delete("/notifications/push/subscriptions")
def delete_push_subscription(
    payload: PushSubscriptionDeleteIn,
    user=Depends(get_usuario_logado),
):
    return service.delete_subscription(int(user["id"]), payload.endpoint)


@router.get("/notifications/manage/recipients")
def get_recipients(
    search: str = Query("", max_length=120),
    user=Depends(get_usuario_logado),
):
    exigir_gestor(user)
    return service.search_recipients(search)


@router.post("/notifications/manage/estimate")
def estimate_recipients(
    payload: EstimateIn, user=Depends(get_usuario_logado)
):
    exigir_gestor(user)
    return service.resolve_estimate(payload.audiences, payload.user_ids)


@router.post("/notifications/manage/batches")
def create_notification_batch(
    payload: BatchCreateIn, user=Depends(get_usuario_logado)
):
    exigir_gestor(user)
    return service.create_batch(payload, user)


@router.get("/notifications/manage/batches")
def get_notification_batches(user=Depends(get_usuario_logado)):
    exigir_gestor(user)
    return service.list_batches()


@router.get("/notifications/manage/batches/{batch_id}/recipients")
def get_notification_batch_recipients(
    batch_id: str, user=Depends(get_usuario_logado)
):
    exigir_gestor(user)
    return service.list_batch_recipients(batch_id)


@router.post("/notifications/manage/batches/{batch_id}/cancel")
def cancel_notification_batch(
    batch_id: str, user=Depends(get_usuario_logado)
):
    exigir_gestor(user)
    return service.cancel_batch(batch_id, user)
