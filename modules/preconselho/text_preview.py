"""Text preview flow for pre-conselho records."""

from fastapi import HTTPException

from .service import list_active_valid_reasons, optional_text, require_preconselho_access
from services.preconselho_service import (
    gerar_texto_pre_conselho_individual,
    validar_motivos_pos_pre_conselho,
    validar_nivel_atencao_pre_conselho,
)


def preview_preconselho_text(payload, usuario: dict) -> dict:
    require_preconselho_access(usuario)
    motivos = list_active_valid_reasons(payload.motivo_ids)
    observacao_pos_preconselho = optional_text(
        payload.pos_preconselho_observacao,
        "Observacao do pos pre-conselho",
        max_len=1000,
    )
    try:
        (
            pos_preconselho_recuperado,
            _pos_preconselho_motivo_ids,
            pos_preconselho_motivos,
        ) = validar_motivos_pos_pre_conselho(
            payload.pos_preconselho_motivo_ids,
            payload.pos_preconselho_recuperado,
            observacao_pos_preconselho,
        )
        nivel_atencao = validar_nivel_atencao_pre_conselho(payload.nivel_atencao)
        return gerar_texto_pre_conselho_individual(
            motivos=motivos,
            observacao_professor=optional_text(
                payload.observacao_professor,
                "Observacao do professor",
                max_len=1000,
            ),
            nivel_atencao=nivel_atencao,
            estudante_nome=str(payload.estudante_nome or "").strip(),
            disciplina_nome=str(payload.disciplina_nome or "").strip(),
            pos_preconselho_recuperado=pos_preconselho_recuperado,
            pos_preconselho_motivos=pos_preconselho_motivos,
            pos_preconselho_observacao=observacao_pos_preconselho,
            estudante_em_rav=bool(payload.estudante_em_rav),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
