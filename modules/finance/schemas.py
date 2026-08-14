from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


TransactionType = Literal["INCOME", "EXPENSE"]
TransactionStatus = Literal["ACTIVE", "CANCELED"]


class FinanceTransactionCreateIn(BaseModel):
    transaction_type: TransactionType
    occurred_on: date
    description: str = Field(min_length=1, max_length=180)
    category: str = Field(min_length=1, max_length=100)
    amount_cents: int = Field(gt=0, le=999_999_999_999)
    counterparty: str = Field(default="", max_length=160)
    notes: str = Field(default="", max_length=1000)


class FinanceTransactionUpdateIn(FinanceTransactionCreateIn):
    pass


class FinanceTransactionCancelIn(BaseModel):
    reason: str = Field(min_length=1, max_length=300)


class FinanceAttachmentOut(BaseModel):
    id: int
    transaction_id: int
    token: str
    original_name: str
    media_type: str
    size_bytes: int
    created_at: str


class FinanceTransactionOut(BaseModel):
    id: int
    created_by_user_id: int
    transaction_type: TransactionType
    occurred_on: str
    description: str
    category: str
    amount_cents: int
    counterparty: str
    notes: str
    status: TransactionStatus
    cancellation_reason: str
    canceled_by_user_id: int | None = None
    canceled_at: str | None = None
    created_at: str
    updated_at: str
    attachments: list[FinanceAttachmentOut] = Field(default_factory=list)
