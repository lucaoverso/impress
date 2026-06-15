from enum import StrEnum


class ApcReviewStatus(StrEnum):
    PENDING = "PENDENTE"
    APPROVED = "APROVADO"
    ADJUSTMENT_REQUIRED = "AJUSTE_SOLICITADO"
