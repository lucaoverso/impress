from fastapi import APIRouter, Depends, HTTPException, Query, Response

from auth import get_usuario_logado
from db.catalogos import buscar_turma_por_id
from repositories.ocorrencias_repository import remover_ocorrencia
from schemas.ocorrencias_schemas import OcorrenciaCreateIn, OcorrenciaOut, OcorrenciaUpdateIn
from services.ocorrencia_pdf_service import gerar_pdf_ocorrencia_registro
from services.ocorrencias_consulta_service import (
    buscar_estudantes_ocorrencia_service,
    buscar_ocorrencia_service,
    buscar_professores_ocorrencia_service,
    listar_ocorrencias_service,
    listar_opcoes_ocorrencias_service,
)
from services.ocorrencias_registro_service import (
    atualizar_ocorrencia_parcial_service,
    criar_ocorrencia_service,
)
from routers.ocorrencias_common import (
    _exigir_gestor,
    _montar_resposta_ocorrencia,
    _nome_arquivo_pdf_ocorrencia,
    _validar_data_opcional,
    _validar_status,
    _validar_tipo_registro,
    _validar_turma_id,
)

router = APIRouter()


@router.get("/ocorrencias/opcoes")
def listar_opcoes_ocorrencias(usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    return listar_opcoes_ocorrencias_service()


@router.get("/ocorrencias/busca/professores")
def buscar_professores_ocorrencia_api(
    q: str = Query(default=""),
    limite: int = Query(default=20),
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    return buscar_professores_ocorrencia_service(termo=q, limite=limite)


@router.get("/ocorrencias/busca/estudantes")
def buscar_estudantes_ocorrencia_api(
    q: str = Query(default=""),
    limite: int = Query(default=20),
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    return buscar_estudantes_ocorrencia_service(termo=q, limite=limite)


@router.post("/ocorrencias", response_model=OcorrenciaOut)
def criar_ocorrencia_api(payload: OcorrenciaCreateIn, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    try:
        return criar_ocorrencia_service(payload)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/ocorrencias", response_model=list[OcorrenciaOut])
def listar_ocorrencias_api(
    tipo_registro: str | None = Query(default=None),
    status: str | None = Query(default=None),
    turma_id: int | None = Query(default=None),
    nome_estudante: str | None = Query(default=None),
    data_inicial: str | None = Query(default=None),
    data_final: str | None = Query(default=None),
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    status_filtro = _validar_status(status) if status is not None and str(status).strip() else None
    tipo_registro_filtro = (
        _validar_tipo_registro(tipo_registro)
        if tipo_registro is not None and str(tipo_registro).strip()
        else None
    )
    data_inicial_norm = _validar_data_opcional(data_inicial, "Data inicial")
    data_final_norm = _validar_data_opcional(data_final, "Data final")
    if data_inicial_norm and data_final_norm and data_inicial_norm > data_final_norm:
        raise HTTPException(400, "Periodo invalido: data inicial maior que data final.")

    turma_id_filtro = _validar_turma_id(turma_id) if turma_id is not None else None
    return listar_ocorrencias_service(
        tipo_registro=tipo_registro_filtro,
        status=status_filtro,
        turma_id=turma_id_filtro,
        nome_estudante=str(nome_estudante or "").strip() or None,
        data_inicial=data_inicial_norm,
        data_final=data_final_norm,
    )


@router.get("/ocorrencias/{ocorrencia_id}", response_model=OcorrenciaOut)
def buscar_ocorrencia_api(ocorrencia_id: int, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    try:
        return buscar_ocorrencia_service(ocorrencia_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/ocorrencias/{ocorrencia_id}/pdf")
def gerar_pdf_ocorrencia_api(ocorrencia_id: int, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    ocorrencia = _montar_resposta_ocorrencia(ocorrencia_id)
    turma = buscar_turma_por_id(int(ocorrencia.get("turma_id") or 0))
    pdf_bytes = gerar_pdf_ocorrencia_registro(ocorrencia, turma=turma)
    nome_arquivo = _nome_arquivo_pdf_ocorrencia(ocorrencia)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{nome_arquivo}"'},
    )


@router.patch("/ocorrencias/{ocorrencia_id}", response_model=OcorrenciaOut)
def atualizar_ocorrencia_parcial_api(
    ocorrencia_id: int,
    payload: OcorrenciaUpdateIn,
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    try:
        return atualizar_ocorrencia_parcial_service(ocorrencia_id, payload)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.put("/ocorrencias/{ocorrencia_id}", response_model=OcorrenciaOut)
def atualizar_ocorrencia_api(
    ocorrencia_id: int,
    payload: OcorrenciaUpdateIn,
    usuario=Depends(get_usuario_logado),
):
    return atualizar_ocorrencia_parcial_api(ocorrencia_id, payload, usuario)


@router.delete("/ocorrencias/{ocorrencia_id}")
def remover_ocorrencia_api(ocorrencia_id: int, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    removido = remover_ocorrencia(ocorrencia_id)
    if not removido:
        raise HTTPException(404, "Registro nao encontrado.")
    return {"mensagem": "Registro excluido com sucesso."}


@router.post("/ocorrencias/{ocorrencia_id}/excluir")
def remover_ocorrencia_fallback_api(ocorrencia_id: int, usuario=Depends(get_usuario_logado)):
    return remover_ocorrencia_api(ocorrencia_id, usuario)
