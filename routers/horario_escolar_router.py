from datetime import datetime
from sqlite3 import IntegrityError

from fastapi import APIRouter, Depends, HTTPException, Query

from auth import get_usuario_logado
from db.catalogos import (
    buscar_disciplina_por_id,
    buscar_turma_por_id,
    listar_disciplinas_ativas,
    listar_turmas_ativas,
)
from db.docencia import listar_atribuicoes_docentes, listar_turmas_disciplinas_admin
from db.horario_escolar import (
    buscar_horario_escolar_por_id,
    criar_horario_escolar,
    excluir_horario_escolar,
    listar_anos_letivos_horario_escolar,
    listar_horarios_escolares,
    atualizar_horario_escolar,
)
from db.usuarios import (
    buscar_usuario_por_id,
    listar_cargas_professores_por_usuario_ids,
    listar_professores_agendamento,
)
from models import (
    HorarioEscolarRegistroIn,
    HorarioEscolarRegistroOut,
    HorarioEscolarRegistroUpdateIn,
)
from services.horario_escolar_service import (
    agrupar_horarios_por_professor,
    agrupar_horarios_por_turma,
    anos_letivos_sugeridos,
    dia_semana_por_data,
    enriquecer_horario_escolar,
    listar_dias_semana_horario,
    listar_faixas_turno_horario,
    montar_cards_disponiveis_turma,
    nome_dia_semana,
    normalizar_dia_semana,
    ordenar_horarios_escolares,
    total_aulas_por_turno,
    validar_aula_numero,
    validar_ano_letivo,
)

from .common import CARGO_PROFESSOR, exigir_gestor, normalizar_cargo_usuario

router = APIRouter()


def _usuario_professor_ativo(professor_id: int) -> dict:
    professor = buscar_usuario_por_id(int(professor_id))
    if not professor or normalizar_cargo_usuario(professor) != CARGO_PROFESSOR:
        raise HTTPException(404, "Professor nao encontrado.")
    if not bool(int(professor.get("ativo", 1) or 0)):
        raise HTTPException(400, "Professor selecionado esta inativo.")
    return professor


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


def _validar_data_iso(valor: str, campo: str = "Data") -> str:
    texto = str(valor or "").strip()
    if not texto:
        raise HTTPException(400, f"{campo} invalida. Use o formato YYYY-MM-DD.")
    try:
        return datetime.strptime(texto, "%Y-%m-%d").date().isoformat()
    except ValueError as exc:
        raise HTTPException(400, f"{campo} invalida. Use o formato YYYY-MM-DD.") from exc


def _traduzir_erro_integridade(exc: IntegrityError) -> str:
    texto = str(exc).lower()
    if "idx_horarios_escolares_professor_slot" in texto:
        return "O professor ja possui aula cadastrada nesse dia e horario."
    if "idx_horarios_escolares_turma_slot" in texto:
        return "Ja existe aula cadastrada para essa turma nesse dia e horario."
    if "professor_usuario_id" in texto and "dia_semana" in texto and "aula_numero" in texto:
        return "O professor ja possui aula cadastrada nesse dia e horario."
    if "turma_id" in texto and "dia_semana" in texto and "aula_numero" in texto:
        return "Ja existe aula cadastrada para essa turma nesse dia e horario."
    return "Conflito ao salvar o horario escolar."


def _validar_vinculo_docente(professor: dict, turma: dict, disciplina: dict):
    professor_id = int(professor["id"])
    turma_id = int(turma["id"])
    disciplina_id = int(disciplina["id"])

    atribuicoes = listar_atribuicoes_docentes(
        professor_id=professor_id,
        turma_id=turma_id,
        disciplina_id=disciplina_id,
        incluir_inativos=False,
    )
    if atribuicoes:
        return

    vinculos_turma_disciplina = listar_turmas_disciplinas_admin(
        turma_id=turma_id,
        disciplina_id=disciplina_id,
        professor_id=professor_id,
        incluir_inativos=False,
    )
    if vinculos_turma_disciplina:
        return

    carga = listar_cargas_professores_por_usuario_ids([professor_id]).get(professor_id, {})
    turma_nome = str(turma.get("nome") or "").strip().casefold()
    disciplina_nome = str(disciplina.get("nome") or "").strip().casefold()
    turmas_carga = {
        str(item or "").strip().casefold()
        for item in (carga.get("turmas") or [])
        if str(item or "").strip()
    }
    disciplinas_carga = {
        str(item or "").strip().casefold()
        for item in (carga.get("disciplinas") or [])
        if str(item or "").strip()
    }
    if turma_nome in turmas_carga and disciplina_nome in disciplinas_carga:
        return

    raise HTTPException(
        400,
        "O professor selecionado nao possui vinculo com a turma e disciplina informadas.",
    )


