import sqlite3
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from auth import get_usuario_logado
from db.apc import (
    atualizar_apc_envio,
    atualizar_apc_periodo,
    buscar_apc_envio_por_id,
    buscar_apc_envio_por_periodo_e_professor,
    buscar_apc_periodo_por_id,
    criar_apc_envio,
    criar_apc_periodo,
    excluir_apc_periodo,
    listar_anos_letivos_apc,
    listar_apc_envios,
    listar_apc_periodos,
)
from db.horario_escolar import listar_anos_letivos_horario_escolar, listar_horarios_escolares
from models import ApcEnvioOut, ApcPeriodoIn, ApcPeriodoOut, ApcPeriodoUpdateIn
from services.apc_service import (
    contexto_apc_anos,
    enriquecer_periodo_apc,
    intervalo_mes_referencia,
    montar_painel_periodo_apc,
    montar_painel_professor_apc,
    nome_arquivo_armazenado,
    normalizar_data_apc,
    normalizar_prazo_envio,
    ordenar_periodos_apc,
    periodo_apc_aberto,
    sanitizar_nome_arquivo,
    validar_mes_referencia,
)
from services.file_service import arquivo_suportado

from .common import normalizar_cargo_usuario, usuario_eh_professor, usuario_tem_acesso_coordenacao
from .config import APC_DIR, FORMATOS_UPLOAD_DESCRICAO

router = APIRouter()


def _pode_gerir_apc(usuario: dict) -> bool:
    return bool(usuario_tem_acesso_coordenacao(usuario))


def _exigir_gestao_apc(usuario: dict):
    if not _pode_gerir_apc(usuario):
        raise HTTPException(403, "Acesso negado.")
    return usuario


def _garantir_diretorio_apc() -> Path:
    caminho = Path(APC_DIR)
    caminho.mkdir(parents=True, exist_ok=True)
    return caminho


def _remover_arquivo_se_existir(caminho: Path):
    try:
        caminho.unlink()
    except FileNotFoundError:
        return
    except OSError:
        return


def _resolver_caminho_envio_seguro(caminho_arquivo: str) -> Path:
    caminho_base = _garantir_diretorio_apc().resolve(strict=False)
    caminho = Path(str(caminho_arquivo or "")).resolve(strict=False)
    try:
        caminho.relative_to(caminho_base)
    except ValueError as exc:
        raise HTTPException(409, "O arquivo vinculado a este envio esta fora do diretorio APC.") from exc

    if not caminho.exists() or not caminho.is_file():
        raise HTTPException(404, "Arquivo do envio nao encontrado.")
    return caminho


def _dados_periodo_payload(payload: ApcPeriodoIn | ApcPeriodoUpdateIn) -> dict:
    try:
        ano_letivo = int(payload.ano_letivo)
    except (TypeError, ValueError) as exc:
        raise HTTPException(400, "Ano letivo invalido.") from exc

    if ano_letivo < 2000 or ano_letivo > 2100:
        raise HTTPException(400, "Ano letivo invalido.")

    try:
        data_referencia = normalizar_data_apc(payload.data_referencia)
        prazo_envio = normalizar_prazo_envio(data_referencia, payload.prazo_envio)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    titulo = str(payload.titulo or "APC").strip() or "APC"
    observacao = str(payload.observacao or "").strip()
    return {
        "ano_letivo": ano_letivo,
        "data_referencia": data_referencia,
        "prazo_envio": prazo_envio,
        "titulo": titulo,
        "observacao": observacao,
    }


def _obter_horarios_periodo(periodo: dict, professor_id: int | None = None) -> list[dict]:
    periodo_norm = enriquecer_periodo_apc(periodo)
    return listar_horarios_escolares(
        ano_letivo=int(periodo_norm["ano_letivo"]),
        professor_id=professor_id,
        dia_semana=periodo_norm["dia_semana"],
    )


def _montar_resumo_calendario_para_usuario(periodo: dict, usuario: dict) -> dict | None:
    periodo_norm = enriquecer_periodo_apc(periodo)
    horarios = _obter_horarios_periodo(periodo_norm)

    if _pode_gerir_apc(usuario):
        painel = montar_painel_periodo_apc(
            periodo_norm,
            horarios,
            listar_apc_envios(periodo_id=int(periodo_norm["id"])),
        )
        return {
            **painel["periodo"],
            "total_elegiveis": painel["total_elegiveis"],
            "total_enviados": painel["total_enviados"],
            "total_pendentes": painel["total_pendentes"],
            "enviado": False,
            "total_aulas": 0,
        }

    painel_professor = montar_painel_professor_apc(
        periodo_norm,
        int(usuario["id"]),
        horarios,
        buscar_apc_envio_por_periodo_e_professor(int(periodo_norm["id"]), int(usuario["id"])),
    )
    if not painel_professor:
        return None

    return {
        **painel_professor["periodo"],
        "total_elegiveis": 1,
        "total_enviados": 1 if painel_professor["envio"] else 0,
        "total_pendentes": 0 if painel_professor["envio"] else 1,
        "enviado": painel_professor["envio"] is not None,
        "total_aulas": int(painel_professor["total_aulas"]),
    }


