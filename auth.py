from fastapi import APIRouter, HTTPException, Header
from models import LoginIn
from services.auth_service import autenticar_usuario, validar_token

router = APIRouter()

@router.post("/login")
def login(dados: LoginIn):
    resultado = autenticar_usuario(dados.email, dados.senha)

    if not resultado:
        raise HTTPException(401, "Credenciais inválidas")

    token, usuario = resultado
    return {
        "token": token,
        "perfil": usuario["perfil"]
    }

def get_usuario_logado(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Token inválido")

    token = authorization.replace("Bearer ", "")
    usuario = validar_token(token)

    if not usuario:
        raise HTTPException(401, "Token inválido")

    return usuario
