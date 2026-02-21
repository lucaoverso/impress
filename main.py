import threading
import os
import tempfile
import sqlite3
from contextlib import asynccontextmanager
from math import ceil
from datetime import datetime
from services.pdf_service import contar_paginas_pdf

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException,
    Form,
    Depends,
    Request
)
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# ===== ROTAS / AUTENTICAÇÃO =====
from auth import router as auth_router, get_usuario_logado
from services.auth_service import hash_senha
from models import (
    AgendamentoIn,
    ProfessorCreateIn,
    ProfessorCargaIn,
    RecursoCreateIn,
    RecursoStatusIn,
    RegrasCotaIn
)

# ===== WORKER =====
from services.worker import worker_loop

# ===== COTAS =====
from services.cota_service import (
    validar_e_consumir_cota,
    obter_cota_atual
)

# ===== BANCO =====
from database import (
    criar_tabelas,
    criar_usuario_se_nao_existir,
    criar_job,
    listar_fila,
    cancelar_job,
    alterar_prioridade,
    listar_jobs_ativos,
    listar_historico,
    listar_jobs_por_usuario,
    gerar_relatorio_consumo,
    gerar_relatorio_impressao,
    gerar_relatorio_uso_recursos,
    gerar_relatorio_uso_recursos_por_professor,
    seed_recursos_padrao,
    listar_recursos_ativos,
    listar_recursos,
    criar_recurso,
    atualizar_status_recurso,
    buscar_recurso_por_id,
    buscar_usuario_por_id,
    buscar_agendamento_conflito,
    criar_agendamento,
    listar_agendamentos,
    buscar_agendamento_por_id,
    cancelar_agendamento,
    criar_professor,
    listar_professores_admin,
    salvar_carga_professor,
    obter_regras_cota,
    atualizar_regras_cota,
    recalcular_cotas_mes,
    calcular_limite_cota_usuario
)

# =========================================================
# LIFESPAN (STARTUP / SHUTDOWN)
# =========================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    criar_tabelas()

    # Seed de usuários iniciais
    criar_usuario_se_nao_existir(
        nome="Administrador",
        email="admin@escola",
        senha_hash=hash_senha("admin123"),
        perfil="admin"
    )

    criar_usuario_se_nao_existir(
        nome="Professor Teste",
        email="professor@escola",
        senha_hash=hash_senha("prof123"),
        perfil="professor"
    )

    seed_recursos_padrao()

    # Worker de impressão
    worker_thread = threading.Thread(
        target=worker_loop,
        daemon=True
    )
    worker_thread.start()

    print("🚀 Aplicação iniciada com worker ativo")

    yield  # aplicação rodando

    # SHUTDOWN
    print("🛑 Aplicação finalizada")


# =========================================================
# APP
# =========================================================

app = FastAPI(
    title="Suite de Servicos Escolares",
    lifespan=lifespan
)

# Rotas
app.include_router(auth_router)

# Static / Templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

TURNOS_CONFIG = {
    "INTEGRAL": {"nome": "Período integral", "aulas": 8},
    "MATUTINO": {"nome": "Matutino", "aulas": 5},
    "VESPERTINO": {"nome": "Vespertino", "aulas": 5},
    "VESPERTINO_EM": {"nome": "Vespertino E.M.", "aulas": 6},
}

def gerar_turmas_validas():
    turmas = []
    for ano in range(6, 10):
        turmas.append(f"{ano}º ano A")
        turmas.append(f"{ano}º ano B")

    for serie in range(1, 4):
        turmas.append(f"{serie} E.M A")
        turmas.append(f"{serie} E.M B")

    return turmas

TURMAS_VALIDAS = set(gerar_turmas_validas())

def contar_paginas_intervalo(intervalo: str, total_paginas: int) -> int:
    if not intervalo or not intervalo.strip():
        return total_paginas

    paginas = set()
    partes = [p.strip() for p in intervalo.split(",") if p.strip()]

    for parte in partes:
        if "-" in parte:
            pedacos = [n.strip() for n in parte.split("-")]
            if len(pedacos) != 2:
                raise HTTPException(400, f'Intervalo inválido: "{parte}"')
            inicio, fim = pedacos
            if not inicio.isdigit() or not fim.isdigit():
                raise HTTPException(400, f'Intervalo inválido: "{parte}"')
            inicio_num = int(inicio)
            fim_num = int(fim)
            if inicio_num <= 0 or fim_num <= 0 or inicio_num > fim_num:
                raise HTTPException(400, f'Intervalo inválido: "{parte}"')
            if fim_num > total_paginas:
                raise HTTPException(400, f"Página {fim_num} não existe no PDF")
            for pagina in range(inicio_num, fim_num + 1):
                paginas.add(pagina)
        else:
            if not parte.isdigit():
                raise HTTPException(400, f'Página inválida: "{parte}"')
            pagina = int(parte)
            if pagina <= 0 or pagina > total_paginas:
                raise HTTPException(400, f"Página {pagina} não existe no PDF")
            paginas.add(pagina)

    if not paginas:
        raise HTTPException(400, "Nenhuma página válida informada")

    return len(paginas)

