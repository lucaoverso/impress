from __future__ import annotations

import io
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

PDF_PAGE_SIZE = (1240, 1754)
PDF_MARGIN_X = 92
PDF_MARGIN_Y = 92
PDF_BOTTOM = 96
PDF_LINE_SPACING = 10


def _load_font(size: int, *, bold: bool = False):
    candidates = []
    if bold:
        candidates.extend([r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\calibrib.ttf"])
    candidates.extend(
        [
            r"C:\Windows\Fonts\arial.ttf",
            r"C:\Windows\Fonts\calibri.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
    )
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _date_br(value: str | None) -> str:
    text = str(value or "").strip()
    if not text:
        return "-"
    try:
        return datetime.strptime(text[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return text


class TeacherReportPdf:
    def __init__(self, report: dict):
        self.report = report
        self.title_font = _load_font(34, bold=True)
        self.heading_font = _load_font(24, bold=True)
        self.body_font = _load_font(20)
        self.small_font = _load_font(17)
        self.pages: list[Image.Image] = []
        self._new_page()

    def _new_page(self):
        self.page = Image.new("RGB", PDF_PAGE_SIZE, "white")
        self.draw = ImageDraw.Draw(self.page)
        self.y = PDF_MARGIN_Y
        self.pages.append(self.page)

    def _ensure_space(self, height: int):
        if self.y + height > PDF_PAGE_SIZE[1] - PDF_BOTTOM:
            self._new_page()

    def _wrap(self, text: str, font, width: int) -> list[str]:
        words = str(text or "").split()
        if not words:
            return [""]
        lines = []
        current = []
        for word in words:
            attempt = " ".join(current + [word])
            if current and self.draw.textbbox((0, 0), attempt, font=font)[2] > width:
                lines.append(" ".join(current))
                current = [word]
            else:
                current.append(word)
        if current:
            lines.append(" ".join(current))
        return lines

    def text(self, value: str, font=None, *, gap: int = PDF_LINE_SPACING):
        font = font or self.body_font
        width = PDF_PAGE_SIZE[0] - (PDF_MARGIN_X * 2)
        line_height = self.draw.textbbox((0, 0), "Ag", font=font)[3] + gap
        for line in self._wrap(value, font, width):
            self._ensure_space(line_height + 2)
            self.draw.text((PDF_MARGIN_X, self.y), line, fill="black", font=font)
            self.y += line_height

    def heading(self, value: str):
        self.y += 14
        self.text(value, self.heading_font, gap=14)

    def bullet(self, label: str, value: str):
        self.text(f"- {label}: {value}", self.body_font, gap=9)

    def section_rows(self, rows: list[str], empty_text: str):
        if not rows:
            self.text(empty_text, self.small_font)
            return
        for row in rows:
            self.text(f"- {row}", self.small_font, gap=8)

    def render(self) -> bytes:
        professor = self.report["professor"]
        periodo = self.report["periodo"]
        resumo = self.report["resumo"]

        self.text("Relatorio individual do professor", self.title_font, gap=16)
        self.text(professor["nome"], self.heading_font)
        self.text(
            f"Periodo: {_date_br(periodo['data_inicio'])} a {_date_br(periodo['data_fim'])}",
            self.body_font,
        )
        self.text(f"Email: {professor.get('email') or 'Nao informado'}", self.small_font)

        self.heading("Resumo")
        self.bullet("Paginas impressas", str(resumo["total_paginas"]))
        self.bullet("Jobs de impressao", str(resumo["total_jobs"]))
        self.bullet("Reservas de recursos", str(resumo["total_reservas"]))
        self.bullet("Pendencias de anexos", str(resumo["total_pendencias"]))
        self.bullet("Entregas registradas", str(resumo["total_entregas"]))

        self.heading("Pontos de atencao")
        self.section_rows(self.report.get("alertas") or [], "Sem alertas relevantes.")

        self.heading("Impressoes recentes")
        self.section_rows(
            [
                f"{_date_br(item.get('criado_em'))} - {item.get('arquivo') or 'Arquivo'} "
                f"({int(item.get('paginas_totais') or 0)} paginas)"
                for item in self.report["impressoes"].get("recentes", [])
            ],
            "Nenhuma impressao concluida no periodo.",
        )

        self.heading("Reservas recentes")
        self.section_rows(
            [
                f"{_date_br(item.get('data'))} - {item.get('recurso_nome') or 'Recurso'} "
                f"- {item.get('turma') or 'Turma nao informada'}"
                for item in self.report["recursos"].get("recentes", [])
            ],
            "Nenhuma reserva ativa no periodo.",
        )

        self.heading("Pendencias de anexos")
        self.section_rows(
            [
                f"{item.get('documento') or 'Documento'} - prazo {_date_br(item.get('prazo'))}"
                for item in self.report["anexos"].get("pendencias", [])
            ],
            "Nenhuma pendencia de anexo no periodo.",
        )

        output = io.BytesIO()
        first, *rest = self.pages
        first.save(output, format="PDF", resolution=150.0, save_all=True, append_images=rest)
        return output.getvalue()


def generate_teacher_report_pdf(report: dict) -> bytes:
    return TeacherReportPdf(report).render()


def format_date_br(value: str | None) -> str:
    return _date_br(value)
