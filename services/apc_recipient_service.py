def recipient_key(item: dict) -> tuple[int, int, int]:
    return (
        int(item.get("professor_id") or 0),
        int(item.get("turma_id") or 0),
        int(item.get("disciplina_id") or 0),
    )


def merge_recipient_options(
    active_recipients: list[dict],
    configured_recipients: list[dict] | None = None,
) -> list[dict]:
    merged = {}
    for item in active_recipients or []:
        key = recipient_key(item)
        if min(key) <= 0:
            continue
        merged[key] = {**item, "vinculo_ativo": True}

    for item in configured_recipients or []:
        key = recipient_key(item)
        if min(key) <= 0 or key in merged:
            continue
        merged[key] = {**item, "vinculo_ativo": False}

    return sorted(
        merged.values(),
        key=lambda item: (
            str(item.get("professor_nome") or "").casefold(),
            not bool(item.get("vinculo_ativo")),
            str(item.get("turma_nome") or "").casefold(),
            str(item.get("disciplina_nome") or "").casefold(),
        ),
    )


def group_recipient_options(recipients: list[dict]) -> list[dict]:
    teachers = {}
    for item in recipients or []:
        professor_id = int(item.get("professor_id") or 0)
        group = teachers.setdefault(
            professor_id,
            {
                "professor_id": professor_id,
                "professor_nome": str(item.get("professor_nome") or "").strip(),
                "professor_email": str(item.get("professor_email") or "").strip(),
                "destinatarios": [],
            },
        )
        subject_name = str(item.get("disciplina_nome") or "").strip()
        class_name = str(item.get("turma_nome") or "").strip()
        active = bool(item.get("vinculo_ativo", True))
        label = f"{subject_name} - {class_name}".strip(" -")
        group["destinatarios"].append(
            {
                "professor_id": professor_id,
                "turma_id": int(item.get("turma_id") or 0),
                "turma_nome": class_name,
                "disciplina_id": int(item.get("disciplina_id") or 0),
                "disciplina_nome": subject_name,
                "label": label,
                "vinculo_ativo": active,
            }
        )
    return list(teachers.values())
