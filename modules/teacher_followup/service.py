from collections import defaultdict
from datetime import date, datetime

from fastapi import HTTPException

from routers.common import usuario_tem_acesso_coordenacao

from . import repository
from .models import RECORD_TYPE_LABELS, FollowupRecordType
from .schemas import FollowupRecordCreate


def require_access(user: dict) -> None:
    if not usuario_tem_acesso_coordenacao(user or {}):
        raise HTTPException(403, "Acesso negado")


def _clean_text(value: str, limit: int) -> str:
    return str(value or "").strip()[:limit]


def _parse_date(value: str) -> str:
    try:
        return date.fromisoformat(str(value or "").strip()).isoformat()
    except ValueError as exc:
        raise HTTPException(400, "Data invalida. Use o formato AAAA-MM-DD.") from exc


def _parse_optional_date(value: str | None, field_name: str) -> str | None:
    text = _clean_text(value, 10)
    if not text:
        return None
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError as exc:
        raise HTTPException(400, f"{field_name} deve usar o formato AAAA-MM-DD.") from exc


def _deadline_empty() -> dict:
    return {
        "expected": 0,
        "sent": 0,
        "on_time": 0,
        "late": 0,
        "pending": 0,
        "on_time_percent": None,
    }


def _parse_datetime(value: str):
    text = str(value or "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _with_percent(values: dict) -> dict:
    expected = int(values["expected"])
    return {
        **values,
        "on_time_percent": round((int(values["on_time"]) / expected) * 100, 1) if expected else None,
    }


def _normalize_period(date_from: str | None, date_to: str | None) -> dict:
    start = _parse_optional_date(date_from, "Data inicial")
    end = _parse_optional_date(date_to, "Data final")
    if start and end and start > end:
        raise HTTPException(400, "A data inicial nao pode ser posterior a data final.")
    return {"date_from": start, "date_to": end}


def _deadline_metrics_by_teacher(
    *,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict[int, dict]:
    metrics = defaultdict(_deadline_empty)
    seen = set()

    for row in repository.list_apc_deadline_rows(date_from=date_from, date_to=date_to):
        key = (
            int(row.get("teacher_id") or 0),
            int(row.get("period_id") or 0),
            str(row.get("audience") or ""),
            int(row.get("turma_id") or 0),
            int(row.get("disciplina_id") or 0),
        )
        if key in seen or key[0] <= 0 or key[1] <= 0:
            continue
        seen.add(key)

        teacher_metrics = metrics[key[0]]
        teacher_metrics["expected"] += 1
        sent_at = _parse_datetime(row.get("delivered_at"))
        deadline = _parse_datetime(row.get("prazo_envio"))
        if not sent_at:
            teacher_metrics["pending"] += 1
        elif deadline and sent_at > deadline:
            teacher_metrics["sent"] += 1
            teacher_metrics["late"] += 1
        else:
            teacher_metrics["sent"] += 1
            teacher_metrics["on_time"] += 1

    return {teacher_id: _with_percent(values) for teacher_id, values in metrics.items()}


def _period_deadline_summary(deadlines: dict[int, dict], teacher_ids: list[int]) -> dict:
    summary = _deadline_empty()
    selected_ids = {int(teacher_id) for teacher_id in teacher_ids}
    for teacher_id, values in deadlines.items():
        if selected_ids and int(teacher_id) not in selected_ids:
            continue
        summary["expected"] += int(values.get("expected") or 0)
        summary["sent"] += int(values.get("sent") or 0)
        summary["on_time"] += int(values.get("on_time") or 0)
        summary["late"] += int(values.get("late") or 0)
        summary["pending"] += int(values.get("pending") or 0)
    return _with_percent(summary)


def _format_record(row: dict) -> dict:
    record_type = str(row.get("record_type") or "").strip()
    return {
        "id": int(row.get("id") or 0),
        "teacher_id": int(row.get("teacher_id") or 0),
        "type": record_type,
        "type_label": RECORD_TYPE_LABELS.get(record_type, record_type),
        "category": str(row.get("category") or "").strip(),
        "description": str(row.get("description") or "").strip(),
        "date": str(row.get("record_date") or "").strip(),
        "created_by_name": str(row.get("created_by_name") or "").strip(),
        "created_at": str(row.get("created_at") or "").strip(),
    }


def _teacher_summary(teacher: dict, counts: dict, deadlines: dict) -> dict:
    teacher_id = int(teacher["id"])
    teacher_counts = counts.get(teacher_id, {})
    teacher_deadlines = deadlines.get(
        teacher_id,
        _deadline_empty(),
    )
    disciplines = list(teacher.get("disciplines") or [])
    return {
        "id": teacher_id,
        "name": str(teacher.get("nome") or "").strip(),
        "email": str(teacher.get("email") or "").strip(),
        "discipline": ", ".join(disciplines) if disciplines else "Sem disciplina vinculada",
        "disciplines": disciplines,
        "on_time_percent": teacher_deadlines["on_time_percent"],
        "positive_count": int(teacher_counts.get("positives") or 0),
        "attention_count": int(teacher_counts.get("attention_points") or 0),
        "deadline_indicators": teacher_deadlines,
    }


def list_teachers(
    user: dict,
    q: str = "",
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    require_access(user)
    period = _normalize_period(date_from, date_to)
    teachers = repository.list_teachers(search=q)
    counts = repository.count_records_by_teacher()
    deadlines = _deadline_metrics_by_teacher(**period)
    teacher_ids = [int(teacher["id"]) for teacher in teachers]
    return {
        "teachers": [_teacher_summary(teacher, counts, deadlines) for teacher in teachers],
        "query": str(q or "").strip(),
        "period": period,
        "period_summary": _period_deadline_summary(deadlines, teacher_ids),
    }


def search_teachers(user: dict, q: str = "") -> dict:
    require_access(user)
    teachers = repository.list_teachers(search=q, limit=20)
    return {
        "teachers": [
            {
                "id": int(teacher["id"]),
                "name": str(teacher.get("nome") or "").strip(),
                "email": str(teacher.get("email") or "").strip(),
                "discipline": ", ".join(teacher.get("disciplines") or []),
            }
            for teacher in teachers
        ]
    }


def get_profile(
    user: dict,
    teacher_id: int,
    record_type: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    require_access(user)
    period = _normalize_period(date_from, date_to)
    teacher = repository.get_teacher(int(teacher_id))
    if not teacher:
        raise HTTPException(404, "Professor nao encontrado.")

    record_type_clean = _clean_text(record_type, 40) or None
    if record_type_clean and record_type_clean not in {item.value for item in FollowupRecordType}:
        raise HTTPException(400, "Tipo de registro invalido.")

    counts = repository.count_records_by_teacher()
    deadlines = _deadline_metrics_by_teacher(**period)
    records = repository.list_records(int(teacher_id), record_type_clean)
    teacher_deadlines = deadlines.get(int(teacher_id), _deadline_empty())
    return {
        "teacher": _teacher_summary(teacher, counts, deadlines),
        "period_summary": {
            "records_total": len(repository.list_records(int(teacher_id))),
            "records_visible": len(records),
            "positives": int(counts.get(int(teacher_id), {}).get("positives") or 0),
            "attention_points": int(counts.get(int(teacher_id), {}).get("attention_points") or 0),
            "deadline_summary": teacher_deadlines,
        },
        "period": period,
        "deadline_indicators": teacher_deadlines,
        "timeline": [_format_record(row) for row in records],
        "previous_evaluations": [],
        "record_types": [
            {"id": item.value, "label": RECORD_TYPE_LABELS[item.value]}
            for item in FollowupRecordType
        ],
    }


def create_record(user: dict, payload: FollowupRecordCreate) -> dict:
    require_access(user)
    teacher = repository.get_teacher(payload.teacher_id)
    if not teacher:
        raise HTTPException(404, "Professor nao encontrado.")

    category = _clean_text(payload.category, 120)
    description = _clean_text(payload.description, 2000)
    if not category:
        raise HTTPException(400, "Categoria e obrigatoria.")
    if not description:
        raise HTTPException(400, "Descricao e obrigatoria.")

    record = repository.create_record(
        teacher_id=payload.teacher_id,
        record_type=payload.record_type.value,
        category=category,
        description=description,
        record_date=_parse_date(payload.record_date),
        created_by_user_id=int(user["id"]) if (user or {}).get("id") is not None else None,
    )
    return {"record": _format_record(record)}
