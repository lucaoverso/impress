import json
import logging

from .config import push_settings
from . import delivery_repository

logger = logging.getLogger(__name__)


def _status_code(exc: Exception) -> int:
    response = getattr(exc, "response", None)
    try:
        return int(getattr(response, "status_code", 0) or 0)
    except (TypeError, ValueError):
        return 0


def _safe_error(exc: Exception, status: int) -> str:
    name = exc.__class__.__name__
    return f"{name} (HTTP {status})" if status else name


def process_one_delivery() -> bool:
    settings = push_settings()
    if not settings["enabled"]:
        return False
    delivery_repository.seed_due_deliveries()
    delivery = delivery_repository.claim_delivery()
    if not delivery:
        return False
    payload = json.dumps(
        {
            "id": delivery["notification_id"],
            "title": delivery["title"],
            "body": delivery["body"],
            "action_url": delivery["action_url"],
            "priority": delivery["priority"],
            "tag": f"notification-{delivery['notification_id']}",
        },
        ensure_ascii=False,
    )
    try:
        from pywebpush import webpush

        webpush(
            subscription_info={
                "endpoint": delivery["endpoint"],
                "keys": {"p256dh": delivery["p256dh"], "auth": delivery["auth"]},
            },
            data=payload,
            vapid_private_key=settings["private_key"],
            vapid_claims={"sub": settings["subject"]},
            ttl=86400,
        )
        delivery_repository.mark_sent(delivery["id"], delivery["subscription_id"])
    except Exception as exc:
        status = _status_code(exc)
        safe_error = _safe_error(exc, status)
        if status in {404, 410}:
            delivery_repository.disable_subscription(
                delivery["subscription_id"], delivery["id"], safe_error
            )
        elif status == 0 or status == 429 or status >= 500:
            delay = min(3600, 60 * (2 ** max(delivery["attempts"] - 1, 0)))
            delivery_repository.mark_retry(
                delivery["id"],
                attempts=delivery["attempts"],
                delay_seconds=delay,
                error=safe_error,
            )
        else:
            delivery_repository.mark_dead(delivery["id"], safe_error)
        logger.warning(
            "Falha sanitizada no Web Push delivery=%s status=%s",
            delivery["id"],
            status or "unknown",
        )
    return True
