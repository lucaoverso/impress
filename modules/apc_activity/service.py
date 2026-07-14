from datetime import datetime
from pathlib import Path

from . import repository
from .pdf_service import generate_activity_pdf
from .sanitizer import sanitize_activity_html, visible_text


def prepare_activity_data(
    payload, *, user: dict, period: dict, delivery: dict, allow_incomplete: bool = False
) -> dict:
    body = sanitize_activity_html(payload.corpo_html)
    skill = str(payload.habilidade or "").strip()
    content = str(payload.conteudo or "").strip()
    if not allow_incomplete:
        if not skill:
            raise ValueError("Informe a habilidade da APC.")
        if not content:
            raise ValueError("Informe o conteudo relacionado.")
        if not visible_text(body):
            raise ValueError("Informe o texto da APC.")
    return {
        "professor_nome": str(user.get("nome") or "Professor(a)").strip(),
        "turma_id": int(delivery.get("turma_id") or 0),
        "turma_nome": str(delivery.get("turma_nome") or "Turma nao informada").strip(),
        "disciplina_id": int(delivery.get("disciplina_id") or 0),
        "disciplina_nome": str(delivery.get("disciplina_nome") or "Disciplina").strip(),
        "data_referencia": str(period.get("data_referencia") or "").strip(),
        "data_referencia_br": _format_date(period.get("data_referencia")),
        "habilidade": skill,
        "conteudo": content,
        "corpo_html": body,
        "activity_columns": int(payload.activity_columns),
    }


def _format_date(value: str) -> str:
    try:
        return datetime.strptime(str(value or ""), "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return str(value or "")


def render_preview(data: dict) -> bytes:
    return generate_activity_pdf(data)


def save_activity(*, data: dict, period_id: int, user_id: int, existing: dict | None, directory: Path) -> tuple[dict, dict, bytes]:
    pdf = generate_activity_pdf(data)
    safe_subject = "".join(char if char.isalnum() else "_" for char in data["disciplina_nome"]).strip("_") or "disciplina"
    client_name = f"APC_{safe_subject}_{data['data_referencia']}.pdf"
    stored_name = f"apc_gerada_{period_id}_{user_id}_{data['turma_id']}_{data['disciplina_id']}.pdf"
    destination = directory / stored_name
    destination.write_bytes(pdf)
    old_path_value = str((existing or {}).get("arquivo_path") or "").strip()
    old_path = Path(old_path_value) if old_path_value else None
    values = {
        "periodo_id": int(period_id),
        "professor_usuario_id": int(user_id),
        "turma_id": data["turma_id"],
        "disciplina_id": data["disciplina_id"],
        "arquivo_nome_cliente": client_name,
        "arquivo_nome_original": client_name,
        "arquivo_path": str(destination),
        "arquivo_tamanho": len(pdf),
        "arquivo_tipo": "application/pdf",
    }
    submission = None
    try:
        submission = repository.save_submission(existing=existing, values=values)
        activity = repository.upsert_generated_activity(envio_id=int(submission["id"]), values=data)
    except Exception:
        if submission is None:
            destination.unlink(missing_ok=True)
        raise
    if old_path is not None and old_path != destination:
        old_path.unlink(missing_ok=True)
    return submission, activity, pdf
