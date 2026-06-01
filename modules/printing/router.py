import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from auth import get_usuario_logado
from modules.printing import repository
from modules.printing.config import (
    DEFAULT_PRINTER_NAME,
    FORMATOS_UPLOAD_DESCRICAO,
    get_default_printer_name,
    get_spool_dir,
    get_upload_formats_description,
)
from modules.printing.dependencies import (
    buscar_usuario_por_id,
    require_print_manager,
    resolve_print_teacher,
    user_can_manage_prints,
    user_has_unlimited_quota,
)
from modules.printing.service import (
    cancel_print_job,
    create_job_from_ready_pdf,
    ensure_print_is_available,
    get_formatted_print_status,
    get_print_quota_response,
    list_formatted_print_classes,
    list_print_tags,
    list_serialized_jobs_for_user,
    prepare_uploaded_file_for_preview,
    prepare_uploaded_file_for_print,
    read_reusable_job_pdf_content,
    reprint_job_from_history,
    validate_print_parameters,
)
from services.cota_service import obter_cota_atual, validar_e_consumir_cota
from services.file_service import arquivo_suportado, converter_para_pdf, obter_extensao_arquivo
from services.pdf_service import contar_paginas_pdf

router = APIRouter()
logger = logging.getLogger(__name__)


def _ensure_spool_dir() -> Path:
    caminho_spool = Path(get_spool_dir())
    caminho_spool.mkdir(parents=True, exist_ok=True)
    return caminho_spool


def _remove_file_if_exists(caminho: Path):
    try:
        caminho.unlink()
    except FileNotFoundError:
        return
    except OSError:
        return


@router.get("/impressao/turmas")
def turmas_impressao(_usuario=Depends(get_usuario_logado)):
    return list_formatted_print_classes()


@router.get("/impressao/tags")
def tags_impressao(_usuario=Depends(get_usuario_logado)):
    return list_print_tags()


@router.get("/impressao/status")
def status_impressao(_usuario=Depends(get_usuario_logado)):
    return get_formatted_print_status()


