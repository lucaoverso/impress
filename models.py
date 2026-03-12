from typing import Literal
from pydantic import BaseModel, Field

class JobCreate(BaseModel):
    copias: int

class JobOut(BaseModel):
    id: int
    arquivo: str
    copias: int
    status: str
    prioridade: int
    criado_em: str

class FilaOut(BaseModel):
    jobs: list[JobOut]

class LoginIn(BaseModel):
    email: str
    senha: str

class ProfessorRecuperarSenhaIn(BaseModel):
    email: str
    data_nascimento: str
    nova_senha: str

class ProfessorRedefinirSenhaAdminIn(BaseModel):
    nova_senha: str

class RadiusEnsureNtHashIn(BaseModel):
    username: str
    password: str

class UsuarioOut(BaseModel):
    id: int
    nome: str
    email: str
    perfil: str
    cargo: str = ""

class AgendamentoIn(BaseModel):
    recurso_id: int
    data: str
    aula: str
    turma: str
    tema_aula: str
    professor_id: int | None = None
    observacao: str = ""

class ProfessorCreateIn(BaseModel):
    nome: str
    email: str
    senha: str
    data_nascimento: str
    aulas_semanais: int = 0
    turmas: list[str] = Field(default_factory=list)
    disciplinas: list[str] = Field(default_factory=list)

class ProfessorUpdateIn(BaseModel):
    nome: str
    email: str
    data_nascimento: str
    aulas_semanais: int = 0
    turmas: list[str] = Field(default_factory=list)
    disciplinas: list[str] = Field(default_factory=list)

class CoordenadorCreateIn(BaseModel):
    nome: str
    email: str
    senha: str
    data_nascimento: str

class ProfessorCargaIn(BaseModel):
    aulas_semanais: int
    turmas_quantidade: int

class TurmaCreateIn(BaseModel):
    nome: str
    turno: str
    quantidade_estudantes: int = 0

class TurmaUpdateIn(BaseModel):
    turno: str
    quantidade_estudantes: int

class DisciplinaCreateIn(BaseModel):
    nome: str
    aulas_semanais: int = 0

class DisciplinaUpdateIn(BaseModel):
    aulas_semanais: int

class RecursoCreateIn(BaseModel):
    nome: str
    tipo: str
    descricao: str = ""
    quantidade_itens: int = 1

class RecursoUpdateIn(BaseModel):
    nome: str
    tipo: str
    descricao: str = ""
    quantidade_itens: int = 1

class RecursoStatusIn(BaseModel):
    ativo: bool

class RegrasCotaIn(BaseModel):
    base_paginas: int
    paginas_por_aula: int
    paginas_por_turma: int
    cota_mensal_escola: int

AcaoAplicadaOcorrencia = Literal[
    "orientacao_verbal",
    "advertencia",
    "chamada_responsavel",
    "encaminhamento_direcao",
    "registro_informativo",
]

StatusOcorrencia = Literal[
    "registrado",
    "em_acompanhamento",
    "aguardando_responsavel",
    "resolvido",
]

class OcorrenciaCreateIn(BaseModel):
    nome_estudante: str | None = None
    estudante_id: int | None = None
    turma_id: int
    professor_requerente: str | None = None
    professor_requerente_id: int | None = None
    disciplina: str
    data_ocorrencia: str
    aula: str
    horario_ocorrencia: str
    descricao: str
    acao_aplicada: AcaoAplicadaOcorrencia
    status: StatusOcorrencia | None = None

class OcorrenciaUpdateIn(BaseModel):
    nome_estudante: str | None = None
    estudante_id: int | None = None
    turma_id: int | None = None
    professor_requerente: str | None = None
    professor_requerente_id: int | None = None
    disciplina: str | None = None
    data_ocorrencia: str | None = None
    aula: str | None = None
    horario_ocorrencia: str | None = None
    descricao: str | None = None
    acao_aplicada: AcaoAplicadaOcorrencia | None = None
    status: StatusOcorrencia | None = None

class OcorrenciaOut(BaseModel):
    id: int
    nome_estudante: str
    estudante_id: int | None = None
    turma_id: int
    turma_nome: str = ""
    professor_requerente: str
    professor_requerente_id: int | None = None
    disciplina: str
    data_ocorrencia: str
    aula: str
    horario_ocorrencia: str
    descricao: str
    acao_aplicada: str
    status: str
    criado_em: str
    atualizado_em: str

class EstudanteCreateIn(BaseModel):
    nome: str
    turma_id: int

class EstudanteUpdateIn(BaseModel):
    nome: str
    turma_id: int
    ativo: bool = True

class EstudanteStatusIn(BaseModel):
    ativo: bool

class EstudanteOut(BaseModel):
    id: int
    nome: str
    turma_id: int
    turma_nome: str = ""
    ativo: int | bool
    criado_em: str
    atualizado_em: str
