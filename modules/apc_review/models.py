from enum import StrEnum


class ApcReviewStatus(StrEnum):
    PENDING = "PENDENTE"
    APPROVED = "APROVADO"
    PRINTED = "IMPRESSO"
    ADJUSTMENT_REQUIRED = "AJUSTE_SOLICITADO"
