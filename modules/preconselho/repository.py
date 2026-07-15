"""Repository boundary for pre-conselho persistence and lookups."""

from db.catalogos import (
    buscar_disciplina_por_id,
    buscar_turma_por_id,
    listar_disciplinas_ativas,
    listar_turmas_ativas,
)
from db.docencia import (
    listar_atribuicoes_docentes,
    listar_atribuicoes_docentes_por_usuario_ids,
    listar_turmas_disciplinas_admin,
)
from db.ocorrencias import buscar_estudante_por_id, listar_estudantes
from db.preconselho import (
    atualizar_habilidade_rav_pre_conselho_dados,
    atualizar_motivo_pre_conselho_dados,
    atualizar_periodo_pre_conselho_dados,
    atualizar_reavaliacao_registro_pre_conselho,
    atualizar_status_habilidade_rav_pre_conselho,
    atualizar_status_motivo_pre_conselho,
    atualizar_status_periodo_pre_conselho,
    buscar_habilidade_rav_pre_conselho_por_id,
    buscar_habilidade_rav_pre_conselho_por_chave,
    buscar_habilidades_rav_pre_conselho_por_ids,
    buscar_motivo_pre_conselho_por_id,
    buscar_motivos_pre_conselho_por_ids,
    buscar_periodo_pre_conselho_por_id,
    buscar_registro_pre_conselho_por_id,
    contar_registros_pre_conselho_por_professor_periodo,
    criar_habilidade_rav_pre_conselho,
    criar_motivo_pre_conselho,
    criar_ou_atualizar_registro_pre_conselho,
    criar_periodo_pre_conselho,
    excluir_registro_pre_conselho,
    listar_estudantes_pre_conselho_painel,
    listar_habilidades_rav_pre_conselho,
    listar_motivos_pre_conselho,
    listar_motivos_reavaliacao_pre_conselho,
    buscar_motivo_reavaliacao_pre_conselho_por_id,
    criar_motivo_reavaliacao_pre_conselho,
    atualizar_motivo_reavaliacao_pre_conselho,
    atualizar_status_motivo_reavaliacao_pre_conselho,
    listar_periodos_pre_conselho,
    listar_rav_pre_conselho_por_turma,
    listar_registros_pre_conselho,
)
from db.usuarios import (
    buscar_usuario_por_id,
    listar_cargas_professores_por_usuario_ids,
    listar_professores_agendamento,
)
from db._proxy import get_database_attr


def get_discipline(disciplina_id: int):
    return buscar_disciplina_por_id(disciplina_id)


def get_classroom(turma_id: int):
    return buscar_turma_por_id(turma_id)


def list_active_disciplines():
    return listar_disciplinas_ativas()


def list_active_classrooms():
    return listar_turmas_ativas()


def list_teacher_assignments(
    *,
    turma_id: int | None = None,
    classroom_id: int | None = None,
    incluir_inativos: bool = False,
):
    turma_consulta = turma_id if turma_id is not None else classroom_id
    return listar_atribuicoes_docentes(
        turma_id=turma_consulta,
        incluir_inativos=incluir_inativos,
    )


def list_teacher_assignments_by_user_ids(
    usuario_ids: list[int] | tuple[int, ...], *, incluir_inativos: bool = False
):
    return listar_atribuicoes_docentes_por_usuario_ids(
        usuario_ids, incluir_inativos=incluir_inativos
    )


def list_admin_classroom_disciplines(
    *,
    turma_ids: list[int] | None = None,
    classroom_id: int | None = None,
    incluir_inativos: bool = False,
):
    turma_consulta = None
    if turma_ids:
        turma_consulta = int(turma_ids[0])
    elif classroom_id is not None:
        turma_consulta = int(classroom_id)
    return listar_turmas_disciplinas_admin(
        turma_id=turma_consulta,
        incluir_inativos=incluir_inativos,
    )


def get_student(estudante_id: int):
    return buscar_estudante_por_id(estudante_id)


def list_students(*, nome: str = "", incluir_inativos: bool = False, turma_id: int | None = None):
    return listar_estudantes(nome=nome, incluir_inativos=incluir_inativos, turma_id=turma_id)


def list_students_with_special_needs(*, turma_id: int | None = None) -> list[dict]:
    conn = get_database_attr("get_connection")()
    cursor = conn.cursor()
    query = """
        SELECT e.id AS estudante_id, e.nome AS estudante_nome, e.sexo,
               e.turma_id, COALESCE(t.nome, '') AS turma_nome,
               l.id AS laudo_id, l.condicao_necessidade, l.classificacao,
               l.sistema_classificacao, l.codigo_laudo, l.descricao_laudo,
               l.relato_professora_apoio, l.recomendacoes_pedagogicas,
               a.id AS apoio_id, a.tipo AS apoio_tipo, a.nome AS apoio_nome
        FROM estudantes e
        LEFT JOIN estudante_laudos l ON l.estudante_id = e.id AND l.ativo = 1
        LEFT JOIN turmas t ON t.id = e.turma_id
        LEFT JOIN estudante_laudo_apoios la ON la.laudo_id = l.id
        LEFT JOIN estudante_apoios_catalogo a ON a.id = la.apoio_id AND a.ativo = 1
        WHERE e.ativo = 1
          AND e.possui_professor_apoio = 1
    """
    params = []
    if turma_id is not None:
        query += " AND e.turma_id = ?"
        params.append(int(turma_id))
    query += " ORDER BY t.nome COLLATE NOCASE, e.nome COLLATE NOCASE, l.id, a.nome COLLATE NOCASE"
    cursor.execute(query, params)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def update_reason_data(*args, **kwargs):
    return atualizar_motivo_pre_conselho_dados(*args, **kwargs)


