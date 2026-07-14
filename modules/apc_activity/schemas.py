from typing import Literal

from pydantic import BaseModel, Field


class ApcActivityIn(BaseModel):
    turma_id: int = 0
    disciplina_id: int = 0
    habilidade: str = Field(min_length=1, max_length=2080)
    conteudo: str = Field(min_length=1, max_length=1000)
    corpo_html: str = Field(min_length=1, max_length=90000)
    activity_columns: Literal[1, 2] = 1


class ApcActivityPreviewIn(BaseModel):
    turma_id: int = 0
    disciplina_id: int = 0
    habilidade: str = Field(default="", max_length=2080)
    conteudo: str = Field(default="", max_length=1000)
    corpo_html: str = Field(default="", max_length=90000)
    activity_columns: Literal[1, 2] = 1


class ApcActivityOut(BaseModel):
    envio: dict
    atividade: dict
