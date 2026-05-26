from __future__ import annotations

import re

from PIL import ImageFont
from services.ocorrencia_pdf.base_legal import _montar_blocos_base_legal
from services.ocorrencia_pdf.constants import COR_TEXTO, SECAO_REGIMENTO
from services.ocorrencia_pdf.parser import _TextoFormatadoRun


class _RenderizadorConteudoMixin:
    def _adicionar_secao_regimento(self, itens: list[dict]):
        self._adicionar_titulo_secao(SECAO_REGIMENTO)
        blocos = _montar_blocos_base_legal(itens)
        for indice, bloco in enumerate(blocos):
            tipo = str(bloco.get("tipo") or "").strip().lower()
            texto = str(bloco.get("texto") or "").strip()
            if not texto:
                continue
            if tipo == "lei":
                self._adicionar_paragrafos(texto, fonte=self.fontes.pequeno_bold, espaco_final=4)
                self._adicionar_espaco(4)
            elif tipo == "artigo":
                self._adicionar_paragrafos(texto, fonte=self.fontes.pequeno_bold, espaco_final=2)
            elif tipo == "inciso":
                self._adicionar_paragrafos(texto, fonte=self.fontes.pequeno, recuo=36, espaco_final=2)
            elif tipo == "alinea":
                self._adicionar_paragrafos(texto, fonte=self.fontes.pequeno, recuo=74, espaco_final=2)
            else:
                self._adicionar_paragrafos(texto, fonte=self.fontes.pequeno, espaco_final=2)

            proximo_tipo = str(blocos[indice + 1].get("tipo") or "").strip().lower() if indice < len(blocos) - 1 else ""
            if tipo == "alinea" and proximo_tipo != "alinea":
                self._adicionar_espaco(4)
            if tipo == "inciso" and proximo_tipo not in {"alinea", "inciso"}:
                self._adicionar_espaco(4)

    def _adicionar_rotulo_valor(self, rotulo: str, valor: str):
        prefixo = f"{rotulo}: "
        largura_prefixo, _ = self._medir_texto(prefixo, self.fontes.corpo_bold)
        largura_disponivel = self.direita - self.esquerda
        altura_linha = self._altura_linha(self.fontes.corpo, fator=1.5)
        if largura_prefixo > largura_disponivel * 0.52:
            linhas_rotulo = self._quebrar_linhas(rotulo, self.fontes.corpo_bold, largura_disponivel)
            linhas_valor = self._quebrar_linhas(valor, self.fontes.corpo, largura_disponivel)
            self._garantir_espaco((len(linhas_rotulo) + len(linhas_valor)) * altura_linha + 12)
            for linha in linhas_rotulo:
                self.draw.text((self.esquerda, self.y), linha, fill=COR_TEXTO, font=self.fontes.corpo_bold)
                self.y += altura_linha
            for linha in linhas_valor:
                self.draw.text((self.esquerda, self.y), linha, fill=COR_TEXTO, font=self.fontes.corpo)
                self.y += altura_linha
            self._adicionar_espaco(12)
            return

        linhas_valor = self._quebrar_linhas(valor, self.fontes.corpo, max(self.direita - (self.esquerda + largura_prefixo), 100))
        self._garantir_espaco(max(len(linhas_valor), 1) * altura_linha + 10)
        self.draw.text((self.esquerda, self.y), prefixo, fill=COR_TEXTO, font=self.fontes.corpo_bold)
        x_valor = self.esquerda + largura_prefixo
        if linhas_valor:
            self.draw.text((x_valor, self.y), linhas_valor[0], fill=COR_TEXTO, font=self.fontes.corpo)
            for linha in linhas_valor[1:]:
                self.y += altura_linha
                self.draw.text((x_valor, self.y), linha, fill=COR_TEXTO, font=self.fontes.corpo)
        self.y += altura_linha + 12

    def _adicionar_titulo_secao(self, texto: str):
        altura = self._altura_linha(self.fontes.secao, fator=1.2)
        self._garantir_espaco(altura + 18)
        largura, _ = self._medir_texto(texto, self.fontes.secao)
        self.draw.text(((self.largura - largura) / 2, self.y), texto, fill=COR_TEXTO, font=self.fontes.secao)
        self.y += altura + 12

    def _adicionar_paragrafos(self, texto: str, *, fonte: ImageFont.ImageFont, destaque_primeira_linha: bool = False, recuo: int = 0, espaco_final: int = 8):
        x_inicio = self.esquerda + max(0, int(recuo))
        largura_disponivel = self.direita - x_inicio
        altura_linha = self._altura_linha(fonte, fator=1.5)
        paragrafos = str(texto or "").replace("\r", "").split("\n")
        for indice, paragrafo in enumerate(paragrafos):
            linhas = self._quebrar_linhas(paragrafo, fonte, largura_disponivel)
            if destaque_primeira_linha and indice == 0 and linhas:
                linhas[0] = linhas[0]
            for linha in linhas:
                self._garantir_espaco(altura_linha + 2)
                self.draw.text((x_inicio, self.y), linha, fill=COR_TEXTO, font=fonte)
                self.y += altura_linha
            if indice != len(paragrafos) - 1:
                self.y += altura_linha // 2
        self.y += max(0, int(espaco_final))

    def _fonte_run_formatado(self, run: _TextoFormatadoRun) -> ImageFont.ImageFont:
        if run.negrito and run.italico:
            return self.fontes.corpo_bold_italico
        if run.negrito:
            return self.fontes.corpo_bold
        if run.italico:
            return self.fontes.corpo_italico
        return self.fontes.corpo

    def _largura_run_formatado(self, run: _TextoFormatadoRun) -> int:
        return self._medir_texto(run.texto, self._fonte_run_formatado(run))[0]

    def _quebrar_runs_formatados(self, runs: list[_TextoFormatadoRun], largura_disponivel: int) -> list[list[_TextoFormatadoRun]]:
        linhas: list[list[_TextoFormatadoRun]] = []
        linha_atual: list[_TextoFormatadoRun] = []
        largura_atual = 0
        espaco_pendente = False

        def fechar_linha():
            nonlocal linha_atual, largura_atual
            if linha_atual:
                linhas.append(linha_atual)
            linha_atual = []
            largura_atual = 0

        for run in runs:
            for token in re.findall(r"\n|[^\S\n]+|[^\s]+", run.texto):
                if token == "\n":
                    fechar_linha()
                    espaco_pendente = False
                    continue
                if token.isspace():
                    if linha_atual:
                        espaco_pendente = True
                    continue
                texto_token = f" {token}" if espaco_pendente and linha_atual else token
                token_run = _TextoFormatadoRun(texto=texto_token, negrito=run.negrito, italico=run.italico, cor_fundo=run.cor_fundo)
                largura_token = self._largura_run_formatado(token_run)
                if linha_atual and largura_atual + largura_token > largura_disponivel:
                    fechar_linha()
                    token_run = _TextoFormatadoRun(texto=token, negrito=run.negrito, italico=run.italico, cor_fundo=run.cor_fundo)
                    largura_token = self._largura_run_formatado(token_run)
                linha_atual.append(token_run)
                largura_atual += largura_token
                espaco_pendente = False
        fechar_linha()
        return linhas

    def _adicionar_runs_formatados(self, runs: list[_TextoFormatadoRun], *, recuo: int = 0, espaco_final: int = 8):
        x_inicio = self.esquerda + max(0, int(recuo))
        largura_disponivel = self.direita - x_inicio
        altura_linha = self._altura_linha(self.fontes.corpo, fator=1.5)
        for linha in self._quebrar_runs_formatados(runs, largura_disponivel):
            self._garantir_espaco(altura_linha + 3)
            x_atual = x_inicio
            for run in linha:
                fonte = self._fonte_run_formatado(run)
                largura_run, _ = self._medir_texto(run.texto, fonte)
                if run.cor_fundo:
                    self.draw.rectangle((x_atual, self.y, x_atual + largura_run, self.y + altura_linha), fill=run.cor_fundo)
                self.draw.text((x_atual, self.y), run.texto, fill=COR_TEXTO, font=fonte)
                x_atual += largura_run
            self.y += altura_linha
        self.y += max(0, int(espaco_final))
