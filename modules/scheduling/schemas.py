from pydantic import BaseModel


class SchedulingReservationCreate(BaseModel):
    recurso_id: int
    data: str
    aula: str
    turma: str
    tema_aula: str
    professor_id: int | None = None
    observacao: str = ""


class SchedulingResourceOption(BaseModel):
    id: int
    nome: str
    tipo: str
    ativo: bool = True


class SchedulingReservationResponse(BaseModel):
    mensagem: str
    agendamento_id: int
