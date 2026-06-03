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
    atualizar_motivo_pre_conselho_dados,
    atualizar_periodo_pre_conselho_dados,
    atualizar_status_motivo_pre_conselho,
    atualizar_status_periodo_pre_conselho,
    buscar_motivo_pre_conselho_por_id,
    buscar_motivos_pre_conselho_por_ids,
    buscar_periodo_pre_conselho_por_id,
    buscar_registro_pre_conselho_por_id,
    contar_registros_pre_conselho_por_professor_periodo,
    criar_motivo_pre_conselho,
    criar_ou_atualizar_registro_pre_conselho,
    criar_periodo_pre_conselho,
    excluir_registro_pre_conselho,
    listar_estudantes_pre_conselho_painel,
    listar_motivos_pre_conselho,
    listar_periodos_pre_conselho,
    listar_registros_pre_conselho,
)
from db.usuarios import (
    buscar_usuario_por_id,
    listar_cargas_professores_por_usuario_ids,
    listar_professores_agendamento,
)


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


def update_reason_data(*args, **kwargs):
    return atualizar_motivo_pre_conselho_dados(*args, **kwargs)


def update_period_data(*args, **kwargs):
    return atualizar_periodo_pre_conselho_dados(*args, **kwargs)


def update_reason_status(motivo_id: int, ativo: bool):
    return atualizar_status_motivo_pre_conselho(motivo_id, ativo)


def update_period_status(periodo_id: int, status: str):
    return atualizar_status_periodo_pre_conselho(periodo_id, status)


def get_reason(motivo_id: int):
    return buscar_motivo_pre_conselho_por_id(motivo_id)


def get_reasons_by_ids(motivo_ids: list[int] | tuple[int, ...]):
    return buscar_motivos_pre_conselho_por_ids(motivo_ids)


def get_period(periodo_id: int):
    return buscar_periodo_pre_conselho_por_id(periodo_id)


def get_record(registro_id: int):
    return buscar_registro_pre_conselho_por_id(registro_id)


def count_records_by_teacher_and_period(*, professor_id: int, periodo_id: int):
    return contar_registros_pre_conselho_por_professor_periodo(professor_id, periodo_id)


def create_reason(*args, **kwargs):
    return criar_motivo_pre_conselho(*args, **kwargs)


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


def list_periods():
    return listar_periodos_pre_conselho()


def list_records(*args, **kwargs):
    return listar_registros_pre_conselho(*args, **kwargs)


def get_user(usuario_id: int):
    return buscar_usuario_por_id(usuario_id)


def list_teacher_workloads_by_user_ids(usuario_ids: list[int] | tuple[int, ...]):
    return listar_cargas_professores_por_usuario_ids(usuario_ids)


def list_available_teachers():
    return listar_professores_agendamento()
