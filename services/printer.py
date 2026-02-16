import time

def imprimir_job(job):
    print(f"🖨️ Imprimindo: {job['arquivo']} ({job['copias']} cópias)")
    time.sleep(3)  # simula tempo de impressão
    print(f"✅ Finalizado: {job['arquivo']}")
