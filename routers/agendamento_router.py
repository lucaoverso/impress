from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from auth import get_usuario_logado
from db.agendamento import (
    buscar_agendamento_por_id,
    cancelar_agendamento,
    contar_agendamentos_ativos_faixa,
    criar_agendamento,
    listar_agendamentos,
)
from db.catalogos import buscar_recurso_por_id, listar_recursos_ativos, listar_turmas_ativas
from db.usuarios import listar_professores_agendamento
from models import AgendamentoIn

from .common import (
    TURNOS_CONFIG,
    calcular_faixa_global,
    exigir_admin,
    resolver_usuario_professor_selecionado,
    usuario_eh_admin,
    validar_aula,
    validar_data_agendamento,
    validar_tema_aula,
    validar_turma,
)

router = APIRouter()


@router.get("/agendamento/recursos")
def recursos_agendamento(_usuario=Depends(get_usuario_logado)):
    return listar_recursos_ativos()


@router.get("/agendamento/opcoes")
def opcoes_agendamento(_usuario=Depends(get_usuario_logado)):
    turnos = [
        {"id": turno_id, "nome": cfg["nome"], "aulas": cfg["aulas"]}
        for turno_id, cfg in TURNOS_CONFIG.items()
    ]
    turmas = []
    for turma in listar_turmas_ativas():
        turno_turma = str(turma.get("turno") or "").strip().upper()
        config_turno = TURNOS_CONFIG.get(turno_turma)
        turmas.append(
            {
                "nome": turma["nome"],
                "turno": turno_turma,
                "turno_nome": config_turno["nome"] if config_turno else "Turno não configurado",
                "aulas": config_turno["aulas"] if config_turno else 0,
                "turno_valido": bool(config_turno),
                "quantidade_estudantes": int(turma.get("quantidade_estudantes") or 0),
            }
        )
    return {"turnos": turnos, "turmas": turmas}


@router.get("/agendamento/professores")
def professores_agendamento(usuario=Depends(get_usuario_logado)):
    exigir_admin(usuario)
    return listar_professores_agendamento()


@router.get("/agendamento/reservas")
def listar_reservas_agendamento(
    data_inicio: str = None,
    data_fim: str = None,
    recurso_id: int = None,
    _usuario=Depends(get_usuario_logado),
):
    data_inicio_norm = validar_data_agendamento(data_inicio) if data_inicio else None
    data_fim_norm = validar_data_agendamento(data_fim) if data_fim else None

    if data_inicio_norm and data_fim_norm and data_inicio_norm > data_fim_norm:
        raise HTTPException(400, "Período inválido: data inicial maior que data final.")

    return listar_agendamentos(
        data_inicio=data_inicio_norm,
        data_fim=data_fim_norm,
        recurso_id=recurso_id,
    )


@router.post("/agendamento/reservas")
def criar_reserva_agendamento(
    payload: AgendamentoIn,
    usuario=Depends(get_usuario_logado),
):
    recurso = buscar_recurso_por_id(payload.recurso_id)
    if not recurso or recurso["ativo"] != 1:
        raise HTTPException(404, "Recurso não encontrado.")

    data_reserva = validar_data_agendamento(payload.data)
    turma = validar_turma(payload.turma)
    tema_aula = validar_tema_aula(payload.tema_aula)
    turno = str(turma.get("turno") or "").strip().upper()
    if turno not in TURNOS_CONFIG:
        raise HTTPException(
            400, "Turma sem turno configurado. Atualize o cadastro da turma no painel admin."
        )

    aula = validar_aula(payload.aula, turno)
    faixa_global = calcular_faixa_global(turno, aula)
    usuario_reserva = resolver_usuario_professor_selecionado(
        usuario,
        payload.professor_id,
        contexto="solicitante do agendamento",
    )
    usuario_reserva_id = int(usuario_reserva["id"])

    capacidade_recurso = max(int(recurso.get("quantidade_itens") or 1), 1)
    reservas_ativas_faixa = contar_agendamentos_ativos_faixa(
        recurso_id=payload.recurso_id,
        data=data_reserva,
        faixa_global=faixa_global,
    )

    if reservas_ativas_faixa >= capacidade_recurso:
        raise HTTPException(
            409,
            (
                "Capacidade máxima atingida para este recurso nesta faixa. "
                f"Reservas ativas: {reservas_ativas_faixa}/{capacidade_recurso}."
            ),
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
        observacao=observacao,
    )

    return {
        "mensagem": "Agendamento realizado com sucesso.",
        "agendamento_id": agendamento_id,
    }


@router.post("/agendamento/reservas/{agendamento_id}/cancelar")
def cancelar_reserva_agendamento(
    agendamento_id: int,
    usuario=Depends(get_usuario_logado),
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
        raise HTTPException(409, "Não é possível cancelar agendamentos de datas passadas.")

    dono_reserva = agendamento["usuario_id"] == usuario["id"]
    if not dono_reserva and not usuario_eh_admin(usuario):
        raise HTTPException(403, "Você não pode cancelar este agendamento.")

    cancelado = cancelar_agendamento(agendamento_id)
    if not cancelado:
        raise HTTPException(400, "Não foi possível cancelar o agendamento.")

    return {"mensagem": "Agendamento cancelado com sucesso."}
