from collections import Counter
from datetime import date


STATUS_PERIODO_PRE_CONSELHO_ABERTO = "ABERTO"
STATUS_PERIODO_PRE_CONSELHO_FECHADO = "FECHADO"
STATUS_PERIODO_PRE_CONSELHO_VALIDOS = (
    STATUS_PERIODO_PRE_CONSELHO_ABERTO,
    STATUS_PERIODO_PRE_CONSELHO_FECHADO,
)

NIVEIS_ATENCAO_PRE_CONSELHO = (
    {"id": "baixo", "nome": "Baixo"},
    {"id": "medio", "nome": "Medio"},
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
        "descricao": "Nao fez a prova bimestral",
        "ordem": 10,
    },
    {
        "categoria": "avaliacao",
        "codigo": "nao_entregou_trabalho",
        "descricao": "Nao entregou o trabalho",
        "ordem": 20,
    },
    {
        "categoria": "avaliacao",
        "codigo": "nao_realizou_atividades_avaliativas",
        "descricao": "Nao realizou atividades avaliativas",
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
        "descricao": "Baixa participacao em aula",
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
        "descricao": "Dificuldade em acompanhar explicacoes",
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
        "descricao": "Nao respeita combinados",
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
        "descricao": "Ausencias em dias de avaliacao",
        "ordem": 120,
    },
    {
        "categoria": "frequencia",
        "codigo": "chega_atrasado_frequencia",
        "descricao": "Chega atrasado com frequencia",
        "ordem": 130,
    },
    {
        "categoria": "organizacao_estudo",
        "codigo": "nao_traz_material",
        "descricao": "Nao traz material",
        "ordem": 140,
    },
    {
        "categoria": "organizacao_estudo",
        "codigo": "nao_realiza_atividades_casa",
        "descricao": "Nao realiza atividades de casa",
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
        "descricao": "Dificuldade de leitura e interpretacao",
        "ordem": 170,
    },
    {
        "categoria": "dificuldades_pedagogicas",
        "codigo": "dificuldade_calculos_basicos",
        "descricao": "Dificuldade em calculos basicos",
        "ordem": 180,
    },
    {
        "categoria": "dificuldades_pedagogicas",
        "codigo": "dificuldade_producao_escrita",
        "descricao": "Dificuldade na producao escrita",
        "ordem": 190,
    },
    {
        "categoria": "dificuldades_pedagogicas",
        "codigo": "necessita_acompanhamento_individualizado",
        "descricao": "Necessita acompanhamento mais individualizado",
        "ordem": 200,
    },
)

_CATEGORIAS_ROTULO = {
    "avaliacao": "Avaliacao",
    "participacao": "Participacao",
    "comportamento": "Comportamento",
    "frequencia": "Frequencia",
    "organizacao_estudo": "Organizacao e estudo",
    "dificuldades_pedagogicas": "Dificuldades pedagogicas",
}

_FRASES_CATEGORIA = {
    "avaliacao": "aspectos avaliativos, com {lista}",
    "participacao": "baixa participacao e engajamento nas aulas, com {lista}",
    "comportamento": "aspectos comportamentais que interferem no processo de aprendizagem, como {lista}",
    "frequencia": "frequencia irregular, com {lista}",
    "organizacao_estudo": "fragilidades de organizacao e rotina de estudos, com {lista}",
    "dificuldades_pedagogicas": "dificuldades pedagogicas observadas, com {lista}",
}

