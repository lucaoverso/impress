from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage

from fastapi import HTTPException

from . import pdf_service, repository


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
        "alertas": _build_teacher_alerts(resumo),
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


def generate_teacher_report_pdf(professor_id: int, data_inicio: str, data_fim: str) -> bytes:
    report = build_teacher_report(professor_id, data_inicio, data_fim)
    return pdf_service.generate_teacher_report_pdf(report)


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

    subject = str(assunto or "").strip() or (
        f"Relatorio individual - {professor['nome']} - "
        f"{pdf_service.format_date_br(data_inicio)} a {pdf_service.format_date_br(data_fim)}"
    )
    body = str(mensagem or "").strip() or (
        "Segue em anexo o relatorio individual do periodo selecionado."
    )
    _send_email_with_attachment(
        to_email=destination,
        subject=subject,
        body=body,
        attachment=pdf_service.generate_teacher_report_pdf(report),
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
