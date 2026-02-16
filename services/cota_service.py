from datetime import datetime
from database import buscar_cota, criar_cota, consumir_cota

LIMITE_PADRAO = 100  # páginas/mês

def validar_e_consumir_cota(usuario_id: int, paginas: int):
    mes_atual = datetime.now().strftime("%Y-%m")

    cota = buscar_cota(usuario_id, mes_atual)

    if not cota:
        criar_cota(usuario_id, mes_atual, LIMITE_PADRAO)
        cota = buscar_cota(usuario_id, mes_atual)

        if not cota:
            raise Exception("Erro ao criar cota")

        restante = cota["limite_paginas"] - cota["usadas_paginas"]
        
    if paginas > restante:
        return False, restante

    consumir_cota(cota["id"], paginas)
    return True, restante - paginas
