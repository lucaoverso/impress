from __future__ import annotations

import io
from PIL import ImageDraw

from services.ocorrencia_pdf.base_legal import _obter_itens_regimento_ocorrencia
from services.ocorrencia_pdf.constants import (
    COR_BORDA,
    COR_TEXTO,
    COR_TEXTO_MUTED,
    MARGEM_BASE,
    MARGEM_X,
    PDF_RESOLUTION_DPI,
    SECAO_DESCRICAO,
    TIPO_REGISTRO_ESTUDANTE,
    TIPO_REGISTRO_GERAL,
    TIPO_REGISTRO_PROFESSOR,
)
from services.ocorrencia_pdf.helpers import (
    _campos_resumo_registro,
    _formatar_data_hora_br,
    _obter_estudantes_vinculados_ocorrencia,
    _obter_observacao_final,
    _obter_professores_vinculados_ocorrencia,
    _texto_seguro,
)


class _RenderizadorRodapeMixin:
    def _desenhar_linha_assinatura(self, x_centro: int, y: int, largura: int, titulo: str):
        x_inicio = int(x_centro - (largura / 2))
        x_fim = int(x_centro + (largura / 2))
        self.draw.line((x_inicio, y, x_fim, y), fill=COR_BORDA, width=2)
        largura_titulo, _ = self._medir_texto(titulo, self.fontes.rodape)
        self.draw.text((x_centro - (largura_titulo / 2), y + 16), titulo, fill=COR_TEXTO, font=self.fontes.rodape)

    def _desenhar_emitido_em(self, y: int):
        emitido_em = f"Emitido em {_formatar_data_hora_br(self.ocorrencia.get('criado_em'))}"
        largura_emitido, _ = self._medir_texto(emitido_em, self.fontes.rodape_italico)
        self.draw.text(((self.largura - largura_emitido) / 2, y), emitido_em, fill=COR_TEXTO_MUTED, font=self.fontes.rodape_italico)

    def _desenhar_assinaturas_corridas(self, *, y_base: int, titulo: str, quantidade_linhas: int):
        largura_titulo, _ = self._medir_texto(titulo, self.fontes.pequeno_bold)
        self.draw.text(((self.largura - largura_titulo) / 2, y_base), titulo, fill=COR_TEXTO, font=self.fontes.pequeno_bold)
        topo_linhas = y_base + 48
        espaco_coluna = 70
        largura_total = self.direita - self.esquerda
        largura_coluna = int((largura_total - espaco_coluna) / 2)
        altura_linha = 58
        linhas_totais = max(quantidade_linhas, 4)
        for indice in range(linhas_totais):
            y_linha = topo_linhas + indice * altura_linha
            for coluna in range(2):
                x_inicio = self.esquerda + coluna * (largura_coluna + espaco_coluna)
                x_fim = x_inicio + largura_coluna
                self.draw.line((x_inicio, y_linha, x_fim, y_linha), fill=COR_BORDA, width=2)
        y_gestao = topo_linhas + (linhas_totais * altura_linha) + 46
        self._desenhar_linha_assinatura(self.centro_x - 330, y_gestao, 420, "Coordenacao Pedagogica")
        self._desenhar_linha_assinatura(self.centro_x + 330, y_gestao, 420, "Direcao")
        self._desenhar_emitido_em(y_gestao + 94)

    def _desenhar_rodape(self):
        tipo_registro = self._tipo_registro()
        if tipo_registro == TIPO_REGISTRO_GERAL:
            altura_bloco = 650
        elif tipo_registro == TIPO_REGISTRO_ESTUDANTE and len(_obter_estudantes_vinculados_ocorrencia(self.ocorrencia)) > 1:
            altura_bloco = 420
        elif tipo_registro == TIPO_REGISTRO_PROFESSOR and len(_obter_professores_vinculados_ocorrencia(self.ocorrencia)) > 1:
            altura_bloco = 420
        else:
            altura_bloco = 300

        if self.y + altura_bloco > self.altura - MARGEM_BASE:
            self._nova_pagina(continuacao=True)
        y_base = self.altura - MARGEM_BASE - altura_bloco + 24

        if tipo_registro == TIPO_REGISTRO_PROFESSOR:
            professores = _obter_professores_vinculados_ocorrencia(self.ocorrencia)
            if len(professores) > 1:
                self._desenhar_assinaturas_corridas(y_base=y_base, titulo="ASSINATURAS DOS PROFESSORES", quantidade_linhas=len(professores))
                return
            centros = [self.esquerda + ((self.direita - self.esquerda) * 0.18), self.centro_x, self.direita - ((self.direita - self.esquerda) * 0.18)]
            for centro, titulo in zip(centros, ["Professor(a)", "Coordenacao Pedagogica", "Direcao"]):
                self._desenhar_linha_assinatura(int(centro), y_base + 54, 420, titulo)
            self._desenhar_emitido_em(y_base + 142)
            return

        if tipo_registro == TIPO_REGISTRO_GERAL:
            self._desenhar_assinaturas_corridas(y_base=y_base, titulo="ASSINATURAS DOS PROFESSORES", quantidade_linhas=12)
            return

        estudantes = _obter_estudantes_vinculados_ocorrencia(self.ocorrencia)
        if len(estudantes) > 1:
            self._desenhar_assinaturas_corridas(y_base=y_base, titulo="ASSINATURAS DOS ESTUDANTES", quantidade_linhas=len(estudantes))
            return

        centros = [self.esquerda + ((self.direita - self.esquerda) * 0.18), self.centro_x, self.direita - ((self.direita - self.esquerda) * 0.18)]
        for centro, titulo in zip(centros, ["Estudante", "Coordenacao Pedagogica", "Direcao"]):
            self._desenhar_linha_assinatura(int(centro), y_base + 54, 420, titulo)
        self._desenhar_emitido_em(y_base + 142)

    def _desenhar_numeracao_paginas(self):
        total = len(self.paginas)
        for indice, pagina in enumerate(self.paginas, start=1):
            draw = ImageDraw.Draw(pagina)
            texto = f"Pagina {indice}/{total}"
            bbox = draw.textbbox((0, 0), texto, font=self.fontes.rodape)
            largura = bbox[2] - bbox[0]
            altura = bbox[3] - bbox[1]
            draw.text((self.largura - MARGEM_X - largura, self.altura - MARGEM_BASE + max(0, 40 - altura // 2)), texto, fill=COR_TEXTO_MUTED, font=self.fontes.rodape)

    def renderizar(self) -> bytes:
        tipo_registro = self._tipo_registro()
        descricao = _texto_seguro(self.ocorrencia.get("descricao"), padrao="")
        regimento_itens = _obter_itens_regimento_ocorrencia(self.ocorrencia)

        for rotulo, valor in _campos_resumo_registro(self.ocorrencia, self.turma):
            self._adicionar_rotulo_valor(rotulo, valor)
        self._adicionar_espaco(6)
        self._adicionar_titulo_secao(SECAO_DESCRICAO)
        self._adicionar_paragrafos(descricao, fonte=self.fontes.corpo)
        self._desenhar_linha()
        if tipo_registro == TIPO_REGISTRO_ESTUDANTE and regimento_itens:
            self._adicionar_secao_regimento(regimento_itens)
        elif tipo_registro == TIPO_REGISTRO_ESTUDANTE:
            self._adicionar_area_regimento_em_branco()
        if tipo_registro == TIPO_REGISTRO_ESTUDANTE:
            self._desenhar_linha()
        self._adicionar_paragrafos(_obter_observacao_final(self.ocorrencia), fonte=self.fontes.pequeno_bold)
        self._desenhar_rodape()
        self._desenhar_numeracao_paginas()

        saida = io.BytesIO()
        primeira, *restantes = self.paginas
        primeira.save(saida, format="PDF", resolution=float(PDF_RESOLUTION_DPI), save_all=True, append_images=restantes)
        return saida.getvalue()
