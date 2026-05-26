from db.catalogos import buscar_turma_por_id
from repositories.ocorrencias_repository import (
    atualizar_estudante,
    atualizar_status_estudante,
    buscar_estudante_por_id,
    criar_estudante,
    listar_estudantes,
    remover_estudante,
)
from services.csv_import_service import importar_estudantes_arquivo


def _texto_obrigatorio_estudante(valor: str | None, *, campo: str, max_len: int = 255) -> str:
    texto = str(valor or "").strip()
    if not texto:
        raise ValueError(f"{campo} e obrigatorio.")
    if len(texto) > max_len:
        raise ValueError(f"{campo} excede o limite de {max_len} caracteres.")
    return texto


def _validar_turma_id_estudante(turma_id: int | None) -> int:
    try:
        turma_id_valor = int(turma_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("Turma invalida.") from exc
    if turma_id_valor <= 0:
        raise ValueError("Turma invalida.")
    if not buscar_turma_por_id(turma_id_valor):
        raise ValueError("Turma invalida.")
    return turma_id_valor


def listar_estudantes_service(
    *,
    nome: str | None = None,
    turma_id: int | None = None,
    incluir_inativos: bool = True,
) -> list[dict]:
    turma_id_filtro = _validar_turma_id_estudante(turma_id) if turma_id is not None else None
    return listar_estudantes(
        incluir_inativos=incluir_inativos,
        nome=str(nome or "").strip() or None,
        turma_id=turma_id_filtro,
    )


def buscar_estudante_service(estudante_id: int) -> dict:
    estudante = buscar_estudante_por_id(estudante_id)
    if not estudante:
        raise LookupError("Estudante nao encontrado.")
    return estudante


def criar_estudante_service(*, nome: str, turma_id: int) -> dict:
    estudante_id = criar_estudante(
        nome=_texto_obrigatorio_estudante(nome, campo="Nome do estudante"),
        turma_id=_validar_turma_id_estudante(turma_id),
        ativo=True,
    )
    return buscar_estudante_service(estudante_id)


def importar_estudantes_arquivo_service(
    *,
    conteudo: bytes,
    nome_arquivo: str,
    tipo_conteudo: str,
) -> dict:
    return importar_estudantes_arquivo(
        conteudo,
        nome_arquivo=nome_arquivo,
        tipo_conteudo=tipo_conteudo,
    )


def atualizar_estudante_service(*, estudante_id: int, nome: str, turma_id: int, ativo: bool) -> dict:
    buscar_estudante_service(estudante_id)
    alterado = atualizar_estudante(
        estudante_id=estudante_id,
        nome=_texto_obrigatorio_estudante(nome, campo="Nome do estudante"),
        turma_id=_validar_turma_id_estudante(turma_id),
        ativo=bool(ativo),
    )
    if not alterado:
        raise LookupError("Estudante nao encontrado.")
    return buscar_estudante_service(estudante_id)


def atualizar_status_estudante_service(*, estudante_id: int, ativo: bool) -> None:
    alterado = atualizar_status_estudante(estudante_id, bool(ativo))
    if not alterado:
        raise LookupError("Estudante nao encontrado.")


def remover_estudante_service(estudante_id: int) -> int:
    removido, ocorrencias_desvinculadas = remover_estudante(estudante_id)
    if not removido:
        raise LookupError("Estudante nao encontrado.")
    return ocorrencias_desvinculadas
