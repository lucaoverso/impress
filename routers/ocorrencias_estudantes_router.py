from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from auth import get_usuario_logado
from repositories.ocorrencias_repository import (
    atualizar_estudante,
    atualizar_status_estudante,
    buscar_estudante_por_id,
    criar_estudante,
    listar_estudantes,
    remover_estudante,
)
from schemas.ocorrencias_schemas import (
    EstudanteCreateIn,
    EstudanteOut,
    EstudanteStatusIn,
    EstudanteUpdateIn,
    ImportacaoCsvOut,
)
from services.csv_import_service import importar_estudantes_arquivo
from routers.ocorrencias_common import (
    _exigir_gestor,
    _ler_upload_estudantes,
    _montar_resposta_estudante,
    _texto_obrigatorio,
    _validar_turma_id,
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
    turma_id_filtro = _validar_turma_id(turma_id) if turma_id is not None else None
    return listar_estudantes(
        incluir_inativos=incluir_inativos,
        nome=str(nome or "").strip() or None,
        turma_id=turma_id_filtro,
    )


@router.get("/estudantes/{estudante_id}", response_model=EstudanteOut)
def buscar_estudante_api(estudante_id: int, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    return _montar_resposta_estudante(estudante_id)


@router.post("/estudantes", response_model=EstudanteOut)
def criar_estudante_api(payload: EstudanteCreateIn, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    turma_id = _validar_turma_id(payload.turma_id)
    try:
        estudante_id = criar_estudante(
            nome=_texto_obrigatorio(payload.nome, "Nome do estudante"),
            turma_id=turma_id,
            ativo=True,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return _montar_resposta_estudante(estudante_id)


@router.post("/estudantes/importar", response_model=ImportacaoCsvOut)
@router.post("/estudantes/importar-csv", response_model=ImportacaoCsvOut)
def importar_estudantes_arquivo_api(
    arquivo: UploadFile = File(...),
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    try:
        conteudo, nome_arquivo, tipo_conteudo = _ler_upload_estudantes(arquivo)
        return importar_estudantes_arquivo(
            conteudo,
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
    if not buscar_estudante_por_id(estudante_id):
        raise HTTPException(404, "Estudante nao encontrado.")

    turma_id = _validar_turma_id(payload.turma_id)
    try:
        alterado = atualizar_estudante(
            estudante_id=estudante_id,
            nome=_texto_obrigatorio(payload.nome, "Nome do estudante"),
            turma_id=turma_id,
            ativo=bool(payload.ativo),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    if not alterado:
        raise HTTPException(404, "Estudante nao encontrado.")
    return _montar_resposta_estudante(estudante_id)


@router.put("/estudantes/{estudante_id}/status")
def atualizar_status_estudante_api(
    estudante_id: int,
    payload: EstudanteStatusIn,
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    alterado = atualizar_status_estudante(estudante_id, bool(payload.ativo))
    if not alterado:
        raise HTTPException(404, "Estudante nao encontrado.")
    return {"mensagem": "Status do estudante atualizado com sucesso."}


@router.delete("/estudantes/{estudante_id}")
def remover_estudante_api(estudante_id: int, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    removido, ocorrencias_desvinculadas = remover_estudante(estudante_id)
    if not removido:
        raise HTTPException(404, "Estudante nao encontrado.")
    return {
        "mensagem": "Estudante excluido com sucesso.",
        "ocorrencias_desvinculadas": ocorrencias_desvinculadas,
    }


@router.post("/estudantes/{estudante_id}/excluir")
def remover_estudante_fallback_api(estudante_id: int, usuario=Depends(get_usuario_logado)):
    return remover_estudante_api(estudante_id, usuario)
