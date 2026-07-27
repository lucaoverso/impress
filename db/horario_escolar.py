from ._proxy import proxy

atualizar_configuracao_aula = proxy("atualizar_configuracao_aula")
atualizar_aula_atividade_professor = proxy("atualizar_aula_atividade_professor")
buscar_horario_escolar_por_id = proxy("buscar_horario_escolar_por_id")
buscar_aula_atividade_professor_por_id = proxy("buscar_aula_atividade_professor_por_id")
buscar_configuracao_aula_por_id = proxy("buscar_configuracao_aula_por_id")
criar_aula_atividade_professor = proxy("criar_aula_atividade_professor")
criar_horario_escolar = proxy("criar_horario_escolar")
criar_configuracao_aula = proxy("criar_configuracao_aula")
excluir_aula_atividade_professor = proxy("excluir_aula_atividade_professor")
excluir_horario_escolar = proxy("excluir_horario_escolar")
listar_anos_letivos_horario_escolar = proxy("listar_anos_letivos_horario_escolar")
listar_aulas_atividade_professores = proxy("listar_aulas_atividade_professores")
listar_configuracoes_aulas = proxy("listar_configuracoes_aulas")
listar_horarios_escolares = proxy("listar_horarios_escolares")
atualizar_horario_escolar = proxy("atualizar_horario_escolar")

__all__ = [
    "atualizar_configuracao_aula",
    "atualizar_aula_atividade_professor",
    "buscar_horario_escolar_por_id",
    "buscar_aula_atividade_professor_por_id",
    "buscar_configuracao_aula_por_id",
    "criar_aula_atividade_professor",
    "criar_horario_escolar",
    "criar_configuracao_aula",
    "excluir_aula_atividade_professor",
    "excluir_horario_escolar",
    "listar_anos_letivos_horario_escolar",
    "listar_aulas_atividade_professores",
    "listar_configuracoes_aulas",
    "listar_horarios_escolares",
    "atualizar_horario_escolar",
]