def update_rav_skill_data(*args, **kwargs):
    return atualizar_habilidade_rav_pre_conselho_dados(*args, **kwargs)


def update_period_data(*args, **kwargs):
    return atualizar_periodo_pre_conselho_dados(*args, **kwargs)


def update_reason_status(motivo_id: int, ativo: bool):
    return atualizar_status_motivo_pre_conselho(motivo_id, ativo)


def update_rav_skill_status(habilidade_id: int, ativo: bool):
    return atualizar_status_habilidade_rav_pre_conselho(habilidade_id, ativo)


def update_period_status(periodo_id: int, status: str):
    return atualizar_status_periodo_pre_conselho(periodo_id, status)


def update_record_review(registro_id: int, **kwargs):
    return atualizar_reavaliacao_registro_pre_conselho(registro_id, **kwargs)


def get_reason(motivo_id: int):
    return buscar_motivo_pre_conselho_por_id(motivo_id)


def get_rav_skill(habilidade_id: int):
    return buscar_habilidade_rav_pre_conselho_por_id(habilidade_id)


def get_rav_skill_by_key(*args, **kwargs):
    return buscar_habilidade_rav_pre_conselho_por_chave(*args, **kwargs)


def get_reasons_by_ids(motivo_ids: list[int] | tuple[int, ...]):
    return buscar_motivos_pre_conselho_por_ids(motivo_ids)


def get_rav_skills_by_ids(habilidade_ids: list[int] | tuple[int, ...]):
    return buscar_habilidades_rav_pre_conselho_por_ids(habilidade_ids)


def get_period(periodo_id: int):
    return buscar_periodo_pre_conselho_por_id(periodo_id)


def get_record(registro_id: int):
    return buscar_registro_pre_conselho_por_id(registro_id)


def count_records_by_teacher_and_period(*, professor_id: int, periodo_id: int):
    return contar_registros_pre_conselho_por_professor_periodo(professor_id, periodo_id)


def create_reason(*args, **kwargs):
    return criar_motivo_pre_conselho(*args, **kwargs)


def create_rav_skill(*args, **kwargs):
    return criar_habilidade_rav_pre_conselho(*args, **kwargs)


def save_record(*args, **kwargs):
    return criar_ou_atualizar_registro_pre_conselho(*args, **kwargs)


def create_period(*args, **kwargs):
    return criar_periodo_pre_conselho(*args, **kwargs)


def delete_record(*args, **kwargs):
    return excluir_registro_pre_conselho(*args, **kwargs)


def list_panel_students(*args, **kwargs):
    return listar_estudantes_pre_conselho_painel(*args, **kwargs)


def list_reasons(*, incluir_inativos: bool = False):
    return listar_motivos_pre_conselho(incluir_inativos=incluir_inativos)


def list_review_reasons(*, incluir_inativos: bool = False):
    return listar_motivos_reavaliacao_pre_conselho(incluir_inativos=incluir_inativos)


def get_review_reason(motivo_id: int):
    return buscar_motivo_reavaliacao_pre_conselho_por_id(motivo_id)


def create_review_reason(**kwargs):
    return criar_motivo_reavaliacao_pre_conselho(**kwargs)


def update_review_reason(motivo_id: int, **kwargs):
    return atualizar_motivo_reavaliacao_pre_conselho(motivo_id, **kwargs)


def update_review_reason_status(motivo_id: int, ativo: bool):
    return atualizar_status_motivo_reavaliacao_pre_conselho(motivo_id, ativo)


def list_rav_skills(
    *,
    periodo_id: int | None = None,
    disciplina_id: int | None = None,
    turma_id: int | None = None,
    incluir_inativos: bool = False,
):
    return listar_habilidades_rav_pre_conselho(
        periodo_id=periodo_id,
        disciplina_id=disciplina_id,
        turma_id=turma_id,
        incluir_inativos=incluir_inativos,
    )


def list_periods():
    return listar_periodos_pre_conselho()


def list_records(*args, **kwargs):
    return listar_registros_pre_conselho(*args, **kwargs)


def list_rav_by_classroom(*args, **kwargs):
    return listar_rav_pre_conselho_por_turma(*args, **kwargs)


def get_user(usuario_id: int):
    return buscar_usuario_por_id(usuario_id)


def list_teacher_workloads_by_user_ids(usuario_ids: list[int] | tuple[int, ...]):
    return listar_cargas_professores_por_usuario_ids(usuario_ids)


def list_available_teachers():
    return listar_professores_agendamento()
