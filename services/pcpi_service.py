import re
import unicodedata
from collections import defaultdict
from datetime import datetime

TURNOS_PCPI_CONFIG = {
    "MATUTINO": {"nome": "Matutino", "aulas": 5},
    "VESPERTINO": {"nome": "Vespertino", "aulas": 6},
}

TURNOS_AGENDAMENTO_POR_TURNO_PCPI = {
    "MATUTINO": {"MATUTINO", "INTEGRAL"},
    "VESPERTINO": {"VESPERTINO", "VESPERTINO_EM", "INTEGRAL"},
}
_AULAS_INTEGRAL_POR_TURNO_PCPI = {
    "MATUTINO": set(range(1, 6)),
    "VESPERTINO": set(range(6, 9)),
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
    "suporte_aula",
    "preparacao_recurso",
    "suporte_tecnico",
    "atendimento_alunos",
    "producao_material",
    "articulacao",
)

GRUPO_AUTOMATICO_STE = "ste"
GRUPO_AUTOMATICO_TECNOLOGIA = "tecnologia_educacional"
GRUPO_AUTOMATICO_AUDIOVISUAL = "recurso_audiovisual"
GRUPO_AUTOMATICO_APOIO = "apoio_pedagogico"

FECHAMENTO_PCPI_PADRAO = (
    "Acompanhamento contínuo das demandas do turno, com suporte pedagógico e "
    "tecnológico às ações planejadas pela unidade escolar."
)


def _texto_limpo(valor) -> str:
    return str(valor or "").strip()


def nome_turno_pcpi(turno: str) -> str:
    turno_norm = _texto_limpo(turno).upper()
    config = TURNOS_PCPI_CONFIG.get(turno_norm)
    if not config:
        return turno_norm or "Turno não informado"
    return str(config["nome"])


def turno_agendamento_pertence_ao_turno_pcpi(turno_agendamento: str, turno_pcpi: str) -> bool:
    turno_pcpi_norm = _texto_limpo(turno_pcpi).upper()
    turno_agendamento_norm = _texto_limpo(turno_agendamento).upper()
    turnos_equivalentes = TURNOS_AGENDAMENTO_POR_TURNO_PCPI.get(turno_pcpi_norm, {turno_pcpi_norm})
    return turno_agendamento_norm in turnos_equivalentes


def _aula_agendamento_para_int(valor) -> int | None:
    texto = _texto_limpo(valor)
    if not texto:
        return None

    correspondencia = re.search(r"\d+", texto)
    if not correspondencia:
        return None

    numero = int(correspondencia.group())
    return numero if numero > 0 else None


def _formatar_ordinal_aula(numero: int) -> str:
    return f"{numero}\u00AA aula"


def _formatar_lista_com_ponto_e_virgula(itens: list[str]) -> str:
    valores = _lista_unica_texto(itens)
    if not valores:
        return ""
    if len(valores) == 1:
        return valores[0]
    if len(valores) == 2:
        return f"{valores[0]}; e {valores[1]}"
    return "; ".join(valores[:-1]) + f"; e {valores[-1]}"


def agendamento_pertence_ao_turno_pcpi(agendamento: dict, turno_pcpi: str) -> bool:
    turno_agendamento = _texto_limpo((agendamento or {}).get("turno")).upper()
    turno_pcpi_norm = _texto_limpo(turno_pcpi).upper()
    if not turno_agendamento_pertence_ao_turno_pcpi(turno_agendamento, turno_pcpi_norm):
        return False

    if turno_agendamento != "INTEGRAL":
        return True

    aula = _aula_agendamento_para_int((agendamento or {}).get("aula"))
    if aula is None:
        return True

    aulas_permitidas = _AULAS_INTEGRAL_POR_TURNO_PCPI.get(turno_pcpi_norm)
    if not aulas_permitidas:
        return False
    return aula in aulas_permitidas


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


def _remover_pontuacao_final(texto: str) -> str:
    valor = _texto_limpo(texto)
    return valor.rstrip(" .,!?:;")


def _texto_inicial_minusculo(texto: str) -> str:
    valor = _texto_limpo(texto)
    if not valor:
        return ""
    return valor[:1].lower() + valor[1:]


def _complemento_com_prefixo(prefixo: str, valor: str) -> str:
    texto = _remover_pontuacao_final(valor)
    if not texto:
        return ""
    return f", {prefixo} {texto}"


