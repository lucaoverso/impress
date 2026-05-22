from fastapi import APIRouter, Depends, HTTPException, Query

from auth import get_usuario_logado
from routers.common import normalizar_cargo_usuario, usuario_tem_acesso_coordenacao
from schemas.pcpi_schemas import (
    PcpiRegistroManualIn,
    PcpiRegistroManualOut,
    PcpiRegistrosManuaisOut,
    PcpiSugestoesOut,
    PcpiTextoGeradoOut,
    PcpiTextoPreviewIn,
)
from services.pcpi_service import (
    carregar_contexto_pcpi,
    criar_registro_manual_pcpi,
    gerar_texto_completo_pcpi,
    gerar_texto_preview_pcpi,
    listar_registros_manuais_pcpi,
    validar_data_pcpi,
    validar_turno_pcpi,
)


router = APIRouter()


def _normalizar_cargo(usuario: dict) -> str:
    return normalizar_cargo_usuario(usuario)


def _exigir_gestor(usuario: dict):
    if not usuario_tem_acesso_coordenacao(usuario):
        raise HTTPException(403, "Acesso negado")
    return usuario


def _validar_data_iso_http(valor: str, campo: str = "Data") -> str:
    try:
        return validar_data_pcpi(valor, campo)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


def _validar_turno_http(valor: str) -> str:
    try:
        return validar_turno_pcpi(valor)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/pcpi/sugestoes", response_model=PcpiSugestoesOut)
def listar_sugestoes_pcpi_api(
    data: str = Query(...),
    turno: str = Query(...),
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    data_norm = _validar_data_iso_http(data)
    turno_norm = _validar_turno_http(turno)
    try:
        sugestoes, _registros = carregar_contexto_pcpi(data_norm, turno_norm)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return sugestoes


@router.get("/pcpi/registros-manuais", response_model=PcpiRegistrosManuaisOut)
def listar_registros_manuais_pcpi_api(
    data: str = Query(...),
    turno: str = Query(...),
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    data_norm = _validar_data_iso_http(data)
    turno_norm = _validar_turno_http(turno)
    try:
        return listar_registros_manuais_pcpi(data_norm, turno_norm)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/pcpi/registros-manuais", response_model=PcpiRegistroManualOut)
def criar_registro_manual_pcpi_api(
    payload: PcpiRegistroManualIn,
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    try:
        registro = criar_registro_manual_pcpi(payload, usuario)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
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
    data_norm = _validar_data_iso_http(data)
    turno_norm = _validar_turno_http(turno)
    try:
        return gerar_texto_completo_pcpi(data_norm, turno_norm)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/pcpi/texto/preview", response_model=PcpiTextoGeradoOut)
def gerar_texto_pcpi_preview_api(
    payload: PcpiTextoPreviewIn,
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    data_norm = _validar_data_iso_http(payload.data)
    turno_norm = _validar_turno_http(payload.turno)
    try:
        return gerar_texto_preview_pcpi(data_norm, turno_norm, payload.agendamento_ids)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
