from __future__ import annotations

from datetime import datetime

from modules.scheduling.config import (
    JANELA_AULAS_PADRAO_POR_TURNO,
    SEGMENTOS_FAIXA_GLOBAL_POR_TURNO,
)

TIPO_GRADE_AULA = "AULA"
TIPO_GRADE_INTERVALO = "INTERVALO"
PERIODO_MATUTINO = "MATUTINO"
PERIODO_VESPERTINO = "VESPERTINO"


def lesson_window_from_turn(turn: str) -> tuple[int, int]:
    turn_norm = str(turn or "").strip().upper()
    return tuple(int(value) for value in JANELA_AULAS_PADRAO_POR_TURNO.get(turn_norm, (1, 5)))


def resolve_class_lesson_window(class_item: dict | None) -> tuple[int, int]:
    item = dict(class_item or {})
    start_lesson = int(item.get("aula_inicial") or 0)
    end_lesson = int(item.get("aula_final") or 0)
    if start_lesson > 0 and end_lesson >= start_lesson:
        return start_lesson, end_lesson
    return lesson_window_from_turn(item.get("turno", ""))


def lesson_number_is_allowed_for_turn(turn: str, lesson_number: int) -> bool:
    turn_norm = str(turn or "").strip().upper()
    lesson_value = int(lesson_number or 0)
    segments = SEGMENTOS_FAIXA_GLOBAL_POR_TURNO.get(turn_norm)
    if not segments:
        return lesson_value > 0
    return any(int(start) <= lesson_value <= int(end) for start, end in segments)


def build_lesson_display_label(
    lesson_number: int,
    start_time: str = "",
    end_time: str = "",
    name: str = "",
) -> str:
    lesson_label = str(name or "").strip() or f"{int(lesson_number)}a aula"
    clean_start = str(start_time or "").strip()
    clean_end = str(end_time or "").strip()
    if clean_start and clean_end:
        return f"{lesson_label} ({clean_start} - {clean_end})"
    return lesson_label


def resolve_lesson_period(lesson_number: int | None, start_time: str = "") -> str:
    clean_start = str(start_time or "").strip()
    try:
        start_hour = int(clean_start.split(":", 1)[0])
    except (TypeError, ValueError):
        start_hour = -1

    if 0 <= start_hour <= 23:
        return PERIODO_MATUTINO if start_hour < 12 else PERIODO_VESPERTINO

    lesson_value = int(lesson_number or 0)
    if lesson_value > 0:
        return PERIODO_MATUTINO if lesson_value <= 5 else PERIODO_VESPERTINO
    return ""


def normalize_schedule_entries(entries: list[dict] | None) -> list[dict]:
    normalized = []
    for raw_item in entries or []:
        item = dict(raw_item or {})
        entry_type = str(item.get("tipo") or TIPO_GRADE_AULA).strip().upper() or TIPO_GRADE_AULA
        lesson_number = item.get("aula_numero")
        if lesson_number not in (None, ""):
            lesson_number = int(lesson_number)
        else:
            lesson_number = None

        start_time = str(item.get("horario_inicio") or "").strip()
        end_time = str(item.get("horario_fim") or "").strip()
        name = str(item.get("nome") or "").strip()
        visual_order = int(item.get("ordem_visual") or 0)
        active = bool(int(item.get("ativo", 1) or 0))

        if entry_type == TIPO_GRADE_AULA and lesson_number:
            if not name:
                name = f"Aula {lesson_number}"
            short_label = name
            display_label = build_lesson_display_label(
                lesson_number,
                start_time,
                end_time,
                name,
            )
        else:
            short_label = name or "Intervalo"
            display_label = short_label

        normalized.append(
            {
                **item,
                "id": int(item.get("id") or 0),
                "ordem_visual": visual_order,
                "tipo": entry_type,
                "aula_numero": lesson_number,
                "nome": name,
                "horario_inicio": start_time,
                "horario_fim": end_time,
                "ativo": active,
                "periodo": resolve_lesson_period(lesson_number, start_time),
                "faixa_global": int(lesson_number or 0),
                "label_curta": short_label,
                "label": display_label,
            }
        )

    return sorted(
        normalized,
        key=lambda item: (
            int(item.get("ordem_visual") or 0),
            int(item.get("id") or 0),
        ),
    )


def list_global_lessons(entries: list[dict] | None, *, only_active: bool = True) -> list[dict]:
    lessons = []
    for item in normalize_schedule_entries(entries):
        if item["tipo"] != TIPO_GRADE_AULA:
            continue
        if only_active and not item["ativo"]:
            continue
        lessons.append(item)
    return sorted(
        lessons,
        key=lambda item: (
            int(item.get("aula_numero") or 0),
            int(item.get("ordem_visual") or 0),
            int(item.get("id") or 0),
        ),
    )


def total_configured_lessons(entries: list[dict] | None) -> int:
    lessons = list_global_lessons(entries, only_active=True)
    if not lessons:
        return 0
    return max(int(item.get("aula_numero") or 0) for item in lessons)