def _complemento_resultado_manual(resultado: str) -> str:
    return _complemento_com_prefixo("com resultado de", resultado)


def _complemento_observacoes_manual(observacoes: str) -> str:
    return _complemento_com_prefixo("incluindo", observacoes)


def _complemento_turma_manual(turma: str) -> str:
    texto = _remover_pontuacao_final(turma)
    if not texto:
        return ""
    return f", na turma {texto}"


def _complemento_recurso_manual(recurso: str) -> str:
    texto = _remover_pontuacao_final(recurso)
    if not texto:
        return ""
    return f", com apoio de {texto}"


def _complemento_finalidade(finalidade: str, *, prefixo: str = "para") -> str:
    texto = _remover_pontuacao_final(finalidade)
    if not texto:
        return ""
    return f" {prefixo} {texto}"


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
        return "aos docentes atendidos no turno"
    if len(descritores) == 1:
        return f"ao professor {descritores[0]}"

    resumo = "demais docentes do turno" if len(descritores) > 3 else ""
    lista = _formatar_lista_resumida(descritores, limite=3, resumo=resumo)
    return f"aos professores {lista}"


def _formatar_docentes_destinatarios(itens: list[dict]) -> str:
    return _formatar_docentes_referencia(itens)


def _formatar_aulas_referencia(itens: list[dict]) -> str:
    aulas = []
    for item in itens:
        aula_num = _aula_agendamento_para_int(item.get("aula"))
        if aula_num is not None and aula_num not in aulas:
            aulas.append(aula_num)

    if not aulas:
        return ""

    rotulos = [_formatar_ordinal_aula(aula) for aula in sorted(aulas)]
    if len(rotulos) == 1:
        return f" durante a {rotulos[0]}"
    return f" durante as aulas {_formatar_lista_pt_br(rotulos)}"


def _formatar_turmas_referencia(itens: list[dict]) -> str:
    turmas = _lista_unica_texto(item.get("turma") for item in itens)
    if not turmas:
        return ""
    if len(turmas) == 1:
        return f" com atendimento a turma {turmas[0]}"
    resumo = "demais turmas atendidas" if len(turmas) > 3 else ""
    lista = _formatar_lista_resumida(turmas, limite=3, resumo=resumo)
    return f" com atendimento as turmas {lista}"


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
    texto = _remover_pontuacao_final(observacoes)
    if not texto:
        return ""
    return f", considerando {texto}"


def _complemento_resultado(resultado: str) -> str:
    texto = _remover_pontuacao_final(resultado)
    if not texto:
        return ""
    return f", resultando em {texto}"


def _tipo_atividade_pcpi(item: dict) -> str:
    tipo_atividade = _texto_limpo(item.get("tipo_atividade")).lower()
    if tipo_atividade in {"ste", "equipamento"}:
        return tipo_atividade

    categoria = _texto_limpo(item.get("categoria_uso"))
    if categoria == GRUPO_AUTOMATICO_STE:
        return "ste"
    return "equipamento"


def _disciplina_pcpi(item: dict) -> str:
    disciplina = _texto_limpo(item.get("disciplina"))
    if disciplina:
        return disciplina

    componentes = _lista_unica_texto(item.get("componentes") or [])
    return _formatar_lista_pt_br(componentes)


def _aula_pcpi(item: dict) -> str:
    aula = _texto_limpo(item.get("aula"))
    if not aula:
        return "aula não informada"

    if "aula" in aula.casefold():
        return aula

    aula_num = _aula_agendamento_para_int(aula)
    if aula_num is not None:
        return _formatar_ordinal_aula(aula_num)
    return aula


def _chave_docente_automatico(item: dict) -> tuple[str, str]:
    """Agrupa registros automáticos pelo docente e pela disciplina/componente."""
    professor_nome = _texto_limpo(item.get("professor_nome")) or "Professor não informado"
    disciplina = _disciplina_pcpi(item) or "disciplina não informada"
    return professor_nome, disciplina


