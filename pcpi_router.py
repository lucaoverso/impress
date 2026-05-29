from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from auth import get_usuario_logado
from db.agendamento import buscar_agendamento_por_id, listar_agendamentos
from db.horario_escolar import listar_horarios_escolares
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
from routers.common import normalizar_cargo_usuario, usuario_tem_acesso_coordenacao
from services.pcpi_pdf_service import gerar_pdf_texto_pcpi
from services.pcpi_service import (
    TURNOS_PCPI_CONFIG,
    agendamento_pertence_ao_turno_pcpi,
    gerar_texto_pcpi,
    montar_sugestoes_pcpi,
    nome_turno_pcpi,
    turno_agendamento_pertence_ao_turno_pcpi,
)


router = APIRouter()

DIAS_SEMANA_POR_WEEKDAY = {
    0: "SEGUNDA",
    1: "TERCA",
    2: "QUARTA",
    3: "QUINTA",
    4: "SEXTA",
    5: "SABADO",
    6: "DOMINGO",
}


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


def _normalizar_agendamento_id(valor) -> int | None:
    try:
        agendamento_id = int(valor)
    except (TypeError, ValueError):
        return None
    return agendamento_id if agendamento_id > 0 else None


def _dia_semana_data_iso(data_iso: str) -> str:
    data_ref = datetime.strptime(data_iso, "%Y-%m-%d").date()
    return DIAS_SEMANA_POR_WEEKDAY.get(data_ref.weekday(), "")


def _montar_texto_acao_pcpi_registro(registro: dict) -> str:
    acao_realizada = str(registro.get("acao_realizada") or "").strip()
    descricao_curta = str(registro.get("descricao_curta") or "").strip()
    observacoes = str(registro.get("observacoes") or "").strip()

    acao = acao_realizada[:1].lower() + acao_realizada[1:] if acao_realizada else ""
    descricao = descricao_curta[:1].lower() + descricao_curta[1:] if descricao_curta else ""
    observacao = observacoes[:1].lower() + observacoes[1:] if observacoes else ""

    if not acao and not descricao and not observacao:
        return ""

    texto = acao or descricao or observacao
    if acao and descricao:
        texto = f"{acao} e {descricao}"
    elif descricao and not acao:
        texto = descricao

    if observacao:
        texto = f"{texto}, com {observacao}" if texto else observacao
    return texto


def _resolver_disciplina_horario_item(item: dict, horarios: list[dict]) -> str:
    professor_id = int(item.get("professor_id") or 0)
    turma = str(item.get("turma") or "").strip()
    faixa_global = int(item.get("faixa_global") or 0)
    aula_numero = int(item.get("aula_numero") or 0)

    for horario in horarios:
        if int(horario.get("professor_id") or 0) != professor_id:
            continue
        if str(horario.get("turma_nome") or "").strip() != turma:
            continue
        if faixa_global > 0 and int(horario.get("faixa_global") or 0) == faixa_global:
            return str(horario.get("disciplina_nome") or "").strip()
        if aula_numero > 0 and int(horario.get("aula_numero") or 0) == aula_numero:
            return str(horario.get("disciplina_nome") or "").strip()
    return ""


def _integrar_contexto_automatico_pcpi(
    sugestoes: dict,
    registros: list[dict],
    horarios: list[dict],
) -> tuple[dict, list[dict]]:
    itens = [dict(item) for item in (sugestoes.get("itens") or [])]
    registros_livres = []
    registros_por_agendamento: dict[int, list[dict]] = {}

    for registro in registros:
        agendamento_id = _normalizar_agendamento_id(registro.get("agendamento_id"))
        if agendamento_id is None:
            registros_livres.append(registro)
            continue
        registros_por_agendamento.setdefault(agendamento_id, []).append(registro)

    for item in itens:
        disciplina_horario = _resolver_disciplina_horario_item(item, horarios)
        if disciplina_horario:
            item["disciplina"] = disciplina_horario

        textos_acao = [
            _montar_texto_acao_pcpi_registro(registro)
            for registro in registros_por_agendamento.get(int(item.get("agendamento_id") or 0), [])
        ]
        textos_acao = [texto for texto in textos_acao if texto]
        item["texto_acao_pcpi"] = "; ".join(textos_acao)

    sugestoes_enriquecidas = dict(sugestoes)
    sugestoes_enriquecidas["itens"] = itens
    return sugestoes_enriquecidas, registros_livres


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
    horarios = listar_horarios_escolares(
        ano_letivo=int(str(data).split("-")[0]),
        dia_semana=_dia_semana_data_iso(data),
    )
    return _integrar_contexto_automatico_pcpi(sugestoes, registros, horarios)