def validar_data_agendamento(data_txt: str) -> str:
    try:
        return datetime.strptime(data_txt, "%Y-%m-%d").date().isoformat()
    except ValueError as exc:
        raise HTTPException(400, "Data inválida. Use o formato YYYY-MM-DD.") from exc

def validar_turno(turno: str) -> str:
    turno_limpo = str(turno).strip().upper()
    if turno_limpo not in TURNOS_CONFIG:
        raise HTTPException(400, "Turno inválido.")
    return turno_limpo

def validar_aula(aula: str, turno: str) -> str:
    aula_limpa = str(aula).strip()
    if not aula_limpa.isdigit():
        raise HTTPException(400, "Aula inválida.")

    numero_aula = int(aula_limpa)
    max_aulas_turno = TURNOS_CONFIG[turno]["aulas"]

    if numero_aula < 1 or numero_aula > max_aulas_turno:
        raise HTTPException(
            400,
            f"Aula inválida para o turno selecionado. Esse turno possui {max_aulas_turno} aulas."
        )

    return aula_limpa

def validar_turma(turma: str) -> str:
    turma_limpa = str(turma).strip()
    if turma_limpa not in TURMAS_VALIDAS:
        raise HTTPException(400, "Turma inválida.")
    return turma_limpa

def validar_mes_referencia(mes: str) -> str:
    try:
        return datetime.strptime(mes, "%Y-%m").strftime("%Y-%m")
    except ValueError as exc:
        raise HTTPException(400, "Mês inválido. Use formato YYYY-MM.") from exc

def mes_atual_referencia() -> str:
    return datetime.now().strftime("%Y-%m")

def exigir_admin(usuario):
    if usuario["perfil"] != "admin":
        raise HTTPException(403, "Acesso negado")
    return usuario

def validar_numero_nao_negativo(valor: int, campo: str):
    if int(valor) < 0:
        raise HTTPException(400, f"{campo} não pode ser negativo.")
    return int(valor)


# =========================================================
# ROTAS BÁSICAS
# =========================================================

@app.get("/")
def root():
    return RedirectResponse(url="/login-page", status_code=302)


@app.get("/health")
def health():
    return {"status": "ok"}


# =========================================================
# IMPRESSÃO (PROFESSOR)
# =========================================================

@app.post("/imprimir")
def imprimir(
    copias: int = Form(...),
    arquivo: UploadFile = File(...),
    paginas_por_folha: int = Form(1),
    duplex: bool = Form(False),
    orientacao: str = Form("retrato"),
    intervalo_paginas: str = Form(""),
    usuario = Depends(get_usuario_logado)
):
    if copias <= 0:
        raise HTTPException(400, "Quantidade inválida")

    if not arquivo or not arquivo.filename:
        raise HTTPException(400, "Arquivo não enviado")

    if not arquivo.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Apenas PDF")

    if paginas_por_folha not in (1, 2, 4):
        raise HTTPException(400, "Paginação por folha inválida")
    if orientacao not in ("retrato", "paisagem"):
        raise HTTPException(400, "Orientação inválida")

    # Salva o arquivo em caminho temporário único
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(arquivo.file.read())
        caminho = tmp.name

    try:
        # 🔢 Conta páginas reais do PDF
        paginas_pdf = contar_paginas_pdf(caminho)
    finally:
        if os.path.exists(caminho):
            os.remove(caminho)

    paginas_selecionadas = contar_paginas_intervalo(intervalo_paginas, paginas_pdf)
    folhas_por_copia = ceil(paginas_selecionadas / paginas_por_folha)
    if duplex:
        folhas_por_copia = ceil(folhas_por_copia / 2)
    paginas_totais = folhas_por_copia * copias

    autorizado, restante = validar_e_consumir_cota(
        usuario_id=usuario["id"],
        paginas=paginas_totais
    )

    if not autorizado:
        raise HTTPException(
            403,
            f"Cota insuficiente. Documento consome {paginas_totais} páginas. "
            f"Restam {restante}."
        )

    criar_job(
        usuario_id=usuario["id"],
        arquivo=arquivo.filename,
        copias=copias,
        paginas_totais=paginas_totais,
        paginas_por_folha=paginas_por_folha,
        duplex=duplex,
        orientacao=orientacao
    )

    return {
        "mensagem": "Job criado com sucesso",
        "paginas_documento": paginas_pdf,
        "paginas_selecionadas": paginas_selecionadas,
        "copias": copias,
        "paginas_consumidas": paginas_totais,
        "paginas_restantes": restante
    }



