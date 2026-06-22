import logging
from pathlib import Path

from db.apc import (
    buscar_apc_envio_por_id,
    buscar_proximo_apc_preview_job,
    concluir_apc_preview_job,
    falhar_apc_preview_job,
    marcar_apc_preview_job_processando,
)
from routers.config import APC_DIR
from services.apc_preview_service import gerar_preview_pdf_apc

logger = logging.getLogger(__name__)


def _diretorio_previews() -> Path:
    diretorio = Path(APC_DIR) / "previews"
    diretorio.mkdir(parents=True, exist_ok=True)
    return diretorio


def caminho_preview_apc(job: dict) -> Path:
    envio_id = int(job.get("envio_id") or 0)
    job_id = int(job.get("id") or 0)
    return _diretorio_previews() / f"apc_preview_{envio_id}_{job_id}.pdf"


def processar_proximo_apc_preview_job() -> bool:
    job = buscar_proximo_apc_preview_job()
    if not job:
        return False

    job_id = int(job["id"])
    if not marcar_apc_preview_job_processando(job_id):
        return True

    try:
        envio = buscar_apc_envio_por_id(int(job["envio_id"]))
        if not envio:
            raise RuntimeError("Envio APC nao encontrado para gerar preview.")

        caminho_origem = Path(str(job.get("arquivo_path") or "")).resolve(strict=False)
        caminho_envio = Path(str(envio.get("arquivo_path") or "")).resolve(strict=False)
        if caminho_origem != caminho_envio:
            raise RuntimeError("Arquivo do envio foi substituido antes da conversao.")
        if not caminho_origem.exists() or not caminho_origem.is_file():
            raise RuntimeError("Arquivo do envio nao encontrado para gerar preview.")

        nome_arquivo = str(job.get("arquivo_nome_original") or caminho_origem.name)
        conteudo_pdf = gerar_preview_pdf_apc(caminho_origem, nome_arquivo)
        caminho_pdf = caminho_preview_apc(job)
        caminho_pdf.write_bytes(conteudo_pdf)
        concluir_apc_preview_job(job_id, str(caminho_pdf))
        return True
    except Exception as exc:
        logger.warning("Falha ao gerar preview APC do job %s: %s", job_id, exc)
        falhar_apc_preview_job(job_id, str(exc))
        return True
