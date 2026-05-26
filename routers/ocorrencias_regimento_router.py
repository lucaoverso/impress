from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from auth import get_usuario_logado
from schemas.ocorrencias_schemas import (
    ImportacaoCsvOut,
    RegimentoItemCreateIn,
    RegimentoItemOut,
    RegimentoItemStatusIn,
    RegimentoItemUpdateIn,
)
from services.ocorrencias_regimento_service import (
    atualizar_regimento_item_service,
    atualizar_status_regimento_item_service,
    buscar_regimento_item_service,
    criar_regimento_item_service,
    importar_regimento_itens_arquivo_service,
    listar_regimento_itens_service,
    remover_regimento_item_service,
)
from routers.ocorrencias_common import (
    _exigir_gestor,
    _ler_upload_base_legal,
)

router = APIRouter()


@router.get("/regimento-itens", response_model=list[RegimentoItemOut])
def listar_regimento_itens_api(
    incluir_inativos: bool = Query(default=True),
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    return listar_regimento_itens_service(incluir_inativos=incluir_inativos)


@router.get("/regimento-itens/{regimento_item_id}", response_model=RegimentoItemOut)
def buscar_regimento_item_api(regimento_item_id: int, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    try:
        return buscar_regimento_item_service(regimento_item_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.delete("/regimento-itens/{regimento_item_id}")
def remover_regimento_item_api(regimento_item_id: int, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    try:
        remover_regimento_item_service(regimento_item_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"mensagem": "Item da base legal excluido com sucesso."}


@router.post("/regimento-itens/{regimento_item_id}/excluir")
def remover_regimento_item_fallback_api(
    regimento_item_id: int,
    usuario=Depends(get_usuario_logado),
):
    return remover_regimento_item_api(regimento_item_id, usuario)


@router.post("/regimento-itens", response_model=RegimentoItemOut)
def criar_regimento_item_api(
    payload: RegimentoItemCreateIn,
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    try:
        return criar_regimento_item_service(payload)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/regimento-itens/importar", response_model=ImportacaoCsvOut)
@router.post("/regimento-itens/importar-csv", response_model=ImportacaoCsvOut)
def importar_regimento_itens_arquivo_api(
    arquivo: UploadFile = File(...),
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    try:
        conteudo, nome_arquivo, tipo_conteudo = _ler_upload_base_legal(arquivo)
        return importar_regimento_itens_arquivo_service(
            conteudo=conteudo,
            nome_arquivo=nome_arquivo,
            tipo_conteudo=tipo_conteudo,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.put("/regimento-itens/{regimento_item_id}", response_model=RegimentoItemOut)
def atualizar_regimento_item_api(
    regimento_item_id: int,
    payload: RegimentoItemUpdateIn,
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    try:
        return atualizar_regimento_item_service(
            regimento_item_id=regimento_item_id,
            payload=payload,
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.put("/regimento-itens/{regimento_item_id}/status")
def atualizar_status_regimento_item_api(
    regimento_item_id: int,
    payload: RegimentoItemStatusIn,
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    try:
        atualizar_status_regimento_item_service(
            regimento_item_id=regimento_item_id,
            ativo=bool(payload.ativo),
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {"mensagem": "Status do item do regimento atualizado com sucesso."}
