import json
import logging
import os
import re
import shutil
import uuid
from math import ceil
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from auth import get_usuario_logado
from db.catalogos import listar_turmas_ativas
from db.impressao import (
    alterar_prioridade,
    buscar_job,
    cancelar_job,
    criar_job,
    listar_fila,
    listar_jobs_por_usuario,
)
from db.usuarios import buscar_usuario_por_id
from services.cota_service import obter_cota_atual, validar_e_consumir_cota
from services.file_service import arquivo_suportado, converter_para_pdf, obter_extensao_arquivo
from services.pdf_service import contar_paginas_pdf

from .common import (
    exigir_gestor,
    resolver_usuario_professor_selecionado,
    usuario_pode_gerir_impressoes,
    usuario_tem_cota_ilimitada,
)
from .config import DEFAULT_PRINTER_NAME, FORMATOS_UPLOAD_DESCRICAO, SPOOL_DIR

router = APIRouter()
logger = logging.getLogger(__name__)


def contar_paginas_intervalo(intervalo: str, total_paginas: int) -> int:
    if not intervalo or not intervalo.strip():
        return total_paginas

    paginas = set()
    partes = [p.strip() for p in intervalo.split(",") if p.strip()]

    for parte in partes:
        if "-" in parte:
            pedacos = [n.strip() for n in parte.split("-")]
            if len(pedacos) != 2:
                raise HTTPException(400, f'Intervalo inválido: "{parte}"')
            inicio, fim = pedacos
            if not inicio.isdigit() or not fim.isdigit():
                raise HTTPException(400, f'Intervalo inválido: "{parte}"')
            inicio_num = int(inicio)
            fim_num = int(fim)
            if inicio_num <= 0 or fim_num <= 0 or inicio_num > fim_num:
                raise HTTPException(400, f'Intervalo inválido: "{parte}"')
            if fim_num > total_paginas:
                raise HTTPException(400, f"Página {fim_num} não existe no documento")
            for pagina in range(inicio_num, fim_num + 1):
                paginas.add(pagina)
        else:
            if not parte.isdigit():
                raise HTTPException(400, f'Página inválida: "{parte}"')
            pagina = int(parte)
            if pagina <= 0 or pagina > total_paginas:
                raise HTTPException(400, f"Página {pagina} não existe no documento")
            paginas.add(pagina)

    if not paginas:
        raise HTTPException(400, "Nenhuma página válida informada")

    return len(paginas)


def garantir_diretorio_spool() -> Path:
    caminho_spool = Path(SPOOL_DIR)
    caminho_spool.mkdir(parents=True, exist_ok=True)
    return caminho_spool


def remover_arquivo_se_existir(caminho: Path):
    try:
        caminho.unlink()
    except FileNotFoundError:
        return
    except OSError:
        return


def sanitizar_nome_arquivo(nome_arquivo: str) -> str:
    nome_base = os.path.basename(nome_arquivo or "").strip().replace(" ", "_")
    nome_limpo = re.sub(r"[^A-Za-z0-9._-]", "_", nome_base)
    if not nome_limpo:
        return "documento.pdf"
    if "." not in nome_limpo:
        return f"{nome_limpo}.pdf"
    return nome_limpo


def obter_layout_duas_por_folha(orientacao: str) -> str:
    if orientacao == "retrato":
        return "tblr"
    return "lrtb"


def montar_opcoes_cups(
    paginas_por_folha: int,
    duplex: bool,
    orientacao: str,
    intervalo_paginas: str,
):
    if duplex:
        sides = "two-sided-short-edge" if orientacao == "paisagem" else "two-sided-long-edge"
    else:
        sides = "one-sided"

    orientacao_cups = 4 if orientacao == "paisagem" else 3
    opcoes = {
        "number-up": paginas_por_folha,
        "sides": sides,
        "orientation-requested": orientacao_cups,
    }

    if orientacao == "paisagem":
        opcoes["landscape"] = True

    if paginas_por_folha == 2:
        opcoes["number-up-layout"] = obter_layout_duas_por_folha(orientacao)

    intervalo = (intervalo_paginas or "").strip()
    if intervalo:
        opcoes["page-ranges"] = intervalo

    return opcoes


