from pydantic import BaseModel


class PrintTagOut(BaseModel):
    id: str
    label: str


class PrintStatusOut(BaseModel):
    sem_papel: bool
    mensagem: str
    atualizado_em: str


class PrintJobOut(BaseModel):
    id: int
    arquivo: str
    copias: int
    status: str
    prioridade: int
    criado_em: str


class PrintQuotaOut(BaseModel):
    limite: int | None
    usadas: int
    restante: int | None
    ilimitada: bool


class PrintingPrinterCreate(BaseModel):
    name: str


class PrintingPrinterStatusUpdate(BaseModel):
    active: bool
