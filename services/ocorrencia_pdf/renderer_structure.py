from __future__ import annotations

import re

from PIL import Image, ImageDraw, ImageFont
from services.ocorrencia_disciplina_service import rotulo_gravidade_ocorrencia
from services.ocorrencia_pdf.constants import (
    A4_RETRATO_PIXELS_300_DPI,
    ALTURA_AREA_REGIMENTO,
    COR_BORDA,
    COR_DESTAQUE,
    COR_FUNDO,
    COR_TEXTO,
    COR_TEXTO_MUTED,
    MARGEM_BASE,
    MARGEM_TOPO,
    MARGEM_X,
    MOLDURA_INSET,
    NOME_ESCOLA,
    PDF_RESOLUTION_DPI,
    RODAPE_RESERVA,
    SECAO_REGIMENTO,
    SUBTITULO_REGISTRO,
    TIPO_REGISTRO_ESTUDANTE,
    TIPO_REGISTRO_GERAL,
    TIPO_REGISTRO_PROFESSOR,
    TITULO_CONTINUACAO,
    _carregar_fontes,
    _carregar_logo,
)
from services.ocorrencia_pdf.helpers import (
    _obter_estudantes_vinculados_ocorrencia,
    _obter_gravidade_ocorrencia,
    _obter_professores_vinculados_ocorrencia,
    _obter_titulo_documento,
)


