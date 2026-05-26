from fastapi import APIRouter, Depends, HTTPException, Query

from auth import get_usuario_logado
from repositories.ocorrencias_repository import (
    atualizar_alinea,
    atualizar_artigo,
    atualizar_inciso,
    atualizar_lei,
    buscar_alinea_por_id,
    buscar_artigo_por_id,
    buscar_inciso_por_id,
    buscar_lei_por_id,
    criar_alinea,
    criar_artigo,
    criar_inciso,
    criar_lei,
    listar_alineas,
    listar_artigos,
    listar_incisos,
    listar_leis,
    remover_alinea,
    remover_artigo,
    remover_inciso,
    remover_lei,
)
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
from routers.ocorrencias_common import (
    _exigir_gestor,
    _montar_resposta_alinea,
    _montar_resposta_artigo,
    _montar_resposta_inciso,
    _montar_resposta_lei,
    _texto_obrigatorio,
)

router = APIRouter()


@router.get("/leis", response_model=list[LeiOut])
def listar_leis_api(usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    return listar_leis()


@router.get("/leis/{lei_id}", response_model=LeiOut)
def buscar_lei_api(lei_id: int, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    return _montar_resposta_lei(lei_id)


@router.post("/leis", response_model=LeiOut)
def criar_lei_api(payload: LeiCreateIn, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    try:
        lei_id = criar_lei(nome=_texto_obrigatorio(payload.nome, "Nome da lei", max_len=120))
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return _montar_resposta_lei(lei_id)


@router.put("/leis/{lei_id}", response_model=LeiOut)
def atualizar_lei_api(lei_id: int, payload: LeiUpdateIn, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    if not buscar_lei_por_id(lei_id):
        raise HTTPException(404, "Lei nao encontrada.")
    try:
        alterado = atualizar_lei(
            lei_id=lei_id,
            nome=_texto_obrigatorio(payload.nome, "Nome da lei", max_len=120),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not alterado:
        raise HTTPException(404, "Lei nao encontrada.")
    return _montar_resposta_lei(lei_id)


@router.delete("/leis/{lei_id}")
def remover_lei_api(lei_id: int, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    try:
        removido = remover_lei(lei_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not removido:
        raise HTTPException(404, "Lei nao encontrada.")
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
    return listar_artigos(lei_id=lei_id)


@router.get("/artigos/{artigo_id}", response_model=ArtigoOut)
def buscar_artigo_api(artigo_id: int, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    return _montar_resposta_artigo(artigo_id)


@router.post("/artigos", response_model=ArtigoOut)
def criar_artigo_api(payload: ArtigoCreateIn, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    if not buscar_lei_por_id(payload.lei_id):
        raise HTTPException(404, "Lei nao encontrada.")
    try:
        artigo_id = criar_artigo(
            lei_id=payload.lei_id,
            numero=_texto_obrigatorio(payload.numero, "Numero do artigo", max_len=120),
            descricao=_texto_obrigatorio(payload.descricao, "Descricao do artigo", max_len=5000),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return _montar_resposta_artigo(artigo_id)


@router.put("/artigos/{artigo_id}", response_model=ArtigoOut)
def atualizar_artigo_api(
    artigo_id: int,
    payload: ArtigoUpdateIn,
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    if not buscar_artigo_por_id(artigo_id):
        raise HTTPException(404, "Artigo nao encontrado.")
    if not buscar_lei_por_id(payload.lei_id):
        raise HTTPException(404, "Lei nao encontrada.")
    try:
        alterado = atualizar_artigo(
            artigo_id=artigo_id,
            lei_id=payload.lei_id,
            numero=_texto_obrigatorio(payload.numero, "Numero do artigo", max_len=120),
            descricao=_texto_obrigatorio(payload.descricao, "Descricao do artigo", max_len=5000),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not alterado:
        raise HTTPException(404, "Artigo nao encontrado.")
    return _montar_resposta_artigo(artigo_id)


@router.delete("/artigos/{artigo_id}")
def remover_artigo_api(artigo_id: int, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    try:
        removido = remover_artigo(artigo_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not removido:
        raise HTTPException(404, "Artigo nao encontrado.")
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
    return listar_incisos(artigo_id=artigo_id)


@router.get("/incisos/{inciso_id}", response_model=IncisoOut)
def buscar_inciso_api(inciso_id: int, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    return _montar_resposta_inciso(inciso_id)


@router.post("/incisos", response_model=IncisoOut)
def criar_inciso_api(payload: IncisoCreateIn, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    if not buscar_artigo_por_id(payload.artigo_id):
        raise HTTPException(404, "Artigo nao encontrado.")
    try:
        inciso_id = criar_inciso(
            artigo_id=payload.artigo_id,
            numero=_texto_obrigatorio(payload.numero, "Numero do inciso", max_len=40),
            descricao=_texto_obrigatorio(payload.descricao, "Descricao do inciso", max_len=5000),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return _montar_resposta_inciso(inciso_id)


@router.put("/incisos/{inciso_id}", response_model=IncisoOut)
def atualizar_inciso_api(
    inciso_id: int,
    payload: IncisoUpdateIn,
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    if not buscar_inciso_por_id(inciso_id):
        raise HTTPException(404, "Inciso nao encontrado.")
    if not buscar_artigo_por_id(payload.artigo_id):
        raise HTTPException(404, "Artigo nao encontrado.")
    try:
        alterado = atualizar_inciso(
            inciso_id=inciso_id,
            artigo_id=payload.artigo_id,
            numero=_texto_obrigatorio(payload.numero, "Numero do inciso", max_len=40),
            descricao=_texto_obrigatorio(payload.descricao, "Descricao do inciso", max_len=5000),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not alterado:
        raise HTTPException(404, "Inciso nao encontrado.")
    return _montar_resposta_inciso(inciso_id)


@router.delete("/incisos/{inciso_id}")
def remover_inciso_api(inciso_id: int, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    try:
        removido = remover_inciso(inciso_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not removido:
        raise HTTPException(404, "Inciso nao encontrado.")
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
    return listar_alineas(inciso_id=inciso_id)


@router.get("/alineas/{alinea_id}", response_model=AlineaOut)
def buscar_alinea_api(alinea_id: int, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    return _montar_resposta_alinea(alinea_id)


@router.post("/alineas", response_model=AlineaOut)
def criar_alinea_api(payload: AlineaCreateIn, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    if not buscar_inciso_por_id(payload.inciso_id):
        raise HTTPException(404, "Inciso nao encontrado.")
    try:
        alinea_id = criar_alinea(
            inciso_id=payload.inciso_id,
            identificador=_texto_obrigatorio(
                payload.identificador,
                "Identificador da alinea",
                max_len=40,
            ),
            descricao=_texto_obrigatorio(payload.descricao, "Descricao da alinea", max_len=5000),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return _montar_resposta_alinea(alinea_id)


@router.put("/alineas/{alinea_id}", response_model=AlineaOut)
def atualizar_alinea_api(
    alinea_id: int,
    payload: AlineaUpdateIn,
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    if not buscar_alinea_por_id(alinea_id):
        raise HTTPException(404, "Alinea nao encontrada.")
    if not buscar_inciso_por_id(payload.inciso_id):
        raise HTTPException(404, "Inciso nao encontrado.")
    try:
        alterado = atualizar_alinea(
            alinea_id=alinea_id,
            inciso_id=payload.inciso_id,
            identificador=_texto_obrigatorio(
                payload.identificador,
                "Identificador da alinea",
                max_len=40,
            ),
            descricao=_texto_obrigatorio(payload.descricao, "Descricao da alinea", max_len=5000),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not alterado:
        raise HTTPException(404, "Alinea nao encontrada.")
    return _montar_resposta_alinea(alinea_id)


@router.delete("/alineas/{alinea_id}")
def remover_alinea_api(alinea_id: int, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    try:
        removido = remover_alinea(alinea_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not removido:
        raise HTTPException(404, "Alinea nao encontrada.")
    return {"mensagem": "Alinea excluida com sucesso."}


@router.post("/alineas/{alinea_id}/excluir")
def remover_alinea_fallback_api(alinea_id: int, usuario=Depends(get_usuario_logado)):
    return remover_alinea_api(alinea_id, usuario)
