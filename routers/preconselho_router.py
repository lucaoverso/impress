from datetime import datetime
from sqlite3 import IntegrityError

from fastapi import APIRouter, Depends, HTTPException, Query

from auth import get_usuario_logado
from db.docencia import listar_atribuicoes_docentes_por_usuario_ids
from repositories.preconselho_repository import (
    atualizar_motivo_pre_conselho_dados,
    atualizar_periodo_pre_conselho_dados,
    atualizar_status_motivo_pre_conselho,
    atualizar_status_periodo_pre_conselho,
    buscar_motivo_pre_conselho_por_id,
    buscar_motivos_pre_conselho_por_ids,
    buscar_periodo_pre_conselho_por_id,
    criar_motivo_pre_conselho,
    criar_periodo_pre_conselho,
    listar_estudantes_pre_conselho_painel,
    listar_motivos_pre_conselho,
    listar_periodos_pre_conselho,
)
from schemas.preconselho_schemas import (
    PreConselhoConsolidadoOut,
    PreConselhoContextoOut,
    PreConselhoDisciplinaOut,
    PreConselhoEstudantePainelOut,
    PreConselhoMotivoCreateIn,
    PreConselhoMotivoOut,
    PreConselhoMotivoStatusIn,
    PreConselhoMotivoUpdateIn,
    PreConselhoPeriodoCreateIn,
    PreConselhoPeriodoOut,
    PreConselhoPeriodoStatusIn,
    PreConselhoPeriodoUpdateIn,
    PreConselhoProfessorOut,
    PreConselhoRegistroOut,
    PreConselhoRegistrosOut,
    PreConselhoRegistroSaveIn,
    PreConselhoRelatorioOut,
    PreConselhoTextoOut,
    PreConselhoTextoPreviewIn,
    PreConselhoTurmaDisciplinaOut,
    PreConselhoTurmaOut,
)
from services.preconselho_contexto_service import (
    listar_estudantes_painel_preconselho,
    minhas_turmas_disciplinas_preconselho,
    normalizar_cargo_preconselho,
    obter_contexto_preconselho,
)
from services.preconselho_consolidado_service import (
    gerar_consolidado_preconselho_service,
)
from services.preconselho_registros_service import (
    excluir_registro_preconselho_service,
    listar_registros_preconselho_service,
    salvar_registro_preconselho,
)
from services.preconselho_relatorio_service import (
    gerar_relatorio_preconselho_service,
)
from services.preconselho_service import (
    STATUS_PERIODO_PRE_CONSELHO_ABERTO,
    gerar_texto_pre_conselho_individual,
    listar_motivos_pos_pre_conselho,
    listar_niveis_atencao_pre_conselho,
    periodo_editavel_para_cargo,
    validar_categoria_motivo_pre_conselho,
    validar_motivos_pos_pre_conselho,
    validar_etapa_pre_conselho,
    validar_nivel_atencao_pre_conselho,
    validar_status_periodo_pre_conselho,
)
from routers.common import normalizar_cargo_usuario, usuario_tem_acesso_coordenacao


router = APIRouter()


def _normalizar_cargo(usuario: dict) -> str:
    return normalizar_cargo_preconselho(usuario)


def _exigir_acesso_preconselho(usuario: dict):
    if _normalizar_cargo(usuario) not in {"ADMIN", "COORDENADOR", "PROFESSOR"}:
        raise HTTPException(403, "Acesso negado.")
    return usuario


def _exigir_admin(usuario: dict):
    if _normalizar_cargo(usuario) != "ADMIN":
        raise HTTPException(403, "Acesso negado.")
    return usuario


def _usuario_id(usuario: dict) -> int:
    try:
        valor = int(usuario.get("id"))
    except (TypeError, ValueError) as exc:
        raise HTTPException(401, "Usuário inválido.") from exc
    if valor <= 0:
        raise HTTPException(401, "Usuário inválido.")
    return valor


def _usuario_eh_admin(usuario: dict) -> bool:
    return _normalizar_cargo(usuario) == "ADMIN"


def _usuario_eh_gestor(usuario: dict) -> bool:
    return usuario_tem_acesso_coordenacao(usuario)


def _usuario_eh_professor(usuario: dict) -> bool:
    return _normalizar_cargo(usuario) == "PROFESSOR"


