from fastapi import HTTPException

from db.usuarios import buscar_usuario_por_id
from routers.common import (
    exigir_gestor as require_print_manager,
    resolver_usuario_professor_selecionado,
    usuario_eh_gestor,
    usuario_tem_cota_ilimitada as user_has_unlimited_quota,
)


def user_can_manage_prints(usuario: dict) -> bool:
    return usuario_eh_gestor(usuario)


def resolve_print_teacher(
    usuario: dict,
    professor_id: int | None,
    *,
    contexto: str,
    permitir_professor_com_acesso_coordenacao: bool = False,
) -> dict:
    if professor_id is not None and not user_can_manage_prints(usuario):
        raise HTTPException(
            403,
            f"Apenas administradores e coordenadores podem selecionar o professor {contexto}.",
        )

    return resolver_usuario_professor_selecionado(
        usuario,
        professor_id,
        contexto=contexto,
        permitir_professor_com_acesso_coordenacao=True,
    )


__all__ = [
    "buscar_usuario_por_id",
    "require_print_manager",
    "resolve_print_teacher",
    "user_can_manage_prints",
    "user_has_unlimited_quota",
]
