import os
import time
from database import (
    buscar_proximo_job,
    atualizar_status,
    atualizar_job_cups,
    atualizar_erro_job,
)
from services.printer import imprimir_job

INTERVALO = 2  # segundos
MANTER_ARQUIVOS_SPOOL = os.getenv("KEEP_SPOOL_FILES", "").strip().lower() in {"1", "true", "yes"}

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
        print(f"⚠️ Não foi possível remover arquivo spool do job {job['id']}: {exc}")

def worker_loop():
    print(f"👷 Worker de impressão iniciado (janela de cancelamento: {JANELA_CANCELAMENTO_SEGUNDOS}s)")

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
            except Exception as e:
                print("❌ Erro ao imprimir:", e)
                atualizar_erro_job(job["id"], str(e))
                atualizar_status(job["id"], "ERRO")
        else:
            time.sleep(INTERVALO)