def _texto_obrigatorio(valor: str, campo: str, *, max_len: int = 255) -> str:
    texto = str(valor or "").strip()
    if not texto:
        raise HTTPException(400, f"{campo} é obrigatório.")
    if len(texto) > max_len:
        raise HTTPException(400, f"{campo} excede o limite de {max_len} caracteres.")
    return texto


def _texto_opcional(valor: str | None, campo: str, *, max_len: int = 1000) -> str:
    texto = str(valor or "").strip()
    if not texto:
        return ""
    if len(texto) > max_len:
        raise HTTPException(400, f"{campo} excede o limite de {max_len} caracteres.")
    return texto


def _validar_data_iso(valor: str, campo: str) -> str:
    texto = _texto_obrigatorio(valor, campo, max_len=20)
    try:
        data = datetime.strptime(texto, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(400, f"{campo} inválida. Use o formato YYYY-MM-DD.") from exc
    return data.isoformat()


def _validar_periodo(periodo_id: int) -> dict:
    try:
        periodo_id_valor = int(periodo_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(400, "Período inválido.") from exc
    periodo = buscar_periodo_pre_conselho_por_id(periodo_id_valor)
    if not periodo:
        raise HTTPException(404, "Período não encontrado.")
    return periodo




















def _motivos_ativos_validos(motivo_ids: list[int]) -> list[dict]:
    motivos = buscar_motivos_pre_conselho_por_ids(motivo_ids)
    ids_recebidos = {int(valor) for valor in motivo_ids or [] if int(valor) > 0}
    ids_encontrados = {int(item["id"]) for item in motivos if int(item.get("ativo") or 0) == 1}
    if ids_recebidos != ids_encontrados:
        raise HTTPException(400, "Existe motivo inválido ou inativo na seleção.")
    return motivos



























@router.get("/preconselho/contexto", response_model=PreConselhoContextoOut)
def obter_contexto_preconselho_api(usuario=Depends(get_usuario_logado)):
    _exigir_acesso_preconselho(usuario)
    try:
        return obter_contexto_preconselho(usuario)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get(
    "/preconselho/minhas-turmas-disciplinas", response_model=list[PreConselhoTurmaDisciplinaOut]
)
def listar_minhas_turmas_disciplinas_preconselho_api(
    periodo_id: int = Query(...),
    usuario=Depends(get_usuario_logado),
):
    if not _usuario_eh_professor(usuario):
        raise HTTPException(403, "Acesso negado.")
    _validar_periodo(periodo_id)
    return minhas_turmas_disciplinas_preconselho(int(periodo_id), _usuario_id(usuario))


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
    _exigir_acesso_preconselho(usuario)
    try:
        return listar_estudantes_painel_preconselho(
            periodo_id=periodo_id,
            turma_id=turma_id,
            disciplina_id=disciplina_id,
            q=q,
            status=status,
            professor_id=professor_id,
            usuario=usuario,
        )
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/preconselho/texto/preview", response_model=PreConselhoTextoOut)
def gerar_texto_preview_preconselho_api(
    payload: PreConselhoTextoPreviewIn,
    usuario=Depends(get_usuario_logado),
):
    _exigir_acesso_preconselho(usuario)
    motivos = _motivos_ativos_validos(payload.motivo_ids)
    observacao_pos_preconselho = _texto_opcional(
        payload.pos_preconselho_observacao,
        "Observação do pós pré-conselho",
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
        retorno = gerar_texto_pre_conselho_individual(
            motivos=motivos,
            observacao_professor=payload.observacao_professor,
            nivel_atencao=payload.nivel_atencao,
            estudante_nome=payload.estudante_nome,
            disciplina_nome=payload.disciplina_nome,
            pos_preconselho_recuperado=pos_preconselho_recuperado,
            pos_preconselho_motivos=pos_preconselho_motivos,
            pos_preconselho_observacao=observacao_pos_preconselho,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return retorno


@router.post("/preconselho/registros", response_model=PreConselhoRegistroOut)
def salvar_registro_preconselho_api(
    payload: PreConselhoRegistroSaveIn,
    usuario=Depends(get_usuario_logado),
):
    _exigir_acesso_preconselho(usuario)
    try:
        return salvar_registro_preconselho(payload, usuario)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(500, str(exc)) from exc


@router.delete("/preconselho/registros/{registro_id}")
def excluir_registro_preconselho_api(registro_id: int, usuario=Depends(get_usuario_logado)):
    _exigir_acesso_preconselho(usuario)
    try:
        return excluir_registro_preconselho_service(registro_id, usuario)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(500, str(exc)) from exc


@router.get("/preconselho/registros", response_model=PreConselhoRegistrosOut)
def listar_registros_preconselho_api(
    periodo_id: int = Query(...),
    turma_id: int | None = Query(default=None),
    disciplina_id: int | None = Query(default=None),
    professor_id: int | None = Query(default=None),
    usuario=Depends(get_usuario_logado),
):
    _exigir_acesso_preconselho(usuario)
    try:
        return listar_registros_preconselho_service(
            periodo_id=periodo_id,
            turma_id=turma_id,
            disciplina_id=disciplina_id,
            professor_id=professor_id,
            usuario=usuario,
        )
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/preconselho/consolidado", response_model=PreConselhoConsolidadoOut)
def gerar_consolidado_preconselho_api(
    periodo_id: int = Query(...),
    turma_id: int | None = Query(default=None),
    disciplina_id: int | None = Query(default=None),
    professor_id: int | None = Query(default=None),
    usuario=Depends(get_usuario_logado),
):
    if not _usuario_eh_gestor(usuario):
        raise HTTPException(403, "Acesso negado.")
    try:
        return gerar_consolidado_preconselho_service(
            periodo_id=periodo_id,
            turma_id=turma_id,
            disciplina_id=disciplina_id,
            professor_id=professor_id,
            usuario=usuario,
        )
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/preconselho/relatorio", response_model=PreConselhoRelatorioOut)
def gerar_relatorio_preconselho_api(
    periodo_id: int = Query(...),
    usuario=Depends(get_usuario_logado),
):
    if not _usuario_eh_gestor(usuario):
        raise HTTPException(403, "Acesso negado.")
    try:
        return gerar_relatorio_preconselho_service(periodo_id=periodo_id, usuario=usuario)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/preconselho/periodos", response_model=list[PreConselhoPeriodoOut])
def listar_periodos_preconselho_api(usuario=Depends(get_usuario_logado)):
    _exigir_acesso_preconselho(usuario)
    cargo = _normalizar_cargo(usuario)
    return [
        {**item, "editavel": periodo_editavel_para_cargo(item.get("status"), cargo)}
        for item in listar_periodos_pre_conselho()
    ]


@router.post("/preconselho/periodos", response_model=PreConselhoPeriodoOut)
def criar_periodo_preconselho_api(
    payload: PreConselhoPeriodoCreateIn, usuario=Depends(get_usuario_logado)
):
    _exigir_admin(usuario)
    try:
        etapa = validar_etapa_pre_conselho(payload.etapa)
        status = validar_status_periodo_pre_conselho(
            payload.status or STATUS_PERIODO_PRE_CONSELHO_ABERTO
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    try:
        periodo_id = criar_periodo_pre_conselho(
            nome=payload.nome,
            ano_letivo=int(payload.ano_letivo),
            etapa=etapa,
            data_inicio=_validar_data_iso(payload.data_inicio, "Data inicial"),
            data_fim=_validar_data_iso(payload.data_fim, "Data final"),
            status=status,
        )
    except IntegrityError as exc:
        raise HTTPException(
            400, "Já existe um período cadastrado para este ano letivo e etapa."
        ) from exc
    periodo = buscar_periodo_pre_conselho_por_id(periodo_id)
    return {**periodo, "editavel": True}


@router.put("/preconselho/periodos/{periodo_id}", response_model=PreConselhoPeriodoOut)
def atualizar_periodo_preconselho_api(
    periodo_id: int,
    payload: PreConselhoPeriodoUpdateIn,
    usuario=Depends(get_usuario_logado),
):
    _exigir_admin(usuario)
    try:
        etapa = validar_etapa_pre_conselho(payload.etapa)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    try:
        if not atualizar_periodo_pre_conselho_dados(
            periodo_id,
            nome=payload.nome,
            ano_letivo=int(payload.ano_letivo),
            etapa=etapa,
            data_inicio=_validar_data_iso(payload.data_inicio, "Data inicial"),
            data_fim=_validar_data_iso(payload.data_fim, "Data final"),
        ):
            raise HTTPException(404, "Período não encontrado.")
    except IntegrityError as exc:
        raise HTTPException(
            400, "Já existe um período cadastrado para este ano letivo e etapa."
        ) from exc
    periodo = buscar_periodo_pre_conselho_por_id(periodo_id)
    return {**periodo, "editavel": True}


@router.put("/preconselho/periodos/{periodo_id}/status", response_model=PreConselhoPeriodoOut)
def atualizar_status_periodo_preconselho_api(
    periodo_id: int,
    payload: PreConselhoPeriodoStatusIn,
    usuario=Depends(get_usuario_logado),
):
    _exigir_admin(usuario)
    try:
        status = validar_status_periodo_pre_conselho(payload.status)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not atualizar_status_periodo_pre_conselho(periodo_id, status):
        raise HTTPException(404, "Período não encontrado.")
    periodo = buscar_periodo_pre_conselho_por_id(periodo_id)
    return {**periodo, "editavel": True}


@router.get("/preconselho/motivos", response_model=list[PreConselhoMotivoOut])
def listar_motivos_preconselho_api(
    incluir_inativos: bool = Query(default=False),
    usuario=Depends(get_usuario_logado),
):
    _exigir_acesso_preconselho(usuario)
    if incluir_inativos and not _usuario_eh_admin(usuario):
        raise HTTPException(403, "Acesso negado.")
    return listar_motivos_pre_conselho(incluir_inativos=incluir_inativos)


@router.post("/preconselho/motivos", response_model=PreConselhoMotivoOut)
def criar_motivo_preconselho_api(
    payload: PreConselhoMotivoCreateIn, usuario=Depends(get_usuario_logado)
):
    _exigir_admin(usuario)
    try:
        categoria = validar_categoria_motivo_pre_conselho(payload.categoria)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    try:
        motivo_id = criar_motivo_pre_conselho(
            categoria=categoria,
            codigo=_texto_obrigatorio(payload.codigo, "Código", max_len=120)
            .lower()
            .replace(" ", "_"),
            descricao=_texto_obrigatorio(payload.descricao, "Descrição", max_len=255),
            ordem=int(payload.ordem or 0),
        )
    except IntegrityError as exc:
        raise HTTPException(400, "Já existe um motivo cadastrado com este código.") from exc
    motivo = buscar_motivo_pre_conselho_por_id(motivo_id)
    return motivo


@router.put("/preconselho/motivos/{motivo_id}", response_model=PreConselhoMotivoOut)
def atualizar_motivo_preconselho_api(
    motivo_id: int,
    payload: PreConselhoMotivoUpdateIn,
    usuario=Depends(get_usuario_logado),
):
    _exigir_admin(usuario)
    try:
        categoria = validar_categoria_motivo_pre_conselho(payload.categoria)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not atualizar_motivo_pre_conselho_dados(
        motivo_id,
        categoria=categoria,
        descricao=_texto_obrigatorio(payload.descricao, "Descrição", max_len=255),
        ordem=int(payload.ordem or 0),
    ):
        raise HTTPException(404, "Motivo não encontrado.")
    motivo = buscar_motivo_pre_conselho_por_id(motivo_id)
    return motivo


@router.put("/preconselho/motivos/{motivo_id}/status", response_model=PreConselhoMotivoOut)
def atualizar_status_motivo_preconselho_api(
    motivo_id: int,
    payload: PreConselhoMotivoStatusIn,
    usuario=Depends(get_usuario_logado),
):
    _exigir_admin(usuario)
    if not atualizar_status_motivo_pre_conselho(motivo_id, payload.ativo):
        raise HTTPException(404, "Motivo não encontrado.")
    motivo = buscar_motivo_pre_conselho_por_id(motivo_id)
    return motivo


@router.get("/preconselho/niveis-atencao")
def listar_niveis_atencao_preconselho_api(usuario=Depends(get_usuario_logado)):
    _exigir_acesso_preconselho(usuario)
    return listar_niveis_atencao_pre_conselho()
