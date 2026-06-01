from db.usuarios import buscar_usuario_por_id
from routers.common import (
    exigir_gestor as require_print_manager,
    resolver_usuario_professor_selecionado as resolve_print_teacher,
    usuario_pode_gerir_impressoes as user_can_manage_prints,
    usuario_tem_cota_ilimitada as user_has_unlimited_quota,
)

__all__ = [
    "buscar_usuario_por_id",
    "require_print_manager",
    "resolve_print_teacher",
    "user_can_manage_prints",
    "user_has_unlimited_quota",
]
