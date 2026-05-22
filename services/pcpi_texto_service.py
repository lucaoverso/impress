from collections import defaultdict

from services.pcpi_common_service import (
    FECHAMENTO_PCPI_PADRAO,
    GRUPO_AUTOMATICO_APOIO,
    GRUPO_AUTOMATICO_AUDIOVISUAL,
    GRUPO_AUTOMATICO_STE,
    GRUPO_AUTOMATICO_TECNOLOGIA,
    _aula_agendamento_para_int,
    _capitalizar_frase,
    _formatar_data_br,
    _formatar_lista_pt_br,
    _formatar_lista_resumida,
    _formatar_ordinal_aula,
    _garantir_ponto_final,
    _lista_unica_texto,
    _texto_limpo,
    nome_turno_pcpi,
)
from services.pcpi_texto_manual_service import gerar_frases_registros_manuais_pcpi


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


def _frase_automatica_ste(itens: list[dict]) -> str:
    docentes = _formatar_docentes_referencia(itens)
    aulas = _formatar_aulas_referencia(itens)
    turmas = _formatar_turmas_referencia(itens)
    frase = (
        "Atendimento na Sala de Tecnologia Educacional (STE), "
        f"com suporte {docentes}{aulas}{turmas} para realizacao das atividades digitais"
    )
    return _garantir_ponto_final(frase)


def _frase_automatica_tecnologia(itens: list[dict]) -> str:
    docentes = _formatar_docentes_referencia(itens)
    aulas = _formatar_aulas_referencia(itens)
    turmas = _formatar_turmas_referencia(itens)
    frase = (
        "Disponibilizacao e acompanhamento de recursos de tecnologia educacional, "
        f"com suporte {docentes}{aulas}{turmas} durante as atividades planejadas"
    )
    return _garantir_ponto_final(frase)


def _frase_automatica_audiovisual(itens: list[dict]) -> str:
    destinatarios = _formatar_docentes_referencia(itens)
    recursos = _formatar_recursos_referencia(itens)
    turmas = _formatar_turmas_referencia(itens)
    recursos_txt = f", com organizacao do uso de {recursos}" if recursos else ""
    frase = (
        "Entrega, organizacao e recolhimento de equipamentos audiovisuais "
        f"{destinatarios}{turmas}{recursos_txt}, para atendimento das aulas do turno"
    )
    return _garantir_ponto_final(frase)


def _frase_automatica_apoio(itens: list[dict]) -> str:
    recursos = _formatar_recursos_referencia(itens)
    turmas = _formatar_turmas_referencia(itens)
    complemento_recursos = f", com organizacao do uso de {recursos}" if recursos else ""
    frase = (
        "Organizacao de recursos de apoio pedagogico no turno"
        f"{turmas}{complemento_recursos}, garantindo atendimento as demandas apresentadas"
    )
    return _garantir_ponto_final(frase)


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
