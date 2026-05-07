from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from auth import get_usuario_logado
from db.agendamento import listar_agendamentos
from db.pcpi import (
    buscar_registro_pcpi_manual_por_id,
    criar_registro_pcpi_manual,
    listar_registros_pcpi_manuais,
)
from db.usuarios import listar_cargas_professores_por_usuario_ids
from models import (
    PcpiRegistroManualIn,
    PcpiRegistroManualOut,
    PcpiRegistrosManuaisOut,
    PcpiSugestoesOut,
    PcpiTextoGeradoOut,
    PcpiTextoPreviewIn,
)
from services.pcpi_service import (
    TURNOS_PCPI_CONFIG,
    agendamento_pertence_ao_turno_pcpi,
    gerar_texto_pcpi,
    montar_sugestoes_pcpi,
    nome_turno_pcpi,
    turno_agendamento_pertence_ao_turno_pcpi,
)
from routers.common import normalizar_cargo_usuario, usuario_tem_acesso_coordenacao


router = APIRouter()


def _normalizar_cargo(usuario: dict) -> str:
    return normalizar_cargo_usuario(usuario)


def _exigir_gestor(usuario: dict):
    if not usuario_tem_acesso_coordenacao(usuario):
        raise HTTPException(403, "Acesso negado")
    return usuario


