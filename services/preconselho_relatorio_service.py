from collections import Counter

from db.catalogos import listar_turmas_ativas
from db.docencia import (
    listar_atribuicoes_docentes,
    listar_turmas_disciplinas_admin,
)
from db.usuarios import (
    listar_cargas_professores_por_usuario_ids,
    listar_professores_agendamento,
)
from repositories.preconselho_repository import listar_registros_pre_conselho
from services.preconselho_service import listar_niveis_atencao_pre_conselho
from services.preconselho_validacao_service import (
    enriquecer_editavel_preconselho,
    validar_periodo_preconselho,
)


def _lista_texto_unica(valores) -> list[str]:
    itens = []
    for valor in valores or []:
        texto = str(valor or "").strip()
        if texto and texto not in itens:
            itens.append(texto)
    return itens


def _formatar_lista_natural(valores) -> str:
    itens = _lista_texto_unica(valores)
    if not itens:
        return ""
    if len(itens) == 1:
        return itens[0]
    if len(itens) == 2:
        return f"{itens[0]} e {itens[1]}"
    return f"{', '.join(itens[:-1])} e {itens[-1]}"


def _montar_item_relatorio(*, nome: str = "", total_registros: int = 0, extra: str = "", item_id: int | None = None) -> dict:
    return {
        "id": int(item_id) if item_id is not None else None,
        "nome": str(nome or "").strip(),
        "total_registros": int(total_registros or 0),
        "extra": str(extra or "").strip(),
    }


def _mapa_corpo_docente_por_turmas(turmas: dict[int, str]) -> dict[int, dict]:
    professores_por_turma = {int(turma_id): {"nomes": [], "corpo_docente": []} for turma_id in turmas}

    def registrar_docente(turma_id: int, professor_nome: str, disciplinas=None):
        nome = str(professor_nome or "").strip()
        disciplinas_lista = _lista_texto_unica(disciplinas or [])
        if not nome:
            return
        bloco = professores_por_turma.setdefault(turma_id, {"nomes": [], "corpo_docente": []})
        if nome not in bloco["nomes"]:
            bloco["nomes"].append(nome)
            bloco["corpo_docente"].append({"professor_nome": nome, "disciplinas": list(disciplinas_lista)})
            return
        for item in bloco["corpo_docente"]:
            if item.get("professor_nome") == nome:
                item["disciplinas"] = _lista_texto_unica(list(item.get("disciplinas") or []) + list(disciplinas_lista))
                break

    for turma_id in sorted(turmas):
        for item in listar_atribuicoes_docentes(turma_id=turma_id, incluir_inativos=False):
            registrar_docente(turma_id, item.get("professor_nome"), [item.get("disciplina_nome")])
        for item in listar_turmas_disciplinas_admin(turma_id=turma_id, incluir_inativos=False):
            registrar_docente(turma_id, item.get("professor_nome"), [item.get("disciplina_nome")])

    professores = listar_professores_agendamento()
    cargas = listar_cargas_professores_por_usuario_ids([int(item["id"]) for item in professores if int(item.get("id") or 0) > 0])
    for turma_id, turma_nome in turmas.items():
        turma_nome_casefold = str(turma_nome or "").strip().casefold()
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
                registrar_docente(turma_id, professor.get("nome"), carga.get("disciplinas") or [])
    return professores_por_turma


def _agrupar_estudantes_relatorio(registros: list[dict]) -> list[dict]:
    agrupados = {}
    for registro in registros or []:
        estudante_id = int(registro.get("estudante_id") or 0)
        if estudante_id <= 0:
            continue
        item = agrupados.setdefault(estudante_id, {"id": estudante_id, "nome": str(registro.get("estudante_nome") or "").strip(), "turma_id": int(registro.get("turma_id") or 0), "turma_nome": str(registro.get("turma_nome") or "").strip(), "total_registros": 0, "disciplinas": [], "professores": [], "niveis": []})
        item["total_registros"] += 1
        item["disciplinas"] = _lista_texto_unica(list(item["disciplinas"]) + [registro.get("disciplina_nome")])
        item["professores"] = _lista_texto_unica(list(item["professores"]) + [registro.get("professor_nome")])
        item["niveis"] = _lista_texto_unica(list(item["niveis"]) + [registro.get("nivel_atencao")])
    return list(agrupados.values())


