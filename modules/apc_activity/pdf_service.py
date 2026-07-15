from __future__ import annotations

import io
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from .image_service import resolve_activity_image
from .rich_text import Block, ImageBlock, Run, parse_html
from .text_layout import alignment_metrics, layout_block


BASE_DIR = Path(__file__).resolve().parents[2]
CREST_PATH = BASE_DIR / "static" / "img" / "brasao_escola_apc.jpeg"
REFERENCE_DPI = 150
SCALE = 72 / REFERENCE_DPI
PAGE_SIZE = (1240, 1754)
MARGIN_X = 75
MARGIN_TOP = 64
MARGIN_BOTTOM = 62
BODY_FONT_SIZE = 25  # 12 pt in the 150 DPI coordinate system of the DOCX comparison.
FONT_SIZE_PT = 12
LINE_HEIGHT = 37.5  # 18 pt: Times New Roman 12 pt with 1.5 spacing.
CREST_SIZE = (114, 118)  # 694690 x 721995 EMU in the reference DOCX.

FONT_FILES = {
    "APCTimes": (
        "C:/Windows/Fonts/times.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    ),
    "APCTimesBold": (
        "C:/Windows/Fonts/timesbd.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSerif-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    ),
    "APCTimesItalic": (
        "C:/Windows/Fonts/timesi.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSerif-Italic.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf",
    ),
    "APCTimesBoldItalic": (
        "C:/Windows/Fonts/timesbi.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSerif-BoldItalic.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-BoldItalic.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-BoldItalic.ttf",
    ),
}

FONT_FALLBACKS = {
    "APCTimes": "Times-Roman",
    "APCTimesBold": "Times-Bold",
    "APCTimesItalic": "Times-Italic",
    "APCTimesBoldItalic": "Times-BoldItalic",
}


def _register_font(name: str, candidates: tuple[str, ...], fallback: str) -> None:
    if name in pdfmetrics.getRegisteredFontNames():
        return
    path = next((candidate for candidate in candidates if Path(candidate).exists()), None)
    if path:
        pdfmetrics.registerFont(TTFont(name, path))
        return
    pdfmetrics.registerFont(pdfmetrics.Font(name, fallback, "WinAnsiEncoding"))


def _register_fonts() -> None:
    for name, candidates in FONT_FILES.items():
        _register_font(name, candidates, FONT_FALLBACKS[name])


class ActivityPdfRenderer:
    def __init__(self, data: dict):
        _register_fonts()
        self.data = data
        self.output = io.BytesIO()
        self.pdf = canvas.Canvas(self.output, pagesize=A4, pageCompression=1)
        self.page_width, self.page_height = A4
        self.y = 0.0
        self.page_started = False
        self._new_page()

    def _new_page(self):
        if self.page_started:
            self.pdf.showPage()
        self.page_started = True
        self.pdf.setLineWidth(0.5)
        self.pdf.rect(50 * SCALE, 50 * SCALE, self.page_width - 100 * SCALE, self.page_height - 100 * SCALE)
        self._header()

    def _draw_text(self, x: float, y: float, text: str, font: str = "APCTimes") -> None:
        self.pdf.setFont(font, FONT_SIZE_PT)
        baseline = self.page_height - y * SCALE - FONT_SIZE_PT * 0.82
        self.pdf.drawString(x * SCALE, baseline, str(text or ""))

    def _header(self):
        if CREST_PATH.exists():
            self.pdf.drawImage(
                ImageReader(str(CREST_PATH)),
                84 * SCALE,
                self.page_height - (MARGIN_TOP + CREST_SIZE[1]) * SCALE,
                CREST_SIZE[0] * SCALE,
                CREST_SIZE[1] * SCALE,
                preserveAspectRatio=False,
                mask="auto",
            )
        center = PAGE_SIZE[0] / 2 + 25
        self._center("ESCOLA ESTADUAL PADRE JOSÉ DANIEL", "APCTimesBold", MARGIN_TOP + 20, center=center)
        self._center("ATIVIDADE PEDAGÓGICA COMPLEMENTAR", "APCTimesBold", MARGIN_TOP + 72, center=center)
        self.y = MARGIN_TOP + 186

    def _center(self, text: str, font: str, y: float, *, center: float | None = None):
        width = self._text_width(text, font)
        self._draw_text((center or PAGE_SIZE[0] / 2) - width / 2, y, text, font)

    def _text_width(self, text: str, font: str) -> float:
        return pdfmetrics.stringWidth(str(text or ""), font, FONT_SIZE_PT) / SCALE

    def _fit_text(self, text: str, max_width: float, font: str) -> str:
        text = str(text or "").strip()
        if self._text_width(text, font) <= max_width:
            return text
        suffix = "..."
        while text and self._text_width(text + suffix, font) > max_width:
            text = text[:-1]
        return text.rstrip() + suffix

    def _metadata(self):
        left, mid, right = MARGIN_X, 943, PAGE_SIZE[0] - MARGIN_X
        rows = (
            ("PROFESSOR:", self.data["professor_nome"], "DATA:", self.data["data_referencia_br"]),
            ("DISCIPLINA:", self.data["disciplina_nome"], "TURMA:", self.data["turma_nome"]),
        )
        for label1, value1, label2, value2 in rows:
            self._draw_text(left, self.y, label1, "APCTimesBold")
            x1 = left + self._text_width(label1 + " ", "APCTimesBold")
            self._draw_text(x1, self.y, self._fit_text(value1, mid - x1 - 24, "APCTimes"))
            self._draw_text(mid, self.y, label2, "APCTimesBold")
            x2 = mid + self._text_width(label2 + " ", "APCTimesBold")
            self._draw_text(x2, self.y, self._fit_text(value2, right - x2, "APCTimes"))
            self.y += 44
        self.y += 46

    def _wrap_plain(self, text: str, font: str, width: float) -> list[str]:
        lines: list[str] = []
        for paragraph in str(text or "").splitlines() or [""]:
            current = ""
            for word in paragraph.split():
                candidate = f"{current} {word}".strip()
                if current and self._text_width(candidate, font) > width:
                    lines.append(current)
                    current = word
                else:
                    current = candidate
            lines.append(current)
        return lines

    def _labeled_value(self, label: str, value: str):
        label_width = 200
        width = PAGE_SIZE[0] - 2 * MARGIN_X - label_width
        lines = self._wrap_plain(value, "APCTimes", width)
        self._draw_text(MARGIN_X, self.y, label, "APCTimesBold")
        for index, line in enumerate(lines):
            self._draw_text(MARGIN_X + label_width, self.y + index * LINE_HEIGHT, line)
        self.y += max(LINE_HEIGHT, len(lines) * LINE_HEIGHT)

    @staticmethod
    def _font_for(run: Run) -> str:
        if run.bold and run.italic:
            return "APCTimesBoldItalic"
        if run.bold:
            return "APCTimesBold"
        if run.italic:
            return "APCTimesItalic"
        return "APCTimes"

    def _layout_block(self, block: Block, width: float) -> list[list[Run]]:
        return layout_block(
            block,
            width,
            lambda run: self._text_width(run.text, self._font_for(run)),
        )

    def _draw_block(self, block: Block, x: float, y: float, width: float) -> float:
        marker_width = 42 if block.marker else 0
        indent = block.indent * 34
        content_width = width - marker_width - indent
        if block.marker:
            self._draw_text(x + indent, y, block.marker)
        lines = self._layout_block(block, content_width)
        for line_index, line in enumerate(lines):
            offset, justify_spacing = alignment_metrics(
                block,
                line,
                line_index,
                len(lines),
                content_width,
                lambda run: self._text_width(run.text, self._font_for(run)),
            )
            cursor = x + indent + marker_width + offset
            line_y = y + line_index * LINE_HEIGHT
            for run in line:
                font = self._font_for(run)
                self._draw_text(cursor, line_y, run.text, font)
                run_width = self._text_width(run.text, font)
                display_width = run_width + (justify_spacing if run.text.isspace() else 0)
                if run.underline:
                    underline_y = self.page_height - (line_y + 29) * SCALE
                    self.pdf.setLineWidth(0.5)
                    self.pdf.line(cursor * SCALE, underline_y, (cursor + display_width) * SCALE, underline_y)
                cursor += display_width
        return len(lines) * LINE_HEIGHT

    def _image_geometry(self, block: ImageBlock, width: float) -> tuple[Path | None, float, float]:
        path = resolve_activity_image(block.token)
        if path is None:
            return None, 0, 0
        reader = ImageReader(str(path))
        source_width, source_height = reader.getSize()
        target_width = width * max(25, min(100, block.width_percent)) / 100
        target_height = target_width * source_height / source_width
        max_image_height = PAGE_SIZE[1] - (MARGIN_TOP + 186) - MARGIN_BOTTOM
        if target_height > max_image_height:
            scale = max_image_height / target_height
            target_width *= scale
            target_height *= scale
        return path, target_width, target_height

    def _draw_image_block(self, block: ImageBlock, x: float, width: float) -> float:
        path, image_width, image_height = self._image_geometry(block, width)
        if path is None:
            return 0
        if block.align == "left":
            image_x = x
        elif block.align == "right":
            image_x = x + width - image_width
        else:
            image_x = x + (width - image_width) / 2
        self.pdf.drawImage(
            ImageReader(str(path)),
            image_x * SCALE,
            self.page_height - (self.y + image_height) * SCALE,
            image_width * SCALE,
            image_height * SCALE,
            preserveAspectRatio=True,
            mask="auto",
        )
        return image_height + 18

    def _content(self):
        self.y += 8
        blocks = parse_html(self.data["corpo_html"])
        columns = int(self.data.get("activity_columns") or 1)
        gap = 42 if columns == 2 else 0
        width = (PAGE_SIZE[0] - 2 * MARGIN_X - gap) / columns
        column, start_y = 0, self.y
        x_positions = [MARGIN_X, MARGIN_X + width + gap]
        for block in blocks:
            if isinstance(block, ImageBlock):
                _path, _image_width, image_height = self._image_geometry(block, width)
                height = image_height + 18
            else:
                height = len(self._layout_block(block, width)) * LINE_HEIGHT
            if self.y + height > PAGE_SIZE[1] - MARGIN_BOTTOM:
                if columns == 2 and column == 0:
                    column, self.y = 1, start_y
                else:
                    self._new_page()
                    column, start_y = 0, self.y
            if isinstance(block, ImageBlock):
                self.y += self._draw_image_block(block, x_positions[column], width)
            else:
                self.y += self._draw_block(block, x_positions[column], self.y, width)

    def render(self) -> bytes:
        self._metadata()
        self._labeled_value("HABILIDADE", self.data.get("habilidade", ""))
        self._labeled_value("CONTEÚDO", self.data.get("conteudo", ""))
        self.y += 49
        title = f"ATIVIDADE PEDAGÓGICA COMPLEMENTAR DE {str(self.data['disciplina_nome']).upper()}"
        for line in self._wrap_plain(title, "APCTimesBold", PAGE_SIZE[0] - 2 * MARGIN_X):
            self._center(line, "APCTimesBold", self.y)
            self.y += LINE_HEIGHT
        self.y += 20
        self._content()
        self.pdf.save()
        return self.output.getvalue()


def generate_activity_pdf(data: dict) -> bytes:
    return ActivityPdfRenderer(data).render()