class _RenderizadorEstruturaMixin:
    def __init__(self, ocorrencia: dict, turma: dict | None = None):
        self.ocorrencia = ocorrencia
        self.turma = turma or {}
        self.fontes = _carregar_fontes()
        self.logo = _carregar_logo()
        self.paginas: list[Image.Image] = []
        self.pagina_atual: Image.Image | None = None
        self.draw: ImageDraw.ImageDraw | None = None
        self.y = 0
        self._nova_pagina(continuacao=False)

    @property
    def largura(self) -> int:
        return A4_RETRATO_PIXELS_300_DPI[0]

    @property
    def altura(self) -> int:
        return A4_RETRATO_PIXELS_300_DPI[1]

    @property
    def esquerda(self) -> int:
        return MARGEM_X

    @property
    def direita(self) -> int:
        return self.largura - MARGEM_X

    @property
    def centro_x(self) -> int:
        return self.largura // 2

    def _reserva_rodape(self) -> int:
        tipo_registro = self._tipo_registro()
        participantes_estudantes = _obter_estudantes_vinculados_ocorrencia(self.ocorrencia)
        participantes_professores = _obter_professores_vinculados_ocorrencia(self.ocorrencia)
        if tipo_registro == TIPO_REGISTRO_GERAL:
            return 780
        if tipo_registro == TIPO_REGISTRO_ESTUDANTE and len(participantes_estudantes) > 1:
            return 520
        if tipo_registro == TIPO_REGISTRO_PROFESSOR and len(participantes_professores) > 1:
            return 520
        if tipo_registro in {TIPO_REGISTRO_PROFESSOR, TIPO_REGISTRO_ESTUDANTE}:
            return 430
        return RODAPE_RESERVA

    @property
    def limite_corpo(self) -> int:
        return self.altura - MARGEM_BASE - self._reserva_rodape()

    def _tipo_registro(self) -> str:
        from services.ocorrencia_pdf.helpers import _obter_tipo_registro

        return _obter_tipo_registro(self.ocorrencia)

    def _nova_pagina(self, *, continuacao: bool):
        pagina = Image.new("RGB", A4_RETRATO_PIXELS_300_DPI, COR_FUNDO)
        draw = ImageDraw.Draw(pagina)
        draw.rectangle(
            (MOLDURA_INSET, MOLDURA_INSET, self.largura - MOLDURA_INSET, self.altura - MOLDURA_INSET),
            outline=COR_BORDA,
            width=3,
        )
        self.paginas.append(pagina)
        self.pagina_atual = pagina
        self.draw = draw
        self.y = self._desenhar_cabecalho(continuacao=continuacao)

    def _medir_texto(self, texto: str, fonte: ImageFont.ImageFont) -> tuple[int, int]:
        bbox = self.draw.textbbox((0, 0), texto, font=fonte)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]

    def _altura_linha(self, fonte: ImageFont.ImageFont, fator: float = 1.3) -> int:
        _, altura = self._medir_texto("Ag", fonte)
        return max(int(altura * fator), altura + 6)

    def _desenhar_texto_centralizado(self, texto: str, fonte: ImageFont.ImageFont, y: int, *, fill=COR_TEXTO) -> int:
        largura, altura = self._medir_texto(texto, fonte)
        self.draw.text(((self.largura - largura) / 2, y), texto, fill=fill, font=fonte)
        return altura

    def _desenhar_titulo_destacado(self, texto: str, y: int) -> int:
        padding_x = 24
        padding_y = 14
        largura_max = max(200, self.largura - (MARGEM_X * 2) - padding_x * 2)
        linhas = self._quebrar_linhas(texto, self.fontes.titulo, largura_max)
        altura_linha = self._altura_linha(self.fontes.titulo, fator=1.08)
        largura_bloco = max(self._medir_texto(linha, self.fontes.titulo)[0] for linha in linhas)
        altura_bloco = max(len(linhas), 1) * altura_linha
        x = (self.largura - largura_bloco) / 2 - padding_x
        self.draw.rectangle((x, y, x + largura_bloco + padding_x * 2, y + altura_bloco + padding_y * 2), fill=COR_DESTAQUE)
        cursor_y = y + padding_y
        for linha in linhas:
            largura_linha, _ = self._medir_texto(linha, self.fontes.titulo)
            self.draw.text(((self.largura - largura_linha) / 2, cursor_y), linha, fill=COR_TEXTO, font=self.fontes.titulo)
            cursor_y += altura_linha
        return altura_bloco + padding_y * 2

    def _desenhar_cabecalho(self, *, continuacao: bool) -> int:
        y = MARGEM_TOPO
        y += self._desenhar_texto_centralizado(NOME_ESCOLA, self.fontes.escola, y, fill=(52, 57, 64))
        y += 18
        if self.logo is not None:
            logo_x = self.centro_x - (self.logo.width // 2)
            self.pagina_atual.paste(self.logo, (logo_x, y), self.logo if self.logo.mode == "RGBA" else None)
            y += self.logo.height + 24
        if continuacao:
            y += self._desenhar_texto_centralizado(TITULO_CONTINUACAO, self.fontes.pequeno_bold, y, fill=COR_TEXTO_MUTED)
            y += 14
        y += self._desenhar_texto_centralizado(SUBTITULO_REGISTRO, self.fontes.subtitulo, y)
        y += 8
        y += self._desenhar_titulo_destacado(_obter_titulo_documento(self.ocorrencia), y)
        gravidade = _obter_gravidade_ocorrencia(self.ocorrencia)
        y += 12
        y += self._desenhar_texto_centralizado(
            f"Gravidade: {rotulo_gravidade_ocorrencia(gravidade)}",
            self.fontes.pequeno_bold,
            y,
            fill=COR_TEXTO_MUTED,
        )
        return y + 28

    def _quebrar_linhas(self, texto: str, fonte: ImageFont.ImageFont, largura_max: int) -> list[str]:
        texto_limpo = re.sub(r"[ \t]+", " ", str(texto or "").replace("\r", "")).strip()
        if not texto_limpo:
            return [""]
        linhas: list[str] = []
        for paragrafo in texto_limpo.split("\n"):
            trecho = paragrafo.strip()
            if not trecho:
                linhas.append("")
                continue
            atual = ""
            for palavra in trecho.split(" "):
                candidata = palavra if not atual else f"{atual} {palavra}"
                if self._medir_texto(candidata, fonte)[0] <= largura_max:
                    atual = candidata
                elif atual:
                    linhas.append(atual)
                    atual = palavra
                else:
                    fragmento = ""
                    for caractere in palavra:
                        candidato_fragmento = f"{fragmento}{caractere}"
                        if self._medir_texto(candidato_fragmento, fonte)[0] <= largura_max:
                            fragmento = candidato_fragmento
                        else:
                            linhas.append(fragmento)
                            fragmento = caractere
                    atual = fragmento
            if atual:
                linhas.append(atual)
        return linhas or [""]

    def _garantir_espaco(self, altura_necessaria: int):
        if self.y + altura_necessaria > self.limite_corpo:
            self._nova_pagina(continuacao=True)

    def _adicionar_espaco(self, valor: int):
        self.y += valor

    def _desenhar_linha(self):
        self._garantir_espaco(16)
        self.draw.line((self.esquerda, self.y, self.direita, self.y), fill=COR_BORDA, width=2)
        self.y += 24

    def _adicionar_area_regimento_em_branco(self):
        altura_titulo = self._altura_linha(self.fontes.pequeno_bold, fator=1.1)
        self._garantir_espaco(altura_titulo + 18 + ALTURA_AREA_REGIMENTO + 18)
        largura_titulo, _ = self._medir_texto(SECAO_REGIMENTO, self.fontes.pequeno_bold)
        self.draw.text(((self.largura - largura_titulo) / 2, self.y), SECAO_REGIMENTO, fill=COR_TEXTO, font=self.fontes.pequeno_bold)
        self.y += altura_titulo + 18
        self.draw.rectangle((self.esquerda, self.y, self.direita, self.y + ALTURA_AREA_REGIMENTO), outline=COR_BORDA, width=2)
        self.y += ALTURA_AREA_REGIMENTO + 18
