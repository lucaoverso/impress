from io import BytesIO
import textwrap

from PIL import Image, ImageDraw, ImageFont

from services.pcpi_service import nome_turno_pcpi

_PDF_PAGE_SIZE = (1240, 1754)
_PDF_MARGIN_X = 96
_PDF_MARGIN_Y = 96
_PDF_LINE_SPACING = 12


def _carregar_fonte(tamanho: int, *, negrito: bool = False):
    caminhos = []
    if negrito:
        caminhos.extend(
            [
                r"C:\Windows\Fonts\arialbd.ttf",
                r"C:\Windows\Fonts\calibrib.ttf",
            ]
        )
    caminhos.extend(
        [
            r"C:\Windows\Fonts\arial.ttf",
            r"C:\Windows\Fonts\calibri.ttf",
        ]
    )
    for caminho in caminhos:
        try:
            return ImageFont.truetype(caminho, tamanho)
        except OSError:
            continue
    return ImageFont.load_default()


def _quebrar_linhas(draw: ImageDraw.ImageDraw, texto: str, fonte, largura_maxima: int) -> list[str]:
    linhas = []
    for paragrafo in str(texto or "").splitlines() or [""]:
        conteudo = paragrafo.strip()
        if not conteudo:
            linhas.append("")
            continue

        atual = []
        for palavra in conteudo.split():
            tentativa = " ".join(atual + [palavra])
            largura = draw.textbbox((0, 0), tentativa, font=fonte)[2]
            if atual and largura > largura_maxima:
                linhas.append(" ".join(atual))
                atual = [palavra]
            else:
                atual.append(palavra)
        if atual:
            linhas.append(" ".join(atual))
    return linhas or [""]


def gerar_pdf_texto_pcpi(dados_texto: dict) -> bytes:
    titulo = "Registro PCPI"
    subtitulo = f"{nome_turno_pcpi(dados_texto.get('turno'))} - {dados_texto.get('data', '')}"
    texto = str(dados_texto.get("texto") or "").strip() or "Sem conteudo para exportacao."

    fonte_titulo = _carregar_fonte(34, negrito=True)
    fonte_subtitulo = _carregar_fonte(20, negrito=True)
    fonte_texto = _carregar_fonte(20)

    imagens = []
    pagina = Image.new("RGB", _PDF_PAGE_SIZE, "white")
    draw = ImageDraw.Draw(pagina)

    y = _PDF_MARGIN_Y
    draw.text((_PDF_MARGIN_X, y), titulo, fill="black", font=fonte_titulo)
    y += draw.textbbox((0, 0), titulo, font=fonte_titulo)[3] + 14
    draw.text((_PDF_MARGIN_X, y), subtitulo, fill="black", font=fonte_subtitulo)
    y += draw.textbbox((0, 0), subtitulo, font=fonte_subtitulo)[3] + 28

    largura_texto = _PDF_PAGE_SIZE[0] - (_PDF_MARGIN_X * 2)
    altura_linha = draw.textbbox((0, 0), "Ag", font=fonte_texto)[3] + _PDF_LINE_SPACING

    for linha in _quebrar_linhas(draw, texto, fonte_texto, largura_texto):
        if y + altura_linha > _PDF_PAGE_SIZE[1] - _PDF_MARGIN_Y:
            imagens.append(pagina)
            pagina = Image.new("RGB", _PDF_PAGE_SIZE, "white")
            draw = ImageDraw.Draw(pagina)
            y = _PDF_MARGIN_Y
        draw.text((_PDF_MARGIN_X, y), linha, fill="black", font=fonte_texto)
        y += altura_linha

    imagens.append(pagina)

    buffer = BytesIO()
    primeira, *restantes = imagens
    primeira.save(buffer, format="PDF", resolution=150.0, save_all=True, append_images=restantes)
    return buffer.getvalue()
