"""Record operations for pre-conselho."""

from fastapi import HTTPException

from . import repository
from .service import (
    enrich_editable_records,
    get_user_id,
    is_admin_user,
    is_record_editable_for_user,
    is_teacher_user,
    list_active_valid_rav_skills,
    list_active_valid_reasons,
    optional_text,
    require_preconselho_access,
    resolve_teacher,
    validate_classroom,
    validate_discipline,
    validate_period,
    validate_student_in_classroom,
    validate_teacher_filters,
    validate_teacher_scope,
)
from services.preconselho_service import (
    gerar_texto_pre_conselho_individual,
    periodo_editavel_para_cargo,
    validar_motivos_pos_pre_conselho,
    validar_nivel_atencao_pre_conselho,
)


def save_preconselho_record(payload, usuario: dict) -> dict:
    require_preconselho_access(usuario)
    periodo = validate_period(payload.periodo_id)
    turma = validate_classroom(payload.turma_id)
    disciplina = validate_discipline(payload.disciplina_id)
    estudante = validate_student_in_classroom(payload.estudante_id, turma["id"])
    if payload.professor_id is not None and not is_admin_user(usuario):
        raise HTTPException(403, "Apenas administrador pode salvar em nome de outro professor.")
    professor = resolve_teacher(usuario, payload.professor_id, permitir_gestor=True)
    validate_teacher_scope(int(professor["id"]), int(turma["id"]), int(disciplina["id"]))

    if is_teacher_user(usuario) and not periodo_editavel_para_cargo(periodo.get("status"), "PROFESSOR"):
        raise HTTPException(403, "Período fechado para edição do professor.")

    if not payload.sinalizar:
        existente = next(
            (
                item
                for item in repository.list_records(
                    periodo_id=int(periodo["id"]),
                    turma_id=int(turma["id"]),
                    disciplina_id=int(disciplina["id"]),
                    professor_usuario_id=int(professor["id"]),
                    estudante_id=int(estudante["id"]),
                )
            ),
            None,
        )
        if not existente:
            raise HTTPException(400, "Não existe registro salvo para remover.")
        if not is_record_editable_for_user(usuario, existente):
            raise HTTPException(403, "Acesso negado.")
        repository.delete_record(
            int(existente["id"]),
            professor_usuario_id=None if is_admin_user(usuario) else int(professor["id"]),
        )
        return {**existente, "editavel": False}

    motivos = list_active_valid_reasons(payload.motivo_ids)
    observacao_professor = optional_text(
        payload.observacao_professor, "Observação do professor", max_len=1000
    )
    observacao_pos_preconselho = optional_text(
        payload.pos_preconselho_observacao,
        "Observação do pós pré-conselho",
        max_len=1000,
    )
    estudante_em_rav = bool(payload.estudante_em_rav) if bool(periodo.get("tem_rav")) else False
    rav_acoes = (
        optional_text(payload.rav_acoes, "Acoes de RAV", max_len=1000)
        if estudante_em_rav
        else ""
    )
    rav_habilidades = (
        list_active_valid_rav_skills(
            payload.rav_habilidade_ids,
            int(disciplina["id"]),
            int(periodo["id"]),
            int(turma["id"]),
        )
        if estudante_em_rav
        else []
    )
    try:
        nivel_atencao = validar_nivel_atencao_pre_conselho(payload.nivel_atencao)
        (
            pos_preconselho_recuperado,
            pos_preconselho_motivo_ids,
            pos_preconselho_motivos,
        ) = validar_motivos_pos_pre_conselho(
            payload.pos_preconselho_motivo_ids,
            payload.pos_preconselho_recuperado,
            observacao_pos_preconselho,
        )
        texto = gerar_texto_pre_conselho_individual(
            motivos=motivos,
            observacao_professor=observacao_professor,
            nivel_atencao=nivel_atencao,
            estudante_nome=str(estudante["nome"]),
            disciplina_nome=str(disciplina["nome"]),
            pos_preconselho_recuperado=pos_preconselho_recuperado,
            pos_preconselho_motivos=pos_preconselho_motivos,
            pos_preconselho_observacao=observacao_pos_preconselho,
            estudante_em_rav=estudante_em_rav,
        )
        if estudante_em_rav and rav_habilidades:
            texto["texto"] = (
                f"{texto['texto']} Habilidades a recuperar: "
                f"{'; '.join(str(item['descricao']) for item in rav_habilidades)}."
            )
        if estudante_em_rav and rav_acoes:
            texto["texto"] = f"{texto['texto']} Acoes previstas: {rav_acoes}."
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    registro_id = repository.save_record(
        periodo_id=int(periodo["id"]),
        turma_id=int(turma["id"]),
        disciplina_id=int(disciplina["id"]),
        professor_usuario_id=int(professor["id"]),
        estudante_id=int(estudante["id"]),
        ano_letivo=int(periodo["ano_letivo"]),
        etapa=int(periodo["etapa"]),
        disciplina_nome=str(disciplina["nome"]),
        motivo_ids=[int(item["id"]) for item in motivos],
        texto_gerado=texto["texto"],
        observacao_professor=observacao_professor,
        nivel_atencao=nivel_atencao,
        pos_preconselho_recuperado=pos_preconselho_recuperado,
        pos_preconselho_motivo_ids=pos_preconselho_motivo_ids,
        pos_preconselho_observacao=observacao_pos_preconselho,
        estudante_em_rav=estudante_em_rav,
        rav_habilidade_ids=[int(item["id"]) for item in rav_habilidades],
        rav_acoes=rav_acoes,
    )

    registro = repository.get_record(registro_id)
    if not registro:
        raise HTTPException(500, "Falha ao carregar o registro salvo.")
    return {**registro, "editavel": is_record_editable_for_user(usuario, registro)}


def delete_preconselho_record(registro_id: int, usuario: dict) -> dict:
    require_preconselho_access(usuario)
    registro = repository.get_record(registro_id)
    if not registro:
        raise HTTPException(404, "Registro não encontrado.")
    if not is_record_editable_for_user(usuario, registro):
        raise HTTPException(403, "Acesso negado.")

    if not repository.delete_record(
        registro_id,
        professor_usuario_id=None if is_admin_user(usuario) else int(registro["professor_id"]),
    ):
        raise HTTPException(500, "Falha ao excluir o registro.")
    return {"ok": True}


def list_preconselho_records(
    *,
    periodo_id: int,
    turma_id: int | None,
    disciplina_id: int | None,
    professor_id: int | None,
    usuario: dict,
) -> dict:
    require_preconselho_access(usuario)
    validate_period(periodo_id)

    professor_filtro = professor_id
    if is_teacher_user(usuario):
        validate_teacher_filters(
            get_user_id(usuario),
            turma_id=turma_id,
            disciplina_id=disciplina_id,
        )
        professor_filtro = get_user_id(usuario)

    itens = repository.list_records(
        periodo_id=periodo_id,
        turma_id=turma_id,
        disciplina_id=disciplina_id,
        professor_usuario_id=professor_filtro,
    )
    itens = enrich_editable_records(usuario, itens)
    return {"total_registros": len(itens), "itens": itens}
