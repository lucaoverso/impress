from collections import Counter
from datetime import date, datetime
from sqlite3 import IntegrityError

from fastapi import HTTPException

from repositories.preconselho_repository import (
    atualizar_motivo_pre_conselho_dados as atualizar_motivo_pre_conselho_dados_repo,
    atualizar_periodo_pre_conselho_dados as atualizar_periodo_pre_conselho_dados_repo,
    atualizar_status_motivo_pre_conselho as atualizar_status_motivo_pre_conselho_repo,
    atualizar_status_periodo_pre_conselho as atualizar_status_periodo_pre_conselho_repo,
    buscar_motivo_pre_conselho_por_id as buscar_motivo_pre_conselho_por_id_repo,
    buscar_periodo_pre_conselho_por_id as buscar_periodo_pre_conselho_por_id_repo,
    criar_motivo_pre_conselho as criar_motivo_pre_conselho_repo,
    criar_periodo_pre_conselho as criar_periodo_pre_conselho_repo,
    listar_motivos_pre_conselho as listar_motivos_pre_conselho_repo,
)


STATUS_PERIODO_PRE_CONSELHO_ABERTO = "ABERTO"
STATUS_PERIODO_PRE_CONSELHO_FECHADO = "FECHADO"
STATUS_PERIODO_PRE_CONSELHO_VALIDOS = (
    STATUS_PERIODO_PRE_CONSELHO_ABERTO,
    STATUS_PERIODO_PRE_CONSELHO_FECHADO,
)

NIVEIS_ATENCAO_PRE_CONSELHO = (
    {"id": "baixo", "nome": "Baixo"},
    {"id": "medio", "nome": "Médio"},
    {"id": "alto", "nome": "Alto"},
)

CATEGORIAS_MOTIVO_PRE_CONSELHO = (
    "avaliacao",
    "participacao",
    "comportamento",
    "frequencia",
    "organizacao_estudo",
    "dificuldades_pedagogicas",
)

MOTIVOS_PRE_CONSELHO_INICIAIS = (
    {
        "categoria": "avaliacao",
        "codigo": "nao_fez_prova_bimestral",
        "descricao": "Não fez a prova bimestral",
        "ordem": 10,
    },
    {
        "categoria": "avaliacao",
        "codigo": "nao_entregou_trabalho",
        "descricao": "Não entregou o trabalho",
        "ordem": 20,
    },
    {
        "categoria": "avaliacao",
        "codigo": "nao_realizou_atividades_avaliativas",
        "descricao": "Não realizou atividades avaliativas",
        "ordem": 30,
    },
    {
        "categoria": "avaliacao",
        "codigo": "nota_abaixo_esperado",
        "descricao": "Teve nota abaixo do esperado",
        "ordem": 40,
    },
    {
        "categoria": "participacao",
        "codigo": "baixa_participacao_aula",
        "descricao": "Baixa participação em aula",
        "ordem": 50,
    },
    {
        "categoria": "participacao",
        "codigo": "pouco_engajamento_atividades",
        "descricao": "Pouco engajamento nas atividades",
        "ordem": 60,
    },
    {
        "categoria": "dificuldades_pedagogicas",
        "codigo": "dificuldade_acompanhar_explicacoes",
        "descricao": "Dificuldade em acompanhar explicações",
        "ordem": 70,
    },
    {
        "categoria": "comportamento",
        "codigo": "conversas_excessivas_em_aula",
        "descricao": "Conversas excessivas em aula",
        "ordem": 80,
    },
    {
        "categoria": "comportamento",
        "codigo": "nao_respeita_combinados",
        "descricao": "Não respeita combinados",
        "ordem": 90,
    },
    {
        "categoria": "comportamento",
        "codigo": "comportamento_inadequado_sala",
        "descricao": "Comportamento inadequado em sala",
        "ordem": 100,
    },
    {
        "categoria": "frequencia",
        "codigo": "faltas_frequentes",
        "descricao": "Faltas frequentes",
        "ordem": 110,
    },
    {
        "categoria": "frequencia",
        "codigo": "ausencias_dias_avaliacao",
        "descricao": "Ausências em dias de avaliação",
        "ordem": 120,
    },
    {
        "categoria": "frequencia",
        "codigo": "chega_atrasado_frequencia",
        "descricao": "Chega atrasado com frequência",
        "ordem": 130,
    },
    {
        "categoria": "organizacao_estudo",
        "codigo": "nao_traz_material",
        "descricao": "Não traz material",
        "ordem": 140,
    },
    {
        "categoria": "organizacao_estudo",
        "codigo": "nao_realiza_atividades_casa",
        "descricao": "Não realiza atividades de casa",
        "ordem": 150,   
    },
    {
        "categoria": "organizacao_estudo",
        "codigo": "falta_rotina_estudos",
        "descricao": "Demonstra falta de rotina de estudos",
        "ordem": 160,
    },
    {
        "categoria": "dificuldades_pedagogicas",
        "codigo": "dificuldade_leitura_interpretacao",
        "descricao": "Dificuldade de leitura e interpretação",
        "ordem": 170,
    },
    {
        "categoria": "dificuldades_pedagogicas",
        "codigo": "dificuldade_calculos_basicos",
        "descricao": "Dificuldade em cálculos básicos",
        "ordem": 180,
    },
    {
        "categoria": "dificuldades_pedagogicas",
        "codigo": "dificuldade_producao_escrita",
        "descricao": "Dificuldade na produção escrita",
        "ordem": 190,
    },
    {
        "categoria": "dificuldades_pedagogicas",
        "codigo": "necessita_acompanhamento_individualizado",
        "descricao": "Necessita acompanhamento mais individualizado",
        "ordem": 200,
    },
)

