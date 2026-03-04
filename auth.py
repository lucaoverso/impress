from fastapi import APIRouter, HTTPException, Header
from models import LoginIn
from services.auth_service import autenticar_usuario, validar_token, obter_ttl_token_dias

router = APIRouter()

def normalizar_cargo(usuario: dict) -> str:
    cargo = str(usuario.get("cargo") or "").strip().upper()
    if cargo:
        return cargo

    perfil = str(usuario.get("perfil") or "").strip().lower()
    if perfil == "admin":
        return "ADMIN"
    if perfil == "coordenador":
        return "COORDENADOR"
    return "PROFESSOR"

@router.post("/login")
def login(dados: LoginIn):
    resultado = autenticar_usuario(dados.email, dados.senha)

    if not resultado:
        raise HTTPException(401, "Credenciais inválidas")

    token, usuario, expira_em = resultado
    cargo = normalizar_cargo(usuario)
    return {
        "token": token,
        "perfil": usuario["perfil"],
        "cargo": cargo,
        "expira_em": expira_em,
        "token_ttl_dias": obter_ttl_token_dias()
    }

def get_usuario_logado(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Token inválido")

    token = authorization.replace("Bearer ", "")
    usuario = validar_token(token)

    if not usuario:
        raise HTTPException(401, "Token inválido")

    return usuario
