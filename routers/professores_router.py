import sqlite3

from fastapi import APIRouter, HTTPException

from db.usuarios import (
    atualizar_senha_usuario,
    buscar_usuario_por_email,
    criar_professor,
    revogar_tokens_usuario,
)
from models import ProfessorCreateIn, ProfessorRecuperarSenhaIn
from security.nt_hash import generate_nt_hash
from services.auth_service import hash_senha

from .common import (
    CARGO_PROFESSOR,
    normalizar_cargo_usuario,
    obter_opcoes_cadastro_professor,
    validar_data_nascimento_professor,
    validar_senha_forte,
)
from .professores_common import validar_payload_cadastro_professor

router = APIRouter()


@router.get("/professores/opcoes")
def opcoes_professores_publico():
    return obter_opcoes_cadastro_professor()


@router.post("/professores/cadastro")
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
            disciplinas=dados["disciplinas"],
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, "Já existe um usuário com este email.") from exc

    return {"mensagem": "Cadastro realizado com sucesso.", "professor_id": professor_id}


@router.post("/professores/recuperar-senha")
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
            "Professor sem data de nascimento cadastrada. Solicite a redefinicao pelo painel.",
        )

    if data_cadastrada != data_nascimento:
        raise HTTPException(400, "Dados de recuperacao invalidos.")

    alterado = atualizar_senha_usuario(int(professor["id"]), nova_senha)
    if not alterado:
        raise HTTPException(404, "Professor nao encontrado.")

    revogar_tokens_usuario(int(professor["id"]))
    return {"mensagem": "Senha redefinida com sucesso. Faca login com a nova senha."}
