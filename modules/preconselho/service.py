"""Business rules and validations for pre-conselho."""

from datetime import datetime

from fastapi import HTTPException

from routers.common import normalizar_cargo_usuario, usuario_tem_acesso_coordenacao

from . import repository
from services.preconselho_service import periodo_editavel_para_cargo


def normalize_user_role(usuario: dict) -> str:
    return normalizar_cargo_usuario(usuario)


def require_preconselho_access(usuario: dict):
    if normalize_user_role(usuario) not in {"ADMIN", "COORDENADOR", "PROFESSOR"}:
        raise HTTPException(403, "Acesso negado.")
    return usuario


def require_admin_access(usuario: dict):
    if normalize_user_role(usuario) != "ADMIN":
        raise HTTPException(403, "Acesso negado.")
    return usuario


def get_user_id(usuario: dict) -> int:
    try:
        valor = int(usuario.get("id"))
    except (TypeError, ValueError) as exc:
        raise HTTPException(401, "Usuário inválido.") from exc
    if valor <= 0:
        raise HTTPException(401, "Usuário inválido.")
    return valor


def is_admin_user(usuario: dict) -> bool:
    return normalize_user_role(usuario) == "ADMIN"


def has_manager_access(usuario: dict) -> bool:
    return usuario_tem_acesso_coordenacao(usuario)


def is_teacher_user(usuario: dict) -> bool:
    return normalize_user_role(usuario) == "PROFESSOR"


def require_text(valor: str, campo: str, *, max_len: int = 255) -> str:
    texto = str(valor or "").strip()
    if not texto:
        raise HTTPException(400, f"{campo} é obrigatório.")
    if len(texto) > max_len:
        raise HTTPException(400, f"{campo} excede o limite de {max_len} caracteres.")
    return texto


def optional_text(valor: str | None, campo: str, *, max_len: int = 1000) -> str:
    texto = str(valor or "").strip()
    if not texto:
        return ""
    if len(texto) > max_len:
        raise HTTPException(400, f"{campo} excede o limite de {max_len} caracteres.")
    return texto


