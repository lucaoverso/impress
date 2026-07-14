from pydantic import BaseModel


class TurmaCreateIn(BaseModel):
    nome: str
    turno: str
    aula_inicial: int | None = None
    aula_final: int | None = None
    quantidade_estudantes: int = 0


class TurmaUpdateIn(BaseModel):
    turno: str
    aula_inicial: int | None = None
    aula_final: int | None = None
    quantidade_estudantes: int


class TurmaStatusIn(BaseModel):
    ativo: bool