_FRASES_MOTIVO = {
    "nao_fez_prova_bimestral": "ausencia na realizacao da prova bimestral",
    "nao_entregou_trabalho": "nao entrega de trabalhos propostos",
    "nao_realizou_atividades_avaliativas": "nao realizacao de atividades avaliativas",
    "nota_abaixo_esperado": "desempenho abaixo do esperado nos instrumentos avaliativos",
    "baixa_participacao_aula": "baixa participacao nas aulas",
    "pouco_engajamento_atividades": "pouco engajamento nas atividades propostas",
    "dificuldade_acompanhar_explicacoes": "dificuldade em acompanhar explicacoes e conteudos",
    "conversas_excessivas_em_aula": "conversas excessivas durante as aulas",
    "nao_respeita_combinados": "dificuldade em respeitar os combinados de convivencia",
    "comportamento_inadequado_sala": "comportamento inadequado em sala",
    "faltas_frequentes": "frequencia irregular",
    "ausencias_dias_avaliacao": "ausencia em dias de avaliacao",
    "chega_atrasado_frequencia": "atrasos frequentes",
    "nao_traz_material": "falta de material necessario para as aulas",
    "nao_realiza_atividades_casa": "nao realizacao das atividades de casa",
    "falta_rotina_estudos": "fragilidade na rotina de estudos",
    "dificuldade_leitura_interpretacao": "dificuldade de leitura e interpretacao",
    "dificuldade_calculos_basicos": "dificuldade em calculos basicos",
    "dificuldade_producao_escrita": "dificuldade na producao escrita",
    "necessita_acompanhamento_individualizado": "necessidade de acompanhamento mais individualizado",
}


def _texto_limpo(valor) -> str:
    return str(valor or "").strip()


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


def _texto_para_observacao(observacao_professor: str) -> str:
    texto = _texto_limpo(observacao_professor)
    if not texto:
        return ""
    texto = texto.rstrip(".")
    texto = texto[0].lower() + texto[1:] if len(texto) > 1 else texto.lower()
    return _garantir_ponto_final(
        f"Conforme registro do professor, observa-se tambem {texto}"
    )


def listar_niveis_atencao_pre_conselho() -> list[dict]:
    return [dict(item) for item in NIVEIS_ATENCAO_PRE_CONSELHO]


def validar_status_periodo_pre_conselho(status: str) -> str:
    status_limpo = _texto_limpo(status).upper()
    if status_limpo not in STATUS_PERIODO_PRE_CONSELHO_VALIDOS:
        raise ValueError("Status de periodo invalido.")
    return status_limpo


def validar_etapa_pre_conselho(etapa: int) -> int:
    try:
        etapa_valor = int(etapa)
    except (TypeError, ValueError) as exc:
        raise ValueError("Etapa invalida.") from exc
    if etapa_valor not in {1, 2, 3, 4}:
        raise ValueError("Etapa invalida.")
    return etapa_valor


def validar_categoria_motivo_pre_conselho(categoria: str) -> str:
    categoria_limpa = _texto_limpo(categoria)
    if categoria_limpa not in CATEGORIAS_MOTIVO_PRE_CONSELHO:
        raise ValueError("Categoria de motivo invalida.")
    return categoria_limpa


def validar_nivel_atencao_pre_conselho(nivel_atencao: str | None) -> str:
    texto = _texto_limpo(nivel_atencao)
    if not texto:
        return ""

    niveis_validos = {item["id"] for item in NIVEIS_ATENCAO_PRE_CONSELHO}
    if texto not in niveis_validos:
        raise ValueError("Nivel de atencao invalido.")
    return texto


def nome_periodo_pre_conselho(ano_letivo: int, etapa: int) -> str:
    etapa_valor = validar_etapa_pre_conselho(etapa)
    return f"{etapa_valor}o Bimestre {int(ano_letivo)}"


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
        raise ValueError("Codigo de motivo invalido.")
    return codigo_limpo


def rotulo_categoria_motivo_pre_conselho(categoria: str) -> str:
    chave = _texto_limpo(categoria)
    return _CATEGORIAS_ROTULO.get(chave, chave)


def _fragmento_motivo(motivo: dict) -> str:
    codigo = _texto_limpo(motivo.get("codigo"))
    descricao = _texto_limpo(motivo.get("descricao"))
    return _FRASES_MOTIVO.get(codigo, descricao.lower() if descricao else "")


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


