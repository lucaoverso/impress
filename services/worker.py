import os
import time
import logging
from pathlib import Path
from db.impressao import (
    buscar_proximo_job,
    atualizar_status,
    atualizar_job_cups,
    atualizar_erro_job,
    listar_arquivo_paths_jobs_em_andamento,
)
from services.printer import imprimir_job

BASE_DIR = Path(__file__).resolve().parent.parent
INTERVALO = 2  # segundos
INTERVALO_LIMPEZA_SPOOL_SEGUNDOS = 3600
MANTER_ARQUIVOS_SPOOL = os.getenv("KEEP_SPOOL_FILES", "true").strip().lower() in {
    "1",
    "true",
    "yes",
}
logger = logging.getLogger(__name__)
DIRETORIO_SPOOL = Path(os.getenv("SPOOL_DIR", str(BASE_DIR / "spool")))
ULTIMA_LIMPEZA_SPOOL_MONOTONIC = 0.0


def _resolver_janela_cancelamento() -> int:
    valor = os.getenv("PRINT_CANCEL_WINDOW_SECONDS", "15").strip()
    try:
        segundos = int(valor)
    except ValueError:
        return 15
    return max(segundos, 0)


def _resolver_retencao_spool_dias() -> int:
    valor = os.getenv("SPOOL_RETENTION_DAYS", "0").strip()
    if not valor:
        return 0

    try:
        dias = int(valor)
    except ValueError:
        logger.warning("Valor invalido para SPOOL_RETENTION_DAYS=%r; usando 0.", valor)
        return 0

    return max(dias, 0)


JANELA_CANCELAMENTO_SEGUNDOS = _resolver_janela_cancelamento()
RETENCAO_SPOOL_DIAS = _resolver_retencao_spool_dias()


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


def _listar_arquivos_spool_protegidos() -> set[Path]:
    caminhos = set()
    for arquivo_path in listar_arquivo_paths_jobs_em_andamento():
        try:
            caminhos.add(Path(arquivo_path).resolve(strict=False))
        except OSError:
            continue
    return caminhos


def _remover_diretorios_vazios(caminho_raiz: Path):
    if not caminho_raiz.exists():
        return

    diretorios = [caminho for caminho in caminho_raiz.rglob("*") if caminho.is_dir()]
    for diretorio in sorted(diretorios, key=lambda item: len(item.parts), reverse=True):
        try:
            diretorio.rmdir()
        except OSError:
            continue


def limpar_spool_expirado() -> int:
    if RETENCAO_SPOOL_DIAS <= 0 or not DIRETORIO_SPOOL.exists():
        return 0

    protegidos = _listar_arquivos_spool_protegidos()
    limite_mtime = time.time() - (RETENCAO_SPOOL_DIAS * 86400)
    removidos = 0

    for caminho in DIRETORIO_SPOOL.rglob("*"):
        if not caminho.is_file():
            continue

        try:
            caminho_resolvido = caminho.resolve(strict=False)
        except OSError:
            caminho_resolvido = caminho

        if caminho_resolvido in protegidos:
            continue

        try:
            mtime = caminho.stat().st_mtime
        except FileNotFoundError:
            continue
        except OSError as exc:
            logger.warning("Nao foi possivel inspecionar arquivo spool %s: %s", caminho, exc)
            continue

        if mtime > limite_mtime:
            continue

        try:
            caminho.unlink()
            removidos += 1
        except FileNotFoundError:
            continue
        except OSError as exc:
            logger.warning("Nao foi possivel remover arquivo expirado do spool %s: %s", caminho, exc)

    _remover_diretorios_vazios(DIRETORIO_SPOOL)
    return removidos


def limpar_spool_expirado_se_necessario():
    global ULTIMA_LIMPEZA_SPOOL_MONOTONIC

    if RETENCAO_SPOOL_DIAS <= 0:
        return

    agora = time.monotonic()
    if (
        ULTIMA_LIMPEZA_SPOOL_MONOTONIC
        and (agora - ULTIMA_LIMPEZA_SPOOL_MONOTONIC) < INTERVALO_LIMPEZA_SPOOL_SEGUNDOS
    ):
        return

    try:
        removidos = limpar_spool_expirado()
    except Exception as exc:
        logger.warning("Falha ao executar limpeza automatica do spool: %s", exc)
        ULTIMA_LIMPEZA_SPOOL_MONOTONIC = agora
        return

    ULTIMA_LIMPEZA_SPOOL_MONOTONIC = agora
    if removidos:
        logger.info(
            "Limpeza automatica do spool removeu %s arquivo(s) com mais de %s dia(s).",
            removidos,
            RETENCAO_SPOOL_DIAS,
        )


def worker_loop():
    logger.info(
        "Worker de impressao iniciado (janela de cancelamento: %ss, retencao do spool: %s)",
        JANELA_CANCELAMENTO_SEGUNDOS,
        f"{RETENCAO_SPOOL_DIAS} dia(s)" if RETENCAO_SPOOL_DIAS > 0 else "desativada",
    )

    while True:
        limpar_spool_expirado_se_necessario()
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
