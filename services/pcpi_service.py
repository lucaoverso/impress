from collections import defaultdict
from datetime import datetime
import unicodedata


TURNOS_PCPI_CONFIG = {
    "MATUTINO": {"nome": "Matutino", "aulas": 5},
    "VESPERTINO": {"nome": "Vespertino", "aulas": 6},
}

TURNOS_AGENDAMENTO_POR_TURNO_PCPI = {
    "MATUTINO": {"MATUTINO", "INTEGRAL"},
    "VESPERTINO": {"VESPERTINO", "VESPERTINO_EM", "INTEGRAL"},
}

TIPOS_ACAO_PCPI = (
    "reuniao",
    "orientacao",
    "rede_social",
    "registro",
    "impressao",
    "adequacao_impressao",
    "projeto",
    "gremio",
    "colaboracao",
    "evento",
    "planejamento",
    "formulario2",
)

GRUPO_AUTOMATICO_STE = "ste"
GRUPO_AUTOMATICO_TECNOLOGIA = "tecnologia_educacional"
GRUPO_AUTOMATICO_AUDIOVISUAL = "recurso_audiovisual"
GRUPO_AUTOMATICO_APOIO = "apoio_pedagogico"

FECHAMENTO_PCPI_PADRAO = (
    "Acompanhamento contínuo das demandas do turno, com suporte pedagógico e tecnológico "
    "às ações planejadas pela unidade escolar."
)


def nome_turno_pcpi(turno: str) -> str:
    turno_norm = str(turno or "").strip().upper()
    config = TURNOS_PCPI_CONFIG.get(turno_norm)
    if not config:
        return turno_norm or "Turno não informado"
    return str(config["nome"])


def turno_agendamento_pertence_ao_turno_pcpi(turno_agendamento: str, turno_pcpi: str) -> bool:
    turno_pcpi_norm = str(turno_pcpi or "").strip().upper()
    turno_agendamento_norm = str(turno_agendamento or "").strip().upper()
    turnos_equivalentes = TURNOS_AGENDAMENTO_POR_TURNO_PCPI.get(turno_pcpi_norm, {turno_pcpi_norm})
    return turno_agendamento_norm in turnos_equivalentes


def _texto_limpo(valor) -> str:
    return str(valor or "").strip()


def _normalizar_texto_chave(valor: str) -> str:
    texto = _texto_limpo(valor).lower()
    sem_acentos = "".join(
        caractere
        for caractere in unicodedata.normalize("NFD", texto)
        if unicodedata.category(caractere) != "Mn"
    )
    return " ".join(sem_acentos.split())


