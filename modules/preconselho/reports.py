"""Consolidated and report flows for pre-conselho."""

from collections import Counter

from fastapi import HTTPException

from . import repository
from .report_helpers import (
    attention_level_label as default_attention_level_label,
    build_report_item as default_build_report_item,
    collect_frequent_reasons as default_collect_frequent_reasons,
    format_natural_list as default_format_natural_list,
    group_students as default_group_students,
    group_teachers as default_group_teachers,
    map_teaching_staff_by_classrooms as default_map_teaching_staff_by_classrooms,
)
from .service import (
    enrich_editable_records,
    has_manager_access,
    resolve_teacher,
    validate_classroom,
    validate_discipline,
    validate_period,
)
from services.preconselho_service import (
    gerar_texto_consolidado_pre_conselho,
    listar_niveis_atencao_pre_conselho,
)


def _lista_natural(valores) -> str:
    itens = []
    for valor in valores or []:
        texto = str(valor or "").strip()
        if texto and texto.casefold() not in {item.casefold() for item in itens}:
            itens.append(texto)
    if len(itens) <= 1:
        return itens[0] if itens else ""
    return ", ".join(itens[:-1]) + " e " + itens[-1]


def _texto_estudantes_necessidades_especiais(registros: list[dict]) -> str:
    estudantes = {}
    for registro in registros or []:
        estudante_id = int(registro.get("estudante_id") or 0)
        if estudante_id <= 0:
            continue
        item = estudantes.setdefault(estudante_id, {
            "nome": str(registro.get("estudante_nome") or "").strip(),
            "sexo": str(registro.get("sexo") or "").strip().upper(),
            "condicoes": [], "necessidades": [], "recursos": [],
        })
        condicao = str(
            registro.get("classificacao") or registro.get("condicao_necessidade") or ""
        ).strip()
        if condicao:
            item["condicoes"].append(condicao)
        apoio = str(registro.get("apoio_nome") or "").strip()
        if apoio and registro.get("apoio_tipo") == "necessidade_pedagogica":
            item["necessidades"].append(apoio)
        elif apoio and registro.get("apoio_tipo") == "recurso_acessibilidade":
            item["recursos"].append(apoio)

    paragrafos = []
    for item in estudantes.values():
        artigo = "da estudante" if item["sexo"] == "F" else "do estudante"
        condicoes = _lista_natural(item["condicoes"]) or "necessidade específica registrada"
        apoios = []
        necessidades = _lista_natural(item["necessidades"])
        recursos = _lista_natural(item["recursos"])
        if necessidades:
            apoios.append(f"necessidades pedagógicas: {necessidades}")
        if recursos:
            apoios.append(f"recursos de acessibilidade: {recursos}")
        trecho_apoios = (
            " Para seu atendimento individualizado, estão registrados " + "; ".join(apoios) + "."
            if apoios else
            " Recomenda-se assegurar acompanhamento pedagógico individualizado conforme suas necessidades."
        )
        paragrafos.append(
            f"Registra-se a presença {artigo} {item['nome'].upper()}, com {condicoes}."
            f"{trecho_apoios} A convivência em sala deve ocorrer de forma respeitosa, "
            "contribuindo para um ambiente inclusivo. Diante desse contexto, recomenda-se "
            "intensificar o acompanhamento pedagógico, com estratégias que estimulem a "
            "participação, a assiduidade e o engajamento no processo de aprendizagem."
        )
    return "\n\n".join(paragrafos)


