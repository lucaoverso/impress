TURNOS_CONFIG = {
    "INTEGRAL": {"nome": "Período integral", "aulas": 8},
    "MATUTINO": {"nome": "Matutino", "aulas": 5},
    "VESPERTINO": {"nome": "Vespertino", "aulas": 5},
    "VESPERTINO_EM": {"nome": "Vespertino E.M.", "aulas": 6},
}
JANELA_AULAS_PADRAO_POR_TURNO = {
    "MATUTINO": (1, 5),
    "VESPERTINO": (6, 10),
    "VESPERTINO_EM": (6, 11),
    "INTEGRAL": (1, 8),
}

__all__ = ["JANELA_AULAS_PADRAO_POR_TURNO", "TURNOS_CONFIG"]
