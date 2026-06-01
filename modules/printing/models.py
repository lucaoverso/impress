from dataclasses import dataclass


@dataclass(frozen=True)
class PrintJobSummary:
    id: int
    arquivo: str
    copias: int
    status: str
    prioridade: int
    criado_em: str


@dataclass(frozen=True)
class PrintQuotaSnapshot:
    limite: int | None
    usadas: int
    restante: int | None
    ilimitada: bool