def _acao_automatica_limpa(texto_acao_pcpi: str) -> str:
    """Limpa pequenos vícios vindos do banco para evitar frases como 'com acompanhou'."""
    texto = _remover_pontuacao_final(texto_acao_pcpi)
    if not texto:
        return ""

    texto = re.sub(r"^\s*(com|e)\s+", "", texto, flags=re.IGNORECASE)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def _naturalizar_acao_automatica(acao: str) -> str:
    """Transforma ações registradas como verbos soltos em complementos narrativos."""
    texto = _acao_automatica_limpa(acao)
    if not texto:
        return ""

    chave = _normalizar_texto_chave(texto)

    if "passar o video" in chave or "exibicao" in chave or "video" in chave:
        if "ste" in chave or "laboratorio" in chave:
            return "preparação e organização da STE para exibição de vídeo"
        return "organização dos equipamentos para exibição de vídeo"

    if "kahoot" in chave:
        return "acompanhamento do desenvolvimento da aula e auxílio na plataforma Kahoot"

    if "acompanhou o desenvolvimento da aula" in chave:
        texto = re.sub(
            r"acompanhou o desenvolvimento da aula",
            "acompanhamento do desenvolvimento da aula",
            texto,
            flags=re.IGNORECASE,
        )

    if "organizou os equipamentos" in chave or "organizacao do equipamento" in chave:
        return "organização dos equipamentos"

    if texto.lower().startswith("preparou "):
        texto = "preparação de " + texto[len("preparou ") :]

    return texto


def _acao_automatica_por_item_ste(item: dict) -> str:
    acao = _naturalizar_acao_automatica(item.get("texto_acao_pcpi"))
    if acao:
        return acao

    tema = _texto_limpo(item.get("tema_aula"))
    if tema:
        return f"acompanhamento do desenvolvimento da aula sobre {tema}"
    return "acompanhamento do desenvolvimento da aula"


def _acao_automatica_por_item_equipamento(item: dict) -> str:
    acao = _naturalizar_acao_automatica(item.get("texto_acao_pcpi"))
    recurso_agendado = (
        _texto_limpo(item.get("recurso_agendado"))
        or _texto_limpo(item.get("recurso_nome"))
        or "equipamento não informado"
    )

    if acao:
        return f"organização do uso de {recurso_agendado} e {acao}"
    return f"organização do uso de {recurso_agendado}"


def _normalizar_acao_automatica(acao: str) -> str:
    """Normaliza a ação apenas para comparar/agrupá-la."""
    return _normalizar_texto_chave(acao)


def _formatar_contextos_turma_aula(itens: list[dict]) -> str:
    """Formata pares turma/aula de forma natural, agrupando quando há mais de um atendimento."""
    pares = []
    for item in itens:
        turma = _texto_limpo(item.get("turma")) or "turma não informada"
        aula = _aula_pcpi(item)
        texto = f"{turma}, durante a {aula}"
        if texto not in pares:
            pares.append(texto)

    if not pares:
        return "com turma e aula não informadas"

    if len(pares) == 1:
        return f"com a turma {pares[0]}"

    return f"com as turmas {_formatar_lista_pt_br(pares)}"


def _formatar_contextos_turma_aula_respectivamente(itens: list[dict]) -> str:
    """Versão um pouco mais compacta para múltiplas turmas/aulas."""
    turmas = []
    aulas = []
    for item in itens:
        turma = _texto_limpo(item.get("turma")) or "turma não informada"
        aula = _aula_pcpi(item)
        if turma not in turmas:
            turmas.append(turma)
        if aula not in aulas:
            aulas.append(aula)

    if not turmas:
        return "com turma e aula não informadas"

    if len(turmas) == 1 and len(aulas) == 1:
        return f"com a turma {turmas[0]}, durante a {aulas[0]}"

    if len(turmas) == len(aulas):
        return (
            f"com as turmas {_formatar_lista_pt_br(turmas)}, "
            f"durante a {_formatar_lista_pt_br(aulas)}, respectivamente"
        )

    return _formatar_contextos_turma_aula(itens)


def _prefixo_docente(professor_nome: str, disciplina: str) -> str:
    if disciplina and disciplina != "disciplina não informada":
        return f"ao professor {professor_nome}, de {disciplina}"
    return f"ao professor {professor_nome}"


def _referencia_docente(professor_nome: str, disciplina: str) -> str:
    if disciplina and disciplina != "disciplina não informada":
        return f"o professor {professor_nome}, de {disciplina}"
    return f"o professor {professor_nome}"


