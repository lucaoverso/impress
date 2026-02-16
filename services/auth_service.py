import uuid
import hashlib
from database import (
    buscar_usuario_por_email,
    salvar_token,
    buscar_usuario_por_token
)

def hash_senha(senha: str) -> str:
    return hashlib.sha256(senha.encode()).hexdigest()

def autenticar_usuario(email: str, senha: str):
    usuario = buscar_usuario_por_email(email)

    if not usuario:
        return None

    if hash_senha(senha) != usuario["senha_hash"]:
        return None

    token = str(uuid.uuid4())
    salvar_token(token, usuario["id"])

    return token, usuario

def validar_token(token: str):
    return buscar_usuario_por_token(token)
