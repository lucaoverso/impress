FAIXA_GLOBAL_OFFSET_POR_TURNO = {
    "MATUTINO": 0,
    "INTEGRAL": 0,
    "VESPERTINO": 5,
    "VESPERTINO_EM": 5,
}

TURNOS_CONFIG = {
    "INTEGRAL": {"nome": "Período integral", "aulas": 8},
    "MATUTINO": {"nome": "Matutino", "aulas": 5},
    "VESPERTINO": {"nome": "Vespertino", "aulas": 5},
    "VESPERTINO_EM": {"nome": "Vespertino E.M.", "aulas": 6},
}

__all__ = ["FAIXA_GLOBAL_OFFSET_POR_TURNO", "TURNOS_CONFIG"]
