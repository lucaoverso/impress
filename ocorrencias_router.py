import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from auth import get_usuario_logado
from database import (
    ACAO_OCORRENCIA_VALIDAS,
    STATUS_OCORRENCIA_REGISTRADO,
    STATUS_OCORRENCIA_VALIDOS,
    atualizar_ocorrencia,
    atualizar_estudante,
    atualizar_status_estudante,
    buscar_estudante_por_id,
    buscar_estudantes_ocorrencia,
    buscar_ocorrencia_por_id,
    buscar_professor_por_id_ocorrencia,
    buscar_professores_ocorrencia,
    buscar_turma_por_id,
    criar_estudante,
    criar_ocorrencia,
    listar_estudantes,
    listar_ocorrencias,
    listar_professores_agendamento,
    listar_turmas_ativas,
)
from models import (
    EstudanteCreateIn,
    EstudanteOut,
    EstudanteStatusIn,
    EstudanteUpdateIn,
    OcorrenciaCreateIn,
    OcorrenciaOut,
    OcorrenciaUpdateIn,
)

router = APIRouter()

_HORARIO_REGEX = re.compile(r"^\d{1,2}:\d{2}(:\d{2})?$")
_ACOES_ROTULOS = {
    "orientacao_verbal": "Orientacao verbal",
    "advertencia": "Advertencia",
    "chamada_responsavel": "Chamada de responsavel",
    "encaminhamento_direcao": "Encaminhamento a direcao",
    "registro_informativo": "Registro informativo",
}
_STATUS_ROTULOS = {
    "registrado": "Registrado",
    "em_acompanhamento": "Em acompanhamento",
    "aguardando_responsavel": "Aguardando responsavel",
    "resolvido": "Resolvido",
}
_TURNOS_CONFIG = {
    "INTEGRAL": {"nome": "Periodo integral", "aulas": 8},
    "MATUTINO": {"nome": "Matutino", "aulas": 5},
    "VESPERTINO": {"nome": "Vespertino", "aulas": 5},
    "VESPERTINO_EM": {"nome": "Vespertino E.M.", "aulas": 6},
}
_FAIXA_GLOBAL_OFFSET_POR_TURNO = {
    "MATUTINO": 0,
    "INTEGRAL": 0,
    "VESPERTINO": 5,
    "VESPERTINO_EM": 5,
}


def _model_to_dict(model, *, exclude_unset: bool = False) -> dict:
    if hasattr(model, "model_dump"):
        return model.model_dump(exclude_unset=exclude_unset)
    return model.dict(exclude_unset=exclude_unset)


def _normalizar_cargo(usuario: dict) -> str:
    cargo = str(usuario.get("cargo") or "").strip().upper()
    if cargo:
        return cargo

    perfil = str(usuario.get("perfil") or "").strip().lower()
    if perfil == "admin":
        return "ADMIN"
    if perfil == "coordenador":
        return "COORDENADOR"
    return "PROFESSOR"


def _exigir_gestor(usuario: dict):
    if _normalizar_cargo(usuario) not in {"ADMIN", "COORDENADOR"}:
        raise HTTPException(403, "Acesso negado")
    return usuario


def _texto_obrigatorio(valor: str | None, campo: str, *, max_len: int = 255) -> str:
    texto = str(valor or "").strip()
    if not texto:
        raise HTTPException(400, f"{campo} e obrigatorio.")
    if len(texto) > max_len:
        raise HTTPException(400, f"{campo} excede o limite de {max_len} caracteres.")
    return texto


def _texto_opcional(valor: str | None, *, max_len: int = 255) -> str | None:
    texto = str(valor or "").strip()
    if not texto:
        return None
    if len(texto) > max_len:
        raise HTTPException(400, f"Texto excede o limite de {max_len} caracteres.")
    return texto


