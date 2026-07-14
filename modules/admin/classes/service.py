import sqlite3

from db.horario_escolar import listar_configuracoes_aulas
from modules.scheduling.config import TURNOS_CONFIG
from modules.scheduling.lesson_config import lesson_window_from_turn, validate_class_lesson_window

from . import repository
from .schemas import TurmaCreateIn, TurmaUpdateIn


class ClassConflictError(Exception):
    pass


class ClassNotFoundError(Exception):
    pass


def list_classes(include_inactive: bool):
    return repository.listar_turmas(incluir_inativas=include_inactive)


def _class_data(payload: TurmaCreateIn | TurmaUpdateIn) -> dict:
    turno = str(payload.turno or "").strip().upper()
    if turno not in TURNOS_CONFIG:
        raise ValueError("Turno inválido.")
    inicio_padrao, fim_padrao = lesson_window_from_turn(turno)
    try:
        aula_inicial, aula_final = validate_class_lesson_window(
            payload.aula_inicial if payload.aula_inicial is not None else inicio_padrao,
            payload.aula_final if payload.aula_final is not None else fim_padrao,
            listar_configuracoes_aulas(incluir_inativas=False),
        )
    except ValueError as exc:
        raise ValueError(str(exc)) from exc
    quantidade = int(payload.quantidade_estudantes or 0)
    if quantidade < 0:
        raise ValueError("Quantidade de estudantes não pode ser negativa.")
    return {
        "turno": turno,
        "aula_inicial": aula_inicial,
        "aula_final": aula_final,
        "quantidade_estudantes": quantidade,
    }


def create_class(payload: TurmaCreateIn) -> int:
    nome = payload.nome.strip()
    if not nome:
        raise ValueError("Nome da turma é obrigatório.")
    try:
        return repository.criar_turma(nome=nome, **_class_data(payload))
    except sqlite3.IntegrityError as exc:
        raise ClassConflictError("Já existe uma turma com este nome.") from exc


def update_class(class_id: int, payload: TurmaUpdateIn) -> None:
    if not repository.atualizar_turma_dados(turma_id=class_id, **_class_data(payload)):
        raise ClassNotFoundError("Turma não encontrada.")


def update_class_status(class_id: int, active: bool) -> None:
    if not repository.atualizar_status_turma(class_id, active):
        raise ClassNotFoundError("Turma não encontrada.")