def _validar_data_iso(valor: str, campo: str = "Data") -> str:
    texto = str(valor or "").strip()
    if not texto:
        raise HTTPException(400, f"{campo} inválida. Use o formato YYYY-MM-DD.")

    try:
        data = datetime.strptime(texto, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(400, f"{campo} inválida. Use o formato YYYY-MM-DD.") from exc
    return data.isoformat()


def _validar_turno(valor: str) -> str:
    turno = str(valor or "").strip().upper()
    if turno not in TURNOS_PCPI_CONFIG:
        turnos_validos = ", ".join(TURNOS_PCPI_CONFIG.keys())
        raise HTTPException(400, f"Turno inválido. Use um dos valores: {turnos_validos}.")
    return turno


def _texto_obrigatorio(valor: str, campo: str, *, max_len: int = 255) -> str:
    texto = str(valor or "").strip()
    if not texto:
        raise HTTPException(400, f"{campo} é obrigatório.")
    if len(texto) > max_len:
        raise HTTPException(400, f"{campo} excede o limite de {max_len} caracteres.")
    return texto


def _texto_opcional(valor: str | None, campo: str = "Texto", *, max_len: int = 255) -> str:
    texto = str(valor or "").strip()
    if not texto:
        return ""
    if len(texto) > max_len:
        raise HTTPException(400, f"{campo} excede o limite de {max_len} caracteres.")
    return texto


def _obter_usuario_id(usuario: dict) -> int | None:
    try:
        valor = int(usuario.get("id"))
    except (TypeError, ValueError):
        return None
    return valor if valor > 0 else None


def _carregar_contexto_pcpi(data: str, turno: str) -> tuple[dict, list[dict]]:
    agendamentos_dia = listar_agendamentos(
        data_inicio=data,
        data_fim=data,
    )
    agendamentos_turno = [
        item
        for item in agendamentos_dia
        if agendamento_pertence_ao_turno_pcpi(item, turno)
    ]

    cargas = listar_cargas_professores_por_usuario_ids(
        [int(item.get("usuario_id") or 0) for item in agendamentos_turno]
    )
    sugestoes = montar_sugestoes_pcpi(data, turno, agendamentos_turno, cargas)
    registros = _listar_registros_manuais_normalizados(data, turno)
    return sugestoes, registros


def _listar_registros_manuais_normalizados(data: str, turno: str) -> list[dict]:
    registros = listar_registros_pcpi_manuais(data=data)
    registros_turno = [
        dict(item)
        for item in registros
        if turno_agendamento_pertence_ao_turno_pcpi(item.get("turno"), turno)
    ]

    for registro in registros_turno:
        registro["turno"] = turno
    return registros_turno


def _filtrar_itens_automaticos_por_ids(
    itens: list[dict], agendamento_ids: list[int] | None
) -> list[dict]:
    if agendamento_ids is None:
        return list(itens or [])

    ids_validos = {
        int(valor) for valor in agendamento_ids if isinstance(valor, int) and int(valor) > 0
    }
    if not ids_validos:
        return []

    return [item for item in (itens or []) if int(item.get("agendamento_id") or 0) in ids_validos]


@router.get("/pcpi/sugestoes", response_model=PcpiSugestoesOut)
def listar_sugestoes_pcpi_api(
    data: str = Query(...),
    turno: str = Query(...),
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    data_norm = _validar_data_iso(data)
    turno_norm = _validar_turno(turno)
    sugestoes, _registros = _carregar_contexto_pcpi(data_norm, turno_norm)
    return sugestoes


@router.get("/pcpi/registros-manuais", response_model=PcpiRegistrosManuaisOut)
def listar_registros_manuais_pcpi_api(
    data: str = Query(...),
    turno: str = Query(...),
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    data_norm = _validar_data_iso(data)
    turno_norm = _validar_turno(turno)

    registros = _listar_registros_manuais_normalizados(data_norm, turno_norm)
    return {
        "data": data_norm,
        "turno": turno_norm,
        "turno_nome": nome_turno_pcpi(turno_norm),
        "total_registros": len(registros),
        "itens": registros,
    }


@router.post("/pcpi/registros-manuais", response_model=PcpiRegistroManualOut)
def criar_registro_manual_pcpi_api(
    payload: PcpiRegistroManualIn,
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)

    data_norm = _validar_data_iso(payload.data)
    turno_norm = _validar_turno(payload.turno)
    professor_nome = _texto_opcional(payload.professor_nome, "Professor ou setor", max_len=160)
    componente = _texto_opcional(payload.componente, "Componente ou recurso", max_len=160)
    turma = _texto_opcional(payload.turma, "Turma", max_len=120)
    descricao_curta = _texto_obrigatorio(payload.descricao_curta, "Descrição curta", max_len=500)
    observacoes = _texto_opcional(payload.observacoes, "Observações", max_len=2000)
    usuario_id = _obter_usuario_id(usuario)

    registro_id = criar_registro_pcpi_manual(
        data=data_norm,
        turno=turno_norm,
        tipo_acao=str(payload.tipo_acao).strip(),
        professor_nome=professor_nome,
        componente=componente,
        turma=turma,
        descricao_curta=descricao_curta,
        observacoes=observacoes,
        criado_por_usuario_id=usuario_id,
        atualizado_por_usuario_id=usuario_id,
    )

    registro = buscar_registro_pcpi_manual_por_id(registro_id)
    if not registro:
        raise HTTPException(500, "Falha ao carregar o registro manual criado.")
    return registro


@router.get("/pcpi/texto", response_model=PcpiTextoGeradoOut)
def gerar_texto_pcpi_api(
    data: str = Query(...),
    turno: str = Query(...),
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    data_norm = _validar_data_iso(data)
    turno_norm = _validar_turno(turno)

    sugestoes, registros = _carregar_contexto_pcpi(data_norm, turno_norm)
    return gerar_texto_pcpi(
        data=data_norm,
        turno=turno_norm,
        itens_automaticos=sugestoes.get("itens") or [],
        registros_manuais=registros,
    )


@router.post("/pcpi/texto/preview", response_model=PcpiTextoGeradoOut)
def gerar_texto_pcpi_preview_api(
    payload: PcpiTextoPreviewIn,
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    data_norm = _validar_data_iso(payload.data)
    turno_norm = _validar_turno(payload.turno)

    sugestoes, registros = _carregar_contexto_pcpi(data_norm, turno_norm)
    itens_automaticos = _filtrar_itens_automaticos_por_ids(
        sugestoes.get("itens") or [],
        payload.agendamento_ids,
    )

    return gerar_texto_pcpi(
        data=data_norm,
        turno=turno_norm,
        itens_automaticos=itens_automaticos,
        registros_manuais=registros,
    )