# =========================================================
# FILA (ADMIN)
# =========================================================

@app.get("/fila")
def fila(usuario = Depends(get_usuario_logado)):
    if usuario["perfil"] != "admin":
        raise HTTPException(403, "Acesso negado")

    return listar_fila()


@app.post("/jobs/{job_id}/cancelar")
def cancelar(job_id: int, usuario = Depends(get_usuario_logado)):
    if usuario["perfil"] != "admin":
        raise HTTPException(403, "Acesso negado")

    cancelar_job(job_id)
    return {"mensagem": "Job cancelado"}


@app.post("/jobs/{job_id}/prioridade")
def prioridade(
    job_id: int,
    urgente: bool = True,
    usuario = Depends(get_usuario_logado)
):
    if usuario["perfil"] != "admin":
        raise HTTPException(403, "Acesso negado")

    alterar_prioridade(job_id, urgente)
    return {"mensagem": "Prioridade atualizada"}


# =========================================================
# PROFESSOR
# =========================================================

@app.get("/meus-jobs")
def meus_jobs(usuario = Depends(get_usuario_logado)):
    return listar_jobs_por_usuario(usuario["id"])


@app.get("/minha-cota")
def minha_cota(usuario = Depends(get_usuario_logado)):
    return obter_cota_atual(usuario["id"])


@app.get("/me")
def eu(usuario = Depends(get_usuario_logado)):
    return usuario


# =========================================================
# AGENDAMENTO DE EQUIPAMENTOS
# =========================================================

@app.get("/agendamento/recursos")
def recursos_agendamento(usuario = Depends(get_usuario_logado)):
    return listar_recursos_ativos()


@app.get("/agendamento/opcoes")
def opcoes_agendamento(usuario = Depends(get_usuario_logado)):
    turnos = [
        {"id": turno_id, "nome": cfg["nome"], "aulas": cfg["aulas"]}
        for turno_id, cfg in TURNOS_CONFIG.items()
    ]
    return {
        "turnos": turnos,
        "turmas": gerar_turmas_validas()
    }


@app.get("/agendamento/reservas")
def listar_reservas_agendamento(
    data_inicio: str = None,
    data_fim: str = None,
    recurso_id: int = None,
    usuario = Depends(get_usuario_logado)
):
    data_inicio_norm = validar_data_agendamento(data_inicio) if data_inicio else None
    data_fim_norm = validar_data_agendamento(data_fim) if data_fim else None

    if data_inicio_norm and data_fim_norm and data_inicio_norm > data_fim_norm:
        raise HTTPException(400, "Período inválido: data inicial maior que data final.")

    return listar_agendamentos(
        data_inicio=data_inicio_norm,
        data_fim=data_fim_norm,
        recurso_id=recurso_id
    )


@app.post("/agendamento/reservas")
def criar_reserva_agendamento(
    payload: AgendamentoIn,
    usuario = Depends(get_usuario_logado)
):
    recurso = buscar_recurso_por_id(payload.recurso_id)
    if not recurso or recurso["ativo"] != 1:
        raise HTTPException(404, "Recurso não encontrado.")

    data_reserva = validar_data_agendamento(payload.data)
    turno = validar_turno(payload.turno)
    aula = validar_aula(payload.aula, turno)
    turma = validar_turma(payload.turma)

    conflito = buscar_agendamento_conflito(
        recurso_id=payload.recurso_id,
        data=data_reserva,
        turno=turno,
        aula=aula
    )
    if conflito:
        raise HTTPException(409, "Este recurso já está reservado nessa data e aula.")

    observacao = (payload.observacao or "").strip()
    agendamento_id = criar_agendamento(
        recurso_id=payload.recurso_id,
        usuario_id=usuario["id"],
        data=data_reserva,
        turno=turno,
        aula=aula,
        turma=turma,
        observacao=observacao
    )

    return {
        "mensagem": "Agendamento realizado com sucesso.",
        "agendamento_id": agendamento_id
    }


