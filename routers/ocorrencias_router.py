import re
import unicodedata
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile

from auth import get_usuario_logado
from db.catalogos import buscar_turma_por_id
from repositories.ocorrencias_repository import (
    atualizar_alinea,
    atualizar_artigo,
    atualizar_inciso,
    atualizar_lei,
    atualizar_estudante,
    atualizar_regimento_item,
    atualizar_status_regimento_item,
    atualizar_status_estudante,
    buscar_alinea_por_id,
    buscar_artigo_por_id,
    buscar_estudante_por_id,
    buscar_inciso_por_id,
    buscar_lei_por_id,
    buscar_ocorrencia_por_id,
    buscar_regimento_item_por_id,
    criar_alinea,
    criar_artigo,
    criar_estudante,
    criar_inciso,
    criar_lei,
    criar_regimento_item,
    listar_alineas,
    listar_artigos,
    listar_estudantes,
    listar_incisos,
    listar_leis,
    listar_regimento_itens,
    remover_alinea,
    remover_artigo,
    remover_estudante,
    remover_inciso,
    remover_lei,
    remover_ocorrencia,
    remover_regimento_item,
)
from schemas.ocorrencias_schemas import (
    AlineaCreateIn,
    AlineaOut,
    AlineaUpdateIn,
    ArtigoCreateIn,
    ArtigoOut,
    ArtigoUpdateIn,
    EstudanteCreateIn,
    EstudanteOut,
    EstudanteStatusIn,
    EstudanteUpdateIn,
    ImportacaoCsvOut,
    IncisoCreateIn,
    IncisoOut,
    IncisoUpdateIn,
    LeiCreateIn,
    LeiOut,
    LeiUpdateIn,
    OcorrenciaCreateIn,
    OcorrenciaOut,
    OcorrenciaUpdateIn,
    RegimentoItemCreateIn,
    RegimentoItemOut,
    RegimentoItemStatusIn,
    RegimentoItemUpdateIn,
)
from services.csv_import_service import importar_base_legal_arquivo, importar_estudantes_arquivo
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
from services.ocorrencia_pdf_service import gerar_pdf_ocorrencia_registro
from routers.common import usuario_tem_acesso_coordenacao

router = APIRouter()

def _model_to_dict(model, *, exclude_unset: bool = False) -> dict:
    if hasattr(model, "model_dump"):
        return model.model_dump(exclude_unset=exclude_unset)
    return model.dict(exclude_unset=exclude_unset)


def _exigir_gestor(usuario: dict):
    if not usuario_tem_acesso_coordenacao(usuario):
        raise HTTPException(403, "Acesso negado")
    return usuario


def _texto_obrigatorio(valor: str | None, campo: str, *, max_len: int = 255) -> str:
    texto = str(valor or "").strip()
    if not texto:
        raise HTTPException(400, f"{campo} e obrigatorio.")
    if len(texto) > max_len:
        raise HTTPException(400, f"{campo} excede o limite de {max_len} caracteres.")
    return texto


def _texto_opcional(valor: str | None, *, max_len: int = 255) -> str | None:
    texto = str(valor or "").strip()
    if not texto:
        return None
    if len(texto) > max_len:
        raise HTTPException(400, f"Texto excede o limite de {max_len} caracteres.")
    return texto


