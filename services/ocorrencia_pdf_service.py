from __future__ import annotations

import io
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
LOGO_ESCOLA_PATH = STATIC_DIR / "img" / "logo_escola.PNG"

PDF_RESOLUTION_DPI = 300
A4_RETRATO_PIXELS_300_DPI = (2480, 3508)

COR_FUNDO = (255, 255, 255)
COR_TEXTO = (28, 32, 38)
COR_TEXTO_MUTED = (92, 99, 108)
COR_DESTAQUE = (224, 228, 233)
COR_BORDA = (123, 132, 143)

MOLDURA_INSET = 105
MARGEM_X = 205
MARGEM_TOPO = 150
MARGEM_BASE = 170
RODAPE_RESERVA = 330

NOME_ESCOLA = "ESCOLA ESTADUAL PADRE JOS\u00c9 DANIEL"
SUBTITULO_REGISTRO = "COORDENA\u00c7\u00c3O PEDAG\u00d3GICA - ASSESSORAMENTO"
TITULO_REGISTRO = "REGISTRO DE OCORR\u00caNCIAS DISCIPLINARES"
TITULO_CONTINUACAO = "CONTINUA\u00c7\u00c3O DO REGISTRO"
SECAO_DESCRICAO = "DESCRI\u00c7\u00c3O DA OCORR\u00caNCIA"
SECAO_REGIMENTO = "REGIMENTO ESCOLAR"
ALTURA_AREA_REGIMENTO = 280
ASSINATURA_RODAPE = (
    "E.E. Padre Jos\u00e9 Daniel\n"
    "Coordena\u00e7\u00e3o Pedag\u00f3gica\n"
    "Assessoria"
)

ACOES_ROTULOS = {
    "orientacao_verbal": "Orientacao verbal",
    "advertencia": "Advertencia",
    "chamada_responsavel": "Chamada de responsavel",
    "encaminhamento_direcao": "Encaminhamento a direcao",
    "registro_informativo": "Registro informativo",
}
STATUS_ROTULOS = {
    "registrado": "Registrado",
    "em_acompanhamento": "Em acompanhamento",
    "aguardando_responsavel": "Aguardando responsavel",
    "resolvido": "Resolvido",
}
OFFSET_TURNO = {
    "MATUTINO": 0,
    "INTEGRAL": 0,
    "VESPERTINO": 5,
    "VESPERTINO_EM": 5,
}

FONTES_REGULARES = (
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/calibri.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
)
FONTES_BOLD = (
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/calibrib.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
)
FONTES_ITALIC = (
    "C:/Windows/Fonts/ariali.ttf",
    "C:/Windows/Fonts/calibrii.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Italic.ttf",
)


@dataclass
class _FontPack:
    escola: ImageFont.ImageFont
    subtitulo: ImageFont.ImageFont
    titulo: ImageFont.ImageFont
    secao: ImageFont.ImageFont
    corpo: ImageFont.ImageFont
    corpo_bold: ImageFont.ImageFont
    pequeno: ImageFont.ImageFont
    pequeno_bold: ImageFont.ImageFont
    rodape: ImageFont.ImageFont
    rodape_italico: ImageFont.ImageFont


def _carregar_fonte(candidatos: tuple[str, ...], tamanho: int) -> ImageFont.ImageFont:
    for caminho in candidatos:
        if Path(caminho).exists():
            return ImageFont.truetype(caminho, tamanho)
    return ImageFont.load_default()


def _carregar_fontes() -> _FontPack:
    return _FontPack(
        escola=_carregar_fonte(FONTES_REGULARES, 58),
        subtitulo=_carregar_fonte(FONTES_REGULARES, 43),
        titulo=_carregar_fonte(FONTES_BOLD, 50),
        secao=_carregar_fonte(FONTES_BOLD, 46),
        corpo=_carregar_fonte(FONTES_REGULARES, 40),
        corpo_bold=_carregar_fonte(FONTES_BOLD, 40),
        pequeno=_carregar_fonte(FONTES_REGULARES, 34),
        pequeno_bold=_carregar_fonte(FONTES_BOLD, 34),
        rodape=_carregar_fonte(FONTES_REGULARES, 32),
        rodape_italico=_carregar_fonte(FONTES_ITALIC, 30),
    )


def _texto_seguro(valor, padrao: str = "Nao informado") -> str:
    texto = str(valor or "").strip()
    return texto or padrao