def find_lesson_by_number(entries: list[dict] | None, lesson_number: int) -> dict | None:
    lesson_value = int(lesson_number or 0)
    if lesson_value <= 0:
        return None
    for item in list_global_lessons(entries, only_active=False):
        if int(item.get("aula_numero") or 0) == lesson_value:
            return item
    return None


def list_lessons_for_class(class_item: dict | None, entries: list[dict] | None) -> list[dict]:
    start_lesson, end_lesson = resolve_class_lesson_window(class_item)
    turn = str((class_item or {}).get("turno") or "").strip().upper()
    return [
        item
        for item in list_global_lessons(entries, only_active=True)
        if (
            start_lesson <= int(item.get("aula_numero") or 0) <= end_lesson
            and lesson_number_is_allowed_for_turn(
                turn,
                int(item.get("aula_numero") or 0),
            )
        )
    ]


def list_visual_schedule_items_for_class(class_item: dict | None, entries: list[dict] | None) -> list[dict]:
    start_lesson, end_lesson = resolve_class_lesson_window(class_item)
    turn = str((class_item or {}).get("turno") or "").strip().upper()
    normalized = normalize_schedule_entries(entries)
    visible = []

    for index, item in enumerate(normalized):
        if not item["ativo"]:
            continue
        if item["tipo"] == TIPO_GRADE_AULA:
            lesson_number = int(item.get("aula_numero") or 0)
            if (
                start_lesson <= lesson_number <= end_lesson
                and lesson_number_is_allowed_for_turn(turn, lesson_number)
            ):
                visible.append(item)
            continue

        previous_lessons = [
            int(candidate.get("aula_numero") or 0)
            for candidate in normalized[:index]
            if candidate.get("tipo") == TIPO_GRADE_AULA and candidate.get("ativo")
        ]
        next_lessons = [
            int(candidate.get("aula_numero") or 0)
            for candidate in normalized[index + 1 :]
            if candidate.get("tipo") == TIPO_GRADE_AULA and candidate.get("ativo")
        ]
        previous_lesson = previous_lessons[-1] if previous_lessons else 0
        next_lesson = next_lessons[0] if next_lessons else 0
        if (
            previous_lesson
            and next_lesson
            and start_lesson <= previous_lesson < next_lesson <= end_lesson
            and lesson_number_is_allowed_for_turn(turn, previous_lesson)
            and lesson_number_is_allowed_for_turn(turn, next_lesson)
        ):
            visible.append(item)

    return visible


def validate_class_lesson_window(
    start_lesson: int | None,
    end_lesson: int | None,
    entries: list[dict] | None,
) -> tuple[int, int]:
    start_value = int(start_lesson or 0)
    end_value = int(end_lesson or 0)
    if start_value <= 0 or end_value < start_value:
        raise ValueError("A janela de aulas da turma e invalida.")

    available_lessons = {
        int(item.get("aula_numero") or 0)
        for item in list_global_lessons(entries, only_active=True)
    }
    if not available_lessons:
        raise ValueError("Cadastre primeiro as aulas globais da escola.")
    if start_value not in available_lessons or end_value not in available_lessons:
        raise ValueError("A turma precisa usar apenas aulas globais ativas.")
    return start_value, end_value


def validate_schedule_entry(
    *,
    visual_order: int,
    entry_type: str,
    lesson_number: int | None,
    name: str,
    start_time: str,
    end_time: str,
) -> dict:
    clean_type = str(entry_type or "").strip().upper() or TIPO_GRADE_AULA
    if clean_type not in {TIPO_GRADE_AULA, TIPO_GRADE_INTERVALO}:
        raise ValueError("Tipo de item da grade invalido.")

    try:
        order_value = int(visual_order)
    except (TypeError, ValueError) as exc:
        raise ValueError("Ordem visual invalida.") from exc
    if order_value <= 0:
        raise ValueError("Ordem visual invalida.")

    clean_name = str(name or "").strip()
    if not clean_name:
        raise ValueError("Informe um nome para o item da grade.")

    clean_start = str(start_time or "").strip()
    clean_end = str(end_time or "").strip()
    try:
        start_dt = datetime.strptime(clean_start, "%H:%M")
        end_dt = datetime.strptime(clean_end, "%H:%M")
    except ValueError as exc:
        raise ValueError("Use horarios no formato HH:MM.") from exc
    if end_dt <= start_dt:
        raise ValueError("O horario final precisa ser maior que o inicial.")

    normalized_lesson = None
    if clean_type == TIPO_GRADE_AULA:
        try:
            normalized_lesson = int(lesson_number or 0)
        except (TypeError, ValueError) as exc:
            raise ValueError("Numero da aula invalido.") from exc
        if normalized_lesson <= 0:
            raise ValueError("Numero da aula invalido.")

    return {
        "ordem_visual": order_value,
        "tipo": clean_type,
        "aula_numero": normalized_lesson,
        "nome": clean_name,
        "horario_inicio": clean_start,
        "horario_fim": clean_end,
    }
