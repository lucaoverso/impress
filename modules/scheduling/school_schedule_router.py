from datetime import datetime
from sqlite3 import IntegrityError

from fastapi import APIRouter, Depends, HTTPException, Query

from auth import get_usuario_logado
from modules.scheduling.school_schedule_data_service import (
    atualizar_horario_escolar,
    buscar_horario_escolar_por_id,
    buscar_turma_por_id,
    criar_horario_escolar,
    excluir_horario_escolar,
    listar_anos_letivos_horario_escolar,
    listar_configuracoes_aulas,
    listar_disciplinas_ativas,
    listar_horarios_escolares,
    listar_professores_agendamento,
    listar_turmas_ativas,
    listar_turmas_disciplinas_admin,
)
from modules.scheduling.lesson_config import normalize_schedule_entries
from models import (
    HorarioEscolarRegistroIn,
    HorarioEscolarRegistroOut,
    HorarioEscolarRegistroUpdateIn,
)
from modules.scheduling.school_schedule_service import (
    agrupar_horarios_por_professor,
    agrupar_horarios_por_turma,
    anos_letivos_sugeridos,
    dia_semana_por_data,
    enriquecer_horario_escolar,
    listar_aulas_turma_horario,
    listar_grade_turma_horario_com_registros,
    listar_dias_semana_horario,
    montar_cards_disponiveis_turma,
    nome_dia_semana,
    normalizar_dia_semana,
    ordenar_horarios_escolares,
    total_aulas_turma_horario,
    validar_ano_letivo,
)
from modules.scheduling.school_schedule_validation_service import (
    translate_integrity_error,
    validate_iso_date,
    validate_school_schedule_payload,
)

from routers.common import (
    exigir_gestor,
    usuario_eh_gestor,
    usuario_eh_professor,
)

router = APIRouter()


def _serializar_contexto_professores(professores: list[dict]) -> list[dict]:
    return [
        {
            "id": int(item["id"]),
            "nome": item["nome"],
            "email": item.get("email", ""),
            "label": (
                f"{item['nome']} ({item.get('email', '')})"
                if str(item.get("email", "")).strip()
                else item["nome"]
            ),
        }
        for item in professores
        if int(item.get("id") or 0) > 0
    ]


def _exigir_visualizacao_horario(usuario) -> dict:
    if not (usuario_eh_gestor(usuario) or usuario_eh_professor(usuario)):
        raise HTTPException(403, "Acesso negado")
    return usuario


def _id_professor_logado(usuario: dict) -> int | None:
    if not usuario_eh_professor(usuario):
        return None
    try:
        professor_id = int(usuario.get("id") or 0)
    except (TypeError, ValueError):
        return None
    return professor_id if professor_id > 0 else None


def _enriquecer_itens_para_usuario(itens: list[dict], usuario: dict) -> list[dict]:
    professor_logado_id = _id_professor_logado(usuario)
    return [
        {
            **dict(item),
            "eh_do_professor_logado": bool(
                professor_logado_id and int(item.get("professor_id") or 0) == professor_logado_id
            ),
        }
        for item in (itens or [])
    ]


@router.get("/horario-escolar/contexto")
def obter_contexto_horario_escolar_api(usuario=Depends(get_usuario_logado)):
    _exigir_visualizacao_horario(usuario)
    professores = listar_professores_agendamento()
    anos = anos_letivos_sugeridos(listar_anos_letivos_horario_escolar())
    eh_gestor = usuario_eh_gestor(usuario)
    professor_logado_id = _id_professor_logado(usuario)
    configuracoes_aulas = normalize_schedule_entries(
        listar_configuracoes_aulas(incluir_inativas=False)
    )
    return {
        "anos_letivos": anos,
        "ano_letivo_atual": datetime.now().year,
        "dias_semana": listar_dias_semana_horario(),
        "grade_aulas": configuracoes_aulas,
        "turmas": listar_turmas_ativas(),
        "disciplinas": listar_disciplinas_ativas() if eh_gestor else [],
        "professores": _serializar_contexto_professores(professores) if eh_gestor else [],
        "modo_interface": "gestor" if eh_gestor else "professor",
        "permite_edicao": eh_gestor,
        "professor_logado_id": professor_logado_id,
    }


@router.get("/horario-escolar/registros")
def listar_horarios_escolares_api(
    ano_letivo: int | None = None,
    turma_id: int | None = None,
    professor_id: int | None = None,
    disciplina_id: int | None = None,
    dia_semana: str | None = None,
    usuario=Depends(get_usuario_logado),
):
    _exigir_visualizacao_horario(usuario)

    ano_letivo_valor = None
    if ano_letivo is not None:
        try:
            ano_letivo_valor = validar_ano_letivo(ano_letivo)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    dia_semana_valor = None
    if str(dia_semana or "").strip():
        try:
            dia_semana_valor = normalizar_dia_semana(dia_semana)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    configuracoes_aulas = listar_configuracoes_aulas(incluir_inativas=False)
    itens = ordenar_horarios_escolares(
        listar_horarios_escolares(
            ano_letivo=ano_letivo_valor,
            turma_id=turma_id,
            professor_id=professor_id,
            disciplina_id=disciplina_id,
            dia_semana=dia_semana_valor,
        ),
        configuracoes_aulas=configuracoes_aulas,
    )
    itens = _enriquecer_itens_para_usuario(itens, usuario)
    return {
        "total_registros": len(itens),
        "itens": itens,
        "grupos_turma": agrupar_horarios_por_turma(itens),
        "grupos_professor": agrupar_horarios_por_professor(itens),
        "modo_interface": "gestor" if usuario_eh_gestor(usuario) else "professor",
        "professor_logado_id": _id_professor_logado(usuario),
    }


