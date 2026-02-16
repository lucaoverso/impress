import time
from database import buscar_proximo_job, atualizar_status
from services.printer import imprimir_job

INTERVALO = 2  # segundos

def worker_loop():
    print("👷 Worker de impressão iniciado")

    while True:
        job = buscar_proximo_job()

        if job:
            try:
                atualizar_status(job["id"], "IMPRIMINDO")
                imprimir_job(job)
                atualizar_status(job["id"], "CONCLUIDO")
            except Exception as e:
                print("❌ Erro ao imprimir:", e)
                atualizar_status(job["id"], "ERRO")
        else:
            time.sleep(INTERVALO)