@router.get("/apc/contexto")
def obter_contexto_apc_api(usuario=Depends(get_usuario_logado)):
    anos_existentes = sorted(
        set(listar_anos_letivos_apc()) | set(listar_anos_letivos_horario_escolar())
    )
    return {
        "anos_letivos": contexto_apc_anos(anos_existentes),
        "ano_letivo_atual": datetime.now().year,
        "mes_atual": datetime.now().strftime("%Y-%m"),
        "hoje": datetime.now().date().isoformat(),
        "usuario": {
            "id": int(usuario["id"]),
            "nome": str(usuario.get("nome") or "").strip(),
            "cargo": normalizar_cargo_usuario(usuario),
            "pode_gerir": _pode_gerir_apc(usuario),
            "eh_professor": usuario_eh_professor(usuario),
        },
    }


@router.get("/apc/calendario")
def listar_calendario_apc_api(
    mes: str,
    ano_letivo: int | None = None,
    usuario=Depends(get_usuario_logado),
):
    try:
        mes_norm = validar_mes_referencia(mes)
        data_inicio, data_fim = intervalo_mes_referencia(mes_norm)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    periodos = ordenar_periodos_apc(
        listar_apc_periodos(
            ano_letivo=int(ano_letivo) if ano_letivo is not None else None,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )
    )

    itens = []
    for periodo in periodos:
        resumo = _montar_resumo_calendario_para_usuario(periodo, usuario)
        if resumo is None:
            continue
        itens.append(resumo)

    return {
        "mes": mes_norm,
        "ano_letivo": int(ano_letivo) if ano_letivo is not None else None,
        "periodos": itens,
    }


@router.get("/apc/periodos/{periodo_id}")
def obter_periodo_apc_api(periodo_id: int, usuario=Depends(get_usuario_logado)):
    periodo = buscar_apc_periodo_por_id(periodo_id)
    if not periodo:
        raise HTTPException(404, "Data de APC nao encontrada.")

    horarios = _obter_horarios_periodo(periodo)
    if _pode_gerir_apc(usuario):
        return montar_painel_periodo_apc(
            periodo,
            horarios,
            listar_apc_envios(periodo_id=periodo_id),
        )

    painel = montar_painel_professor_apc(
        periodo,
        int(usuario["id"]),
        horarios,
        buscar_apc_envio_por_periodo_e_professor(periodo_id, int(usuario["id"])),
    )
    if not painel:
        raise HTTPException(403, "Nenhuma APC prevista para voce nesta data.")
    return painel


@router.post("/apc/periodos", response_model=ApcPeriodoOut)
def criar_periodo_apc_api(payload: ApcPeriodoIn, usuario=Depends(get_usuario_logado)):
    _exigir_gestao_apc(usuario)
    dados = _dados_periodo_payload(payload)
    try:
        periodo = criar_apc_periodo(
            ano_letivo=dados["ano_letivo"],
            data_referencia=dados["data_referencia"],
            prazo_envio=dados["prazo_envio"],
            titulo=dados["titulo"],
            observacao=dados["observacao"],
            criado_por_usuario_id=int(usuario["id"]),
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, "Ja existe uma APC cadastrada para essa data no ano letivo.") from exc
    return enriquecer_periodo_apc(periodo)


