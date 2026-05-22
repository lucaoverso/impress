from db.docencia import (
    listar_atribuicoes_docentes,
    listar_turmas_disciplinas_admin,
)
from db.usuarios import (
    listar_cargas_professores_por_usuario_ids,
    listar_professores_agendamento,
)
from repositories.preconselho_repository import listar_registros_pre_conselho
from services.preconselho_service import gerar_texto_consolidado_pre_conselho
from services.preconselho_validacao_service import (
    enriquecer_editavel_preconselho,
    resolver_professor_preconselho,
    validar_disciplina_preconselho,
    validar_periodo_preconselho,
    validar_turma_preconselho,
)


def _lista_texto_unica(valores) -> list[str]:
    itens = []
    for valor in valores or []:
        texto = str(valor or "").strip()
        if texto and texto not in itens:
            itens.append(texto)
    return itens


def _mapa_corpo_docente_por_turmas(turmas: dict[int, str]) -> dict[int, dict]:
    turmas_validas = {
        int(turma_id): str(turma_nome or "").strip()
        for turma_id, turma_nome in (turmas or {}).items()
        if int(turma_id) > 0 and str(turma_nome or "").strip()
    }
    if not turmas_validas:
        return {}

    professores_por_turma = {
        turma_id: {"nomes": [], "corpo_docente": []}
        for turma_id in turmas_validas
    }

    def registrar_docente(turma_id: int, professor_nome: str, disciplinas=None):
        nome = str(professor_nome or "").strip()
        disciplinas_lista = _lista_texto_unica(disciplinas or [])
        if not nome:
            return

        bloco = professores_por_turma.setdefault(
            turma_id,
            {"nomes": [], "corpo_docente": []},
        )
        if nome not in bloco["nomes"]:
            bloco["nomes"].append(nome)
            bloco["corpo_docente"].append(
                {"professor_nome": nome, "disciplinas": list(disciplinas_lista)}
            )
            return

        for item in bloco["corpo_docente"]:
            if item.get("professor_nome") != nome:
                continue
            item["disciplinas"] = _lista_texto_unica(
                list(item.get("disciplinas") or []) + list(disciplinas_lista)
            )
            break

    for turma_id in sorted(turmas_validas):
        for item in listar_atribuicoes_docentes(turma_id=turma_id, incluir_inativos=False):
            registrar_docente(turma_id, item.get("professor_nome"), [item.get("disciplina_nome")])
        for item in listar_turmas_disciplinas_admin(turma_id=turma_id, incluir_inativos=False):
            registrar_docente(turma_id, item.get("professor_nome"), [item.get("disciplina_nome")])

    professores = listar_professores_agendamento()
    cargas = listar_cargas_professores_por_usuario_ids(
        [int(item["id"]) for item in professores if int(item.get("id") or 0) > 0]
    )
    for turma_id, turma_nome in turmas_validas.items():
        turma_nome_casefold = turma_nome.casefold()
        for professor in professores:
            professor_id = int(professor.get("id") or 0)
            if professor_id <= 0:
                continue
            carga = cargas.get(professor_id, {})
            turmas_carga = {
                str(item or "").strip().casefold()
                for item in (carga.get("turmas") or [])
                if str(item or "").strip()
            }
            if turma_nome_casefold in turmas_carga:
                registrar_docente(
                    turma_id,
                    professor.get("nome"),
                    carga.get("disciplinas") or [],
                )

    return {
        turma_id: dados
        for turma_id, dados in professores_por_turma.items()
        if dados.get("nomes")
    }


def _enriquecer_professores_turma_registros(registros: list[dict]) -> list[dict]:
    turmas = {}
    for registro in registros or []:
        turma_id = int(registro.get("turma_id") or 0)
        turma_nome = str(registro.get("turma_nome") or "").strip()
        if turma_id > 0 and turma_nome:
            turmas[turma_id] = turma_nome

    mapa = _mapa_corpo_docente_por_turmas(turmas)
    return [
        {
            **item,
            "professores_turma": list(
                (mapa.get(int(item.get("turma_id") or 0), {}) or {}).get("nomes", [])
            ),
            "corpo_docente_turma": list(
                (mapa.get(int(item.get("turma_id") or 0), {}) or {}).get("corpo_docente", [])
            ),
        }
        for item in (registros or [])
    ]


def gerar_consolidado_preconselho_service(
    periodo_id: int,
    turma_id: int | None,
    disciplina_id: int | None,
    professor_id: int | None,
    usuario: dict,
) -> dict:
    periodo = validar_periodo_preconselho(periodo_id)
    turma = validar_turma_preconselho(turma_id) if turma_id is not None else None
    disciplina = validar_disciplina_preconselho(disciplina_id) if disciplina_id is not None else None
    professor = None
    if professor_id is not None:
        professor = resolver_professor_preconselho(usuario, professor_id, permitir_gestor=True)

    itens = listar_registros_pre_conselho(
        periodo_id=int(periodo["id"]),
        turma_id=int(turma["id"]) if turma else None,
        disciplina_id=int(disciplina["id"]) if disciplina else None,
        professor_usuario_id=int(professor["id"]) if professor else None,
    )
    itens = enriquecer_editavel_preconselho(usuario, itens)
    itens = _enriquecer_professores_turma_registros(itens)
    consolidado = gerar_texto_consolidado_pre_conselho(
        periodo_nome=str(periodo["nome"]),
        turma_nome=str(turma["nome"]) if turma else "Todas as turmas",
        disciplina_nome=str(disciplina["nome"]) if disciplina else "Todas as disciplinas",
        registros=itens,
        professor_nome=str(professor["nome"]) if professor else "",
    )
    return {
        "periodo_id": int(periodo["id"]),
        "periodo_nome": periodo["nome"],
        "turma_id": int(turma["id"]) if turma else None,
        "turma_nome": turma["nome"] if turma else "",
        "disciplina_id": int(disciplina["id"]) if disciplina else None,
        "disciplina_nome": disciplina["nome"] if disciplina else "",
        "professor_id": int(professor["id"]) if professor else None,
        "professor_nome": professor["nome"] if professor else "",
        "total_registros": int(consolidado["total_registros"]),
        "total_estudantes": int(consolidado["total_estudantes"]),
        "motivos_frequentes": consolidado["motivos_frequentes"],
        "texto": consolidado["texto"],
        "itens_agrupados": consolidado["itens_agrupados"],
        "itens": itens,
    }
