from collections import Counter
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query

from auth import get_usuario_logado
from db.catalogos import (
    buscar_disciplina_por_id,
    buscar_turma_por_id,
    listar_disciplinas_ativas,
    listar_turmas_ativas,
)
from db.docencia import (
    listar_atribuicoes_docentes,
    listar_atribuicoes_docentes_por_usuario_ids,
    listar_turmas_disciplinas_admin,
)
from db.ocorrencias import buscar_estudante_por_id, listar_estudantes
from repositories.preconselho_repository import (
    buscar_motivos_pre_conselho_por_ids,
    buscar_periodo_pre_conselho_por_id,
    buscar_registro_pre_conselho_por_id,
    contar_registros_pre_conselho_por_professor_periodo,
    criar_ou_atualizar_registro_pre_conselho,
    excluir_registro_pre_conselho,
    listar_estudantes_pre_conselho_painel,
    listar_motivos_pre_conselho,
    listar_periodos_pre_conselho,
    listar_registros_pre_conselho,
)
from db.usuarios import (
    buscar_usuario_por_id,
    listar_cargas_professores_por_usuario_ids,
    listar_professores_agendamento,
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
from services.preconselho_service import (
    STATUS_PERIODO_PRE_CONSELHO_ABERTO,
    atualizar_motivo_preconselho_admin,
    atualizar_periodo_preconselho_admin,
    atualizar_status_motivo_preconselho_admin,
    atualizar_status_periodo_preconselho_admin,
    criar_motivo_preconselho_admin,
    criar_periodo_preconselho_admin,
    gerar_texto_consolidado_pre_conselho,
    gerar_texto_pre_conselho_individual,
    listar_motivos_pos_pre_conselho,
    listar_motivos_preconselho_visiveis,
    listar_niveis_atencao_pre_conselho,
    periodo_editavel_para_cargo,
    texto_obrigatorio_preconselho,
    validar_data_iso_preconselho,
    validar_categoria_motivo_pre_conselho,
    validar_motivos_pos_pre_conselho,
    validar_etapa_pre_conselho,
    validar_nivel_atencao_pre_conselho,
    validar_status_periodo_pre_conselho,
)
from routers.common import normalizar_cargo_usuario, usuario_tem_acesso_coordenacao


router = APIRouter()


def _normalizar_cargo(usuario: dict) -> str:
    return normalizar_cargo_usuario(usuario)


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


def _validar_turma(turma_id: int) -> dict:
    try:
        turma_id_valor = int(turma_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(400, "Turma inválida.") from exc
    turma = buscar_turma_por_id(turma_id_valor)
    if not turma:
        raise HTTPException(404, "Turma não encontrada.")
    return turma


def _validar_disciplina(disciplina_id: int) -> dict:
    try:
        disciplina_id_valor = int(disciplina_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(400, "Disciplina inválida.") from exc
    disciplina = buscar_disciplina_por_id(disciplina_id_valor)
    if not disciplina:
        raise HTTPException(404, "Disciplina não encontrada.")
    return disciplina


def _validar_estudante_na_turma(estudante_id: int, turma_id: int) -> dict:
    try:
        estudante_id_valor = int(estudante_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(400, "Estudante inválido.") from exc
    estudante = buscar_estudante_por_id(estudante_id_valor)
    if not estudante:
        raise HTTPException(404, "Estudante não encontrado.")
    if int(estudante.get("turma_id") or 0) != int(turma_id):
        raise HTTPException(400, "O estudante não pertence à turma selecionada.")
    return estudante


def _resolver_professor(
    usuario: dict, professor_id: int | None = None, *, permitir_gestor: bool = False
) -> dict:
    cargo = _normalizar_cargo(usuario)
    usuario_id = _usuario_id(usuario)

    if cargo == "PROFESSOR":
        if professor_id in (None, usuario_id):
            return {"id": usuario_id, "nome": str(usuario.get("nome") or "").strip()}
        if not (permitir_gestor and _usuario_eh_gestor(usuario)):
            raise HTTPException(403, "Acesso negado.")

    if not permitir_gestor or not _usuario_eh_gestor(usuario):
        raise HTTPException(403, "Acesso negado.")
    if professor_id is None:
        raise HTTPException(400, "Professor obrigatório.")

    professor = buscar_usuario_por_id(int(professor_id))
    if not professor or _normalizar_cargo(professor) != "PROFESSOR":
        raise HTTPException(404, "Professor não encontrado.")
    return {"id": int(professor["id"]), "nome": professor["nome"]}


def _escopo_professor_legado(usuario_id: int) -> dict:
    carga = listar_cargas_professores_por_usuario_ids([usuario_id]).get(usuario_id, {})
    nomes_turmas = {
        str(item).strip().casefold() for item in carga.get("turmas") or [] if str(item).strip()
    }
    nomes_disciplinas = {
        str(item).strip().casefold() for item in carga.get("disciplinas") or [] if str(item).strip()
    }

    turmas = [
        dict(item)
        for item in listar_turmas_ativas()
        if str(item.get("nome") or "").strip().casefold() in nomes_turmas
    ]
    disciplinas = [
        dict(item)
        for item in listar_disciplinas_ativas()
        if str(item.get("nome") or "").strip().casefold() in nomes_disciplinas
    ]
    combinacoes = []
    for turma in turmas:
        for disciplina in disciplinas:
            combinacoes.append(
                {
                    "turma_id": int(turma["id"]),
                    "turma_nome": turma.get("nome", "") or "",
                    "turno": turma.get("turno", "") or "",
                    "disciplina_id": int(disciplina["id"]),
                    "disciplina_nome": disciplina.get("nome", "") or "",
                }
            )

    return {
        "usa_atribuicoes_exatas": False,
        "turmas": turmas,
        "disciplinas": disciplinas,
        "combinacoes": combinacoes,
    }


def _escopo_professor(usuario_id: int) -> dict:
    atribuicoes = listar_atribuicoes_docentes_por_usuario_ids(
        [usuario_id],
        incluir_inativos=False,
    ).get(usuario_id, [])
    if not atribuicoes:
        return _escopo_professor_legado(usuario_id)

    turmas_por_id = {}
    disciplinas_por_id = {}
    combinacoes = []
    for atribuicao in atribuicoes:
        turma_id = int(atribuicao["turma_id"])
        disciplina_id = int(atribuicao["disciplina_id"])
        if turma_id not in turmas_por_id:
            turmas_por_id[turma_id] = {
                "id": turma_id,
                "nome": atribuicao.get("turma_nome", "") or "",
                "turno": atribuicao.get("turno", "") or "",
            }
        if disciplina_id not in disciplinas_por_id:
            disciplinas_por_id[disciplina_id] = {
                "id": disciplina_id,
                "nome": atribuicao.get("disciplina_nome", "") or "",
            }
        combinacoes.append(
            {
                "turma_id": turma_id,
                "turma_nome": atribuicao.get("turma_nome", "") or "",
                "turno": atribuicao.get("turno", "") or "",
                "disciplina_id": disciplina_id,
                "disciplina_nome": atribuicao.get("disciplina_nome", "") or "",
            }
        )

    turmas = sorted(
        turmas_por_id.values(),
        key=lambda item: (str(item.get("nome") or "").casefold(), int(item.get("id") or 0)),
    )
    disciplinas = sorted(
        disciplinas_por_id.values(),
        key=lambda item: (str(item.get("nome") or "").casefold(), int(item.get("id") or 0)),
    )
    combinacoes.sort(
        key=lambda item: (
            str(item.get("turma_nome") or "").casefold(),
            str(item.get("disciplina_nome") or "").casefold(),
            int(item.get("turma_id") or 0),
            int(item.get("disciplina_id") or 0),
        )
    )

    return {
        "usa_atribuicoes_exatas": True,
        "turmas": turmas,
        "disciplinas": disciplinas,
        "combinacoes": combinacoes,
    }


def _opcoes_professor(usuario_id: int) -> tuple[list[dict], list[dict]]:
    escopo = _escopo_professor(usuario_id)
    return escopo["turmas"], escopo["disciplinas"]


def _validar_escopo_professor(professor_id: int, turma_id: int, disciplina_id: int):
    escopo = _escopo_professor(professor_id)
    turma_ids = {int(item["id"]) for item in escopo["turmas"]}
    disciplina_ids = {int(item["id"]) for item in escopo["disciplinas"]}
    turma_id_valor = int(turma_id)
    disciplina_id_valor = int(disciplina_id)

    if turma_id_valor not in turma_ids:
        raise HTTPException(403, "Turma fora da carga do professor.")
    if disciplina_id_valor not in disciplina_ids:
        raise HTTPException(403, "Disciplina fora da carga do professor.")
    if escopo["usa_atribuicoes_exatas"]:
        combinacoes = {
            (int(item["turma_id"]), int(item["disciplina_id"])) for item in escopo["combinacoes"]
        }
        if (turma_id_valor, disciplina_id_valor) not in combinacoes:
            raise HTTPException(403, "Disciplina fora da atribuição docente da turma selecionada.")
    return escopo["turmas"], escopo["disciplinas"]


def _validar_filtros_professor(
    professor_id: int,
    *,
    turma_id: int | None = None,
    disciplina_id: int | None = None,
):
    escopo = _escopo_professor(professor_id)
    turma_ids = {int(item["id"]) for item in escopo["turmas"]}
    disciplina_ids = {int(item["id"]) for item in escopo["disciplinas"]}

    if turma_id is not None and int(turma_id) not in turma_ids:
        raise HTTPException(403, "Turma fora da carga do professor.")
    if disciplina_id is not None and int(disciplina_id) not in disciplina_ids:
        raise HTTPException(403, "Disciplina fora da carga do professor.")
    if escopo["usa_atribuicoes_exatas"] and turma_id is not None and disciplina_id is not None:
        combinacoes = {
            (int(item["turma_id"]), int(item["disciplina_id"])) for item in escopo["combinacoes"]
        }
        if (int(turma_id), int(disciplina_id)) not in combinacoes:
            raise HTTPException(403, "Disciplina fora da atribuição docente da turma selecionada.")


def _motivos_ativos_validos(motivo_ids: list[int]) -> list[dict]:
    motivos = buscar_motivos_pre_conselho_por_ids(motivo_ids)
    ids_recebidos = {int(valor) for valor in motivo_ids or [] if int(valor) > 0}
    ids_encontrados = {int(item["id"]) for item in motivos if int(item.get("ativo") or 0) == 1}
    if ids_recebidos != ids_encontrados:
        raise HTTPException(400, "Existe motivo inválido ou inativo na seleção.")
    return motivos


def _registro_editavel_usuario(usuario: dict, registro: dict) -> bool:
    if _usuario_eh_admin(usuario):
        return True
    if _usuario_eh_professor(usuario):
        return int(registro.get("professor_id") or 0) == _usuario_id(
            usuario
        ) and periodo_editavel_para_cargo(registro.get("periodo_status"), "PROFESSOR")
    return False


def _enriquecer_editavel(usuario: dict, itens: list[dict]) -> list[dict]:
    return [{**item, "editavel": _registro_editavel_usuario(usuario, item)} for item in itens]


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


def _montar_item_relatorio(
    *,
    nome: str = "",
    total_registros: int = 0,
    extra: str = "",
    item_id: int | None = None,
) -> dict:
    return {
        "id": int(item_id) if item_id is not None else None,
        "nome": str(nome or "").strip(),
        "total_registros": int(total_registros or 0),
        "extra": str(extra or "").strip(),
    }


def _mapa_corpo_docente_por_turmas(turmas: dict[int, str]) -> dict[int, dict]:
    turmas_validas = {
        int(turma_id): str(turma_nome or "").strip()
        for turma_id, turma_nome in (turmas or {}).items()
        if int(turma_id) > 0 and str(turma_nome or "").strip()
    }
    if not turmas_validas:
        return {}

    professores_por_turma = {
        turma_id: {
            "nomes": [],
            "corpo_docente": [],
        }
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
                {
                    "professor_nome": nome,
                    "disciplinas": list(disciplinas_lista),
                }
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
        atribuicoes = listar_atribuicoes_docentes(turma_id=turma_id, incluir_inativos=False)
        turmas_disciplinas = listar_turmas_disciplinas_admin(
            turma_id=turma_id,
            incluir_inativos=False,
        )
        for item in atribuicoes:
            registrar_docente(
                turma_id,
                item.get("professor_nome"),
                [item.get("disciplina_nome")],
            )
        for item in turmas_disciplinas:
            registrar_docente(
                turma_id,
                item.get("professor_nome"),
                [item.get("disciplina_nome")],
            )

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


def _mapa_professores_por_turma(registros: list[dict]) -> dict[int, dict]:
    turmas = {}
    for registro in registros or []:
        turma_id = int(registro.get("turma_id") or 0)
        turma_nome = str(registro.get("turma_nome") or "").strip()
        if turma_id > 0 and turma_nome:
            turmas[turma_id] = turma_nome

    return _mapa_corpo_docente_por_turmas(turmas)


def _enriquecer_professores_turma_registros(registros: list[dict]) -> list[dict]:
    mapa = _mapa_professores_por_turma(registros)
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


def _agrupar_estudantes_relatorio(registros: list[dict]) -> list[dict]:
    agrupados = {}
    for registro in registros or []:
        estudante_id = int(registro.get("estudante_id") or 0)
        if estudante_id <= 0:
            continue

        item = agrupados.setdefault(
            estudante_id,
            {
                "id": estudante_id,
                "nome": str(registro.get("estudante_nome") or "").strip(),
                "turma_id": int(registro.get("turma_id") or 0),
                "turma_nome": str(registro.get("turma_nome") or "").strip(),
                "total_registros": 0,
                "disciplinas": [],
                "professores": [],
                "niveis": [],
            },
        )
        item["total_registros"] += 1
        item["disciplinas"] = _lista_texto_unica(
            list(item["disciplinas"]) + [registro.get("disciplina_nome")]
        )
        item["professores"] = _lista_texto_unica(
            list(item["professores"]) + [registro.get("professor_nome")]
        )
        item["niveis"] = _lista_texto_unica(
            list(item["niveis"]) + [registro.get("nivel_atencao")]
        )
    return list(agrupados.values())


def _agrupar_professores_relatorio(registros: list[dict]) -> list[dict]:
    agrupados = {}
    for registro in registros or []:
        professor_id = int(registro.get("professor_id") or 0)
        if professor_id <= 0:
            continue

        item = agrupados.setdefault(
            professor_id,
            {
                "id": professor_id,
                "nome": str(registro.get("professor_nome") or "").strip(),
                "total_registros": 0,
                "turmas": [],
                "disciplinas": [],
            },
        )
        item["total_registros"] += 1
        item["turmas"] = _lista_texto_unica(list(item["turmas"]) + [registro.get("turma_nome")])
        item["disciplinas"] = _lista_texto_unica(
            list(item["disciplinas"]) + [registro.get("disciplina_nome")]
        )
    return list(agrupados.values())


def _coletar_motivos_frequentes(registros: list[dict], *, limite: int = 5) -> list[dict]:
    contador = Counter()
    for registro in registros or []:
        for motivo in registro.get("motivos") or []:
            descricao = str(motivo.get("descricao") or "").strip()
            if descricao:
                contador[descricao] += 1

    return [
        _montar_item_relatorio(nome=descricao, total_registros=total)
        for descricao, total in contador.most_common(limite)
    ]


def _rotulo_nivel_atencao_relatorio(nivel: str, niveis_map: dict[str, str]) -> str:
    nivel_limpo = str(nivel or "").strip()
    if not nivel_limpo:
        return ""
    return niveis_map.get(nivel_limpo, nivel_limpo.capitalize())


def _minhas_turmas_disciplinas(periodo_id: int, professor_id: int) -> list[dict]:
    escopo = _escopo_professor(professor_id)
    registros = contar_registros_pre_conselho_por_professor_periodo(periodo_id, professor_id)
    estudantes_por_turma = {
        int(turma["id"]): len(
            listar_estudantes(nome="", incluir_inativos=False, turma_id=int(turma["id"]))
        )
        for turma in escopo["turmas"]
    }

    itens = []
    for combinacao in escopo["combinacoes"]:
        turma_id = int(combinacao["turma_id"])
        disciplina_id = int(combinacao["disciplina_id"])
        total_estudantes = int(estudantes_por_turma.get(turma_id, 0))
        total_sinalizados = int(registros.get((turma_id, disciplina_id), 0))
        itens.append(
            {
                "turma_id": turma_id,
                "turma_nome": combinacao["turma_nome"],
                "turno": combinacao.get("turno", "") or "",
                "disciplina_id": disciplina_id,
                "disciplina_nome": combinacao["disciplina_nome"],
                "total_estudantes": total_estudantes,
                "total_sinalizados": total_sinalizados,
                "total_pendentes": max(total_estudantes - total_sinalizados, 0),
            }
        )
    return itens


@router.get("/preconselho/contexto", response_model=PreConselhoContextoOut)
def obter_contexto_preconselho_api(usuario=Depends(get_usuario_logado)):
    _exigir_acesso_preconselho(usuario)
    cargo = _normalizar_cargo(usuario)
    usuario_id = _usuario_id(usuario)
    turmas_professor, disciplinas_professor = (
        _opcoes_professor(usuario_id) if _usuario_eh_professor(usuario) else ([], [])
    )
    periodos = listar_periodos_pre_conselho()
    periodo_referencia = next(
        (item for item in periodos if item.get("status") == STATUS_PERIODO_PRE_CONSELHO_ABERTO),
        None,
    )
    minhas_turmas_disciplinas = (
        _minhas_turmas_disciplinas(int(periodo_referencia["id"]), usuario_id)
        if _usuario_eh_professor(usuario) and periodo_referencia
        else []
    )

    return {
        "cargo": cargo,
        "pode_configurar": _usuario_eh_admin(usuario),
        "pode_consolidar": _usuario_eh_gestor(usuario),
        "pode_relatorio": _usuario_eh_gestor(usuario),
        "pode_editar_periodo_fechado": _usuario_eh_admin(usuario),
        "professor_id": usuario_id if _usuario_eh_professor(usuario) else None,
        "professor_nome": str(usuario.get("nome") or "").strip()
        if _usuario_eh_professor(usuario)
        else "",
        "periodos": [
            {
                **item,
                "editavel": periodo_editavel_para_cargo(item.get("status"), cargo),
            }
            for item in periodos
        ],
        "turmas": turmas_professor if _usuario_eh_professor(usuario) else listar_turmas_ativas(),
        "disciplinas": disciplinas_professor
        if _usuario_eh_professor(usuario)
        else listar_disciplinas_ativas(),
        "motivos": listar_motivos_pre_conselho(incluir_inativos=_usuario_eh_admin(usuario)),
        "professores": [
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
            for item in listar_professores_agendamento()
        ]
        if _usuario_eh_gestor(usuario)
        else [],
        "niveis_atencao": listar_niveis_atencao_pre_conselho(),
        "motivos_pos_preconselho": listar_motivos_pos_pre_conselho(),
        "minhas_turmas_disciplinas": minhas_turmas_disciplinas,
    }


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
    return _minhas_turmas_disciplinas(int(periodo_id), _usuario_id(usuario))


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
    periodo = _validar_periodo(periodo_id)
    turma = _validar_turma(turma_id)
    disciplina = _validar_disciplina(disciplina_id)
    professor = _resolver_professor(usuario, professor_id, permitir_gestor=True)
    _validar_escopo_professor(int(professor["id"]), int(turma["id"]), int(disciplina["id"]))

    itens = listar_estudantes_pre_conselho_painel(
        periodo_id=int(periodo["id"]),
        turma_id=int(turma["id"]),
        disciplina_id=int(disciplina["id"]),
        professor_usuario_id=int(professor["id"]),
        busca_nome=q,
        status=status,
    )
    return itens


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
    periodo = _validar_periodo(payload.periodo_id)
    turma = _validar_turma(payload.turma_id)
    disciplina = _validar_disciplina(payload.disciplina_id)
    estudante = _validar_estudante_na_turma(payload.estudante_id, turma["id"])
    if payload.professor_id is not None and not _usuario_eh_admin(usuario):
        raise HTTPException(403, "Apenas administrador pode salvar em nome de outro professor.")
    professor = _resolver_professor(usuario, payload.professor_id, permitir_gestor=True)
    _validar_escopo_professor(int(professor["id"]), int(turma["id"]), int(disciplina["id"]))

    if _usuario_eh_professor(usuario) and not periodo_editavel_para_cargo(
        periodo.get("status"), "PROFESSOR"
    ):
        raise HTTPException(403, "Período fechado para edição do professor.")

    if not payload.sinalizar:
        existente = next(
            (
                item
                for item in listar_registros_pre_conselho(
                    periodo_id=int(periodo["id"]),
                    turma_id=int(turma["id"]),
                    disciplina_id=int(disciplina["id"]),
                    professor_usuario_id=int(professor["id"]),
                    estudante_id=int(estudante["id"]),
                )
            ),
            None,
        )
        if not existente:
            raise HTTPException(400, "Não existe registro salvo para remover.")
        if not _registro_editavel_usuario(usuario, existente):
            raise HTTPException(403, "Acesso negado.")
        excluir_registro_pre_conselho(
            int(existente["id"]),
            professor_usuario_id=None if _usuario_eh_admin(usuario) else int(professor["id"]),
        )
        return {**existente, "editavel": False}

    motivos = _motivos_ativos_validos(payload.motivo_ids)
    observacao_professor = _texto_opcional(
        payload.observacao_professor, "Observação do professor", max_len=1000
    )
    observacao_pos_preconselho = _texto_opcional(
        payload.pos_preconselho_observacao,
        "Observação do pós pré-conselho",
        max_len=1000,
    )
    try:
        nivel_atencao = validar_nivel_atencao_pre_conselho(payload.nivel_atencao)
        (
            pos_preconselho_recuperado,
            pos_preconselho_motivo_ids,
            pos_preconselho_motivos,
        ) = validar_motivos_pos_pre_conselho(
            payload.pos_preconselho_motivo_ids,
            payload.pos_preconselho_recuperado,
            observacao_pos_preconselho,
        )
        texto = gerar_texto_pre_conselho_individual(
            motivos=motivos,
            observacao_professor=observacao_professor,
            nivel_atencao=nivel_atencao,
            estudante_nome=str(estudante["nome"]),
            disciplina_nome=str(disciplina["nome"]),
            pos_preconselho_recuperado=pos_preconselho_recuperado,
            pos_preconselho_motivos=pos_preconselho_motivos,
            pos_preconselho_observacao=observacao_pos_preconselho,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    registro_id = criar_ou_atualizar_registro_pre_conselho(
        periodo_id=int(periodo["id"]),
        turma_id=int(turma["id"]),
        disciplina_id=int(disciplina["id"]),
        professor_usuario_id=int(professor["id"]),
        estudante_id=int(estudante["id"]),
        ano_letivo=int(periodo["ano_letivo"]),
        etapa=int(periodo["etapa"]),
        disciplina_nome=str(disciplina["nome"]),
        motivo_ids=[int(item["id"]) for item in motivos],
        texto_gerado=texto["texto"],
        observacao_professor=observacao_professor,
        nivel_atencao=nivel_atencao,
        pos_preconselho_recuperado=pos_preconselho_recuperado,
        pos_preconselho_motivo_ids=pos_preconselho_motivo_ids,
        pos_preconselho_observacao=observacao_pos_preconselho,
    )

    registro = buscar_registro_pre_conselho_por_id(registro_id)
    if not registro:
        raise HTTPException(500, "Falha ao carregar o registro salvo.")
    return {**registro, "editavel": _registro_editavel_usuario(usuario, registro)}


@router.delete("/preconselho/registros/{registro_id}")
def excluir_registro_preconselho_api(registro_id: int, usuario=Depends(get_usuario_logado)):
    _exigir_acesso_preconselho(usuario)
    registro = buscar_registro_pre_conselho_por_id(registro_id)
    if not registro:
        raise HTTPException(404, "Registro não encontrado.")
    if not _registro_editavel_usuario(usuario, registro):
        raise HTTPException(403, "Acesso negado.")

    if not excluir_registro_pre_conselho(
        registro_id,
        professor_usuario_id=None if _usuario_eh_admin(usuario) else int(registro["professor_id"]),
    ):
        raise HTTPException(500, "Falha ao excluir o registro.")
    return {"ok": True}


@router.get("/preconselho/registros", response_model=PreConselhoRegistrosOut)
def listar_registros_preconselho_api(
    periodo_id: int = Query(...),
    turma_id: int | None = Query(default=None),
    disciplina_id: int | None = Query(default=None),
    professor_id: int | None = Query(default=None),
    usuario=Depends(get_usuario_logado),
):
    _exigir_acesso_preconselho(usuario)
    _validar_periodo(periodo_id)

    professor_filtro = professor_id
    if _usuario_eh_professor(usuario):
        _validar_filtros_professor(
            _usuario_id(usuario),
            turma_id=turma_id,
            disciplina_id=disciplina_id,
        )
        professor_filtro = _usuario_id(usuario)

    itens = listar_registros_pre_conselho(
        periodo_id=periodo_id,
        turma_id=turma_id,
        disciplina_id=disciplina_id,
        professor_usuario_id=professor_filtro,
    )
    itens = _enriquecer_editavel(usuario, itens)
    return {"total_registros": len(itens), "itens": itens}


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
    periodo = _validar_periodo(periodo_id)

    turma = _validar_turma(turma_id) if turma_id is not None else None
    disciplina = _validar_disciplina(disciplina_id) if disciplina_id is not None else None
    professor = None
    if professor_id is not None:
        professor = _resolver_professor(usuario, professor_id, permitir_gestor=True)

    itens = listar_registros_pre_conselho(
        periodo_id=int(periodo["id"]),
        turma_id=int(turma["id"]) if turma else None,
        disciplina_id=int(disciplina["id"]) if disciplina else None,
        professor_usuario_id=int(professor["id"]) if professor else None,
    )
    itens = _enriquecer_editavel(usuario, itens)
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


@router.get("/preconselho/relatorio", response_model=PreConselhoRelatorioOut)
def gerar_relatorio_preconselho_api(
    periodo_id: int = Query(...),
    usuario=Depends(get_usuario_logado),
):
    if not _usuario_eh_gestor(usuario):
        raise HTTPException(403, "Acesso negado.")
    periodo = _validar_periodo(periodo_id)

    registros = _enriquecer_editavel(
        usuario,
        listar_registros_pre_conselho(periodo_id=int(periodo["id"])),
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
        for item in listar_turmas_ativas()
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

    professores_relacionados_por_turma = _mapa_corpo_docente_por_turmas(
        {
            turma_id: str(item.get("nome") or "").strip()
            for turma_id, item in turmas_base.items()
            if str(item.get("nome") or "").strip()
        }
    )

    estudantes_agrupados = sorted(
        _agrupar_estudantes_relatorio(registros),
        key=lambda item: (
            -int(item.get("total_registros") or 0),
            str(item.get("nome") or "").casefold(),
        ),
    )
    professores_agrupados = sorted(
        _agrupar_professores_relatorio(registros),
        key=lambda item: (
            -int(item.get("total_registros") or 0),
            str(item.get("nome") or "").casefold(),
        ),
    )
    motivos_frequentes = _coletar_motivos_frequentes(registros, limite=5)

    contagem_turmas = Counter(
        int(item.get("turma_id") or 0)
        for item in registros
        if int(item.get("turma_id") or 0) > 0
    )
    estudantes_por_turma = Counter(
        int(item.get("turma_id") or 0)
        for item in estudantes_agrupados
        if int(item.get("turma_id") or 0) > 0
    )

    turma_destaque = _montar_item_relatorio()
    if contagem_turmas:
        turma_id_destaque, total_registros_turma = sorted(
            contagem_turmas.items(),
            key=lambda item: (
                -int(item[1]),
                str((turmas_base.get(int(item[0])) or {}).get("nome") or "").casefold(),
            ),
        )[0]
        turma_info = turmas_base.get(int(turma_id_destaque), {})
        turma_destaque = _montar_item_relatorio(
            item_id=int(turma_id_destaque),
            nome=str(turma_info.get("nome") or "").strip(),
            total_registros=int(total_registros_turma or 0),
            extra=f"{int(estudantes_por_turma.get(int(turma_id_destaque), 0))} estudante(s) sinalizado(s)",
        )

    professor_destaque = _montar_item_relatorio()
    if professores_agrupados:
        professor_topo = professores_agrupados[0]
        professor_destaque = _montar_item_relatorio(
            item_id=int(professor_topo.get("id") or 0),
            nome=str(professor_topo.get("nome") or "").strip(),
            total_registros=int(professor_topo.get("total_registros") or 0),
            extra=f"{len(professor_topo.get('turmas') or [])} turma(s) com registros",
        )

    estudantes_destaque = []
    for item in estudantes_agrupados[:5]:
        niveis = _formatar_lista_natural(
            [
                _rotulo_nivel_atencao_relatorio(nivel, niveis_map)
                for nivel in item.get("niveis") or []
                if str(nivel or "").strip()
            ]
        )
        partes_extra = [
            str(item.get("turma_nome") or "").strip(),
            _formatar_lista_natural(item.get("disciplinas") or []),
            f"Atenção {niveis}" if niveis else "",
        ]
        estudantes_destaque.append(
            _montar_item_relatorio(
                item_id=int(item.get("id") or 0),
                nome=str(item.get("nome") or "").strip(),
                total_registros=int(item.get("total_registros") or 0),
                extra=" • ".join(parte for parte in partes_extra if parte),
            )
        )

    contador_niveis = Counter(
        _rotulo_nivel_atencao_relatorio(item.get("nivel_atencao"), niveis_map)
        for item in registros
        if _rotulo_nivel_atencao_relatorio(item.get("nivel_atencao"), niveis_map)
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
            + ", ".join(
                f"{item['nome']} ({item['total_registros']})" for item in motivos_frequentes[:3]
            )
            + "."
        )
    if contador_niveis:
        pontos_criticos.append(
            "Níveis de atenção mais recorrentes: "
            + ", ".join(
                f"{nivel} ({total})" for nivel, total in contador_niveis.most_common(3)
            )
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
        registros_turma = [
            item for item in registros if int(item.get("turma_id") or 0) == turma_id
        ]
        estudantes_turma = sorted(
            _agrupar_estudantes_relatorio(registros_turma),
            key=lambda item: (
                -int(item.get("total_registros") or 0),
                str(item.get("nome") or "").casefold(),
            ),
        )
        professores_turma = sorted(
            _agrupar_professores_relatorio(registros_turma),
            key=lambda item: (
                -int(item.get("total_registros") or 0),
                str(item.get("nome") or "").casefold(),
            ),
        )
        motivos_turma = _coletar_motivos_frequentes(registros_turma, limite=5)

        professor_destaque_turma = _montar_item_relatorio()
        if professores_turma:
            topo_turma = professores_turma[0]
            professor_destaque_turma = _montar_item_relatorio(
                item_id=int(topo_turma.get("id") or 0),
                nome=str(topo_turma.get("nome") or "").strip(),
                total_registros=int(topo_turma.get("total_registros") or 0),
                extra=_formatar_lista_natural(topo_turma.get("disciplinas") or []),
            )

        estudantes_destaque_turma = []
        for item in estudantes_turma[:5]:
            niveis = _formatar_lista_natural(
                [
                    _rotulo_nivel_atencao_relatorio(nivel, niveis_map)
                    for nivel in item.get("niveis") or []
                    if str(nivel or "").strip()
                ]
            )
            partes_extra = [
                _formatar_lista_natural(item.get("disciplinas") or []),
                f"Atenção {niveis}" if niveis else "",
            ]
            estudantes_destaque_turma.append(
                _montar_item_relatorio(
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
            (professores_relacionados_por_turma.get(turma_id) or {}).get("corpo_docente", []),
            key=lambda entry: (
                -int(
                    contagem_professores_turma.get(
                        str(entry.get("professor_nome") or "").strip(),
                        0,
                    )
                ),
                str(entry.get("professor_nome") or "").casefold(),
            ),
        ):
            nome_professor = str(item.get("professor_nome") or "").strip()
            if not nome_professor:
                continue
            nomes_professores_relacionados.add(nome_professor)
            professores_relacionados.append(
                _montar_item_relatorio(
                    nome=nome_professor,
                    total_registros=int(contagem_professores_turma.get(nome_professor, 0)),
                    extra=_formatar_lista_natural(item.get("disciplinas") or []),
                )
            )
        for item in professores_turma:
            nome_professor = str(item.get("nome") or "").strip()
            if not nome_professor or nome_professor in nomes_professores_relacionados:
                continue
            professores_relacionados.append(
                _montar_item_relatorio(
                    item_id=int(item.get("id") or 0),
                    nome=nome_professor,
                    total_registros=int(item.get("total_registros") or 0),
                    extra=_formatar_lista_natural(item.get("disciplinas") or []),
                )
            )

        contador_niveis_turma = Counter(
            _rotulo_nivel_atencao_relatorio(item.get("nivel_atencao"), niveis_map)
            for item in registros_turma
            if _rotulo_nivel_atencao_relatorio(item.get("nivel_atencao"), niveis_map)
        )
        pontos_atencao = []
        if motivos_turma:
            pontos_atencao.append(
                "Motivos mais frequentes: "
                + ", ".join(
                    f"{item['nome']} ({item['total_registros']})"
                    for item in motivos_turma[:3]
                )
                + "."
            )
        estudantes_multiplos = [
            item for item in estudantes_turma if int(item.get("total_registros") or 0) > 1
        ]
        if estudantes_multiplos:
            pontos_atencao.append(
                "Estudantes com mais de um registro: "
                + ", ".join(
                    f"{item['nome']} ({item['total_registros']})"
                    for item in estudantes_multiplos[:3]
                )
                + "."
            )
        if contador_niveis_turma:
            pontos_atencao.append(
                "Níveis de atenção em destaque: "
                + ", ".join(
                    f"{nivel} ({total})"
                    for nivel, total in contador_niveis_turma.most_common(3)
                )
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
    return criar_periodo_preconselho_admin(payload)


@router.put("/preconselho/periodos/{periodo_id}", response_model=PreConselhoPeriodoOut)
def atualizar_periodo_preconselho_api(
    periodo_id: int,
    payload: PreConselhoPeriodoUpdateIn,
    usuario=Depends(get_usuario_logado),
):
    _exigir_admin(usuario)
    return atualizar_periodo_preconselho_admin(periodo_id, payload)


@router.put("/preconselho/periodos/{periodo_id}/status", response_model=PreConselhoPeriodoOut)
def atualizar_status_periodo_preconselho_api(
    periodo_id: int,
    payload: PreConselhoPeriodoStatusIn,
    usuario=Depends(get_usuario_logado),
):
    _exigir_admin(usuario)
    return atualizar_status_periodo_preconselho_admin(periodo_id, payload.status)


@router.get("/preconselho/motivos", response_model=list[PreConselhoMotivoOut])
def listar_motivos_preconselho_api(
    incluir_inativos: bool = Query(default=False),
    usuario=Depends(get_usuario_logado),
):
    _exigir_acesso_preconselho(usuario)
    return listar_motivos_preconselho_visiveis(
        incluir_inativos=incluir_inativos,
        usuario_eh_admin=_usuario_eh_admin(usuario),
    )


@router.post("/preconselho/motivos", response_model=PreConselhoMotivoOut)
def criar_motivo_preconselho_api(
    payload: PreConselhoMotivoCreateIn, usuario=Depends(get_usuario_logado)
):
    _exigir_admin(usuario)
    return criar_motivo_preconselho_admin(payload)


@router.put("/preconselho/motivos/{motivo_id}", response_model=PreConselhoMotivoOut)
def atualizar_motivo_preconselho_api(
    motivo_id: int,
    payload: PreConselhoMotivoUpdateIn,
    usuario=Depends(get_usuario_logado),
):
    _exigir_admin(usuario)
    return atualizar_motivo_preconselho_admin(motivo_id, payload)


@router.put("/preconselho/motivos/{motivo_id}/status", response_model=PreConselhoMotivoOut)
def atualizar_status_motivo_preconselho_api(
    motivo_id: int,
    payload: PreConselhoMotivoStatusIn,
    usuario=Depends(get_usuario_logado),
):
    _exigir_admin(usuario)
    return atualizar_status_motivo_preconselho_admin(motivo_id, payload.ativo)


@router.get("/preconselho/niveis-atencao")
def listar_niveis_atencao_preconselho_api(usuario=Depends(get_usuario_logado)):
    _exigir_acesso_preconselho(usuario)
    return listar_niveis_atencao_pre_conselho()