@app.post("/agendamento/reservas/{agendamento_id}/cancelar")
def cancelar_reserva_agendamento(
    agendamento_id: int,
    usuario = Depends(get_usuario_logado)
):
    agendamento = buscar_agendamento_por_id(agendamento_id)
    if not agendamento:
        raise HTTPException(404, "Agendamento não encontrado.")

    if agendamento["status"] != "ATIVO":
        raise HTTPException(400, "Este agendamento já foi cancelado.")

    dono_reserva = agendamento["usuario_id"] == usuario["id"]
    if not dono_reserva and usuario["perfil"] != "admin":
        raise HTTPException(403, "Você não pode cancelar este agendamento.")

    cancelado = cancelar_agendamento(agendamento_id)
    if not cancelado:
        raise HTTPException(400, "Não foi possível cancelar o agendamento.")

    return {"mensagem": "Agendamento cancelado com sucesso."}


# =========================================================
# PÁGINAS HTML
# =========================================================

@app.get("/login-page")
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/servicos")
def servicos_page(request: Request):
    return templates.TemplateResponse("servicos.html", {"request": request})


@app.get("/impressao")
def impressao_page(request: Request):
    return templates.TemplateResponse("professor.html", {"request": request})


@app.get("/professor")
def professor_redirect():
    return RedirectResponse(url="/impressao", status_code=302)


@app.get("/agendamento")
def agendamento_page(request: Request):
    return templates.TemplateResponse("agendamento.html", {"request": request})


@app.get("/admin")
def admin_page(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})

# =========================================================
# ADMIN
# =========================================================

@app.get("/admin/fila")
def fila_admin(usuario = Depends(get_usuario_logado)):
    exigir_admin(usuario)

    return listar_jobs_ativos()

@app.get("/admin/historico")
def historico_admin(
    data_inicio: str = None,
    data_fim: str = None,
    usuario_id: int = None,
    usuario = Depends(get_usuario_logado)
):
    exigir_admin(usuario)

    return listar_historico(data_inicio, data_fim, usuario_id)

@app.get("/admin/relatorio")
def relatorio_admin(
    data_inicio: str = None,
    data_fim: str = None,
    usuario = Depends(get_usuario_logado)
):
    exigir_admin(usuario)
    data_inicio_norm = validar_data_agendamento(data_inicio) if data_inicio else None
    data_fim_norm = validar_data_agendamento(data_fim) if data_fim else None

    return gerar_relatorio_impressao(data_inicio_norm, data_fim_norm)

@app.get("/admin/relatorio/impressao")
def relatorio_impressao_admin(
    data_inicio: str = None,
    data_fim: str = None,
    usuario = Depends(get_usuario_logado)
):
    exigir_admin(usuario)
    data_inicio_norm = validar_data_agendamento(data_inicio) if data_inicio else None
    data_fim_norm = validar_data_agendamento(data_fim) if data_fim else None

    return gerar_relatorio_impressao(data_inicio_norm, data_fim_norm)

@app.get("/admin/relatorio/recursos")
def relatorio_recursos_admin(
    data_inicio: str = None,
    data_fim: str = None,
    usuario = Depends(get_usuario_logado)
):
    exigir_admin(usuario)
    data_inicio_norm = validar_data_agendamento(data_inicio) if data_inicio else None
    data_fim_norm = validar_data_agendamento(data_fim) if data_fim else None

    return {
        "por_recurso": gerar_relatorio_uso_recursos(data_inicio_norm, data_fim_norm),
        "por_professor": gerar_relatorio_uso_recursos_por_professor(data_inicio_norm, data_fim_norm)
    }

@app.get("/admin/professores")
def listar_professores_painel(
    mes: str = None,
    usuario = Depends(get_usuario_logado)
):
    exigir_admin(usuario)
    mes_referencia = validar_mes_referencia(mes) if mes else mes_atual_referencia()
    regras = obter_regras_cota()
    professores = listar_professores_admin(mes_referencia)

    for professor in professores:
        professor["cota_projetada"] = calcular_limite_cota_usuario(professor["id"])

    return {
        "mes_referencia": mes_referencia,
        "regras_cota": regras,
        "professores": professores
    }