def _validar_data_iso(valor: str, campo: str) -> str:
    texto = _texto_obrigatorio(valor, campo, max_len=20)
    try:
        data = datetime.strptime(texto, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(400, f"{campo} invalida. Use o formato YYYY-MM-DD.") from exc
    return data.isoformat()


def _validar_data_opcional(valor: str | None, campo: str) -> str | None:
    if valor is None:
        return None
    texto = str(valor).strip()
    if not texto:
        return None
    return _validar_data_iso(texto, campo)


def _validar_turma_id(turma_id: int) -> int:
    try:
        turma_id_valor = int(turma_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(400, "Turma invalida.") from exc
    if turma_id_valor <= 0:
        raise HTTPException(400, "Turma invalida.")

    turma = buscar_turma_por_id(turma_id_valor)
    if not turma:
        raise HTTPException(400, "Turma invalida.")
    return turma_id_valor


def _montar_resposta_ocorrencia(ocorrencia_id: int) -> dict:
    ocorrencia = buscar_ocorrencia_por_id(ocorrencia_id)
    if not ocorrencia:
        raise HTTPException(404, "Ocorrencia nao encontrada.")
    return ocorrencia


def _slug_ascii(texto: str) -> str:
    texto_normalizado = unicodedata.normalize("NFKD", str(texto or "").strip())
    texto_ascii = texto_normalizado.encode("ascii", "ignore").decode("ascii")
    texto_limpo = re.sub(r"[^A-Za-z0-9]+", "_", texto_ascii).strip("_").lower()
    return texto_limpo or "ocorrencia"


def _nome_arquivo_pdf_ocorrencia(ocorrencia: dict) -> str:
    estudante = _slug_ascii(ocorrencia.get("nome_estudante") or "ocorrencia")
    data = str(ocorrencia.get("data_ocorrencia") or "").strip() or datetime.now().date().isoformat()
    data_limpa = re.sub(r"[^0-9-]+", "", data) or datetime.now().date().isoformat()
    return f"registro_ocorrencia_{estudante}_{data_limpa}.pdf"


def _montar_resposta_regimento_item(regimento_item_id: int) -> dict:
    item = buscar_regimento_item_por_id(regimento_item_id)
    if not item:
        raise HTTPException(404, "Item do regimento nao encontrado.")
    return item


def _montar_resposta_lei(lei_id: int) -> dict:
    lei = buscar_lei_por_id(lei_id)
    if not lei:
        raise HTTPException(404, "Lei nao encontrada.")
    return lei


def _montar_resposta_artigo(artigo_id: int) -> dict:
    artigo = buscar_artigo_por_id(artigo_id)
    if not artigo:
        raise HTTPException(404, "Artigo nao encontrado.")
    return artigo


def _montar_resposta_inciso(inciso_id: int) -> dict:
    inciso = buscar_inciso_por_id(inciso_id)
    if not inciso:
        raise HTTPException(404, "Inciso nao encontrado.")
    return inciso


def _montar_resposta_alinea(alinea_id: int) -> dict:
    alinea = buscar_alinea_por_id(alinea_id)
    if not alinea:
        raise HTTPException(404, "Alinea nao encontrada.")
    return alinea


def _normalizar_payload_regimento(payload) -> dict:
    dados_brutos = _model_to_dict(payload, exclude_unset=False)
    lei_nome = (
        _texto_obrigatorio(
            dados_brutos.get("lei_nome"),
            "Lei",
            max_len=120,
        )
        if str(dados_brutos.get("lei_nome") or "").strip()
        else "Base legal"
    )

    artigo_numero = _texto_obrigatorio(
        dados_brutos.get("artigo_numero") or dados_brutos.get("artigo"),
        "Numero do artigo",
        max_len=120,
    )
    artigo_descricao = _texto_obrigatorio(
        dados_brutos.get("artigo_descricao") or dados_brutos.get("descricao"),
        "Descricao do artigo",
        max_len=5000,
    )

    inciso_numero = _texto_opcional(dados_brutos.get("inciso_numero"), max_len=40)
    inciso_descricao = _texto_opcional(dados_brutos.get("inciso_descricao"), max_len=5000)
    alinea_identificador = _texto_opcional(
        dados_brutos.get("alinea_identificador"),
        max_len=40,
    )
    alinea_descricao = _texto_opcional(dados_brutos.get("alinea_descricao"), max_len=5000)

    if bool(inciso_numero) != bool(inciso_descricao):
        raise HTTPException(400, "Inciso e descricao do inciso devem ser informados juntos.")
    if alinea_identificador and not inciso_numero:
        raise HTTPException(400, "Informe um inciso antes de cadastrar uma alinea.")
    if bool(alinea_identificador) != bool(alinea_descricao):
        raise HTTPException(400, "Alinea e descricao da alinea devem ser informadas juntas.")

    return {
        "lei_nome": lei_nome,
        "artigo_numero": artigo_numero,
        "artigo_descricao": artigo_descricao,
        "inciso_numero": inciso_numero,
        "inciso_descricao": inciso_descricao,
        "alinea_identificador": alinea_identificador,
        "alinea_descricao": alinea_descricao,
    }


def _montar_resposta_estudante(estudante_id: int) -> dict:
    estudante = buscar_estudante_por_id(estudante_id)
    if not estudante:
        raise HTTPException(404, "Estudante nao encontrado.")
    return estudante


def _ler_upload_estudantes(arquivo: UploadFile) -> tuple[bytes, str, str]:
    nome_arquivo = str(getattr(arquivo, "filename", "") or "").strip()
    if not nome_arquivo:
        raise HTTPException(400, "Arquivo de estudantes nao enviado.")

    tipo_conteudo = str(getattr(arquivo, "content_type", "") or "").lower()
    extensao_valida = nome_arquivo.lower().endswith(".json") or nome_arquivo.lower().endswith(
        ".csv"
    )
    tipo_valido = "json" in tipo_conteudo or "csv" in tipo_conteudo or "text/plain" in tipo_conteudo
    if not extensao_valida and not tipo_valido:
        raise HTTPException(400, "Envie um arquivo JSON ou CSV valido.")

    conteudo = arquivo.file.read()
    if not conteudo:
        raise HTTPException(400, "Arquivo de estudantes vazio.")
    return conteudo, nome_arquivo, tipo_conteudo


def _ler_upload_base_legal(arquivo: UploadFile) -> tuple[bytes, str, str]:
    nome_arquivo = str(getattr(arquivo, "filename", "") or "").strip()
    if not nome_arquivo:
        raise HTTPException(400, "Arquivo da base legal nao enviado.")

    tipo_conteudo = str(getattr(arquivo, "content_type", "") or "").lower()
    extensao_valida = nome_arquivo.lower().endswith(".json") or nome_arquivo.lower().endswith(
        ".csv"
    )
    tipo_valido = "json" in tipo_conteudo or "csv" in tipo_conteudo or "text/plain" in tipo_conteudo
    if not extensao_valida and not tipo_valido:
        raise HTTPException(400, "Envie um arquivo JSON ou CSV valido.")

    conteudo = arquivo.file.read()
    if not conteudo:
        raise HTTPException(400, "Arquivo da base legal vazio.")
    return conteudo, nome_arquivo, tipo_conteudo


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

    status_filtro = None
    if status is not None and str(status).strip():
        status_filtro = _validar_status(status)

    tipo_registro_filtro = None
    if tipo_registro is not None and str(tipo_registro).strip():
        tipo_registro_filtro = _validar_tipo_registro(tipo_registro)

    data_inicial_norm = _validar_data_opcional(data_inicial, "Data inicial")
    data_final_norm = _validar_data_opcional(data_final, "Data final")
    if data_inicial_norm and data_final_norm and data_inicial_norm > data_final_norm:
        raise HTTPException(400, "Periodo invalido: data inicial maior que data final.")

    turma_id_filtro = None
    if turma_id is not None:
        turma_id_filtro = _validar_turma_id(turma_id)

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


@router.get("/estudantes", response_model=list[EstudanteOut])
def listar_estudantes_api(
    nome: str | None = Query(default=None),
    turma_id: int | None = Query(default=None),
    incluir_inativos: bool = Query(default=True),
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    turma_id_filtro = None
    if turma_id is not None:
        turma_id_filtro = _validar_turma_id(turma_id)

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
        lei_id = criar_lei(
            nome=_texto_obrigatorio(payload.nome, "Nome da lei", max_len=120),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return _montar_resposta_lei(lei_id)


@router.put("/leis/{lei_id}", response_model=LeiOut)
def atualizar_lei_api(
    lei_id: int,
    payload: LeiUpdateIn,
    usuario=Depends(get_usuario_logado),
):
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
                payload.identificador, "Identificador da alinea", max_len=40
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
                payload.identificador, "Identificador da alinea", max_len=40
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
    regimento_item_id: int, usuario=Depends(get_usuario_logado)
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
