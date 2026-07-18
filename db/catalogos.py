from ._proxy import proxy
from modules.admin.resources.repository import (
    atualizar_recurso_dados,
    atualizar_status_recurso,
    buscar_recurso_por_id,
    criar_recurso,
    listar_recursos,
    listar_recursos_ativos,
)
from modules.admin.classes.repository import (
    atualizar_status_turma,
    atualizar_turma_dados,
    buscar_turma_por_id,
    buscar_turma_por_nome,
    criar_turma,
    listar_turmas,
    listar_turmas_ativas,
)

atualizar_disciplina_dados = proxy("atualizar_disciplina_dados")
atualizar_status_disciplina = proxy("atualizar_status_disciplina")
buscar_disciplina_por_id = proxy("buscar_disciplina_por_id")
buscar_disciplina_por_nome = proxy("buscar_disciplina_por_nome")
criar_disciplina = proxy("criar_disciplina")
listar_disciplinas = proxy("listar_disciplinas")
listar_disciplinas_ativas = proxy("listar_disciplinas_ativas")

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