def _frase_grupo_automatico_ste(professor_nome: str, disciplina: str, itens: list[dict]) -> str:
    grupos_por_acao: dict[str, list[dict]] = defaultdict(list)
    acoes_por_chave = {}

    for item in itens:
        acao = _acao_automatica_por_item_ste(item)
        chave = _normalizar_acao_automatica(acao)
        grupos_por_acao[chave].append(item)
        acoes_por_chave[chave] = acao

    partes = []
    for chave, itens_acao in grupos_por_acao.items():
        contexto = _formatar_contextos_turma_aula_respectivamente(itens_acao)
        acao = _texto_inicial_minusculo(acoes_por_chave[chave])
        partes.append(f"{contexto}, envolvendo {acao}")

    return _garantir_ponto_final(
        f"Foi prestado atendimento {_prefixo_docente(professor_nome, disciplina)}, "
        f"{_formatar_lista_com_ponto_e_virgula(partes)}"
    )


def _frase_grupo_automatico_equipamento(professor_nome: str, disciplina: str, itens: list[dict]) -> str:
    grupos_por_acao: dict[str, list[dict]] = defaultdict(list)
    acoes_por_chave = {}

    for item in itens:
        acao = _acao_automatica_por_item_equipamento(item)
        chave = _normalizar_acao_automatica(acao)
        grupos_por_acao[chave].append(item)
        acoes_por_chave[chave] = acao

    partes = []
    for chave, itens_acao in grupos_por_acao.items():
        contexto = _formatar_contextos_turma_aula_respectivamente(itens_acao)
        acao = _texto_inicial_minusculo(acoes_por_chave[chave])
        partes.append(f"{contexto}, para {acao}")

    return _garantir_ponto_final(
        f"Foram organizados e recolhidos recursos para {_referencia_docente(professor_nome, disciplina)}, "
        f"{_formatar_lista_com_ponto_e_virgula(partes)}"
    )


def _frase_automatica_por_tipo(tipo_atividade: str, itens: list[dict]) -> str:
    """Gera textos automáticos mais narrativos, agrupando por docente e ação."""
    grupos_docentes: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for item in itens:
        grupos_docentes[_chave_docente_automatico(item)].append(item)

    frases = []
    for (professor_nome, disciplina), itens_docente in grupos_docentes.items():
        if tipo_atividade == "ste":
            frases.append(_frase_grupo_automatico_ste(professor_nome, disciplina, itens_docente))
        else:
            frases.append(_frase_grupo_automatico_equipamento(professor_nome, disciplina, itens_docente))

    if not frases:
        return ""

    if tipo_atividade == "ste":
        titulo = "Atendimentos realizados na Sala de Tecnologia Educacional (STE):"
    else:
        titulo = "Organização e recolhimento de equipamentos e recursos:"

    return f"{titulo} {' '.join(frases)}"


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
        "aula_numero": _aula_agendamento_para_int(agendamento.get("aula")) or 0,
        "faixa_global": int(agendamento.get("faixa_global") or 0),
        "recurso_id": int(agendamento["recurso_id"]),
        "recurso_nome": recurso_nome,
        "recurso_tipo": recurso_tipo,
        "professor_id": int(agendamento["usuario_id"]),
        "professor_nome": _texto_limpo(agendamento.get("professor_nome")),
        "disciplina": _formatar_lista_pt_br(componentes),
        "componentes": componentes,
        "turma": _texto_limpo(agendamento.get("turma")),
        "tema_aula": _texto_limpo(agendamento.get("tema_aula")),
        "observacao": _texto_limpo(agendamento.get("observacao")),
        "categoria_uso": classificar_categoria_uso(recurso_nome, recurso_tipo),
        "tipo_atividade": (
            "ste"
            if classificar_categoria_uso(recurso_nome, recurso_tipo) == GRUPO_AUTOMATICO_STE
            else "equipamento"
        ),
        "recurso_agendado": recurso_nome,
        "texto_acao_pcpi": "",
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
        grupos[_tipo_atividade_pcpi(item)].append(item)

    frases = []
    if grupos["ste"]:
        frases.append(_frase_automatica_por_tipo("ste", grupos["ste"]))
    if grupos["equipamento"]:
        frases.append(_frase_automatica_por_tipo("equipamento", grupos["equipamento"]))
    return [frase for frase in frases if _texto_limpo(frase)]


def _contexto_registro_vinculado(registro: dict) -> str:
    turma = _texto_limpo(registro.get("turma"))
    professor = _texto_limpo(registro.get("professor_nome"))
    partes = []
    if turma:
        partes.append(f"da turma {turma}")
    if professor:
        partes.append(f"com o professor {professor}")
    if not partes:
        return "No atendimento agendado"
    return f"No atendimento agendado {' '.join(partes)}"


