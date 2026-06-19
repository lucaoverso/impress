from typing import Literal

from pydantic import BaseModel


class ApcReviewUpdateIn(BaseModel):
    status: Literal["PENDENTE", "APROVADO", "IMPRESSO", "AJUSTE_SOLICITADO"]
    mensagem: str = ""
