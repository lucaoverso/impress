from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageFont, ImageOps

BASE_DIR = Path(__file__).resolve().parent.parent.parent
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
FONTES_SERIF_REGULARES = (
    "C:/Windows/Fonts/times.ttf",
    "C:/Windows/Fonts/times new roman.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf",
)
FONTES_SERIF_BOLD = (
    "C:/Windows/Fonts/timesbd.ttf",
    "C:/Windows/Fonts/times new roman bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSerif-Bold.ttf",
)
FONTES_SERIF_ITALIC = (
    "C:/Windows/Fonts/timesi.ttf",
    "C:/Windows/Fonts/times new roman italic.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSerif-Italic.ttf",
)
FONTES_SERIF_BOLD_ITALIC = (
    "C:/Windows/Fonts/timesbi.ttf",
    "C:/Windows/Fonts/times new roman bold italic.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-BoldItalic.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSerif-BoldItalic.ttf",
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


def _carregar_fonte(candidatos: tuple[str, ...], tamanho: int) -> ImageFont.ImageFont:
    for caminho in candidatos:
        if Path(caminho).exists():
            return ImageFont.truetype(caminho, tamanho)
    return ImageFont.load_default()


def _carregar_fontes() -> _FontPack:
    return _FontPack(
        escola=_carregar_fonte(FONTES_REGULARES, 58),
        subtitulo=_carregar_fonte(FONTES_REGULARES, 43),
        titulo=_carregar_fonte(FONTES_SERIF_BOLD, 50),
        secao=_carregar_fonte(FONTES_SERIF_BOLD, 48),
        corpo=_carregar_fonte(FONTES_SERIF_REGULARES, 50),
        corpo_bold=_carregar_fonte(FONTES_SERIF_BOLD, 50),
        corpo_italico=_carregar_fonte(FONTES_SERIF_ITALIC, 50),
        corpo_bold_italico=_carregar_fonte(FONTES_SERIF_BOLD_ITALIC, 50),
        pequeno=_carregar_fonte(FONTES_SERIF_REGULARES, 42),
        pequeno_bold=_carregar_fonte(FONTES_SERIF_BOLD, 42),
        rodape=_carregar_fonte(FONTES_SERIF_REGULARES, 36),
        rodape_italico=_carregar_fonte(FONTES_SERIF_ITALIC, 34),
    )


def _carregar_logo() -> Image.Image | None:
    if not LOGO_ESCOLA_PATH.exists():
        return None
    with Image.open(LOGO_ESCOLA_PATH) as logo_origem:
        logo = ImageOps.exif_transpose(logo_origem).convert("RGBA")
        logo.thumbnail((500, 500), Image.Resampling.LANCZOS)
        return logo.copy()