def validar_parametros_impressao(
    copias: int,
    paginas_por_folha: int,
    orientacao: str,
):
    if copias <= 0:
        raise HTTPException(400, "Quantidade inválida")
    if paginas_por_folha not in (1, 2, 4):
        raise HTTPException(400, "Paginação por folha inválida")
    if orientacao not in ("retrato", "paisagem"):
        raise HTTPException(400, "Orientação inválida")


def obter_job_com_acesso(job_id: int, usuario: dict) -> dict:
    job = buscar_job(job_id)
    if not job:
        raise HTTPException(404, "Job não encontrado.")

    usuario_job_raw = job.get("usuario_id")
    usuario_job_id = int(usuario_job_raw) if usuario_job_raw is not None else None
    eh_gestor = usuario_pode_gerir_impressoes(usuario)
    eh_dono = usuario_job_id is not None and usuario_job_id == int(usuario["id"])
    if not eh_gestor and not eh_dono:
        raise HTTPException(403, "Você não pode acessar este job.")

    return job


def job_pode_ser_reutilizado(job: dict) -> bool:
    status = str(job.get("status") or "").strip().upper()
    return status in {"CONCLUIDO", "FINALIZADO"}


def resolver_caminho_pdf_job(job: dict) -> Path:
    arquivo_path = str(job.get("arquivo_path") or "").strip()
    if not arquivo_path:
        raise HTTPException(404, "Este job não possui arquivo disponível para reutilização.")

    caminho_spool = garantir_diretorio_spool().resolve(strict=False)
    caminho_job = Path(arquivo_path).resolve(strict=False)
    try:
        caminho_job.relative_to(caminho_spool)
    except ValueError as exc:
        raise HTTPException(409, "O arquivo vinculado a este job está fora do spool configurado.") from exc

    if not caminho_job.exists() or not caminho_job.is_file():
        raise HTTPException(404, "O arquivo deste job não está mais disponível no spool.")

    return caminho_job


def copiar_pdf_job_para_spool(caminho_origem: Path, nome_referencia: str) -> Path:
    nome_sanitizado = sanitizar_nome_arquivo(nome_referencia or caminho_origem.name or "documento.pdf")
    nome_base = Path(nome_sanitizado).stem or "documento"
    caminho_destino = garantir_diretorio_spool() / f"{uuid.uuid4().hex}_{nome_base}.pdf"
    try:
        shutil.copy2(caminho_origem, caminho_destino)
    except OSError as exc:
        raise HTTPException(
            500,
            "Falha ao preparar o arquivo do histórico para uma nova impressão.",
        ) from exc
    return caminho_destino