@router.put("/apc/periodos/{periodo_id}", response_model=ApcPeriodoOut)
def atualizar_periodo_apc_api(
    periodo_id: int,
    payload: ApcPeriodoUpdateIn,
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestao_apc(usuario)
    if not buscar_apc_periodo_por_id(periodo_id):
        raise HTTPException(404, "Data de APC nao encontrada.")

    dados = _dados_periodo_payload(payload)
    try:
        periodo = atualizar_apc_periodo(
            periodo_id=periodo_id,
            ano_letivo=dados["ano_letivo"],
            data_referencia=dados["data_referencia"],
            prazo_envio=dados["prazo_envio"],
            titulo=dados["titulo"],
            observacao=dados["observacao"],
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, "Ja existe uma APC cadastrada para essa data no ano letivo.") from exc

    if not periodo:
        raise HTTPException(404, "Data de APC nao encontrada.")
    return enriquecer_periodo_apc(periodo)


@router.delete("/apc/periodos/{periodo_id}")
def excluir_periodo_apc_api(periodo_id: int, usuario=Depends(get_usuario_logado)):
    _exigir_gestao_apc(usuario)
    if not buscar_apc_periodo_por_id(periodo_id):
        raise HTTPException(404, "Data de APC nao encontrada.")
    try:
        removido = excluir_apc_periodo(periodo_id)
    except sqlite3.IntegrityError as exc:
        raise HTTPException(
            409,
            "Nao e possivel excluir esta data porque ja existem arquivos enviados.",
        ) from exc
    if not removido:
        raise HTTPException(404, "Data de APC nao encontrada.")
    return {"mensagem": "Data de APC removida com sucesso."}


@router.post("/apc/periodos/{periodo_id}/envio", response_model=ApcEnvioOut)
def enviar_arquivo_apc_api(
    periodo_id: int,
    arquivo: UploadFile = File(...),
    usuario=Depends(get_usuario_logado),
):
    if not usuario_eh_professor(usuario):
        raise HTTPException(403, "Somente professores podem enviar APC.")

    periodo = buscar_apc_periodo_por_id(periodo_id)
    if not periodo:
        raise HTTPException(404, "Data de APC nao encontrada.")
    periodo_norm = enriquecer_periodo_apc(periodo)

    if not periodo_apc_aberto(periodo_norm):
        raise HTTPException(409, "O prazo de envio desta APC ja foi encerrado.")

    if not arquivo or not arquivo.filename:
        raise HTTPException(400, "Arquivo nao enviado.")
    if not arquivo_suportado(arquivo.filename):
        raise HTTPException(400, f"Formato nao suportado. Envie {FORMATOS_UPLOAD_DESCRICAO}.")

    horarios = _obter_horarios_periodo(periodo_norm, professor_id=int(usuario["id"]))
    envio_existente = buscar_apc_envio_por_periodo_e_professor(periodo_id, int(usuario["id"]))
    painel = montar_painel_professor_apc(periodo_norm, int(usuario["id"]), horarios, envio_existente)
    if not painel:
        raise HTTPException(403, "Nao ha APC prevista para voce nesta data.")

    conteudo = arquivo.file.read()
    if not conteudo:
        raise HTTPException(400, "Arquivo vazio.")

    diretorio = _garantir_diretorio_apc()
    nome_destino = nome_arquivo_armazenado(periodo_id, int(usuario["id"]), arquivo.filename)
    caminho_destino = diretorio / nome_destino

    try:
        with caminho_destino.open("wb") as destino:
            destino.write(conteudo)
    except OSError as exc:
        raise HTTPException(500, "Falha ao armazenar o arquivo da APC.") from exc

    try:
        if envio_existente:
            envio = atualizar_apc_envio(
                envio_id=int(envio_existente["id"]),
                arquivo_nome_original=sanitizar_nome_arquivo(arquivo.filename),
                arquivo_path=str(caminho_destino),
                arquivo_tamanho=len(conteudo),
                arquivo_tipo=str(arquivo.content_type or "").strip(),
            )
            caminho_antigo = Path(str(envio_existente.get("arquivo_path") or "").strip())
            if caminho_antigo and caminho_antigo != caminho_destino:
                _remover_arquivo_se_existir(caminho_antigo)
        else:
            envio = criar_apc_envio(
                periodo_id=periodo_id,
                professor_usuario_id=int(usuario["id"]),
                arquivo_nome_original=sanitizar_nome_arquivo(arquivo.filename),
                arquivo_path=str(caminho_destino),
                arquivo_tamanho=len(conteudo),
                arquivo_tipo=str(arquivo.content_type or "").strip(),
            )
    except sqlite3.IntegrityError as exc:
        _remover_arquivo_se_existir(caminho_destino)
        raise HTTPException(409, "Conflito ao registrar o envio da APC.") from exc
    except Exception:
        _remover_arquivo_se_existir(caminho_destino)
        raise

    if not envio:
        _remover_arquivo_se_existir(caminho_destino)
        raise HTTPException(500, "Falha ao registrar o envio da APC.")
    return envio


@router.get("/apc/envios/{envio_id}/arquivo")
def baixar_arquivo_apc_api(envio_id: int, usuario=Depends(get_usuario_logado)):
    envio = buscar_apc_envio_por_id(envio_id)
    if not envio:
        raise HTTPException(404, "Envio nao encontrado.")

    professor_id = int(envio.get("professor_id") or 0)
    if not _pode_gerir_apc(usuario) and int(usuario["id"]) != professor_id:
        raise HTTPException(403, "Voce nao pode acessar este arquivo.")

    caminho = _resolver_caminho_envio_seguro(envio.get("arquivo_path"))
    media_type = str(envio.get("arquivo_tipo") or "").strip() or "application/octet-stream"
    return FileResponse(
        path=str(caminho),
        filename=str(envio.get("arquivo_nome_original") or caminho.name),
        media_type=media_type,
    )
