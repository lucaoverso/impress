"""Helper functions for pre-conselho consolidated/report outputs."""

from collections import Counter

from . import repository


def unique_text_list(values) -> list[str]:
    items = []
    for value in values or []:
        text = str(value or "").strip()
        if text and text not in items:
            items.append(text)
    return items


def format_natural_list(values) -> str:
    items = unique_text_list(values)
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} e {items[1]}"
    return f"{', '.join(items[:-1])} e {items[-1]}"


def build_report_item(
    *,
    name: str = "",
    nome: str = "",
    total_records: int = 0,
    total_registros: int | None = None,
    extra: str = "",
    item_id: int | None = None,
) -> dict:
    item_name = str(nome or name or "").strip()
    total_item = int(total_registros) if total_registros is not None else int(total_records or 0)
    return {
        "id": int(item_id) if item_id is not None else None,
        "nome": item_name,
        "total_registros": total_item,
        "extra": str(extra or "").strip(),
    }


def map_teaching_staff_by_classrooms(classrooms: dict[int, str]) -> dict[int, dict]:
    valid_classrooms = {
        int(classroom_id): str(classroom_name or "").strip()
        for classroom_id, classroom_name in (classrooms or {}).items()
        if int(classroom_id) > 0 and str(classroom_name or "").strip()
    }
    if not valid_classrooms:
        return {}

    teachers_by_classroom = {
        classroom_id: {
            "nomes": [],
            "corpo_docente": [],
        }
        for classroom_id in valid_classrooms
    }

    def register_teacher(classroom_id: int, teacher_name: str, disciplines=None):
        name = str(teacher_name or "").strip()
        disciplines_list = unique_text_list(disciplines or [])
        if not name:
            return

        block = teachers_by_classroom.setdefault(
            classroom_id,
            {"nomes": [], "corpo_docente": []},
        )
        if name not in block["nomes"]:
            block["nomes"].append(name)
            block["corpo_docente"].append(
                {
                    "professor_nome": name,
                    "disciplinas": list(disciplines_list),
                }
            )
            return

        for item in block["corpo_docente"]:
            if item.get("professor_nome") != name:
                continue
            item["disciplinas"] = unique_text_list(
                list(item.get("disciplinas") or []) + list(disciplines_list)
            )
            break

    for classroom_id in sorted(valid_classrooms):
        assignments = repository.list_teacher_assignments(classroom_id=classroom_id, incluir_inativos=False)
        admin_links = repository.list_admin_classroom_disciplines(
            classroom_id=classroom_id,
            incluir_inativos=False,
        )
        for item in assignments:
            register_teacher(
                classroom_id,
                item.get("professor_nome"),
                [item.get("disciplina_nome")],
            )
        for item in admin_links:
            register_teacher(
                classroom_id,
                item.get("professor_nome"),
                [item.get("disciplina_nome")],
            )

    teachers = repository.list_available_teachers()
    workloads = repository.list_teacher_workloads_by_user_ids(
        [int(item["id"]) for item in teachers if int(item.get("id") or 0) > 0]
    )
    for classroom_id, classroom_name in valid_classrooms.items():
        classroom_name_casefold = classroom_name.casefold()
        for teacher in teachers:
            teacher_id = int(teacher.get("id") or 0)
            if teacher_id <= 0:
                continue

            workload = workloads.get(teacher_id, {})
            workload_classrooms = {
                str(item or "").strip().casefold()
                for item in (workload.get("turmas") or [])
                if str(item or "").strip()
            }
            if classroom_name_casefold in workload_classrooms:
                register_teacher(
                    classroom_id,
                    teacher.get("nome"),
                    workload.get("disciplinas") or [],
                )

    return {
        classroom_id: data
        for classroom_id, data in teachers_by_classroom.items()
        if data.get("nomes")
    }


def map_teachers_by_classroom(records: list[dict]) -> dict[int, dict]:
    classrooms = {}
    for record in records or []:
        classroom_id = int(record.get("turma_id") or 0)
        classroom_name = str(record.get("turma_nome") or "").strip()
        if classroom_id > 0 and classroom_name:
            classrooms[classroom_id] = classroom_name

    return map_teaching_staff_by_classrooms(classrooms)


def enrich_teachers_in_records(records: list[dict]) -> list[dict]:
    mapping = map_teachers_by_classroom(records)
    return [
        {
            **item,
            "professores_turma": list(
                (mapping.get(int(item.get("turma_id") or 0), {}) or {}).get("nomes", [])
            ),
            "corpo_docente_turma": list(
                (mapping.get(int(item.get("turma_id") or 0), {}) or {}).get("corpo_docente", [])
            ),
        }
        for item in (records or [])
    ]


def group_students(records: list[dict]) -> list[dict]:
    grouped = {}
    for record in records or []:
        student_id = int(record.get("estudante_id") or 0)
        if student_id <= 0:
            continue

        item = grouped.setdefault(
            student_id,
            {
                "id": student_id,
                "nome": str(record.get("estudante_nome") or "").strip(),
                "turma_id": int(record.get("turma_id") or 0),
                "turma_nome": str(record.get("turma_nome") or "").strip(),
                "total_registros": 0,
                "disciplinas": [],
                "professores": [],
                "niveis": [],
            },
        )
        item["total_registros"] += 1
        item["disciplinas"] = unique_text_list(
            list(item["disciplinas"]) + [record.get("disciplina_nome")]
        )
        item["professores"] = unique_text_list(
            list(item["professores"]) + [record.get("professor_nome")]
        )
        item["niveis"] = unique_text_list(
            list(item["niveis"]) + [record.get("nivel_atencao")]
        )
    return list(grouped.values())


def group_teachers(records: list[dict]) -> list[dict]:
    grouped = {}
    for record in records or []:
        teacher_id = int(record.get("professor_id") or 0)
        if teacher_id <= 0:
            continue

        item = grouped.setdefault(
            teacher_id,
            {
                "id": teacher_id,
                "nome": str(record.get("professor_nome") or "").strip(),
                "total_registros": 0,
                "turmas": [],
                "disciplinas": [],
            },
        )
        item["total_registros"] += 1
        item["turmas"] = unique_text_list(list(item["turmas"]) + [record.get("turma_nome")])
        item["disciplinas"] = unique_text_list(
            list(item["disciplinas"]) + [record.get("disciplina_nome")]
        )
    return list(grouped.values())


def collect_frequent_reasons(
    records: list[dict],
    *,
    limit: int = 5,
    limite: int | None = None,
) -> list[dict]:
    limite_consulta = int(limite) if limite is not None else int(limit)
    counter = Counter()
    for record in records or []:
        for reason in record.get("motivos") or []:
            description = str(reason.get("descricao") or "").strip()
            if description:
                counter[description] += 1

    return [
        build_report_item(name=description, total_records=total)
        for description, total in counter.most_common(limite_consulta)
    ]


def attention_level_label(level: str, levels_map: dict[str, str]) -> str:
    clean_level = str(level or "").strip()
    if not clean_level:
        return ""
    return levels_map.get(clean_level, clean_level.capitalize())
