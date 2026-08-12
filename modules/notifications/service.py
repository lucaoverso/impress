from datetime import UTC, datetime
from math import ceil
from uuid import uuid4

from fastapi import HTTPException

from modules.audit.models import AuditCategory, AuditOutcome
from modules.audit.service import record_event

from . import delivery_repository, management_repository, repository
from .config import app_timezone, push_settings


def utc_text(value: datetime | None = None) -> str:
    moment = value or datetime.now(UTC)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S")


def parse_local_schedule(value: str | None) -> datetime:
    text = str(value or "").strip()
    if not text:
        return datetime.now(UTC)
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise HTTPException(400, "Informe uma data e hora válidas.") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=app_timezone())
    result = parsed.astimezone(UTC)
    if result < datetime.now(UTC):
        raise HTTPException(400, "A data de envio não pode estar no passado.")
    return result


def create_notification(
    *,
    recipient_user_id: int,
    category: str,
    title: str,
    body: str,
    action_url: str = "/",
    priority: str = "normal",
    source_type: str = "",
    source_id: str = "",
    dedupe_key: str | None = None,
    batch_id: str | None = None,
    metadata: dict | None = None,
    created_by_user_id: int | None = None,
    available_at: datetime | None = None,
) -> dict:
    title = str(title or "").strip()
    body = str(body or "").strip()
    action_url = str(action_url or "/").strip() or "/"
    if not title or len(title) > 100:
        raise ValueError("O título deve ter entre 1 e 100 caracteres.")
    if not body or len(body) > 300:
        raise ValueError("A mensagem deve ter entre 1 e 300 caracteres.")
    if not action_url.startswith("/") or action_url.startswith("//"):
        raise ValueError("A URL da notificação deve ser interna.")
    if priority not in {"normal", "urgent"}:
        raise ValueError("Prioridade inválida.")
    return repository.create_notification(
        {
            "recipient_user_id": int(recipient_user_id),
            "category": str(category).strip()[:50],
            "title": title,
            "body": body,
            "action_url": action_url[:500],
            "priority": priority,
            "source_type": str(source_type).strip()[:50],
            "source_id": str(source_id).strip()[:100],
            "dedupe_key": str(dedupe_key).strip()[:200] if dedupe_key else None,
            "batch_id": batch_id,
            "metadata": metadata or {},
            "created_by_user_id": created_by_user_id,
            "available_at": utc_text(available_at),
        }
    )


