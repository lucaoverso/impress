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
    validate_classroom,
    validate_discipline,
    validate_period,
)
from services.preconselho_service import (
    STATUS_PERIODO_PRE_CONSELHO_ABERTO,
    STATUS_PERIODO_PRE_CONSELHO_ENCERRADO,
    listar_niveis_atencao_pre_conselho,
    nome_periodo_pre_conselho,
    periodo_editavel_para_cargo,
    validar_categoria_motivo_pre_conselho,
    validar_etapa_pre_conselho,
    validar_status_periodo_pre_conselho,
)

RAV_HABILIDADE_DESCRICAO_MAX_LEN = 1000


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
    if status == STATUS_PERIODO_PRE_CONSELHO_ENCERRADO:
        pendentes = [
            item
            for item in repository.list_records(periodo_id=int(periodo_id))
            if item.get("pos_preconselho_recuperado") is None
        ]
        if pendentes:
            raise HTTPException(
                400,
                f"Existem {len(pendentes)} reavaliação(ões) pendente(s). Conclua-as antes de encerrar.",
            )
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


def list_preconselho_rav_skills(
    *,
    periodo_id: int | None,
    disciplina_id: int | None,
    turma_id: int | None,
    incluir_inativos: bool,
    usuario: dict,
) -> list[dict]:
    require_preconselho_access(usuario)
    if incluir_inativos and not is_admin_user(usuario):
        raise HTTPException(403, "Acesso negado.")
    if periodo_id is not None:
        validate_period(periodo_id)
    if disciplina_id is not None:
        validate_discipline(disciplina_id)
    if turma_id is not None:
        validate_classroom(turma_id)
    return repository.list_rav_skills(
        periodo_id=periodo_id,
        disciplina_id=disciplina_id,
        turma_id=turma_id,
        incluir_inativos=incluir_inativos,
    )


def _normalizar_turma_ids(turma_ids: list[int] | tuple[int, ...]) -> list[int]:
    ids = []
    for turma_id in turma_ids or []:
        turma = validate_classroom(turma_id)
        valor = int(turma["id"])
        if valor not in ids:
            ids.append(valor)
    if not ids:
        raise HTTPException(400, "Selecione ao menos uma turma para a habilidade de RAV.")
    return ids


def create_preconselho_rav_skill(payload, usuario: dict) -> dict:
    require_admin_access(usuario)
    validate_period(payload.periodo_id)
    validate_discipline(payload.disciplina_id)
    turma_ids = _normalizar_turma_ids(payload.turma_ids)
    try:
        habilidade_id = repository.create_rav_skill(
            periodo_id=int(payload.periodo_id),
            disciplina_id=int(payload.disciplina_id),
            codigo=optional_text(payload.codigo, "Codigo", max_len=80),
            descricao=require_text(
                payload.descricao,
                "Habilidade",
                max_len=RAV_HABILIDADE_DESCRICAO_MAX_LEN,
            ),
            turma_ids=turma_ids,
            ordem=int(payload.ordem or 0),
        )
    except Exception as exc:
        raise HTTPException(500, "Falha ao criar a habilidade de RAV.") from exc
    habilidade = repository.get_rav_skill(habilidade_id)
    if not habilidade:
        raise HTTPException(500, "Falha ao carregar a habilidade criada.")
    return habilidade


def update_preconselho_rav_skill(habilidade_id: int, payload, usuario: dict) -> dict:
    require_admin_access(usuario)
    validate_period(payload.periodo_id)
    validate_discipline(payload.disciplina_id)
    turma_ids = _normalizar_turma_ids(payload.turma_ids)
    atualizado = repository.update_rav_skill_data(
        habilidade_id,
        periodo_id=int(payload.periodo_id),
        disciplina_id=int(payload.disciplina_id),
        codigo=optional_text(payload.codigo, "Codigo", max_len=80),
        descricao=require_text(
            payload.descricao,
            "Habilidade",
            max_len=RAV_HABILIDADE_DESCRICAO_MAX_LEN,
        ),
        turma_ids=turma_ids,
        ordem=int(payload.ordem or 0),
    )
    if not atualizado:
        raise HTTPException(404, "Habilidade de RAV nÃ£o encontrada.")
    habilidade = repository.get_rav_skill(habilidade_id)
    if not habilidade:
        raise HTTPException(500, "Falha ao carregar a habilidade atualizada.")
    return habilidade


def _mapa_por_nome(itens: list[dict]) -> dict[str, dict]:
    return {str(item.get("nome") or "").strip().casefold(): item for item in itens}


