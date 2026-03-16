import threading
import os
import json
import re
import uuid
import sqlite3
from pathlib import Path
from contextlib import asynccontextmanager
from math import ceil
from datetime import datetime
from services.pdf_service import contar_paginas_pdf
from services.file_service import (
    arquivo_suportado,
    converter_para_pdf,
    obter_extensao_arquivo,
)

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException,
    Form,
    Depends,
    Request,
    Header,
)
from fastapi.responses import RedirectResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# ===== ROTAS / AUTENTICAÇÃO =====
from auth import router as auth_router, get_usuario_logado
from ocorrencias_router import router as ocorrencias_router
from services.auth_service import hash_senha
from security.nt_hash import generate_nt_hash
from models import (
    AgendamentoIn,
    ProfessorCreateIn,
    ProfessorUpdateIn,
    ProfessorRecuperarSenhaIn,
    ProfessorRedefinirSenhaAdminIn,
    CoordenadorCreateIn,
    ProfessorCargaIn,
    TurmaCreateIn,
    TurmaUpdateIn,
    DisciplinaCreateIn,
    DisciplinaUpdateIn,
    RecursoCreateIn,
    RecursoUpdateIn,
    RecursoStatusIn,
    RegrasCotaIn,
    RadiusEnsureNtHashIn,
)

# ===== WORKER =====
from services.worker import worker_loop

# ===== COTAS =====
from services.cota_service import (
    validar_e_consumir_cota,
    obter_cota_atual
)
from services.radius_service import ensure_nt_hash_for_radius

# ===== BANCO =====
from database import (
    criar_tabelas,
    criar_usuario_se_nao_existir,
    criar_job,
    listar_fila,
    cancelar_job,
    buscar_job,
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
    listar_turmas,
    listar_turmas_ativas,
    criar_turma,
    atualizar_turma_dados,
    atualizar_status_turma,
    listar_disciplinas,
    listar_disciplinas_ativas,
    criar_disciplina,
    atualizar_disciplina_dados,
    atualizar_status_disciplina,
    buscar_recurso_por_id,
    atualizar_recurso_dados,
    contar_agendamentos_ativos_faixa,
    buscar_usuario_por_email,
    buscar_usuario_por_id,
    atualizar_senha_usuario,
    revogar_tokens_usuario,
    criar_agendamento,
    listar_agendamentos,
    buscar_agendamento_por_id,
    cancelar_agendamento,
    criar_professor,
    criar_coordenador,
    atualizar_professor,
    listar_coordenadores_admin,
    listar_professores_admin,
    listar_professores_agendamento,
    salvar_carga_professor,
    obter_regras_cota,
    atualizar_regras_cota,
    recalcular_cotas_mes,
    calcular_cotas_mensais_professores
)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
SPOOL_DIR = os.getenv("SPOOL_DIR", str(BASE_DIR / "spool"))
DEFAULT_PRINTER_NAME = os.getenv("CUPS_PRINTER", "").strip()
ENABLE_EMBEDDED_WORKER = os.getenv("ENABLE_EMBEDDED_WORKER", "").strip().lower() in {"1", "true", "yes"}
FORMATOS_UPLOAD_DESCRICAO = "PDF, DOCX, DOC, PNG, JPG ou JPEG"

def _resolver_asset_version() -> str:
    valor = os.getenv("STATIC_ASSET_VERSION", "").strip()
    if valor:
        return valor
    return str(int(datetime.now().timestamp()))

ASSET_VERSION = _resolver_asset_version()

def _resolver_janela_cancelamento() -> int:
    valor = os.getenv("PRINT_CANCEL_WINDOW_SECONDS", "15").strip()
    try:
        segundos = int(valor)
    except ValueError:
        return 15
    return max(segundos, 0)

PRINT_CANCEL_WINDOW_SECONDS = _resolver_janela_cancelamento()

def _resolver_radius_internal_secret() -> str:
    return os.getenv("RADIUS_INTERNAL_SECRET", "").strip()

RADIUS_INTERNAL_SECRET = _resolver_radius_internal_secret()

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
        senha_plana="admin123",
        perfil="admin",
        cargo="ADMIN"
    )

    criar_usuario_se_nao_existir(
        nome="Professor Teste",
        email="professor@escola",
        senha_hash=hash_senha("prof123"),
        senha_plana="prof123",
        perfil="professor",
        cargo="PROFESSOR"
    )

    seed_recursos_padrao()

    if ENABLE_EMBEDDED_WORKER:
        worker_thread = threading.Thread(
            target=worker_loop,
            daemon=True
        )
        worker_thread.start()
        print("🚀 Aplicação iniciada com worker embutido ativo")
    else:
        print("🚀 Aplicação iniciada (worker externo esperado)")

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
app.include_router(ocorrencias_router)

# Static / Templates
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

TURNOS_CONFIG = {
    "INTEGRAL": {"nome": "Período integral", "aulas": 8},
    "MATUTINO": {"nome": "Matutino", "aulas": 5},
    "VESPERTINO": {"nome": "Vespertino", "aulas": 5},
    "VESPERTINO_EM": {"nome": "Vespertino E.M.", "aulas": 6},
}
FAIXA_GLOBAL_OFFSET_POR_TURNO = {
    "MATUTINO": 0,
    "INTEGRAL": 0,
    "VESPERTINO": 5,
    "VESPERTINO_EM": 5,
}
SENHA_FORTE_REGEX = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$")
CARGO_ADMIN = "ADMIN"
CARGO_PROFESSOR = "PROFESSOR"
CARGO_COORDENADOR = "COORDENADOR"
MODULOS_POR_CARGO = {
    CARGO_ADMIN: ["impressao", "agendamento", "gestao", "coordenacao"],
    CARGO_PROFESSOR: ["impressao", "agendamento"],
    CARGO_COORDENADOR: ["coordenacao"],
}

