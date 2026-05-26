from fastapi import APIRouter, Depends, HTTPException, Query, Response

from auth import get_usuario_logado
from schemas.ocorrencias_schemas import OcorrenciaCreateIn, OcorrenciaOut, OcorrenciaUpdateIn
from services.ocorrencias_consulta_service import (
    buscar_estudantes_ocorrencia_service,
    buscar_ocorrencia_service,
    buscar_professores_ocorrencia_service,
    gerar_pdf_ocorrencia_service,
    listar_ocorrencias_filtradas_service,
    listar_opcoes_ocorrencias_service,
)
from services.ocorrencias_registro_service import (
    atualizar_ocorrencia_parcial_service,
    criar_ocorrencia_service,
    remover_ocorrencia_service,
)
from routers.ocorrencias_common import _exigir_gestor

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
    try:
        return listar_ocorrencias_filtradas_service(
            tipo_registro=tipo_registro,
            status=status,
            turma_id=turma_id,
            nome_estudante=nome_estudante,
            data_inicial=data_inicial,
            data_final=data_final,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


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
    try:
        pdf_bytes, nome_arquivo = gerar_pdf_ocorrencia_service(ocorrencia_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
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
    try:
        remover_ocorrencia_service(ocorrencia_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {"mensagem": "Registro excluido com sucesso."}


@router.post("/ocorrencias/{ocorrencia_id}/excluir")
def remover_ocorrencia_fallback_api(ocorrencia_id: int, usuario=Depends(get_usuario_logado)):
    return remover_ocorrencia_api(ocorrencia_id, usuario)
