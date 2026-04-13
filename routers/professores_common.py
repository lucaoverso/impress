from fastapi import HTTPException

from models import CoordenadorCreateIn, ProfessorCreateIn, ProfessorUpdateIn

from .common import (
    validar_data_nascimento_professor,
    validar_disciplinas_professor,
    validar_numero_nao_negativo,
    validar_senha_forte,
    validar_turmas_professor,
)


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
