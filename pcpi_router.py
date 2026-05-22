from fastapi import APIRouter, Depends, HTTPException, Query

from auth import get_usuario_logado
from repositories.pcpi_repository import (
    criar_e_buscar_registro_pcpi_manual,
    listar_agendamentos_pcpi_por_data,
    listar_cargas_professores_pcpi_por_usuario_ids,
    listar_registros_pcpi_manuais_por_data,
)
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
    agendamento_pertence_ao_turno_pcpi,
    filtrar_itens_automaticos_pcpi,
    gerar_texto_pcpi,
    montar_contexto_pcpi,
    montar_listagem_registros_manuais_pcpi,
    obter_usuario_id_pcpi,
    validar_data_pcpi,
    validar_texto_obrigatorio_pcpi,
    validar_texto_opcional_pcpi,
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


def _texto_obrigatorio_http(valor: str, campo: str, *, max_len: int = 255) -> str:
    try:
        return validar_texto_obrigatorio_pcpi(valor, campo, max_len=max_len)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


def _texto_opcional_http(valor: str | None, campo: str = "Texto", *, max_len: int = 255) -> str:
    try:
        return validar_texto_opcional_pcpi(valor, campo, max_len=max_len)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


def _carregar_contexto_pcpi_http(data: str, turno: str) -> tuple[dict, list[dict]]:
    agendamentos_dia = listar_agendamentos_pcpi_por_data(data)
    cargas = listar_cargas_professores_pcpi_por_usuario_ids(
        [
            int(item.get("usuario_id") or 0)
            for item in agendamentos_dia
            if agendamento_pertence_ao_turno_pcpi(item, turno)
        ]
    )
    registros = listar_registros_pcpi_manuais_por_data(data=data)
    try:
        return montar_contexto_pcpi(data, turno, agendamentos_dia, cargas, registros)
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
    sugestoes, _registros = _carregar_contexto_pcpi_http(data_norm, turno_norm)
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
        return montar_listagem_registros_manuais_pcpi(
            data_norm,
            turno_norm,
            listar_registros_pcpi_manuais_por_data(data=data_norm),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/pcpi/registros-manuais", response_model=PcpiRegistroManualOut)
def criar_registro_manual_pcpi_api(
    payload: PcpiRegistroManualIn,
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)

    data_norm = _validar_data_iso_http(payload.data)
    turno_norm = _validar_turno_http(payload.turno)
    professor_nome = _texto_opcional_http(payload.professor_nome, "Professor ou setor", max_len=160)
    componente = _texto_opcional_http(payload.componente, "Componente ou recurso", max_len=160)
    turma = _texto_opcional_http(payload.turma, "Turma", max_len=120)
    descricao_curta = _texto_obrigatorio_http(payload.descricao_curta, "Descricao curta", max_len=500)
    observacoes = _texto_opcional_http(payload.observacoes, "Observacoes", max_len=2000)
    usuario_id = obter_usuario_id_pcpi(usuario)

    registro = criar_e_buscar_registro_pcpi_manual(
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

    sugestoes, registros = _carregar_contexto_pcpi_http(data_norm, turno_norm)
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
    data_norm = _validar_data_iso_http(payload.data)
    turno_norm = _validar_turno_http(payload.turno)

    sugestoes, registros = _carregar_contexto_pcpi_http(data_norm, turno_norm)
    itens_automaticos = filtrar_itens_automaticos_pcpi(
        sugestoes.get("itens") or [],
        payload.agendamento_ids,
    )

    return gerar_texto_pcpi(
        data=data_norm,
        turno=turno_norm,
        itens_automaticos=itens_automaticos,
        registros_manuais=registros,
    )
