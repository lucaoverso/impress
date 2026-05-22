from repositories.preconselho_repository import (
    buscar_registro_pre_conselho_por_id,
    criar_ou_atualizar_registro_pre_conselho,
    excluir_registro_pre_conselho,
    listar_registros_pre_conselho,
)
from services.preconselho_service import (
    gerar_texto_pre_conselho_individual,
    periodo_editavel_para_cargo,
    validar_motivos_pos_pre_conselho,
    validar_nivel_atencao_pre_conselho,
)
from services.preconselho_validacao_service import (
    enriquecer_editavel_preconselho,
    motivos_ativos_validos_preconselho,
    obter_usuario_id_preconselho,
    registro_editavel_usuario_preconselho,
    resolver_professor_preconselho,
    usuario_eh_admin_preconselho,
    usuario_eh_professor_preconselho,
    validar_disciplina_preconselho,
    validar_escopo_professor_preconselho,
    validar_estudante_na_turma_preconselho,
    validar_filtros_professor_preconselho,
    validar_periodo_preconselho,
    validar_texto_opcional_preconselho,
    validar_turma_preconselho,
)


def salvar_registro_preconselho(payload, usuario: dict) -> dict:
    periodo = validar_periodo_preconselho(payload.periodo_id)
    turma = validar_turma_preconselho(payload.turma_id)
    disciplina = validar_disciplina_preconselho(payload.disciplina_id)
    estudante = validar_estudante_na_turma_preconselho(payload.estudante_id, turma["id"])

    if payload.professor_id is not None and not usuario_eh_admin_preconselho(usuario):
        raise PermissionError("Apenas administrador pode salvar em nome de outro professor.")

    professor = resolver_professor_preconselho(
        usuario,
        payload.professor_id,
        permitir_gestor=True,
    )
    validar_escopo_professor_preconselho(
        int(professor["id"]),
        int(turma["id"]),
        int(disciplina["id"]),
    )

    if usuario_eh_professor_preconselho(usuario) and not periodo_editavel_para_cargo(
        periodo.get("status"),
        "PROFESSOR",
    ):
        raise PermissionError("Periodo fechado para edicao do professor.")

    if not payload.sinalizar:
        existente = next(
            (
                item
                for item in listar_registros_pre_conselho(
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
            raise ValueError("Nao existe registro salvo para remover.")
        if not registro_editavel_usuario_preconselho(usuario, existente):
            raise PermissionError("Acesso negado.")
        excluir_registro_pre_conselho(
            int(existente["id"]),
            professor_usuario_id=None if usuario_eh_admin_preconselho(usuario) else int(professor["id"]),
        )
        return {**existente, "editavel": False}

    motivos = motivos_ativos_validos_preconselho(payload.motivo_ids)
    observacao_professor = validar_texto_opcional_preconselho(
        payload.observacao_professor,
        "Observacao do professor",
        max_len=1000,
    )
    observacao_pos_preconselho = validar_texto_opcional_preconselho(
        payload.pos_preconselho_observacao,
        "Observacao do pos pre-conselho",
        max_len=1000,
    )
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
    )

    registro_id = criar_ou_atualizar_registro_pre_conselho(
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
    )
    registro = buscar_registro_pre_conselho_por_id(registro_id)
    if not registro:
        raise RuntimeError("Falha ao carregar o registro salvo.")
    return {
        **registro,
        "editavel": registro_editavel_usuario_preconselho(usuario, registro),
    }


def excluir_registro_preconselho_service(registro_id: int, usuario: dict) -> dict:
    registro = buscar_registro_pre_conselho_por_id(registro_id)
    if not registro:
        raise LookupError("Registro nao encontrado.")
    if not registro_editavel_usuario_preconselho(usuario, registro):
        raise PermissionError("Acesso negado.")

    professor_usuario_id = None
    if not usuario_eh_admin_preconselho(usuario):
        professor_usuario_id = int(registro["professor_id"])

    if not excluir_registro_pre_conselho(
        registro_id,
        professor_usuario_id=professor_usuario_id,
    ):
        raise RuntimeError("Falha ao excluir o registro.")
    return {"ok": True}


def listar_registros_preconselho_service(
    periodo_id: int,
    turma_id: int | None,
    disciplina_id: int | None,
    professor_id: int | None,
    usuario: dict,
) -> dict:
    validar_periodo_preconselho(periodo_id)

    professor_filtro = professor_id
    if usuario_eh_professor_preconselho(usuario):
        professor_filtro = obter_usuario_id_preconselho(usuario)
        validar_filtros_professor_preconselho(
            professor_filtro,
            turma_id=turma_id,
            disciplina_id=disciplina_id,
        )

    itens = listar_registros_pre_conselho(
        periodo_id=periodo_id,
        turma_id=turma_id,
        disciplina_id=disciplina_id,
        professor_usuario_id=professor_filtro,
    )
    itens = enriquecer_editavel_preconselho(usuario, itens)
    return {"total_registros": len(itens), "itens": itens}