def _listar_registros_manuais_normalizados(data: str, turno: str) -> list[dict]:
    registros = listar_registros_pcpi_manuais(data=data)
    registros_turno = [
        dict(item)
        for item in registros
        if turno_agendamento_pertence_ao_turno_pcpi(item.get("turno"), turno)
    ]

    for registro in registros_turno:
        registro["turno"] = turno
        registro["origem"] = str(registro.get("origem") or "MANUAL").strip().upper() or "MANUAL"
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


def _filtrar_registros_por_agendamento(
    registros: list[dict], agendamento_ids: list[int] | None
) -> list[dict]:
    if agendamento_ids is None:
        return list(registros or [])

    ids_validos = {
        int(valor) for valor in agendamento_ids if isinstance(valor, int) and int(valor) > 0
    }
    filtrados = []
    for registro in registros or []:
        agendamento_id = _normalizar_agendamento_id(registro.get("agendamento_id"))
        if agendamento_id is None or agendamento_id in ids_validos:
            filtrados.append(registro)
    return filtrados


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
    total_registros_manuais = sum(
        1 for item in registros if not _normalizar_agendamento_id(item.get("agendamento_id"))
    )
    total_registros_vinculados = len(registros) - total_registros_manuais
    return {
        "data": data_norm,
        "turno": turno_norm,
        "turno_nome": nome_turno_pcpi(turno_norm),
        "total_registros": len(registros),
        "total_registros_manuais": total_registros_manuais,
        "total_registros_vinculados": total_registros_vinculados,
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
    agendamento_id = _normalizar_agendamento_id(payload.agendamento_id)
    professor_nome = _texto_opcional(payload.professor_nome, "Professor ou setor", max_len=160)
    componente = _texto_opcional(payload.componente, "Componente ou recurso", max_len=160)
    turma = _texto_opcional(payload.turma, "Turma", max_len=120)
    acao_realizada = _texto_opcional(payload.acao_realizada, "Ação realizada", max_len=200)
    descricao_curta = _texto_obrigatorio(payload.descricao_curta, "Descrição curta", max_len=500)
    resultado = _texto_opcional(payload.resultado, "Resultado", max_len=400)
    observacoes = _texto_opcional(payload.observacoes, "Observações", max_len=2000)
    usuario_id = _obter_usuario_id(usuario)
    origem = "MANUAL"

    if agendamento_id is not None:
        agendamento = buscar_agendamento_por_id(agendamento_id)
        if not agendamento:
            raise HTTPException(404, "Agendamento vinculado não encontrado.")
        if str(agendamento.get("data") or "") != data_norm:
            raise HTTPException(400, "O agendamento vinculado não pertence à data selecionada.")
        if not agendamento_pertence_ao_turno_pcpi(agendamento, turno_norm):
            raise HTTPException(400, "O agendamento vinculado não pertence ao turno selecionado.")
        origem = "AGENDAMENTO"

    if origem == "AGENDAMENTO" and not acao_realizada:
        raise HTTPException(400, "Informe a ação realizada no atendimento agendado.")

    registro_id = criar_registro_pcpi_manual(
        data=data_norm,
        turno=turno_norm,
        tipo_acao=str(payload.tipo_acao).strip(),
        origem=origem,
        agendamento_id=agendamento_id,
        acao_realizada=acao_realizada,
        professor_nome=professor_nome,
        componente=componente,
        turma=turma,
        descricao_curta=descricao_curta,
        resultado=resultado,
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
    registros_filtrados = _filtrar_registros_por_agendamento(registros, payload.agendamento_ids)

    return gerar_texto_pcpi(
        data=data_norm,
        turno=turno_norm,
        itens_automaticos=itens_automaticos,
        registros_manuais=registros_filtrados,
    )


@router.post("/pcpi/texto/pdf")
def gerar_texto_pcpi_pdf_api(
    payload: PcpiTextoPreviewIn,
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    dados_texto = gerar_texto_pcpi_preview_api(payload=payload, usuario=usuario)
    pdf_bytes = gerar_pdf_texto_pcpi(dados_texto)
    nome_arquivo = f"pcpi-{dados_texto['data']}-{dados_texto['turno'].lower()}.pdf"
    headers = {"Content-Disposition": f'attachment; filename="{nome_arquivo}"'}
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)
