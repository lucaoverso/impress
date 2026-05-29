from ._proxy import get_database_attr, proxy

TOKEN_TTL_DIAS = get_database_attr("TOKEN_TTL_DIAS")
atualizar_professor = proxy("atualizar_professor")
atualizar_senha_usuario = proxy("atualizar_senha_usuario")
buscar_usuario_por_email = proxy("buscar_usuario_por_email")
buscar_usuario_por_id = proxy("buscar_usuario_por_id")
buscar_usuario_por_token = proxy("buscar_usuario_por_token")
criar_coordenador = proxy("criar_coordenador")
criar_professor = proxy("criar_professor")
criar_usuario = proxy("criar_usuario")
criar_usuario_se_nao_existir = proxy("criar_usuario_se_nao_existir")
desativar_professor = proxy("desativar_professor")
promover_professor_para_coordenador = proxy("promover_professor_para_coordenador")
hash_senha = proxy("hash_senha")
limpar_tokens_expirados = proxy("limpar_tokens_expirados")
listar_cargas_professores_por_usuario_ids = proxy("listar_cargas_professores_por_usuario_ids")
listar_coordenadores_admin = proxy("listar_coordenadores_admin")
listar_professores_admin = proxy("listar_professores_admin")
listar_professores_agendamento = proxy("listar_professores_agendamento")
preencher_nt_hash_se_ausente = proxy("preencher_nt_hash_se_ausente")
revogar_tokens_usuario = proxy("revogar_tokens_usuario")
salvar_token = proxy("salvar_token")

__all__ = [
    "TOKEN_TTL_DIAS",
    "atualizar_professor",
    "atualizar_senha_usuario",
    "buscar_usuario_por_email",
    "buscar_usuario_por_id",
    "buscar_usuario_por_token",
    "criar_coordenador",
    "criar_professor",
    "criar_usuario",
    "criar_usuario_se_nao_existir",
    "desativar_professor",
    "promover_professor_para_coordenador",
    "hash_senha",
    "limpar_tokens_expirados",
    "listar_cargas_professores_por_usuario_ids",
    "listar_coordenadores_admin",
    "listar_professores_admin",
    "listar_professores_agendamento",
    "preencher_nt_hash_se_ausente",
    "revogar_tokens_usuario",
    "salvar_token",
]