@router.post("/imprimir")
def imprimir(
    copias: int = Form(...),
    arquivo: UploadFile = File(...),
    paginas_por_folha: int = Form(1),
    duplex: bool = Form(False),
    orientacao: str = Form("retrato"),
    intervalo_paginas: str = Form(""),
    tags: list[str] = Form(default=[]),
    professor_id: int | None = Form(None),
    usuario=Depends(get_usuario_logado),
):
    ensure_print_is_available(get_formatted_print_status())
    validate_print_parameters(copias, paginas_por_folha, orientacao)

    if not arquivo or not arquivo.filename:
        raise HTTPException(400, "Arquivo não enviado")

    if not arquivo_suportado(arquivo.filename):
        raise HTTPException(400, f"Formato não suportado. Envie {FORMATOS_UPLOAD_DESCRICAO}.")

    usuario_responsavel = resolve_print_teacher(
        usuario,
        professor_id,
        contexto="solicitante da impressão",
        permitir_professor_com_acesso_coordenacao=True,
    )

    conteudo_arquivo = arquivo.file.read()
    resultado_preparo = prepare_uploaded_file_for_print(
        nome_arquivo=arquivo.filename,
        conteudo_arquivo=conteudo_arquivo,
        spool_dir=_ensure_spool_dir(),
        obter_extensao_arquivo=obter_extensao_arquivo,
        converter_para_pdf=converter_para_pdf,
        remover_arquivo_se_existir=_remove_file_if_exists,
    )

    return create_job_from_ready_pdf(
        caminho_arquivo=resultado_preparo["caminho_arquivo"],
        nome_arquivo_exibicao=arquivo.filename,
        copias=copias,
        paginas_por_folha=paginas_por_folha,
        duplex=duplex,
        orientacao=orientacao,
        intervalo_paginas=intervalo_paginas,
        usuario_responsavel=usuario_responsavel,
        tags_impressao=tags,
        remover_arquivo_em_falha=True,
        contar_paginas_pdf=contar_paginas_pdf,
        validar_e_consumir_cota=validar_e_consumir_cota,
        usuario_tem_cota_ilimitada=user_has_unlimited_quota,
        default_printer_name=DEFAULT_PRINTER_NAME,
        logger=logger,
        remover_arquivo_se_existir=_remove_file_if_exists,
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

    conteudo_arquivo = arquivo.file.read()
    resultado_preview = prepare_uploaded_file_for_preview(
        nome_arquivo=arquivo.filename,
        conteudo_arquivo=conteudo_arquivo,
        spool_dir=_ensure_spool_dir(),
        obter_extensao_arquivo=obter_extensao_arquivo,
        converter_para_pdf=converter_para_pdf,
        remover_arquivo_se_existir=_remove_file_if_exists,
    )

    return Response(
        content=resultado_preview["conteudo_pdf"],
        media_type="application/pdf",
        headers={"Cache-Control": "no-store"},
    )


@router.get("/fila")
def fila(usuario=Depends(get_usuario_logado)):
    require_print_manager(usuario)
    return repository.list_queue()


@router.get("/jobs/{job_id}/preview")
def preview_job_historico(job_id: int, usuario=Depends(get_usuario_logado)):
    _job, _caminho_arquivo, conteudo_pdf = read_reusable_job_pdf_content(
        job_id=job_id,
        usuario=usuario,
        spool_dir=_ensure_spool_dir(),
        usuario_pode_gerir_impressoes=user_can_manage_prints,
    )
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
    tags: list[str] = Form(default=[]),
    professor_id: int | None = Form(None),
    usuario=Depends(get_usuario_logado),
):
    ensure_print_is_available(get_formatted_print_status())
    validate_print_parameters(copias, paginas_por_folha, orientacao)

    usuario_responsavel = resolve_print_teacher(
        usuario,
        professor_id,
        contexto="solicitante da reimpressão",
        permitir_professor_com_acesso_coordenacao=True,
    )

    return reprint_job_from_history(
        job_id=job_id,
        copias=copias,
        paginas_por_folha=paginas_por_folha,
        duplex=duplex,
        orientacao=orientacao,
        intervalo_paginas=intervalo_paginas,
        tags_impressao=tags,
        usuario=usuario,
        usuario_responsavel=usuario_responsavel,
        spool_dir=_ensure_spool_dir(),
        contar_paginas_pdf=contar_paginas_pdf,
        validar_e_consumir_cota=validar_e_consumir_cota,
        usuario_pode_gerir_impressoes=user_can_manage_prints,
        usuario_tem_cota_ilimitada=user_has_unlimited_quota,
        default_printer_name=DEFAULT_PRINTER_NAME,
        logger=logger,
        remover_arquivo_se_existir=_remove_file_if_exists,
    )


@router.post("/jobs/{job_id}/cancelar")
def cancelar(job_id: int, usuario=Depends(get_usuario_logado)):
    return cancel_print_job(
        job_id=job_id,
        usuario=usuario,
        usuario_pode_gerir_impressoes=user_can_manage_prints,
        buscar_usuario_por_id=buscar_usuario_por_id,
        usuario_tem_cota_ilimitada=user_has_unlimited_quota,
        obter_cota_atual=obter_cota_atual,
    )


@router.post("/jobs/{job_id}/prioridade")
def prioridade(
    job_id: int,
    urgente: bool = True,
    usuario=Depends(get_usuario_logado),
):
    require_print_manager(usuario)
    repository.update_job_priority(job_id, urgente)
    return {"mensagem": "Prioridade atualizada"}


@router.get("/meus-jobs")
def meus_jobs(
    professor_id: int | None = None,
    usuario=Depends(get_usuario_logado),
):
    usuario_consulta = resolve_print_teacher(
        usuario,
        professor_id,
        contexto="na impressão",
        permitir_professor_com_acesso_coordenacao=True,
    )
    return list_serialized_jobs_for_user(usuario_consulta["id"])


@router.get("/minha-cota")
def minha_cota(
    professor_id: int | None = None,
    usuario=Depends(get_usuario_logado),
):
    usuario_consulta = resolve_print_teacher(
        usuario,
        professor_id,
        contexto="na impressão",
        permitir_professor_com_acesso_coordenacao=True,
    )
    return get_print_quota_response(
        usuario_consulta,
        obter_cota_atual=obter_cota_atual,
        usuario_tem_cota_ilimitada=user_has_unlimited_quota,
    )
