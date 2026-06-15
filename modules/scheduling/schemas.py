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
    descricao: str = ""
    quantidade_itens: int = 1
    imagem_capa: str = ""
    ativo: bool = True


class SchedulingTeacherOut(BaseModel):
    id: int
    nome: str
    email: str = ""


class SchedulingTurnoOption(BaseModel):
    id: str
    nome: str
    aulas: int


class SchedulingLessonConfigOut(BaseModel):
    id: int
    ordem_visual: int
    tipo: str
    aula_numero: int | None = None
    nome: str
    horario_inicio: str = ""
    horario_fim: str = ""
    ativo: bool = True
    periodo: str = ""
    faixa_global: int = 0
    label: str = ""
    label_curta: str = ""


class SchedulingLessonConfigIn(BaseModel):
    ordem_visual: int
    tipo: str
    aula_numero: int | None = None
    nome: str
    horario_inicio: str
    horario_fim: str
    ativo: bool = True


class SchedulingClassOption(BaseModel):
    nome: str
    turno: str
    turno_nome: str
    aulas: int
    turno_valido: bool
    quantidade_estudantes: int
    aula_inicial: int
    aula_final: int
    aulas_disponiveis: list[SchedulingLessonConfigOut]


class SchedulingOptionsOut(BaseModel):
    turnos: list[SchedulingTurnoOption]
    grade_aulas: list[SchedulingLessonConfigOut]
    aulas_globais: list[SchedulingLessonConfigOut]
    turmas: list[SchedulingClassOption]


class SchedulingReservationOut(BaseModel):
    id: int
    recurso_id: int
    recurso_nome: str
    recurso_tipo: str
    usuario_id: int
    professor_nome: str
    data: str
    turno: str
    aula: str
    faixa_global: int
    turma: str
    tema_aula: str
    observacao: str
    status: str
    criado_em: str | None = None
    cancelado_em: str | None = None


class SchedulingReservationResponse(BaseModel):
    mensagem: str
    agendamento_id: int


class SchedulingOperationResponse(BaseModel):
    mensagem: str
