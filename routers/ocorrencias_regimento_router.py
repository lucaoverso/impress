from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from auth import get_usuario_logado
from repositories.ocorrencias_repository import (
    atualizar_regimento_item,
    atualizar_status_regimento_item,
    buscar_regimento_item_por_id,
    criar_regimento_item,
    listar_regimento_itens,
    remover_regimento_item,
)
from schemas.ocorrencias_schemas import (
    ImportacaoCsvOut,
    RegimentoItemCreateIn,
    RegimentoItemOut,
    RegimentoItemStatusIn,
    RegimentoItemUpdateIn,
)
from services.csv_import_service import importar_base_legal_arquivo
from routers.ocorrencias_common import (
    _exigir_gestor,
    _ler_upload_base_legal,
    _montar_resposta_regimento_item,
    _normalizar_payload_regimento,
)

router = APIRouter()


@router.get("/regimento-itens", response_model=list[RegimentoItemOut])
def listar_regimento_itens_api(
    incluir_inativos: bool = Query(default=True),
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    return listar_regimento_itens(incluir_inativos=incluir_inativos)


@router.get("/regimento-itens/{regimento_item_id}", response_model=RegimentoItemOut)
def buscar_regimento_item_api(regimento_item_id: int, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    return _montar_resposta_regimento_item(regimento_item_id)


@router.delete("/regimento-itens/{regimento_item_id}")
def remover_regimento_item_api(regimento_item_id: int, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    try:
        removido = remover_regimento_item(regimento_item_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not removido:
        raise HTTPException(404, "Item do regimento nao encontrado.")
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
    dados = _normalizar_payload_regimento(payload)
    try:
        regimento_item_id = criar_regimento_item(
            lei_nome=dados["lei_nome"],
            artigo_numero=dados["artigo_numero"],
            artigo_descricao=dados["artigo_descricao"],
            inciso_numero=dados["inciso_numero"],
            inciso_descricao=dados["inciso_descricao"],
            alinea_identificador=dados["alinea_identificador"],
            alinea_descricao=dados["alinea_descricao"],
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return _montar_resposta_regimento_item(regimento_item_id)


@router.post("/regimento-itens/importar", response_model=ImportacaoCsvOut)
@router.post("/regimento-itens/importar-csv", response_model=ImportacaoCsvOut)
def importar_regimento_itens_arquivo_api(
    arquivo: UploadFile = File(...),
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    try:
        conteudo, nome_arquivo, tipo_conteudo = _ler_upload_base_legal(arquivo)
        return importar_base_legal_arquivo(
            conteudo,
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
    if not buscar_regimento_item_por_id(regimento_item_id):
        raise HTTPException(404, "Item do regimento nao encontrado.")

    dados = _normalizar_payload_regimento(payload)
    try:
        alterado = atualizar_regimento_item(
            regimento_item_id=regimento_item_id,
            lei_nome=dados["lei_nome"],
            artigo_numero=dados["artigo_numero"],
            artigo_descricao=dados["artigo_descricao"],
            inciso_numero=dados["inciso_numero"],
            inciso_descricao=dados["inciso_descricao"],
            alinea_identificador=dados["alinea_identificador"],
            alinea_descricao=dados["alinea_descricao"],
            ativo=bool(payload.ativo),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    if not alterado:
        raise HTTPException(404, "Item do regimento nao encontrado.")
    return _montar_resposta_regimento_item(regimento_item_id)


@router.put("/regimento-itens/{regimento_item_id}/status")
def atualizar_status_regimento_item_api(
    regimento_item_id: int,
    payload: RegimentoItemStatusIn,
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    alterado = atualizar_status_regimento_item(regimento_item_id, bool(payload.ativo))
    if not alterado:
        raise HTTPException(404, "Item do regimento nao encontrado.")
    return {"mensagem": "Status do item do regimento atualizado com sucesso."}
