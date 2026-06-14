from ._proxy import proxy

atualizar_configuracao_aula = proxy("atualizar_configuracao_aula")
buscar_horario_escolar_por_id = proxy("buscar_horario_escolar_por_id")
buscar_configuracao_aula_por_id = proxy("buscar_configuracao_aula_por_id")
criar_horario_escolar = proxy("criar_horario_escolar")
criar_configuracao_aula = proxy("criar_configuracao_aula")
excluir_horario_escolar = proxy("excluir_horario_escolar")
listar_anos_letivos_horario_escolar = proxy("listar_anos_letivos_horario_escolar")
listar_configuracoes_aulas = proxy("listar_configuracoes_aulas")
listar_horarios_escolares = proxy("listar_horarios_escolares")
atualizar_horario_escolar = proxy("atualizar_horario_escolar")

__all__ = [
    "atualizar_configuracao_aula",
    "buscar_horario_escolar_por_id",
    "buscar_configuracao_aula_por_id",
    "criar_horario_escolar",
    "criar_configuracao_aula",
    "excluir_horario_escolar",
    "listar_anos_letivos_horario_escolar",
    "listar_configuracoes_aulas",
    "listar_horarios_escolares",
    "atualizar_horario_escolar",
]
