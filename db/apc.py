from ._proxy import proxy

buscar_apc_envio_por_id = proxy("buscar_apc_envio_por_id")
buscar_apc_envio_por_periodo_e_professor = proxy("buscar_apc_envio_por_periodo_e_professor")
buscar_apc_periodo_por_id = proxy("buscar_apc_periodo_por_id")
criar_apc_envio = proxy("criar_apc_envio")
criar_apc_periodo = proxy("criar_apc_periodo")
excluir_apc_periodo = proxy("excluir_apc_periodo")
listar_anos_letivos_apc = proxy("listar_anos_letivos_apc")
listar_apc_envios = proxy("listar_apc_envios")
listar_apc_periodos = proxy("listar_apc_periodos")
atualizar_apc_envio = proxy("atualizar_apc_envio")
atualizar_apc_periodo = proxy("atualizar_apc_periodo")

__all__ = [
    "buscar_apc_envio_por_id",
    "buscar_apc_envio_por_periodo_e_professor",
    "buscar_apc_periodo_por_id",
    "criar_apc_envio",
    "criar_apc_periodo",
    "excluir_apc_periodo",
    "listar_anos_letivos_apc",
    "listar_apc_envios",
    "listar_apc_periodos",
    "atualizar_apc_envio",
    "atualizar_apc_periodo",
]
