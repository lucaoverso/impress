import logging
from pathlib import Path

from modules.printing.config import DEFAULT_PRINTER_NAME, SPOOL_DIR
from modules.printing.dependencies import user_can_manage_prints, user_has_unlimited_quota
from modules.printing.repository import (
    cancel_job as cancelar_job,
    create_job as criar_job,
    get_job as buscar_job,
    get_print_status as obter_status_impressao,
)
from modules.printing.router import (
    cancelar,
    fila,
    imprimir,
    meus_jobs,
    minha_cota,
    preview_impressao,
    preview_job_historico,
    prioridade,
    reimprimir_job_historico,
    router,
    status_impressao,
    tags_impressao,
    turmas_impressao,
)
from modules.printing.service import (
    build_cups_options,
    build_print_status_alert,
    copy_job_pdf_to_spool,
    count_interval_pages,
    create_job_from_ready_pdf,
    ensure_print_is_available,
    extract_job_tags,
    get_job_with_access,
    normalize_print_tags,
    print_job_can_be_reused,
    resolve_job_pdf_path,
    resolve_print_tags,
    sanitize_file_name,
    serialize_print_job,
    validate_print_parameters,
    validate_required_tags,
)
from services.cota_service import validar_e_consumir_cota
from services.pdf_service import contar_paginas_pdf

logger = logging.getLogger(__name__)


def contar_paginas_intervalo(intervalo: str, total_paginas: int) -> int:
    return count_interval_pages(intervalo, total_paginas)


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
    return sanitize_file_name(nome_arquivo)


def montar_opcoes_cups(
    paginas_por_folha: int,
    duplex: bool,
    orientacao: str,
    intervalo_paginas: str,
):
    return build_cups_options(paginas_por_folha, duplex, orientacao, intervalo_paginas)


def obter_alerta_indisponibilidade_impressao() -> dict:
    return build_print_status_alert(obter_status_impressao())


def exigir_impressao_disponivel():
    ensure_print_is_available(obter_alerta_indisponibilidade_impressao())


def validar_parametros_impressao(
    copias: int,
    paginas_por_folha: int,
    orientacao: str,
):
    validate_print_parameters(copias, paginas_por_folha, orientacao)


def normalizar_tags_impressao(tags: list[str] | None) -> list[str]:
    return normalize_print_tags(tags)


def resolver_tags_impressao(tags: list[str] | None, job_base: dict | None = None) -> list[str]:
    return resolve_print_tags(tags, job_base)


def validar_tags_obrigatorias(tags: list[str] | None):
    validate_required_tags(tags)


def extrair_tags_job(job: dict | None) -> list[str]:
    return extract_job_tags(job)


def serializar_job_impressao(job: dict) -> dict:
    return serialize_print_job(job)


def obter_job_com_acesso(job_id: int, usuario: dict) -> dict:
    return get_job_with_access(
        job_id=job_id,
        usuario=usuario,
        usuario_pode_gerir_impressoes=user_can_manage_prints,
    )


def job_pode_ser_reutilizado(job: dict) -> bool:
    return print_job_can_be_reused(job)


def resolver_caminho_pdf_job(job: dict) -> Path:
    return resolve_job_pdf_path(job, garantir_diretorio_spool())


def copiar_pdf_job_para_spool(caminho_origem: Path, nome_referencia: str) -> Path:
    return copy_job_pdf_to_spool(
        caminho_origem=caminho_origem,
        nome_referencia=nome_referencia,
        spool_dir=garantir_diretorio_spool(),
    )


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
    tags_impressao: list[str] | None = None,
    remover_arquivo_em_falha: bool = True,
):
    return create_job_from_ready_pdf(
        caminho_arquivo=caminho_arquivo,
        nome_arquivo_exibicao=nome_arquivo_exibicao,
        copias=copias,
        paginas_por_folha=paginas_por_folha,
        duplex=duplex,
        orientacao=orientacao,
        intervalo_paginas=intervalo_paginas,
        usuario_responsavel=usuario_responsavel,
        tags_impressao=tags_impressao,
        remover_arquivo_em_falha=remover_arquivo_em_falha,
        contar_paginas_pdf=contar_paginas_pdf,
        validar_e_consumir_cota=validar_e_consumir_cota,
        usuario_tem_cota_ilimitada=user_has_unlimited_quota,
        criar_job=criar_job,
        default_printer_name=DEFAULT_PRINTER_NAME,
        logger=logger,
        remover_arquivo_se_existir=remover_arquivo_se_existir,
    )
