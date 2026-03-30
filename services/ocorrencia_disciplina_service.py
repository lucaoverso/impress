from __future__ import annotations

import re

GRAVIDADE_LEVE = "leve"
GRAVIDADE_GRAVE = "grave"
GRAVIDADE_GRAVISSIMA = "gravissima"
GRAVIDADES_OCORRENCIA = (
    GRAVIDADE_LEVE,
    GRAVIDADE_GRAVE,
    GRAVIDADE_GRAVISSIMA,
)
GRAVIDADES_ROTULOS = {
    GRAVIDADE_LEVE: "Falta leve",
    GRAVIDADE_GRAVE: "Falta grave",
    GRAVIDADE_GRAVISSIMA: "Falta gravissima",
}
_GRAVIDADES_ORDEM = {
    GRAVIDADE_LEVE: 1,
    GRAVIDADE_GRAVE: 2,
    GRAVIDADE_GRAVISSIMA: 3,
}

ACAO_OCORRENCIA_ADVERTENCIA_VERBAL = "advertencia_verbal"
ACAO_OCORRENCIA_RETIRADA_SALA_ORIENTACAO = "retirada_sala_orientacao"
ACAO_OCORRENCIA_SUSPENSAO_EXTRACURRICULAR = "suspensao_extracurricular"
ACAO_OCORRENCIA_SUSPENSAO_ORIENTADA_2_DIAS = "suspensao_orientada_2_dias"
ACAO_OCORRENCIA_SUSPENSAO_AULAS_3_DIAS = "suspensao_aulas_3_dias"
ACAO_OCORRENCIA_TRANSFERENCIA_COMPULSORIA = "transferencia_compulsoria"

ACAO_OCORRENCIA_ORIENTACAO_VERBAL = "orientacao_verbal"
ACAO_OCORRENCIA_ADVERTENCIA = "advertencia"
ACAO_OCORRENCIA_CHAMADA_RESPONSAVEL = "chamada_responsavel"
ACAO_OCORRENCIA_ENCAMINHAMENTO_DIRECAO = "encaminhamento_direcao"
ACAO_OCORRENCIA_REGISTRO_INFORMATIVO = "registro_informativo"

ACOES_OCORRENCIA_DETALHADAS = (
    ACAO_OCORRENCIA_ADVERTENCIA_VERBAL,
    ACAO_OCORRENCIA_RETIRADA_SALA_ORIENTACAO,
    ACAO_OCORRENCIA_SUSPENSAO_EXTRACURRICULAR,
    ACAO_OCORRENCIA_SUSPENSAO_ORIENTADA_2_DIAS,
    ACAO_OCORRENCIA_SUSPENSAO_AULAS_3_DIAS,
    ACAO_OCORRENCIA_TRANSFERENCIA_COMPULSORIA,
)
ACOES_OCORRENCIA_LEGADAS = (
    ACAO_OCORRENCIA_ORIENTACAO_VERBAL,
    ACAO_OCORRENCIA_ADVERTENCIA,
    ACAO_OCORRENCIA_CHAMADA_RESPONSAVEL,
    ACAO_OCORRENCIA_ENCAMINHAMENTO_DIRECAO,
    ACAO_OCORRENCIA_REGISTRO_INFORMATIVO,
)
ACAO_OCORRENCIA_VALIDAS = ACOES_OCORRENCIA_DETALHADAS + ACOES_OCORRENCIA_LEGADAS

ACOES_ROTULOS = {
    ACAO_OCORRENCIA_ADVERTENCIA_VERBAL: "Advertencia verbal",
    ACAO_OCORRENCIA_RETIRADA_SALA_ORIENTACAO: (
        "Retirada de sala e encaminhamento para orientacao"
    ),
    ACAO_OCORRENCIA_SUSPENSAO_EXTRACURRICULAR: (
        "Suspensao temporaria em programas extracurriculares"
    ),
    ACAO_OCORRENCIA_SUSPENSAO_ORIENTADA_2_DIAS: (
        "Suspensao orientada das aulas (ate 2 dias letivos)"
    ),
    ACAO_OCORRENCIA_SUSPENSAO_AULAS_3_DIAS: (
        "Suspensao das aulas (ate 3 dias letivos)"
    ),
    ACAO_OCORRENCIA_TRANSFERENCIA_COMPULSORIA: "Transferencia compulsoria",
    ACAO_OCORRENCIA_ORIENTACAO_VERBAL: "Orientacao verbal",
    ACAO_OCORRENCIA_ADVERTENCIA: "Advertencia",
    ACAO_OCORRENCIA_CHAMADA_RESPONSAVEL: "Chamada de responsavel",
    ACAO_OCORRENCIA_ENCAMINHAMENTO_DIRECAO: "Encaminhamento a direcao",
    ACAO_OCORRENCIA_REGISTRO_INFORMATIVO: "Registro informativo",
}

ACOES_POR_GRAVIDADE = {
    GRAVIDADE_LEVE: (
        ACAO_OCORRENCIA_ADVERTENCIA_VERBAL,
        ACAO_OCORRENCIA_RETIRADA_SALA_ORIENTACAO,
    ),
    GRAVIDADE_GRAVE: (
        ACAO_OCORRENCIA_SUSPENSAO_EXTRACURRICULAR,
        ACAO_OCORRENCIA_SUSPENSAO_ORIENTADA_2_DIAS,
    ),
    GRAVIDADE_GRAVISSIMA: (
        ACAO_OCORRENCIA_SUSPENSAO_AULAS_3_DIAS,
        ACAO_OCORRENCIA_TRANSFERENCIA_COMPULSORIA,
    ),
}