def criar_job_a_partir_pdf_pronto(
    *,
    caminho_arquivo: Path,
    nome_arquivo_exibicao: str,
    copias: int,
    paginas_por_folha: int,
    duplex: bool,
    orientacao: str,
    intervalo_paginas: str,
    usuario_responsavel: dict,
    remover_arquivo_em_falha: bool = True,
):
    def limpar_em_falha():
        if remover_arquivo_em_falha:
            remover_arquivo_se_existir(caminho_arquivo)

    try:
        paginas_pdf = contar_paginas_pdf(str(caminho_arquivo))
    except HTTPException:
        limpar_em_falha()
        raise
    except Exception as exc:
        limpar_em_falha()
        logger.exception("Falha ao contar paginas do PDF preparado para impressao: %s", caminho_arquivo)
        raise HTTPException(
            500,
            "Falha ao ler o PDF preparado para impressao.",
        ) from exc

    intervalo_normalizado = (intervalo_paginas or "").strip()
    try:
        paginas_selecionadas = contar_paginas_intervalo(intervalo_normalizado, paginas_pdf)
    except HTTPException:
        limpar_em_falha()
        raise
    except Exception as exc:
        limpar_em_falha()
        logger.exception("Falha ao validar intervalo de paginas para impressao: %s", caminho_arquivo)
        raise HTTPException(
            400,
            "Intervalo de paginas invalido para este documento.",
        ) from exc

    folhas_por_copia = ceil(paginas_selecionadas / paginas_por_folha)
    if duplex:
        folhas_por_copia = ceil(folhas_por_copia / 2)
    paginas_totais = folhas_por_copia * copias

    cota_ilimitada = usuario_tem_cota_ilimitada(usuario_responsavel)
    restante = None
    if not cota_ilimitada:
        try:
            autorizado, restante = validar_e_consumir_cota(
                usuario_id=usuario_responsavel["id"],
                paginas=paginas_totais,
            )
        except HTTPException:
            limpar_em_falha()
            raise
        except Exception as exc:
            limpar_em_falha()
            logger.exception(
                "Falha ao validar/consumir cota para usuario %s no envio de impressao",
                usuario_responsavel.get("id"),
            )
            raise HTTPException(
                500,
                "Falha ao validar a cota de impressao.",
            ) from exc

        if not autorizado:
            limpar_em_falha()
            raise HTTPException(
                403,
                f"Cota insuficiente. Documento consome {paginas_totais} páginas. Restam {restante}.",
            )

    opcoes_cups = montar_opcoes_cups(
        paginas_por_folha=paginas_por_folha,
        duplex=duplex,
        orientacao=orientacao,
        intervalo_paginas=intervalo_normalizado,
    )

    try:
        criar_job(
            usuario_id=usuario_responsavel["id"],
            arquivo=nome_arquivo_exibicao,
            arquivo_path=str(caminho_arquivo),
            copias=copias,
            paginas_totais=paginas_totais,
            paginas_por_folha=paginas_por_folha,
            duplex=duplex,
            orientacao=orientacao,
            intervalo_paginas=intervalo_normalizado,
            printer_name=DEFAULT_PRINTER_NAME,
            cups_options=json.dumps(opcoes_cups, ensure_ascii=True),
        )
    except HTTPException:
        limpar_em_falha()
        raise
    except Exception as exc:
        limpar_em_falha()
        logger.exception(
            "Falha ao registrar job de impressao para usuario %s",
            usuario_responsavel.get("id"),
        )
        raise HTTPException(
            500,
            "Falha ao registrar o job de impressao.",
        ) from exc

    return {
        "mensagem": "Job criado com sucesso",
        "paginas_documento": paginas_pdf,
        "paginas_selecionadas": paginas_selecionadas,
        "copias": copias,
        "paginas_consumidas": paginas_totais,
        "paginas_restantes": restante,
        "cota_ilimitada": cota_ilimitada,
    }


@router.get("/impressao/turmas")
def turmas_impressao(_usuario=Depends(get_usuario_logado)):
    turmas = []
    for turma in listar_turmas_ativas():
        turmas.append(
            {
                "id": int(turma["id"]),
                "nome": turma["nome"],
                "turno": str(turma.get("turno") or "").strip().upper(),
                "quantidade_estudantes": max(int(turma.get("quantidade_estudantes") or 0), 0),
            }
        )
    return turmas


@router.post("/imprimir")
def imprimir(
    copias: int = Form(...),
    arquivo: UploadFile = File(...),
    paginas_por_folha: int = Form(1),
    duplex: bool = Form(False),
    orientacao: str = Form("retrato"),
    intervalo_paginas: str = Form(""),
    professor_id: int | None = Form(None),
    usuario=Depends(get_usuario_logado),
):
    validar_parametros_impressao(copias, paginas_por_folha, orientacao)

    if not arquivo or not arquivo.filename:
        raise HTTPException(400, "Arquivo não enviado")

    if not arquivo_suportado(arquivo.filename):
        raise HTTPException(400, f"Formato não suportado. Envie {FORMATOS_UPLOAD_DESCRICAO}.")

    extensao_arquivo = obter_extensao_arquivo(arquivo.filename)

    usuario_responsavel = resolver_usuario_professor_selecionado(
        usuario,
        professor_id,
        contexto="solicitante da impressão",
        permitir_professor_com_acesso_coordenacao=True,
    )

    conteudo_arquivo = arquivo.file.read()
    if not conteudo_arquivo:
        raise HTTPException(400, "Arquivo vazio")

    caminho_spool = garantir_diretorio_spool()
    nome_arquivo_spool = f"{uuid.uuid4().hex}_{sanitizar_nome_arquivo(arquivo.filename)}"
    caminho_arquivo_original = caminho_spool / nome_arquivo_spool

    try:
        with caminho_arquivo_original.open("wb") as destino:
            destino.write(conteudo_arquivo)
    except OSError as exc:
        raise HTTPException(500, "Falha ao armazenar o arquivo para impressão.") from exc

    caminho_arquivo = caminho_arquivo_original
    caminho_convertido = caminho_arquivo_original.with_suffix(".pdf")
    try:
        caminho_arquivo = converter_para_pdf(caminho_arquivo_original, extensao_arquivo)
    except ValueError as exc:
        remover_arquivo_se_existir(caminho_arquivo_original)
        raise HTTPException(400, str(exc)) from exc
    except RuntimeError as exc:
        remover_arquivo_se_existir(caminho_arquivo_original)
        if caminho_convertido != caminho_arquivo_original:
            remover_arquivo_se_existir(caminho_convertido)
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        remover_arquivo_se_existir(caminho_arquivo_original)
        if caminho_convertido != caminho_arquivo_original:
            remover_arquivo_se_existir(caminho_convertido)
        raise HTTPException(500, "Falha ao preparar o arquivo para impressão.") from exc

    if caminho_arquivo != caminho_arquivo_original:
        remover_arquivo_se_existir(caminho_arquivo_original)

    return criar_job_a_partir_pdf_pronto(
        caminho_arquivo=caminho_arquivo,
        nome_arquivo_exibicao=arquivo.filename,
        copias=copias,
        paginas_por_folha=paginas_por_folha,
        duplex=duplex,
        orientacao=orientacao,
        intervalo_paginas=intervalo_paginas,
        usuario_responsavel=usuario_responsavel,
    )