def obter_nomes_turmas_ativas() -> list[str]:
    return [turma["nome"] for turma in listar_turmas_ativas()]

def obter_nomes_disciplinas_ativas() -> list[str]:
    return [disciplina["nome"] for disciplina in listar_disciplinas_ativas()]

def validar_data_nascimento_professor(data_txt: str) -> str:
    try:
        data_nascimento = datetime.strptime(data_txt, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(400, "Data de nascimento inválida. Use o formato YYYY-MM-DD.") from exc

    hoje = datetime.now().date()
    if data_nascimento >= hoje:
        raise HTTPException(400, "Data de nascimento deve ser anterior à data atual.")
    if data_nascimento.year < 1900:
        raise HTTPException(400, "Data de nascimento inválida.")
    return data_nascimento.isoformat()

def validar_senha_forte(senha: str) -> str:
    if not SENHA_FORTE_REGEX.match(senha or ""):
        raise HTTPException(
            400,
            "A senha deve ter no mínimo 8 caracteres, incluindo letra maiúscula, letra minúscula, número e caractere especial."
        )
    return senha

def _normalizar_lista_texto(itens: list[str]) -> list[str]:
    normalizados = []
    for item in itens or []:
        texto = str(item).strip()
        if texto and texto not in normalizados:
            normalizados.append(texto)
    return normalizados

def validar_turmas_professor(turmas: list[str]) -> list[str]:
    turmas_normalizadas = _normalizar_lista_texto(turmas)
    if not turmas_normalizadas:
        raise HTTPException(400, "Selecione ao menos uma turma.")

    turmas_validas = set(obter_nomes_turmas_ativas())
    turmas_invalidas = [turma for turma in turmas_normalizadas if turma not in turmas_validas]
    if turmas_invalidas:
        raise HTTPException(400, "Uma ou mais turmas selecionadas são inválidas.")
    return turmas_normalizadas

def validar_disciplinas_professor(disciplinas: list[str]) -> list[str]:
    disciplinas_normalizadas = _normalizar_lista_texto(disciplinas)
    if not disciplinas_normalizadas:
        raise HTTPException(400, "Selecione ao menos uma disciplina.")

    disciplinas_validas = set(obter_nomes_disciplinas_ativas())
    invalidas = [disc for disc in disciplinas_normalizadas if disc not in disciplinas_validas]
    if invalidas:
        raise HTTPException(400, "Uma ou mais disciplinas selecionadas são inválidas.")
    return disciplinas_normalizadas

def obter_opcoes_cadastro_professor():
    return {
        "turmas": obter_nomes_turmas_ativas(),
        "disciplinas": obter_nomes_disciplinas_ativas(),
    }

def _validar_dados_usuario_basicos(
    nome: str,
    email: str,
    data_nascimento_txt: str,
):
    nome_limpo = str(nome or "").strip()
    email_limpo = str(email or "").strip().lower()

    if not nome_limpo:
        raise HTTPException(400, "Nome é obrigatório.")
    if not email_limpo:
        raise HTTPException(400, "Email é obrigatório.")

    data_nascimento = validar_data_nascimento_professor(data_nascimento_txt)
    return {
        "nome": nome_limpo,
        "email": email_limpo,
        "data_nascimento": data_nascimento,
    }

def _validar_dados_professor_comuns(
    nome: str,
    email: str,
    data_nascimento_txt: str,
    aulas_semanais_bruto: int,
    turmas_bruto: list[str],
    disciplinas_bruto: list[str],
):
    dados_basicos = _validar_dados_usuario_basicos(
        nome=nome,
        email=email,
        data_nascimento_txt=data_nascimento_txt,
    )
    aulas_semanais = validar_numero_nao_negativo(aulas_semanais_bruto, "Aulas semanais")
    turmas = validar_turmas_professor(turmas_bruto)
    disciplinas = validar_disciplinas_professor(disciplinas_bruto)

    return {
        **dados_basicos,
        "aulas_semanais": aulas_semanais,
        "turmas": turmas,
        "turmas_quantidade": len(turmas),
        "disciplinas": disciplinas,
    }

def validar_payload_cadastro_professor(payload: ProfessorCreateIn):
    senha = payload.senha.strip()
    if not senha:
        raise HTTPException(400, "Senha é obrigatória.")
    validar_senha_forte(senha)

    dados = _validar_dados_professor_comuns(
        nome=payload.nome,
        email=payload.email,
        data_nascimento_txt=payload.data_nascimento,
        aulas_semanais_bruto=payload.aulas_semanais,
        turmas_bruto=payload.turmas,
        disciplinas_bruto=payload.disciplinas,
    )
    dados["senha"] = senha
    return dados

def validar_payload_atualizacao_professor(payload: ProfessorUpdateIn):
    return _validar_dados_professor_comuns(
        nome=payload.nome,
        email=payload.email,
        data_nascimento_txt=payload.data_nascimento,
        aulas_semanais_bruto=payload.aulas_semanais,
        turmas_bruto=payload.turmas,
        disciplinas_bruto=payload.disciplinas,
    )

def validar_payload_cadastro_coordenador(payload: CoordenadorCreateIn):
    senha = payload.senha.strip()
    if not senha:
        raise HTTPException(400, "Senha é obrigatória.")
    validar_senha_forte(senha)

    dados = _validar_dados_usuario_basicos(
        nome=payload.nome,
        email=payload.email,
        data_nascimento_txt=payload.data_nascimento,
    )
    dados["senha"] = senha
    return dados

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
                raise HTTPException(400, f"Página {fim_num} não existe no documento")
            for pagina in range(inicio_num, fim_num + 1):
                paginas.add(pagina)
        else:
            if not parte.isdigit():
                raise HTTPException(400, f'Página inválida: "{parte}"')
            pagina = int(parte)
            if pagina <= 0 or pagina > total_paginas:
                raise HTTPException(400, f"Página {pagina} não existe no documento")
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

def calcular_faixa_global(turno: str, aula: str) -> int:
    turno_limpo = validar_turno(turno)
    numero_aula = int(validar_aula(aula, turno_limpo))
    faixa_global = numero_aula + FAIXA_GLOBAL_OFFSET_POR_TURNO[turno_limpo]

    # No integral, a faixa 6 fica livre para não colidir com a 1ª do vespertino.
    if turno_limpo == "INTEGRAL" and numero_aula > 5:
        faixa_global += 1

    return faixa_global

def validar_turma(turma: str) -> dict:
    turma_limpa = str(turma).strip()
    if not turma_limpa:
        raise HTTPException(400, "Turma inválida.")

    for turma_db in listar_turmas_ativas():
        nome_turma = str(turma_db.get("nome", "")).strip()
        if nome_turma == turma_limpa:
            return dict(turma_db)

    raise HTTPException(400, "Turma inválida.")

def validar_tema_aula(tema_aula: str) -> str:
    tema_limpo = str(tema_aula or "").strip()
    if not tema_limpo:
        raise HTTPException(400, "Tema da aula é obrigatório.")
    return tema_limpo

def validar_mes_referencia(mes: str) -> str:
    try:
        return datetime.strptime(mes, "%Y-%m").strftime("%Y-%m")
    except ValueError as exc:
        raise HTTPException(400, "Mês inválido. Use formato YYYY-MM.") from exc

def mes_atual_referencia() -> str:
    return datetime.now().strftime("%Y-%m")

def normalizar_cargo_usuario(usuario: dict) -> str:
    cargo = str(usuario.get("cargo") or "").strip().upper()
    if cargo in MODULOS_POR_CARGO:
        return cargo

    perfil = str(usuario.get("perfil") or "").strip().lower()
    if perfil == "admin":
        return CARGO_ADMIN
    if perfil == "coordenador":
        return CARGO_COORDENADOR
    return CARGO_PROFESSOR

def modulos_por_cargo(cargo: str) -> list[str]:
    return list(MODULOS_POR_CARGO.get(cargo, MODULOS_POR_CARGO[CARGO_PROFESSOR]))

def usuario_eh_admin(usuario: dict) -> bool:
    return normalizar_cargo_usuario(usuario) == CARGO_ADMIN

def usuario_eh_gestor(usuario: dict) -> bool:
    return normalizar_cargo_usuario(usuario) in {CARGO_ADMIN, CARGO_COORDENADOR}

def exigir_admin(usuario):
    if not usuario_eh_admin(usuario):
        raise HTTPException(403, "Acesso negado")
    return usuario

def exigir_gestor(usuario):
    if not usuario_eh_gestor(usuario):
        raise HTTPException(403, "Acesso negado")
    return usuario

def validar_numero_nao_negativo(valor: int, campo: str):
    if int(valor) < 0:
        raise HTTPException(400, f"{campo} não pode ser negativo.")
    return int(valor)

def garantir_diretorio_spool() -> Path:
    caminho_spool = Path(SPOOL_DIR)
    caminho_spool.mkdir(parents=True, exist_ok=True)
    return caminho_spool

def remover_arquivo_se_existir(caminho: Path):
    try:
        caminho.unlink()
    except FileNotFoundError:
        return
    except OSError:
        return

def sanitizar_nome_arquivo(nome_arquivo: str) -> str:
    nome_base = os.path.basename(nome_arquivo or "").strip().replace(" ", "_")
    nome_limpo = re.sub(r"[^A-Za-z0-9._-]", "_", nome_base)
    if not nome_limpo:
        return "documento.pdf"
    if "." not in nome_limpo:
        return f"{nome_limpo}.pdf"
    return nome_limpo

def obter_layout_duas_por_folha(orientacao: str) -> str:
    if orientacao == "retrato":
        return "tblr"
    return "lrtb"

def montar_opcoes_cups(
    paginas_por_folha: int,
    duplex: bool,
    orientacao: str,
    intervalo_paginas: str
):
    if duplex:
        sides = "two-sided-short-edge" if orientacao == "paisagem" else "two-sided-long-edge"
    else:
        sides = "one-sided"

    orientacao_cups = 4 if orientacao == "paisagem" else 3

    opcoes = {
        "number-up": paginas_por_folha,
        "sides": sides,
        "orientation-requested": orientacao_cups,
    }

    if orientacao == "paisagem":
        # Alguns drivers CUPS respeitam melhor a flag "landscape" do que só orientation-requested.
        opcoes["landscape"] = True

    if paginas_por_folha == 2:
        # Garante disposição horizontal das duas páginas por folha.
        opcoes["number-up-layout"] = obter_layout_duas_por_folha(orientacao)

    intervalo = (intervalo_paginas or "").strip()
    if intervalo:
        opcoes["page-ranges"] = intervalo

    return opcoes


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

    if not arquivo_suportado(arquivo.filename):
        raise HTTPException(400, f"Formato não suportado. Envie {FORMATOS_UPLOAD_DESCRICAO}.")

    extensao_arquivo = obter_extensao_arquivo(arquivo.filename)

    if paginas_por_folha not in (1, 2, 4):
        raise HTTPException(400, "Paginação por folha inválida")
    if orientacao not in ("retrato", "paisagem"):
        raise HTTPException(400, "Orientação inválida")

    conteudo_arquivo = arquivo.file.read()
    if not conteudo_arquivo:
        raise HTTPException(400, "Arquivo vazio")

    caminho_spool = garantir_diretorio_spool()
    nome_arquivo_spool = f"{uuid.uuid4().hex}_{sanitizar_nome_arquivo(arquivo.filename)}"
    caminho_arquivo_original = caminho_spool / nome_arquivo_spool

    try:
        with caminho_arquivo_original.open("wb") as destino:
            destino.write(conteudo_arquivo)
    except OSError as exc:
        raise HTTPException(500, "Falha ao armazenar o arquivo para impressão.") from exc

    caminho_arquivo = caminho_arquivo_original
    caminho_convertido = caminho_arquivo_original.with_suffix(".pdf")
    try:
        caminho_arquivo = converter_para_pdf(caminho_arquivo_original, extensao_arquivo)
    except ValueError as exc:
        remover_arquivo_se_existir(caminho_arquivo_original)
        raise HTTPException(400, str(exc)) from exc
    except RuntimeError as exc:
        remover_arquivo_se_existir(caminho_arquivo_original)
        if caminho_convertido != caminho_arquivo_original:
            remover_arquivo_se_existir(caminho_convertido)
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        remover_arquivo_se_existir(caminho_arquivo_original)
        if caminho_convertido != caminho_arquivo_original:
            remover_arquivo_se_existir(caminho_convertido)
        raise HTTPException(500, "Falha ao preparar o arquivo para impressão.") from exc

    if caminho_arquivo != caminho_arquivo_original:
        remover_arquivo_se_existir(caminho_arquivo_original)

    try:
        # Conta páginas reais após padronizar o arquivo em PDF.
        paginas_pdf = contar_paginas_pdf(str(caminho_arquivo))
    except Exception:
        remover_arquivo_se_existir(caminho_arquivo)
        raise

    intervalo_normalizado = (intervalo_paginas or "").strip()
    try:
        paginas_selecionadas = contar_paginas_intervalo(intervalo_normalizado, paginas_pdf)
    except Exception:
        remover_arquivo_se_existir(caminho_arquivo)
        raise

    folhas_por_copia = ceil(paginas_selecionadas / paginas_por_folha)
    if duplex:
        folhas_por_copia = ceil(folhas_por_copia / 2)
    paginas_totais = folhas_por_copia * copias

    try:
        autorizado, restante = validar_e_consumir_cota(
            usuario_id=usuario["id"],
            paginas=paginas_totais
        )
    except Exception:
        remover_arquivo_se_existir(caminho_arquivo)
        raise

    if not autorizado:
        remover_arquivo_se_existir(caminho_arquivo)
        raise HTTPException(
            403,
            f"Cota insuficiente. Documento consome {paginas_totais} páginas. "
            f"Restam {restante}."
        )

    opcoes_cups = montar_opcoes_cups(
        paginas_por_folha=paginas_por_folha,
        duplex=duplex,
        orientacao=orientacao,
        intervalo_paginas=intervalo_normalizado
    )

    try:
        criar_job(
            usuario_id=usuario["id"],
            arquivo=arquivo.filename,
            arquivo_path=str(caminho_arquivo),
            copias=copias,
            paginas_totais=paginas_totais,
            paginas_por_folha=paginas_por_folha,
            duplex=duplex,
            orientacao=orientacao,
            intervalo_paginas=intervalo_normalizado,
            printer_name=DEFAULT_PRINTER_NAME,
            cups_options=json.dumps(opcoes_cups, ensure_ascii=True)
        )
    except Exception:
        remover_arquivo_se_existir(caminho_arquivo)
        raise

    return {
        "mensagem": "Job criado com sucesso",
        "paginas_documento": paginas_pdf,
        "paginas_selecionadas": paginas_selecionadas,
        "copias": copias,
        "paginas_consumidas": paginas_totais,
        "paginas_restantes": restante
    }

@app.post("/impressao/preview")
def preview_impressao(
    arquivo: UploadFile = File(...),
    _usuario = Depends(get_usuario_logado)
):
    if not arquivo or not arquivo.filename:
        raise HTTPException(400, "Arquivo não enviado")

    if not arquivo_suportado(arquivo.filename):
        raise HTTPException(400, f"Formato não suportado. Envie {FORMATOS_UPLOAD_DESCRICAO}.")

    extensao_arquivo = obter_extensao_arquivo(arquivo.filename)
    conteudo_arquivo = arquivo.file.read()
    if not conteudo_arquivo:
        raise HTTPException(400, "Arquivo vazio")

    caminho_spool = garantir_diretorio_spool()
    nome_arquivo_spool = f"preview_{uuid.uuid4().hex}_{sanitizar_nome_arquivo(arquivo.filename)}"
    caminho_arquivo_original = caminho_spool / nome_arquivo_spool

    try:
        with caminho_arquivo_original.open("wb") as destino:
            destino.write(conteudo_arquivo)
    except OSError as exc:
        raise HTTPException(500, "Falha ao armazenar arquivo para pré-visualização.") from exc

    caminho_arquivo_pdf = caminho_arquivo_original
    caminho_convertido = caminho_arquivo_original.with_suffix(".pdf")

    try:
        caminho_arquivo_pdf = converter_para_pdf(caminho_arquivo_original, extensao_arquivo)
        conteudo_pdf = caminho_arquivo_pdf.read_bytes()
        if not conteudo_pdf:
            raise HTTPException(500, "Falha ao gerar PDF de pré-visualização.")
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, "Falha ao gerar pré-visualização do documento.") from exc
    finally:
        remover_arquivo_se_existir(caminho_arquivo_original)
        if caminho_convertido != caminho_arquivo_original:
            remover_arquivo_se_existir(caminho_convertido)

    return Response(
        content=conteudo_pdf,
        media_type="application/pdf",
        headers={"Cache-Control": "no-store"}
    )



