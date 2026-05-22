from collections import defaultdict

from services.pcpi_common_service import (
    _coletar_descricoes_registros,
    _coletar_observacoes_registros,
    _complemento_observacoes,
    _garantir_ponto_final,
    _normalizar_texto_chave,
    _texto_limpo,
)


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
        frases.append(_garantir_ponto_final(f"Reuniao com {participantes} para {finalidade}{observacoes}"))
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
                f"Orientacao ao professor {professor} sobre o uso de {recurso}"
                f"{complemento_finalidade}{observacoes}"
            )
        else:
            frase = f"Orientacao sobre o uso de {recurso}{complemento_finalidade}{observacoes}"
        frases.append(_garantir_ponto_final(frase))
    return frases


def _frases_registro(registros: list[dict]) -> list[str]:
    descricoes = _coletar_descricoes_registros(registros)
    observacoes = _coletar_observacoes_registros(registros)
    frase = "Registro e organizacao das demandas do turno, com atualizacao das informacoes"
    if descricoes:
        frase += f", contemplando {descricoes}"
    if observacoes:
        frase += f", considerando {observacoes}"
    return [_garantir_ponto_final(frase)]


def _frases_impressao(registros: list[dict]) -> list[str]:
    descricoes = _coletar_descricoes_registros(registros)
    observacoes = _coletar_observacoes_registros(registros)
    frase = "Impressao e organizacao de materiais pedagogicos solicitados no turno"
    if descricoes:
        frase += f", contemplando {descricoes}"
    if observacoes:
        frase += f", considerando {observacoes}"
    return [_garantir_ponto_final(frase)]


def _frases_adequacao_impressao(registros: list[dict]) -> list[str]:
    descricoes = _coletar_descricoes_registros(registros)
    observacoes = _coletar_observacoes_registros(registros)
    frase = "Adequacao de materiais impressos conforme necessidades pedagogicas especificas do turno"
    if descricoes:
        frase += f", com atendimento a {descricoes}"
    if observacoes:
        frase += f", considerando {observacoes}"
    return [_garantir_ponto_final(frase)]


def _frases_rede_social(registros: list[dict]) -> list[str]:
    descricoes = _coletar_descricoes_registros(registros)
    observacoes = _coletar_observacoes_registros(registros)
    frase = "Criacao de conteudos digitais para divulgacao institucional das acoes da escola"
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
            nome_projeto = "acoes do turno"
        observacoes = _complemento_observacoes(registro.get("observacoes"))
        frases.append(
            _garantir_ponto_final(f"Acompanhamento das acoes do projeto {nome_projeto}{observacoes}")
        )
    return frases


def _frases_gremio(registros: list[dict]) -> list[str]:
    descricoes = _coletar_descricoes_registros(registros)
    observacoes = _coletar_observacoes_registros(registros)
    frase = "Acompanhamento das acoes do Gremio Estudantil, com apoio aos encaminhamentos do turno"
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
            frase = f"Colaboracao com {referencia} nas acoes pedagogicas e tecnologicas do turno{observacoes}"
        else:
            frase = f"Colaboracao nas acoes pedagogicas e tecnologicas do turno{observacoes}"
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
        frases.append(_garantir_ponto_final(f"Organizacao e apoio ao evento {evento}{observacoes}"))
    return frases


def _frases_planejamento(registros: list[dict]) -> list[str]:
    descricoes = _coletar_descricoes_registros(registros)
    observacoes = _coletar_observacoes_registros(registros)
    frase = "Planejamento e organizacao das acoes pedagogicas e tecnologicas do turno"
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
            projeto = "atividade pedagogica em desenvolvimento"
        observacoes = _complemento_observacoes(registro.get("observacoes"))
        frases.append(
            _garantir_ponto_final(
                f"Elaboracao do Formulario II referente ao projeto {projeto}{observacoes}"
            )
        )
    return frases


def _frases_genericas(registros: list[dict]) -> list[str]:
    frases = []
    for registro in registros:
        descricao = _texto_limpo(registro.get("descricao_curta")) or "demanda do turno"
        observacoes = _complemento_observacoes(registro.get("observacoes"))
        frases.append(_garantir_ponto_final(f"Atendimento a demanda relacionada a {descricao}{observacoes}"))
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
