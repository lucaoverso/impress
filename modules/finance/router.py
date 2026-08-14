from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import FileResponse

from auth import get_usuario_logado
from modules.audit.models import AuditOutcome
from modules.audit.service import record_event
from routers.common import exigir_admin

from . import pdf_service, service
from .schemas import (
    FinanceAttachmentOut,
    FinanceTransactionCancelIn,
    FinanceTransactionCreateIn,
    FinanceTransactionOut,
    FinanceTransactionUpdateIn,
)


router = APIRouter(prefix="/api/admin/finance", tags=["Gestao financeira"])


def require_finance_admin(user=Depends(get_usuario_logado)) -> dict:
    return exigir_admin(user)


def _run(action: Callable[..., Any], *args, **kwargs):
    try:
        return action(*args, **kwargs)
    except service.FinanceNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except service.FinanceConflictError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except service.FinanceValidationError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


def _audit(user: dict, action: str, description: str, entity_id: int | None = None) -> None:
    record_event(
        category="finance",
        action=action,
        outcome=AuditOutcome.SUCCESS,
        actor=user,
        description=description,
        entity_type="finance_transaction",
        entity_id=entity_id,
    )


@router.get("/summary")
def finance_summary(
    month: str | None = None,
    user=Depends(require_finance_admin),
):
    return _run(service.get_month_overview, month)


@router.get("/transactions", response_model=list[FinanceTransactionOut])
def list_finance_transactions(
    month: str | None = None,
    transaction_status: str | None = Query(default=None, alias="status"),
    user=Depends(require_finance_admin),
):
    return _run(service.list_transactions, month=month, status=transaction_status)


@router.post(
    "/transactions",
    response_model=FinanceTransactionOut,
    status_code=status.HTTP_201_CREATED,
)
def create_finance_transaction(
    payload: FinanceTransactionCreateIn,
    user=Depends(require_finance_admin),
):
    item = _run(
        service.create_transaction,
        actor_user_id=int(user.get("id") or 0),
        payload=payload,
    )
    _audit(user, "finance.transaction.create", "Lancamento financeiro criado.", item["id"])
    return item


@router.put("/transactions/{transaction_id}", response_model=FinanceTransactionOut)
def update_finance_transaction(
    transaction_id: int,
    payload: FinanceTransactionUpdateIn,
    user=Depends(require_finance_admin),
):
    item = _run(service.update_transaction, transaction_id, payload)
    _audit(user, "finance.transaction.update", "Lancamento financeiro atualizado.", item["id"])
    return item


@router.post("/transactions/{transaction_id}/cancel", response_model=FinanceTransactionOut)
def cancel_finance_transaction(
    transaction_id: int,
    payload: FinanceTransactionCancelIn,
    user=Depends(require_finance_admin),
):
    item = _run(
        service.cancel_transaction,
        transaction_id,
        actor_user_id=int(user.get("id") or 0),
        reason=payload.reason,
    )
    _audit(user, "finance.transaction.cancel", "Lancamento financeiro cancelado.", item["id"])
    return item


@router.post(
    "/transactions/{transaction_id}/attachments",
    response_model=FinanceAttachmentOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_finance_attachment(
    transaction_id: int,
    file: UploadFile = File(...),
    user=Depends(require_finance_admin),
):
    content = await file.read(10 * 1024 * 1024 + 1)
    item = _run(
        service.add_attachment,
        transaction_id,
        content=content,
        original_filename=file.filename or "comprovante",
    )
    _audit(
        user,
        "finance.attachment.create",
        "Comprovante financeiro anexado.",
        transaction_id,
    )
    return item


@router.delete(
    "/transactions/{transaction_id}/attachments/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_finance_attachment(
    transaction_id: int,
    attachment_id: int,
    user=Depends(require_finance_admin),
):
    _run(service.remove_attachment, transaction_id, attachment_id)
    _audit(
        user,
        "finance.attachment.delete",
        "Comprovante financeiro removido.",
        transaction_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/attachments/{token}", response_class=FileResponse)
def download_finance_attachment(
    token: str,
    user=Depends(require_finance_admin),
):
    attachment, path = _run(service.get_attachment, token)
    return FileResponse(
        path,
        media_type=attachment["media_type"],
        filename=attachment["original_name"],
        headers={"Cache-Control": "private, no-store"},
    )


@router.get("/report.pdf")
def download_finance_report(
    month: str | None = None,
    user=Depends(require_finance_admin),
):
    report = _run(service.build_month_report, month)
    content = pdf_service.generate_month_report_pdf(report)
    _audit(user, "finance.report.generate", "Relatorio financeiro mensal gerado.")
    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="prestacao-contas-{report["month"]}.pdf"'
            ),
            "Cache-Control": "private, no-store",
        },
    )
