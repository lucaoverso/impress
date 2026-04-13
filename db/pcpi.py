from ._proxy import proxy

buscar_registro_pcpi_manual_por_id = proxy("buscar_registro_pcpi_manual_por_id")
criar_registro_pcpi_manual = proxy("criar_registro_pcpi_manual")
listar_registros_pcpi_manuais = proxy("listar_registros_pcpi_manuais")

__all__ = [
    "buscar_registro_pcpi_manual_por_id",
    "criar_registro_pcpi_manual",
    "listar_registros_pcpi_manuais",
]
