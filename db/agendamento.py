from ._proxy import proxy

buscar_agendamento_por_id = proxy("buscar_agendamento_por_id")
cancelar_agendamento = proxy("cancelar_agendamento")
contar_agendamentos_ativos_faixa = proxy("contar_agendamentos_ativos_faixa")
criar_agendamento = proxy("criar_agendamento")
listar_agendamentos = proxy("listar_agendamentos")

__all__ = [
    "buscar_agendamento_por_id",
    "cancelar_agendamento",
    "contar_agendamentos_ativos_faixa",
    "criar_agendamento",
    "listar_agendamentos",
]
