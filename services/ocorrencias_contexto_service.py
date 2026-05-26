from __future__ import annotations

from typing import TYPE_CHECKING

from db.catalogos import buscar_turma_por_id
from repositories.ocorrencias_repository import (
    buscar_estudante_por_id,
    buscar_professor_por_id_ocorrencia,
)
from services.ocorrencias_validacao_service import (
    TIPO_REGISTRO_ESTUDANTE,
    TIPO_REGISTRO_PROFESSOR,
    texto_obrigatorio_ocorrencia,
    texto_opcional_ocorrencia,
    validar_estudante_id_ocorrencia,
    validar_professor_id_ocorrencia,
    validar_turma_id_ocorrencia,
)

if TYPE_CHECKING:
    from schemas.ocorrencias_schemas import (
        OcorrenciaEstudanteVinculadoIn,
        OcorrenciaProfessorVinculadoIn,
    )


def resumir_nomes_vinculados_ocorrencia(itens: list[dict], *, campo_nome: str = "nome") -> str:
    nomes = [
        str(item.get(campo_nome) or "").strip()
        for item in (itens or [])
        if str(item.get(campo_nome) or "").strip()
    ]
    return ", ".join(nomes)


def _resolver_dados_professor_ocorrencia(
    *,
    professor_requerente: str | None,
    professor_requerente_id: int | None,
    campo_rotulo: str = "Professor requerente",
) -> tuple[str, int | None]:
    professor_id_valor = validar_professor_id_ocorrencia(
        professor_requerente_id, campo=campo_rotulo
    )
    professor_nome = texto_opcional_ocorrencia(professor_requerente, max_len=255)
    if professor_id_valor is None:
        if not professor_nome:
            raise ValueError(f"{campo_rotulo} e obrigatorio.")
        return professor_nome, None
    professor = buscar_professor_por_id_ocorrencia(professor_id_valor)
    if not professor:
        raise ValueError(f"{campo_rotulo} selecionado nao encontrado.")
    return str(professor.get("nome") or "").strip(), professor_id_valor


def resolver_estudantes_vinculados_ocorrencia(
    *,
    estudantes_vinculados: list["OcorrenciaEstudanteVinculadoIn"] | list[dict] | None,
    nome_estudante: str | None,
    estudante_id: int | None,
    turma_id: int | None,
) -> list[dict]:
    turma_id_padrao = validar_turma_id_ocorrencia(turma_id) if turma_id not in (None, "") else None
    candidatos = []
    for item in estudantes_vinculados or []:
        if isinstance(item, dict):
            candidatos.append(
                {
                    "estudante_id": item.get("estudante_id"),
                    "nome": item.get("nome"),
                    "turma_id": item.get("turma_id"),
                }
            )
        else:
            candidatos.append(
                {
                    "estudante_id": getattr(item, "estudante_id", None),
                    "nome": getattr(item, "nome", None),
                    "turma_id": getattr(item, "turma_id", None),
                }
            )
    if not candidatos and (
        texto_opcional_ocorrencia(nome_estudante, max_len=255)
        or validar_estudante_id_ocorrencia(estudante_id) is not None
    ):
        candidatos.append(
            {
                "estudante_id": estudante_id,
                "nome": nome_estudante,
                "turma_id": turma_id_padrao,
            }
        )
    itens_resolvidos = []
    vistos = set()
    for item in candidatos:
        estudante_id_valor = validar_estudante_id_ocorrencia(item.get("estudante_id"))
        if estudante_id_valor is not None:
            estudante = buscar_estudante_por_id(estudante_id_valor)
            if not estudante:
                raise ValueError("Estudante selecionado nao encontrado.")
            if int(estudante.get("ativo") or 0) != 1:
                raise ValueError("Estudante selecionado esta inativo.")
            nome_resolvido = str(estudante.get("nome") or "").strip()
            turma_resolvida_id = int(estudante.get("turma_id") or 0)
            if turma_resolvida_id <= 0:
                raise ValueError("Turma do estudante nao identificada.")
            turma_item = item.get("turma_id")
            if turma_item not in (None, "") and int(turma_item) != turma_resolvida_id:
                raise ValueError("Turma do estudante divergente dos dados cadastrados.")
        else:
            nome_resolvido = texto_obrigatorio_ocorrencia(
                item.get("nome"), "Nome do estudante", max_len=255
            )
            turma_resolvida_id = (
                validar_turma_id_ocorrencia(item.get("turma_id"))
                if item.get("turma_id") not in (None, "")
                else turma_id_padrao
            )
            if turma_resolvida_id is None:
                raise ValueError("Turma do estudante nao identificada.")
        turma = buscar_turma_por_id(turma_resolvida_id)
        turma_nome = str((turma or {}).get("nome") or "").strip()
        chave = f"id:{estudante_id_valor}" if estudante_id_valor else f"nome:{nome_resolvido.casefold()}"
        if chave in vistos:
            continue
        vistos.add(chave)
        itens_resolvidos.append(
            {
                "estudante_id": estudante_id_valor,
                "nome": nome_resolvido,
                "turma_id": turma_resolvida_id,
                "turma_nome": turma_nome,
            }
        )
    if not itens_resolvidos:
        raise ValueError("Selecione ao menos um estudante para o registro.")
    return itens_resolvidos