def build_preconselho_consolidated(
    *,
    periodo_id: int,
    turma_id: int | None,
    disciplina_id: int | None,
    professor_id: int | None,
    usuario: dict,
    versao: str = "preconselho",
    enrich_teachers_in_records=None,
) -> dict:
    if not has_manager_access(usuario):
        raise HTTPException(403, "Acesso negado.")
    periodo = validate_period(periodo_id)

    turma = validate_classroom(turma_id) if turma_id is not None else None
    disciplina = validate_discipline(disciplina_id) if disciplina_id is not None else None
    professor = None
    if professor_id is not None:
        professor = resolve_teacher(usuario, professor_id, permitir_gestor=True)

    versao_normalizada = str(versao or "preconselho").strip().lower()
    if versao_normalizada not in {"preconselho", "conselho"}:
        raise HTTPException(400, "Versão de consolidado inválida.")

    itens_originais = repository.list_records(
        periodo_id=int(periodo["id"]),
        turma_id=int(turma["id"]) if turma else None,
        disciplina_id=int(disciplina["id"]) if disciplina else None,
        professor_usuario_id=int(professor["id"]) if professor else None,
    )
    itens_originais = enrich_editable_records(usuario, itens_originais)
    enrich_teachers_in_records = enrich_teachers_in_records or repository_enrich_teachers_in_records
    itens_originais = enrich_teachers_in_records(itens_originais)
    total_recuperados = sum(item.get("pos_preconselho_recuperado") is True for item in itens_originais)
    total_mantidos = sum(item.get("pos_preconselho_recuperado") is False for item in itens_originais)
    total_pendentes = sum(item.get("pos_preconselho_recuperado") is None for item in itens_originais)
    itens = (
        [item for item in itens_originais if item.get("pos_preconselho_recuperado") is False]
        if versao_normalizada == "conselho"
        else [
            {
                **item,
                "pos_preconselho_recuperado": None,
                "pos_preconselho_motivo_ids": [],
                "pos_preconselho_motivos": [],
                "pos_preconselho_observacao": "",
            }
            for item in itens_originais
        ]
    )
    consolidado = gerar_texto_consolidado_pre_conselho(
        periodo_nome=str(periodo["nome"]),
        turma_nome=str(turma["nome"]) if turma else "Todas as turmas",
        disciplina_nome=str(disciplina["nome"]) if disciplina else "Todas as disciplinas",
        registros=itens,
        professor_nome=str(professor["nome"]) if professor else "",
        versao=versao_normalizada,
    )
    texto_necessidades = _texto_estudantes_necessidades_especiais(
        repository.list_students_with_special_needs(
            turma_id=int(turma["id"]) if turma else None
        )
    )
    texto_consolidado = str(consolidado["texto"] or "").strip()
    if texto_necessidades:
        texto_consolidado = "\n\n".join(
            trecho for trecho in (texto_consolidado, texto_necessidades) if trecho
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
        "versao": versao_normalizada,
        "total_registros": int(consolidado["total_registros"]),
        "total_estudantes": int(consolidado["total_estudantes"]),
        "total_recuperados": total_recuperados,
        "total_mantidos": total_mantidos,
        "total_pendentes": total_pendentes,
        "motivos_frequentes": consolidado["motivos_frequentes"],
        "texto": texto_consolidado,
        "texto_estudantes_necessidades_especiais": texto_necessidades,
        "itens_agrupados": consolidado["itens_agrupados"],
        "itens": itens,
    }


