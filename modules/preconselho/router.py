"""HTTP router for the pre-conselho domain module."""

from fastapi import APIRouter, Depends, Query

from auth import get_usuario_logado
from models import (
    PreConselhoConsolidadoOut,
    PreConselhoContextoOut,
    PreConselhoEstudantePainelOut,
    PreConselhoMotivoCreateIn,
    PreConselhoMotivoOut,
    PreConselhoMotivoStatusIn,
    PreConselhoMotivoUpdateIn,
    PreConselhoMotivoReavaliacaoOut,
    PreConselhoMotivoReavaliacaoCreateIn,
    PreConselhoMotivoReavaliacaoUpdateIn,
    PreConselhoPeriodoCreateIn,
    PreConselhoPeriodoOut,
    PreConselhoPeriodoStatusIn,
    PreConselhoPeriodoUpdateIn,
    PreConselhoRavHabilidadeCreateIn,
    PreConselhoRavHabilidadeImportIn,
    PreConselhoRavHabilidadeImportOut,
    PreConselhoRavHabilidadeOut,
    PreConselhoRavHabilidadeStatusIn,
    PreConselhoRavHabilidadeUpdateIn,
    PreConselhoRavTurmaOut,
    PreConselhoRegistroSaveIn,
    PreConselhoReavaliacaoIn,
    PreConselhoRegistrosOut,
    PreConselhoRelatorioOut,
    PreConselhoTextoOut,
    PreConselhoTextoPreviewIn,
    PreConselhoTurmaDisciplinaOut,
)

from .service import (
    build_preconselho_context,
    build_preconselho_consolidated,
    build_preconselho_rav_view,
    build_preconselho_report,
    create_preconselho_period,
    create_preconselho_rav_skill,
    create_preconselho_reason,
    create_review_reason,
    delete_preconselho_record,
    import_preconselho_rav_skills,
    list_my_classroom_disciplines,
    list_panel_students,
    list_preconselho_attention_levels,
    list_preconselho_periods,
    list_preconselho_rav_skills,
    list_preconselho_reasons,
    list_review_reasons,
    list_preconselho_records,
    preview_preconselho_text,
    review_preconselho_record,
    save_preconselho_record,
    update_preconselho_period,
    update_preconselho_period_status,
    update_preconselho_rav_skill,
    update_preconselho_rav_skill_status,
    update_preconselho_reason,
    update_preconselho_reason_status,
    update_review_reason,
    update_review_reason_status,
)

router = APIRouter()


@router.get("/preconselho/contexto", response_model=PreConselhoContextoOut)
def obter_contexto_preconselho_api(usuario=Depends(get_usuario_logado)):
    return build_preconselho_context(usuario)


@router.get(
    "/preconselho/minhas-turmas-disciplinas",
    response_model=list[PreConselhoTurmaDisciplinaOut],
)
def listar_minhas_turmas_disciplinas_preconselho_api(
    periodo_id: int = Query(...),
    usuario=Depends(get_usuario_logado),
):
    return list_my_classroom_disciplines(periodo_id=periodo_id, usuario=usuario)


@router.get("/preconselho/estudantes", response_model=list[PreConselhoEstudantePainelOut])
def listar_estudantes_preconselho_api(
    periodo_id: int = Query(...),
    turma_id: int = Query(...),
    disciplina_id: int = Query(...),
    q: str = Query(default=""),
    status: str = Query(default="todos"),
    professor_id: int | None = Query(default=None),
    usuario=Depends(get_usuario_logado),
):
    return list_panel_students(
        periodo_id=periodo_id,
        turma_id=turma_id,
        disciplina_id=disciplina_id,
        q=q,
        status=status,
        professor_id=professor_id,
        usuario=usuario,
    )


@router.post("/preconselho/texto/preview", response_model=PreConselhoTextoOut)
def gerar_texto_preview_preconselho_api(
    payload: PreConselhoTextoPreviewIn,
    usuario=Depends(get_usuario_logado),
):
    return preview_preconselho_text(payload, usuario)


@router.post("/preconselho/registros")
def salvar_registro_preconselho_api(
    payload: PreConselhoRegistroSaveIn,
    usuario=Depends(get_usuario_logado),
):
    return save_preconselho_record(payload, usuario)


