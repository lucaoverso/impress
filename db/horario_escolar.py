from ._proxy import proxy

buscar_horario_escolar_por_id = proxy("buscar_horario_escolar_por_id")
criar_horario_escolar = proxy("criar_horario_escolar")
excluir_horario_escolar = proxy("excluir_horario_escolar")
listar_anos_letivos_horario_escolar = proxy("listar_anos_letivos_horario_escolar")
listar_horarios_escolares = proxy("listar_horarios_escolares")
atualizar_horario_escolar = proxy("atualizar_horario_escolar")

__all__ = [
    "buscar_horario_escolar_por_id",
    "criar_horario_escolar",
    "excluir_horario_escolar",
    "listar_anos_letivos_horario_escolar",
    "listar_horarios_escolares",
    "atualizar_horario_escolar",
]
