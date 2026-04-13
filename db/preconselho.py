from ._proxy import proxy

atualizar_motivo_pre_conselho_dados = proxy("atualizar_motivo_pre_conselho_dados")
atualizar_periodo_pre_conselho_dados = proxy("atualizar_periodo_pre_conselho_dados")
atualizar_status_motivo_pre_conselho = proxy("atualizar_status_motivo_pre_conselho")
atualizar_status_periodo_pre_conselho = proxy("atualizar_status_periodo_pre_conselho")
buscar_motivo_pre_conselho_por_id = proxy("buscar_motivo_pre_conselho_por_id")
buscar_motivos_pre_conselho_por_ids = proxy("buscar_motivos_pre_conselho_por_ids")
buscar_periodo_pre_conselho_por_id = proxy("buscar_periodo_pre_conselho_por_id")
buscar_registro_pre_conselho_por_id = proxy("buscar_registro_pre_conselho_por_id")
contar_registros_pre_conselho_por_professor_periodo = proxy(
    "contar_registros_pre_conselho_por_professor_periodo"
)
criar_motivo_pre_conselho = proxy("criar_motivo_pre_conselho")
criar_ou_atualizar_registro_pre_conselho = proxy("criar_ou_atualizar_registro_pre_conselho")
criar_periodo_pre_conselho = proxy("criar_periodo_pre_conselho")
excluir_registro_pre_conselho = proxy("excluir_registro_pre_conselho")
listar_estudantes_pre_conselho_painel = proxy("listar_estudantes_pre_conselho_painel")
listar_motivos_pre_conselho = proxy("listar_motivos_pre_conselho")
listar_periodos_pre_conselho = proxy("listar_periodos_pre_conselho")
listar_registros_pre_conselho = proxy("listar_registros_pre_conselho")

__all__ = [
    "atualizar_motivo_pre_conselho_dados",
    "atualizar_periodo_pre_conselho_dados",
    "atualizar_status_motivo_pre_conselho",
    "atualizar_status_periodo_pre_conselho",
    "buscar_motivo_pre_conselho_por_id",
    "buscar_motivos_pre_conselho_por_ids",
    "buscar_periodo_pre_conselho_por_id",
    "buscar_registro_pre_conselho_por_id",
    "contar_registros_pre_conselho_por_professor_periodo",
    "criar_motivo_pre_conselho",
    "criar_ou_atualizar_registro_pre_conselho",
    "criar_periodo_pre_conselho",
    "excluir_registro_pre_conselho",
    "listar_estudantes_pre_conselho_painel",
    "listar_motivos_pre_conselho",
    "listar_periodos_pre_conselho",
    "listar_registros_pre_conselho",
]
