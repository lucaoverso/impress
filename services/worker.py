import os
import time
import logging
from db.impressao import (
    buscar_proximo_job,
    atualizar_status,
    atualizar_job_cups,
    atualizar_erro_job,
)
from services.printer import imprimir_job

INTERVALO = 2  # segundos
MANTER_ARQUIVOS_SPOOL = os.getenv("KEEP_SPOOL_FILES", "").strip().lower() in {"1", "true", "yes"}
logger = logging.getLogger(__name__)


def _resolver_janela_cancelamento() -> int:
    valor = os.getenv("PRINT_CANCEL_WINDOW_SECONDS", "15").strip()
    try:
        segundos = int(valor)
    except ValueError:
        return 15
    return max(segundos, 0)


JANELA_CANCELAMENTO_SEGUNDOS = _resolver_janela_cancelamento()


def limpar_arquivo_job(job):
    if MANTER_ARQUIVOS_SPOOL:
        return

    arquivo_path = job.get("arquivo_path")
    if not arquivo_path:
        return

    try:
        os.remove(arquivo_path)
    except FileNotFoundError:
        return
    except OSError as exc:
        logger.warning(
            "Nao foi possivel remover arquivo spool do job %s: %s",
            job["id"],
            exc,
        )


def worker_loop():
    logger.info(
        "Worker de impressao iniciado (janela de cancelamento: %ss)",
        JANELA_CANCELAMENTO_SEGUNDOS,
    )

    while True:
        job = buscar_proximo_job(atraso_minimo_segundos=JANELA_CANCELAMENTO_SEGUNDOS)

        if job:
            try:
                atualizar_status(job["id"], "IMPRIMINDO")
                resultado = imprimir_job(job)
                atualizar_job_cups(
                    job_id=job["id"],
                    cups_job_id=resultado.get("cups_job_id"),
                    printer_name=resultado.get("printer_name"),
                )
                atualizar_status(job["id"], "CONCLUIDO")
                limpar_arquivo_job(job)
            except Exception as exc:
                logger.exception("Erro ao imprimir job %s", job["id"])
                atualizar_erro_job(job["id"], str(exc))
                atualizar_status(job["id"], "ERRO")
        else:
            time.sleep(INTERVALO)
