from __future__ import annotations

import io
import re
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps
from services.ocorrencia_disciplina_service import (
    inferir_gravidade_ocorrencia,
    rotulo_acao_ocorrencia,
    rotulo_gravidade_ocorrencia,
)

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
SUBTITULO_REGISTRO = "COORDENA\u00c7\u00c3O PEDAG\u00d3GICA - CENTRAL DE REGISTROS"
TITULO_REGISTRO = "REGISTRO DISCIPLINAR DO ESTUDANTE"
TITULO_CONTINUACAO = "CONTINUA\u00c7\u00c3O DO REGISTRO"
SECAO_DESCRICAO = "DESCRI\u00c7\u00c3O DA OCORR\u00caNCIA"
SECAO_REGIMENTO = "BASE LEGAL"
ALTURA_AREA_REGIMENTO = 280
TIPO_REGISTRO_ESTUDANTE = "estudante"
TIPO_REGISTRO_PROFESSOR = "professor"
TIPO_REGISTRO_GERAL = "geral"

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
FONTES_BOLD_ITALIC = (
    "C:/Windows/Fonts/arialbi.ttf",
    "C:/Windows/Fonts/calibriz.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-BoldItalic.ttf",
)


@dataclass
class _FontPack:
    escola: ImageFont.ImageFont
    subtitulo: ImageFont.ImageFont
    titulo: ImageFont.ImageFont
    secao: ImageFont.ImageFont
    corpo: ImageFont.ImageFont
    corpo_bold: ImageFont.ImageFont
    corpo_italico: ImageFont.ImageFont
    corpo_bold_italico: ImageFont.ImageFont
    pequeno: ImageFont.ImageFont
    pequeno_bold: ImageFont.ImageFont
    rodape: ImageFont.ImageFont
    rodape_italico: ImageFont.ImageFont


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
        corpo_italico=_carregar_fonte(FONTES_ITALIC, 40),
        corpo_bold_italico=_carregar_fonte(FONTES_BOLD_ITALIC, 40),
        pequeno=_carregar_fonte(FONTES_REGULARES, 34),
        pequeno_bold=_carregar_fonte(FONTES_BOLD, 34),
        rodape=_carregar_fonte(FONTES_REGULARES, 32),
        rodape_italico=_carregar_fonte(FONTES_ITALIC, 30),
    )


def _texto_seguro(valor, padrao: str = "Nao informado") -> str:
    texto = str(valor or "").strip()
    return texto or padrao


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
        if not separador:
            continue
        if propriedade.strip().lower() == "background-color":
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
        proximo = _EstiloTextoFormatado(
            negrito=alteracoes.get("negrito", atual.negrito),
            italico=alteracoes.get("italico", atual.italico),
            cor_fundo=alteracoes.get("cor_fundo", atual.cor_fundo),
        )
        self.estilos.append(proximo)

    def _desempilhar_estilo(self):
        if len(self.estilos) > 1:
            self.estilos.pop()

    def handle_starttag(self, tag: str, attrs):
        tag_norm = tag.lower()
        attrs_dict = {str(nome).lower(): str(valor or "") for nome, valor in attrs}

        if tag_norm in {"p", "div"}:
            self._adicionar_quebra()
            return
        if tag_norm == "br":
            self._adicionar_quebra()
            return
        if tag_norm in {"b", "strong"}:
            self._empilhar_estilo(negrito=True)
            return
        if tag_norm in {"i", "em"}:
            self._empilhar_estilo(italico=True)
            return
        if tag_norm == "mark":
            self._empilhar_estilo(
                cor_fundo=_extrair_cor_fundo_descricao(attrs_dict.get("style")) or (255, 243, 163)
            )
            return
        if tag_norm == "span":
            cor_fundo = _extrair_cor_fundo_descricao(attrs_dict.get("style"))
            if cor_fundo:
                self._empilhar_estilo(cor_fundo=cor_fundo)

    def handle_endtag(self, tag: str):
        tag_norm = tag.lower()
        if tag_norm in {"b", "strong", "i", "em", "mark", "span"}:
            self._desempilhar_estilo()
            return
        if tag_norm in {"p", "div"}:
            self._adicionar_quebra()

    def handle_data(self, data: str):
        self._adicionar_texto(data)


def _obter_runs_descricao_formatada(html: str | None) -> list[_TextoFormatadoRun]:
    parser = _DescricaoFormatadaParser()
    parser.feed(str(html or ""))
    parser.close()
    return [run for run in parser.runs if run.texto]


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
    return rotulo_acao_ocorrencia(valor)


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