def _frases_execucoes_agendamento(registros: list[dict]) -> list[str]:
    frases = []
    for registro in registros:
        contexto = _contexto_registro_vinculado(registro)
        acao_realizada = _texto_limpo(registro.get("acao_realizada")) or "prestou apoio ao desenvolvimento da atividade"
        descricao = _remover_pontuacao_final(registro.get("descricao_curta")) or "demanda do turno"
        resultado = _complemento_resultado(registro.get("resultado"))
        observacoes = _complemento_observacoes(registro.get("observacoes"))
        frase = f"{contexto}, o PCPI {acao_realizada}, com foco em {descricao}{resultado}{observacoes}"
        frases.append(_garantir_ponto_final(frase))
    return frases


def _frases_reuniao(registros: list[dict]) -> list[str]:
    frases = []
    for registro in registros:
        participantes = (
            _texto_limpo(registro.get("professor_nome"))
            or "coordenação e demais profissionais da unidade escolar"
        )
        finalidade = (
            _texto_limpo(registro.get("descricao_curta"))
            or "alinhamento de demandas institucionais"
        )
        observacoes = _complemento_observacoes_manual(registro.get("observacoes"))
        frases.append(
            _garantir_ponto_final(
                f"Reunião com {participantes}{_complemento_finalidade(finalidade)}{observacoes}"
            )
        )
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
            complemento_finalidade = f", com foco em {_texto_inicial_minusculo(finalidade)}"
        observacoes = _complemento_observacoes_manual(registro.get("observacoes"))

        if professor:
            frase = (
                f"Orientação com o professor {professor} sobre o uso de {recurso}"
                f"{complemento_finalidade}{observacoes}"
            )
        else:
            frase = f"Orientação sobre o uso de {recurso}{complemento_finalidade}{observacoes}"
        frases.append(_garantir_ponto_final(frase))
    return frases


def _frases_registro(registros: list[dict]) -> list[str]:
    descricoes = _coletar_descricoes_registros(registros)
    observacoes = _coletar_observacoes_registros(registros)
    frase = "Registro e organização das demandas do turno, com atualização das informações"
    if descricoes:
        frase += f", contemplando {descricoes}"
    if observacoes:
        frase += f", incluindo {observacoes}"
    return [_garantir_ponto_final(frase)]


def _frases_impressao(registros: list[dict]) -> list[str]:
    descricoes = _coletar_descricoes_registros(registros)
    observacoes = _coletar_observacoes_registros(registros)
    frase = "Impressão e organização de materiais pedagógicos solicitados no turno"
    if descricoes:
        frase += f", contemplando {descricoes}"
    if observacoes:
        frase += f", incluindo {observacoes}"
    return [_garantir_ponto_final(frase)]


def _frases_adequacao_impressao(registros: list[dict]) -> list[str]:
    descricoes = _coletar_descricoes_registros(registros)
    observacoes = _coletar_observacoes_registros(registros)
    frase = "Adequação de materiais impressos conforme necessidades pedagógicas específicas do turno"
    if descricoes:
        frase += f", com atendimento a {descricoes}"
    if observacoes:
        frase += f", incluindo {observacoes}"
    return [_garantir_ponto_final(frase)]


def _frases_rede_social(registros: list[dict]) -> list[str]:
    descricoes = _coletar_descricoes_registros(registros)
    observacoes = _coletar_observacoes_registros(registros)
    frase = "Criação de conteúdos digitais para divulgação institucional das ações da escola"
    if descricoes:
        frase += f", com destaque para {descricoes}"
    if observacoes:
        frase += f", incluindo {observacoes}"
    return [_garantir_ponto_final(frase)]


def _frases_projeto(registros: list[dict]) -> list[str]:
    frases = []
    for registro in registros:
        nome_projeto = _texto_limpo(registro.get("componente")) or _texto_limpo(
            registro.get("descricao_curta")
        )
        if not nome_projeto:
            nome_projeto = "ações do turno"
        observacoes = _complemento_observacoes_manual(registro.get("observacoes"))
        frases.append(
            _garantir_ponto_final(f"Acompanhamento das ações do projeto {nome_projeto}{observacoes}")
        )
    return frases