@router.delete("/preconselho/registros/{registro_id}")
def excluir_registro_preconselho_api(
    registro_id: int,
    usuario=Depends(get_usuario_logado),
):
    return delete_preconselho_record(registro_id, usuario)


@router.put("/preconselho/registros/{registro_id}/reavaliacao")
def reavaliar_registro_preconselho_api(
    registro_id: int,
    payload: PreConselhoReavaliacaoIn,
    usuario=Depends(get_usuario_logado),
):
    return review_preconselho_record(registro_id, payload, usuario)


@router.get("/preconselho/registros", response_model=PreConselhoRegistrosOut)
def listar_registros_preconselho_api(
    periodo_id: int = Query(...),
    turma_id: int | None = Query(default=None),
    disciplina_id: int | None = Query(default=None),
    professor_id: int | None = Query(default=None),
    usuario=Depends(get_usuario_logado),
):
    return list_preconselho_records(
        periodo_id=periodo_id,
        turma_id=turma_id,
        disciplina_id=disciplina_id,
        professor_id=professor_id,
        usuario=usuario,
    )


@router.get("/preconselho/consolidado", response_model=PreConselhoConsolidadoOut)
def gerar_consolidado_preconselho_api(
    periodo_id: int = Query(...),
    turma_id: int | None = Query(default=None),
    disciplina_id: int | None = Query(default=None),
    professor_id: int | None = Query(default=None),
    versao: str = "preconselho",
    usuario=Depends(get_usuario_logado),
):
    return build_preconselho_consolidated(
        periodo_id=periodo_id,
        turma_id=turma_id,
        disciplina_id=disciplina_id,
        professor_id=professor_id,
        versao=versao,
        usuario=usuario,
    )


@router.get("/preconselho/relatorio", response_model=PreConselhoRelatorioOut)
def gerar_relatorio_preconselho_api(
    periodo_id: int = Query(...),
    usuario=Depends(get_usuario_logado),
):
    return build_preconselho_report(periodo_id=periodo_id, usuario=usuario)


@router.get("/preconselho/rav/turma", response_model=PreConselhoRavTurmaOut)
def visualizar_rav_turma_preconselho_api(
    periodo_id: int = Query(...),
    turma_id: int | None = Query(default=None),
    usuario=Depends(get_usuario_logado),
):
    return build_preconselho_rav_view(
        periodo_id=periodo_id,
        turma_id=turma_id,
        usuario=usuario,
    )


@router.get("/preconselho/periodos", response_model=list[PreConselhoPeriodoOut])
def listar_periodos_preconselho_api(usuario=Depends(get_usuario_logado)):
    return list_preconselho_periods(usuario)


@router.post("/preconselho/periodos", response_model=PreConselhoPeriodoOut)
def criar_periodo_preconselho_api(
    payload: PreConselhoPeriodoCreateIn,
    usuario=Depends(get_usuario_logado),
):
    return create_preconselho_period(payload, usuario)


@router.put("/preconselho/periodos/{periodo_id}", response_model=PreConselhoPeriodoOut)
def atualizar_periodo_preconselho_api(
    periodo_id: int,
    payload: PreConselhoPeriodoUpdateIn,
    usuario=Depends(get_usuario_logado),
):
    return update_preconselho_period(periodo_id, payload, usuario)


@router.put(
    "/preconselho/periodos/{periodo_id}/status",
    response_model=PreConselhoPeriodoOut,
)
def atualizar_status_periodo_preconselho_api(
    periodo_id: int,
    payload: PreConselhoPeriodoStatusIn,
    usuario=Depends(get_usuario_logado),
):
    return update_preconselho_period_status(periodo_id, payload, usuario)


@router.get("/preconselho/motivos", response_model=list[PreConselhoMotivoOut])
def listar_motivos_preconselho_api(
    incluir_inativos: bool = Query(default=False),
    usuario=Depends(get_usuario_logado),
):
    return list_preconselho_reasons(incluir_inativos=incluir_inativos, usuario=usuario)


@router.post("/preconselho/motivos", response_model=PreConselhoMotivoOut)
def criar_motivo_preconselho_api(
    payload: PreConselhoMotivoCreateIn,
    usuario=Depends(get_usuario_logado),
):
    return create_preconselho_reason(payload, usuario)


