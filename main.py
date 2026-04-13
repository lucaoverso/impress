import importlib
import logging
import threading
from datetime import datetime, UTC
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from app_logging import setup_logging
from auth import router as auth_router
from db.bootstrap import criar_tabelas, criar_usuario_se_nao_existir, seed_recursos_padrao
from ocorrencias_router import router as ocorrencias_router
from pcpi_router import router as pcpi_router
from preconselho_router import router as preconselho_router
import routers.admin_router as admin_router_module
import routers.agendamento_router as agendamento_router_module
import routers.common as common_module
import routers.config as config_module
import routers.impressao_router as impressao_router_module
import routers.pages_router as pages_router_module
import routers.professores_common as professores_common_module
import routers.professores_router as professores_router_module
import routers.system_router as system_router_module
from services.auth_service import hash_senha
from services.worker import worker_loop

setup_logging()
logger = logging.getLogger(__name__)

config_module = importlib.reload(config_module)
common_module = importlib.reload(common_module)
professores_common_module = importlib.reload(professores_common_module)
system_router_module = importlib.reload(system_router_module)
pages_router_module = importlib.reload(pages_router_module)
impressao_router_module = importlib.reload(impressao_router_module)
agendamento_router_module = importlib.reload(agendamento_router_module)
professores_router_module = importlib.reload(professores_router_module)
admin_router_module = importlib.reload(admin_router_module)

ENABLE_EMBEDDED_WORKER = config_module.ENABLE_EMBEDDED_WORKER
STATIC_DIR = config_module.STATIC_DIR

system_router = system_router_module.router
pages_router = pages_router_module.router
impressao_router = impressao_router_module.router
agendamento_router = agendamento_router_module.router
professores_router = professores_router_module.router
admin_router = admin_router_module.router

root = system_router_module.root
health = system_router_module.health
eu = system_router_module.eu
internal_radius_ensure_nt_hash = system_router_module.internal_radius_ensure_nt_hash

login_page = pages_router_module.login_page
servicos_page = pages_router_module.servicos_page
impressao_page = pages_router_module.impressao_page
professor_redirect = pages_router_module.professor_redirect
agendamento_page = pages_router_module.agendamento_page
pcpi_page = pages_router_module.pcpi_page
preconselho_page = pages_router_module.preconselho_page
cadastro_professor_page = pages_router_module.cadastro_professor_page
admin_page = pages_router_module.admin_page
coordenacao_page = pages_router_module.coordenacao_page

turmas_impressao = impressao_router_module.turmas_impressao
imprimir = impressao_router_module.imprimir
preview_impressao = impressao_router_module.preview_impressao
fila = impressao_router_module.fila
cancelar = impressao_router_module.cancelar
prioridade = impressao_router_module.prioridade
meus_jobs = impressao_router_module.meus_jobs
minha_cota = impressao_router_module.minha_cota

recursos_agendamento = agendamento_router_module.recursos_agendamento
opcoes_agendamento = agendamento_router_module.opcoes_agendamento
professores_agendamento = agendamento_router_module.professores_agendamento
listar_reservas_agendamento = agendamento_router_module.listar_reservas_agendamento
criar_reserva_agendamento = agendamento_router_module.criar_reserva_agendamento
cancelar_reserva_agendamento = agendamento_router_module.cancelar_reserva_agendamento

opcoes_professores_publico = professores_router_module.opcoes_professores_publico
criar_professor_publico = professores_router_module.criar_professor_publico
recuperar_senha_professor = professores_router_module.recuperar_senha_professor

listar_contexto_turmas_disciplinas_admin = (
    admin_router_module.listar_contexto_turmas_disciplinas_admin
)
criar_turma_disciplina_admin_api = admin_router_module.criar_turma_disciplina_admin_api
atualizar_turma_disciplina_admin_api = admin_router_module.atualizar_turma_disciplina_admin_api
excluir_turma_disciplina_admin_api = admin_router_module.excluir_turma_disciplina_admin_api
listar_contexto_atribuicoes_docentes_admin = (
    admin_router_module.listar_contexto_atribuicoes_docentes_admin
)
listar_atribuicoes_docentes_admin_api = admin_router_module.listar_atribuicoes_docentes_admin_api
criar_atribuicao_docente_admin_api = admin_router_module.criar_atribuicao_docente_admin_api
sincronizar_atribuicoes_docentes_admin_api = (
    admin_router_module.sincronizar_atribuicoes_docentes_admin_api
)
excluir_atribuicao_docente_admin_api = admin_router_module.excluir_atribuicao_docente_admin_api
listar_professores_painel = admin_router_module.listar_professores_painel
excluir_professor_painel = admin_router_module.excluir_professor_painel


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.started_at = datetime.now(UTC)
    app.state.boot_status = "starting"
    app.state.worker_mode = "embedded" if ENABLE_EMBEDDED_WORKER else "external"

    try:
        criar_tabelas()

        criar_usuario_se_nao_existir(
            nome="Administrador",
            email="admin@escola",
            senha_hash=hash_senha("admin123"),
            senha_plana="admin123",
            perfil="admin",
            cargo="ADMIN",
        )

        criar_usuario_se_nao_existir(
            nome="Professor Teste",
            email="professor@escola",
            senha_hash=hash_senha("prof123"),
            senha_plana="prof123",
            perfil="professor",
            cargo="PROFESSOR",
        )

        seed_recursos_padrao()

        if ENABLE_EMBEDDED_WORKER:
            worker_thread = threading.Thread(target=worker_loop, daemon=True)
            worker_thread.start()
            logger.info("Aplicacao iniciada com worker embutido ativo")
        else:
            logger.info("Aplicacao iniciada com worker externo esperado")

        app.state.boot_status = "ready"
        yield
    except Exception:
        app.state.boot_status = "error"
        logger.exception("Falha na inicializacao da aplicacao")
        raise
    finally:
        app.state.boot_status = "stopping"
        logger.info("Aplicacao finalizada")


app = FastAPI(title="Suite de Servicos Escolares", lifespan=lifespan)

app.include_router(auth_router)
app.include_router(system_router)
app.include_router(pages_router)
app.include_router(impressao_router)
app.include_router(agendamento_router)
app.include_router(professores_router)
app.include_router(admin_router)
app.include_router(ocorrencias_router)
app.include_router(pcpi_router)
app.include_router(preconselho_router)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