def _agrupar_professores_relatorio(registros: list[dict]) -> list[dict]:
    agrupados = {}
    for registro in registros or []:
        professor_id = int(registro.get("professor_id") or 0)
        if professor_id <= 0:
            continue
        item = agrupados.setdefault(professor_id, {"id": professor_id, "nome": str(registro.get("professor_nome") or "").strip(), "total_registros": 0, "turmas": [], "disciplinas": []})
        item["total_registros"] += 1
        item["turmas"] = _lista_texto_unica(list(item["turmas"]) + [registro.get("turma_nome")])
        item["disciplinas"] = _lista_texto_unica(list(item["disciplinas"]) + [registro.get("disciplina_nome")])
    return list(agrupados.values())


def _coletar_motivos_frequentes(registros: list[dict], *, limite: int = 5) -> list[dict]:
    contador = Counter()
    for registro in registros or []:
        for motivo in registro.get("motivos") or []:
            descricao = str(motivo.get("descricao") or "").strip()
            if descricao:
                contador[descricao] += 1
    return [_montar_item_relatorio(nome=descricao, total_registros=total) for descricao, total in contador.most_common(limite)]


def _rotulo_nivel_atencao_relatorio(nivel: str, niveis_map: dict[str, str]) -> str:
    nivel_limpo = str(nivel or "").strip()
    if not nivel_limpo:
        return ""
    return niveis_map.get(nivel_limpo, nivel_limpo.capitalize())