def list_inbox(user_id: int, *, filter_name: str, page: int, page_size: int) -> dict:
    if filter_name not in {"all", "unread"}:
        raise HTTPException(400, "Filtro de notificações inválido.")
    page = max(1, int(page))
    page_size = min(50, max(5, int(page_size)))
    items, total = repository.list_notifications(
        int(user_id),
        unread_only=filter_name == "unread",
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    return {
        "items": items,
        "total": total,
        "unread_count": repository.unread_count(int(user_id)),
        "page": page,
        "page_size": page_size,
        "pages": ceil(total / page_size) if total else 0,
    }


def mark_one_read(notification_id: int, user_id: int):
    if not repository.mark_read(notification_id, user_id):
        raise HTTPException(404, "Notificação não encontrada.")
    return {"ok": True, "unread_count": repository.unread_count(user_id)}


def get_unread_count(user_id: int) -> dict:
    return {"unread_count": repository.unread_count(int(user_id))}


def mark_all_read(user_id: int) -> dict:
    updated = repository.mark_all_read(int(user_id))
    return {"ok": True, "updated": updated, "unread_count": 0}


def push_config(user_id: int) -> dict:
    settings = push_settings()
    return {
        "enabled": bool(settings["enabled"]),
        "public_key": settings["public_key"] if settings["enabled"] else "",
        "supported": True,
        "active": bool(delivery_repository.active_subscription_count(user_id)),
    }


def save_subscription(user_id: int, endpoint: str, keys: dict, user_agent: str):
    delivery_repository.upsert_subscription(
        user_id, endpoint, keys["p256dh"], keys["auth"], user_agent
    )
    return {"ok": True, "active": True}


def delete_subscription(user_id: int, endpoint: str):
    delivery_repository.deactivate_subscription(user_id, endpoint)
    return {"ok": True, "active": False}


def resolve_estimate(audiences: list[str], user_ids: list[int]) -> dict:
    valid = {"all", "teachers", "managers"}
    normalized = sorted({item.strip().lower() for item in audiences if item.strip()})
    if any(item not in valid for item in normalized):
        raise HTTPException(400, "Público inválido.")
    recipients = repository.resolve_audience(normalized, user_ids)
    return {"count": len(recipients), "recipient_ids": recipients}


def search_recipients(search: str) -> dict:
    return {"items": repository.list_recipients(search)}


def list_batches() -> dict:
    now = utc_text()
    items = repository.list_batches()
    for item in items:
        if int(item["cancelled"] or 0) >= int(item["recipients"] or 0):
            item["status"] = "cancelled"
        elif str(item["scheduled_at"]) > now:
            item["status"] = "scheduled"
        else:
            item["status"] = "sent"
    return {"items": items}


def list_batch_recipients(batch_id: str) -> dict:
    normalized_batch_id = str(batch_id or "").strip()
    items = management_repository.list_batch_recipients(normalized_batch_id)
    if not items:
        raise HTTPException(404, "Lote de notificações não encontrado.")
    for item in items:
        item["active_devices"] = int(item.get("active_devices") or 0)
        item["push_active"] = item["active_devices"] > 0
    return {
        "batch_id": normalized_batch_id,
        "title": items[0]["title"],
        "items": items,
        "total": len(items),
        "read_count": sum(1 for item in items if item.get("read_at")),
        "push_active_count": sum(1 for item in items if item["push_active"]),
    }


def create_batch(payload, actor: dict) -> dict:
    estimate = resolve_estimate(payload.audiences, payload.user_ids)
    recipients = estimate["recipient_ids"]
    if not recipients:
        raise HTTPException(400, "Selecione ao menos um destinatário ativo.")
    available_at = parse_local_schedule(payload.scheduled_at)
    batch_id = str(uuid4())
    for user_id in recipients:
        create_notification(
            recipient_user_id=user_id,
            category="manual",
            title=payload.title,
            body=payload.body,
            action_url=payload.action_url,
            priority=payload.priority,
            source_type="manual_batch",
            source_id=batch_id,
            dedupe_key=f"manual:{batch_id}:{user_id}",
            batch_id=batch_id,
            created_by_user_id=int(actor["id"]),
            available_at=available_at,
        )
    record_event(
        category=AuditCategory.NOTIFICATIONS,
        action="notifications.batch.create",
        outcome=AuditOutcome.SUCCESS,
        actor=actor,
        entity_type="notification_batch",
        entity_id=batch_id,
        description=f"Lote de notificações criado para {len(recipients)} destinatários.",
        metadata={"recipients": len(recipients), "scheduled_at": utc_text(available_at)},
    )
    return {
        "batch_id": batch_id,
        "recipients": len(recipients),
        "scheduled_at": utc_text(available_at),
    }


def cancel_batch(batch_id: str, actor: dict) -> dict:
    cancelled = repository.cancel_batch(batch_id.strip())
    if not cancelled:
        raise HTTPException(409, "Este lote já foi disparado, cancelado ou não existe.")
    record_event(
        category=AuditCategory.NOTIFICATIONS,
        action="notifications.batch.cancel",
        outcome=AuditOutcome.SUCCESS,
        actor=actor,
        entity_type="notification_batch",
        entity_id=batch_id,
        description=f"Lote de notificações cancelado antes do disparo ({cancelled} itens).",
        metadata={"cancelled": cancelled},
    )
    return {"ok": True, "cancelled": cancelled}
