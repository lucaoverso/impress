from __future__ import annotations

import io
import os
import smtplib
from email.message import EmailMessage
from datetime import datetime

from fastapi import HTTPException
from PIL import Image, ImageDraw, ImageFont

from . import repository

PDF_PAGE_SIZE = (1240, 1754)
PDF_MARGIN_X = 92
PDF_MARGIN_Y = 92
PDF_BOTTOM = 96
PDF_LINE_SPACING = 10


def get_dashboard(data_inicio: str, data_fim: str) -> dict:
    return repository.get_management_dashboard(data_inicio, data_fim)


def get_attachments(data_inicio: str, data_fim: str) -> dict:
    return repository.get_attachments_report(data_inicio, data_fim)


def list_teacher_report_recipients() -> list[dict]:
    return [
        {
            "id": int(item.get("id") or 0),
            "nome": str(item.get("nome") or "").strip(),
            "email": str(item.get("email") or "").strip(),
        }
        for item in repository.list_teacher_recipients()
    ]


def build_teacher_report(professor_id: int, data_inicio: str, data_fim: str) -> dict:
    professor = repository.get_teacher(int(professor_id))
    if not professor:
        raise HTTPException(404, "Professor nao encontrado.")

    impressoes = repository.get_teacher_printing_summary(int(professor_id), data_inicio, data_fim)
    recursos = repository.get_teacher_resource_summary(int(professor_id), data_inicio, data_fim)
    anexos_base = repository.get_attachments_report(data_inicio, data_fim)
    pendencias = [
        item
        for item in anexos_base.get("tabelas", {}).get("professores_pendencias", [])
        if int(item.get("professor_id") or 0) == int(professor_id)
    ]
    entregas = [
        item
        for item in anexos_base.get("tabelas", {}).get("entregas_recentes", [])
        if int(item.get("professor_id") or 0) == int(professor_id)
    ]

    resumo = {
        "total_paginas": impressoes["total_paginas"],
        "total_jobs": impressoes["total_jobs"],
        "total_reservas": recursos["total_reservas"],
        "total_pendencias": len(pendencias),
        "total_entregas": len([item for item in entregas if item.get("situacao") != "Pendente"]),
    }
    alertas = _build_teacher_alerts(resumo)

    return {
        "professor": {
            "id": int(professor.get("id") or 0),
            "nome": str(professor.get("nome") or "").strip(),
            "email": str(professor.get("email") or "").strip(),
        },
        "periodo": {"data_inicio": data_inicio, "data_fim": data_fim},
        "resumo": resumo,
        "impressoes": impressoes,
        "recursos": recursos,
        "anexos": {
            "pendencias": pendencias,
            "entregas": entregas,
        },
        "alertas": alertas,
    }


def _build_teacher_alerts(resumo: dict) -> list[str]:
    alertas = []
    if int(resumo.get("total_pendencias") or 0) > 0:
        alertas.append("Ha documentos pendentes na Central de Anexos.")
    if int(resumo.get("total_paginas") or 0) >= 150:
        alertas.append("Volume de impressoes elevado no periodo.")
    if not alertas:
        alertas.append("Sem alertas relevantes para o periodo.")
    return alertas


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


class _TeacherReportPdf:
    def __init__(self, report: dict):
        self.report = report
        self.title_font = _load_font(34, bold=True)
        self.heading_font = _load_font(24, bold=True)
        self.body_font = _load_font(20)
        self.bold_font = _load_font(20, bold=True)
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

        self.heading("Impressões recentes")
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


def generate_teacher_report_pdf(professor_id: int, data_inicio: str, data_fim: str) -> bytes:
    report = build_teacher_report(professor_id, data_inicio, data_fim)
    return _TeacherReportPdf(report).render()


def send_teacher_report_email(
    professor_id: int,
    data_inicio: str,
    data_fim: str,
    *,
    destino_email: str | None = None,
    assunto: str | None = None,
    mensagem: str | None = None,
) -> dict:
    report = build_teacher_report(professor_id, data_inicio, data_fim)
    professor = report["professor"]
    destination = str(destino_email or professor.get("email") or "").strip()
    if not destination:
        raise HTTPException(400, "Professor sem email cadastrado.")

    pdf_bytes = _TeacherReportPdf(report).render()
    subject = str(assunto or "").strip() or (
        f"Relatorio individual - {professor['nome']} - {_date_br(data_inicio)} a {_date_br(data_fim)}"
    )
    body = str(mensagem or "").strip() or (
        "Segue em anexo o relatorio individual do periodo selecionado."
    )
    _send_email_with_attachment(
        to_email=destination,
        subject=subject,
        body=body,
        attachment=pdf_bytes,
        filename=f"relatorio-professor-{int(professor_id)}.pdf",
    )
    return {"mensagem": "Relatorio enviado com sucesso.", "destino_email": destination}


def _send_email_with_attachment(
    *,
    to_email: str,
    subject: str,
    body: str,
    attachment: bytes,
    filename: str,
):
    host = os.getenv("SMTP_HOST", "").strip()
    if not host:
        raise HTTPException(
            503,
            "Envio de email nao configurado. Defina SMTP_HOST, SMTP_PORT e SMTP_FROM.",
        )
    port = int(os.getenv("SMTP_PORT", "587") or 587)
    from_email = os.getenv("SMTP_FROM", "").strip() or os.getenv("SMTP_USER", "").strip()
    if not from_email:
        raise HTTPException(503, "Envio de email sem remetente configurado.")

    message = EmailMessage()
    message["From"] = from_email
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)
    message.add_attachment(
        attachment,
        maintype="application",
        subtype="pdf",
        filename=filename,
    )

    user = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip()
    use_tls = os.getenv("SMTP_TLS", "1").strip().lower() not in {"0", "false", "nao", "no"}

    try:
        with smtplib.SMTP(host, port, timeout=20) as smtp:
            if use_tls:
                smtp.starttls()
            if user and password:
                smtp.login(user, password)
            smtp.send_message(message)
    except OSError as exc:
        raise HTTPException(502, "Falha ao enviar email pelo servidor SMTP.") from exc
