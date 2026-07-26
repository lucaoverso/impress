from collections import defaultdict
from datetime import UTC, datetime, timedelta

from services.apc_recipients import resolve_apc_recipients

from . import apc_repository, repository
from .config import app_timezone
from .service import create_notification


def _parse_sqlite_local(value: str) -> datetime:
    parsed = datetime.fromisoformat(str(value or "").strip())
    return parsed.replace(tzinfo=app_timezone()).astimezone(UTC)


def _parse_sqlite_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(str(value or "").strip())
    return parsed.replace(tzinfo=UTC)


def _obligations_by_teacher(period: dict) -> dict[int, list[list[int]]]:
    grouped: dict[int, set[tuple[int, int]]] = defaultdict(set)
    for item in resolve_apc_recipients(period):
        teacher_id = int(item.get("professor_id") or 0)
        if teacher_id > 0:
            grouped[teacher_id].add(
                (
                    int(item.get("turma_id") or 0),
                    int(item.get("disciplina_id") or 0),
                )
            )
    return {
        teacher_id: [list(value) for value in sorted(values)]
        for teacher_id, values in grouped.items()
    }


def _all_submitted(period_id: int, teacher_id: int, obligations: list[list[int]]) -> bool:
    submitted = {
        (int(item.get("turma_id") or 0), int(item.get("disciplina_id") or 0))
        for item in apc_repository.list_submissions(period_id, teacher_id)
    }
    return bool(obligations) and all(tuple(item) in submitted for item in obligations)


def sync_apc_period(period_id: int) -> int:
    period = apc_repository.get_period(int(period_id))
    if not period:
        repository.cancel_source("apc_period", str(period_id))
        return 0
    deadline = _parse_sqlite_local(period["prazo_envio"])
    changed_at = _parse_sqlite_utc(period.get("atualizado_em") or period["criado_em"])
    now = datetime.now(UTC)
    obligations = _obligations_by_teacher(period)
    valid_keys: list[str] = []
    created = 0
    deadline_key = deadline.strftime("%Y%m%dT%H%M%SZ")

    for teacher_id, items in obligations.items():
        common = {
            "recipient_user_id": teacher_id,
            "category": "attachments",
            "action_url": f"/apc?periodo_id={int(period_id)}",
            "source_type": "apc_period",
            "source_id": str(period_id),
            "metadata": {"obligations": items, "deadline_utc": deadline_key},
        }
        initial_key = f"apc:{period_id}:created:{deadline_key}:{teacher_id}"
        valid_keys.append(initial_key)
        if deadline > now:
            created += bool(
                create_notification(
                    **common,
                    title=f"Nova demanda: {period.get('titulo') or 'Central de anexos'}",
                    body="Há uma nova demanda para anexar. Abra a Central de Anexos para conferir o prazo.",
                    priority="normal",
                    dedupe_key=initial_key,
                    available_at=changed_at,
                )
            )

        for hours, priority in ((72, "normal"), (24, "urgent")):
            marker = deadline - timedelta(hours=hours)
            key = f"apc:{period_id}:{deadline_key}:{hours}h:{teacher_id}"
            valid_keys.append(key)
            if changed_at > marker or deadline <= now:
                continue
            notification = create_notification(
                **common,
                title=f"Prazo em {hours}h: {period.get('titulo') or 'demanda de anexos'}",
                body="Ainda há anexo pendente. Abra a demanda para revisar suas entregas.",
                priority=priority,
                dedupe_key=key,
                available_at=marker,
            )
            created += bool(notification)
    repository.cancel_source_except("apc_period", str(period_id), valid_keys)
    _cancel_completed_due_reminders(period_id, obligations, now)
    return created


def _cancel_completed_due_reminders(
    period_id: int, obligations: dict[int, list[list[int]]], now: datetime
):
    for teacher_id, items in obligations.items():
        if not _all_submitted(period_id, teacher_id, items):
            continue
        conn_rows = apc_repository.list_due_reminders(period_id, teacher_id)
        for row in conn_rows:
            if row["available_at"] <= now.strftime("%Y-%m-%d %H:%M:%S"):
                apc_repository.cancel_notification(row["id"])


def cancel_apc_period(period_id: int):
    return repository.cancel_source("apc_period", str(period_id))


def reconcile_all_apc():
    periods = apc_repository.list_periods()
    current = {str(item["id"]) for item in periods}
    for period in periods:
        sync_apc_period(int(period["id"]))
    for source_id in repository.list_active_source_ids("apc_period"):
        if source_id not in current:
            repository.cancel_source("apc_period", source_id)
