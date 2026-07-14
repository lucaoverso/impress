from fastapi import APIRouter, Depends

from auth import get_usuario_logado
from routers.common import (
    modulos_por_usuario,
    normalizar_cargo_usuario,
    usuario_eh_admin,
    usuario_eh_gestor,
    usuario_eh_professor,
    usuario_pode_gerir_impressoes,
    usuario_tem_acesso_coordenacao,
)

from .schemas import ProfileUpdateIn
from .service import update_own_profile

router = APIRouter()


@router.patch("/me/profile")
def update_profile(payload: ProfileUpdateIn, user=Depends(get_usuario_logado)):
    update_own_profile(user, payload)
    updated = dict(user)
    updated["nome"] = " ".join(payload.nome.split())
    updated["email"] = payload.email.strip().lower()
    updated["cargo"] = normalizar_cargo_usuario(updated)
    updated["modulos"] = modulos_por_usuario(updated)
    updated["eh_gestor"] = usuario_eh_gestor(updated)
    updated["eh_admin"] = usuario_eh_admin(updated)
    updated["eh_professor"] = usuario_eh_professor(updated)
    updated["tem_acesso_coordenacao"] = usuario_tem_acesso_coordenacao(updated)
    updated["pode_gerir_impressoes"] = usuario_pode_gerir_impressoes(updated)
    return updated
