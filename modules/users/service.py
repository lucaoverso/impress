import re

from fastapi import HTTPException

from routers.common import validar_senha_forte
from services.auth_service import hash_senha
from security.nt_hash import generate_nt_hash

from . import repository
from .schemas import ProfileUpdateIn

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+$")


def update_own_profile(user: dict, payload: ProfileUpdateIn) -> None:
    name = " ".join(payload.nome.split())
    email = payload.email.strip().lower()
    password = payload.nova_senha.strip()

    if len(name) < 2:
        raise HTTPException(400, "Informe seu nome.")
    if not EMAIL_RE.fullmatch(email):
        raise HTTPException(400, "Informe um e-mail válido.")
    if repository.email_belongs_to_another_user(email, int(user["id"])):
        raise HTTPException(409, "Este e-mail já está em uso.")

    password_hash = None
    nt_hash = None
    if password:
        validar_senha_forte(password)
        password_hash = hash_senha(password)
        nt_hash = generate_nt_hash(password)

    if not repository.update_profile(
        int(user["id"]), name, email, password_hash=password_hash, nt_hash=nt_hash
    ):
        raise HTTPException(404, "Usuário não encontrado.")