def gerar_relatorio_preconselho_service(periodo_id: int, usuario: dict) -> dict:
    periodo = validar_periodo_preconselho(periodo_id)
    registros = enriquecer_editavel_preconselho(usuario, listar_registros_pre_conselho(periodo_id=int(periodo["id"])))
    niveis_map = {str(item.get("id") or "").strip(): str(item.get("nome") or "").strip() for item in listar_niveis_atencao_pre_conselho() if str(item.get("id") or "").strip()}
    turmas_base = {int(item["id"]): {"id": int(item["id"]), "nome": str(item.get("nome") or "").strip(), "turno": str(item.get("turno") or "").strip(), "quantidade_estudantes": int(item.get("quantidade_estudantes") or 0)} for item in listar_turmas_ativas() if int(item.get("id") or 0) > 0}
    for registro in registros:
        turma_id = int(registro.get("turma_id") or 0)
        if turma_id > 0 and turma_id not in turmas_base:
            turmas_base[turma_id] = {"id": turma_id, "nome": str(registro.get("turma_nome") or "").strip(), "turno": "", "quantidade_estudantes": 0}

    professores_relacionados_por_turma = _mapa_corpo_docente_por_turmas({turma_id: str(item.get("nome") or "").strip() for turma_id, item in turmas_base.items() if str(item.get("nome") or "").strip()})
    estudantes_agrupados = sorted(_agrupar_estudantes_relatorio(registros), key=lambda item: (-int(item.get("total_registros") or 0), str(item.get("nome") or "").casefold()))
    professores_agrupados = sorted(_agrupar_professores_relatorio(registros), key=lambda item: (-int(item.get("total_registros") or 0), str(item.get("nome") or "").casefold()))
    motivos_frequentes = _coletar_motivos_frequentes(registros, limite=5)
    contagem_turmas = Counter(int(item.get("turma_id") or 0) for item in registros if int(item.get("turma_id") or 0) > 0)
    estudantes_por_turma = Counter(int(item.get("turma_id") or 0) for item in estudantes_agrupados if int(item.get("turma_id") or 0) > 0)

    turma_destaque = _montar_item_relatorio()
    if contagem_turmas:
        turma_id_destaque, total_registros_turma = sorted(contagem_turmas.items(), key=lambda item: (-int(item[1]), str((turmas_base.get(int(item[0])) or {}).get("nome") or "").casefold()))[0]
        turma_info = turmas_base.get(int(turma_id_destaque), {})
        turma_destaque = _montar_item_relatorio(item_id=int(turma_id_destaque), nome=str(turma_info.get("nome") or "").strip(), total_registros=int(total_registros_turma or 0), extra=f"{int(estudantes_por_turma.get(int(turma_id_destaque), 0))} estudante(s) sinalizado(s)")

    professor_destaque = _montar_item_relatorio()
    if professores_agrupados:
        professor_topo = professores_agrupados[0]
        professor_destaque = _montar_item_relatorio(item_id=int(professor_topo.get("id") or 0), nome=str(professor_topo.get("nome") or "").strip(), total_registros=int(professor_topo.get("total_registros") or 0), extra=f"{len(professor_topo.get('turmas') or [])} turma(s) com registros")

    estudantes_destaque = []
    for item in estudantes_agrupados[:5]:
        niveis = _formatar_lista_natural([_rotulo_nivel_atencao_relatorio(nivel, niveis_map) for nivel in item.get("niveis") or [] if str(nivel or "").strip()])
        partes_extra = [str(item.get("turma_nome") or "").strip(), _formatar_lista_natural(item.get("disciplinas") or []), f"Atencao {niveis}" if niveis else ""]
        estudantes_destaque.append(_montar_item_relatorio(item_id=int(item.get("id") or 0), nome=str(item.get("nome") or "").strip(), total_registros=int(item.get("total_registros") or 0), extra=" • ".join(parte for parte in partes_extra if parte)))

    pontos_criticos = []
    if turma_destaque.get("nome"):
        pontos_criticos.append(f"Turma com maior volume de registros: {turma_destaque['nome']} ({turma_destaque['total_registros']}).")
    if professor_destaque.get("nome"):
        pontos_criticos.append(f"Professor com mais registros: {professor_destaque['nome']} ({professor_destaque['total_registros']}).")
    if motivos_frequentes:
        pontos_criticos.append("Motivos mais frequentes: " + ", ".join(f"{item['nome']} ({item['total_registros']})" for item in motivos_frequentes[:3]) + ".")
    contador_niveis = Counter(_rotulo_nivel_atencao_relatorio(item.get("nivel_atencao"), niveis_map) for item in registros if _rotulo_nivel_atencao_relatorio(item.get("nivel_atencao"), niveis_map))
    if contador_niveis:
        pontos_criticos.append("Niveis de atencao mais recorrentes: " + ", ".join(f"{nivel} ({total})" for nivel, total in contador_niveis.most_common(3)) + ".")
    total_nao_recuperados = sum(1 for item in registros if item.get("pos_preconselho_recuperado") is False)
    if total_nao_recuperados > 0:
        pontos_criticos.append(f"{total_nao_recuperados} registro(s) indicam manutencao do baixo rendimento apos a recuperacao paralela.")
    if not pontos_criticos:
        pontos_criticos.append("Nenhum registro lancado no periodo selecionado.")

    turmas_relatorio = []
    turmas_ordenadas = sorted(turmas_base.values(), key=lambda item: (-int(contagem_turmas.get(int(item.get('id') or 0), 0)), str(item.get("nome") or "").casefold()))
    for turma in turmas_ordenadas:
        turma_id = int(turma.get("id") or 0)
        registros_turma = [item for item in registros if int(item.get("turma_id") or 0) == turma_id]
        estudantes_turma = sorted(_agrupar_estudantes_relatorio(registros_turma), key=lambda item: (-int(item.get("total_registros") or 0), str(item.get("nome") or "").casefold()))
        professores_turma = sorted(_agrupar_professores_relatorio(registros_turma), key=lambda item: (-int(item.get("total_registros") or 0), str(item.get("nome") or "").casefold()))
        motivos_turma = _coletar_motivos_frequentes(registros_turma, limite=5)
        professor_destaque_turma = _montar_item_relatorio()
        if professores_turma:
            topo_turma = professores_turma[0]
            professor_destaque_turma = _montar_item_relatorio(item_id=int(topo_turma.get("id") or 0), nome=str(topo_turma.get("nome") or "").strip(), total_registros=int(topo_turma.get("total_registros") or 0), extra=_formatar_lista_natural(topo_turma.get("disciplinas") or []))
        estudantes_destaque_turma = []
        for item in estudantes_turma[:5]:
            niveis = _formatar_lista_natural([_rotulo_nivel_atencao_relatorio(nivel, niveis_map) for nivel in item.get("niveis") or [] if str(nivel or "").strip()])
            partes_extra = [_formatar_lista_natural(item.get("disciplinas") or []), f"Atencao {niveis}" if niveis else ""]
            estudantes_destaque_turma.append(_montar_item_relatorio(item_id=int(item.get("id") or 0), nome=str(item.get("nome") or "").strip(), total_registros=int(item.get("total_registros") or 0), extra=" • ".join(parte for parte in partes_extra if parte)))
        contagem_professores_turma = {str(item.get("nome") or "").strip(): int(item.get("total_registros") or 0) for item in professores_turma}
        professores_relacionados = []
        nomes_professores_relacionados = set()
        for item in sorted((professores_relacionados_por_turma.get(turma_id) or {}).get("corpo_docente", []), key=lambda entry: (-int(contagem_professores_turma.get(str(entry.get("professor_nome") or "").strip(), 0)), str(entry.get("professor_nome") or "").casefold())):
            nome_professor = str(item.get("professor_nome") or "").strip()
            if not nome_professor:
                continue
            nomes_professores_relacionados.add(nome_professor)
            professores_relacionados.append(_montar_item_relatorio(nome=nome_professor, total_registros=int(contagem_professores_turma.get(nome_professor, 0)), extra=_formatar_lista_natural(item.get("disciplinas") or [])))
        for item in professores_turma:
            nome_professor = str(item.get("nome") or "").strip()
            if nome_professor and nome_professor not in nomes_professores_relacionados:
                professores_relacionados.append(_montar_item_relatorio(item_id=int(item.get("id") or 0), nome=nome_professor, total_registros=int(item.get("total_registros") or 0), extra=_formatar_lista_natural(item.get("disciplinas") or [])))
        pontos_atencao = []
        if motivos_turma:
            pontos_atencao.append("Motivos mais frequentes: " + ", ".join(f"{item['nome']} ({item['total_registros']})" for item in motivos_turma[:3]) + ".")
        estudantes_multiplos = [item for item in estudantes_turma if int(item.get("total_registros") or 0) > 1]
        if estudantes_multiplos:
            pontos_atencao.append("Estudantes com mais de um registro: " + ", ".join(f"{item['nome']} ({item['total_registros']})" for item in estudantes_multiplos[:3]) + ".")
        contador_niveis_turma = Counter(_rotulo_nivel_atencao_relatorio(item.get("nivel_atencao"), niveis_map) for item in registros_turma if _rotulo_nivel_atencao_relatorio(item.get("nivel_atencao"), niveis_map))
        if contador_niveis_turma:
            pontos_atencao.append("Niveis de atencao em destaque: " + ", ".join(f"{nivel} ({total})" for nivel, total in contador_niveis_turma.most_common(3)) + ".")
        total_nao_recuperados_turma = sum(1 for item in registros_turma if item.get("pos_preconselho_recuperado") is False)
        if total_nao_recuperados_turma > 0:
            pontos_atencao.append(f"{total_nao_recuperados_turma} registro(s) mantiveram indicacao de baixo rendimento apos recuperacao paralela.")
        if not pontos_atencao:
            pontos_atencao.append("Nenhum registro lancado para esta turma no periodo selecionado." if not registros_turma else "Sem concentracao critica adicional alem dos registros ja lancados.")
        turmas_relatorio.append({"turma_id": turma_id, "turma_nome": str(turma.get("nome") or "").strip(), "turno": str(turma.get("turno") or "").strip(), "quantidade_estudantes": int(turma.get("quantidade_estudantes") or 0), "total_registros": len(registros_turma), "total_estudantes_sinalizados": len(estudantes_turma), "professor_destaque": professor_destaque_turma, "estudantes_destaque": estudantes_destaque_turma, "professores_relacionados": professores_relacionados, "motivos_frequentes": motivos_turma, "pontos_atencao": pontos_atencao})
    return {"periodo_id": int(periodo["id"]), "periodo_nome": str(periodo.get("nome") or ""), "total_registros": len(registros), "total_estudantes_sinalizados": len(estudantes_agrupados), "total_turmas_com_registros": len(contagem_turmas), "total_professores_com_registros": len(professores_agrupados), "turma_destaque": turma_destaque, "professor_destaque": professor_destaque, "motivos_frequentes": motivos_frequentes, "pontos_criticos": pontos_criticos, "estudantes_destaque": estudantes_destaque, "turmas": turmas_relatorio}