# =========================================================
# FILA (ADMIN)
# =========================================================

@app.get("/fila")
def fila(usuario = Depends(get_usuario_logado)):
    exigir_gestor(usuario)
    return listar_fila()


@app.post("/jobs/{job_id}/cancelar")
def cancelar(job_id: int, usuario = Depends(get_usuario_logado)):
    job = buscar_job(job_id)
    if not job:
        raise HTTPException(404, "Job não encontrado.")

    usuario_job_raw = job.get("usuario_id")
    usuario_job_id = int(usuario_job_raw) if usuario_job_raw is not None else None
    eh_gestor = usuario_eh_gestor(usuario)
    eh_dono = usuario_job_id is not None and usuario_job_id == int(usuario["id"])
    if not eh_gestor and not eh_dono:
        raise HTTPException(403, "Você não pode cancelar este job.")

    resultado = cancelar_job(job_id)
    if not resultado.get("cancelado"):
        raise HTTPException(409, "Este job não pode mais ser cancelado (já está em impressão ou finalizado).")

    paginas_restantes = None
    if usuario_job_id is not None:
        cota = obter_cota_atual(usuario_job_id)
        paginas_restantes = int(cota["restante"])

    return {
        "mensagem": "Job cancelado com sucesso.",
        "paginas_estornadas": int(resultado.get("paginas_estornadas") or 0),
        "paginas_restantes": paginas_restantes,
    }


