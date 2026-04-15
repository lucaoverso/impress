import re
from datetime import datetime

from fastapi import HTTPException

from db.catalogos import listar_disciplinas_ativas, listar_turmas_ativas
from db.usuarios import buscar_usuario_por_id

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
    CARGO_ADMIN: ["impressao", "agendamento", "download", "gestao", "coordenacao", "pcpi", "preconselho"],
    CARGO_PROFESSOR: ["impressao", "agendamento", "download", "preconselho"],
    CARGO_COORDENADOR: ["download", "coordenacao", "pcpi", "preconselho"],
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
            "A senha deve ter no mínimo 8 caracteres, incluindo letra maiúscula, letra "
            "minúscula, número e caractere especial.",
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
            f"Aula inválida para o turno selecionado. Esse turno possui {max_aulas_turno} aulas.",
        )

    return aula_limpa


def calcular_faixa_global(turno: str, aula: str) -> int:
    turno_limpo = validar_turno(turno)
    numero_aula = int(validar_aula(aula, turno_limpo))
    faixa_global = numero_aula + FAIXA_GLOBAL_OFFSET_POR_TURNO[turno_limpo]

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


def usuario_tem_cota_ilimitada(usuario: dict) -> bool:
    return usuario_eh_admin(usuario)


def exigir_admin(usuario):
    if not usuario_eh_admin(usuario):
        raise HTTPException(403, "Acesso negado")
    return usuario


def exigir_gestor(usuario):
    if not usuario_eh_gestor(usuario):
        raise HTTPException(403, "Acesso negado")
    return usuario


def resolver_usuario_professor_selecionado(
    usuario: dict,
    professor_id: int | None,
    *,
    contexto: str,
) -> dict:
    if professor_id is None:
        return usuario

    professor_id_int = int(professor_id)
    if professor_id_int <= 0:
        raise HTTPException(400, "Professor inválido.")

    if not usuario_eh_admin(usuario):
        raise HTTPException(403, f"Apenas administrador pode selecionar o professor {contexto}.")

    professor = buscar_usuario_por_id(professor_id_int)
    if not professor:
        raise HTTPException(404, "Professor não encontrado.")

    if normalizar_cargo_usuario(professor) != CARGO_PROFESSOR:
        raise HTTPException(400, "O usuário selecionado não é professor.")

    return professor


def validar_numero_nao_negativo(valor: int, campo: str):
    if int(valor) < 0:
        raise HTTPException(400, f"{campo} não pode ser negativo.")
    return int(valor)