def _resolver_disciplina_habilidade(item) -> dict:
    if item.disciplina_id:
        return validate_discipline(item.disciplina_id)
    nome = str(item.disciplina or "").strip().casefold()
    disciplina = _mapa_por_nome(repository.list_active_disciplines()).get(nome)
    if not disciplina:
        raise HTTPException(400, f"Disciplina nao encontrada: {item.disciplina or item.disciplina_id}")
    return disciplina


def _resolver_periodo_habilidade(
    item,
    periodo_padrao_id: int | None = None,
    periodo_padrao_nome: str = "",
) -> dict:
    periodo_id = int(item.periodo_id or periodo_padrao_id or 0)
    if periodo_id > 0:
        return validate_period(periodo_id)
    nome = str(item.periodo or periodo_padrao_nome or "").strip().casefold()
    periodo = next(
        (
            periodo
            for periodo in repository.list_periods()
            if str(periodo.get("nome") or "").strip().casefold() == nome
        ),
        None,
    )
    if not periodo:
        raise HTTPException(400, f"Periodo nao encontrado: {item.periodo or periodo_padrao_nome or periodo_padrao_id}")
    return periodo


def _resolver_turmas_habilidade(item) -> list[int]:
    ids = list(item.turma_ids or [])
    turmas_texto = list(item.turmas or [])
    if item.turma:
        turmas_texto.extend(
            parte.strip()
            for parte in str(item.turma).split(",")
            if parte.strip()
        )
    if turmas_texto:
        turmas_por_nome = _mapa_por_nome(repository.list_active_classrooms())
        for nome_turma in turmas_texto:
            turma = turmas_por_nome.get(str(nome_turma or "").strip().casefold())
            if not turma:
                raise HTTPException(400, f"Turma nao encontrada: {nome_turma}")
            ids.append(int(turma["id"]))
    return _normalizar_turma_ids(ids)


def import_preconselho_rav_skills(payload, usuario: dict) -> dict:
    require_admin_access(usuario)
    habilidades = list(payload.habilidades or [])
    resultado = {
        "total_recebido": len(habilidades),
        "criadas": 0,
        "atualizadas": 0,
        "ignoradas": 0,
        "erros": [],
    }

    for indice, item in enumerate(habilidades, start=1):
        try:
            periodo = _resolver_periodo_habilidade(item, payload.periodo_id, payload.periodo)
            periodo_id = int(periodo["id"])
            disciplina = _resolver_disciplina_habilidade(item)
            turma_ids = _resolver_turmas_habilidade(item)
            descricao = require_text(
                item.descricao or item.texto,
                "Habilidade",
                max_len=RAV_HABILIDADE_DESCRICAO_MAX_LEN,
            )
            codigo = optional_text(item.codigo, "Codigo", max_len=80)
            existente = repository.get_rav_skill_by_key(
                periodo_id=periodo_id,
                disciplina_id=int(disciplina["id"]),
                codigo=codigo,
                descricao=descricao,
            )
            if existente:
                repository.update_rav_skill_data(
                    int(existente["id"]),
                    periodo_id=periodo_id,
                    disciplina_id=int(disciplina["id"]),
                    codigo=codigo,
                    descricao=descricao,
                    turma_ids=turma_ids,
                    ordem=int(item.ordem or 0),
                )
                resultado["atualizadas"] += 1
            else:
                repository.create_rav_skill(
                    periodo_id=periodo_id,
                    disciplina_id=int(disciplina["id"]),
                    codigo=codigo,
                    descricao=descricao,
                    turma_ids=turma_ids,
                    ordem=int(item.ordem or 0),
                )
                resultado["criadas"] += 1
        except HTTPException as exc:
            resultado["ignoradas"] += 1
            resultado["erros"].append(f"Item {indice}: {exc.detail}")
        except Exception as exc:
            resultado["ignoradas"] += 1
            resultado["erros"].append(f"Item {indice}: falha ao importar ({exc})")

    return resultado


def update_preconselho_rav_skill_status(habilidade_id: int, payload, usuario: dict) -> dict:
    require_admin_access(usuario)
    atualizado = repository.update_rav_skill_status(habilidade_id, bool(payload.ativo))
    if not atualizado:
        raise HTTPException(404, "Habilidade de RAV nÃ£o encontrada.")
    habilidade = repository.get_rav_skill(habilidade_id)
    if not habilidade:
        raise HTTPException(500, "Falha ao carregar a habilidade atualizada.")
    return habilidade


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
