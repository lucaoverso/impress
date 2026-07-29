from fastapi import APIRouter, Depends, Request

from auth import get_usuario_logado
from routers.config import render_template_response
from routers.common import (
    modulos_por_usuario,
    normalizar_cargo_usuario,
    usuario_eh_admin,
    usuario_eh_gestor,
    usuario_eh_professor,
    usuario_pode_gerir_impressoes,
    usuario_tem_acesso_coordenacao,
)

from .schemas import ProfileOverviewOut, ProfileStudentsOut, ProfileUpdateIn
from .service import get_own_profile_overview, list_own_profile_students, update_own_profile

router = APIRouter()


@router.get("/meu-perfil")
def profile_page(request: Request):
    return render_template_response(
        request,
        "users/profile.html",
        cache_control="no-store",
    )


@router.get("/me/profile/overview", response_model=ProfileOverviewOut)
def profile_overview(user=Depends(get_usuario_logado)):
    return get_own_profile_overview(user)


@router.get("/me/profile/students", response_model=ProfileStudentsOut)
def profile_students(user=Depends(get_usuario_logado)):
    return list_own_profile_students(user)


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
