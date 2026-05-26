from repositories.ocorrencias_repository import (
    STATUS_OCORRENCIA_REGISTRADO,
    atualizar_ocorrencia,
    buscar_ocorrencia_por_id,
    buscar_regimento_itens_por_ids,
    criar_ocorrencia,
    salvar_ocorrencia_estudantes_vinculados,
    salvar_ocorrencia_professores_vinculados,
    salvar_regimento_itens_ocorrencia,
)
from services.ocorrencia_disciplina_service import inferir_gravidade_ocorrencia
from services.ocorrencias_consulta_service import buscar_ocorrencia_service
from services.ocorrencias_contexto_service import resolver_contexto_registro_ocorrencia
from services.ocorrencias_validacao_service import (
    TIPO_REGISTRO_ESTUDANTE,
    TIPO_REGISTRO_PROFESSOR,
    exigir_regimento_item_ids_ocorrencia,
    model_to_dict_ocorrencia,
    normalizar_regimento_item_ids_ocorrencia,
    registro_exige_aula_ocorrencia,
    registro_exige_base_legal_ocorrencia,
    texto_obrigatorio_ocorrencia,
    texto_opcional_ocorrencia,
    validar_acao_aplicada_para_tipo_ocorrencia,
    validar_data_iso_ocorrencia,
    validar_faixa_aula_por_turma_ocorrencia,
    validar_horario_ocorrencia_service,
    validar_status_ocorrencia,
    validar_tipo_registro_ocorrencia,
)


def criar_ocorrencia_service(payload) -> dict:
    tipo_registro = validar_tipo_registro_ocorrencia(getattr(payload, "tipo_registro", None))
    status = validar_status_ocorrencia(
        getattr(payload, "status", None) or STATUS_OCORRENCIA_REGISTRADO
    )
    acao_aplicada = validar_acao_aplicada_para_tipo_ocorrencia(
        getattr(payload, "acao_aplicada", None),
        tipo_registro,
    )
    regimento_item_ids = normalizar_regimento_item_ids_ocorrencia(
        getattr(payload, "regimento_item_ids", None)
    )
    if registro_exige_base_legal_ocorrencia(tipo_registro):
        regimento_item_ids = exigir_regimento_item_ids_ocorrencia(regimento_item_ids)
    else:
        regimento_item_ids = []
    regimento_itens = buscar_regimento_itens_por_ids(regimento_item_ids) if regimento_item_ids else []
    if tipo_registro == TIPO_REGISTRO_ESTUDANTE and regimento_itens:
        inferir_gravidade_ocorrencia(regimento_itens)
    descricao = texto_obrigatorio_ocorrencia(
        getattr(payload, "descricao", None),
        "Descricao",
        max_len=5000,
    )
    contexto = resolver_contexto_registro_ocorrencia(
        tipo_registro=tipo_registro,
        nome_estudante=getattr(payload, "nome_estudante", None),
        estudante_id=getattr(payload, "estudante_id", None),
        estudantes_vinculados=getattr(payload, "estudantes_vinculados", None),
        turma_id=getattr(payload, "turma_id", None),
        professor_requerente=getattr(payload, "professor_requerente", None),
        professor_requerente_id=getattr(payload, "professor_requerente_id", None),
        professores_vinculados=getattr(payload, "professores_vinculados", None),
    )
    turma_id = contexto["turma_id"]
    faixa_aula = (
        validar_faixa_aula_por_turma_ocorrencia(getattr(payload, "aula", None), turma_id)
        if registro_exige_aula_ocorrencia(tipo_registro) and turma_id
        else ""
    )
    disciplina = (
        texto_obrigatorio_ocorrencia(getattr(payload, "disciplina", None), "Disciplina")
        if tipo_registro == TIPO_REGISTRO_ESTUDANTE
        else (texto_opcional_ocorrencia(getattr(payload, "disciplina", None), max_len=255) or "")
    )
    ocorrencia_id = criar_ocorrencia(
        tipo_registro=tipo_registro,
        nome_estudante=contexto["nome_estudante"],
        estudante_id=contexto["estudante_id"],
        turma_id=turma_id,
        professor_requerente=contexto["professor_requerente"],
        professor_requerente_id=contexto["professor_requerente_id"],
        disciplina=disciplina,
        data_ocorrencia=validar_data_iso_ocorrencia(
            getattr(payload, "data_ocorrencia", None),
            "Data da ocorrencia",
        ),
        aula=faixa_aula,
        horario_ocorrencia=validar_horario_ocorrencia_service(
            getattr(payload, "horario_ocorrencia", None)
        ),
        descricao=descricao,
        acao_aplicada=acao_aplicada,
        status=status,
        regimento_item_ids=regimento_item_ids,
        estudantes_vinculados=contexto["estudantes_vinculados"],
        professores_vinculados=contexto["professores_vinculados"],
    )
    return buscar_ocorrencia_service(ocorrencia_id)


