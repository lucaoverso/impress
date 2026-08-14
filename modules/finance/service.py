from datetime import date, datetime

from . import attachment_service, repository
from .schemas import FinanceTransactionCreateIn, FinanceTransactionUpdateIn


class FinanceNotFoundError(LookupError):
    pass


class FinanceConflictError(RuntimeError):
    pass


class FinanceValidationError(ValueError):
    pass


def validate_month(month: str | None) -> str:
    value = str(month or "").strip() or date.today().strftime("%Y-%m")
    try:
        return datetime.strptime(value, "%Y-%m").strftime("%Y-%m")
    except ValueError as exc:
        raise FinanceValidationError("Mes invalido. Use o formato AAAA-MM.") from exc


def _clean(value, limit: int) -> str:
    return " ".join(str(value or "").strip().split())[:limit]


def _values(payload: FinanceTransactionCreateIn | FinanceTransactionUpdateIn) -> dict:
    description = _clean(payload.description, 180)
    category = _clean(payload.category, 100)
    if not description:
        raise FinanceValidationError("Informe a descricao do lancamento.")
    if not category:
        raise FinanceValidationError("Informe a categoria do lancamento.")
    return {
        "transaction_type": payload.transaction_type,
        "occurred_on": payload.occurred_on.isoformat(),
        "description": description,
        "category": category,
        "amount_cents": int(payload.amount_cents),
        "counterparty": _clean(payload.counterparty, 160),
        "notes": str(payload.notes or "").strip()[:1000],
    }


def create_transaction(*, actor_user_id: int, payload: FinanceTransactionCreateIn) -> dict:
    if int(actor_user_id or 0) <= 0:
        raise FinanceValidationError("Administrador invalido.")
    return repository.create_transaction(
        created_by_user_id=int(actor_user_id), values=_values(payload)
    )


def get_transaction(transaction_id: int) -> dict:
    item = repository.get_transaction(transaction_id)
    if not item:
        raise FinanceNotFoundError("Lancamento financeiro nao encontrado.")
    return item


def list_transactions(*, month: str | None, status: str | None = None) -> list[dict]:
    normalized_status = str(status or "").strip().upper() or None
    if normalized_status not in {None, "ACTIVE", "CANCELED"}:
        raise FinanceValidationError("Status de lancamento invalido.")
    return repository.list_transactions(
        month=validate_month(month), status=normalized_status
    )


def update_transaction(
    transaction_id: int, payload: FinanceTransactionUpdateIn
) -> dict:
    current = get_transaction(transaction_id)
    if current["status"] != "ACTIVE":
        raise FinanceConflictError("Lancamentos cancelados nao podem ser editados.")
    updated = repository.update_transaction(transaction_id, _values(payload))
    if not updated:
        raise FinanceConflictError("O lancamento nao esta mais disponivel para edicao.")
    return updated


def cancel_transaction(
    transaction_id: int, *, actor_user_id: int, reason: str
) -> dict:
    current = get_transaction(transaction_id)
    if current["status"] != "ACTIVE":
        raise FinanceConflictError("Este lancamento ja esta cancelado.")
    normalized_reason = _clean(reason, 300)
    if not normalized_reason:
        raise FinanceValidationError("Informe o motivo do cancelamento.")
    canceled = repository.cancel_transaction(
        transaction_id,
        canceled_by_user_id=int(actor_user_id),
        reason=normalized_reason,
    )
    if not canceled:
        raise FinanceConflictError("O lancamento nao esta mais disponivel.")
    return canceled


def get_month_overview(month: str | None) -> dict:
    normalized_month = validate_month(month)
    summary = repository.get_month_summary(normalized_month)
    return {"month": normalized_month, **summary}


def add_attachment(
    transaction_id: int,
    *,
    content: bytes,
    original_filename: str,
) -> dict:
    transaction = get_transaction(transaction_id)
    if transaction["status"] != "ACTIVE":
        raise FinanceConflictError(
            "Nao e possivel anexar comprovantes a um lancamento cancelado."
        )
    try:
        stored = attachment_service.store_attachment(
            content, original_filename=original_filename
        )
    except attachment_service.FinanceAttachmentValidationError as exc:
        raise FinanceValidationError(str(exc)) from exc
    try:
        return repository.create_attachment(transaction_id, stored)
    except Exception:
        attachment_service.delete_attachment_file(stored["stored_name"])
        raise


def get_attachment(token: str) -> tuple[dict, object]:
    attachment = repository.get_attachment_by_token(str(token or "").strip().lower())
    if not attachment:
        raise FinanceNotFoundError("Comprovante nao encontrado.")
    path = attachment_service.resolve_attachment(attachment["stored_name"])
    if not path:
        raise FinanceNotFoundError("Arquivo do comprovante nao encontrado.")
    return attachment, path


def remove_attachment(transaction_id: int, attachment_id: int) -> None:
    transaction = get_transaction(transaction_id)
    if transaction["status"] != "ACTIVE":
        raise FinanceConflictError(
            "Nao e possivel remover comprovantes de um lancamento cancelado."
        )
    attachment = repository.delete_attachment(transaction_id, attachment_id)
    if not attachment:
        raise FinanceNotFoundError("Comprovante nao encontrado.")
    attachment_service.delete_attachment_file(attachment["stored_name"])


def build_month_report(month: str | None) -> dict:
    normalized_month = validate_month(month)
    return {
        "month": normalized_month,
        "summary": repository.get_month_summary(normalized_month),
        "transactions": repository.list_transactions(
            month=normalized_month, status="ACTIVE"
        ),
    }
