from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from auth import get_usuario_logado
from schemas.ocorrencias_schemas import (
    EstudanteCreateIn,
    EstudanteOut,
    EstudanteStatusIn,
    EstudanteUpdateIn,
    ImportacaoCsvOut,
)
from services.ocorrencias_estudantes_service import (
    atualizar_estudante_service,
    atualizar_status_estudante_service,
    buscar_estudante_service,
    criar_estudante_service,
    importar_estudantes_arquivo_service,
    listar_estudantes_service,
    remover_estudante_service,
)
from routers.ocorrencias_common import (
    _exigir_gestor,
    _ler_upload_estudantes,
)

router = APIRouter()


@router.get("/estudantes", response_model=list[EstudanteOut])
def listar_estudantes_api(
    nome: str | None = Query(default=None),
    turma_id: int | None = Query(default=None),
    incluir_inativos: bool = Query(default=True),
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    try:
        return listar_estudantes_service(
            nome=nome,
            turma_id=turma_id,
            incluir_inativos=incluir_inativos,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/estudantes/{estudante_id}", response_model=EstudanteOut)
def buscar_estudante_api(estudante_id: int, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    try:
        return buscar_estudante_service(estudante_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/estudantes", response_model=EstudanteOut)
def criar_estudante_api(payload: EstudanteCreateIn, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    try:
        return criar_estudante_service(nome=payload.nome, turma_id=payload.turma_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/estudantes/importar", response_model=ImportacaoCsvOut)
@router.post("/estudantes/importar-csv", response_model=ImportacaoCsvOut)
def importar_estudantes_arquivo_api(
    arquivo: UploadFile = File(...),
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    try:
        conteudo, nome_arquivo, tipo_conteudo = _ler_upload_estudantes(arquivo)
        return importar_estudantes_arquivo_service(
            conteudo=conteudo,
            nome_arquivo=nome_arquivo,
            tipo_conteudo=tipo_conteudo,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.put("/estudantes/{estudante_id}", response_model=EstudanteOut)
def atualizar_estudante_api(
    estudante_id: int,
    payload: EstudanteUpdateIn,
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    try:
        return atualizar_estudante_service(
            estudante_id=estudante_id,
            nome=payload.nome,
            turma_id=payload.turma_id,
            ativo=payload.ativo,
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.put("/estudantes/{estudante_id}/status")
def atualizar_status_estudante_api(
    estudante_id: int,
    payload: EstudanteStatusIn,
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    try:
        atualizar_status_estudante_service(estudante_id=estudante_id, ativo=payload.ativo)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {"mensagem": "Status do estudante atualizado com sucesso."}


@router.delete("/estudantes/{estudante_id}")
def remover_estudante_api(estudante_id: int, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    try:
        ocorrencias_desvinculadas = remover_estudante_service(estudante_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {
        "mensagem": "Estudante excluido com sucesso.",
        "ocorrencias_desvinculadas": ocorrencias_desvinculadas,
    }


@router.post("/estudantes/{estudante_id}/excluir")
def remover_estudante_fallback_api(estudante_id: int, usuario=Depends(get_usuario_logado)):
    return remover_estudante_api(estudante_id, usuario)