@app.post("/admin/professores")
def criar_professor_painel(
    payload: ProfessorCreateIn,
    usuario = Depends(get_usuario_logado)
):
    exigir_admin(usuario)

    nome = payload.nome.strip()
    email = payload.email.strip().lower()
    senha = payload.senha.strip()
    aulas_semanais = validar_numero_nao_negativo(payload.aulas_semanais, "Aulas semanais")
    turmas_quantidade = validar_numero_nao_negativo(payload.turmas_quantidade, "Quantidade de turmas")

    if not nome:
        raise HTTPException(400, "Nome é obrigatório.")
    if not email:
        raise HTTPException(400, "Email é obrigatório.")
    if not senha:
        raise HTTPException(400, "Senha é obrigatória.")

    try:
        professor_id = criar_professor(
            nome=nome,
            email=email,
            senha_hash=hash_senha(senha),
            aulas_semanais=aulas_semanais,
            turmas_quantidade=turmas_quantidade
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, "Já existe um usuário com este email.") from exc

    return {"mensagem": "Professor cadastrado com sucesso.", "professor_id": professor_id}

@app.put("/admin/professores/{professor_id}/carga")
def atualizar_carga_professor_painel(
    professor_id: int,
    payload: ProfessorCargaIn,
    usuario = Depends(get_usuario_logado)
):
    exigir_admin(usuario)
    professor = buscar_usuario_por_id(professor_id)
    if not professor or professor["perfil"] != "professor":
        raise HTTPException(404, "Professor não encontrado.")

    aulas_semanais = validar_numero_nao_negativo(payload.aulas_semanais, "Aulas semanais")
    turmas_quantidade = validar_numero_nao_negativo(payload.turmas_quantidade, "Quantidade de turmas")

    salvar_carga_professor(
        usuario_id=professor_id,
        aulas_semanais=aulas_semanais,
        turmas_quantidade=turmas_quantidade
    )
    return {"mensagem": "Carga do professor atualizada com sucesso."}

@app.get("/admin/cotas/regras")
def obter_regras_cota_admin(usuario = Depends(get_usuario_logado)):
    exigir_admin(usuario)
    return obter_regras_cota()

@app.put("/admin/cotas/regras")
def atualizar_regras_cota_admin(
    payload: RegrasCotaIn,
    usuario = Depends(get_usuario_logado)
):
    exigir_admin(usuario)
    base_paginas = validar_numero_nao_negativo(payload.base_paginas, "Base de páginas")
    paginas_por_aula = validar_numero_nao_negativo(payload.paginas_por_aula, "Páginas por aula")
    paginas_por_turma = validar_numero_nao_negativo(payload.paginas_por_turma, "Páginas por turma")

    atualizar_regras_cota(base_paginas, paginas_por_aula, paginas_por_turma)
    return {"mensagem": "Regras de cota atualizadas com sucesso."}

@app.post("/admin/cotas/recalcular")
def recalcular_cotas_admin(
    mes: str = None,
    usuario = Depends(get_usuario_logado)
):
    exigir_admin(usuario)
    mes_referencia = validar_mes_referencia(mes) if mes else mes_atual_referencia()
    recalcular_cotas_mes(mes_referencia)
    return {"mensagem": "Cotas recalculadas com sucesso.", "mes_referencia": mes_referencia}

@app.get("/admin/recursos")
def listar_recursos_admin_api(
    incluir_inativos: bool = True,
    usuario = Depends(get_usuario_logado)
):
    exigir_admin(usuario)
    return listar_recursos(incluir_inativos=incluir_inativos)

@app.post("/admin/recursos")
def criar_recurso_admin(
    payload: RecursoCreateIn,
    usuario = Depends(get_usuario_logado)
):
    exigir_admin(usuario)

    nome = payload.nome.strip()
    tipo = payload.tipo.strip()
    descricao = (payload.descricao or "").strip()

    if not nome:
        raise HTTPException(400, "Nome do recurso é obrigatório.")
    if not tipo:
        raise HTTPException(400, "Tipo do recurso é obrigatório.")

    try:
        recurso_id = criar_recurso(nome=nome, tipo=tipo, descricao=descricao)
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, "Já existe um recurso com este nome.") from exc

    return {"mensagem": "Recurso criado com sucesso.", "recurso_id": recurso_id}

@app.put("/admin/recursos/{recurso_id}/status")
def atualizar_status_recurso_admin(
    recurso_id: int,
    payload: RecursoStatusIn,
    usuario = Depends(get_usuario_logado)
):
    exigir_admin(usuario)
    alterado = atualizar_status_recurso(recurso_id, payload.ativo)
    if not alterado:
        raise HTTPException(404, "Recurso não encontrado.")
    return {"mensagem": "Status do recurso atualizado com sucesso."}
