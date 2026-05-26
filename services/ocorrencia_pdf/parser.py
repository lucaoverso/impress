from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser


@dataclass
class _TextoFormatadoRun:
    texto: str
    negrito: bool = False
    italico: bool = False
    cor_fundo: tuple[int, int, int] | None = None


@dataclass
class _EstiloTextoFormatado:
    negrito: bool = False
    italico: bool = False
    cor_fundo: tuple[int, int, int] | None = None


def _normalizar_cor_fundo_descricao(valor: str | None) -> tuple[int, int, int] | None:
    texto = str(valor or "").strip()
    if not texto:
        return None

    match_hex = re.fullmatch(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})", texto)
    if match_hex:
        cor = match_hex.group(1)
        if len(cor) == 3:
            cor = "".join(caractere * 2 for caractere in cor)
        return tuple(int(cor[indice : indice + 2], 16) for indice in (0, 2, 4))

    match_rgb = re.fullmatch(
        r"rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})(?:\s*,\s*(?:0|1|0?\.\d+))?\s*\)",
        texto,
        flags=re.IGNORECASE,
    )
    if not match_rgb:
        return None
    componentes = tuple(int(match_rgb.group(indice)) for indice in range(1, 4))
    if any(componente < 0 or componente > 255 for componente in componentes):
        return None
    return componentes


def _extrair_cor_fundo_descricao(style: str | None) -> tuple[int, int, int] | None:
    for declaracao in str(style or "").split(";"):
        propriedade, separador, valor = declaracao.partition(":")
        if separador and propriedade.strip().lower() == "background-color":
            return _normalizar_cor_fundo_descricao(valor)
    return None


class _DescricaoFormatadaParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.runs: list[_TextoFormatadoRun] = []
        self.estilos: list[_EstiloTextoFormatado] = [_EstiloTextoFormatado()]

    def _estilo_atual(self) -> _EstiloTextoFormatado:
        return self.estilos[-1]

    def _adicionar_texto(self, texto: str):
        if not texto:
            return
        estilo = self._estilo_atual()
        self.runs.append(
            _TextoFormatadoRun(
                texto=texto,
                negrito=estilo.negrito,
                italico=estilo.italico,
                cor_fundo=estilo.cor_fundo,
            )
        )

    def _adicionar_quebra(self):
        if self.runs and self.runs[-1].texto.endswith("\n"):
            return
        self._adicionar_texto("\n")

    def _empilhar_estilo(self, **alteracoes):
        atual = self._estilo_atual()
        self.estilos.append(
            _EstiloTextoFormatado(
                negrito=alteracoes.get("negrito", atual.negrito),
                italico=alteracoes.get("italico", atual.italico),
                cor_fundo=alteracoes.get("cor_fundo", atual.cor_fundo),
            )
        )

    def _desempilhar_estilo(self):
        if len(self.estilos) > 1:
            self.estilos.pop()

    def handle_starttag(self, tag: str, attrs):
        tag_norm = tag.lower()
        attrs_dict = {str(nome).lower(): str(valor or "") for nome, valor in attrs}
        if tag_norm in {"p", "div"}:
            self._adicionar_quebra()
        elif tag_norm == "br":
            self._adicionar_quebra()
        elif tag_norm in {"b", "strong"}:
            self._empilhar_estilo(negrito=True)
        elif tag_norm in {"i", "em"}:
            self._empilhar_estilo(italico=True)
        elif tag_norm == "mark":
            self._empilhar_estilo(
                cor_fundo=_extrair_cor_fundo_descricao(attrs_dict.get("style")) or (255, 243, 163)
            )
        elif tag_norm == "span":
            cor_fundo = _extrair_cor_fundo_descricao(attrs_dict.get("style"))
            if cor_fundo:
                self._empilhar_estilo(cor_fundo=cor_fundo)

    def handle_endtag(self, tag: str):
        tag_norm = tag.lower()
        if tag_norm in {"b", "strong", "i", "em", "mark", "span"}:
            self._desempilhar_estilo()
        elif tag_norm in {"p", "div"}:
            self._adicionar_quebra()

    def handle_data(self, data: str):
        self._adicionar_texto(data)


def _obter_runs_descricao_formatada(html: str | None) -> list[_TextoFormatadoRun]:
    parser = _DescricaoFormatadaParser()
    parser.feed(str(html or ""))
    parser.close()
    return [run for run in parser.runs if run.texto]
