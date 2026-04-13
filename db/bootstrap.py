from ._proxy import proxy

criar_tabelas = proxy("criar_tabelas")
criar_usuario_se_nao_existir = proxy("criar_usuario_se_nao_existir")
seed_recursos_padrao = proxy("seed_recursos_padrao")

__all__ = [
    "criar_tabelas",
    "criar_usuario_se_nao_existir",
    "seed_recursos_padrao",
]