@router.get("/horario-escolar/turmas/{turma_id}/matriz")
def obter_matriz_horario_turma_api(
    turma_id: int,
    ano_letivo: int = Query(...),
    usuario=Depends(get_usuario_logado),
):
    exigir_gestor(usuario)

    try:
        ano_letivo_valor = validar_ano_letivo(ano_letivo)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    turma = buscar_turma_por_id(int(turma_id))
    if not turma:
        raise HTTPException(404, "Turma não encontrada.")

    configuracoes_aulas = listar_configuracoes_aulas(incluir_inativas=False)
    registros = ordenar_horarios_escolares(
        listar_horarios_escolares(
            ano_letivo=ano_letivo_valor,
            turma_id=int(turma["id"]),
        ),
        configuracoes_aulas=configuracoes_aulas,
    )
    turma_disciplinas = listar_turmas_disciplinas_admin(
        turma_id=int(turma["id"]),
        incluir_inativos=False,
    )
    cards_disponiveis, cards_resumo, alertas = montar_cards_disponiveis_turma(
        turma_disciplinas,
        registros,
    )
    total_aulas = total_aulas_turma_horario(turma, configuracoes_aulas)
    faixas = listar_grade_turma_horario_com_registros(turma, configuracoes_aulas, registros)
    aulas = listar_aulas_turma_horario(turma, configuracoes_aulas)

    return {
        "ano_letivo": ano_letivo_valor,
        "turma": {
            **dict(turma),
            "total_aulas": total_aulas,
        },
        "dias_semana": listar_dias_semana_horario(),
        "aulas": [int(item.get("aula_numero") or 0) for item in aulas],
        "faixas": faixas,
        "registros": registros,
        "cards_disponiveis": cards_disponiveis,
        "cards_resumo": cards_resumo,
        "alertas": alertas,
    }


@router.post("/horario-escolar/registros", response_model=HorarioEscolarRegistroOut)
def criar_horario_escolar_api(
    payload: HorarioEscolarRegistroIn,
    usuario=Depends(get_usuario_logado),
):
    exigir_gestor(usuario)
    dados = validate_school_schedule_payload(payload)
    try:
        item = criar_horario_escolar(
            ano_letivo=dados["ano_letivo"],
            turma_id=dados["turma_id"],
            disciplina_id=dados["disciplina_id"],
            professor_usuario_id=dados["professor_id"],
            dia_semana=dados["dia_semana"],
            aula_numero=dados["aula_numero"],
        )
    except IntegrityError as exc:
        raise HTTPException(409, translate_integrity_error(exc)) from exc
    return enriquecer_horario_escolar(
        item,
        configuracoes_aulas=listar_configuracoes_aulas(incluir_inativas=False),
    )


@router.put("/horario-escolar/registros/{registro_id}", response_model=HorarioEscolarRegistroOut)
def atualizar_horario_escolar_api(
    registro_id: int,
    payload: HorarioEscolarRegistroUpdateIn,
    usuario=Depends(get_usuario_logado),
):
    exigir_gestor(usuario)
    if not buscar_horario_escolar_por_id(registro_id):
        raise HTTPException(404, "Registro do horário escolar não encontrado.")
    dados = validate_school_schedule_payload(payload)
    try:
        item = atualizar_horario_escolar(
            registro_id=registro_id,
            ano_letivo=dados["ano_letivo"],
            turma_id=dados["turma_id"],
            disciplina_id=dados["disciplina_id"],
            professor_usuario_id=dados["professor_id"],
            dia_semana=dados["dia_semana"],
            aula_numero=dados["aula_numero"],
        )
    except IntegrityError as exc:
        raise HTTPException(409, translate_integrity_error(exc)) from exc
    if not item:
        raise HTTPException(404, "Registro do horário escolar não encontrado.")
    return enriquecer_horario_escolar(
        item,
        configuracoes_aulas=listar_configuracoes_aulas(incluir_inativas=False),
    )


@router.delete("/horario-escolar/registros/{registro_id}")
def excluir_horario_escolar_api(
    registro_id: int,
    usuario=Depends(get_usuario_logado),
):
    exigir_gestor(usuario)
    if not excluir_horario_escolar(registro_id):
        raise HTTPException(404, "Registro do horário escolar não encontrado.")
    return {"mensagem": "Registro do horário escolar removido com sucesso."}


@router.get("/horario-escolar/professores-do-dia")
def listar_professores_do_dia_api(
    data: str = Query(...),
    ano_letivo: int | None = Query(default=None),
    usuario=Depends(get_usuario_logado),
):
    exigir_gestor(usuario)
    data_iso = validate_iso_date(data)
    try:
        dia_semana = dia_semana_por_data(data_iso)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    ano_referencia = ano_letivo if ano_letivo is not None else int(data_iso[:4])
    try:
        ano_referencia = validar_ano_letivo(ano_referencia)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    configuracoes_aulas = listar_configuracoes_aulas(incluir_inativas=False)
    itens = ordenar_horarios_escolares(
        listar_horarios_escolares(
            ano_letivo=ano_referencia,
            dia_semana=dia_semana,
        ),
        configuracoes_aulas=configuracoes_aulas,
    )
    grupos_professor = agrupar_horarios_por_professor(itens)
    return {
        "data": data_iso,
        "ano_letivo": ano_referencia,
        "dia_semana": dia_semana,
        "dia_semana_nome": nome_dia_semana(dia_semana),
        "total_registros": len(itens),
        "total_professores": len(grupos_professor),
        "professores": grupos_professor,
        "itens": itens,
    }
