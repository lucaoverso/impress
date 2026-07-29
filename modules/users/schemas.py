from pydantic import BaseModel, Field


class ProfileUpdateIn(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=254)
    nova_senha: str = Field(default="", max_length=128)


class ProfileIdentityOut(BaseModel):
    id: int
    nome: str
    email: str
    cargo: str
    data_nascimento: str = ""
    turmas: list[str] = Field(default_factory=list)
    disciplinas: list[str] = Field(default_factory=list)


class ProfileScheduleSlotOut(BaseModel):
    aula_numero: int
    ordem_visual: int
    nome: str
    horario_inicio: str = ""
    horario_fim: str = ""


class ProfileScheduleItemOut(BaseModel):
    id: int
    dia_semana: str
    aula_numero: int
    faixa_global: int
    turma_id: int
    turma_nome: str
    turno: str = ""
    disciplina_id: int
    disciplina_nome: str
    tem_estudante_apoio: bool = False


class ProfileScheduleOut(BaseModel):
    ano_letivo: int
    dias_semana: list[dict[str, str]] = Field(default_factory=list)
    faixas: list[ProfileScheduleSlotOut] = Field(default_factory=list)
    itens: list[ProfileScheduleItemOut] = Field(default_factory=list)


class ProfileSubmissionOut(BaseModel):
    id: int
    arquivo: str
    turma_nome: str = ""
    disciplina_nome: str = ""
    enviado_em: str = ""
    status: str
    status_label: str


class ProfilePrintJobOut(BaseModel):
    id: int
    arquivo: str
    copias: int
    paginas_totais: int
    criado_em: str = ""
    status: str
    status_label: str


class ProfileBookingOut(BaseModel):
    id: int
    recurso_nome: str
    recurso_tipo: str = ""
    data: str
    aula: str = ""
    horario_inicio: str = ""
    horario_fim: str = ""
    turma: str = ""
    tema_aula: str = ""
    status: str
    status_label: str


class ProfileStudentSupportOut(BaseModel):
    id: int
    nome: str
    turma_id: int
    turma_nome: str
    apoios: list[str] = Field(default_factory=list)
    recomendacoes: list[str] = Field(default_factory=list)
    resumo_apoio: str


class ProfileStudentPreviewOut(BaseModel):
    total: int
    itens: list[ProfileStudentSupportOut] = Field(default_factory=list)


class TeacherDashboardOut(BaseModel):
    horario: ProfileScheduleOut
    estudantes: ProfileStudentPreviewOut
    envios_apc: list[ProfileSubmissionOut] = Field(default_factory=list)
    impressoes: list[ProfilePrintJobOut] = Field(default_factory=list)
    agendamentos: list[ProfileBookingOut] = Field(default_factory=list)


class ProfileOverviewOut(BaseModel):
    usuario: ProfileIdentityOut
    teacher_dashboard: TeacherDashboardOut | None = None


class ProfileStudentsOut(BaseModel):
    total: int
    itens: list[ProfileStudentSupportOut] = Field(default_factory=list)