def build_preconselho_report(
    *,
    periodo_id: int,
    usuario: dict,
    map_teaching_staff_by_classrooms=None,
    group_students=None,
    group_teachers=None,
    collect_frequent_reasons=None,
    build_report_item=None,
    format_natural_list=None,
    attention_level_label=None,
) -> dict:
    if not has_manager_access(usuario):
        raise HTTPException(403, "Acesso negado.")
    periodo = validate_period(periodo_id)

    map_teaching_staff_by_classrooms = (
        map_teaching_staff_by_classrooms or default_map_teaching_staff_by_classrooms
    )
    group_students = group_students or default_group_students
    group_teachers = group_teachers or default_group_teachers
    collect_frequent_reasons = collect_frequent_reasons or default_collect_frequent_reasons
    build_report_item = build_report_item or default_build_report_item
    format_natural_list = format_natural_list or default_format_natural_list
    attention_level_label = attention_level_label or default_attention_level_label

    registros = enrich_editable_records(
        usuario,
        repository.list_records(periodo_id=int(periodo["id"])),
    )

    niveis_map = {
        str(item.get("id") or "").strip(): str(item.get("nome") or "").strip()
        for item in listar_niveis_atencao_pre_conselho()
        if str(item.get("id") or "").strip()
    }

    turmas_base = {
        int(item["id"]): {
            "id": int(item["id"]),
            "nome": str(item.get("nome") or "").strip(),
            "turno": str(item.get("turno") or "").strip(),
            "quantidade_estudantes": int(item.get("quantidade_estudantes") or 0),
        }
        for item in repository.list_active_classrooms()
        if int(item.get("id") or 0) > 0
    }
    for registro in registros:
        turma_id = int(registro.get("turma_id") or 0)
        if turma_id <= 0:
            continue
        if turma_id not in turmas_base:
            turmas_base[turma_id] = {
                "id": turma_id,
                "nome": str(registro.get("turma_nome") or "").strip(),
                "turno": "",
                "quantidade_estudantes": 0,
            }
            continue
        if not turmas_base[turma_id].get("nome"):
            turmas_base[turma_id]["nome"] = str(registro.get("turma_nome") or "").strip()

    teaching_staff_by_classroom = map_teaching_staff_by_classrooms(
        {
            turma_id: str(item.get("nome") or "").strip()
            for turma_id, item in turmas_base.items()
            if str(item.get("nome") or "").strip()
        }
    )

    estudantes_agrupados = sorted(
        group_students(registros),
        key=lambda item: (-int(item.get("total_registros") or 0), str(item.get("nome") or "").casefold()),
    )
    professores_agrupados = sorted(
        group_teachers(registros),
        key=lambda item: (-int(item.get("total_registros") or 0), str(item.get("nome") or "").casefold()),
    )
    motivos_frequentes = collect_frequent_reasons(registros, limite=5)

    contagem_turmas = Counter(
        int(item.get("turma_id") or 0) for item in registros if int(item.get("turma_id") or 0) > 0
    )
    estudantes_por_turma = Counter(
        int(item.get("turma_id") or 0)
        for item in estudantes_agrupados
        if int(item.get("turma_id") or 0) > 0
    )

    turma_destaque = build_report_item()
    if contagem_turmas:
        turma_id_destaque, total_registros_turma = sorted(
            contagem_turmas.items(),
            key=lambda item: (
                -int(item[1]),
                str((turmas_base.get(int(item[0])) or {}).get("nome") or "").casefold(),
            ),
        )[0]
        turma_info = turmas_base.get(int(turma_id_destaque), {})
        turma_destaque = build_report_item(
            item_id=int(turma_id_destaque),
            nome=str(turma_info.get("nome") or "").strip(),
            total_registros=int(total_registros_turma or 0),
            extra=f"{int(estudantes_por_turma.get(int(turma_id_destaque), 0))} estudante(s) sinalizado(s)",
        )

    professor_destaque = build_report_item()
    if professores_agrupados:
        professor_topo = professores_agrupados[0]
        professor_destaque = build_report_item(
            item_id=int(professor_topo.get("id") or 0),
            nome=str(professor_topo.get("nome") or "").strip(),
            total_registros=int(professor_topo.get("total_registros") or 0),
            extra=f"{len(professor_topo.get('turmas') or [])} turma(s) com registros",
        )

    estudantes_destaque = []
    for item in estudantes_agrupados[:5]:
        niveis = format_natural_list(
            [
                attention_level_label(nivel, niveis_map)
                for nivel in item.get("niveis") or []
                if str(nivel or "").strip()
            ]
        )
        partes_extra = [
            str(item.get("turma_nome") or "").strip(),
            format_natural_list(item.get("disciplinas") or []),
            f"Atenção {niveis}" if niveis else "",
        ]
        estudantes_destaque.append(
            build_report_item(
                item_id=int(item.get("id") or 0),
                nome=str(item.get("nome") or "").strip(),
                total_registros=int(item.get("total_registros") or 0),
                extra=" • ".join(parte for parte in partes_extra if parte),
            )
        )

    contador_niveis = Counter(
        attention_level_label(item.get("nivel_atencao"), niveis_map)
        for item in registros
        if attention_level_label(item.get("nivel_atencao"), niveis_map)
    )
    pontos_criticos = []
    if turma_destaque.get("nome"):
        pontos_criticos.append(
            f"Turma com maior volume de registros: {turma_destaque['nome']} ({turma_destaque['total_registros']})."
        )
    if professor_destaque.get("nome"):
        pontos_criticos.append(
            f"Professor com mais registros: {professor_destaque['nome']} ({professor_destaque['total_registros']})."
        )
    if motivos_frequentes:
        pontos_criticos.append(
            "Motivos mais frequentes: "
            + ", ".join(f"{item['nome']} ({item['total_registros']})" for item in motivos_frequentes[:3])
            + "."
        )
    if contador_niveis:
        pontos_criticos.append(
            "Níveis de atenção mais recorrentes: "
            + ", ".join(f"{nivel} ({total})" for nivel, total in contador_niveis.most_common(3))
            + "."
        )
    total_nao_recuperados = sum(
        1 for item in registros if item.get("pos_preconselho_recuperado") is False
    )
    if total_nao_recuperados > 0:
        pontos_criticos.append(
            f"{total_nao_recuperados} registro(s) indicam manutenção do baixo rendimento após a recuperação paralela."
        )
    if not pontos_criticos:
        pontos_criticos.append("Nenhum registro lançado no período selecionado.")

    turmas_relatorio = []
    turmas_ordenadas = sorted(
        turmas_base.values(),
        key=lambda item: (
            -int(contagem_turmas.get(int(item.get("id") or 0), 0)),
            str(item.get("nome") or "").casefold(),
        ),
    )

    for turma in turmas_ordenadas:
        turma_id = int(turma.get("id") or 0)
        registros_turma = [item for item in registros if int(item.get("turma_id") or 0) == turma_id]
        estudantes_turma = sorted(
            group_students(registros_turma),
            key=lambda item: (-int(item.get("total_registros") or 0), str(item.get("nome") or "").casefold()),
        )
        professores_turma = sorted(
            group_teachers(registros_turma),
            key=lambda item: (-int(item.get("total_registros") or 0), str(item.get("nome") or "").casefold()),
        )
        motivos_turma = collect_frequent_reasons(registros_turma, limite=5)
        professor_destaque_turma = build_report_item()
        if professores_turma:
            topo_turma = professores_turma[0]
            professor_destaque_turma = build_report_item(
                item_id=int(topo_turma.get("id") or 0),
                nome=str(topo_turma.get("nome") or "").strip(),
                total_registros=int(topo_turma.get("total_registros") or 0),
                extra=format_natural_list(topo_turma.get("disciplinas") or []),
            )

        estudantes_destaque_turma = []
        for item in estudantes_turma[:5]:
            niveis = format_natural_list(
                [
                    attention_level_label(nivel, niveis_map)
                    for nivel in item.get("niveis") or []
                    if str(nivel or "").strip()
                ]
            )
            partes_extra = [
                format_natural_list(item.get("disciplinas") or []),
                f"Atenção {niveis}" if niveis else "",
            ]
            estudantes_destaque_turma.append(
                build_report_item(
                    item_id=int(item.get("id") or 0),
                    nome=str(item.get("nome") or "").strip(),
                    total_registros=int(item.get("total_registros") or 0),
                    extra=" • ".join(parte for parte in partes_extra if parte),
                )
            )

        contagem_professores_turma = {
            str(item.get("nome") or "").strip(): int(item.get("total_registros") or 0)
            for item in professores_turma
        }
        professores_relacionados = []
        nomes_professores_relacionados = set()
        for item in sorted(
            (teaching_staff_by_classroom.get(turma_id) or {}).get("corpo_docente", []),
            key=lambda entry: (
                -int(contagem_professores_turma.get(str(entry.get("professor_nome") or "").strip(), 0)),
                str(entry.get("professor_nome") or "").casefold(),
            ),
        ):
            nome_professor = str(item.get("professor_nome") or "").strip()
            if not nome_professor:
                continue
            nomes_professores_relacionados.add(nome_professor)
            professores_relacionados.append(
                build_report_item(
                    nome=nome_professor,
                    total_registros=int(contagem_professores_turma.get(nome_professor, 0)),
                    extra=format_natural_list(item.get("disciplinas") or []),
                )
            )
        for item in professores_turma:
            nome_professor = str(item.get("nome") or "").strip()
            if not nome_professor or nome_professor in nomes_professores_relacionados:
                continue
            professores_relacionados.append(
                build_report_item(
                    item_id=int(item.get("id") or 0),
                    nome=nome_professor,
                    total_registros=int(item.get("total_registros") or 0),
                    extra=format_natural_list(item.get("disciplinas") or []),
                )
            )

        contador_niveis_turma = Counter(
            attention_level_label(item.get("nivel_atencao"), niveis_map)
            for item in registros_turma
            if attention_level_label(item.get("nivel_atencao"), niveis_map)
        )
        pontos_atencao = []
        if motivos_turma:
            pontos_atencao.append(
                "Motivos mais frequentes: "
                + ", ".join(f"{item['nome']} ({item['total_registros']})" for item in motivos_turma[:3])
                + "."
            )
        estudantes_multiplos = [item for item in estudantes_turma if int(item.get("total_registros") or 0) > 1]
        if estudantes_multiplos:
            pontos_atencao.append(
                "Estudantes com mais de um registro: "
                + ", ".join(f"{item['nome']} ({item['total_registros']})" for item in estudantes_multiplos[:3])
                + "."
            )
        if contador_niveis_turma:
            pontos_atencao.append(
                "Níveis de atenção em destaque: "
                + ", ".join(f"{nivel} ({total})" for nivel, total in contador_niveis_turma.most_common(3))
                + "."
            )
        total_nao_recuperados_turma = sum(
            1 for item in registros_turma if item.get("pos_preconselho_recuperado") is False
        )
        if total_nao_recuperados_turma > 0:
            pontos_atencao.append(
                f"{total_nao_recuperados_turma} registro(s) mantiveram indicação de baixo rendimento após recuperação paralela."
            )
        if not pontos_atencao:
            pontos_atencao.append(
                "Nenhum registro lançado para esta turma no período selecionado."
                if not registros_turma
                else "Sem concentração crítica adicional além dos registros já lançados."
            )

        turmas_relatorio.append(
            {
                "turma_id": turma_id,
                "turma_nome": str(turma.get("nome") or "").strip(),
                "turno": str(turma.get("turno") or "").strip(),
                "quantidade_estudantes": int(turma.get("quantidade_estudantes") or 0),
                "total_registros": len(registros_turma),
                "total_estudantes_sinalizados": len(estudantes_turma),
                "professor_destaque": professor_destaque_turma,
                "estudantes_destaque": estudantes_destaque_turma,
                "professores_relacionados": professores_relacionados,
                "motivos_frequentes": motivos_turma,
                "pontos_atencao": pontos_atencao,
            }
        )

    return {
        "periodo_id": int(periodo["id"]),
        "periodo_nome": str(periodo.get("nome") or ""),
        "total_registros": len(registros),
        "total_estudantes_sinalizados": len(estudantes_agrupados),
        "total_turmas_com_registros": len(contagem_turmas),
        "total_professores_com_registros": len(professores_agrupados),
        "turma_destaque": turma_destaque,
        "professor_destaque": professor_destaque,
        "motivos_frequentes": motivos_frequentes,
        "pontos_criticos": pontos_criticos,
        "estudantes_destaque": estudantes_destaque,
        "turmas": turmas_relatorio,
    }


def build_preconselho_rav_view(
    *,
    periodo_id: int,
    turma_id: int | None,
    usuario: dict,
) -> dict:
    if not has_manager_access(usuario):
        raise HTTPException(403, "Acesso negado.")
    periodo = validate_period(periodo_id)
    turma = validate_classroom(turma_id) if turma_id is not None else None
    itens = repository.list_rav_by_classroom(
        periodo_id=int(periodo["id"]),
        turma_id=int(turma["id"]) if turma else None,
    )
    itens = enrich_editable_records(usuario, itens)
    estudantes = {int(item.get("estudante_id") or 0) for item in itens}
    estudantes.discard(0)
    return {
        "periodo_id": int(periodo["id"]),
        "turma_id": int(turma["id"]) if turma else None,
        "total_estudantes": len(estudantes),
        "total_registros": len(itens),
        "itens": itens,
    }


def repository_enrich_teachers_in_records(records: list[dict]) -> list[dict]:
    from .report_helpers import enrich_teachers_in_records

    return enrich_teachers_in_records(records)
