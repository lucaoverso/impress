from datetime import datetime
from database import (
    buscar_cota,
    criar_cota,
    consumir_cota,
    buscar_cota_do_usuario,
    calcular_limite_cota_usuario
)

LIMITE_PADRAO = 100

def _obter_limite_usuario(usuario_id: int) -> int:
    try:
        limite = int(calcular_limite_cota_usuario(usuario_id))
        return max(limite, 0)
    except Exception:
        return LIMITE_PADRAO

def validar_e_consumir_cota(usuario_id: int, paginas: int):
    mes_atual = datetime.now().strftime("%Y-%m")

    cota = buscar_cota(usuario_id, mes_atual)

    if not cota:
        criar_cota(usuario_id, mes_atual, _obter_limite_usuario(usuario_id))
        cota = buscar_cota(usuario_id, mes_atual)

        if not cota:
            # erro grave de banco
            raise Exception("Erro ao criar cota")

    limite = int(cota["limite_paginas"])
    usadas = int(cota["usadas_paginas"])

    restante = limite - usadas

    if paginas > restante:
        return False, restante

    consumir_cota(cota["id"], paginas)
    return True, restante - paginas

def obter_cota_atual(usuario_id: int):
    mes_atual = datetime.now().strftime("%Y-%m")

    cota = buscar_cota_do_usuario(usuario_id, mes_atual)

    if not cota:
        criar_cota(usuario_id, mes_atual, _obter_limite_usuario(usuario_id))
        cota = buscar_cota_do_usuario(usuario_id, mes_atual)

    restante = cota["limite_paginas"] - cota["usadas_paginas"]

    return {
        "limite": cota["limite_paginas"],
        "usadas": cota["usadas_paginas"],
        "restante": restante
    }
