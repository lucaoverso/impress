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
from db.docencia import (
    listar_atribuicoes_docentes,
    listar_atribuicoes_docentes_por_usuario_ids,
    listar_turmas_disciplinas_admin,
)
from db.ocorrencias import buscar_estudante_por_id, listar_estudantes
from db.preconselho import (
    atualizar_motivo_pre_conselho_dados,
    atualizar_periodo_pre_conselho_dados,
    atualizar_status_motivo_pre_conselho,
    atualizar_status_periodo_pre_conselho,
    buscar_motivo_pre_conselho_por_id,
    buscar_motivos_pre_conselho_por_ids,
    buscar_periodo_pre_conselho_por_id,
    buscar_registro_pre_conselho_por_id,
    contar_registros_pre_conselho_por_professor_periodo,
    criar_motivo_pre_conselho,
    criar_ou_atualizar_registro_pre_conselho,
    criar_periodo_pre_conselho,
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
from models import (
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
    PreConselhoTextoOut,
    PreConselhoTextoPreviewIn,
    PreConselhoTurmaDisciplinaOut,
    PreConselhoTurmaOut,
)
from services.preconselho_service import (
    STATUS_PERIODO_PRE_CONSELHO_ABERTO,
    gerar_texto_consolidado_pre_conselho,
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


def _mapa_professores_por_turma(registros: list[dict]) -> dict[int, dict]:
    turmas = {}
    for registro in registros or []:
        turma_id = int(registro.get("turma_id") or 0)
        turma_nome = str(registro.get("turma_nome") or "").strip()
        if turma_id > 0 and turma_nome:
            turmas[turma_id] = turma_nome

    if not turmas:
        return {}

    professores_por_turma = {
        turma_id: {
            "nomes": [],
            "corpo_docente": [],
        }
        for turma_id in turmas
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

    for turma_id in sorted(turmas):
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
    for turma_id, turma_nome in turmas.items():
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