@router.post("/impressao/preview")
def preview_impressao(
    arquivo: UploadFile = File(...),
    _usuario=Depends(get_usuario_logado),
):
    if not arquivo or not arquivo.filename:
        raise HTTPException(400, "Arquivo não enviado")

    if not arquivo_suportado(arquivo.filename):
        raise HTTPException(400, f"Formato não suportado. Envie {FORMATOS_UPLOAD_DESCRICAO}.")

    extensao_arquivo = obter_extensao_arquivo(arquivo.filename)
    conteudo_arquivo = arquivo.file.read()
    if not conteudo_arquivo:
        raise HTTPException(400, "Arquivo vazio")

    caminho_spool = garantir_diretorio_spool()
    nome_arquivo_spool = f"preview_{uuid.uuid4().hex}_{sanitizar_nome_arquivo(arquivo.filename)}"
    caminho_arquivo_original = caminho_spool / nome_arquivo_spool

    try:
        with caminho_arquivo_original.open("wb") as destino:
            destino.write(conteudo_arquivo)
    except OSError as exc:
        raise HTTPException(500, "Falha ao armazenar arquivo para pré-visualização.") from exc

    caminho_arquivo_pdf = caminho_arquivo_original
    caminho_convertido = caminho_arquivo_original.with_suffix(".pdf")

    try:
        caminho_arquivo_pdf = converter_para_pdf(caminho_arquivo_original, extensao_arquivo)
        conteudo_pdf = caminho_arquivo_pdf.read_bytes()
        if not conteudo_pdf:
            raise HTTPException(500, "Falha ao gerar PDF de pré-visualização.")
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, "Falha ao gerar pré-visualização do documento.") from exc
    finally:
        remover_arquivo_se_existir(caminho_arquivo_original)
        if caminho_convertido != caminho_arquivo_original:
            remover_arquivo_se_existir(caminho_convertido)

    return Response(
        content=conteudo_pdf,
        media_type="application/pdf",
        headers={"Cache-Control": "no-store"},
    )


@router.get("/fila")
def fila(usuario=Depends(get_usuario_logado)):
    exigir_gestor(usuario)
    return listar_fila()


@router.get("/jobs/{job_id}/preview")
def preview_job_historico(job_id: int, usuario=Depends(get_usuario_logado)):
    job = obter_job_com_acesso(job_id, usuario)
    if not job_pode_ser_reutilizado(job):
        raise HTTPException(409, "Apenas jobs concluídos podem ser reutilizados no preview.")

    caminho_arquivo = resolver_caminho_pdf_job(job)
    try:
        conteudo_pdf = caminho_arquivo.read_bytes()
    except OSError as exc:
        raise HTTPException(500, "Falha ao ler o arquivo vinculado a este job.") from exc

    if not conteudo_pdf:
        raise HTTPException(404, "O arquivo deste job está vazio ou indisponível.")

    return Response(
        content=conteudo_pdf,
        media_type="application/pdf",
        headers={"Cache-Control": "no-store"},
    )


