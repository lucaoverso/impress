import json
import logging
from datetime import date
from math import ceil

from fastapi import HTTPException

from modules.audit import repository
from modules.audit.models import AuditCategory, AuditOutcome

logger = logging.getLogger(__name__)

SENSITIVE_KEYS = {
    "authorization",
    "password",
    "senha",
    "senha_hash",
    "token",
    "nova_senha",
}
VALID_CATEGORIES = {item.value for item in AuditCategory}
VALID_OUTCOMES = {item.value for item in AuditOutcome}
AUDIT_RETENTION_DAYS = 180


def _clean_text(value, limit: int = 500) -> str:
    return str(value or "").strip()[:limit]


def _sanitize_metadata(value, depth: int = 0):
    if depth > 3:
        return "[limite]"
    if isinstance(value, dict):
        return {
            _clean_text(key, 80): _sanitize_metadata(item, depth + 1)
            for key, item in value.items()
            if str(key).strip().lower() not in SENSITIVE_KEYS
        }
    if isinstance(value, (list, tuple)):
        return [_sanitize_metadata(item, depth + 1) for item in value[:30]]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return _clean_text(value, 300)


def record_event(
    *,
    category: AuditCategory | str,
    action: str,
    outcome: AuditOutcome | str,
    description: str,
    actor: dict | None = None,
    actor_email: str = "",
    entity_type: str = "",
    entity_id: int | str | None = None,
    metadata: dict | None = None,
) -> int | None:
    try:
        actor = actor or {}
        sanitized_metadata = _sanitize_metadata(metadata or {})
        event_id = repository.create_event(
            category=_clean_text(category, 40),
            action=_clean_text(action, 80),
            outcome=_clean_text(outcome, 20),
            actor_user_id=int(actor["id"]) if actor.get("id") is not None else None,
            actor_name=_clean_text(actor.get("nome"), 160),
            actor_email=_clean_text(actor.get("email") or actor_email, 200).lower(),
            description=_clean_text(description, 500),
            entity_type=_clean_text(entity_type, 60),
            entity_id=_clean_text(entity_id, 80),
            metadata=sanitized_metadata,
        )
        try:
            repository.delete_events_older_than(AUDIT_RETENTION_DAYS)
        except Exception:
            logger.exception("Falha ao aplicar retencao dos eventos de auditoria.")
        return event_id
    except Exception:
        logger.exception("Falha ao registrar evento de auditoria: %s", action)
        return None


def _validate_date(value: str | None, field_name: str) -> str | None:
    normalized = _clean_text(value, 10)
    if not normalized:
        return None
    try:
        date.fromisoformat(normalized)
    except ValueError as exc:
        raise HTTPException(400, f"{field_name} deve usar o formato AAAA-MM-DD.") from exc
    return normalized


def list_audit_events(
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    category: str | None = None,
    outcome: str | None = None,
    actor_user_id: int | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 30,
) -> dict:
    date_from = _validate_date(date_from, "Data inicial")
    date_to = _validate_date(date_to, "Data final")
    category = _clean_text(category, 40).lower() or None
    outcome = _clean_text(outcome, 20).lower() or None
    search = _clean_text(search, 120) or None

    if date_from and date_to and date_from > date_to:
        raise HTTPException(400, "A data inicial nao pode ser posterior a data final.")
    if category and category not in VALID_CATEGORIES:
        raise HTTPException(400, "Categoria de auditoria invalida.")
    if outcome and outcome not in VALID_OUTCOMES:
        raise HTTPException(400, "Resultado de auditoria invalido.")

    page = max(1, int(page))
    page_size = min(100, max(10, int(page_size)))
    rows, total = repository.list_events(
        date_from=date_from,
        date_to=date_to,
        category=category,
        outcome=outcome,
        actor_user_id=actor_user_id,
        search=search,
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    items = []
    for row in rows:
        try:
            metadata = json.loads(row.pop("metadata_json") or "{}")
        except (TypeError, json.JSONDecodeError):
            metadata = {}
        row["metadata"] = metadata if isinstance(metadata, dict) else {}
        items.append(row)

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": ceil(total / page_size) if total else 0,
    }