def _frases_gremio(registros: list[dict]) -> list[str]:
    descricoes = _coletar_descricoes_registros(registros)
    observacoes = _coletar_observacoes_registros(registros)
    frase = "Acompanhamento das ações do Grêmio Estudantil, com apoio aos encaminhamentos do turno"
    if descricoes:
        frase += f", contemplando {descricoes}"
    if observacoes:
        frase += f", incluindo {observacoes}"
    return [_garantir_ponto_final(frase)]


def _frases_colaboracao(registros: list[dict]) -> list[str]:
    frases = []
    for registro in registros:
        referencia = _texto_limpo(registro.get("professor_nome")) or _texto_limpo(
            registro.get("descricao_curta")
        )
        observacoes = _complemento_observacoes_manual(registro.get("observacoes"))
        if referencia:
            frase = f"Ação colaborativa com {referencia} nas ações pedagógicas e tecnológicas do turno{observacoes}"
        else:
            frase = f"Ação colaborativa nas ações pedagógicas e tecnológicas do turno{observacoes}"
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
        observacoes = _complemento_observacoes_manual(registro.get("observacoes"))
        frases.append(_garantir_ponto_final(f"Organização e apoio ao evento {evento}{observacoes}"))
    return frases


def _frases_planejamento(registros: list[dict]) -> list[str]:
    descricoes = _coletar_descricoes_registros(registros)
    observacoes = _coletar_observacoes_registros(registros)
    frase = "Planejamento e organização das ações pedagógicas e tecnológicas do turno"
    if descricoes:
        frase += f", contemplando {descricoes}"
    if observacoes:
        frase += f", incluindo {observacoes}"
    return [_garantir_ponto_final(frase)]


def _frases_formulario2(registros: list[dict]) -> list[str]:
    frases = []
    for registro in registros:
        projeto = _texto_limpo(registro.get("descricao_curta")) or _texto_limpo(
            registro.get("componente")
        )
        if not projeto:
            projeto = "atividade pedagógica em desenvolvimento"
        observacoes = _complemento_observacoes_manual(registro.get("observacoes"))
        frases.append(
            _garantir_ponto_final(
                f"Elaboração do Formulário II referente ao projeto {projeto}{observacoes}"
            )
        )
    return frases


def _frases_suporte_aula(registros: list[dict]) -> list[str]:
    frases = []
    for registro in registros:
        acao_realizada = _texto_inicial_minusculo(registro.get("acao_realizada")) or "acompanhou a aula"
        descricao = _texto_inicial_minusculo(registro.get("descricao_curta")) or "atividade pedagógica do turno"
        resultado = _complemento_resultado_manual(registro.get("resultado"))
        observacoes = _complemento_observacoes_manual(registro.get("observacoes"))
        turma_txt = _complemento_turma_manual(registro.get("turma"))
        frases.append(
            _garantir_ponto_final(
                f"Ação pedagógica de suporte à aula{turma_txt}, em que o PCPI {acao_realizada}{_complemento_finalidade(descricao)}{resultado}{observacoes}"
            )
        )
    return frases


def _frases_preparacao_recurso(registros: list[dict]) -> list[str]:
    frases = []
    for registro in registros:
        recurso = _texto_limpo(registro.get("componente")) or "os recursos do turno"
        acao_realizada = _texto_inicial_minusculo(registro.get("acao_realizada")) or "organizou e preparou os equipamentos"
        descricao = _texto_inicial_minusculo(registro.get("descricao_curta")) or "atendimento planejado"
        resultado = _complemento_resultado_manual(registro.get("resultado"))
        observacoes = _complemento_observacoes_manual(registro.get("observacoes"))
        frases.append(
            _garantir_ponto_final(
                f"Preparação de recurso para {descricao}, em que o PCPI {acao_realizada} com {recurso}{resultado}{observacoes}"
            )
        )
    return frases


def _frases_suporte_tecnico(registros: list[dict]) -> list[str]:
    frases = []
    for registro in registros:
        acao_realizada = _texto_inicial_minusculo(registro.get("acao_realizada")) or "realizou ajustes técnicos"
        descricao = _texto_inicial_minusculo(registro.get("descricao_curta")) or "demanda tecnológica do turno"
        resultado = _complemento_resultado_manual(registro.get("resultado"))
        observacoes = _complemento_observacoes_manual(registro.get("observacoes"))
        frases.append(
            _garantir_ponto_final(
                f"Suporte técnico prestado no turno, em que o PCPI {acao_realizada}{_complemento_finalidade(descricao)}{resultado}{observacoes}"
            )
        )
    return frases


