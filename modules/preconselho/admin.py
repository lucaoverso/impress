"""Administrative flows for pre-conselho."""

from fastapi import HTTPException

from . import repository
from .service import (
    is_admin_user,
    normalize_user_role,
    optional_text,
    require_admin_access,
    require_preconselho_access,
    require_text,
    validate_iso_date,
)
from services.preconselho_service import (
    STATUS_PERIODO_PRE_CONSELHO_ABERTO,
    listar_niveis_atencao_pre_conselho,
    nome_periodo_pre_conselho,
    periodo_editavel_para_cargo,
    validar_categoria_motivo_pre_conselho,
    validar_etapa_pre_conselho,
    validar_status_periodo_pre_conselho,
)


def list_preconselho_periods(usuario: dict) -> list[dict]:
    require_preconselho_access(usuario)
    cargo = normalize_user_role(usuario)
    return [
        {**item, "editavel": periodo_editavel_para_cargo(item.get("status"), cargo)}
        for item in repository.list_periods()
    ]


def create_preconselho_period(payload, usuario: dict) -> dict:
    require_admin_access(usuario)
    etapa = validar_etapa_pre_conselho(payload.etapa)
    status = validar_status_periodo_pre_conselho(payload.status or STATUS_PERIODO_PRE_CONSELHO_ABERTO)
    ano_letivo = int(payload.ano_letivo)
    nome = optional_text(payload.nome, "Nome", max_len=120) or nome_periodo_pre_conselho(
        ano_letivo,
        etapa,
    )
    try:
        periodo_id = repository.create_period(
            nome=nome,
            ano_letivo=ano_letivo,
            etapa=etapa,
            data_inicio=validate_iso_date(payload.data_inicio, "Data inicial"),
            data_fim=validate_iso_date(payload.data_fim, "Data final"),
            status=status,
            tem_rav=bool(payload.tem_rav),
        )
    except Exception as exc:
        raise HTTPException(500, "Falha ao criar o período.") from exc
    periodo = repository.get_period(periodo_id)
    if not periodo:
        raise HTTPException(500, "Falha ao carregar o período criado.")
    return periodo


def update_preconselho_period(periodo_id: int, payload, usuario: dict) -> dict:
    require_admin_access(usuario)
    periodo = repository.get_period(periodo_id)
    if not periodo:
        raise HTTPException(404, "Período não encontrado.")

    etapa = validar_etapa_pre_conselho(payload.etapa)
    ano_letivo = int(payload.ano_letivo)
    nome = optional_text(payload.nome, "Nome", max_len=120) or nome_periodo_pre_conselho(
        ano_letivo,
        etapa,
    )
    atualizado = repository.update_period_data(
        periodo_id,
        nome=nome,
        ano_letivo=ano_letivo,
        etapa=etapa,
        data_inicio=validate_iso_date(payload.data_inicio, "Data inicial"),
        data_fim=validate_iso_date(payload.data_fim, "Data final"),
        tem_rav=bool(payload.tem_rav),
    )
    if not atualizado:
        raise HTTPException(404, "Período não encontrado.")
    periodo = repository.get_period(periodo_id)
    if not periodo:
        raise HTTPException(500, "Falha ao carregar o período atualizado.")
    return periodo


def update_preconselho_period_status(periodo_id: int, payload, usuario: dict) -> dict:
    require_admin_access(usuario)
    status = validar_status_periodo_pre_conselho(payload.status)
    atualizado = repository.update_period_status(periodo_id, status)
    if not atualizado:
        raise HTTPException(404, "Período não encontrado.")
    periodo = repository.get_period(periodo_id)
    if not periodo:
        raise HTTPException(500, "Falha ao carregar o período atualizado.")
    return periodo


def list_preconselho_reasons(*, incluir_inativos: bool, usuario: dict) -> list[dict]:
    require_preconselho_access(usuario)
    if incluir_inativos and not is_admin_user(usuario):
        raise HTTPException(403, "Acesso negado.")
    return repository.list_reasons(incluir_inativos=incluir_inativos)


def create_preconselho_reason(payload, usuario: dict) -> dict:
    require_admin_access(usuario)
    try:
        motivo_id = repository.create_reason(
            categoria=validar_categoria_motivo_pre_conselho(payload.categoria),
            codigo=require_text(payload.codigo, "Código", max_len=120).casefold(),
            descricao=require_text(payload.descricao, "Descrição", max_len=255),
            ordem=int(payload.ordem or 0),
        )
    except Exception as exc:
        raise HTTPException(500, "Falha ao criar o motivo.") from exc
    motivo = repository.get_reason(motivo_id)
    if not motivo:
        raise HTTPException(500, "Falha ao carregar o motivo criado.")
    return motivo


def update_preconselho_reason(motivo_id: int, payload, usuario: dict) -> dict:
    require_admin_access(usuario)
    atualizado = repository.update_reason_data(
        motivo_id,
        categoria=validar_categoria_motivo_pre_conselho(payload.categoria),
        descricao=require_text(payload.descricao, "Descrição", max_len=255),
        ordem=int(payload.ordem or 0),
    )
    if not atualizado:
        raise HTTPException(404, "Motivo não encontrado.")
    motivo = repository.get_reason(motivo_id)
    if not motivo:
        raise HTTPException(500, "Falha ao carregar o motivo atualizado.")
    return motivo


def update_preconselho_reason_status(motivo_id: int, payload, usuario: dict) -> dict:
    require_admin_access(usuario)
    atualizado = repository.update_reason_status(motivo_id, bool(payload.ativo))
    if not atualizado:
        raise HTTPException(404, "Motivo não encontrado.")
    motivo = repository.get_reason(motivo_id)
    if not motivo:
        raise HTTPException(500, "Falha ao carregar o motivo atualizado.")
    return motivo


def list_preconselho_attention_levels(usuario: dict) -> list[dict]:
    require_preconselho_access(usuario)
    return listar_niveis_atencao_pre_conselho()
