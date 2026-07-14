from pydantic import BaseModel


class RecursoCreateIn(BaseModel):
    nome: str
    tipo: str
    descricao: str = ""
    quantidade_itens: int = 1
    imagem_capa: str = ""


class RecursoUpdateIn(RecursoCreateIn):
    pass


class RecursoStatusIn(BaseModel):
    ativo: bool