@app.post("/jobs/{job_id}/prioridade")
def prioridade(
    job_id: int,
    urgente: bool = True,
    usuario = Depends(get_usuario_logado)
):
    exigir_gestor(usuario)
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
    cargo = normalizar_cargo_usuario(usuario)
    dados = dict(usuario)
    dados["cargo"] = cargo
    dados["modulos"] = modulos_por_cargo(cargo)
    dados["eh_gestor"] = usuario_eh_gestor(usuario)
    dados["eh_admin"] = usuario_eh_admin(usuario)
    return dados

@app.post("/internal/radius/ensure-nt-hash", include_in_schema=False)
def internal_radius_ensure_nt_hash(
    payload: RadiusEnsureNtHashIn,
    x_radius_secret: str = Header(default="", alias="X-RADIUS-SECRET"),
):
    secret = RADIUS_INTERNAL_SECRET
    if not secret or x_radius_secret != secret:
        return JSONResponse(status_code=403, content={"ok": False})

    if not ensure_nt_hash_for_radius(payload.username, payload.password):
        return JSONResponse(status_code=401, content={"ok": False})

    return {"ok": True}


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
    turmas = []
    for turma in listar_turmas_ativas():
        turno_turma = str(turma.get("turno") or "").strip().upper()
        config_turno = TURNOS_CONFIG.get(turno_turma)
        turmas.append({
            "nome": turma["nome"],
            "turno": turno_turma,
            "turno_nome": config_turno["nome"] if config_turno else "Turno não configurado",
            "aulas": config_turno["aulas"] if config_turno else 0,
            "turno_valido": bool(config_turno),
            "quantidade_estudantes": int(turma.get("quantidade_estudantes") or 0),
        })
    return {
        "turnos": turnos,
        "turmas": turmas,
    }


