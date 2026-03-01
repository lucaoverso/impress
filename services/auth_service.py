import uuid
import hashlib
from datetime import datetime, timedelta
from database import (
    buscar_usuario_por_email,
    salvar_token,
    buscar_usuario_por_token,
    limpar_tokens_expirados,
    TOKEN_TTL_DIAS
)

def hash_senha(senha: str) -> str:
    return hashlib.sha256(senha.encode()).hexdigest()

def autenticar_usuario(email: str, senha: str):
    usuario = buscar_usuario_por_email(email)

    if not usuario:
        return None

    if hash_senha(senha) != usuario["senha_hash"]:
        return None

    limpar_tokens_expirados()
    token = str(uuid.uuid4())
    expira_em = (datetime.utcnow() + timedelta(days=TOKEN_TTL_DIAS)).strftime("%Y-%m-%d %H:%M:%S")
    salvar_token(token, usuario["id"], expira_em)

    return token, usuario, expira_em

def validar_token(token: str):
    return buscar_usuario_por_token(token)

def obter_ttl_token_dias() -> int:
    return TOKEN_TTL_DIAS