def _obter_tipo_registro(ocorrencia: dict) -> str:
    tipo = str(ocorrencia.get("tipo_registro") or "").strip().lower()
    if tipo in {TIPO_REGISTRO_ESTUDANTE, TIPO_REGISTRO_PROFESSOR, TIPO_REGISTRO_GERAL}:
        return tipo
    return TIPO_REGISTRO_ESTUDANTE


def _obter_observacao_final(ocorrencia: dict) -> str:
    acao = str(ocorrencia.get("acao_aplicada") or "").strip()
    tipo_registro = _obter_tipo_registro(ocorrencia)
    observacoes = {
        "advertencia_verbal": (
            "OBS.: Aplicada advertência verbal com orientação pedagógica, conforme a base legal selecionada."
        ),
        "retirada_sala_orientacao": (
            "OBS.: Aplicada retirada do estudante da sala ou atividade, com encaminhamento para orientação."
        ),
        "suspensao_extracurricular": (
            "OBS.: Aplicada suspensão temporária de participação em programas extracurriculares."
        ),
        "suspensao_orientada_2_dias": (
            "OBS.: Aplicada suspensão orientada das aulas pelo período definido pela equipe escolar."
        ),
        "suspensao_aulas_3_dias": (
            "OBS.: Aplicada suspensão das aulas, respeitado o limite previsto na base legal."
        ),
        "transferencia_compulsoria": (
            "OBS.: Aplicada transferência compulsória, conforme decisão institucional cabível ao caso."
        ),
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
            "OBS.: Documento emitido para registro informativo e acompanhamento pedagogico interno."
        ),
        "orientacao_professor": (
            "OBS.: Registro emitido para documentar a orientacao individual feita ao professor, com ciencia formal das partes."
        ),
        "reuniao_alinhamento": (
            "OBS.: Registro emitido para documentar reuniao de alinhamento e pactuacao institucional com o professor."
        ),
        "orientacao_geral_docentes": (
            "OBS.: Registro emitido para documentar orientacao geral apresentada ao corpo docente, com coleta de assinaturas ao final."
        ),
    }
    if acao in observacoes:
        return observacoes[acao]
    if tipo_registro == TIPO_REGISTRO_PROFESSOR:
        return "OBS.: Documento emitido para registro funcional e acompanhamento da orientacao ao professor."
    if tipo_registro == TIPO_REGISTRO_GERAL:
        return "OBS.: Documento emitido para registro institucional de orientacao geral ao corpo docente."
    return observacoes.get(
        acao,
        f"OBS.: Documento emitido para registro e acompanhamento da acao aplicada: {_rotulo_acao(acao)}.",
    )


def _obter_gravidade_ocorrencia(ocorrencia: dict) -> str | None:
    if _obter_tipo_registro(ocorrencia) != TIPO_REGISTRO_ESTUDANTE:
        return None
    return inferir_gravidade_ocorrencia(_obter_itens_regimento_ocorrencia(ocorrencia))


def _obter_titulo_documento(ocorrencia: dict) -> str:
    acao = str(ocorrencia.get("acao_aplicada") or "").strip()
    if not acao:
        tipo_registro = _obter_tipo_registro(ocorrencia)
        if tipo_registro == TIPO_REGISTRO_PROFESSOR:
            return "REGISTRO INDIVIDUAL DE PROFESSOR"
        if tipo_registro == TIPO_REGISTRO_GERAL:
            return "REGISTRO GERAL AOS PROFESSORES"
        return TITULO_REGISTRO
    return _rotulo_acao(acao).upper()


