from pydantic import BaseModel, Field


class ProfileUpdateIn(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=254)
    nova_senha: str = Field(default="", max_length=128)