MOTIVOS_POS_PRE_CONSELHO = {
    "recuperado": (
        {
            "id": "participou_e_avancou_recuperacao",
            "descricao": "Participou da recuperação paralela e apresentou avanços",
        },
        {
            "id": "retomou_conteudos_essenciais",
            "descricao": "Retomou os conteúdos essenciais da disciplina",
        },
        {
            "id": "melhorou_resultados_avaliativos",
            "descricao": "Melhorou os resultados nas atividades e avaliações de recuperação",
        },
        {
            "id": "ampliou_participacao_compromisso",
            "descricao": "Demonstrou mais participação, compromisso e entrega das atividades",
        },
    ),
    "nao_recuperado": (
        {
            "id": "manteve_baixo_rendimento",
            "descricao": "Manteve baixo rendimento mesmo após a recuperação paralela",
        },
        {
            "id": "nao_concluiu_atividades_recuperacao",
            "descricao": "Não concluiu as atividades propostas na recuperação paralela",
        },
        {
            "id": "baixa_frequencia_recuperacao",
            "descricao": "Apresentou baixa frequência nos momentos de recuperação",
        },
        {
            "id": "dificuldades_persistem_conteudos",
            "descricao": "As dificuldades nos conteúdos essenciais persistem",
        },
    ),
}

_CATEGORIAS_ROTULO = {
    "avaliacao": "Avaliação",
    "participacao": "Participação",
    "comportamento": "Comportamento",
    "frequencia": "Frequência",
    "organizacao_estudo": "Organização e estudo",
    "dificuldades_pedagogicas": "Dificuldades pedagógicas",
}

_FRASES_CATEGORIA = {
    "avaliacao": "aspectos avaliativos, com {lista}",
    "participacao": "baixa participação e engajamento nas aulas, com {lista}",
    "comportamento": "aspectos comportamentais que interferem no processo de aprendizagem, como {lista}",
    "frequencia": "frequência irregular, com {lista}",
    "organizacao_estudo": "fragilidades de organização e rotina de estudos, com {lista}",
    "dificuldades_pedagogicas": "dificuldades pedagógicas observadas, com {lista}",
}

_FRASES_MOTIVO = {
    "nao_fez_prova_bimestral": "ausência na realização da prova bimestral",
    "nao_entregou_trabalho": "não entrega de trabalhos propostos",
    "nao_realizou_atividades_avaliativas": "não realização de atividades avaliativas",
    "nota_abaixo_esperado": "desempenho abaixo do esperado nos instrumentos avaliativos",
    "baixa_participacao_aula": "baixa participação nas aulas",
    "pouco_engajamento_atividades": "pouco engajamento nas atividades propostas",
    "dificuldade_acompanhar_explicacoes": "dificuldade em acompanhar explicações e conteúdos",
    "conversas_excessivas_em_aula": "conversas excessivas durante as aulas",
    "nao_respeita_combinados": "dificuldade em respeitar os combinados de convivência",
    "comportamento_inadequado_sala": "comportamento inadequado em sala",
    "faltas_frequentes": "frequência irregular",
    "ausencias_dias_avaliacao": "ausência em dias de avaliação",
    "chega_atrasado_frequencia": "atrasos frequentes",
    "nao_traz_material": "falta de material necessário para as aulas",
    "nao_realiza_atividades_casa": "não realização das atividades de casa",
    "falta_rotina_estudos": "fragilidade na rotina de estudos",
    "dificuldade_leitura_interpretacao": "dificuldade de leitura e interpretação",
    "dificuldade_calculos_basicos": "dificuldade em cálculos básicos",
    "dificuldade_producao_escrita": "dificuldade na produção escrita",
    "necessita_acompanhamento_individualizado": "necessidade de acompanhamento mais individualizado",
}


def _texto_limpo(valor) -> str:
    return str(valor or "").strip()


def texto_obrigatorio_preconselho(valor: str, campo: str, *, max_len: int = 255) -> str:
    texto = _texto_limpo(valor)
    if not texto:
        raise HTTPException(400, f"{campo} é obrigatório.")
    if len(texto) > max_len:
        raise HTTPException(400, f"{campo} excede o limite de {max_len} caracteres.")
    return texto


