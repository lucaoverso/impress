from fastapi import APIRouter, Depends, HTTPException, Query

from auth import get_usuario_logado
from schemas.ocorrencias_schemas import (
    AlineaCreateIn,
    AlineaOut,
    AlineaUpdateIn,
    ArtigoCreateIn,
    ArtigoOut,
    ArtigoUpdateIn,
    IncisoCreateIn,
    IncisoOut,
    IncisoUpdateIn,
    LeiCreateIn,
    LeiOut,
    LeiUpdateIn,
)
from services.ocorrencias_base_legal_service import (
    atualizar_alinea_service,
    atualizar_artigo_service,
    atualizar_inciso_service,
    atualizar_lei_service,
    buscar_alinea_service,
    buscar_artigo_service,
    buscar_inciso_service,
    buscar_lei_service,
    criar_alinea_service,
    criar_artigo_service,
    criar_inciso_service,
    criar_lei_service,
    listar_alineas_service,
    listar_artigos_service,
    listar_incisos_service,
    listar_leis_service,
    remover_alinea_service,
    remover_artigo_service,
    remover_inciso_service,
    remover_lei_service,
)
from routers.ocorrencias_common import _exigir_gestor

router = APIRouter()


@router.get("/leis", response_model=list[LeiOut])
def listar_leis_api(usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    return listar_leis_service()


@router.get("/leis/{lei_id}", response_model=LeiOut)
def buscar_lei_api(lei_id: int, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    try:
        return buscar_lei_service(lei_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/leis", response_model=LeiOut)
def criar_lei_api(payload: LeiCreateIn, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    try:
        return criar_lei_service(nome=payload.nome)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.put("/leis/{lei_id}", response_model=LeiOut)
def atualizar_lei_api(lei_id: int, payload: LeiUpdateIn, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    try:
        return atualizar_lei_service(lei_id=lei_id, nome=payload.nome)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.delete("/leis/{lei_id}")
def remover_lei_api(lei_id: int, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    try:
        remover_lei_service(lei_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"mensagem": "Lei excluida com sucesso."}


@router.post("/leis/{lei_id}/excluir")
def remover_lei_fallback_api(lei_id: int, usuario=Depends(get_usuario_logado)):
    return remover_lei_api(lei_id, usuario)


@router.get("/artigos", response_model=list[ArtigoOut])
def listar_artigos_api(
    lei_id: int | None = Query(default=None),
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    return listar_artigos_service(lei_id=lei_id)


@router.get("/artigos/{artigo_id}", response_model=ArtigoOut)
def buscar_artigo_api(artigo_id: int, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    try:
        return buscar_artigo_service(artigo_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/artigos", response_model=ArtigoOut)
def criar_artigo_api(payload: ArtigoCreateIn, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    try:
        return criar_artigo_service(
            lei_id=payload.lei_id,
            numero=payload.numero,
            descricao=payload.descricao,
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.put("/artigos/{artigo_id}", response_model=ArtigoOut)
def atualizar_artigo_api(
    artigo_id: int,
    payload: ArtigoUpdateIn,
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    try:
        return atualizar_artigo_service(
            artigo_id=artigo_id,
            lei_id=payload.lei_id,
            numero=payload.numero,
            descricao=payload.descricao,
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.delete("/artigos/{artigo_id}")
def remover_artigo_api(artigo_id: int, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    try:
        remover_artigo_service(artigo_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"mensagem": "Artigo excluido com sucesso."}


@router.post("/artigos/{artigo_id}/excluir")
def remover_artigo_fallback_api(artigo_id: int, usuario=Depends(get_usuario_logado)):
    return remover_artigo_api(artigo_id, usuario)


@router.get("/incisos", response_model=list[IncisoOut])
def listar_incisos_api(
    artigo_id: int | None = Query(default=None),
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    return listar_incisos_service(artigo_id=artigo_id)


@router.get("/incisos/{inciso_id}", response_model=IncisoOut)
def buscar_inciso_api(inciso_id: int, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    try:
        return buscar_inciso_service(inciso_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/incisos", response_model=IncisoOut)
def criar_inciso_api(payload: IncisoCreateIn, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    try:
        return criar_inciso_service(
            artigo_id=payload.artigo_id,
            numero=payload.numero,
            descricao=payload.descricao,
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.put("/incisos/{inciso_id}", response_model=IncisoOut)
def atualizar_inciso_api(
    inciso_id: int,
    payload: IncisoUpdateIn,
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    try:
        return atualizar_inciso_service(
            inciso_id=inciso_id,
            artigo_id=payload.artigo_id,
            numero=payload.numero,
            descricao=payload.descricao,
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.delete("/incisos/{inciso_id}")
def remover_inciso_api(inciso_id: int, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    try:
        remover_inciso_service(inciso_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"mensagem": "Inciso excluido com sucesso."}


@router.post("/incisos/{inciso_id}/excluir")
def remover_inciso_fallback_api(inciso_id: int, usuario=Depends(get_usuario_logado)):
    return remover_inciso_api(inciso_id, usuario)


@router.get("/alineas", response_model=list[AlineaOut])
def listar_alineas_api(
    inciso_id: int | None = Query(default=None),
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    return listar_alineas_service(inciso_id=inciso_id)


@router.get("/alineas/{alinea_id}", response_model=AlineaOut)
def buscar_alinea_api(alinea_id: int, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    try:
        return buscar_alinea_service(alinea_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/alineas", response_model=AlineaOut)
def criar_alinea_api(payload: AlineaCreateIn, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    try:
        return criar_alinea_service(
            inciso_id=payload.inciso_id,
            identificador=payload.identificador,
            descricao=payload.descricao,
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.put("/alineas/{alinea_id}", response_model=AlineaOut)
def atualizar_alinea_api(
    alinea_id: int,
    payload: AlineaUpdateIn,
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    try:
        return atualizar_alinea_service(
            alinea_id=alinea_id,
            inciso_id=payload.inciso_id,
            identificador=payload.identificador,
            descricao=payload.descricao,
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.delete("/alineas/{alinea_id}")
def remover_alinea_api(alinea_id: int, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    try:
        remover_alinea_service(alinea_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"mensagem": "Alinea excluida com sucesso."}


@router.post("/alineas/{alinea_id}/excluir")
def remover_alinea_fallback_api(alinea_id: int, usuario=Depends(get_usuario_logado)):
    return remover_alinea_api(alinea_id, usuario)
