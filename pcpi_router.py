from fastapi import APIRouter, Depends, HTTPException, Query

from auth import get_usuario_logado
from routers.common import usuario_tem_acesso_coordenacao
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
    filtrar_itens_automaticos_pcpi_por_ids,
    gerar_texto_pcpi,
    listar_registros_manuais_pcpi_normalizados,
    nome_turno_pcpi,
    validar_data_iso_pcpi,
    validar_turno_pcpi,
)


router = APIRouter()


def _exigir_gestor(usuario: dict):
    if not usuario_tem_acesso_coordenacao(usuario):
        raise HTTPException(403, "Acesso negado")
    return usuario


@router.get("/pcpi/sugestoes", response_model=PcpiSugestoesOut)
def listar_sugestoes_pcpi_api(
    data: str = Query(...),
    turno: str = Query(...),
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    data_norm = validar_data_iso_pcpi(data)
    turno_norm = validar_turno_pcpi(turno)
    sugestoes, _registros = carregar_contexto_pcpi(data_norm, turno_norm)
    return sugestoes


@router.get("/pcpi/registros-manuais", response_model=PcpiRegistrosManuaisOut)
def listar_registros_manuais_pcpi_api(
    data: str = Query(...),
    turno: str = Query(...),
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    data_norm = validar_data_iso_pcpi(data)
    turno_norm = validar_turno_pcpi(turno)

    registros = listar_registros_manuais_pcpi_normalizados(data_norm, turno_norm)
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
    return criar_registro_manual_pcpi(payload, usuario)


@router.get("/pcpi/texto", response_model=PcpiTextoGeradoOut)
def gerar_texto_pcpi_api(
    data: str = Query(...),
    turno: str = Query(...),
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    data_norm = validar_data_iso_pcpi(data)
    turno_norm = validar_turno_pcpi(turno)

    sugestoes, registros = carregar_contexto_pcpi(data_norm, turno_norm)
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
    data_norm = validar_data_iso_pcpi(payload.data)
    turno_norm = validar_turno_pcpi(payload.turno)

    sugestoes, registros = carregar_contexto_pcpi(data_norm, turno_norm)
    itens_automaticos = filtrar_itens_automaticos_pcpi_por_ids(
        sugestoes.get("itens") or [],
        payload.agendamento_ids,
    )

    return gerar_texto_pcpi(
        data=data_norm,
        turno=turno_norm,
        itens_automaticos=itens_automaticos,
        registros_manuais=registros,
    )
