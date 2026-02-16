import threading 
from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Depends
from datetime import datetime
from auth import router as auth_router
from services.worker import worker_loop
from contextlib import asynccontextmanager
from services.cota_service import validar_e_consumir_cota
from auth import get_usuario_logado
from database import (
    criar_tabelas,
    criar_job,
    listar_fila,
    buscar_job,
    cancelar_job,
    alterar_prioridade, 
    listar_jobs_por_usuario
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    criar_tabelas()

    worker_thread = threading.Thread(
        target=worker_loop,
        daemon=True
    )
    worker_thread.start()

    print("🚀 Aplicação iniciada com worker ativo")

    yield  # aplicação rodando

    # SHUTDOWN
    print("🛑 Aplicação finalizada")

app = FastAPI(
    title="Servidor de Impressão Escolar",
    lifespan=lifespan
)

app.include_router(auth_router)

@app.get("/")
def health():
    return {"status": "ok"}

from fastapi import Depends

@app.post("/imprimir")
def imprimir(
    copias: int = Form(...),
    arquivo: UploadFile = File(...),
    usuario = Depends(get_usuario_logado)
):
    if copias <= 0:
        raise HTTPException(400, "Quantidade inválida")

    if not arquivo or not arquivo.filename:
        raise HTTPException(400, "Arquivo não enviado")

    if not arquivo.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Apenas PDF")

    # ⚠️ MVP: 1 página = 1 cópia
    paginas = copias  

    autorizado, restante = validar_e_consumir_cota(
        usuario_id=usuario["id"],
        paginas=paginas
    )

    if not autorizado:
        raise HTTPException(
            403,
            f"Cota insuficiente. Restam {restante} páginas."
        )

    caminho = f"/tmp/{arquivo.filename}"
    with open(caminho, "wb") as f:
        f.write(arquivo.file.read())

    criar_job(
        usuario_id=usuario["id"],
        arquivo=arquivo.filename,
        copias=copias
    )

    return {
        "mensagem": "Job criado com sucesso",
        "paginas_restantes": restante
    }



#Fila de impressão
from models import JobOut

@app.get("/fila")
def fila(usuario = Depends(get_usuario_logado)):
    if usuario["perfil"] != "admin":
        raise HTTPException(403, "Acesso negado")

    return listar_fila()


#cancelar impressão
@app.post("/jobs/{job_id}/cancelar")
def cancelar(job_id: int):
    job = buscar_job(job_id)
    if not job:
        raise HTTPException(404, "Job não encontrado")

    if job["status"] != "PENDENTE":
        raise HTTPException(400, "Job não pode ser cancelado")

    cancelar_job(job_id)
    return {"mensagem": "Job cancelado"}


#Definir prioridade
@app.post("/jobs/{job_id}/prioridade")
def prioridade(job_id: int, urgente: bool = True):
    alterar_prioridade(job_id, urgente)
    return {"mensagem": "Prioridade atualizada"}


#atualizar status do job (simulação de impressão)
@app.post("/jobs/{job_id}/status")
def atualizar_status(job_id: int, status: str):
    job = buscar_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")

    if status not in ["IMPRIMINDO", "CONCLUIDO"]:
        raise HTTPException(status_code=400, detail="Status inválido")

    job["status"] = status

    return {
        "mensagem": "Status atualizado",
        "job": job
    }

@app.get("/meus-jobs")
def meus_jobs(usuario = Depends(get_usuario_logado)):
    return listar_jobs_por_usuario(usuario["id"])
