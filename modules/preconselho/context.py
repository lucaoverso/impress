"""Context and panel flows for pre-conselho."""

from fastapi import HTTPException

from . import repository
from .service import (
    get_teacher_options,
    get_user_id,
    has_manager_access,
    is_admin_user,
    is_teacher_user,
    normalize_user_role,
    require_preconselho_access,
    resolve_teacher,
    validate_classroom,
    validate_discipline,
    validate_period,
    validate_teacher_scope,
    build_teacher_scope,
)
from services.preconselho_service import (
    STATUS_PERIODO_PRE_CONSELHO_ABERTO,
    listar_motivos_pos_pre_conselho,
    listar_niveis_atencao_pre_conselho,
    periodo_editavel_para_cargo,
)


def list_teacher_classroom_disciplines(*, periodo_id: int, professor_id: int) -> list[dict]:
    escopo = build_teacher_scope(professor_id)
    registros = repository.count_records_by_teacher_and_period(
        professor_id=professor_id,
        periodo_id=periodo_id,
    )
    estudantes_por_turma = {
        int(turma["id"]): len(
            repository.list_students(
                nome="",
                incluir_inativos=False,
                turma_id=int(turma["id"]),
            )
        )
        for turma in escopo["turmas"]
    }

    itens = []
    for combinacao in escopo["combinacoes"]:
        turma_id = int(combinacao["turma_id"])
        disciplina_id = int(combinacao["disciplina_id"])
        total_estudantes = int(estudantes_por_turma.get(turma_id, 0))
        total_sinalizados = int(registros.get((turma_id, disciplina_id), 0))
        itens.append(
            {
                "turma_id": turma_id,
                "turma_nome": combinacao["turma_nome"],
                "turno": combinacao.get("turno", "") or "",
                "disciplina_id": disciplina_id,
                "disciplina_nome": combinacao["disciplina_nome"],
                "total_estudantes": total_estudantes,
                "total_sinalizados": total_sinalizados,
                "total_pendentes": max(total_estudantes - total_sinalizados, 0),
            }
        )
    return itens


def build_preconselho_context(usuario: dict) -> dict:
    require_preconselho_access(usuario)
    cargo = normalize_user_role(usuario)
    usuario_id = get_user_id(usuario)
    turmas_professor, disciplinas_professor = (
        get_teacher_options(usuario_id) if is_teacher_user(usuario) else ([], [])
    )
    periodos = repository.list_periods()
    periodo_referencia = next(
        (item for item in periodos if item.get("status") == STATUS_PERIODO_PRE_CONSELHO_ABERTO),
        None,
    )
    minhas_turmas_disciplinas = (
        list_teacher_classroom_disciplines(
            periodo_id=int(periodo_referencia["id"]),
            professor_id=usuario_id,
        )
        if is_teacher_user(usuario) and periodo_referencia
        else []
    )

    professores = []
    if has_manager_access(usuario):
        professores = [
            {
                "id": int(item["id"]),
                "nome": item["nome"],
                "email": item.get("email", ""),
                "label": (
                    f"{item['nome']} ({item.get('email', '')})"
                    if str(item.get("email", "")).strip()
                    else item["nome"]
                ),
            }
            for item in repository.list_available_teachers()
        ]

    return {
        "cargo": cargo,
        "pode_configurar": is_admin_user(usuario),
        "pode_consolidar": has_manager_access(usuario),
        "pode_relatorio": has_manager_access(usuario),
        "pode_editar_periodo_fechado": is_admin_user(usuario),
        "professor_id": usuario_id if is_teacher_user(usuario) else None,
        "professor_nome": str(usuario.get("nome") or "").strip() if is_teacher_user(usuario) else "",
        "periodos": [
            {
                **item,
                "editavel": periodo_editavel_para_cargo(item.get("status"), cargo),
            }
            for item in periodos
        ],
        "turmas": turmas_professor if is_teacher_user(usuario) else repository.list_active_classrooms(),
        "disciplinas": (
            disciplinas_professor if is_teacher_user(usuario) else repository.list_active_disciplines()
        ),
        "motivos": repository.list_reasons(incluir_inativos=is_admin_user(usuario)),
        "rav_habilidades": repository.list_rav_skills(incluir_inativos=is_admin_user(usuario)),
        "professores": professores,
        "niveis_atencao": listar_niveis_atencao_pre_conselho(),
        "motivos_pos_preconselho": listar_motivos_pos_pre_conselho(),
        "minhas_turmas_disciplinas": minhas_turmas_disciplinas,
    }


def list_my_classroom_disciplines(*, periodo_id: int, usuario: dict) -> list[dict]:
    if not is_teacher_user(usuario):
        raise HTTPException(403, "Acesso negado.")
    validate_period(periodo_id)
    return list_teacher_classroom_disciplines(
        periodo_id=int(periodo_id),
        professor_id=get_user_id(usuario),
    )


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
    require_preconselho_access(usuario)
    periodo = validate_period(periodo_id)
    turma = validate_classroom(turma_id)
    disciplina = validate_discipline(disciplina_id)
    professor = resolve_teacher(usuario, professor_id, permitir_gestor=True)
    validate_teacher_scope(int(professor["id"]), int(turma["id"]), int(disciplina["id"]))

    return repository.list_panel_students(
        periodo_id=int(periodo["id"]),
        turma_id=int(turma["id"]),
        disciplina_id=int(disciplina["id"]),
        professor_usuario_id=int(professor["id"]),
        busca_nome=q,
        status=status,
    )