def resolver_professores_vinculados_ocorrencia(
    *,
    professores_vinculados: list["OcorrenciaProfessorVinculadoIn"] | list[dict] | None,
    professor_requerente: str | None,
    professor_requerente_id: int | None,
) -> list[dict]:
    candidatos = []
    for item in professores_vinculados or []:
        if isinstance(item, dict):
            candidatos.append(
                {
                    "professor_id": item.get("professor_id"),
                    "nome": item.get("nome"),
                    "email": item.get("email"),
                }
            )
        else:
            candidatos.append(
                {
                    "professor_id": getattr(item, "professor_id", None),
                    "nome": getattr(item, "nome", None),
                    "email": getattr(item, "email", None),
                }
            )
    if not candidatos and (
        texto_opcional_ocorrencia(professor_requerente, max_len=255)
        or validar_professor_id_ocorrencia(professor_requerente_id, campo="Professor") is not None
    ):
        candidatos.append(
            {
                "professor_id": professor_requerente_id,
                "nome": professor_requerente,
                "email": "",
            }
        )
    itens_resolvidos = []
    vistos = set()
    for item in candidatos:
        professor_id_valor = validar_professor_id_ocorrencia(item.get("professor_id"), campo="Professor")
        if professor_id_valor is not None:
            professor = buscar_professor_por_id_ocorrencia(professor_id_valor)
            if not professor:
                raise ValueError("Professor selecionado nao encontrado.")
            nome_resolvido = str(professor.get("nome") or "").strip()
            email_resolvido = str(professor.get("email") or "").strip()
        else:
            nome_resolvido = texto_obrigatorio_ocorrencia(
                item.get("nome"), "Nome do professor", max_len=255
            )
            email_resolvido = texto_opcional_ocorrencia(item.get("email"), max_len=255) or ""
        if nome_resolvido.strip().lower() == "todos os professores":
            raise ValueError("Selecione professores individualmente neste tipo de registro.")
        chave = f"id:{professor_id_valor}" if professor_id_valor else f"nome:{nome_resolvido.casefold()}"
        if chave in vistos:
            continue
        vistos.add(chave)
        itens_resolvidos.append(
            {
                "professor_id": professor_id_valor,
                "nome": nome_resolvido,
                "email": email_resolvido,
            }
        )
    if not itens_resolvidos:
        raise ValueError("Selecione ao menos um professor para o registro.")
    return itens_resolvidos


def resolver_contexto_registro_ocorrencia(
    *,
    tipo_registro: str,
    nome_estudante: str | None,
    estudante_id: int | None,
    estudantes_vinculados: list["OcorrenciaEstudanteVinculadoIn"] | list[dict] | None,
    turma_id: int | None,
    professor_requerente: str | None,
    professor_requerente_id: int | None,
    professores_vinculados: list["OcorrenciaProfessorVinculadoIn"] | list[dict] | None,
) -> dict:
    if tipo_registro == TIPO_REGISTRO_ESTUDANTE:
        estudantes_resolvidos = resolver_estudantes_vinculados_ocorrencia(
            estudantes_vinculados=estudantes_vinculados,
            nome_estudante=nome_estudante,
            estudante_id=estudante_id,
            turma_id=turma_id,
        )
        turmas_vinculadas = {
            int(item["turma_id"])
            for item in estudantes_resolvidos
            if item.get("turma_id") is not None and int(item["turma_id"]) > 0
        }
        turma_id_valor = next(iter(turmas_vinculadas)) if len(turmas_vinculadas) == 1 else None
        professor_nome, professor_id_valor = _resolver_dados_professor_ocorrencia(
            professor_requerente=professor_requerente,
            professor_requerente_id=professor_requerente_id,
            campo_rotulo="Professor requerente",
        )
        return {
            "nome_estudante": resumir_nomes_vinculados_ocorrencia(estudantes_resolvidos),
            "estudante_id": estudantes_resolvidos[0].get("estudante_id"),
            "estudantes_vinculados": estudantes_resolvidos,
            "turma_id": turma_id_valor,
            "professor_requerente": professor_nome,
            "professor_requerente_id": professor_id_valor,
            "professores_vinculados": [],
        }
    if tipo_registro == TIPO_REGISTRO_PROFESSOR:
        professores_resolvidos = resolver_professores_vinculados_ocorrencia(
            professores_vinculados=professores_vinculados,
            professor_requerente=professor_requerente,
            professor_requerente_id=professor_requerente_id,
        )
        nomes_professores = resumir_nomes_vinculados_ocorrencia(professores_resolvidos)
        return {
            "nome_estudante": nomes_professores,
            "estudante_id": None,
            "estudantes_vinculados": [],
            "turma_id": None,
            "professor_requerente": nomes_professores,
            "professor_requerente_id": professores_resolvidos[0].get("professor_id"),
            "professores_vinculados": professores_resolvidos,
        }
    return {
        "nome_estudante": texto_obrigatorio_ocorrencia(
            nome_estudante, "Titulo do registro geral", max_len=255
        ),
        "estudante_id": None,
        "estudantes_vinculados": [],
        "turma_id": None,
        "professor_requerente": "Todos os professores",
        "professor_requerente_id": None,
        "professores_vinculados": [],
    }
