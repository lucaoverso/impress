import json
import logging
import shutil
import uuid
from math import ceil
from pathlib import Path

from fastapi import HTTPException

from modules.printing import repository
from modules.printing.job_access import get_job_with_access
from modules.printing.policies import (
    build_cups_options,
    count_interval_pages,
    print_job_can_be_reused,
    resolve_job_pdf_path,
    resolve_print_tags,
    sanitize_file_name,
    validate_required_tags,
)


def copy_job_pdf_to_spool(
    *,
    caminho_origem: Path,
    nome_referencia: str,
    spool_dir: Path,
):
    nome_sanitizado = sanitize_file_name(nome_referencia or caminho_origem.name or "documento.pdf")
    nome_base = Path(nome_sanitizado).stem or "documento"
    caminho_destino = spool_dir / f"{uuid.uuid4().hex}_{nome_base}.pdf"
    try:
        shutil.copy2(caminho_origem, caminho_destino)
    except OSError as exc:
        raise HTTPException(
            500,
            "Falha ao preparar o arquivo do histórico para uma nova impressão.",
        ) from exc
    return caminho_destino


def create_job_from_ready_pdf(
    *,
    caminho_arquivo: Path,
    nome_arquivo_exibicao: str,
    copias: int,
    paginas_por_folha: int,
    duplex: bool,
    orientacao: str,
    intervalo_paginas: str,
    usuario_responsavel: dict,
    tags_impressao: list[str] | None,
    remover_arquivo_em_falha: bool,
    contar_paginas_pdf,
    validar_e_consumir_cota,
    usuario_tem_cota_ilimitada,
    criar_job=None,
    default_printer_name: str,
    logger: logging.Logger,
    remover_arquivo_se_existir,
):
    criar_job_fn = criar_job or repository.create_job

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
        paginas_selecionadas = count_interval_pages(intervalo_normalizado, paginas_pdf)
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

    opcoes_cups = build_cups_options(
        paginas_por_folha=paginas_por_folha,
        duplex=duplex,
        orientacao=orientacao,
        intervalo_paginas=intervalo_normalizado,
    )
    tags_normalizadas = resolve_print_tags(tags_impressao)
    validate_required_tags(tags_normalizadas)

    try:
        criar_job_fn(
            usuario_id=usuario_responsavel["id"],
            arquivo=nome_arquivo_exibicao,
            arquivo_path=str(caminho_arquivo),
            copias=copias,
            paginas_totais=paginas_totais,
            paginas_por_folha=paginas_por_folha,
            duplex=duplex,
            orientacao=orientacao,
            intervalo_paginas=intervalo_normalizado,
            printer_name=default_printer_name,
            cups_options=json.dumps(opcoes_cups, ensure_ascii=True),
            tags_json=json.dumps(tags_normalizadas, ensure_ascii=False),
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
        "tags": tags_normalizadas,
    }


def reprint_job_from_history(
    *,
    job_id: int,
    copias: int,
    paginas_por_folha: int,
    duplex: bool,
    orientacao: str,
    intervalo_paginas: str,
    tags_impressao: list[str] | None,
    usuario: dict,
    usuario_responsavel: dict,
    spool_dir: Path,
    contar_paginas_pdf,
    validar_e_consumir_cota,
    usuario_pode_gerir_impressoes,
    usuario_tem_cota_ilimitada,
    default_printer_name: str,
    logger: logging.Logger,
    remover_arquivo_se_existir,
):
    job = get_job_with_access(
        job_id=job_id,
        usuario=usuario,
        usuario_pode_gerir_impressoes=usuario_pode_gerir_impressoes,
    )
    if not print_job_can_be_reused(job):
        raise HTTPException(409, "Apenas jobs concluídos podem ser reutilizados para nova impressão.")

    caminho_origem = resolve_job_pdf_path(job, spool_dir)
    nome_arquivo_exibicao = str(job.get("arquivo") or caminho_origem.name)
    caminho_copia = copy_job_pdf_to_spool(
        caminho_origem=caminho_origem,
        nome_referencia=nome_arquivo_exibicao,
        spool_dir=spool_dir,
    )

    return create_job_from_ready_pdf(
        caminho_arquivo=caminho_copia,
        nome_arquivo_exibicao=nome_arquivo_exibicao,
        copias=copias,
        paginas_por_folha=paginas_por_folha,
        duplex=duplex,
        orientacao=orientacao,
        intervalo_paginas=intervalo_paginas,
        usuario_responsavel=usuario_responsavel,
        tags_impressao=resolve_print_tags(tags_impressao, job),
        remover_arquivo_em_falha=True,
        contar_paginas_pdf=contar_paginas_pdf,
        validar_e_consumir_cota=validar_e_consumir_cota,
        usuario_tem_cota_ilimitada=usuario_tem_cota_ilimitada,
        default_printer_name=default_printer_name,
        logger=logger,
        remover_arquivo_se_existir=remover_arquivo_se_existir,
    )