def validate_iso_date(valor: str, campo: str) -> str:
    texto = require_text(valor, campo, max_len=20)
    try:
        data = datetime.strptime(texto, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(400, f"{campo} inválida. Use o formato YYYY-MM-DD.") from exc
    return data.isoformat()


def validate_period(periodo_id: int, *, get_period=repository.get_period) -> dict:
    try:
        periodo_id_valor = int(periodo_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(400, "Período inválido.") from exc
    periodo = get_period(periodo_id_valor)
    if not periodo:
        raise HTTPException(404, "Período não encontrado.")
    return periodo


def validate_classroom(turma_id: int, *, get_classroom=repository.get_classroom) -> dict:
    try:
        turma_id_valor = int(turma_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(400, "Turma inválida.") from exc
    turma = get_classroom(turma_id_valor)
    if not turma:
        raise HTTPException(404, "Turma não encontrada.")
    return turma


def validate_discipline(disciplina_id: int, *, get_discipline=repository.get_discipline) -> dict:
    try:
        disciplina_id_valor = int(disciplina_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(400, "Disciplina inválida.") from exc
    disciplina = get_discipline(disciplina_id_valor)
    if not disciplina:
        raise HTTPException(404, "Disciplina não encontrada.")
    return disciplina


def validate_student_in_classroom(
    estudante_id: int,
    turma_id: int,
    *,
    get_student=repository.get_student,
) -> dict:
    try:
        estudante_id_valor = int(estudante_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(400, "Estudante inválido.") from exc
    estudante = get_student(estudante_id_valor)
    if not estudante:
        raise HTTPException(404, "Estudante não encontrado.")
    if int(estudante.get("turma_id") or 0) != int(turma_id):
        raise HTTPException(400, "O estudante não pertence à turma selecionada.")
    return estudante


def resolve_teacher(
    usuario: dict,
    professor_id: int | None = None,
    *,
    permitir_gestor: bool = False,
    get_user=repository.get_user,
) -> dict:
    cargo = normalize_user_role(usuario)
    usuario_id = get_user_id(usuario)

    if cargo == "PROFESSOR":
        if professor_id in (None, usuario_id):
            return {"id": usuario_id, "nome": str(usuario.get("nome") or "").strip()}
        if not (permitir_gestor and has_manager_access(usuario)):
            raise HTTPException(403, "Acesso negado.")

    if not permitir_gestor or not has_manager_access(usuario):
        raise HTTPException(403, "Acesso negado.")
    if professor_id is None:
        raise HTTPException(400, "Professor obrigatório.")

    professor = get_user(int(professor_id))
    if not professor or normalize_user_role(professor) != "PROFESSOR":
        raise HTTPException(404, "Professor não encontrado.")
    return {"id": int(professor["id"]), "nome": professor["nome"]}


def build_legacy_teacher_scope(
    usuario_id: int,
    *,
    list_teacher_workloads_by_user_ids=repository.list_teacher_workloads_by_user_ids,
    list_active_classrooms=repository.list_active_classrooms,
    list_active_disciplines=repository.list_active_disciplines,
) -> dict:
    carga = list_teacher_workloads_by_user_ids([usuario_id]).get(usuario_id, {})
    nomes_turmas = {
        str(item).strip().casefold() for item in carga.get("turmas") or [] if str(item).strip()
    }
    nomes_disciplinas = {
        str(item).strip().casefold() for item in carga.get("disciplinas") or [] if str(item).strip()
    }

    turmas = [
        dict(item)
        for item in list_active_classrooms()
        if str(item.get("nome") or "").strip().casefold() in nomes_turmas
    ]
    disciplinas = [
        dict(item)
        for item in list_active_disciplines()
        if str(item.get("nome") or "").strip().casefold() in nomes_disciplinas
    ]
    combinacoes = []
    for turma in turmas:
        for disciplina in disciplinas:
            combinacoes.append(
                {
                    "turma_id": int(turma["id"]),
                    "turma_nome": turma.get("nome", "") or "",
                    "turno": turma.get("turno", "") or "",
                    "disciplina_id": int(disciplina["id"]),
                    "disciplina_nome": disciplina.get("nome", "") or "",
                }
            )

    return {
        "usa_atribuicoes_exatas": False,
        "turmas": turmas,
        "disciplinas": disciplinas,
        "combinacoes": combinacoes,
    }


def build_teacher_scope(
    usuario_id: int,
    *,
    list_teacher_assignments_by_user_ids=repository.list_teacher_assignments_by_user_ids,
    build_legacy_scope=build_legacy_teacher_scope,
) -> dict:
    atribuicoes = list_teacher_assignments_by_user_ids(
        [usuario_id],
        incluir_inativos=False,
    ).get(usuario_id, [])
    if not atribuicoes:
        return build_legacy_scope(usuario_id)

    turmas_por_id = {}
    disciplinas_por_id = {}
    combinacoes = []
    for atribuicao in atribuicoes:
        turma_id = int(atribuicao["turma_id"])
        disciplina_id = int(atribuicao["disciplina_id"])
        if turma_id not in turmas_por_id:
            turmas_por_id[turma_id] = {
                "id": turma_id,
                "nome": atribuicao.get("turma_nome", "") or "",
                "turno": atribuicao.get("turno", "") or "",
            }
        if disciplina_id not in disciplinas_por_id:
            disciplinas_por_id[disciplina_id] = {
                "id": disciplina_id,
                "nome": atribuicao.get("disciplina_nome", "") or "",
            }
        combinacoes.append(
            {
                "turma_id": turma_id,
                "turma_nome": atribuicao.get("turma_nome", "") or "",
                "turno": atribuicao.get("turno", "") or "",
                "disciplina_id": disciplina_id,
                "disciplina_nome": atribuicao.get("disciplina_nome", "") or "",
            }
        )

    turmas = sorted(
        turmas_por_id.values(),
        key=lambda item: (str(item.get("nome") or "").casefold(), int(item.get("id") or 0)),
    )
    disciplinas = sorted(
        disciplinas_por_id.values(),
        key=lambda item: (str(item.get("nome") or "").casefold(), int(item.get("id") or 0)),
    )
    combinacoes.sort(
        key=lambda item: (
            str(item.get("turma_nome") or "").casefold(),
            str(item.get("disciplina_nome") or "").casefold(),
            int(item.get("turma_id") or 0),
            int(item.get("disciplina_id") or 0),
        )
    )

    return {
        "usa_atribuicoes_exatas": True,
        "turmas": turmas,
        "disciplinas": disciplinas,
        "combinacoes": combinacoes,
    }


def get_teacher_options(usuario_id: int) -> tuple[list[dict], list[dict]]:
    escopo = build_teacher_scope(usuario_id)
    return escopo["turmas"], escopo["disciplinas"]


def validate_teacher_scope(professor_id: int, turma_id: int, disciplina_id: int):
    escopo = build_teacher_scope(professor_id)
    turma_ids = {int(item["id"]) for item in escopo["turmas"]}
    disciplina_ids = {int(item["id"]) for item in escopo["disciplinas"]}
    turma_id_valor = int(turma_id)
    disciplina_id_valor = int(disciplina_id)

    if turma_id_valor not in turma_ids:
        raise HTTPException(403, "Turma fora da carga do professor.")
    if disciplina_id_valor not in disciplina_ids:
        raise HTTPException(403, "Disciplina fora da carga do professor.")
    if escopo["usa_atribuicoes_exatas"]:
        combinacoes = {
            (int(item["turma_id"]), int(item["disciplina_id"])) for item in escopo["combinacoes"]
        }
        if (turma_id_valor, disciplina_id_valor) not in combinacoes:
            raise HTTPException(403, "Disciplina fora da atribuição docente da turma selecionada.")
    return escopo["turmas"], escopo["disciplinas"]


def validate_teacher_filters(
    professor_id: int,
    *,
    turma_id: int | None = None,
    disciplina_id: int | None = None,
):
    escopo = build_teacher_scope(professor_id)
    turma_ids = {int(item["id"]) for item in escopo["turmas"]}
    disciplina_ids = {int(item["id"]) for item in escopo["disciplinas"]}

    if turma_id is not None and int(turma_id) not in turma_ids:
        raise HTTPException(403, "Turma fora da carga do professor.")
    if disciplina_id is not None and int(disciplina_id) not in disciplina_ids:
        raise HTTPException(403, "Disciplina fora da carga do professor.")
    if escopo["usa_atribuicoes_exatas"] and turma_id is not None and disciplina_id is not None:
        combinacoes = {
            (int(item["turma_id"]), int(item["disciplina_id"])) for item in escopo["combinacoes"]
        }
        if (int(turma_id), int(disciplina_id)) not in combinacoes:
            raise HTTPException(403, "Disciplina fora da atribuição docente da turma selecionada.")


def list_active_valid_reasons(
    motivo_ids: list[int],
    *,
    get_reasons_by_ids=repository.get_reasons_by_ids,
) -> list[dict]:
    motivos = get_reasons_by_ids(motivo_ids)
    ids_recebidos = {int(valor) for valor in motivo_ids or [] if int(valor) > 0}
    ids_encontrados = {int(item["id"]) for item in motivos if int(item.get("ativo") or 0) == 1}
    if ids_recebidos != ids_encontrados:
        raise HTTPException(400, "Existe motivo inválido ou inativo na seleção.")
    return motivos


def list_active_valid_rav_skills(
    habilidade_ids: list[int],
    disciplina_id: int,
    periodo_id: int | None = None,
    turma_id: int | None = None,
    *,
    get_rav_skills_by_ids=repository.get_rav_skills_by_ids,
) -> list[dict]:
    habilidades = get_rav_skills_by_ids(habilidade_ids)
    ids_recebidos = {int(valor) for valor in habilidade_ids or [] if int(valor) > 0}
    ids_encontrados = {
        int(item["id"])
        for item in habilidades
        if int(item.get("ativo") or 0) == 1
        and int(item.get("disciplina_id") or 0) == int(disciplina_id)
        and (periodo_id is None or int(item.get("periodo_id") or 0) == int(periodo_id))
        and (
            turma_id is None
            or int(turma_id) in {int(valor) for valor in item.get("turma_ids") or []}
        )
    }
    if ids_recebidos != ids_encontrados:
        raise HTTPException(400, "Existe habilidade de RAV invÃ¡lida, inativa ou fora da disciplina.")
    return habilidades


def is_record_editable_for_user(usuario: dict, registro: dict) -> bool:
    if is_admin_user(usuario):
        return True
    if is_teacher_user(usuario):
        return int(registro.get("professor_id") or 0) == get_user_id(
            usuario
        ) and periodo_editavel_para_cargo(registro.get("periodo_status"), "PROFESSOR")
    return False


def enrich_editable_records(usuario: dict, itens: list[dict]) -> list[dict]:
    return [{**item, "editavel": is_record_editable_for_user(usuario, item)} for item in itens]


def save_preconselho_record(payload, usuario: dict) -> dict:
    from .records import save_preconselho_record as _save_preconselho_record

    return _save_preconselho_record(payload, usuario)


def delete_preconselho_record(registro_id: int, usuario: dict) -> dict:
    from .records import delete_preconselho_record as _delete_preconselho_record

    return _delete_preconselho_record(registro_id, usuario)


def review_preconselho_record(registro_id: int, payload, usuario: dict) -> dict:
    from .records import review_preconselho_record as _review_preconselho_record

    return _review_preconselho_record(registro_id, payload, usuario)


def list_preconselho_records(
    *,
    periodo_id: int,
    turma_id: int | None,
    disciplina_id: int | None,
    professor_id: int | None,
    usuario: dict,
) -> dict:
    from .records import list_preconselho_records as _list_preconselho_records

    return _list_preconselho_records(
        periodo_id=periodo_id,
        turma_id=turma_id,
        disciplina_id=disciplina_id,
        professor_id=professor_id,
        usuario=usuario,
    )


def build_preconselho_context(usuario: dict) -> dict:
    from .context import build_preconselho_context as _build_preconselho_context

    return _build_preconselho_context(usuario)


def list_my_classroom_disciplines(*, periodo_id: int, usuario: dict) -> list[dict]:
    from .context import list_my_classroom_disciplines as _list_my_classroom_disciplines

    return _list_my_classroom_disciplines(periodo_id=periodo_id, usuario=usuario)


def list_panel_students(
    *,
    periodo_id: int,
    turma_id: int,
    disciplina_id: int,
    q: str,
    status: str,
    professor_id: int | None,
    usuario: dict,
) -> list[dict]:
    from .context import list_panel_students as _list_panel_students

    return _list_panel_students(
        periodo_id=periodo_id,
        turma_id=turma_id,
        disciplina_id=disciplina_id,
        q=q,
        status=status,
        professor_id=professor_id,
        usuario=usuario,
    )


def list_preconselho_periods(usuario: dict) -> list[dict]:
    from .admin import list_preconselho_periods as _list_preconselho_periods

    return _list_preconselho_periods(usuario)


def create_preconselho_period(payload, usuario: dict) -> dict:
    from .admin import create_preconselho_period as _create_preconselho_period

    return _create_preconselho_period(payload, usuario)


def update_preconselho_period(periodo_id: int, payload, usuario: dict) -> dict:
    from .admin import update_preconselho_period as _update_preconselho_period

    return _update_preconselho_period(periodo_id, payload, usuario)


def update_preconselho_period_status(periodo_id: int, payload, usuario: dict) -> dict:
    from .admin import update_preconselho_period_status as _update_preconselho_period_status

    return _update_preconselho_period_status(periodo_id, payload, usuario)


def list_preconselho_reasons(*, incluir_inativos: bool, usuario: dict) -> list[dict]:
    from .admin import list_preconselho_reasons as _list_preconselho_reasons

    return _list_preconselho_reasons(incluir_inativos=incluir_inativos, usuario=usuario)


def list_preconselho_rav_skills(
    *,
    periodo_id: int | None,
    disciplina_id: int | None,
    turma_id: int | None,
    incluir_inativos: bool,
    usuario: dict,
) -> list[dict]:
    from .admin import list_preconselho_rav_skills as _list_preconselho_rav_skills

    return _list_preconselho_rav_skills(
        periodo_id=periodo_id,
        disciplina_id=disciplina_id,
        turma_id=turma_id,
        incluir_inativos=incluir_inativos,
        usuario=usuario,
    )


def create_preconselho_rav_skill(payload, usuario: dict) -> dict:
    from .admin import create_preconselho_rav_skill as _create_preconselho_rav_skill

    return _create_preconselho_rav_skill(payload, usuario)


def update_preconselho_rav_skill(habilidade_id: int, payload, usuario: dict) -> dict:
    from .admin import update_preconselho_rav_skill as _update_preconselho_rav_skill

    return _update_preconselho_rav_skill(habilidade_id, payload, usuario)


def update_preconselho_rav_skill_status(habilidade_id: int, payload, usuario: dict) -> dict:
    from .admin import (
        update_preconselho_rav_skill_status as _update_preconselho_rav_skill_status,
    )

    return _update_preconselho_rav_skill_status(habilidade_id, payload, usuario)


def import_preconselho_rav_skills(payload, usuario: dict) -> dict:
    from .admin import import_preconselho_rav_skills as _import_preconselho_rav_skills

    return _import_preconselho_rav_skills(payload, usuario)


def create_preconselho_reason(payload, usuario: dict) -> dict:
    from .admin import create_preconselho_reason as _create_preconselho_reason

    return _create_preconselho_reason(payload, usuario)


def update_preconselho_reason(motivo_id: int, payload, usuario: dict) -> dict:
    from .admin import update_preconselho_reason as _update_preconselho_reason

    return _update_preconselho_reason(motivo_id, payload, usuario)


def update_preconselho_reason_status(motivo_id: int, payload, usuario: dict) -> dict:
    from .admin import update_preconselho_reason_status as _update_preconselho_reason_status

    return _update_preconselho_reason_status(motivo_id, payload, usuario)


def list_preconselho_attention_levels(usuario: dict) -> list[dict]:
    from .admin import list_preconselho_attention_levels as _list_preconselho_attention_levels

    return _list_preconselho_attention_levels(usuario)


def build_preconselho_consolidated(
    *,
    periodo_id: int,
    turma_id: int | None,
    disciplina_id: int | None,
    professor_id: int | None,
    usuario: dict,
    versao: str = "preconselho",
    enrich_teachers_in_records=None,
) -> dict:
    from .reports import build_preconselho_consolidated as _build_preconselho_consolidated

    return _build_preconselho_consolidated(
        periodo_id=periodo_id,
        turma_id=turma_id,
        disciplina_id=disciplina_id,
        professor_id=professor_id,
        versao=versao,
        usuario=usuario,
        enrich_teachers_in_records=enrich_teachers_in_records,
    )


def build_preconselho_report(
    *,
    periodo_id: int,
    usuario: dict,
    map_teaching_staff_by_classrooms=None,
    group_students=None,
    group_teachers=None,
    collect_frequent_reasons=None,
    build_report_item=None,
    format_natural_list=None,
    attention_level_label=None,
) -> dict:
    from .reports import build_preconselho_report as _build_preconselho_report

    return _build_preconselho_report(
        periodo_id=periodo_id,
        usuario=usuario,
        map_teaching_staff_by_classrooms=map_teaching_staff_by_classrooms,
        group_students=group_students,
        group_teachers=group_teachers,
        collect_frequent_reasons=collect_frequent_reasons,
        build_report_item=build_report_item,
        format_natural_list=format_natural_list,
        attention_level_label=attention_level_label,
    )


def build_preconselho_rav_view(
    *,
    periodo_id: int,
    turma_id: int | None,
    usuario: dict,
) -> dict:
    from .reports import build_preconselho_rav_view as _build_preconselho_rav_view

    return _build_preconselho_rav_view(
        periodo_id=periodo_id,
        turma_id=turma_id,
        usuario=usuario,
    )


def preview_preconselho_text(payload, usuario: dict) -> dict:
    from .text_preview import preview_preconselho_text as _preview_preconselho_text

    return _preview_preconselho_text(payload, usuario)


def list_preconselho_periods(usuario: dict) -> list[dict]:
    from .admin import list_preconselho_periods as _list_preconselho_periods

    return _list_preconselho_periods(usuario)


def create_preconselho_period(payload, usuario: dict) -> dict:
    from .admin import create_preconselho_period as _create_preconselho_period

    return _create_preconselho_period(payload, usuario)


def update_preconselho_period(periodo_id: int, payload, usuario: dict) -> dict:
    from .admin import update_preconselho_period as _update_preconselho_period

    return _update_preconselho_period(periodo_id, payload, usuario)


def update_preconselho_period_status(periodo_id: int, payload, usuario: dict) -> dict:
    from .admin import (
        update_preconselho_period_status as _update_preconselho_period_status,
    )

    return _update_preconselho_period_status(periodo_id, payload, usuario)


def list_preconselho_reasons(*, incluir_inativos: bool, usuario: dict) -> list[dict]:
    from .admin import list_preconselho_reasons as _list_preconselho_reasons

    return _list_preconselho_reasons(
        incluir_inativos=incluir_inativos,
        usuario=usuario,
    )


def create_preconselho_reason(payload, usuario: dict) -> dict:
    from .admin import create_preconselho_reason as _create_preconselho_reason

    return _create_preconselho_reason(payload, usuario)


def update_preconselho_reason(motivo_id: int, payload, usuario: dict) -> dict:
    from .admin import update_preconselho_reason as _update_preconselho_reason

    return _update_preconselho_reason(motivo_id, payload, usuario)


def update_preconselho_reason_status(motivo_id: int, payload, usuario: dict) -> dict:
    from .admin import (
        update_preconselho_reason_status as _update_preconselho_reason_status,
    )

    return _update_preconselho_reason_status(motivo_id, payload, usuario)


def list_preconselho_attention_levels(usuario: dict) -> list[dict]:
    from .admin import (
        list_preconselho_attention_levels as _list_preconselho_attention_levels,
    )

    return _list_preconselho_attention_levels(usuario)