def gerar_texto_pre_conselho_individual(
    motivos: list[dict],
    observacao_professor: str = "",
    nivel_atencao: str | None = None,
) -> dict:
    if not motivos:
        raise ValueError("Selecione ao menos um motivo para gerar o texto.")

    nivel_limpo = validar_nivel_atencao_pre_conselho(nivel_atencao)
    frases_categoria = _agrupar_motivos_por_categoria(motivos)
    if not frases_categoria:
        raise ValueError("Nao foi possivel gerar o texto com os motivos selecionados.")

    abertura = (
        "O estudante apresentou baixo rendimento no periodo, relacionado a "
        f"{_formatar_lista_pt_br(frases_categoria)}, demandando acompanhamento pedagogico mais proximo."
    )

    complemento_nivel = ""
    if nivel_limpo == "alto":
        complemento_nivel = (
            " Recomenda-se prioridade no acompanhamento individualizado e articulacao com a equipe pedagogica."
        )
    elif nivel_limpo == "medio":
        complemento_nivel = (
            " Recomenda-se monitoramento sistematico e intervenções pedagogicas ao longo do periodo seguinte."
        )
    elif nivel_limpo == "baixo":
        complemento_nivel = (
            " Recomenda-se acompanhamento continuo e retomada orientada dos conteudos essenciais."
        )

    observacao = _texto_para_observacao(observacao_professor)
    texto = " ".join(
        parte
        for parte in (
            _garantir_ponto_final(abertura),
            _texto_limpo(complemento_nivel),
            observacao,
        )
        if parte
    )
    return {
        "texto": texto,
        "fragmentos": frases_categoria,
    }


def _motivos_frequentes(registros: list[dict], *, limite: int = 5) -> list[str]:
    contador = Counter()
    for registro in registros or []:
        for motivo in registro.get("motivos") or []:
            descricao = _texto_limpo(motivo.get("descricao"))
            if descricao:
                contador[descricao] += 1
    return [descricao for descricao, _total in contador.most_common(limite)]


def _nomes_estudantes_resumidos(registros: list[dict], *, limite: int = 8) -> str:
    nomes = _lista_unica_texto(registro.get("estudante_nome") for registro in registros or [])
    if not nomes:
        return ""
    if len(nomes) <= limite:
        return _formatar_lista_pt_br(nomes)
    prefixo = nomes[:limite] + ["demais estudantes sinalizados"]
    return _formatar_lista_pt_br(prefixo)


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

    if total_registros == 0:
        texto = (
            f"No periodo {periodo_nome}, na turma {turma_nome}, na disciplina de {disciplina_nome}, "
            "nao ha registros de estudantes sinalizados no pre-conselho."
        )
        return {
            "total_registros": 0,
            "total_estudantes": 0,
            "motivos_frequentes": [],
            "texto": texto,
        }

    referencia_professor = ""
    if _texto_limpo(professor_nome):
        referencia_professor = f", com registros vinculados ao professor {professor_nome}"

    abertura = (
        f"No periodo {periodo_nome}, na turma {turma_nome}, na disciplina de {disciplina_nome}"
        f"{referencia_professor}, foram sinalizados {total_estudantes} estudante(s) com indicativos de baixo rendimento."
    )

    fatores = ""
    if motivos_frequentes:
        fatores = (
            "Os motivos mais recorrentes foram "
            f"{_formatar_lista_pt_br(motivos_frequentes)}."
        )

    estudantes = _nomes_estudantes_resumidos(itens)
    estudantes_txt = ""
    if estudantes:
        estudantes_txt = f"Estudantes sinalizados: {estudantes}."

    fechamento = (
        "Recomenda-se acompanhamento pedagogico articulado entre docentes, coordenacao e familias, "
        "com foco na recomposicao das aprendizagens e no monitoramento sistematico dos casos registrados."
    )

    return {
        "total_registros": total_registros,
        "total_estudantes": total_estudantes,
        "motivos_frequentes": motivos_frequentes,
        "texto": " ".join(
            parte
            for parte in (abertura, fatores, estudantes_txt, fechamento)
            if parte
        ),
    }