def _formatar_data_br(valor: str | None) -> str:
    texto = str(valor or "").strip()
    if not texto:
        return "Nao informada"
    try:
        return datetime.strptime(texto, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return texto


def _formatar_data_hora_br(valor: str | None) -> str:
    texto = str(valor or "").strip()
    if not texto:
        return "Nao informado"
    try:
        return datetime.strptime(texto, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y as %H:%M")
    except ValueError:
        return texto


def _rotulo_acao(valor: str | None) -> str:
    texto = str(valor or "").strip()
    return ACOES_ROTULOS.get(texto, texto or "Nao informada")


def _rotulo_status(valor: str | None) -> str:
    texto = str(valor or "").strip()
    return STATUS_ROTULOS.get(texto, texto or "Nao informado")


def _formatar_aula(ocorrencia: dict, turma: dict | None) -> str:
    texto = str(ocorrencia.get("aula") or "").strip()
    if not texto:
        return "Nao informada"
    if not texto.isdigit():
        return texto

    faixa = int(texto)
    turno = str((turma or {}).get("turno") or "").strip().upper()
    offset = OFFSET_TURNO.get(turno)
    if offset is None:
        return f"Faixa {faixa}"

    if turno == "INTEGRAL":
        if 1 <= faixa <= 5:
            return f"{faixa}a aula"
        if faixa >= 7:
            return f"{faixa - 1}a aula"
        return f"Faixa {faixa}"

    aula_turno = faixa - offset
    if aula_turno > 0:
        return f"{aula_turno}a aula"
    return f"Faixa {faixa}"


def _obter_observacao_final(ocorrencia: dict) -> str:
    acao = str(ocorrencia.get("acao_aplicada") or "").strip()
    observacoes = {
        "orientacao_verbal": (
            "OBS.: O registro fica arquivado para acompanhamento pedag\u00f3gico e "
            "orienta\u00e7\u00e3o verbal junto ao estudante."
        ),
        "advertencia": (
            "OBS.: Pela falta de integracao e compromisso e por nao acatar as "
            "solicitacoes da docente, recebe esta acao pedagogico-disciplinar de advertencia."
        ),
        "chamada_responsavel": (
            "OBS.: Solicitado o comparecimento do responsavel para alinhamento e "
            "acompanhamento conjunto do caso."
        ),
        "encaminhamento_direcao": (
            "OBS.: O registro segue encaminhado a Direcao para providencias e "
            "acompanhamento institucional."
        ),
        "registro_informativo": (
            "OBS.: Documento emitido para registro informativo e acompanhamento "
            "pedagogico interno."
        ),
    }
    return observacoes.get(
        acao,
        f"OBS.: Documento emitido para registro e acompanhamento da acao aplicada: {_rotulo_acao(acao)}."
    )


def _obter_itens_regimento_ocorrencia(ocorrencia: dict) -> list[dict]:
    itens = ocorrencia.get("regimento_itens")
    if not isinstance(itens, list):
        return []

    itens_norm = []
    for item in itens:
        if not isinstance(item, dict):
            continue
        artigo = str(item.get("artigo") or "").strip()
        descricao = str(item.get("descricao") or "").strip()
        if not artigo and not descricao:
            continue
        itens_norm.append(
            {
                "artigo": artigo or "Sem artigo",
                "descricao": descricao,
                "ordem": int(item.get("ordem") or 0),
            }
        )

    return sorted(
        itens_norm,
        key=lambda item: (item.get("ordem", 0), item.get("artigo", "")),
    )


def _carregar_logo() -> Image.Image | None:
    if not LOGO_ESCOLA_PATH.exists():
        return None

    with Image.open(LOGO_ESCOLA_PATH) as logo_origem:
        logo = ImageOps.exif_transpose(logo_origem).convert("RGBA")
        logo.thumbnail((500, 500), Image.Resampling.LANCZOS)
        return logo.copy()


class _RenderizadorRegistroOcorrencia:
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

    @property
    def limite_corpo(self) -> int:
        return self.altura - MARGEM_BASE - RODAPE_RESERVA

    def _nova_pagina(self, *, continuacao: bool):
        pagina = Image.new("RGB", A4_RETRATO_PIXELS_300_DPI, COR_FUNDO)
        draw = ImageDraw.Draw(pagina)
        draw.rectangle(
            (
                MOLDURA_INSET,
                MOLDURA_INSET,
                self.largura - MOLDURA_INSET,
                self.altura - MOLDURA_INSET,
            ),
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

    def _desenhar_texto_centralizado(
        self,
        texto: str,
        fonte: ImageFont.ImageFont,
        y: int,
        *,
        fill=COR_TEXTO,
    ) -> int:
        largura, altura = self._medir_texto(texto, fonte)
        self.draw.text(((self.largura - largura) / 2, y), texto, fill=fill, font=fonte)
        return altura

    def _desenhar_titulo_destacado(self, texto: str, y: int) -> int:
        largura, altura = self._medir_texto(texto, self.fontes.titulo)
        padding_x = 24
        padding_y = 14
        x = (self.largura - largura) / 2 - padding_x
        self.draw.rectangle(
            (x, y, x + largura + padding_x * 2, y + altura + padding_y * 2),
            fill=COR_DESTAQUE,
        )
        self.draw.text(
            ((self.largura - largura) / 2, y + padding_y),
            texto,
            fill=COR_TEXTO,
            font=self.fontes.titulo,
        )
        return altura + padding_y * 2

    def _desenhar_cabecalho(self, *, continuacao: bool) -> int:
        y = MARGEM_TOPO
        y += self._desenhar_texto_centralizado(
            NOME_ESCOLA,
            self.fontes.escola,
            y,
            fill=(52, 57, 64),
        )
        y += 18

        if self.logo is not None:
            logo_x = self.centro_x - (self.logo.width // 2)
            if self.logo.mode == "RGBA":
                self.pagina_atual.paste(self.logo, (logo_x, y), self.logo)
            else:
                self.pagina_atual.paste(self.logo, (logo_x, y))
            y += self.logo.height + 24

        if continuacao:
            y += self._desenhar_texto_centralizado(
                TITULO_CONTINUACAO,
                self.fontes.pequeno_bold,
                y,
                fill=COR_TEXTO_MUTED,
            )
            y += 14

        y += self._desenhar_texto_centralizado(
            SUBTITULO_REGISTRO,
            self.fontes.subtitulo,
            y,
        )
        y += 8
        y += self._desenhar_titulo_destacado(TITULO_REGISTRO, y)
        return y + 34

    def _quebrar_linhas(
        self,
        texto: str,
        fonte: ImageFont.ImageFont,
        largura_max: int,
    ) -> list[str]:
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
                largura, _ = self._medir_texto(candidata, fonte)
                if largura <= largura_max:
                    atual = candidata
                    continue

                if atual:
                    linhas.append(atual)
                    atual = palavra
                    continue

                fragmento = ""
                for caractere in palavra:
                    candidato_fragmento = f"{fragmento}{caractere}"
                    largura_fragmento, _ = self._medir_texto(candidato_fragmento, fonte)
                    if largura_fragmento <= largura_max:
                        fragmento = candidato_fragmento
                        continue
                    linhas.append(fragmento)
                    fragmento = caractere
                atual = fragmento

            if atual:
                linhas.append(atual)
        return linhas or [""]

    def _garantir_espaco(self, altura_necessaria: int):
        if self.y + altura_necessaria <= self.limite_corpo:
            return
        self._nova_pagina(continuacao=True)

    def _adicionar_espaco(self, valor: int):
        self.y += valor

    def _desenhar_linha(self):
        self._garantir_espaco(16)
        self.draw.line(
            (self.esquerda, self.y, self.direita, self.y),
            fill=COR_BORDA,
            width=2,
        )
        self.y += 24

    def _adicionar_area_regimento_em_branco(self):
        altura_titulo = self._altura_linha(self.fontes.pequeno_bold, fator=1.1)
        altura_total = altura_titulo + 18 + ALTURA_AREA_REGIMENTO + 18
        self._garantir_espaco(altura_total)

        largura_titulo, _ = self._medir_texto(SECAO_REGIMENTO, self.fontes.pequeno_bold)
        self.draw.text(
            ((self.largura - largura_titulo) / 2, self.y),
            SECAO_REGIMENTO,
            fill=COR_TEXTO,
            font=self.fontes.pequeno_bold,
        )
        self.y += altura_titulo + 18

        self.draw.rectangle(
            (self.esquerda, self.y, self.direita, self.y + ALTURA_AREA_REGIMENTO),
            outline=COR_BORDA,
            width=2,
        )
        self.y += ALTURA_AREA_REGIMENTO + 18

    def _adicionar_secao_regimento(self, itens: list[dict]):
        self._adicionar_titulo_secao(SECAO_REGIMENTO)
        for indice, item in enumerate(itens):
            artigo = str(item.get("artigo") or "").strip() or "Sem artigo"
            descricao = str(item.get("descricao") or "").strip()
            self._adicionar_paragrafos(artigo, fonte=self.fontes.pequeno_bold)
            if descricao:
                self._adicionar_paragrafos(descricao, fonte=self.fontes.pequeno)
            if indice != len(itens) - 1:
                self._adicionar_espaco(10)

    def _adicionar_rotulo_valor(self, rotulo: str, valor: str):
        prefixo = f"{rotulo}: "
        largura_prefixo, _ = self._medir_texto(prefixo, self.fontes.corpo_bold)
        largura_disponivel = self.direita - self.esquerda
        altura_linha = self._altura_linha(self.fontes.corpo)

        if largura_prefixo > largura_disponivel * 0.52:
            linhas_rotulo = self._quebrar_linhas(rotulo, self.fontes.corpo_bold, largura_disponivel)
            linhas_valor = self._quebrar_linhas(valor, self.fontes.corpo, largura_disponivel)
            altura_total = (len(linhas_rotulo) + len(linhas_valor)) * altura_linha + 12
            self._garantir_espaco(altura_total)
            for linha in linhas_rotulo:
                self.draw.text((self.esquerda, self.y), linha, fill=COR_TEXTO, font=self.fontes.corpo_bold)
                self.y += altura_linha
            for linha in linhas_valor:
                self.draw.text((self.esquerda, self.y), linha, fill=COR_TEXTO, font=self.fontes.corpo)
                self.y += altura_linha
            self._adicionar_espaco(10)
            return

        linhas_valor = self._quebrar_linhas(
            valor,
            self.fontes.corpo,
            max(self.direita - (self.esquerda + largura_prefixo), 100),
        )
        altura_total = max(len(linhas_valor), 1) * altura_linha + 10
        self._garantir_espaco(altura_total)
        self.draw.text((self.esquerda, self.y), prefixo, fill=COR_TEXTO, font=self.fontes.corpo_bold)

        x_valor = self.esquerda + largura_prefixo
        if linhas_valor:
            self.draw.text((x_valor, self.y), linhas_valor[0], fill=COR_TEXTO, font=self.fontes.corpo)
            for linha in linhas_valor[1:]:
                self.y += altura_linha
                self.draw.text((x_valor, self.y), linha, fill=COR_TEXTO, font=self.fontes.corpo)
        self.y += altura_linha + 10

    def _adicionar_titulo_secao(self, texto: str):
        altura = self._altura_linha(self.fontes.secao, fator=1.1)
        self._garantir_espaco(altura + 14)
        largura, _ = self._medir_texto(texto, self.fontes.secao)
        self.draw.text(
            ((self.largura - largura) / 2, self.y),
            texto,
            fill=COR_TEXTO,
            font=self.fontes.secao,
        )
        self.y += altura + 8

    def _adicionar_paragrafos(
        self,
        texto: str,
        *,
        fonte: ImageFont.ImageFont,
        destaque_primeira_linha: bool = False,
    ):
        largura_disponivel = self.direita - self.esquerda
        altura_linha = self._altura_linha(fonte)
        paragrafos = str(texto or "").replace("\r", "").split("\n")

        for indice, paragrafo in enumerate(paragrafos):
            linhas = self._quebrar_linhas(paragrafo, fonte, largura_disponivel)
            if destaque_primeira_linha and indice == 0 and linhas:
                linhas[0] = linhas[0]

            for linha in linhas:
                self._garantir_espaco(altura_linha + 2)
                self.draw.text((self.esquerda, self.y), linha, fill=COR_TEXTO, font=fonte)
                self.y += altura_linha

            if indice != len(paragrafos) - 1:
                self.y += altura_linha // 3

        self.y += 8

    def _desenhar_rodape(self):
        altura_bloco = 220
        if self.y + altura_bloco > self.altura - MARGEM_BASE:
            self._nova_pagina(continuacao=True)

        y_base = self.altura - MARGEM_BASE - 170
        largura_linha = 560
        self.draw.line(
            (
                self.centro_x - (largura_linha // 2),
                y_base,
                self.centro_x + (largura_linha // 2),
                y_base,
            ),
            fill=COR_BORDA,
            width=2,
        )

        linhas = ASSINATURA_RODAPE.split("\n")
        altura_linha = self._altura_linha(self.fontes.rodape, fator=1.15)
        y = y_base + 18
        for linha in linhas:
            largura, _ = self._medir_texto(linha, self.fontes.rodape)
            self.draw.text(
                ((self.largura - largura) / 2, y),
                linha,
                fill=COR_TEXTO,
                font=self.fontes.rodape,
            )
            y += altura_linha

        emitido_em = f"Emitido em {_formatar_data_hora_br(self.ocorrencia.get('criado_em'))}"
        largura_emitido, _ = self._medir_texto(emitido_em, self.fontes.rodape_italico)
        self.draw.text(
            ((self.largura - largura_emitido) / 2, y + 8),
            emitido_em,
            fill=COR_TEXTO_MUTED,
            font=self.fontes.rodape_italico,
        )

    def _desenhar_numeracao_paginas(self):
        total = len(self.paginas)
        for indice, pagina in enumerate(self.paginas, start=1):
            draw = ImageDraw.Draw(pagina)
            texto = f"Pagina {indice}/{total}"
            bbox = draw.textbbox((0, 0), texto, font=self.fontes.rodape)
            largura = bbox[2] - bbox[0]
            altura = bbox[3] - bbox[1]
            draw.text(
                (
                    self.largura - MARGEM_X - largura,
                    self.altura - MARGEM_BASE + max(0, 40 - altura // 2),
                ),
                texto,
                fill=COR_TEXTO_MUTED,
                font=self.fontes.rodape,
            )

    def renderizar(self) -> bytes:
        estudante = _texto_seguro(self.ocorrencia.get("nome_estudante"))
        turma = _texto_seguro(self.ocorrencia.get("turma_nome"))
        professor = _texto_seguro(self.ocorrencia.get("professor_requerente"))
        disciplina = _texto_seguro(self.ocorrencia.get("disciplina"))
        data = _formatar_data_br(self.ocorrencia.get("data_ocorrencia"))
        aula = _formatar_aula(self.ocorrencia, self.turma)
        horario = _texto_seguro(self.ocorrencia.get("horario_ocorrencia"))
        acao = _rotulo_acao(self.ocorrencia.get("acao_aplicada"))
        status = _rotulo_status(self.ocorrencia.get("status"))
        descricao = _texto_seguro(self.ocorrencia.get("descricao"), padrao="")
        regimento_itens = _obter_itens_regimento_ocorrencia(self.ocorrencia)

        self._adicionar_rotulo_valor("Estudante(s)", estudante)
        self._adicionar_rotulo_valor("Turma", turma)
        self._adicionar_rotulo_valor("Professor requerente", professor)
        self._adicionar_rotulo_valor("Disciplina ou funcao", disciplina)
        self._adicionar_rotulo_valor("Data", data)
        self._adicionar_rotulo_valor("Aula", aula)
        self._adicionar_rotulo_valor("Horario", f"As {horario} h" if horario != "Nao informado" else horario)
        self._adicionar_rotulo_valor("Acao aplicada", acao)
        self._adicionar_rotulo_valor("Status", status)

        self._adicionar_espaco(6)
        self._adicionar_titulo_secao(SECAO_DESCRICAO)
        self._adicionar_paragrafos(descricao, fonte=self.fontes.corpo)
        self._desenhar_linha()
        if regimento_itens:
            self._adicionar_secao_regimento(regimento_itens)
        else:
            self._adicionar_area_regimento_em_branco()
        self._desenhar_linha()

        self._adicionar_paragrafos(_obter_observacao_final(self.ocorrencia), fonte=self.fontes.pequeno_bold)
        self._desenhar_rodape()
        self._desenhar_numeracao_paginas()

        saida = io.BytesIO()
        primeira, *restantes = self.paginas
        primeira.save(
            saida,
            format="PDF",
            resolution=float(PDF_RESOLUTION_DPI),
            save_all=True,
            append_images=restantes,
        )
        return saida.getvalue()


def gerar_pdf_ocorrencia_registro(ocorrencia: dict, *, turma: dict | None = None) -> bytes:
    renderizador = _RenderizadorRegistroOcorrencia(ocorrencia, turma=turma)
    return renderizador.renderizar()