def atualizar_ocorrencia_parcial_service(ocorrencia_id: int, payload) -> dict:
    atual = buscar_ocorrencia_por_id(ocorrencia_id)
    if not atual:
        raise LookupError("Ocorrencia nao encontrada.")
    dados_brutos = model_to_dict_ocorrencia(payload, exclude_unset=True)
    if not dados_brutos:
        raise ValueError("Informe ao menos um campo para atualizar.")

    dados_validados = {}
    regimento_item_ids_validados = None
    estudantes_vinculados_para_salvar = None
    professores_vinculados_para_salvar = None
    tipo_registro_atual = validar_tipo_registro_ocorrencia(atual.get("tipo_registro"))
    tipo_registro_merge = validar_tipo_registro_ocorrencia(
        dados_brutos.get("tipo_registro", tipo_registro_atual)
    )
    if "tipo_registro" in dados_brutos:
        dados_validados["tipo_registro"] = tipo_registro_merge

    campos_contexto = {
        "tipo_registro",
        "nome_estudante",
        "estudante_id",
        "estudantes_vinculados",
        "turma_id",
        "professor_requerente",
        "professor_requerente_id",
        "professores_vinculados",
    }
    if campos_contexto & set(dados_brutos.keys()):
        usar_estudantes_atuais = (
            tipo_registro_merge == TIPO_REGISTRO_ESTUDANTE
            and tipo_registro_atual == TIPO_REGISTRO_ESTUDANTE
            and "estudantes_vinculados" not in dados_brutos
        )
        usar_professores_atuais = (
            tipo_registro_merge == TIPO_REGISTRO_PROFESSOR
            and tipo_registro_atual == TIPO_REGISTRO_PROFESSOR
            and "professores_vinculados" not in dados_brutos
        )
        contexto_merge = resolver_contexto_registro_ocorrencia(
            tipo_registro=tipo_registro_merge,
            nome_estudante=(
                dados_brutos.get("nome_estudante")
                if "nome_estudante" in dados_brutos
                else (atual.get("nome_estudante") if tipo_registro_merge == tipo_registro_atual else None)
            ),
            estudante_id=(
                dados_brutos.get("estudante_id")
                if "estudante_id" in dados_brutos
                else (
                    atual.get("estudante_id")
                    if tipo_registro_merge == TIPO_REGISTRO_ESTUDANTE
                    and tipo_registro_atual == TIPO_REGISTRO_ESTUDANTE
                    else None
                )
            ),
            estudantes_vinculados=(
                dados_brutos.get("estudantes_vinculados")
                if "estudantes_vinculados" in dados_brutos
                else (atual.get("estudantes_vinculados") if usar_estudantes_atuais else [])
            ),
            turma_id=dados_brutos.get("turma_id", atual.get("turma_id")),
            professor_requerente=dados_brutos.get(
                "professor_requerente",
                (
                    atual.get("professor_requerente")
                    if tipo_registro_merge == tipo_registro_atual
                    or tipo_registro_merge == TIPO_REGISTRO_ESTUDANTE
                    and tipo_registro_atual == TIPO_REGISTRO_ESTUDANTE
                    else None
                ),
            ),
            professor_requerente_id=dados_brutos.get(
                "professor_requerente_id",
                (
                    atual.get("professor_requerente_id")
                    if tipo_registro_merge == tipo_registro_atual
                    or tipo_registro_merge == TIPO_REGISTRO_ESTUDANTE
                    and tipo_registro_atual == TIPO_REGISTRO_ESTUDANTE
                    else None
                ),
            ),
            professores_vinculados=(
                dados_brutos.get("professores_vinculados")
                if "professores_vinculados" in dados_brutos
                else (atual.get("professores_vinculados") if usar_professores_atuais else [])
            ),
        )
        dados_validados["nome_estudante"] = contexto_merge["nome_estudante"]
        dados_validados["estudante_id"] = contexto_merge["estudante_id"]
        dados_validados["turma_id"] = contexto_merge["turma_id"]
        dados_validados["professor_requerente"] = contexto_merge["professor_requerente"]
        dados_validados["professor_requerente_id"] = contexto_merge["professor_requerente_id"]
        estudantes_vinculados_para_salvar = contexto_merge["estudantes_vinculados"]
        professores_vinculados_para_salvar = contexto_merge["professores_vinculados"]
        if not registro_exige_aula_ocorrencia(tipo_registro_merge):
            dados_validados["aula"] = ""

    if "disciplina" in dados_brutos or "tipo_registro" in dados_brutos:
        disciplina_valor = dados_brutos.get("disciplina", atual.get("disciplina"))
        dados_validados["disciplina"] = (
            texto_obrigatorio_ocorrencia(disciplina_valor, "Disciplina")
            if tipo_registro_merge == TIPO_REGISTRO_ESTUDANTE
            else (texto_opcional_ocorrencia(disciplina_valor, max_len=255) or "")
        )
    if "data_ocorrencia" in dados_brutos:
        dados_validados["data_ocorrencia"] = validar_data_iso_ocorrencia(
            dados_brutos["data_ocorrencia"],
            "Data da ocorrencia",
        )
    if "aula" in dados_brutos and registro_exige_aula_ocorrencia(tipo_registro_merge):
        turma_id_para_aula = dados_validados.get("turma_id", atual.get("turma_id"))
        if turma_id_para_aula:
            dados_validados["aula"] = validar_faixa_aula_por_turma_ocorrencia(
                dados_brutos["aula"],
                int(turma_id_para_aula),
            )
        else:
            dados_validados["aula"] = ""
    elif "turma_id" in dados_validados and registro_exige_aula_ocorrencia(tipo_registro_merge):
        if dados_validados.get("turma_id"):
            dados_validados["aula"] = validar_faixa_aula_por_turma_ocorrencia(
                atual.get("aula"),
                int(dados_validados["turma_id"]),
            )
        else:
            dados_validados["aula"] = ""
    elif "tipo_registro" in dados_brutos and not registro_exige_aula_ocorrencia(tipo_registro_merge):
        dados_validados["aula"] = ""
    if "horario_ocorrencia" in dados_brutos:
        dados_validados["horario_ocorrencia"] = validar_horario_ocorrencia_service(
            dados_brutos["horario_ocorrencia"]
        )
    if "descricao" in dados_brutos:
        dados_validados["descricao"] = texto_obrigatorio_ocorrencia(
            dados_brutos["descricao"],
            "Descricao",
            max_len=5000,
        )
    if "regimento_item_ids" in dados_brutos:
        regimento_item_ids_validados = normalizar_regimento_item_ids_ocorrencia(
            dados_brutos.get("regimento_item_ids")
        )
        if registro_exige_base_legal_ocorrencia(tipo_registro_merge):
            regimento_item_ids_validados = exigir_regimento_item_ids_ocorrencia(
                regimento_item_ids_validados
            )
        else:
            regimento_item_ids_validados = []
    elif "tipo_registro" in dados_brutos and not registro_exige_base_legal_ocorrencia(tipo_registro_merge):
        regimento_item_ids_validados = []
    if "acao_aplicada" in dados_brutos:
        dados_validados["acao_aplicada"] = validar_acao_aplicada_para_tipo_ocorrencia(
            dados_brutos["acao_aplicada"],
            tipo_registro_merge,
        )
    if "status" in dados_brutos:
        dados_validados["status"] = validar_status_ocorrencia(dados_brutos["status"])
    if "tipo_registro" in dados_brutos and "acao_aplicada" not in dados_brutos:
        validar_acao_aplicada_para_tipo_ocorrencia(atual.get("acao_aplicada"), tipo_registro_merge)
    if (
        "tipo_registro" in dados_brutos
        and tipo_registro_merge == TIPO_REGISTRO_ESTUDANTE
        and regimento_item_ids_validados is None
        and not list(atual.get("regimento_itens") or [])
    ):
        raise ValueError("Selecione ao menos uma base legal para vincular a ocorrencia.")
    if not dados_validados and regimento_item_ids_validados is None:
        raise ValueError("Nenhum campo valido informado para atualizacao.")
    if (
        tipo_registro_merge == TIPO_REGISTRO_ESTUDANTE
        and (regimento_item_ids_validados is not None or "acao_aplicada" in dados_validados)
    ):
        itens_para_validar = (
            buscar_regimento_itens_por_ids(regimento_item_ids_validados)
            if regimento_item_ids_validados is not None and regimento_item_ids_validados
            else list(atual.get("regimento_itens") or [])
        )
        inferir_gravidade_ocorrencia(itens_para_validar)

    if dados_validados:
        atualizar_ocorrencia(ocorrencia_id, dados_validados)
    if estudantes_vinculados_para_salvar is not None:
        salvar_ocorrencia_estudantes_vinculados(ocorrencia_id, estudantes_vinculados_para_salvar)
    if professores_vinculados_para_salvar is not None:
        salvar_ocorrencia_professores_vinculados(ocorrencia_id, professores_vinculados_para_salvar)
    if regimento_item_ids_validados is not None:
        salvar_regimento_itens_ocorrencia(ocorrencia_id, regimento_item_ids_validados)
    return buscar_ocorrencia_service(ocorrencia_id)