def _validar_data_iso(valor: str, campo: str) -> str:
    texto = _texto_obrigatorio(valor, campo, max_len=20)
    try:
        data = datetime.strptime(texto, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(400, f"{campo} invalida. Use o formato YYYY-MM-DD.") from exc
    return data.isoformat()


def _validar_data_opcional(valor: str | None, campo: str) -> str | None:
    if valor is None:
        return None
    texto = str(valor).strip()
    if not texto:
        return None
    return _validar_data_iso(texto, campo)


def _validar_horario_ocorrencia(valor: str) -> str:
    texto = _texto_obrigatorio(valor, "Horario da ocorrencia", max_len=30)
    if _HORARIO_REGEX.match(texto):
        formato = "%H:%M:%S" if texto.count(":") == 2 else "%H:%M"
        try:
            datetime.strptime(texto, formato)
        except ValueError as exc:
            raise HTTPException(400, "Horario da ocorrencia invalido.") from exc
    return texto


def _validar_status(valor: str) -> str:
    status = str(valor or "").strip()
    if status not in STATUS_OCORRENCIA_VALIDOS:
        raise HTTPException(400, "Status invalido.")
    return status


def _validar_acao_aplicada(valor: str) -> str:
    acao = str(valor or "").strip()
    if acao not in ACAO_OCORRENCIA_VALIDAS:
        raise HTTPException(400, "Acao aplicada invalida.")
    return acao


def _validar_turma_id(turma_id: int) -> int:
    try:
        turma_id_valor = int(turma_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(400, "Turma invalida.") from exc
    if turma_id_valor <= 0:
        raise HTTPException(400, "Turma invalida.")

    turma = buscar_turma_por_id(turma_id_valor)
    if not turma:
        raise HTTPException(400, "Turma invalida.")
    return turma_id_valor


def _normalizar_turno_turma(valor: str | None) -> str:
    return str(valor or "").strip().upper()


def _faixa_global_por_turno_e_aula(turno: str, aula_turno: int) -> int:
    faixa_global = int(aula_turno) + _FAIXA_GLOBAL_OFFSET_POR_TURNO[turno]
    # No integral, a faixa 6 fica livre para não colidir com a 1ª do vespertino.
    if turno == "INTEGRAL" and int(aula_turno) > 5:
        faixa_global += 1
    return faixa_global


def _faixas_disponiveis_turno(turno: str) -> list[int]:
    turno_normalizado = _normalizar_turno_turma(turno)
    config_turno = _TURNOS_CONFIG.get(turno_normalizado)
    if not config_turno:
        return []

    faixas = []
    total_aulas = int(config_turno["aulas"])
    for aula_turno in range(1, total_aulas + 1):
        faixas.append(_faixa_global_por_turno_e_aula(turno_normalizado, aula_turno))
    return faixas


def _validar_faixa_aula_por_turma(aula: str | None, turma_id: int) -> str:
    texto_aula = _texto_obrigatorio(aula, "Aula", max_len=20)
    if not texto_aula.isdigit():
        raise HTTPException(400, "Aula invalida. Selecione uma faixa valida.")

    faixa_global = int(texto_aula)
    if faixa_global <= 0:
        raise HTTPException(400, "Aula invalida. Selecione uma faixa valida.")

    turma = buscar_turma_por_id(turma_id)
    if not turma:
        raise HTTPException(400, "Turma invalida.")

    turno_turma = _normalizar_turno_turma(turma.get("turno"))
    config_turno = _TURNOS_CONFIG.get(turno_turma)
    if not config_turno:
        raise HTTPException(400, "Turma sem turno configurado. Atualize o cadastro da turma.")

    faixas_disponiveis = set(_faixas_disponiveis_turno(turno_turma))
    if faixa_global not in faixas_disponiveis:
        raise HTTPException(400, "Faixa de aula invalida para o turno da turma selecionada.")

    return str(faixa_global)


def _validar_estudante_id(estudante_id: int | None) -> int | None:
    if estudante_id is None:
        return None
    try:
        estudante_id_valor = int(estudante_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(400, "Estudante invalido.") from exc
    if estudante_id_valor <= 0:
        raise HTTPException(400, "Estudante invalido.")
    return estudante_id_valor


def _validar_professor_id(professor_id: int | None) -> int | None:
    if professor_id is None:
        return None
    try:
        professor_id_valor = int(professor_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(400, "Professor requerente invalido.") from exc
    if professor_id_valor <= 0:
        raise HTTPException(400, "Professor requerente invalido.")
    return professor_id_valor


def _resolver_dados_estudante(
    *,
    nome_estudante: str | None,
    estudante_id: int | None,
    turma_id: int,
) -> tuple[str, int | None]:
    estudante_id_valor = _validar_estudante_id(estudante_id)
    nome_resolvido = _texto_opcional(nome_estudante, max_len=255)

    if estudante_id_valor is None:
        if not nome_resolvido:
            raise HTTPException(400, "Nome do estudante e obrigatorio.")
        return nome_resolvido, None

    estudante = buscar_estudante_por_id(estudante_id_valor)
    if not estudante:
        raise HTTPException(400, "Estudante selecionado nao encontrado.")
    if int(estudante.get("ativo") or 0) != 1:
        raise HTTPException(400, "Estudante selecionado esta inativo.")

    turma_estudante_id = int(estudante.get("turma_id") or 0)
    if turma_estudante_id != int(turma_id):
        raise HTTPException(400, "Turma da ocorrencia diferente da turma do estudante.")

    return str(estudante.get("nome") or "").strip(), estudante_id_valor


def _resolver_dados_professor(
    *,
    professor_requerente: str | None,
    professor_requerente_id: int | None,
) -> tuple[str, int | None]:
    professor_id_valor = _validar_professor_id(professor_requerente_id)
    professor_nome = _texto_opcional(professor_requerente, max_len=255)

    if professor_id_valor is None:
        if not professor_nome:
            raise HTTPException(400, "Professor requerente e obrigatorio.")
        return professor_nome, None

    professor = buscar_professor_por_id_ocorrencia(professor_id_valor)
    if not professor:
        raise HTTPException(400, "Professor selecionado nao encontrado.")
    return str(professor.get("nome") or "").strip(), professor_id_valor


def _montar_resposta_ocorrencia(ocorrencia_id: int) -> dict:
    ocorrencia = buscar_ocorrencia_por_id(ocorrencia_id)
    if not ocorrencia:
        raise HTTPException(404, "Ocorrencia nao encontrada.")
    return ocorrencia


def _montar_resposta_estudante(estudante_id: int) -> dict:
    estudante = buscar_estudante_por_id(estudante_id)
    if not estudante:
        raise HTTPException(404, "Estudante nao encontrado.")
    return estudante


@router.get("/ocorrencias/opcoes")
def listar_opcoes_ocorrencias(usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    turmas = listar_turmas_ativas()
    professores = listar_professores_agendamento()

    turmas_formatadas = []
    for turma in turmas:
        turno_turma = _normalizar_turno_turma(turma.get("turno"))
        config_turno = _TURNOS_CONFIG.get(turno_turma)
        turmas_formatadas.append(
            {
                "id": turma["id"],
                "nome": turma["nome"],
                "turno": turno_turma,
                "turno_nome": config_turno["nome"] if config_turno else "Turno nao configurado",
                "aulas": int(config_turno["aulas"]) if config_turno else 0,
                "turno_valido": bool(config_turno),
                "faixas_disponiveis": _faixas_disponiveis_turno(turno_turma),
            }
        )

    return {
        "status_padrao": STATUS_OCORRENCIA_REGISTRADO,
        "acoes_aplicadas": [
            {"id": acao, "nome": _ACOES_ROTULOS.get(acao, acao)}
            for acao in ACAO_OCORRENCIA_VALIDAS
        ],
        "status": [
            {"id": status, "nome": _STATUS_ROTULOS.get(status, status)}
            for status in STATUS_OCORRENCIA_VALIDOS
        ],
        "turmas": turmas_formatadas,
        "professores": [
            {
                "id": professor["id"],
                "nome": professor["nome"],
                "email": professor.get("email", ""),
                "label": (
                    f'{professor["nome"]} ({professor.get("email", "")})'
                    if str(professor.get("email", "")).strip()
                    else str(professor["nome"])
                ),
            }
            for professor in professores
        ],
    }


@router.get("/ocorrencias/busca/professores")
def buscar_professores_ocorrencia_api(
    q: str = Query(default=""),
    limite: int = Query(default=20),
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    professores = buscar_professores_ocorrencia(termo=q, limite=limite)
    return [
        {
            "id": professor["id"],
            "nome": professor["nome"],
            "email": professor.get("email", ""),
            "label": (
                f'{professor["nome"]} ({professor.get("email", "")})'
                if str(professor.get("email", "")).strip()
                else str(professor["nome"])
            ),
        }
        for professor in professores
    ]


@router.get("/ocorrencias/busca/estudantes")
def buscar_estudantes_ocorrencia_api(
    q: str = Query(default=""),
    turma_id: int | None = Query(default=None),
    limite: int = Query(default=20),
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    turma_id_filtro = None
    if turma_id is not None:
        turma_id_filtro = _validar_turma_id(turma_id)

    estudantes = buscar_estudantes_ocorrencia(
        termo=q,
        turma_id=turma_id_filtro,
        limite=limite,
    )
    return [
        {
            "id": estudante["id"],
            "nome": estudante["nome"],
            "turma_id": estudante["turma_id"],
            "turma_nome": estudante.get("turma_nome", ""),
            "label": f'{estudante["nome"]} ({estudante.get("turma_nome", "Sem turma")})',
        }
        for estudante in estudantes
    ]


@router.post("/ocorrencias", response_model=OcorrenciaOut)
def criar_ocorrencia_api(payload: OcorrenciaCreateIn, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)

    turma_id = _validar_turma_id(payload.turma_id)
    faixa_aula = _validar_faixa_aula_por_turma(payload.aula, turma_id)
    status = _validar_status(payload.status or STATUS_OCORRENCIA_REGISTRADO)
    acao_aplicada = _validar_acao_aplicada(payload.acao_aplicada)

    nome_estudante, estudante_id = _resolver_dados_estudante(
        nome_estudante=payload.nome_estudante,
        estudante_id=payload.estudante_id,
        turma_id=turma_id,
    )
    professor_requerente, professor_requerente_id = _resolver_dados_professor(
        professor_requerente=payload.professor_requerente,
        professor_requerente_id=payload.professor_requerente_id,
    )

    try:
        ocorrencia_id = criar_ocorrencia(
            nome_estudante=nome_estudante,
            estudante_id=estudante_id,
            turma_id=turma_id,
            professor_requerente=professor_requerente,
            professor_requerente_id=professor_requerente_id,
            disciplina=_texto_obrigatorio(payload.disciplina, "Disciplina"),
            data_ocorrencia=_validar_data_iso(payload.data_ocorrencia, "Data da ocorrencia"),
            aula=faixa_aula,
            horario_ocorrencia=_validar_horario_ocorrencia(payload.horario_ocorrencia),
            descricao=_texto_obrigatorio(payload.descricao, "Descricao", max_len=5000),
            acao_aplicada=acao_aplicada,
            status=status,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return _montar_resposta_ocorrencia(ocorrencia_id)


@router.get("/ocorrencias", response_model=list[OcorrenciaOut])
def listar_ocorrencias_api(
    status: str | None = Query(default=None),
    turma_id: int | None = Query(default=None),
    nome_estudante: str | None = Query(default=None),
    data_inicial: str | None = Query(default=None),
    data_final: str | None = Query(default=None),
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)

    status_filtro = None
    if status is not None and str(status).strip():
        status_filtro = _validar_status(status)

    data_inicial_norm = _validar_data_opcional(data_inicial, "Data inicial")
    data_final_norm = _validar_data_opcional(data_final, "Data final")
    if data_inicial_norm and data_final_norm and data_inicial_norm > data_final_norm:
        raise HTTPException(400, "Periodo invalido: data inicial maior que data final.")

    turma_id_filtro = None
    if turma_id is not None:
        turma_id_filtro = _validar_turma_id(turma_id)

    return listar_ocorrencias(
        status=status_filtro,
        turma_id=turma_id_filtro,
        nome_estudante=str(nome_estudante or "").strip() or None,
        data_inicial=data_inicial_norm,
        data_final=data_final_norm,
    )


@router.get("/ocorrencias/{ocorrencia_id}", response_model=OcorrenciaOut)
def buscar_ocorrencia_api(ocorrencia_id: int, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    return _montar_resposta_ocorrencia(ocorrencia_id)


@router.patch("/ocorrencias/{ocorrencia_id}", response_model=OcorrenciaOut)
def atualizar_ocorrencia_parcial_api(
    ocorrencia_id: int,
    payload: OcorrenciaUpdateIn,
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    atual = buscar_ocorrencia_por_id(ocorrencia_id)
    if not atual:
        raise HTTPException(404, "Ocorrencia nao encontrada.")

    dados_brutos = _model_to_dict(payload, exclude_unset=True)
    if not dados_brutos:
        raise HTTPException(400, "Informe ao menos um campo para atualizar.")

    dados_validados = {}

    if {"nome_estudante", "estudante_id", "turma_id"} & set(dados_brutos.keys()):
        turma_id_merge = _validar_turma_id(dados_brutos.get("turma_id", atual["turma_id"]))
        nome_estudante_merge, estudante_id_merge = _resolver_dados_estudante(
            nome_estudante=dados_brutos.get("nome_estudante", atual["nome_estudante"]),
            estudante_id=dados_brutos.get("estudante_id", atual.get("estudante_id")),
            turma_id=turma_id_merge,
        )
        dados_validados["turma_id"] = turma_id_merge
        dados_validados["nome_estudante"] = nome_estudante_merge
        dados_validados["estudante_id"] = estudante_id_merge
    elif "turma_id" in dados_brutos:
        dados_validados["turma_id"] = _validar_turma_id(dados_brutos["turma_id"])

    if {"professor_requerente", "professor_requerente_id"} & set(dados_brutos.keys()):
        professor_nome_merge, professor_id_merge = _resolver_dados_professor(
            professor_requerente=dados_brutos.get(
                "professor_requerente",
                atual["professor_requerente"],
            ),
            professor_requerente_id=dados_brutos.get(
                "professor_requerente_id",
                atual.get("professor_requerente_id"),
            ),
        )
        dados_validados["professor_requerente"] = professor_nome_merge
        dados_validados["professor_requerente_id"] = professor_id_merge

    if "disciplina" in dados_brutos:
        dados_validados["disciplina"] = _texto_obrigatorio(
            dados_brutos["disciplina"],
            "Disciplina",
        )
    if "data_ocorrencia" in dados_brutos:
        dados_validados["data_ocorrencia"] = _validar_data_iso(
            dados_brutos["data_ocorrencia"],
            "Data da ocorrencia",
        )
    if "aula" in dados_brutos:
        turma_id_para_aula = int(dados_validados.get("turma_id", atual["turma_id"]))
        dados_validados["aula"] = _validar_faixa_aula_por_turma(
            dados_brutos["aula"],
            turma_id_para_aula,
        )
    elif "turma_id" in dados_validados:
        # Ao trocar turma, garante que a aula atual também pertença à faixa válida do novo turno.
        dados_validados["aula"] = _validar_faixa_aula_por_turma(
            atual.get("aula"),
            int(dados_validados["turma_id"]),
        )
    if "horario_ocorrencia" in dados_brutos:
        dados_validados["horario_ocorrencia"] = _validar_horario_ocorrencia(
            dados_brutos["horario_ocorrencia"]
        )
    if "descricao" in dados_brutos:
        dados_validados["descricao"] = _texto_obrigatorio(
            dados_brutos["descricao"],
            "Descricao",
            max_len=5000,
        )
    if "acao_aplicada" in dados_brutos:
        dados_validados["acao_aplicada"] = _validar_acao_aplicada(dados_brutos["acao_aplicada"])
    if "status" in dados_brutos:
        dados_validados["status"] = _validar_status(dados_brutos["status"])

    if not dados_validados:
        raise HTTPException(400, "Nenhum campo valido informado para atualizacao.")

    try:
        alterado = atualizar_ocorrencia(ocorrencia_id, dados_validados)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    if not alterado:
        raise HTTPException(404, "Ocorrencia nao encontrada.")
    return _montar_resposta_ocorrencia(ocorrencia_id)


@router.put("/ocorrencias/{ocorrencia_id}", response_model=OcorrenciaOut)
def atualizar_ocorrencia_api(
    ocorrencia_id: int,
    payload: OcorrenciaUpdateIn,
    usuario=Depends(get_usuario_logado),
):
    return atualizar_ocorrencia_parcial_api(ocorrencia_id, payload, usuario)


@router.get("/estudantes", response_model=list[EstudanteOut])
def listar_estudantes_api(
    nome: str | None = Query(default=None),
    turma_id: int | None = Query(default=None),
    incluir_inativos: bool = Query(default=True),
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    turma_id_filtro = None
    if turma_id is not None:
        turma_id_filtro = _validar_turma_id(turma_id)

    return listar_estudantes(
        incluir_inativos=incluir_inativos,
        nome=str(nome or "").strip() or None,
        turma_id=turma_id_filtro,
    )


@router.get("/estudantes/{estudante_id}", response_model=EstudanteOut)
def buscar_estudante_api(estudante_id: int, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    return _montar_resposta_estudante(estudante_id)


@router.post("/estudantes", response_model=EstudanteOut)
def criar_estudante_api(payload: EstudanteCreateIn, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    turma_id = _validar_turma_id(payload.turma_id)
    try:
        estudante_id = criar_estudante(
            nome=_texto_obrigatorio(payload.nome, "Nome do estudante"),
            turma_id=turma_id,
            ativo=True,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return _montar_resposta_estudante(estudante_id)


@router.put("/estudantes/{estudante_id}", response_model=EstudanteOut)
def atualizar_estudante_api(
    estudante_id: int,
    payload: EstudanteUpdateIn,
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    if not buscar_estudante_por_id(estudante_id):
        raise HTTPException(404, "Estudante nao encontrado.")

    turma_id = _validar_turma_id(payload.turma_id)
    try:
        alterado = atualizar_estudante(
            estudante_id=estudante_id,
            nome=_texto_obrigatorio(payload.nome, "Nome do estudante"),
            turma_id=turma_id,
            ativo=bool(payload.ativo),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    if not alterado:
        raise HTTPException(404, "Estudante nao encontrado.")
    return _montar_resposta_estudante(estudante_id)


@router.put("/estudantes/{estudante_id}/status")
def atualizar_status_estudante_api(
    estudante_id: int,
    payload: EstudanteStatusIn,
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    alterado = atualizar_status_estudante(estudante_id, bool(payload.ativo))
    if not alterado:
        raise HTTPException(404, "Estudante nao encontrado.")
    return {"mensagem": "Status do estudante atualizado com sucesso."}