@app.get("/agendamento/professores")
def professores_agendamento(usuario = Depends(get_usuario_logado)):
    exigir_admin(usuario)
    return listar_professores_agendamento()


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
    turma = validar_turma(payload.turma)
    tema_aula = validar_tema_aula(payload.tema_aula)
    turno = str(turma.get("turno") or "").strip().upper()
    if turno not in TURNOS_CONFIG:
        raise HTTPException(400, "Turma sem turno configurado. Atualize o cadastro da turma no painel admin.")

    aula = validar_aula(payload.aula, turno)
    faixa_global = calcular_faixa_global(turno, aula)
    usuario_reserva_id = int(usuario["id"])
    professor_id_payload = payload.professor_id
    if professor_id_payload is not None:
        if not usuario_eh_admin(usuario):
            raise HTTPException(403, "Apenas administrador pode escolher o professor no agendamento.")

        professor = buscar_usuario_por_id(int(professor_id_payload))
        if not professor:
            raise HTTPException(404, "Professor não encontrado.")

        cargo_professor = normalizar_cargo_usuario(professor)
        if cargo_professor != CARGO_PROFESSOR:
            raise HTTPException(400, "O usuário selecionado não é professor.")

        usuario_reserva_id = int(professor["id"])

    capacidade_recurso = max(int(recurso.get("quantidade_itens") or 1), 1)
    reservas_ativas_faixa = contar_agendamentos_ativos_faixa(
        recurso_id=payload.recurso_id,
        data=data_reserva,
        faixa_global=faixa_global
    )

    if reservas_ativas_faixa >= capacidade_recurso:
        raise HTTPException(
            409,
            (
                f"Capacidade máxima atingida para este recurso nesta faixa. "
                f"Reservas ativas: {reservas_ativas_faixa}/{capacidade_recurso}."
            )
        )

    observacao = (payload.observacao or "").strip()
    agendamento_id = criar_agendamento(
        recurso_id=payload.recurso_id,
        usuario_id=usuario_reserva_id,
        data=data_reserva,
        turno=turno,
        aula=aula,
        faixa_global=faixa_global,
        turma=turma["nome"],
        tema_aula=tema_aula,
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

    try:
        data_reserva = datetime.strptime(str(agendamento["data"]), "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(400, "Data do agendamento inválida.") from exc

    if data_reserva < datetime.now().date():
        raise HTTPException(
            409,
            "Não é possível cancelar agendamentos de datas passadas."
        )

    dono_reserva = agendamento["usuario_id"] == usuario["id"]
    if not dono_reserva and not usuario_eh_admin(usuario):
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
    return templates.TemplateResponse(
        "professor.html",
        {
            "request": request,
            "cancel_window_seconds": PRINT_CANCEL_WINDOW_SECONDS,
        }
    )


@app.get("/professor")
def professor_redirect():
    return RedirectResponse(url="/impressao", status_code=302)


@app.get("/agendamento")
def agendamento_page(request: Request):
    response = templates.TemplateResponse(
        "agendamento.html",
        {
            "request": request,
            "asset_version": ASSET_VERSION,
        }
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/cadastro-professor")
def cadastro_professor_page(request: Request):
    return templates.TemplateResponse("cadastro_professor.html", {"request": request})


@app.get("/admin")
def admin_page(request: Request):
    response = templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "asset_version": ASSET_VERSION,
        }
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/coordenacao")
def coordenacao_page(request: Request):
    response = templates.TemplateResponse(
        "coordenacao.html",
        {
            "request": request,
            "asset_version": ASSET_VERSION,
        }
    )
    response.headers["Cache-Control"] = "no-store"
    return response

# =========================================================
# ADMIN
# =========================================================

@app.get("/admin/fila")
def fila_admin(usuario = Depends(get_usuario_logado)):
    exigir_gestor(usuario)

    return listar_jobs_ativos()

@app.get("/admin/historico")
def historico_admin(
    data_inicio: str = None,
    data_fim: str = None,
    usuario_id: int = None,
    usuario = Depends(get_usuario_logado)
):
    exigir_gestor(usuario)

    return listar_historico(data_inicio, data_fim, usuario_id)

@app.get("/admin/relatorio")
def relatorio_admin(
    data_inicio: str = None,
    data_fim: str = None,
    usuario = Depends(get_usuario_logado)
):
    exigir_gestor(usuario)
    data_inicio_norm = validar_data_agendamento(data_inicio) if data_inicio else None
    data_fim_norm = validar_data_agendamento(data_fim) if data_fim else None

    return gerar_relatorio_impressao(data_inicio_norm, data_fim_norm)

@app.get("/admin/relatorio/impressao")
def relatorio_impressao_admin(
    data_inicio: str = None,
    data_fim: str = None,
    usuario = Depends(get_usuario_logado)
):
    exigir_gestor(usuario)
    data_inicio_norm = validar_data_agendamento(data_inicio) if data_inicio else None
    data_fim_norm = validar_data_agendamento(data_fim) if data_fim else None

    return gerar_relatorio_impressao(data_inicio_norm, data_fim_norm)

@app.get("/admin/relatorio/recursos")
def relatorio_recursos_admin(
    data_inicio: str = None,
    data_fim: str = None,
    usuario = Depends(get_usuario_logado)
):
    exigir_gestor(usuario)
    data_inicio_norm = validar_data_agendamento(data_inicio) if data_inicio else None
    data_fim_norm = validar_data_agendamento(data_fim) if data_fim else None

    return {
        "por_recurso": gerar_relatorio_uso_recursos(data_inicio_norm, data_fim_norm),
        "por_professor": gerar_relatorio_uso_recursos_por_professor(data_inicio_norm, data_fim_norm)
    }

@app.get("/admin/turmas")
def listar_turmas_admin_api(
    incluir_inativas: bool = True,
    usuario = Depends(get_usuario_logado)
):
    exigir_gestor(usuario)
    return listar_turmas(incluir_inativas=incluir_inativas)

@app.post("/admin/turmas")
def criar_turma_admin(
    payload: TurmaCreateIn,
    usuario = Depends(get_usuario_logado)
):
    exigir_gestor(usuario)
    nome = payload.nome.strip()
    turno = validar_turno(payload.turno)
    quantidade_estudantes = validar_numero_nao_negativo(
        payload.quantidade_estudantes,
        "Quantidade de estudantes"
    )

    if not nome:
        raise HTTPException(400, "Nome da turma é obrigatório.")

    try:
        turma_id = criar_turma(
            nome=nome,
            turno=turno,
            quantidade_estudantes=quantidade_estudantes
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, "Já existe uma turma com este nome.") from exc

    return {"mensagem": "Turma cadastrada com sucesso.", "turma_id": turma_id}

@app.put("/admin/turmas/{turma_id}")
def atualizar_turma_admin(
    turma_id: int,
    payload: TurmaUpdateIn,
    usuario = Depends(get_usuario_logado)
):
    exigir_gestor(usuario)
    turno = validar_turno(payload.turno)
    quantidade_estudantes = validar_numero_nao_negativo(
        payload.quantidade_estudantes,
        "Quantidade de estudantes"
    )

    alterado = atualizar_turma_dados(
        turma_id=turma_id,
        turno=turno,
        quantidade_estudantes=quantidade_estudantes
    )
    if not alterado:
        raise HTTPException(404, "Turma não encontrada.")
    return {"mensagem": "Dados da turma atualizados com sucesso."}

@app.put("/admin/turmas/{turma_id}/status")
def atualizar_status_turma_admin(
    turma_id: int,
    payload: RecursoStatusIn,
    usuario = Depends(get_usuario_logado)
):
    exigir_gestor(usuario)
    alterado = atualizar_status_turma(turma_id, payload.ativo)
    if not alterado:
        raise HTTPException(404, "Turma não encontrada.")
    return {"mensagem": "Status da turma atualizado com sucesso."}

@app.get("/admin/disciplinas")
def listar_disciplinas_admin_api(
    incluir_inativas: bool = True,
    usuario = Depends(get_usuario_logado)
):
    exigir_gestor(usuario)
    return listar_disciplinas(incluir_inativas=incluir_inativas)

@app.post("/admin/disciplinas")
def criar_disciplina_admin(
    payload: DisciplinaCreateIn,
    usuario = Depends(get_usuario_logado)
):
    exigir_gestor(usuario)
    nome = payload.nome.strip()
    aulas_semanais = validar_numero_nao_negativo(payload.aulas_semanais, "Aulas semanais")

    if not nome:
        raise HTTPException(400, "Nome da disciplina é obrigatório.")

    try:
        disciplina_id = criar_disciplina(nome=nome, aulas_semanais=aulas_semanais)
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, "Já existe uma disciplina com este nome.") from exc

    return {"mensagem": "Disciplina cadastrada com sucesso.", "disciplina_id": disciplina_id}

@app.put("/admin/disciplinas/{disciplina_id}")
def atualizar_disciplina_admin(
    disciplina_id: int,
    payload: DisciplinaUpdateIn,
    usuario = Depends(get_usuario_logado)
):
    exigir_gestor(usuario)
    aulas_semanais = validar_numero_nao_negativo(payload.aulas_semanais, "Aulas semanais")
    alterado = atualizar_disciplina_dados(
        disciplina_id=disciplina_id,
        aulas_semanais=aulas_semanais
    )
    if not alterado:
        raise HTTPException(404, "Disciplina não encontrada.")
    return {"mensagem": "Dados da disciplina atualizados com sucesso."}

@app.put("/admin/disciplinas/{disciplina_id}/status")
def atualizar_status_disciplina_admin(
    disciplina_id: int,
    payload: RecursoStatusIn,
    usuario = Depends(get_usuario_logado)
):
    exigir_gestor(usuario)
    alterado = atualizar_status_disciplina(disciplina_id, payload.ativo)
    if not alterado:
        raise HTTPException(404, "Disciplina não encontrada.")
    return {"mensagem": "Status da disciplina atualizado com sucesso."}

@app.get("/professores/opcoes")
def opcoes_professores_publico():
    return obter_opcoes_cadastro_professor()

@app.post("/professores/cadastro")
def criar_professor_publico(payload: ProfessorCreateIn):
    dados = validar_payload_cadastro_professor(payload)

    try:
        professor_id = criar_professor(
            nome=dados["nome"],
            email=dados["email"],
            senha_hash=hash_senha(dados["senha"]),
            nt_hash=generate_nt_hash(dados["senha"]),
            data_nascimento=dados["data_nascimento"],
            aulas_semanais=dados["aulas_semanais"],
            turmas_quantidade=dados["turmas_quantidade"],
            turmas=dados["turmas"],
            disciplinas=dados["disciplinas"]
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, "Já existe um usuário com este email.") from exc

    return {"mensagem": "Cadastro realizado com sucesso.", "professor_id": professor_id}

@app.post("/professores/recuperar-senha")
def recuperar_senha_professor(payload: ProfessorRecuperarSenhaIn):
    email = str(payload.email or "").strip().lower()
    if not email:
        raise HTTPException(400, "Email e obrigatorio.")

    nova_senha = str(payload.nova_senha or "").strip()
    if not nova_senha:
        raise HTTPException(400, "Nova senha e obrigatoria.")
    validar_senha_forte(nova_senha)

    data_nascimento = validar_data_nascimento_professor(payload.data_nascimento)
    professor = buscar_usuario_por_email(email)

    if not professor or normalizar_cargo_usuario(professor) != CARGO_PROFESSOR:
        raise HTTPException(404, "Professor nao encontrado para os dados informados.")

    data_cadastrada = str(professor.get("data_nascimento") or "").strip()
    if not data_cadastrada:
        raise HTTPException(
            400,
            "Professor sem data de nascimento cadastrada. Solicite a redefinicao pelo painel."
        )

    if data_cadastrada != data_nascimento:
        raise HTTPException(400, "Dados de recuperacao invalidos.")

    alterado = atualizar_senha_usuario(int(professor["id"]), nova_senha)
    if not alterado:
        raise HTTPException(404, "Professor nao encontrado.")

    revogar_tokens_usuario(int(professor["id"]))
    return {"mensagem": "Senha redefinida com sucesso. Faca login com a nova senha."}

@app.get("/admin/professores/opcoes")
def opcoes_professores_admin(usuario = Depends(get_usuario_logado)):
    exigir_admin(usuario)
    return obter_opcoes_cadastro_professor()

@app.get("/admin/professores")
def listar_professores_painel(
    mes: str = None,
    usuario = Depends(get_usuario_logado)
):
    exigir_admin(usuario)
    mes_referencia = validar_mes_referencia(mes) if mes else mes_atual_referencia()
    regras = obter_regras_cota()
    professores = listar_professores_admin(mes_referencia)
    calculos = calcular_cotas_mensais_professores()
    calculos_por_usuario = {
        int(calculo["usuario_id"]): calculo
        for calculo in calculos
    }

    for professor in professores:
        calculo_professor = calculos_por_usuario.get(int(professor["id"]), {})
        professor["peso_total_individual"] = calculo_professor.get("peso_total_individual", 0)
        professor["cota_projetada"] = int(calculo_professor.get("cota_mensal_calculada", 0))

    return {
        "mes_referencia": mes_referencia,
        "regras_cota": regras,
        "professores": professores
    }

@app.get("/admin/coordenadores")
def listar_coordenadores_painel(usuario = Depends(get_usuario_logado)):
    exigir_admin(usuario)
    return listar_coordenadores_admin()

@app.post("/admin/coordenadores")
def criar_coordenador_painel(
    payload: CoordenadorCreateIn,
    usuario = Depends(get_usuario_logado)
):
    exigir_admin(usuario)
    dados = validar_payload_cadastro_coordenador(payload)

    try:
        coordenador_id = criar_coordenador(
            nome=dados["nome"],
            email=dados["email"],
            senha_hash=hash_senha(dados["senha"]),
            nt_hash=generate_nt_hash(dados["senha"]),
            data_nascimento=dados["data_nascimento"],
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, "Já existe um usuário com este email.") from exc

    return {"mensagem": "Coordenador cadastrado com sucesso.", "coordenador_id": coordenador_id}

@app.post("/admin/professores")
def criar_professor_painel(
    payload: ProfessorCreateIn,
    usuario = Depends(get_usuario_logado)
):
    exigir_admin(usuario)
    dados = validar_payload_cadastro_professor(payload)

    try:
        professor_id = criar_professor(
            nome=dados["nome"],
            email=dados["email"],
            senha_hash=hash_senha(dados["senha"]),
            nt_hash=generate_nt_hash(dados["senha"]),
            data_nascimento=dados["data_nascimento"],
            aulas_semanais=dados["aulas_semanais"],
            turmas_quantidade=dados["turmas_quantidade"],
            turmas=dados["turmas"],
            disciplinas=dados["disciplinas"]
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, "Já existe um usuário com este email.") from exc

    return {"mensagem": "Professor cadastrado com sucesso.", "professor_id": professor_id}

@app.put("/admin/professores/{professor_id}")
def atualizar_professor_painel(
    professor_id: int,
    payload: ProfessorUpdateIn,
    usuario = Depends(get_usuario_logado)
):
    exigir_admin(usuario)
    professor = buscar_usuario_por_id(professor_id)
    if not professor or professor["perfil"] != "professor":
        raise HTTPException(404, "Professor não encontrado.")

    dados = validar_payload_atualizacao_professor(payload)

    try:
        alterado = atualizar_professor(
            usuario_id=professor_id,
            nome=dados["nome"],
            email=dados["email"],
            data_nascimento=dados["data_nascimento"],
            aulas_semanais=dados["aulas_semanais"],
            turmas_quantidade=dados["turmas_quantidade"],
            turmas=dados["turmas"],
            disciplinas=dados["disciplinas"]
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, "Já existe um usuário com este email.") from exc

    if not alterado:
        raise HTTPException(404, "Professor não encontrado.")

    return {"mensagem": "Professor atualizado com sucesso."}

@app.put("/admin/professores/{professor_id}/senha")
def redefinir_senha_professor_painel(
    professor_id: int,
    payload: ProfessorRedefinirSenhaAdminIn,
    usuario = Depends(get_usuario_logado)
):
    exigir_admin(usuario)
    professor = buscar_usuario_por_id(professor_id)
    if not professor or professor["perfil"] != "professor":
        raise HTTPException(404, "Professor nao encontrado.")

    nova_senha = str(payload.nova_senha or "").strip()
    if not nova_senha:
        raise HTTPException(400, "Nova senha e obrigatoria.")
    validar_senha_forte(nova_senha)

    alterado = atualizar_senha_usuario(professor_id, nova_senha)
    if not alterado:
        raise HTTPException(404, "Professor nao encontrado.")

    revogar_tokens_usuario(professor_id)
    return {"mensagem": "Senha redefinida com sucesso."}

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
    cota_mensal_escola = validar_numero_nao_negativo(payload.cota_mensal_escola, "Cota mensal da escola")

    atualizar_regras_cota(base_paginas, paginas_por_aula, paginas_por_turma, cota_mensal_escola)
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
    exigir_gestor(usuario)
    return listar_recursos(incluir_inativos=incluir_inativos)

@app.post("/admin/recursos")
def criar_recurso_admin(
    payload: RecursoCreateIn,
    usuario = Depends(get_usuario_logado)
):
    exigir_gestor(usuario)

    nome = payload.nome.strip()
    tipo = payload.tipo.strip()
    descricao = (payload.descricao or "").strip()
    quantidade_itens = validar_numero_nao_negativo(payload.quantidade_itens, "Quantidade de itens")

    if not nome:
        raise HTTPException(400, "Nome do recurso é obrigatório.")
    if not tipo:
        raise HTTPException(400, "Tipo do recurso é obrigatório.")
    if quantidade_itens < 1:
        raise HTTPException(400, "Quantidade de itens deve ser no mínimo 1.")

    try:
        recurso_id = criar_recurso(
            nome=nome,
            tipo=tipo,
            descricao=descricao,
            quantidade_itens=quantidade_itens
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, "Já existe um recurso com este nome.") from exc

    return {"mensagem": "Recurso criado com sucesso.", "recurso_id": recurso_id}

@app.put("/admin/recursos/{recurso_id}")
def atualizar_recurso_admin(
    recurso_id: int,
    payload: RecursoUpdateIn,
    usuario = Depends(get_usuario_logado)
):
    exigir_gestor(usuario)
    nome = payload.nome.strip()
    tipo = payload.tipo.strip()
    descricao = (payload.descricao or "").strip()
    quantidade_itens = validar_numero_nao_negativo(payload.quantidade_itens, "Quantidade de itens")
    if not nome:
        raise HTTPException(400, "Nome do recurso é obrigatório.")
    if not tipo:
        raise HTTPException(400, "Tipo do recurso é obrigatório.")
    if quantidade_itens < 1:
        raise HTTPException(400, "Quantidade de itens deve ser no mínimo 1.")

    try:
        alterado = atualizar_recurso_dados(
            recurso_id=recurso_id,
            nome=nome,
            tipo=tipo,
            descricao=descricao,
            quantidade_itens=quantidade_itens
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, "Já existe um recurso com este nome.") from exc

    if not alterado:
        raise HTTPException(404, "Recurso não encontrado.")
    return {"mensagem": "Recurso atualizado com sucesso."}

@app.put("/admin/recursos/{recurso_id}/status")
def atualizar_status_recurso_admin(
    recurso_id: int,
    payload: RecursoStatusIn,
    usuario = Depends(get_usuario_logado)
):
    exigir_gestor(usuario)
    alterado = atualizar_status_recurso(recurso_id, payload.ativo)
    if not alterado:
        raise HTTPException(404, "Recurso não encontrado.")
    return {"mensagem": "Status do recurso atualizado com sucesso."}