def _obter_itens_regimento_ocorrencia(ocorrencia: dict) -> list[dict]:
    itens = ocorrencia.get("regimento_itens")
    if not isinstance(itens, list):
        return []

    regex_artigo = re.compile(r"Art\.?\s*([^\s,;:-]+(?:[-A-Za-z0-9.]+)?)", re.IGNORECASE)
    regex_inciso = re.compile(r"(?:inciso\s+([IVXLCDM]+)|-\s*([IVXLCDM]+)\b)", re.IGNORECASE)
    regex_alinea = re.compile(r"alinea\s+([a-z])\b", re.IGNORECASE)

    itens_norm = []
    for item in itens:
        if not isinstance(item, dict):
            continue
        artigo = str(item.get("artigo") or "").strip()
        descricao = str(item.get("descricao") or "").strip()
        if not artigo and not descricao:
            continue

        lei_nome = str(item.get("lei_nome") or "").strip()
        artigo_numero = str(item.get("artigo_numero") or "").strip()
        artigo_descricao = str(item.get("artigo_descricao") or "").strip()
        inciso_numero = str(item.get("inciso_numero") or "").strip()
        inciso_descricao = str(item.get("inciso_descricao") or "").strip()
        alinea_identificador = str(item.get("alinea_identificador") or "").strip()
        alinea_descricao = str(item.get("alinea_descricao") or "").strip()

        if not lei_nome and " - Art." in artigo:
            lei_nome = artigo.split(" - Art.", 1)[0].strip()

        if not artigo_numero:
            match_artigo = regex_artigo.search(artigo)
            if match_artigo:
                artigo_numero = str(match_artigo.group(1) or "").strip()
        if not inciso_numero:
            match_inciso = regex_inciso.search(artigo)
            if match_inciso:
                inciso_numero = str(match_inciso.group(1) or match_inciso.group(2) or "").strip()
        if not alinea_identificador:
            match_alinea = regex_alinea.search(artigo)
            if match_alinea:
                alinea_identificador = str(match_alinea.group(1) or "").strip()

        tipo = str(item.get("tipo") or "").strip().lower()
        if not tipo:
            if alinea_identificador or item.get("alinea_id") is not None:
                tipo = "alinea"
            elif inciso_numero or item.get("inciso_id") is not None:
                tipo = "inciso"
            else:
                tipo = "artigo"

        if tipo == "artigo" and not artigo_descricao:
            artigo_descricao = descricao
        if tipo == "inciso" and not inciso_descricao:
            inciso_descricao = descricao
        if tipo == "alinea" and not alinea_descricao:
            alinea_descricao = descricao

        itens_norm.append(
            {
                "tipo": tipo,
                "artigo_id": int(item["artigo_id"]) if item.get("artigo_id") is not None else None,
                "inciso_id": int(item["inciso_id"]) if item.get("inciso_id") is not None else None,
                "alinea_id": int(item["alinea_id"]) if item.get("alinea_id") is not None else None,
                "lei_nome": lei_nome or None,
                "artigo_numero": artigo_numero or None,
                "artigo_descricao": artigo_descricao or None,
                "inciso_numero": inciso_numero or None,
                "inciso_descricao": inciso_descricao or None,
                "alinea_identificador": alinea_identificador or None,
                "alinea_descricao": alinea_descricao or None,
                "artigo": artigo or "Sem artigo",
                "descricao": descricao,
                "ordem": int(item.get("ordem") or 0),
            }
        )

    return sorted(
        itens_norm,
        key=lambda item: (item.get("ordem", 0), item.get("artigo", "")),
    )


def _obter_estudantes_vinculados_ocorrencia(ocorrencia: dict) -> list[dict]:
    itens = ocorrencia.get("estudantes_vinculados")
    if not isinstance(itens, list):
        return []

    vinculados = []
    for item in itens:
        if not isinstance(item, dict):
            continue
        nome = str(item.get("nome") or "").strip()
        if not nome:
            continue
        vinculados.append(
            {
                "estudante_id": item.get("estudante_id"),
                "nome": nome,
                "turma_id": item.get("turma_id"),
                "turma_nome": str(item.get("turma_nome") or "").strip(),
            }
        )
    return vinculados


def _obter_professores_vinculados_ocorrencia(ocorrencia: dict) -> list[dict]:
    itens = ocorrencia.get("professores_vinculados")
    if not isinstance(itens, list):
        return []

    vinculados = []
    for item in itens:
        if not isinstance(item, dict):
            continue
        nome = str(item.get("nome") or "").strip()
        if not nome:
            continue
        vinculados.append(
            {
                "professor_id": item.get("professor_id"),
                "nome": nome,
                "email": str(item.get("email") or "").strip(),
            }
        )
    return vinculados


def _formatar_linha_artigo(
    numero: str | None, descricao: str | None, rotulo_legado: str | None = None
) -> str:
    numero_limpo = re.sub(r"^art\.?\s*", "", str(numero or "").strip(), flags=re.IGNORECASE)
    descricao_limpa = str(descricao or "").strip()
    if numero_limpo:
        prefixo = f"Art. {numero_limpo}."
        return f"{prefixo} {descricao_limpa}".strip() if descricao_limpa else prefixo
    return str(rotulo_legado or descricao_limpa or "Sem artigo").strip() or "Sem artigo"


def _formatar_linha_inciso(numero: str | None, descricao: str | None) -> str:
    numero_limpo = str(numero or "").strip()
    descricao_limpa = str(descricao or "").strip()
    if numero_limpo and descricao_limpa:
        return f"{numero_limpo} - {descricao_limpa}"
    return numero_limpo or descricao_limpa


