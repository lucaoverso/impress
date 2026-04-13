from ._proxy import proxy

atualizar_disciplina_dados = proxy("atualizar_disciplina_dados")
atualizar_recurso_dados = proxy("atualizar_recurso_dados")
atualizar_status_disciplina = proxy("atualizar_status_disciplina")
atualizar_status_recurso = proxy("atualizar_status_recurso")
atualizar_status_turma = proxy("atualizar_status_turma")
atualizar_turma_dados = proxy("atualizar_turma_dados")
buscar_disciplina_por_id = proxy("buscar_disciplina_por_id")
buscar_disciplina_por_nome = proxy("buscar_disciplina_por_nome")
buscar_recurso_por_id = proxy("buscar_recurso_por_id")
buscar_turma_por_id = proxy("buscar_turma_por_id")
buscar_turma_por_nome = proxy("buscar_turma_por_nome")
criar_disciplina = proxy("criar_disciplina")
criar_recurso = proxy("criar_recurso")
criar_turma = proxy("criar_turma")
listar_disciplinas = proxy("listar_disciplinas")
listar_disciplinas_ativas = proxy("listar_disciplinas_ativas")
listar_recursos = proxy("listar_recursos")
listar_recursos_ativos = proxy("listar_recursos_ativos")
listar_turmas = proxy("listar_turmas")
listar_turmas_ativas = proxy("listar_turmas_ativas")

__all__ = [
    "atualizar_disciplina_dados",
    "atualizar_recurso_dados",
    "atualizar_status_disciplina",
    "atualizar_status_recurso",
    "atualizar_status_turma",
    "atualizar_turma_dados",
    "buscar_disciplina_por_id",
    "buscar_disciplina_por_nome",
    "buscar_recurso_por_id",
    "buscar_turma_por_id",
    "buscar_turma_por_nome",
    "criar_disciplina",
    "criar_recurso",
    "criar_turma",
    "listar_disciplinas",
    "listar_disciplinas_ativas",
    "listar_recursos",
    "listar_recursos_ativos",
    "listar_turmas",
    "listar_turmas_ativas",
]