def _validar_payload_horario(
    payload: HorarioEscolarRegistroIn | HorarioEscolarRegistroUpdateIn,
) -> dict:
    try:
        ano_letivo = validar_ano_letivo(payload.ano_letivo)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    turma = buscar_turma_por_id(int(payload.turma_id))
    if not turma:
        raise HTTPException(404, "Turma nao encontrada.")

    disciplina = buscar_disciplina_por_id(int(payload.disciplina_id))
    if not disciplina:
        raise HTTPException(404, "Disciplina nao encontrada.")

    professor = _usuario_professor_ativo(int(payload.professor_id))

    try:
        dia_semana = normalizar_dia_semana(payload.dia_semana)
        aula_numero = validar_aula_numero(payload.aula_numero, turma.get("turno"))
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    _validar_vinculo_docente(professor, turma, disciplina)

    return {
        "ano_letivo": ano_letivo,
        "turma_id": int(turma["id"]),
        "disciplina_id": int(disciplina["id"]),
        "professor_id": int(professor["id"]),
        "dia_semana": dia_semana,
        "aula_numero": aula_numero,
    }


@router.get("/horario-escolar/contexto")
def obter_contexto_horario_escolar_api(usuario=Depends(get_usuario_logado)):
    exigir_gestor(usuario)
    professores = listar_professores_agendamento()
    anos = anos_letivos_sugeridos(listar_anos_letivos_horario_escolar())
    return {
        "anos_letivos": anos,
        "ano_letivo_atual": datetime.now().year,
        "dias_semana": listar_dias_semana_horario(),
        "turmas": listar_turmas_ativas(),
        "disciplinas": listar_disciplinas_ativas(),
        "professores": _serializar_contexto_professores(professores),
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
    exigir_gestor(usuario)

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

    itens = ordenar_horarios_escolares(
        listar_horarios_escolares(
            ano_letivo=ano_letivo_valor,
            turma_id=turma_id,
            professor_id=professor_id,
            disciplina_id=disciplina_id,
            dia_semana=dia_semana_valor,
        )
    )
    return {
        "total_registros": len(itens),
        "itens": itens,
        "grupos_turma": agrupar_horarios_por_turma(itens),
        "grupos_professor": agrupar_horarios_por_professor(itens),
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
        raise HTTPException(404, "Turma nao encontrada.")

    registros = ordenar_horarios_escolares(
        listar_horarios_escolares(
            ano_letivo=ano_letivo_valor,
            turma_id=int(turma["id"]),
        )
    )
    turma_disciplinas = listar_turmas_disciplinas_admin(
        turma_id=int(turma["id"]),
        incluir_inativos=False,
    )
    cards_disponiveis, cards_resumo, alertas = montar_cards_disponiveis_turma(
        turma_disciplinas,
        registros,
    )
    total_aulas = total_aulas_por_turno(turma.get("turno"))
    faixas = listar_faixas_turno_horario(turma.get("turno"))

    return {
        "ano_letivo": ano_letivo_valor,
        "turma": {
            **dict(turma),
            "total_aulas": total_aulas,
        },
        "dias_semana": listar_dias_semana_horario(),
        "aulas": list(range(1, total_aulas + 1)),
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
    dados = _validar_payload_horario(payload)
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
        raise HTTPException(409, _traduzir_erro_integridade(exc)) from exc
    return enriquecer_horario_escolar(item)


@router.put("/horario-escolar/registros/{registro_id}", response_model=HorarioEscolarRegistroOut)
def atualizar_horario_escolar_api(
    registro_id: int,
    payload: HorarioEscolarRegistroUpdateIn,
    usuario=Depends(get_usuario_logado),
):
    exigir_gestor(usuario)
    if not buscar_horario_escolar_por_id(registro_id):
        raise HTTPException(404, "Registro do horario escolar nao encontrado.")
    dados = _validar_payload_horario(payload)
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
        raise HTTPException(409, _traduzir_erro_integridade(exc)) from exc
    if not item:
        raise HTTPException(404, "Registro do horario escolar nao encontrado.")
    return enriquecer_horario_escolar(item)


@router.delete("/horario-escolar/registros/{registro_id}")
def excluir_horario_escolar_api(
    registro_id: int,
    usuario=Depends(get_usuario_logado),
):
    exigir_gestor(usuario)
    if not excluir_horario_escolar(registro_id):
        raise HTTPException(404, "Registro do horario escolar nao encontrado.")
    return {"mensagem": "Registro do horario escolar removido com sucesso."}


@router.get("/horario-escolar/professores-do-dia")
def listar_professores_do_dia_api(
    data: str = Query(...),
    ano_letivo: int | None = Query(default=None),
    usuario=Depends(get_usuario_logado),
):
    exigir_gestor(usuario)
    data_iso = _validar_data_iso(data)
    try:
        dia_semana = dia_semana_por_data(data_iso)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    ano_referencia = ano_letivo if ano_letivo is not None else int(data_iso[:4])
    try:
        ano_referencia = validar_ano_letivo(ano_referencia)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    itens = ordenar_horarios_escolares(
        listar_horarios_escolares(
            ano_letivo=ano_referencia,
            dia_semana=dia_semana,
        )
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