def _formatar_linha_alinea(identificador: str | None, descricao: str | None) -> str:
    identificador_limpo = str(identificador or "").strip()
    descricao_limpa = str(descricao or "").strip()
    if identificador_limpo and descricao_limpa:
        return f"{identificador_limpo}) {descricao_limpa}"
    return identificador_limpo or descricao_limpa


def _normalizar_texto_chave(valor: str | None) -> str:
    return re.sub(r"\s+", " ", str(valor or "").strip()).casefold()


def _limpar_rotulo_artigo_legado(rotulo: str | None) -> str:
    texto = str(rotulo or "").strip()
    if not texto:
        return ""
    if " - Art." in texto:
        texto = f"Art.{texto.split(' - Art.', 1)[1]}"
    texto = re.sub(r",?\s*alinea\s+[a-z]\b.*$", "", texto, flags=re.IGNORECASE)
    texto = re.sub(r",?\s*inciso\s+[IVXLCDM]+\b.*$", "", texto, flags=re.IGNORECASE)
    texto = re.sub(r"\s*-\s*[IVXLCDM]+\b.*$", "", texto, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", texto).strip(" ,;-")


def _montar_chave_artigo(item: dict, chave_lei: str, ordem: int) -> str | int:
    artigo_id = item.get("artigo_id")
    if artigo_id is not None and int(artigo_id) > 0:
        return int(artigo_id)

    artigo_numero = _normalizar_texto_chave(item.get("artigo_numero"))
    if artigo_numero:
        return f"{chave_lei}|artigo|{artigo_numero}"

    rotulo_legado = _normalizar_texto_chave(_limpar_rotulo_artigo_legado(item.get("artigo")))
    if rotulo_legado:
        return f"{chave_lei}|artigo-legado|{rotulo_legado}"

    return f"{chave_lei}|artigo-ordem|{ordem}"


def _montar_chave_inciso(item: dict, chave_artigo: str | int, ordem: int) -> str | int:
    inciso_id = item.get("inciso_id")
    if inciso_id is not None and int(inciso_id) > 0:
        return int(inciso_id)

    inciso_numero = _normalizar_texto_chave(item.get("inciso_numero"))
    if inciso_numero:
        return f"{chave_artigo}|inciso|{inciso_numero}"

    return f"{chave_artigo}|inciso-ordem|{ordem}"


def _montar_chave_alinea(item: dict, chave_inciso: str | int, ordem: int) -> str | int:
    alinea_id = item.get("alinea_id")
    if alinea_id is not None and int(alinea_id) > 0:
        return int(alinea_id)

    alinea_identificador = _normalizar_texto_chave(item.get("alinea_identificador"))
    if alinea_identificador:
        return f"{chave_inciso}|alinea|{alinea_identificador}"

    return f"{chave_inciso}|alinea-ordem|{ordem}"


def _montar_blocos_base_legal(itens: list[dict]) -> list[dict]:
    if not itens:
        return []

    itens = _obter_itens_regimento_ocorrencia({"regimento_itens": itens})
    if not itens:
        return []

    leis: dict[str, dict] = {}
    for item in itens:
        lei_nome = str(item.get("lei_nome") or "").strip()
        artigo_numero = str(item.get("artigo_numero") or "").strip()
        artigo_descricao = str(item.get("artigo_descricao") or "").strip()
        inciso_numero = str(item.get("inciso_numero") or "").strip()
        inciso_descricao = str(item.get("inciso_descricao") or "").strip()
        alinea_identificador = str(item.get("alinea_identificador") or "").strip()
        alinea_descricao = str(item.get("alinea_descricao") or "").strip()
        ordem = int(item.get("ordem") or 0)
        tipo = str(item.get("tipo") or "").strip().lower() or "artigo"

        chave_lei = lei_nome or "__sem_lei__"
        lei = leis.setdefault(
            chave_lei,
            {
                "nome": lei_nome,
                "ordem": ordem,
                "artigos": {},
            },
        )
        lei["ordem"] = min(int(lei.get("ordem") or ordem), ordem)

        chave_artigo = _montar_chave_artigo(item, chave_lei, ordem)
        artigo = lei["artigos"].setdefault(
            chave_artigo,
            {
                "ordem": ordem,
                "numero": artigo_numero,
                "descricao": artigo_descricao,
                "rotulo_legado": str(item.get("artigo") or "").strip(),
                "incisos": {},
            },
        )
        artigo["ordem"] = min(int(artigo.get("ordem") or ordem), ordem)
        if artigo_numero and not artigo.get("numero"):
            artigo["numero"] = artigo_numero
        if artigo_descricao and not artigo.get("descricao"):
            artigo["descricao"] = artigo_descricao
        if str(item.get("artigo") or "").strip() and not artigo.get("rotulo_legado"):
            artigo["rotulo_legado"] = str(item.get("artigo") or "").strip()

        if tipo == "artigo" and not inciso_numero and not alinea_identificador:
            continue

        chave_inciso = _montar_chave_inciso(item, chave_artigo, ordem)
        inciso = artigo["incisos"].setdefault(
            chave_inciso,
            {
                "ordem": ordem,
                "numero": inciso_numero,
                "descricao": inciso_descricao,
                "alineas": {},
            },
        )
        inciso["ordem"] = min(int(inciso.get("ordem") or ordem), ordem)
        if inciso_numero and not inciso.get("numero"):
            inciso["numero"] = inciso_numero
        if inciso_descricao and not inciso.get("descricao"):
            inciso["descricao"] = inciso_descricao

        if tipo != "alinea" and not alinea_identificador:
            continue

        chave_alinea = _montar_chave_alinea(item, chave_inciso, ordem)
        alinea = inciso["alineas"].setdefault(
            chave_alinea,
            {
                "ordem": ordem,
                "identificador": alinea_identificador,
                "descricao": alinea_descricao,
            },
        )
        alinea["ordem"] = min(int(alinea.get("ordem") or ordem), ordem)
        if alinea_identificador and not alinea.get("identificador"):
            alinea["identificador"] = alinea_identificador
        if alinea_descricao and not alinea.get("descricao"):
            alinea["descricao"] = alinea_descricao

    blocos: list[dict] = []
    leis_ordenadas = sorted(
        leis.values(),
        key=lambda lei: (int(lei.get("ordem") or 0), str(lei.get("nome") or "").lower()),
    )
    total_leis_nomeadas = len([lei for lei in leis_ordenadas if str(lei.get("nome") or "").strip()])
    mostrar_lei = total_leis_nomeadas > 1

    for lei in leis_ordenadas:
        nome_lei = str(lei.get("nome") or "").strip()
        if mostrar_lei and nome_lei:
            blocos.append({"tipo": "lei", "texto": nome_lei})

        artigos_ordenados = sorted(
            lei["artigos"].values(),
            key=lambda artigo: (int(artigo.get("ordem") or 0), str(artigo.get("numero") or "")),
        )
        for artigo in artigos_ordenados:
            blocos.append(
                {
                    "tipo": "artigo",
                    "texto": _formatar_linha_artigo(
                        artigo.get("numero"),
                        artigo.get("descricao"),
                        artigo.get("rotulo_legado"),
                    ),
                }
            )

            incisos_ordenados = sorted(
                artigo["incisos"].values(),
                key=lambda inciso: (int(inciso.get("ordem") or 0), str(inciso.get("numero") or "")),
            )
            for inciso in incisos_ordenados:
                texto_inciso = _formatar_linha_inciso(inciso.get("numero"), inciso.get("descricao"))
                if texto_inciso:
                    blocos.append({"tipo": "inciso", "texto": texto_inciso})

                alineas_ordenadas = sorted(
                    inciso["alineas"].values(),
                    key=lambda alinea: (
                        int(alinea.get("ordem") or 0),
                        str(alinea.get("identificador") or ""),
                    ),
                )
                for alinea in alineas_ordenadas:
                    texto_alinea = _formatar_linha_alinea(
                        alinea.get("identificador"),
                        alinea.get("descricao"),
                    )
                    if texto_alinea:
                        blocos.append({"tipo": "alinea", "texto": texto_alinea})

    return blocos


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

    def _reserva_rodape(self) -> int:
        tipo_registro = _obter_tipo_registro(self.ocorrencia)
        participantes_estudantes = _obter_estudantes_vinculados_ocorrencia(self.ocorrencia)
        participantes_professores = _obter_professores_vinculados_ocorrencia(self.ocorrencia)
        if tipo_registro == TIPO_REGISTRO_GERAL:
            return 780
        if tipo_registro == TIPO_REGISTRO_ESTUDANTE and len(participantes_estudantes) > 1:
            return 520
        if tipo_registro == TIPO_REGISTRO_PROFESSOR and len(participantes_professores) > 1:
            return 520
        if tipo_registro == TIPO_REGISTRO_PROFESSOR:
            return 430
        if tipo_registro == TIPO_REGISTRO_ESTUDANTE:
            return 430
        return RODAPE_RESERVA

    @property
    def limite_corpo(self) -> int:
        return self.altura - MARGEM_BASE - self._reserva_rodape()

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
        padding_x = 24
        padding_y = 14
        largura_max = max(200, self.largura - (MARGEM_X * 2) - padding_x * 2)
        linhas = self._quebrar_linhas(texto, self.fontes.titulo, largura_max)
        altura_linha = self._altura_linha(self.fontes.titulo, fator=1.08)
        largura_bloco = max(self._medir_texto(linha, self.fontes.titulo)[0] for linha in linhas)
        altura_bloco = max(len(linhas), 1) * altura_linha
        x = (self.largura - largura_bloco) / 2 - padding_x
        self.draw.rectangle(
            (x, y, x + largura_bloco + padding_x * 2, y + altura_bloco + padding_y * 2),
            fill=COR_DESTAQUE,
        )
        cursor_y = y + padding_y
        for linha in linhas:
            largura_linha, _ = self._medir_texto(linha, self.fontes.titulo)
            self.draw.text(
                ((self.largura - largura_linha) / 2, cursor_y),
                linha,
                fill=COR_TEXTO,
                font=self.fontes.titulo,
            )
            cursor_y += altura_linha
        return altura_bloco + padding_y * 2

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
        y += self._desenhar_titulo_destacado(_obter_titulo_documento(self.ocorrencia), y)

        gravidade = _obter_gravidade_ocorrencia(self.ocorrencia)
        texto_gravidade = f"Gravidade: {rotulo_gravidade_ocorrencia(gravidade)}"
        y += 12
        y += self._desenhar_texto_centralizado(
            texto_gravidade,
            self.fontes.pequeno_bold,
            y,
            fill=COR_TEXTO_MUTED,
        )
        return y + 28

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
                self._adicionar_paragrafos(
                    texto, fonte=self.fontes.pequeno, recuo=36, espaco_final=2
                )
            elif tipo == "alinea":
                self._adicionar_paragrafos(
                    texto, fonte=self.fontes.pequeno, recuo=74, espaco_final=2
                )
            else:
                self._adicionar_paragrafos(texto, fonte=self.fontes.pequeno, espaco_final=2)

            proximo_tipo = (
                str(blocos[indice + 1].get("tipo") or "").strip().lower()
                if indice < len(blocos) - 1
                else ""
            )
            if tipo == "alinea" and proximo_tipo != "alinea":
                self._adicionar_espaco(4)
            if tipo == "inciso" and proximo_tipo not in {"alinea", "inciso"}:
                self._adicionar_espaco(4)

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
                self.draw.text(
                    (self.esquerda, self.y), linha, fill=COR_TEXTO, font=self.fontes.corpo_bold
                )
                self.y += altura_linha
            for linha in linhas_valor:
                self.draw.text(
                    (self.esquerda, self.y), linha, fill=COR_TEXTO, font=self.fontes.corpo
                )
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
        self.draw.text(
            (self.esquerda, self.y), prefixo, fill=COR_TEXTO, font=self.fontes.corpo_bold
        )

        x_valor = self.esquerda + largura_prefixo
        if linhas_valor:
            self.draw.text(
                (x_valor, self.y), linhas_valor[0], fill=COR_TEXTO, font=self.fontes.corpo
            )
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
        recuo: int = 0,
        espaco_final: int = 8,
    ):
        x_inicio = self.esquerda + max(0, int(recuo))
        largura_disponivel = self.direita - x_inicio
        altura_linha = self._altura_linha(fonte)
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
                self.y += altura_linha // 3

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
        largura, _altura = self._medir_texto(run.texto, self._fonte_run_formatado(run))
        return largura

    def _quebrar_runs_formatados(
        self,
        runs: list[_TextoFormatadoRun],
        largura_disponivel: int,
    ) -> list[list[_TextoFormatadoRun]]:
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
            tokens = re.findall(r"\n|[^\S\n]+|[^\s]+", run.texto)
            for token in tokens:
                if token == "\n":
                    fechar_linha()
                    espaco_pendente = False
                    continue
                if token.isspace():
                    if linha_atual:
                        espaco_pendente = True
                    continue

                texto_token = f" {token}" if espaco_pendente and linha_atual else token
                token_run = _TextoFormatadoRun(
                    texto=texto_token,
                    negrito=run.negrito,
                    italico=run.italico,
                    cor_fundo=run.cor_fundo,
                )
                largura_token = self._largura_run_formatado(token_run)

                if linha_atual and largura_atual + largura_token > largura_disponivel:
                    fechar_linha()
                    token_run = _TextoFormatadoRun(
                        texto=token,
                        negrito=run.negrito,
                        italico=run.italico,
                        cor_fundo=run.cor_fundo,
                    )
                    largura_token = self._largura_run_formatado(token_run)

                linha_atual.append(token_run)
                largura_atual += largura_token
                espaco_pendente = False

        fechar_linha()
        return linhas

    def _adicionar_runs_formatados(
        self,
        runs: list[_TextoFormatadoRun],
        *,
        recuo: int = 0,
        espaco_final: int = 8,
    ):
        x_inicio = self.esquerda + max(0, int(recuo))
        largura_disponivel = self.direita - x_inicio
        altura_linha = self._altura_linha(self.fontes.corpo, fator=1.15)
        linhas = self._quebrar_runs_formatados(runs, largura_disponivel)

        for linha in linhas:
            self._garantir_espaco(altura_linha + 3)
            x_atual = x_inicio
            for run in linha:
                fonte = self._fonte_run_formatado(run)
                largura_run, _altura_run = self._medir_texto(run.texto, fonte)
                if run.cor_fundo:
                    self.draw.rectangle(
                        (
                            x_atual,
                            self.y,
                            x_atual + largura_run,
                            self.y + altura_linha,
                        ),
                        fill=run.cor_fundo,
                    )
                self.draw.text((x_atual, self.y), run.texto, fill=COR_TEXTO, font=fonte)
                x_atual += largura_run
            self.y += altura_linha

        self.y += max(0, int(espaco_final))

    def _desenhar_linha_assinatura(
        self,
        x_centro: int,
        y: int,
        largura: int,
        titulo: str,
    ):
        x_inicio = int(x_centro - (largura / 2))
        x_fim = int(x_centro + (largura / 2))
        self.draw.line((x_inicio, y, x_fim, y), fill=COR_BORDA, width=2)
        largura_titulo, _ = self._medir_texto(titulo, self.fontes.rodape)
        self.draw.text(
            (x_centro - (largura_titulo / 2), y + 16),
            titulo,
            fill=COR_TEXTO,
            font=self.fontes.rodape,
        )

    def _desenhar_emitido_em(self, y: int):
        emitido_em = f"Emitido em {_formatar_data_hora_br(self.ocorrencia.get('criado_em'))}"
        largura_emitido, _ = self._medir_texto(emitido_em, self.fontes.rodape_italico)
        self.draw.text(
            ((self.largura - largura_emitido) / 2, y),
            emitido_em,
            fill=COR_TEXTO_MUTED,
            font=self.fontes.rodape_italico,
        )

    def _desenhar_assinaturas_corridas(
        self,
        *,
        y_base: int,
        titulo: str,
        quantidade_linhas: int,
    ):
        largura_titulo, _ = self._medir_texto(titulo, self.fontes.pequeno_bold)
        self.draw.text(
            ((self.largura - largura_titulo) / 2, y_base),
            titulo,
            fill=COR_TEXTO,
            font=self.fontes.pequeno_bold,
        )

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
        self._desenhar_linha_assinatura(
            self.centro_x - 330,
            y_gestao,
            420,
            "Coordenacao Pedagogica",
        )
        self._desenhar_linha_assinatura(
            self.centro_x + 330,
            y_gestao,
            420,
            "Direcao",
        )
        self._desenhar_emitido_em(y_gestao + 94)

    def _desenhar_rodape(self):
        tipo_registro = _obter_tipo_registro(self.ocorrencia)
        if tipo_registro == TIPO_REGISTRO_GERAL:
            altura_bloco = 650
        elif tipo_registro == TIPO_REGISTRO_ESTUDANTE and len(
            _obter_estudantes_vinculados_ocorrencia(self.ocorrencia)
        ) > 1:
            altura_bloco = 420
        elif tipo_registro == TIPO_REGISTRO_PROFESSOR and len(
            _obter_professores_vinculados_ocorrencia(self.ocorrencia)
        ) > 1:
            altura_bloco = 420
        elif tipo_registro == TIPO_REGISTRO_PROFESSOR:
            altura_bloco = 300
        else:
            altura_bloco = 300

        if self.y + altura_bloco > self.altura - MARGEM_BASE:
            self._nova_pagina(continuacao=True)

        y_base = self.altura - MARGEM_BASE - altura_bloco + 24

        if tipo_registro == TIPO_REGISTRO_PROFESSOR:
            professores_vinculados = _obter_professores_vinculados_ocorrencia(self.ocorrencia)
            if len(professores_vinculados) > 1:
                self._desenhar_assinaturas_corridas(
                    y_base=y_base,
                    titulo="ASSINATURAS DOS PROFESSORES",
                    quantidade_linhas=len(professores_vinculados),
                )
                return
            centros = [
                self.esquerda + ((self.direita - self.esquerda) * 0.18),
                self.centro_x,
                self.direita - ((self.direita - self.esquerda) * 0.18),
            ]
            titulos = ["Professor(a)", "Coordenacao Pedagogica", "Direcao"]
            for centro, titulo in zip(centros, titulos):
                self._desenhar_linha_assinatura(int(centro), y_base + 54, 420, titulo)
            self._desenhar_emitido_em(y_base + 142)
            return

        if tipo_registro == TIPO_REGISTRO_GERAL:
            self._desenhar_assinaturas_corridas(
                y_base=y_base,
                titulo="ASSINATURAS DOS PROFESSORES",
                quantidade_linhas=12,
            )
            return

        estudantes_vinculados = _obter_estudantes_vinculados_ocorrencia(self.ocorrencia)
        if len(estudantes_vinculados) > 1:
            self._desenhar_assinaturas_corridas(
                y_base=y_base,
                titulo="ASSINATURAS DOS ESTUDANTES",
                quantidade_linhas=len(estudantes_vinculados),
            )
            return

        centros = [
            self.esquerda + ((self.direita - self.esquerda) * 0.18),
            self.centro_x,
            self.direita - ((self.direita - self.esquerda) * 0.18),
        ]
        titulos = ["Estudante", "Coordenacao Pedagogica", "Direcao"]
        for centro, titulo in zip(centros, titulos):
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
            draw.text(
                (
                    self.largura - MARGEM_X - largura,
                    self.altura - MARGEM_BASE + max(0, 40 - altura // 2),
                ),
                texto,
                fill=COR_TEXTO_MUTED,
                font=self.fontes.rodape,
            )

    def _campos_resumo_registro(self) -> list[tuple[str, str]]:
        tipo_registro = _obter_tipo_registro(self.ocorrencia)
        referencia = _texto_seguro(self.ocorrencia.get("nome_estudante"))
        professor = _texto_seguro(self.ocorrencia.get("professor_requerente"))
        disciplina = _texto_seguro(self.ocorrencia.get("disciplina"))
        data = _formatar_data_br(self.ocorrencia.get("data_ocorrencia"))
        horario = _texto_seguro(self.ocorrencia.get("horario_ocorrencia"))
        acao = _rotulo_acao(self.ocorrencia.get("acao_aplicada"))
        status = _rotulo_status(self.ocorrencia.get("status"))

        if tipo_registro == TIPO_REGISTRO_PROFESSOR:
            total_professores = len(_obter_professores_vinculados_ocorrencia(self.ocorrencia))
            return [
                ("Professor(es)" if total_professores > 1 else "Professor", professor),
                ("Assunto ou pauta", disciplina),
                ("Data", data),
                ("Horario", f"As {horario} h" if horario != "Nao informado" else horario),
                ("Acao aplicada", acao),
                ("Status", status),
            ]

        if tipo_registro == TIPO_REGISTRO_GERAL:
            return [
                ("Registro geral", referencia),
                ("Publico", professor),
                ("Tema ou pauta", disciplina),
                ("Data", data),
                ("Horario", f"As {horario} h" if horario != "Nao informado" else horario),
                ("Acao aplicada", acao),
                ("Status", status),
            ]

        turma = _texto_seguro(self.ocorrencia.get("turma_nome"))
        aula = _formatar_aula(self.ocorrencia, self.turma)
        total_estudantes = len(_obter_estudantes_vinculados_ocorrencia(self.ocorrencia))
        return [
            ("Estudante(s)" if total_estudantes > 1 else "Estudante", referencia),
            ("Turma", turma),
            ("Professor requerente", professor),
            ("Disciplina ou funcao", disciplina),
            ("Data", data),
            ("Aula", aula),
            ("Horario", f"As {horario} h" if horario != "Nao informado" else horario),
            ("Acao aplicada", acao),
            ("Status", status),
        ]

    def renderizar(self) -> bytes:
        tipo_registro = _obter_tipo_registro(self.ocorrencia)
        descricao = _texto_seguro(self.ocorrencia.get("descricao"), padrao="")
        regimento_itens = _obter_itens_regimento_ocorrencia(self.ocorrencia)

        for rotulo, valor in self._campos_resumo_registro():
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

        self._adicionar_paragrafos(
            _obter_observacao_final(self.ocorrencia), fonte=self.fontes.pequeno_bold
        )
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