_REGEX_ARTIGO = re.compile(r"Art\.?\s*([^\s,;:-]+(?:[-A-Za-z0-9.]+)?)", re.IGNORECASE)
_REGEX_INCISO = re.compile(r"(?:inciso\s+([IVXLCDM]+)|-\s*([IVXLCDM]+)\b)", re.IGNORECASE)


def _texto_limpo(valor) -> str:
    return str(valor or "").strip()


def _normalizar_numero_artigo(valor) -> str:
    return re.sub(r"^art\.?\s*", "", _texto_limpo(valor), flags=re.IGNORECASE)


def _normalizar_numero_inciso(valor) -> str:
    return _texto_limpo(valor).upper()


def _extrair_artigo_e_inciso(item: dict | None) -> tuple[str, str]:
    dados = item if isinstance(item, dict) else {}
    artigo_numero = _normalizar_numero_artigo(dados.get("artigo_numero"))
    inciso_numero = _normalizar_numero_inciso(dados.get("inciso_numero"))
    artigo_rotulo = _texto_limpo(dados.get("artigo"))

    if artigo_rotulo and not artigo_numero:
        match_artigo = _REGEX_ARTIGO.search(artigo_rotulo)
        if match_artigo:
            artigo_numero = _normalizar_numero_artigo(match_artigo.group(1))

    if artigo_rotulo and not inciso_numero:
        match_inciso = _REGEX_INCISO.search(artigo_rotulo)
        if match_inciso:
            inciso_numero = _normalizar_numero_inciso(
                match_inciso.group(1) or match_inciso.group(2)
            )

    return artigo_numero, inciso_numero


def _romano_para_int(valor: str | None) -> int | None:
    texto = _normalizar_numero_inciso(valor)
    if not texto:
        return None
    mapa = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    anterior = 0
    for simbolo in reversed(texto):
        atual = mapa.get(simbolo)
        if atual is None:
            return None
        if atual < anterior:
            total -= atual
        else:
            total += atual
            anterior = atual
    return total


def rotulo_acao_ocorrencia(valor: str | None) -> str:
    texto = _texto_limpo(valor)
    return ACOES_ROTULOS.get(texto, texto or "Nao informada")


def rotulo_gravidade_ocorrencia(valor: str | None) -> str:
    texto = _texto_limpo(valor).lower()
    return GRAVIDADES_ROTULOS.get(texto, texto or "Nao identificada")


def listar_acoes_aplicadas() -> list[dict]:
    opcoes = []
    ordem = 1
    for gravidade in GRAVIDADES_OCORRENCIA:
        for acao in ACOES_POR_GRAVIDADE[gravidade]:
            opcoes.append(
                {
                    "id": acao,
                    "nome": rotulo_acao_ocorrencia(acao),
                    "gravidade": gravidade,
                    "legado": False,
                    "ordem": ordem,
                }
            )
            ordem += 1

    for acao in ACOES_OCORRENCIA_LEGADAS:
        opcoes.append(
            {
                "id": acao,
                "nome": f"{rotulo_acao_ocorrencia(acao)} (legado)",
                "gravidade": None,
                "legado": True,
                "ordem": ordem,
            }
        )
        ordem += 1
    return opcoes


def acoes_permitidas_por_gravidade(gravidade: str | None) -> tuple[str, ...]:
    gravidade_norm = _texto_limpo(gravidade).lower()
    return ACOES_POR_GRAVIDADE.get(gravidade_norm, ())


def acao_compativel_com_gravidade(acao: str | None, gravidade: str | None) -> bool:
    acao_norm = _texto_limpo(acao)
    if not acao_norm:
        return False
    if acao_norm in ACOES_OCORRENCIA_LEGADAS:
        return True

    permitidas = acoes_permitidas_por_gravidade(gravidade)
    if not permitidas:
        return acao_norm in ACAO_OCORRENCIA_VALIDAS
    return acao_norm in permitidas


def inferir_gravidade_item_base_legal(item: dict | None) -> str | None:
    artigo_numero, inciso_numero = _extrair_artigo_e_inciso(item)
    if not artigo_numero:
        return None

    if artigo_numero == "76":
        return GRAVIDADE_LEVE

    if artigo_numero == "81":
        inciso_valor = _romano_para_int(inciso_numero)
        if inciso_valor == 1:
            return GRAVIDADE_LEVE
        if inciso_valor == 2:
            return GRAVIDADE_GRAVE
        if inciso_valor == 3:
            return GRAVIDADE_GRAVISSIMA
        return None

    if artigo_numero == "82":
        inciso_valor = _romano_para_int(inciso_numero)
        if inciso_valor == 1:
            return GRAVIDADE_LEVE
        if inciso_valor == 2:
            return GRAVIDADE_GRAVE
        if inciso_valor == 3:
            return GRAVIDADE_GRAVISSIMA
        return None

    if artigo_numero != "77":
        return None

    inciso_valor = _romano_para_int(inciso_numero)
    if inciso_valor is None:
        return None
    if 1 <= inciso_valor <= 7:
        return GRAVIDADE_LEVE
    if 8 <= inciso_valor <= 13:
        return GRAVIDADE_GRAVE
    if 14 <= inciso_valor <= 26:
        return GRAVIDADE_GRAVISSIMA
    return None


def inferir_gravidade_ocorrencia(itens: list[dict] | None) -> str | None:
    gravidade_final = None
    ordem_final = 0
    for item in itens or []:
        gravidade_item = inferir_gravidade_item_base_legal(item)
        ordem_item = _GRAVIDADES_ORDEM.get(gravidade_item or "", 0)
        if ordem_item > ordem_final:
            gravidade_final = gravidade_item
            ordem_final = ordem_item
    return gravidade_final