def validar_data_iso_preconselho(valor: str, campo: str) -> str:
    texto = texto_obrigatorio_preconselho(valor, campo, max_len=20)
    try:
        data = datetime.strptime(texto, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(400, f"{campo} inválida. Use o formato YYYY-MM-DD.") from exc
    return data.isoformat()


def _lista_unica_texto(valores) -> list[str]:
    itens = []
    for valor in valores or []:
        texto = _texto_limpo(valor)
        if texto and texto not in itens:
            itens.append(texto)
    return itens


def _formatar_lista_pt_br(itens) -> str:
    valores = _lista_unica_texto(itens)
    if not valores:
        return ""
    if len(valores) == 1:
        return valores[0]
    if len(valores) == 2:
        return f"{valores[0]} e {valores[1]}"
    return ", ".join(valores[:-1]) + f" e {valores[-1]}"


def _garantir_ponto_final(frase: str) -> str:
    texto = _texto_limpo(frase)
    if not texto:
        return ""
    if texto[-1] in ".!?":
        return texto
    return texto + "."


def _texto_lista_observacao(observacao_professor: str) -> str:
    texto = _texto_limpo(observacao_professor).rstrip(".;: ")
    if not texto:
        return ""
    return texto[0].lower() + texto[1:] if len(texto) > 1 else texto.lower()


def _texto_para_observacao(observacao_professor: str) -> str:
    texto = _texto_lista_observacao(observacao_professor)
    if not texto:
        return ""
    return _garantir_ponto_final(f"Como relato complementar do professor, destaca-se que {texto}")


def _texto_relato_complementar_consolidado(
    disciplina_nome: str,
    professor_nome: str,
    observacao_professor: str,
) -> str:
    observacao = _texto_lista_observacao(observacao_professor)
    if not observacao:
        return ""

    disciplina = _texto_limpo(disciplina_nome) or "Disciplina não informada"
    professor = _texto_limpo(professor_nome)
    if professor:
        partes_nome = [parte.strip(".,;:") for parte in professor.split() if parte.strip(".,;:")]
        prefixos = {"prof", "professor", "professora"}
        primeiro_nome = ""
        for parte in partes_nome:
            if parte.casefold() in prefixos:
                continue
            primeiro_nome = parte
            break
        if primeiro_nome:
            return f"em {disciplina}, Prof {primeiro_nome} relatou que {observacao}"
    return f"em {disciplina}, foi relatado que {observacao}"


def listar_niveis_atencao_pre_conselho() -> list[dict]:
    return [dict(item) for item in NIVEIS_ATENCAO_PRE_CONSELHO]


def criar_periodo_preconselho_admin(payload) -> dict:
    try:
        etapa = validar_etapa_pre_conselho(payload.etapa)
        status = validar_status_periodo_pre_conselho(
            payload.status or STATUS_PERIODO_PRE_CONSELHO_ABERTO
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    try:
        periodo_id = criar_periodo_pre_conselho_repo(
            nome=payload.nome,
            ano_letivo=int(payload.ano_letivo),
            etapa=etapa,
            data_inicio=validar_data_iso_preconselho(payload.data_inicio, "Data inicial"),
            data_fim=validar_data_iso_preconselho(payload.data_fim, "Data final"),
            status=status,
        )
    except IntegrityError as exc:
        raise HTTPException(
            400, "Já existe um período cadastrado para este ano letivo e etapa."
        ) from exc

    periodo = buscar_periodo_pre_conselho_por_id_repo(periodo_id)
    return {**periodo, "editavel": True}


def atualizar_periodo_preconselho_admin(periodo_id: int, payload) -> dict:
    try:
        etapa = validar_etapa_pre_conselho(payload.etapa)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    try:
        if not atualizar_periodo_pre_conselho_dados_repo(
            periodo_id,
            nome=payload.nome,
            ano_letivo=int(payload.ano_letivo),
            etapa=etapa,
            data_inicio=validar_data_iso_preconselho(payload.data_inicio, "Data inicial"),
            data_fim=validar_data_iso_preconselho(payload.data_fim, "Data final"),
        ):
            raise HTTPException(404, "Período não encontrado.")
    except IntegrityError as exc:
        raise HTTPException(
            400, "Já existe um período cadastrado para este ano letivo e etapa."
        ) from exc

    periodo = buscar_periodo_pre_conselho_por_id_repo(periodo_id)
    return {**periodo, "editavel": True}


def atualizar_status_periodo_preconselho_admin(periodo_id: int, status: str) -> dict:
    try:
        status_validado = validar_status_periodo_pre_conselho(status)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    if not atualizar_status_periodo_pre_conselho_repo(periodo_id, status_validado):
        raise HTTPException(404, "Período não encontrado.")

    periodo = buscar_periodo_pre_conselho_por_id_repo(periodo_id)
    return {**periodo, "editavel": True}


def listar_motivos_preconselho_visiveis(*, incluir_inativos: bool, usuario_eh_admin: bool):
    if incluir_inativos and not usuario_eh_admin:
        raise HTTPException(403, "Acesso negado.")
    return listar_motivos_pre_conselho_repo(incluir_inativos=incluir_inativos)


def criar_motivo_preconselho_admin(payload) -> dict:
    try:
        categoria = validar_categoria_motivo_pre_conselho(payload.categoria)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    try:
        motivo_id = criar_motivo_pre_conselho_repo(
            categoria=categoria,
            codigo=texto_obrigatorio_preconselho(payload.codigo, "Código", max_len=120)
            .lower()
            .replace(" ", "_"),
            descricao=texto_obrigatorio_preconselho(
                payload.descricao, "Descrição", max_len=255
            ),
            ordem=int(payload.ordem or 0),
        )
    except IntegrityError as exc:
        raise HTTPException(400, "Já existe um motivo cadastrado com este código.") from exc

    return buscar_motivo_pre_conselho_por_id_repo(motivo_id)


def atualizar_motivo_preconselho_admin(motivo_id: int, payload) -> dict:
    try:
        categoria = validar_categoria_motivo_pre_conselho(payload.categoria)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    if not atualizar_motivo_pre_conselho_dados_repo(
        motivo_id,
        categoria=categoria,
        descricao=texto_obrigatorio_preconselho(payload.descricao, "Descrição", max_len=255),
        ordem=int(payload.ordem or 0),
    ):
        raise HTTPException(404, "Motivo não encontrado.")

    return buscar_motivo_pre_conselho_por_id_repo(motivo_id)


def atualizar_status_motivo_preconselho_admin(motivo_id: int, ativo: bool) -> dict:
    if not atualizar_status_motivo_pre_conselho_repo(motivo_id, ativo):
        raise HTTPException(404, "Motivo não encontrado.")
    return buscar_motivo_pre_conselho_por_id_repo(motivo_id)


def validar_status_periodo_pre_conselho(status: str) -> str:
    status_limpo = _texto_limpo(status).upper()
    if status_limpo not in STATUS_PERIODO_PRE_CONSELHO_VALIDOS:
        raise ValueError("Status de período inválido.")
    return status_limpo


def validar_etapa_pre_conselho(etapa: int) -> int:
    try:
        etapa_valor = int(etapa)
    except (TypeError, ValueError) as exc:
        raise ValueError("Etapa inválida.") from exc
    if etapa_valor not in {1, 2, 3, 4}:
        raise ValueError("Etapa inválida.")
    return etapa_valor


def validar_categoria_motivo_pre_conselho(categoria: str) -> str:
    categoria_limpa = _texto_limpo(categoria)
    if categoria_limpa not in CATEGORIAS_MOTIVO_PRE_CONSELHO:
        raise ValueError("Categoria de motivo inválida.")
    return categoria_limpa


def validar_nivel_atencao_pre_conselho(nivel_atencao: str | None) -> str:
    texto = _texto_limpo(nivel_atencao)
    if not texto:
        return ""

    niveis_validos = {item["id"] for item in NIVEIS_ATENCAO_PRE_CONSELHO}
    if texto not in niveis_validos:
        raise ValueError("Nivel de atenção inválido.")
    return texto


def listar_motivos_pos_pre_conselho() -> dict[str, list[dict]]:
    return {
        "recuperado": [dict(item) for item in MOTIVOS_POS_PRE_CONSELHO["recuperado"]],
        "nao_recuperado": [dict(item) for item in MOTIVOS_POS_PRE_CONSELHO["nao_recuperado"]],
    }


def normalizar_status_pos_pre_conselho(
    recuperado: bool | None,
    motivo_ids: list[str] | None = None,
    observacao: str = "",
) -> bool | None:
    possui_dados = bool(_lista_unica_texto(motivo_ids) or _texto_limpo(observacao))
    if recuperado is None:
        return False if possui_dados else None
    return bool(recuperado)


def descrever_motivos_pos_pre_conselho(
    motivo_ids: list[str] | None,
    recuperado: bool | None,
) -> list[str]:
    status = normalizar_status_pos_pre_conselho(recuperado, motivo_ids)
    if status is None:
        return []

    chave = "recuperado" if status else "nao_recuperado"
    catalogo = {
        _texto_limpo(item["id"]): _texto_limpo(item["descricao"])
        for item in MOTIVOS_POS_PRE_CONSELHO[chave]
    }
    descricoes = []
    for motivo_id in _lista_unica_texto(motivo_ids):
        descricao = catalogo.get(motivo_id)
        if descricao and descricao not in descricoes:
            descricoes.append(descricao)
    return descricoes


def validar_motivos_pos_pre_conselho(
    motivo_ids: list[str] | None,
    recuperado: bool | None,
    observacao: str = "",
) -> tuple[bool | None, list[str], list[str]]:
    status = normalizar_status_pos_pre_conselho(recuperado, motivo_ids, observacao)
    ids_normalizados = _lista_unica_texto(motivo_ids)
    if status is None:
        if ids_normalizados:
            raise ValueError("Os motivos do pós pré-conselho exigem a definição do resultado.")
        return None, [], []

    chave = "recuperado" if status else "nao_recuperado"
    catalogo = {_texto_limpo(item["id"]): item for item in MOTIVOS_POS_PRE_CONSELHO[chave]}
    ids_invalidos = [motivo_id for motivo_id in ids_normalizados if motivo_id not in catalogo]
    if ids_invalidos:
        raise ValueError("Existe motivo inválido na etapa de pós pré-conselho.")

    descricoes = [
        _texto_limpo(catalogo[motivo_id]["descricao"])
        for motivo_id in ids_normalizados
        if _texto_limpo(catalogo[motivo_id]["descricao"])
    ]
    return status, ids_normalizados, descricoes


def nome_periodo_pre_conselho(ano_letivo: int, etapa: int) -> str:
    etapa_valor = validar_etapa_pre_conselho(etapa)
    return f"{etapa_valor}º Bimestre {int(ano_letivo)}"


def periodo_editavel_para_cargo(status: str, cargo: str) -> bool:
    status_limpo = _texto_limpo(status).upper()
    cargo_limpo = _texto_limpo(cargo).upper()
    if cargo_limpo == "ADMIN":
        return True
    return status_limpo == STATUS_PERIODO_PRE_CONSELHO_ABERTO and cargo_limpo == "PROFESSOR"


def periodo_esta_aberto(status: str) -> bool:
    return _texto_limpo(status).upper() == STATUS_PERIODO_PRE_CONSELHO_ABERTO


def catalogo_motivos_iniciais_pre_conselho() -> list[dict]:
    return [dict(item) for item in MOTIVOS_PRE_CONSELHO_INICIAIS]


def codigo_motivo_pre_conselho_valido(codigo: str) -> str:
    codigo_limpo = _texto_limpo(codigo)
    codigos = {item["codigo"] for item in MOTIVOS_PRE_CONSELHO_INICIAIS}
    if codigo_limpo not in codigos:
        raise ValueError("Código de motivo inválido.")
    return codigo_limpo


def rotulo_categoria_motivo_pre_conselho(categoria: str) -> str:
    chave = _texto_limpo(categoria)
    return _CATEGORIAS_ROTULO.get(chave, chave)


def _fragmento_motivo(motivo: dict) -> str:
    codigo = _texto_limpo(motivo.get("codigo"))
    descricao = _texto_limpo(motivo.get("descricao"))
    return _FRASES_MOTIVO.get(codigo, descricao.lower() if descricao else "")


def _listar_fragmentos_motivos(motivos: list[dict]) -> list[str]:
    fragmentos = []
    for motivo in motivos or []:
        frase = _fragmento_motivo(motivo)
        if frase and frase not in fragmentos:
            fragmentos.append(frase)
    return fragmentos


def _agrupar_motivos_por_categoria(motivos: list[dict]) -> list[str]:
    motivos_por_categoria = {}

    for motivo in motivos or []:
        categoria = _texto_limpo(motivo.get("categoria"))
        if categoria not in CATEGORIAS_MOTIVO_PRE_CONSELHO:
            continue

        frase = _fragmento_motivo(motivo)
        if not frase:
            continue
        motivos_por_categoria.setdefault(categoria, [])
        if frase not in motivos_por_categoria[categoria]:
            motivos_por_categoria[categoria].append(frase)

    frases_categoria = []
    for categoria in CATEGORIAS_MOTIVO_PRE_CONSELHO:
        fragmentos = motivos_por_categoria.get(categoria) or []
        if not fragmentos:
            continue
        template = _FRASES_CATEGORIA.get(categoria, "{lista}")
        frases_categoria.append(template.format(lista=_formatar_lista_pt_br(fragmentos)))
    return frases_categoria


def _descricao_disciplinas(disciplinas: list[str]) -> str:
    disciplinas_unicas = _lista_unica_texto(disciplinas)
    if not disciplinas_unicas:
        return "no período"
    if len(disciplinas_unicas) == 1:
        return f"na disciplina de {disciplinas_unicas[0]}"
    return f"nas disciplinas de {_formatar_lista_pt_br(disciplinas_unicas)}"


def _texto_recomendacao_nivel(nivel_atencao: str) -> str:
    if nivel_atencao == "alto":
        return "Recomenda-se prioridade no acompanhamento individualizado e articulação com a equipe pedagógica."
    if nivel_atencao == "medio":
        return "Recomenda-se monitoramento sistemático e intervenções pedagógicas ao longo do período seguinte."
    if nivel_atencao == "baixo":
        return "Recomenda-se acompanhamento contínuo e retomada orientada dos conteúdos essenciais."
    return ""


def _texto_professores_turma(professores: list[str]) -> str:
    nomes = _lista_unica_texto(professores)
    if not nomes:
        return ""
    if len(nomes) == 1:
        return _garantir_ponto_final(f"O professor que atua na turma é {nomes[0]}")
    return _garantir_ponto_final(
        f"Os professores que atuam na turma são {_formatar_lista_pt_br(nomes)}"
    )


def _texto_pos_pre_conselho(
    recuperado: bool | None,
    motivos_pos_pre_conselho: list[str] | None = None,
    observacao_pos_pre_conselho: str = "",
) -> str:
    status = normalizar_status_pos_pre_conselho(
        recuperado,
        motivos_pos_pre_conselho,
        observacao_pos_pre_conselho,
    )
    if status is None:
        return ""

    observacao = _texto_lista_observacao(observacao_pos_pre_conselho)

    if status:
        abertura = "Após o pré-conselho, o estudante foi recuperado por meio da recuperação paralela"
    else:
        abertura = "Após o pré-conselho, o estudante manteve baixo rendimento, mesmo após a recuperação paralela"

    partes = [_garantir_ponto_final(abertura)]
    if observacao:
        partes.append(
            _garantir_ponto_final(
                f"No pós-pré-conselho, observou-se ainda que {observacao}"
            )
        )
    return " ".join(parte for parte in partes if parte)


def gerar_texto_pre_conselho_individual(
    motivos: list[dict],
    observacao_professor: str = "",
    nivel_atencao: str | None = None,
    estudante_nome: str = "",
    disciplina_nome: str = "",
    pos_preconselho_recuperado: bool | None = None,
    pos_preconselho_motivos: list[str] | None = None,
    pos_preconselho_observacao: str = "",
) -> dict:
    if not motivos:
        raise ValueError("Selecione ao menos um motivo para gerar o texto.")

    nivel_limpo = validar_nivel_atencao_pre_conselho(nivel_atencao)
    fragmentos_motivos = _listar_fragmentos_motivos(motivos)
    if not fragmentos_motivos:
        raise ValueError("Não foi possível gerar o texto com os motivos selecionados.")

    sujeito = (
        f"O estudante {_texto_limpo(estudante_nome)}"
        if _texto_limpo(estudante_nome)
        else "O estudante"
    )
    abertura = (
        f"{sujeito} obteve baixo rendimento {_descricao_disciplinas([disciplina_nome])}, "
        f"em razão de {_formatar_lista_pt_br(fragmentos_motivos)}."
    )

    complemento_nivel = _texto_recomendacao_nivel(nivel_limpo)
    observacao = _texto_para_observacao(observacao_professor)
    pos_preconselho = _texto_pos_pre_conselho(
        pos_preconselho_recuperado,
        pos_preconselho_motivos,
        pos_preconselho_observacao,
    )
    texto = " ".join(
        parte
        for parte in (
            abertura,
            complemento_nivel,
            observacao,
            pos_preconselho,
        )
        if parte
    )
    return {
        "texto": texto,
        "fragmentos": fragmentos_motivos,
    }


def _motivos_frequentes(registros: list[dict], *, limite: int = 5) -> list[str]:
    contador = Counter()
    for registro in registros or []:
        for motivo in registro.get("motivos") or []:
            descricao = _texto_limpo(motivo.get("descricao"))
            if descricao:
                contador[descricao] += 1
    return [descricao for descricao, _total in contador.most_common(limite)]


def _nivel_mais_critico(registros: list[dict]) -> str:
    prioridade = {"": 0, "baixo": 1, "medio": 2, "alto": 3}
    nivel_encontrado = ""
    for registro in registros or []:
        nivel = validar_nivel_atencao_pre_conselho(registro.get("nivel_atencao"))
        if prioridade[nivel] > prioridade[nivel_encontrado]:
            nivel_encontrado = nivel
    return nivel_encontrado


def _agrupar_registros_por_estudante(registros: list[dict]) -> list[list[dict]]:
    grupos = {}
    ordem_chaves = []

    for registro in registros or []:
        estudante_id = int(registro.get("estudante_id") or 0)
        estudante_nome = _texto_limpo(registro.get("estudante_nome"))
        chave = f"id:{estudante_id}" if estudante_id > 0 else f"nome:{estudante_nome.casefold()}"
        if chave not in grupos:
            grupos[chave] = []
            ordem_chaves.append(chave)
        grupos[chave].append(dict(registro))

    return [grupos[chave] for chave in ordem_chaves]


def _resumir_registros_por_disciplina(registros: list[dict]) -> list[dict]:
    agrupados = {}
    ordem = []

    for registro in registros or []:
        disciplina_nome = (
            _texto_limpo(registro.get("disciplina_nome")) or "Disciplina não informada"
        )
        if disciplina_nome not in agrupados:
            agrupados[disciplina_nome] = {
                "disciplina": disciplina_nome,
                "motivos": [],
                "observacoes": [],
            }
            ordem.append(disciplina_nome)

        bloco = agrupados[disciplina_nome]
        for fragmento in _listar_fragmentos_motivos(registro.get("motivos") or []):
            if fragmento not in bloco["motivos"]:
                bloco["motivos"].append(fragmento)

        observacao = _texto_lista_observacao(registro.get("observacao_professor"))
        if observacao and observacao not in bloco["observacoes"]:
            bloco["observacoes"].append(observacao)

        status_pos = normalizar_status_pos_pre_conselho(
            registro.get("pos_preconselho_recuperado"),
            registro.get("pos_preconselho_motivo_ids"),
            registro.get("pos_preconselho_observacao"),
        )
        if status_pos is not None:
            bloco.setdefault("pos_preconselho", []).append(
                {
                    "recuperado": status_pos,
                    "observacao": _texto_limpo(registro.get("pos_preconselho_observacao")),
                }
            )

    return [agrupados[chave] for chave in ordem]


def _texto_estudante_consolidado(registros: list[dict]) -> dict:
    if not registros:
        return {
            "estudante_id": 0,
            "estudante_nome": "",
            "turma_nome": "",
            "nivel_atencao": "",
            "total_registros": 0,
            "disciplinas": [],
            "motivos": [],
            "observacoes": [],
            "professores": [],
            "texto": "",
        }

    base = dict(registros[0])
    disciplinas_resumidas = _resumir_registros_por_disciplina(registros)
    disciplinas = [item["disciplina"] for item in disciplinas_resumidas]
    motivos = _lista_unica_texto(
        fragmento for item in disciplinas_resumidas for fragmento in item["motivos"]
    )
    observacoes = _lista_unica_texto(
        _texto_relato_complementar_consolidado(
            registro.get("disciplina_nome"),
            registro.get("professor_nome"),
            registro.get("observacao_professor"),
        )
        for registro in registros
    )
    professores = _lista_unica_texto(
        nome
        for item in registros
        for nome in (
            item.get("professores_turma")
            if isinstance(item.get("professores_turma"), list)
            else [item.get("professor_nome")]
        )
    )
    nivel_atencao = _nivel_mais_critico(registros)

    estudante_nome = _texto_limpo(base.get("estudante_nome")) or "Estudante não identificado"
    abertura = (
        f"O estudante {estudante_nome} obteve baixo rendimento {_descricao_disciplinas(disciplinas)}, "
        f"em razão de {_formatar_lista_pt_br(motivos)}."
    )

    detalhes_disciplina = ""
    if len(disciplinas_resumidas) > 1:
        detalhes = [
            f"em {item['disciplina']}, {_formatar_lista_pt_br(item['motivos'])}"
            for item in disciplinas_resumidas
            if item["motivos"]
        ]
        if detalhes:
            detalhes_disciplina = _garantir_ponto_final(
                "Por disciplina, observaram-se " + "; ".join(detalhes)
            )

    recomendacao = _texto_recomendacao_nivel(nivel_atencao)
    professores_txt = _texto_professores_turma(professores)
    observacao_txt = ""
    if observacoes:
        observacao_txt = _garantir_ponto_final(
            "Relatos complementares registrados: " + "; ".join(observacoes)
        )

    pos_preconselho_txt = ""
    detalhes_pos_preconselho = []
    for item in disciplinas_resumidas:
        registros_pos = item.get("pos_preconselho") or []
        if not registros_pos:
            continue

        recuperado = any(bool(registro.get("recuperado")) for registro in registros_pos)
        observacoes_pos = _lista_unica_texto(
            registro.get("observacao") for registro in registros_pos
        )

        frase = (
            f"em {item['disciplina']}, houve recuperação por meio da recuperação paralela"
            if recuperado
            else f"em {item['disciplina']}, o estudante manteve baixo rendimento após a recuperação paralela"
        )
        if observacoes_pos:
            frase += f", com observação de que {_formatar_lista_pt_br(observacoes_pos)}"
        detalhes_pos_preconselho.append(frase)

    if detalhes_pos_preconselho:
        pos_preconselho_txt = _garantir_ponto_final(
            "No pós-pré-conselho, registrou-se que " + "; ".join(detalhes_pos_preconselho)
        )

    texto = " ".join(
        parte
        for parte in (
            abertura,
            professores_txt,
            recomendacao,
            detalhes_disciplina,
            observacao_txt,
            pos_preconselho_txt,
        )
        if parte
    )
    return {
        "estudante_id": int(base.get("estudante_id") or 0),
        "estudante_nome": estudante_nome,
        "turma_nome": _texto_limpo(base.get("turma_nome")),
        "nivel_atencao": nivel_atencao,
        "total_registros": len(registros),
        "disciplinas": disciplinas,
        "motivos": motivos,
        "observacoes": observacoes,
        "professores": professores,
        "texto": texto,
    }


def _texto_abertura_consolidado(
    periodo_nome: str,
    turma_nome: str,
    disciplina_nome: str,
    professor_nome: str,
    registros: list[dict],
    *,
    total_registros: int,
    total_estudantes: int,
) -> str:
    partes = [f"No período {periodo_nome}"]

    turma_limpa = _texto_limpo(turma_nome)
    disciplina_limpa = _texto_limpo(disciplina_nome)
    professor_limpo = _texto_limpo(professor_nome)

    if turma_limpa and turma_limpa != "Todas as turmas":
        partes.append(f"na turma {turma_limpa}")
    else:
        partes.append("considerando todas as turmas")

    if disciplina_limpa and disciplina_limpa != "Todas as disciplinas":
        partes.append(f"na disciplina de {disciplina_limpa}")
    else:
        partes.append("considerando todas as disciplinas")

    if professor_limpo:
        partes.append(f"com registros vinculados ao professor {professor_limpo}")

    abertura = (
        ", ".join(partes)
        + f", foram consolidados {total_registros} registro(s) de {total_estudantes} estudante(s) sinalizado(s)."
    )

    if turma_limpa and turma_limpa != "Todas as turmas":
        corpo_docente = _texto_corpo_docente_turma(registros)
        if corpo_docente:
            abertura += f" A turma do {turma_limpa}, composta pelo seguinte corpo docente: {corpo_docente}."

    return abertura


def _nomes_estudantes_resumidos(registros: list[dict], *, limite: int = 8) -> str:
    nomes = _lista_unica_texto(registro.get("estudante_nome") for registro in registros or [])
    if not nomes:
        return ""
    if len(nomes) <= limite:
        return _formatar_lista_pt_br(nomes)
    prefixo = nomes[:limite] + ["demais estudantes sinalizados"]
    return _formatar_lista_pt_br(prefixo)


def _texto_corpo_docente_turma(registros: list[dict]) -> str:
    corpo_docente = []
    for registro in registros or []:
        if isinstance(registro.get("corpo_docente_turma"), list) and registro.get("corpo_docente_turma"):
            corpo_docente = registro.get("corpo_docente_turma")
            break

    if corpo_docente:
        itens = []
        for item in corpo_docente:
            professor = _texto_limpo(item.get("professor_nome"))
            disciplinas = _lista_unica_texto(item.get("disciplinas") or [])
            if not professor:
                continue
            if disciplinas:
                itens.append(f"{professor} ({_formatar_lista_pt_br(disciplinas)})")
            else:
                itens.append(professor)
        return _formatar_lista_pt_br(itens)

    docentes = {}
    ordem_docentes = []

    for registro in registros or []:
        professor = _texto_limpo(registro.get("professor_nome"))
        disciplina = _texto_limpo(registro.get("disciplina_nome")) or "Disciplina não informada"
        if not professor:
            continue
        if professor not in docentes:
            docentes[professor] = []
            ordem_docentes.append(professor)
        if disciplina not in docentes[professor]:
            docentes[professor].append(disciplina)

    itens = []
    for professor in ordem_docentes:
        itens.append(f"{professor} ({_formatar_lista_pt_br(docentes[professor])})")
    return _formatar_lista_pt_br(itens)


def _resolver_periodo_atual() -> tuple[int, int]:
    hoje = date.today()
    if hoje.month <= 4:
        return hoje.year, 1
    if hoje.month <= 6:
        return hoje.year, 2
    if hoje.month <= 9:
        return hoje.year, 3
    return hoje.year, 4


def periodos_padrao_pre_conselho(ano_letivo: int | None = None) -> list[dict]:
    ano, etapa_atual = _resolver_periodo_atual()
    ano_base = int(ano_letivo or ano)
    periodos = []
    faixas = {
        1: ("01-20", "04-30"),
        2: ("05-01", "06-30"),
        3: ("07-21", "09-30"),
        4: ("10-01", "12-20"),
    }
    for etapa in (1, 2, 3, 4):
        inicio, fim = faixas[etapa]
        periodos.append(
            {
                "nome": nome_periodo_pre_conselho(ano_base, etapa),
                "ano_letivo": ano_base,
                "etapa": etapa,
                "data_inicio": f"{ano_base}-{inicio}",
                "data_fim": f"{ano_base}-{fim}",
                "status": (
                    STATUS_PERIODO_PRE_CONSELHO_ABERTO
                    if ano_base == ano and etapa == etapa_atual
                    else STATUS_PERIODO_PRE_CONSELHO_FECHADO
                ),
            }
        )
    return periodos


def gerar_texto_consolidado_pre_conselho(
    periodo_nome: str,
    turma_nome: str,
    disciplina_nome: str,
    registros: list[dict],
    *,
    professor_nome: str = "",
) -> dict:
    itens = [dict(item) for item in registros or []]
    total_registros = len(itens)
    total_estudantes = len(_lista_unica_texto(item.get("estudante_nome") for item in itens))
    motivos_frequentes = _motivos_frequentes(itens)
    professores_turma = _lista_unica_texto(
        nome
        for item in itens
        for nome in (
            item.get("professores_turma")
            if isinstance(item.get("professores_turma"), list)
            else [item.get("professor_nome")]
        )
    )
    itens_agrupados = [
        _texto_estudante_consolidado(grupo) for grupo in _agrupar_registros_por_estudante(itens)
    ]

    if total_registros == 0:
        texto = (
            f"No período {periodo_nome}, na turma {turma_nome}, na disciplina de {disciplina_nome}, "
            "não há registros de estudantes sinalizados no pré-conselho."
        )
        return {
            "total_registros": 0,
            "total_estudantes": 0,
            "motivos_frequentes": [],
            "itens_agrupados": [],
            "texto": texto,
        }

    abertura = _texto_abertura_consolidado(
        periodo_nome,
        turma_nome,
        disciplina_nome,
        professor_nome,
        itens,
        total_registros=total_registros,
        total_estudantes=total_estudantes,
    )

    fatores = ""
    if motivos_frequentes:
        fatores = f"Os motivos mais recorrentes foram {_formatar_lista_pt_br(motivos_frequentes)}."

    professores_txt = ""
    if professores_turma:
        if len(professores_turma) == 1:
            professores_txt = f"O professor que atua na turma é {professores_turma[0]}."
        else:
            professores_txt = (
                "Os professores que atuam na turma são "
                f"{_formatar_lista_pt_br(professores_turma)}."
            )

    estudantes_txt = "\n\n".join(
        item["texto"] for item in itens_agrupados if _texto_limpo(item.get("texto"))
    )

    return {
        "total_registros": total_registros,
        "total_estudantes": total_estudantes,
        "motivos_frequentes": motivos_frequentes,
        "itens_agrupados": itens_agrupados,
        "texto": "\n\n".join(
            parte for parte in (abertura, professores_txt, fatores, estudantes_txt) if parte
        ),
    }
