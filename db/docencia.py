from ._proxy import proxy

atualizar_turma_disciplina = proxy("atualizar_turma_disciplina")
criar_atribuicao_docente = proxy("criar_atribuicao_docente")
criar_ou_atualizar_turma_disciplina = proxy("criar_ou_atualizar_turma_disciplina")
excluir_atribuicao_docente = proxy("excluir_atribuicao_docente")
excluir_turma_disciplina = proxy("excluir_turma_disciplina")
listar_atribuicoes_docentes = proxy("listar_atribuicoes_docentes")
listar_atribuicoes_docentes_por_usuario_ids = proxy("listar_atribuicoes_docentes_por_usuario_ids")
listar_turmas_disciplinas_admin = proxy("listar_turmas_disciplinas_admin")
salvar_carga_professor = proxy("salvar_carga_professor")
sincronizar_atribuicoes_docentes_professor_disciplina = proxy(
    "sincronizar_atribuicoes_docentes_professor_disciplina"
)

__all__ = [
    "atualizar_turma_disciplina",
    "criar_atribuicao_docente",
    "criar_ou_atualizar_turma_disciplina",
    "excluir_atribuicao_docente",
    "excluir_turma_disciplina",
    "listar_atribuicoes_docentes",
    "listar_atribuicoes_docentes_por_usuario_ids",
    "listar_turmas_disciplinas_admin",
    "salvar_carga_professor",
    "sincronizar_atribuicoes_docentes_professor_disciplina",
]