@router.post("/jobs/{job_id}/reimprimir")
def reimprimir_job_historico(
    job_id: int,
    copias: int = Form(...),
    paginas_por_folha: int = Form(1),
    duplex: bool = Form(False),
    orientacao: str = Form("retrato"),
    intervalo_paginas: str = Form(""),
    professor_id: int | None = Form(None),
    usuario=Depends(get_usuario_logado),
):
    validar_parametros_impressao(copias, paginas_por_folha, orientacao)

    job = obter_job_com_acesso(job_id, usuario)
    if not job_pode_ser_reutilizado(job):
        raise HTTPException(409, "Apenas jobs concluídos podem ser reutilizados para nova impressão.")

    usuario_responsavel = resolver_usuario_professor_selecionado(
        usuario,
        professor_id,
        contexto="solicitante da reimpressão",
        permitir_professor_com_acesso_coordenacao=True,
    )

    caminho_origem = resolver_caminho_pdf_job(job)
    caminho_copia = copiar_pdf_job_para_spool(
        caminho_origem,
        str(job.get("arquivo") or caminho_origem.name),
    )

    return criar_job_a_partir_pdf_pronto(
        caminho_arquivo=caminho_copia,
        nome_arquivo_exibicao=str(job.get("arquivo") or caminho_origem.name),
        copias=copias,
        paginas_por_folha=paginas_por_folha,
        duplex=duplex,
        orientacao=orientacao,
        intervalo_paginas=intervalo_paginas,
        usuario_responsavel=usuario_responsavel,
    )


@router.post("/jobs/{job_id}/cancelar")
def cancelar(job_id: int, usuario=Depends(get_usuario_logado)):
    job = obter_job_com_acesso(job_id, usuario)

    usuario_job_raw = job.get("usuario_id")
    usuario_job_id = int(usuario_job_raw) if usuario_job_raw is not None else None
    usuario_job = (
        buscar_usuario_por_id(usuario_job_id, incluir_inativos=True)
        if usuario_job_id is not None
        else None
    )
    cota_ilimitada = bool(usuario_job and usuario_tem_cota_ilimitada(usuario_job))

    resultado = cancelar_job(job_id, estornar_cota=not cota_ilimitada)
    if not resultado.get("cancelado"):
        raise HTTPException(
            409,
            "Este job não pode mais ser cancelado (já está em impressão ou finalizado).",
        )

    paginas_restantes = None
    if usuario_job_id is not None and not cota_ilimitada:
        cota = obter_cota_atual(usuario_job_id)
        paginas_restantes = int(cota["restante"])

    return {
        "mensagem": "Job cancelado com sucesso.",
        "paginas_estornadas": int(resultado.get("paginas_estornadas") or 0),
        "paginas_restantes": paginas_restantes,
        "cota_ilimitada": cota_ilimitada,
    }


@router.post("/jobs/{job_id}/prioridade")
def prioridade(
    job_id: int,
    urgente: bool = True,
    usuario=Depends(get_usuario_logado),
):
    exigir_gestor(usuario)
    alterar_prioridade(job_id, urgente)
    return {"mensagem": "Prioridade atualizada"}


@router.get("/meus-jobs")
def meus_jobs(
    professor_id: int | None = None,
    usuario=Depends(get_usuario_logado),
):
    usuario_consulta = resolver_usuario_professor_selecionado(
        usuario,
        professor_id,
        contexto="na impressão",
        permitir_professor_com_acesso_coordenacao=True,
    )
    return listar_jobs_por_usuario(usuario_consulta["id"])


@router.get("/minha-cota")
def minha_cota(
    professor_id: int | None = None,
    usuario=Depends(get_usuario_logado),
):
    usuario_consulta = resolver_usuario_professor_selecionado(
        usuario,
        professor_id,
        contexto="na impressão",
        permitir_professor_com_acesso_coordenacao=True,
    )
    if usuario_tem_cota_ilimitada(usuario_consulta):
        return {
            "limite": None,
            "usadas": 0,
            "restante": None,
            "ilimitada": True,
        }

    cota = obter_cota_atual(usuario_consulta["id"])
    cota["ilimitada"] = False
    return cota
