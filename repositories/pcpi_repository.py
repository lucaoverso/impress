from db.pcpi import (
    buscar_registro_pcpi_manual_por_id as _buscar_registro_pcpi_manual_por_id,
    criar_registro_pcpi_manual as _criar_registro_pcpi_manual,
    listar_registros_pcpi_manuais as _listar_registros_pcpi_manuais,
)


def buscar_registro_pcpi_manual_por_id(registro_id: int):
    return _buscar_registro_pcpi_manual_por_id(registro_id)


def criar_registro_pcpi_manual(**dados):
    return _criar_registro_pcpi_manual(**dados)


def listar_registros_pcpi_manuais(*, data: str):
    return _listar_registros_pcpi_manuais(data=data)


__all__ = [
    "buscar_registro_pcpi_manual_por_id",
    "criar_registro_pcpi_manual",
    "listar_registros_pcpi_manuais",
]

