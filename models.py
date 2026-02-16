from pydantic import BaseModel
from datetime import datetime
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


