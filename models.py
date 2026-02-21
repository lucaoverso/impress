from pydantic import BaseModel

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

class UsuarioOut(BaseModel):
    id: int
    nome: str
    email: str
    perfil: str

class AgendamentoIn(BaseModel):
    recurso_id: int
    data: str
    turno: str
    aula: str
    turma: str
    observacao: str = ""

class ProfessorCreateIn(BaseModel):
    nome: str
    email: str
    senha: str
    aulas_semanais: int = 0
    turmas_quantidade: int = 0

class ProfessorCargaIn(BaseModel):
    aulas_semanais: int
    turmas_quantidade: int

class RecursoCreateIn(BaseModel):
    nome: str
    tipo: str
    descricao: str = ""

class RecursoStatusIn(BaseModel):
    ativo: bool

class RegrasCotaIn(BaseModel):
    base_paginas: int
    paginas_por_aula: int
    paginas_por_turma: int