def _frases_atendimento_alunos(registros: list[dict]) -> list[str]:
    frases = []
    for registro in registros:
        acao_realizada = _texto_inicial_minusculo(registro.get("acao_realizada")) or "prestou atendimento aos estudantes"
        descricao = _texto_inicial_minusculo(registro.get("descricao_curta")) or "atividade em desenvolvimento"
        resultado = _complemento_resultado_manual(registro.get("resultado"))
        observacoes = _complemento_observacoes_manual(registro.get("observacoes"))
        frases.append(
            _garantir_ponto_final(
                f"Atendimento aos estudantes durante o turno, em que o PCPI {acao_realizada} em apoio a {descricao}{resultado}{observacoes}"
            )
        )
    return frases


def _frases_producao_material(registros: list[dict]) -> list[str]:
    frases = []
    for registro in registros:
        acao_realizada = _texto_inicial_minusculo(registro.get("acao_realizada")) or "produziu e organizou materiais"
        descricao = _texto_inicial_minusculo(registro.get("descricao_curta")) or "demanda pedagógica do turno"
        resultado = _complemento_resultado_manual(registro.get("resultado"))
        observacoes = _complemento_observacoes_manual(registro.get("observacoes"))
        frases.append(
            _garantir_ponto_final(
                f"Produção de material para {descricao}, em que o PCPI {acao_realizada}{resultado}{observacoes}"
            )
        )
    return frases


def _frases_articulacao(registros: list[dict]) -> list[str]:
    frases = []
    for registro in registros:
        referencia = _texto_limpo(registro.get("professor_nome")) or "a equipe escolar"
        acao_realizada = _texto_inicial_minusculo(registro.get("acao_realizada")) or "alinhou encaminhamentos"
        descricao = _texto_inicial_minusculo(registro.get("descricao_curta")) or "demandas do turno"
        resultado = _complemento_resultado_manual(registro.get("resultado"))
        observacoes = _complemento_observacoes_manual(registro.get("observacoes"))
        frases.append(
            _garantir_ponto_final(
                f"Articulação com {referencia}{_complemento_finalidade(descricao)}, em que o PCPI {acao_realizada}{resultado}{observacoes}"
            )
        )
    return frases


def _frases_genericas(registros: list[dict]) -> list[str]:
    frases = []
    for registro in registros:
        descricao = _texto_inicial_minusculo(registro.get("descricao_curta")) or "demanda do turno"
        observacoes = _complemento_observacoes_manual(registro.get("observacoes"))
        frases.append(_garantir_ponto_final(f"Atendimento relacionado a {descricao}{observacoes}"))
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
    "suporte_aula": _frases_suporte_aula,
    "preparacao_recurso": _frases_preparacao_recurso,
    "suporte_tecnico": _frases_suporte_tecnico,
    "atendimento_alunos": _frases_atendimento_alunos,
    "producao_material": _frases_producao_material,
    "articulacao": _frases_articulacao,
}


def gerar_frases_registros_manuais_pcpi(registros_manuais: list[dict]) -> list[str]:
    registros_manuais_livres = [
        registro
        for registro in (registros_manuais or [])
        if int(registro.get("agendamento_id") or 0) <= 0
    ]
    grupos: dict[str, list[dict]] = defaultdict(list)
    ordem_tipos = []

    for registro in registros_manuais_livres:
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


def _gerar_texto_pcpi_deterministico(
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
            f"Registro do turno {nome_turno_pcpi(turno)} de {_formatar_data_br(data)} sem acoes "
            "automaticas ou lancamentos manuais para composicao textual."
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


def gerar_texto_pcpi(
    data: str,
    turno: str,
    itens_automaticos: list[dict],
    registros_manuais: list[dict] | None = None,
) -> dict:
    return _gerar_texto_pcpi_deterministico(
        data,
        turno,
        itens_automaticos,
        registros_manuais,
    )


def gerar_texto_base_pcpi(
    data: str,
    turno: str,
    itens_automaticos: list[dict],
    registros_manuais: list[dict] | None = None,
) -> str:
    return _gerar_texto_pcpi_deterministico(
        data,
        turno,
        itens_automaticos,
        registros_manuais,
    ).get("texto", "")


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
