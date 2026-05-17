from ._proxy import proxy

gerar_dashboard_relatorios = proxy("gerar_dashboard_relatorios")
gerar_relatorio_anexos = proxy("gerar_relatorio_anexos")

__all__ = [
    "gerar_dashboard_relatorios",
    "gerar_relatorio_anexos",
]
