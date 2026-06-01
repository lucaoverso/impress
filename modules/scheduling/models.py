from dataclasses import dataclass


@dataclass(frozen=True)
class SchedulingResource:
    id: int
    nome: str
    tipo: str
    ativo: bool


@dataclass(frozen=True)
class SchedulingReservation:
    id: int
    recurso_id: int
    usuario_id: int
    data: str
    turno: str
    aula: str
    faixa_global: int
    status: str