def _formatar_data_br(data_iso: str) -> str:
    try:
        return datetime.strptime(str(data_iso), "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return str(data_iso or "")


def _lista_unica_texto(valores) -> list[str]:
    itens = []
    for valor in valores or []:
        texto = _texto_limpo(valor)
        if texto and texto not in itens:
            itens.append(texto)
    return itens


def _formatar_lista_pt_br(itens: list[str]) -> str:
    valores = _lista_unica_texto(itens)
    if not valores:
        return ""
    if len(valores) == 1:
        return valores[0]
    if len(valores) == 2:
        return f"{valores[0]} e {valores[1]}"
    return ", ".join(valores[:-1]) + f" e {valores[-1]}"


def _formatar_lista_resumida(itens: list[str], *, limite: int = 3, resumo: str = "") -> str:
    valores = _lista_unica_texto(itens)
    if not valores:
        return ""
    if len(valores) <= limite:
        return _formatar_lista_pt_br(valores)

    prefixo = valores[:limite]
    if resumo:
        prefixo.append(resumo)
    return _formatar_lista_pt_br(prefixo)


def _capitalizar_frase(frase: str) -> str:
    texto = _texto_limpo(frase)
    if not texto:
        return ""
    return texto[0].upper() + texto[1:]


def _garantir_ponto_final(frase: str) -> str:
    texto = _texto_limpo(frase)
    if not texto:
        return ""
    if texto[-1] in ".!?":
        return texto
    return texto + "."


def _coletar_descritores_docentes(itens: list[dict]) -> list[str]:
    descritores = []
    for item in itens:
        nome = _texto_limpo(item.get("professor_nome"))
        componentes = _lista_unica_texto(item.get("componentes") or [])
        componente = _formatar_lista_resumida(componentes, limite=2, resumo="outros componentes")

        if nome and componente:
            descritor = f"{nome} ({componente})"
        elif nome:
            descritor = nome
        elif componente:
            descritor = componente
        else:
            descritor = ""

        if descritor and descritor not in descritores:
            descritores.append(descritor)
    return descritores


def _formatar_docentes_referencia(itens: list[dict]) -> str:
    descritores = _coletar_descritores_docentes(itens)
    if not descritores:
        return "docentes atendidos(as) no turno"
    if len(descritores) == 1:
        return f"o(a) professor(a) {descritores[0]}"

    resumo = "demais docentes do turno" if len(descritores) > 3 else ""
    lista = _formatar_lista_resumida(descritores, limite=3, resumo=resumo)
    return f"os(as) professores(as) {lista}"


def _formatar_docentes_destinatarios(itens: list[dict]) -> str:
    descritores = _coletar_descritores_docentes(itens)
    if not descritores:
        return "aos(às) docentes atendidos(as) no turno"
    if len(descritores) == 1:
        return f"ao(à) professor(a) {descritores[0]}"

    resumo = "demais docentes do turno" if len(descritores) > 3 else ""
    lista = _formatar_lista_resumida(descritores, limite=3, resumo=resumo)
    return f"aos(às) professores(as) {lista}"


def _formatar_aulas_referencia(itens: list[dict]) -> str:
    aulas = []
    for item in itens:
        aula_txt = _texto_limpo(item.get("aula"))
        if aula_txt.isdigit():
            aula_num = int(aula_txt)
            if aula_num > 0 and aula_num not in aulas:
                aulas.append(aula_num)

    if not aulas:
        return ""

    rotulos = [f"{aula}ª" for aula in sorted(aulas)]
    if len(rotulos) == 1:
        return f" durante a {rotulos[0]} aula"
    return f" durante a(s) {_formatar_lista_pt_br(rotulos)} aulas"


def _formatar_turmas_referencia(itens: list[dict]) -> str:
    turmas = _lista_unica_texto(item.get("turma") for item in itens)
    if not turmas:
        return ""
    if len(turmas) == 1:
        return f" com atendimento à turma {turmas[0]}"
    resumo = "demais turmas atendidas" if len(turmas) > 3 else ""
    lista = _formatar_lista_resumida(turmas, limite=3, resumo=resumo)
    return f" com atendimento às turmas {lista}"


def _formatar_recursos_referencia(itens: list[dict]) -> str:
    recursos = _lista_unica_texto(item.get("recurso_nome") for item in itens)
    return _formatar_lista_resumida(recursos, limite=3, resumo="outros recursos")


def _coletar_descricoes_registros(registros: list[dict], *, campo: str = "descricao_curta") -> str:
    valores = _lista_unica_texto(registro.get(campo) for registro in registros)
    return _formatar_lista_resumida(valores, limite=3, resumo="outras demandas do turno")


def _coletar_observacoes_registros(registros: list[dict]) -> str:
    valores = _lista_unica_texto(registro.get("observacoes") for registro in registros)
    return _formatar_lista_resumida(valores, limite=2, resumo="outros apontamentos do turno")


def _complemento_observacoes(observacoes: str) -> str:
    texto = _texto_limpo(observacoes)
    if not texto:
        return ""
    return f", considerando {texto}"


def _frase_automatica_ste(itens: list[dict]) -> str:
    docentes = _formatar_docentes_referencia(itens)
    aulas = _formatar_aulas_referencia(itens)
    turmas = _formatar_turmas_referencia(itens)
    frase = (
        "Disponibilização e acompanhamento na Sala de Tecnologia Educacional (STE), "
        f"auxiliando {docentes}{aulas}{turmas}, oferecendo suporte técnico e pedagógico "
        "na execução das atividades digitais"
    )
    return _garantir_ponto_final(frase)


def _frase_automatica_tecnologia(itens: list[dict]) -> str:
    docentes = _formatar_docentes_referencia(itens)
    aulas = _formatar_aulas_referencia(itens)
    turmas = _formatar_turmas_referencia(itens)
    frase = (
        "Disponibilização e acompanhamento de recursos de tecnologia educacional, "
        f"auxiliando {docentes}{aulas}{turmas}, com suporte técnico e pedagógico "
        "na execução das atividades digitais"
    )
    return _garantir_ponto_final(frase)


def _frase_automatica_audiovisual(itens: list[dict]) -> str:
    destinatarios = _formatar_docentes_destinatarios(itens)
    recursos = _formatar_recursos_referencia(itens)
    turmas = _formatar_turmas_referencia(itens)
    recursos_txt = f", com organização do uso de {recursos}" if recursos else ""
    frase = (
        "Entrega e recebimento de equipamentos tecnológicos "
        f"{destinatarios}, para utilização em sala de aula{turmas}{recursos_txt}, "
        "garantindo suporte ao uso adequado dos recursos audiovisuais"
    )
    return _garantir_ponto_final(frase)


def _frase_automatica_apoio(itens: list[dict]) -> str:
    recursos = _formatar_recursos_referencia(itens)
    turmas = _formatar_turmas_referencia(itens)
    complemento_recursos = f", com organização do uso de {recursos}" if recursos else ""
    frase = (
        "Atendimento e organização de recursos de apoio pedagógico no turno"
        f"{turmas}{complemento_recursos}, assegurando disponibilidade e suporte técnico "
        "às demandas apresentadas"
    )
    return _garantir_ponto_final(frase)


def classificar_categoria_uso(recurso_nome: str, recurso_tipo: str) -> str:
    chave = _normalizar_texto_chave(f"{recurso_nome} {recurso_tipo}")
    if any(
        token in chave for token in ("ste", "sala de tecnologia", "sala de tecnologia educacional")
    ):
        return GRUPO_AUTOMATICO_STE
    if any(
        token in chave
        for token in ("notebook", "tablet", "laboratorio", "maker", "computador", "tecnologia")
    ):
        return GRUPO_AUTOMATICO_TECNOLOGIA
    if any(
        token in chave
        for token in ("projetor", "datashow", "audio", "video", "som", "caixa de som")
    ):
        return GRUPO_AUTOMATICO_AUDIOVISUAL
    return GRUPO_AUTOMATICO_APOIO


def normalizar_agendamento_pcpi(
    agendamento: dict,
    carga_professor: dict | None = None,
    turno_pcpi: str | None = None,
) -> dict:
    carga = carga_professor or {}
    componentes = [
        _texto_limpo(item) for item in (carga.get("disciplinas") or []) if _texto_limpo(item)
    ]

    recurso_nome = _texto_limpo(agendamento.get("recurso_nome"))
    recurso_tipo = _texto_limpo(agendamento.get("recurso_tipo"))
    turno = _texto_limpo(turno_pcpi or agendamento.get("turno")).upper()

    return {
        "agendamento_id": int(agendamento["id"]),
        "data": _texto_limpo(agendamento.get("data")),
        "turno": turno,
        "turno_nome": nome_turno_pcpi(turno),
        "aula": _texto_limpo(agendamento.get("aula")),
        "faixa_global": int(agendamento.get("faixa_global") or 0),
        "recurso_id": int(agendamento["recurso_id"]),
        "recurso_nome": recurso_nome,
        "recurso_tipo": recurso_tipo,
        "professor_id": int(agendamento["usuario_id"]),
        "professor_nome": _texto_limpo(agendamento.get("professor_nome")),
        "componentes": componentes,
        "turma": _texto_limpo(agendamento.get("turma")),
        "tema_aula": _texto_limpo(agendamento.get("tema_aula")),
        "observacao": _texto_limpo(agendamento.get("observacao")),
        "categoria_uso": classificar_categoria_uso(recurso_nome, recurso_tipo),
    }


def _montar_resumo_sugestoes(itens: list[dict]) -> dict:
    recursos = _lista_unica_texto(item.get("recurso_nome") for item in itens)
    professores = _lista_unica_texto(item.get("professor_nome") for item in itens)
    turmas = _lista_unica_texto(item.get("turma") for item in itens)
    categorias = _lista_unica_texto(item.get("categoria_uso") for item in itens)
    return {
        "total_agendamentos": len(itens),
        "total_professores": len(professores),
        "total_turmas": len(turmas),
        "recursos": recursos,
        "categorias_uso": categorias,
    }


def gerar_frases_automaticas_pcpi(itens_automaticos: list[dict]) -> list[str]:
    grupos: dict[str, list[dict]] = defaultdict(list)
    for item in itens_automaticos or []:
        categoria = _texto_limpo(item.get("categoria_uso")) or GRUPO_AUTOMATICO_APOIO
        grupos[categoria].append(item)

    frases = []
    if grupos[GRUPO_AUTOMATICO_STE]:
        frases.append(_frase_automatica_ste(grupos[GRUPO_AUTOMATICO_STE]))
    if grupos[GRUPO_AUTOMATICO_TECNOLOGIA]:
        frases.append(_frase_automatica_tecnologia(grupos[GRUPO_AUTOMATICO_TECNOLOGIA]))
    if grupos[GRUPO_AUTOMATICO_AUDIOVISUAL]:
        frases.append(_frase_automatica_audiovisual(grupos[GRUPO_AUTOMATICO_AUDIOVISUAL]))
    if grupos[GRUPO_AUTOMATICO_APOIO]:
        frases.append(_frase_automatica_apoio(grupos[GRUPO_AUTOMATICO_APOIO]))
    return [frase for frase in frases if _texto_limpo(frase)]


def _frases_reuniao(registros: list[dict]) -> list[str]:
    frases = []
    for registro in registros:
        participantes = (
            _texto_limpo(registro.get("professor_nome"))
            or "setores e profissionais da unidade escolar"
        )
        finalidade = (
            _texto_limpo(registro.get("descricao_curta"))
            or "alinhamento de demandas institucionais"
        )
        observacoes = _complemento_observacoes(registro.get("observacoes"))
        frase = (
            f"Participação em reunião com {participantes}, para {finalidade}, "
            f"com organização das ações pedagógicas e tecnológicas da unidade escolar{observacoes}"
        )
        frases.append(_garantir_ponto_final(frase))
    return frases


def _frases_orientacao(registros: list[dict]) -> list[str]:
    frases = []
    for registro in registros:
        professor = _texto_limpo(registro.get("professor_nome"))
        recurso = _texto_limpo(registro.get("componente")) or _texto_limpo(
            registro.get("descricao_curta")
        )
        if not recurso:
            recurso = "recursos e ferramentas digitais"
        finalidade = _texto_limpo(registro.get("descricao_curta"))
        complemento_finalidade = ""
        if finalidade and _normalizar_texto_chave(finalidade) != _normalizar_texto_chave(recurso):
            complemento_finalidade = f", com foco em {finalidade}"
        observacoes = _complemento_observacoes(registro.get("observacoes"))

        if professor:
            frase = (
                f"Orientação ao(à) professor(a) {professor} quanto ao uso de {recurso}"
                f"{complemento_finalidade}, com foco na aplicação pedagógica do recurso{observacoes}"
            )
        else:
            frase = (
                f"Orientação quanto ao uso de {recurso}{complemento_finalidade}, "
                f"com foco na aplicação pedagógica do recurso{observacoes}"
            )
        frases.append(_garantir_ponto_final(frase))
    return frases


def _frases_registro(registros: list[dict]) -> list[str]:
    descricoes = _coletar_descricoes_registros(registros)
    observacoes = _coletar_observacoes_registros(registros)
    frase = (
        "Registro e sistematização das demandas do turno, com atualização de informações "
        "e acompanhamento administrativo e pedagógico"
    )
    if descricoes:
        frase += f", contemplando {descricoes}"
    if observacoes:
        frase += f", considerando {observacoes}"
    return [_garantir_ponto_final(frase)]


def _frases_impressao(registros: list[dict]) -> list[str]:
    descricoes = _coletar_descricoes_registros(registros)
    observacoes = _coletar_observacoes_registros(registros)
    frase = (
        "Produção e organização de impressões de materiais pedagógicos, conforme demandas "
        "apresentadas pelos docentes, visando subsidiar o planejamento e a execução das aulas"
    )
    if descricoes:
        frase += f", contemplando {descricoes}"
    if observacoes:
        frase += f", considerando {observacoes}"
    return [_garantir_ponto_final(frase)]


def _frases_adequacao_impressao(registros: list[dict]) -> list[str]:
    descricoes = _coletar_descricoes_registros(registros)
    observacoes = _coletar_observacoes_registros(registros)
    frase = (
        "Produção e adequação de materiais impressos, considerando as necessidades "
        "pedagógicas específicas apresentadas no turno"
    )
    if descricoes:
        frase += f", com atendimento a {descricoes}"
    if observacoes:
        frase += f", considerando {observacoes}"
    return [_garantir_ponto_final(frase)]


def _frases_rede_social(registros: list[dict]) -> list[str]:
    descricoes = _coletar_descricoes_registros(registros)
    observacoes = _coletar_observacoes_registros(registros)
    frase = (
        "Criação e elaboração de conteúdos digitais para divulgação institucional "
        "das ações pedagógicas desenvolvidas pela escola"
    )
    if descricoes:
        frase += f", com destaque para {descricoes}"
    if observacoes:
        frase += f", considerando {observacoes}"
    return [_garantir_ponto_final(frase)]


def _frases_projeto(registros: list[dict]) -> list[str]:
    frases = []
    for registro in registros:
        nome_projeto = _texto_limpo(registro.get("componente")) or _texto_limpo(
            registro.get("descricao_curta")
        )
        if not nome_projeto:
            nome_projeto = "ações do turno"
        observacoes = _complemento_observacoes(registro.get("observacoes"))
        frase = (
            f"Elaboração e acompanhamento de ações referentes ao projeto {nome_projeto}, "
            f"com organização de materiais, orientações e encaminhamentos pedagógicos{observacoes}"
        )
        frases.append(_garantir_ponto_final(frase))
    return frases


def _frases_gremio(registros: list[dict]) -> list[str]:
    descricoes = _coletar_descricoes_registros(registros)
    observacoes = _coletar_observacoes_registros(registros)
    frase = (
        "Acompanhamento e organização de ações relacionadas ao Grêmio Estudantil, "
        "com apoio aos encaminhamentos e registros do processo"
    )
    if descricoes:
        frase += f", contemplando {descricoes}"
    if observacoes:
        frase += f", considerando {observacoes}"
    return [_garantir_ponto_final(frase)]


def _frases_colaboracao(registros: list[dict]) -> list[str]:
    frases = []
    for registro in registros:
        referencia = _texto_limpo(registro.get("professor_nome")) or _texto_limpo(
            registro.get("descricao_curta")
        )
        observacoes = _complemento_observacoes(registro.get("observacoes"))
        if referencia:
            frase = (
                f"Colaboração com {referencia}, visando ao desenvolvimento de ações "
                f"pedagógicas e tecnológicas no turno{observacoes}"
            )
        else:
            frase = (
                "Colaboração no desenvolvimento de ações pedagógicas e tecnológicas "
                f"do turno{observacoes}"
            )
        frases.append(_garantir_ponto_final(frase))
    return frases


def _frases_evento(registros: list[dict]) -> list[str]:
    frases = []
    for registro in registros:
        evento = _texto_limpo(registro.get("descricao_curta")) or _texto_limpo(
            registro.get("componente")
        )
        if not evento:
            evento = "atividade institucional"
        observacoes = _complemento_observacoes(registro.get("observacoes"))
        frase = (
            f"Organização e apoio às ações relacionadas ao evento {evento}, "
            f"com acompanhamento dos encaminhamentos pedagógicos e tecnológicos necessários{observacoes}"
        )
        frases.append(_garantir_ponto_final(frase))
    return frases


def _frases_planejamento(registros: list[dict]) -> list[str]:
    descricoes = _coletar_descricoes_registros(registros)
    observacoes = _coletar_observacoes_registros(registros)
    frase = (
        "Planejamento e organização das ações pedagógicas e tecnológicas do turno, "
        "voltados ao atendimento das demandas institucionais apresentadas"
    )
    if descricoes:
        frase += f", contemplando {descricoes}"
    if observacoes:
        frase += f", considerando {observacoes}"
    return [_garantir_ponto_final(frase)]


def _frases_formulario2(registros: list[dict]) -> list[str]:
    frases = []
    for registro in registros:
        projeto = _texto_limpo(registro.get("descricao_curta")) or _texto_limpo(
            registro.get("componente")
        )
        if not projeto:
            projeto = "atividade pedagógica em desenvolvimento"
        observacoes = _complemento_observacoes(registro.get("observacoes"))
        frase = (
            f"Elaboração do Formulário II referente ao projeto {projeto}, com estruturação "
            f"de objetivos, metodologia, estratégias e critérios de avaliação{observacoes}"
        )
        frases.append(_garantir_ponto_final(frase))
    return frases


def _frases_genericas(registros: list[dict]) -> list[str]:
    frases = []
    for registro in registros:
        descricao = _texto_limpo(registro.get("descricao_curta")) or "demanda do turno"
        observacoes = _complemento_observacoes(registro.get("observacoes"))
        frase = (
            f"Atendimento e organização de demanda relacionada a {descricao}, "
            f"com suporte pedagógico e tecnológico no turno{observacoes}"
        )
        frases.append(_garantir_ponto_final(frase))
    return frases


FORMATADORES_ACAO_MANUAL = {
    "reuniao": _frases_reuniao,
    "orientacao": _frases_orientacao,
    "rede_social": _frases_rede_social,
    "registro": _frases_registro,
    "impressao": _frases_impressao,
    "adequacao_impressao": _frases_adequacao_impressao,
    "projeto": _frases_projeto,
    "gremio": _frases_gremio,
    "colaboracao": _frases_colaboracao,
    "evento": _frases_evento,
    "planejamento": _frases_planejamento,
    "formulario2": _frases_formulario2,
}


def gerar_frases_registros_manuais_pcpi(registros_manuais: list[dict]) -> list[str]:
    grupos: dict[str, list[dict]] = defaultdict(list)
    ordem_tipos = []

    for registro in registros_manuais or []:
        tipo = _texto_limpo(registro.get("tipo_acao"))
        if not tipo:
            continue
        if tipo not in ordem_tipos:
            ordem_tipos.append(tipo)
        grupos[tipo].append(registro)

    frases = []
    for tipo in ordem_tipos:
        formatador = FORMATADORES_ACAO_MANUAL.get(tipo, _frases_genericas)
        frases.extend(formatador(grupos[tipo]))
    return [frase for frase in frases if _texto_limpo(frase)]


def _precisa_fechamento(frases_automaticas: list[str], frases_manuais: list[str]) -> bool:
    frases = [
        frase
        for frase in (frases_automaticas or []) + (frases_manuais or [])
        if _texto_limpo(frase)
    ]
    if len(frases) <= 1:
        return True
    texto = " ".join(frases)
    return len(texto) < 260


def gerar_texto_pcpi(
    data: str,
    turno: str,
    itens_automaticos: list[dict],
    registros_manuais: list[dict] | None = None,
) -> dict:
    registros = registros_manuais or []
    frases_automaticas = gerar_frases_automaticas_pcpi(itens_automaticos)
    frases_manuais = gerar_frases_registros_manuais_pcpi(registros)

    frase_fechamento = ""
    if not frases_automaticas and not frases_manuais:
        frase_fechamento = (
            f"Registro do turno {nome_turno_pcpi(turno)} de {_formatar_data_br(data)} sem ações "
            "automáticas ou lançamentos manuais para composição textual."
        )
    elif _precisa_fechamento(frases_automaticas, frases_manuais):
        frase_fechamento = FECHAMENTO_PCPI_PADRAO

    blocos = frases_automaticas + frases_manuais
    if frase_fechamento:
        blocos.append(_garantir_ponto_final(frase_fechamento))
    texto = " ".join(_capitalizar_frase(bloco) for bloco in blocos if _texto_limpo(bloco)).strip()

    return {
        "data": data,
        "turno": _texto_limpo(turno).upper(),
        "turno_nome": nome_turno_pcpi(turno),
        "total_agendamentos": len(itens_automaticos or []),
        "total_registros_manuais": len(registros),
        "frases_automaticas": frases_automaticas,
        "frases_manuais": frases_manuais,
        "frase_fechamento": _garantir_ponto_final(frase_fechamento) if frase_fechamento else "",
        "texto": texto,
    }


def gerar_texto_base_pcpi(
    data: str,
    turno: str,
    itens_automaticos: list[dict],
    registros_manuais: list[dict] | None = None,
) -> str:
    return gerar_texto_pcpi(data, turno, itens_automaticos, registros_manuais).get("texto", "")


def montar_sugestoes_pcpi(
    data: str,
    turno: str,
    agendamentos: list[dict],
    cargas_professores: dict[int, dict] | None = None,
) -> dict:
    cargas = cargas_professores or {}
    itens = []

    for agendamento in sorted(
        agendamentos,
        key=lambda item: (
            int(item.get("faixa_global") or 0),
            _texto_limpo(item.get("recurso_nome")),
            _texto_limpo(item.get("turma")),
        ),
    ):
        usuario_id = int(agendamento.get("usuario_id") or 0)
        itens.append(normalizar_agendamento_pcpi(agendamento, cargas.get(usuario_id), turno))

    return {
        "data": data,
        "turno": _texto_limpo(turno).upper(),
        "turno_nome": nome_turno_pcpi(turno),
        "resumo": _montar_resumo_sugestoes(itens),
        "itens": itens,
        "texto_base": gerar_texto_base_pcpi(data, turno, itens),
    }
