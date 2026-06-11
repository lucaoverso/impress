import logging
import uuid
from pathlib import Path

from modules.printing.config import DEFAULT_PRINTER_NAME, get_spool_dir
from modules.printing.dependencies import resolve_print_teacher, user_has_unlimited_quota
from modules.printing.service import (
    create_job_from_ready_pdf,
    ensure_print_is_available,
    get_formatted_print_status,
    validate_print_parameters,
)
from services.cota_service import validar_e_consumir_cota
from services.pdf_service import contar_paginas_pdf

logger = logging.getLogger(__name__)


def _remover_arquivo_se_existir(caminho: Path):
    try:
        caminho.unlink()
    except (FileNotFoundError, OSError):
        return


def imprimir_anexo_pdf(
    *,
    conteudo_pdf: bytes,
    nome_arquivo: str,
    copias: int,
    paginas_por_folha: int,
    duplex: bool,
    orientacao: str,
    intervalo_paginas: str,
    tags: list[str],
    professor_id: int | None,
    usuario: dict,
):
    ensure_print_is_available(get_formatted_print_status())
    validate_print_parameters(copias, paginas_por_folha, orientacao)

    usuario_responsavel = resolve_print_teacher(
        usuario,
        professor_id,
        contexto="solicitante da impressao do anexo",
        permitir_professor_com_acesso_coordenacao=True,
    )

    spool_dir = Path(get_spool_dir())
    spool_dir.mkdir(parents=True, exist_ok=True)
    nome_base = Path(nome_arquivo or "anexo").stem or "anexo"
    caminho_pdf = spool_dir / f"{uuid.uuid4().hex}_{nome_base}.pdf"
    caminho_pdf.write_bytes(conteudo_pdf)

    return create_job_from_ready_pdf(
        caminho_arquivo=caminho_pdf,
        nome_arquivo_exibicao=nome_arquivo or "Anexo.pdf",
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
        remover_arquivo_se_existir=_remover_arquivo_se_existir,
    )