@router.put("/preconselho/motivos/{motivo_id}", response_model=PreConselhoMotivoOut)
def atualizar_motivo_preconselho_api(
    motivo_id: int,
    payload: PreConselhoMotivoUpdateIn,
    usuario=Depends(get_usuario_logado),
):
    return update_preconselho_reason(motivo_id, payload, usuario)


@router.put(
    "/preconselho/motivos/{motivo_id}/status",
    response_model=PreConselhoMotivoOut,
)
def atualizar_status_motivo_preconselho_api(
    motivo_id: int,
    payload: PreConselhoMotivoStatusIn,
    usuario=Depends(get_usuario_logado),
):
    return update_preconselho_reason_status(motivo_id, payload, usuario)


@router.get("/preconselho/motivos-reavaliacao", response_model=list[PreConselhoMotivoReavaliacaoOut])
def listar_motivos_reavaliacao_api(incluir_inativos: bool = Query(default=False), usuario=Depends(get_usuario_logado)):
    return list_review_reasons(incluir_inativos=incluir_inativos, usuario=usuario)


@router.post("/preconselho/motivos-reavaliacao", response_model=PreConselhoMotivoReavaliacaoOut)
def criar_motivo_reavaliacao_api(payload: PreConselhoMotivoReavaliacaoCreateIn, usuario=Depends(get_usuario_logado)):
    return create_review_reason(payload, usuario)


@router.put("/preconselho/motivos-reavaliacao/{motivo_id}", response_model=PreConselhoMotivoReavaliacaoOut)
def atualizar_motivo_reavaliacao_api(motivo_id: int, payload: PreConselhoMotivoReavaliacaoUpdateIn, usuario=Depends(get_usuario_logado)):
    return update_review_reason(motivo_id, payload, usuario)


@router.put("/preconselho/motivos-reavaliacao/{motivo_id}/status", response_model=PreConselhoMotivoReavaliacaoOut)
def atualizar_status_motivo_reavaliacao_api(motivo_id: int, payload: PreConselhoMotivoStatusIn, usuario=Depends(get_usuario_logado)):
    return update_review_reason_status(motivo_id, payload, usuario)


@router.get("/preconselho/habilidades-rav", response_model=list[PreConselhoRavHabilidadeOut])
def listar_habilidades_rav_preconselho_api(
    periodo_id: int | None = Query(default=None),
    disciplina_id: int | None = Query(default=None),
    turma_id: int | None = Query(default=None),
    incluir_inativos: bool = Query(default=False),
    usuario=Depends(get_usuario_logado),
):
    return list_preconselho_rav_skills(
        periodo_id=periodo_id,
        disciplina_id=disciplina_id,
        turma_id=turma_id,
        incluir_inativos=incluir_inativos,
        usuario=usuario,
    )


@router.post("/preconselho/habilidades-rav", response_model=PreConselhoRavHabilidadeOut)
def criar_habilidade_rav_preconselho_api(
    payload: PreConselhoRavHabilidadeCreateIn,
    usuario=Depends(get_usuario_logado),
):
    return create_preconselho_rav_skill(payload, usuario)


@router.post(
    "/preconselho/habilidades-rav/importar-json",
    response_model=PreConselhoRavHabilidadeImportOut,
)
def importar_habilidades_rav_preconselho_api(
    payload: PreConselhoRavHabilidadeImportIn,
    usuario=Depends(get_usuario_logado),
):
    return import_preconselho_rav_skills(payload, usuario)


@router.put("/preconselho/habilidades-rav/{habilidade_id}", response_model=PreConselhoRavHabilidadeOut)
def atualizar_habilidade_rav_preconselho_api(
    habilidade_id: int,
    payload: PreConselhoRavHabilidadeUpdateIn,
    usuario=Depends(get_usuario_logado),
):
    return update_preconselho_rav_skill(habilidade_id, payload, usuario)


@router.put(
    "/preconselho/habilidades-rav/{habilidade_id}/status",
    response_model=PreConselhoRavHabilidadeOut,
)
def atualizar_status_habilidade_rav_preconselho_api(
    habilidade_id: int,
    payload: PreConselhoRavHabilidadeStatusIn,
    usuario=Depends(get_usuario_logado),
):
    return update_preconselho_rav_skill_status(habilidade_id, payload, usuario)


@router.get("/preconselho/niveis-atencao")
def listar_niveis_atencao_preconselho_api(usuario=Depends(get_usuario_logado)):
    return list_preconselho_attention_levels(usuario)
