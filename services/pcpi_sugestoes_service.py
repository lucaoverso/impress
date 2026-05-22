from services.pcpi_common_service import (
    GRUPO_AUTOMATICO_APOIO,
    GRUPO_AUTOMATICO_AUDIOVISUAL,
    GRUPO_AUTOMATICO_STE,
    GRUPO_AUTOMATICO_TECNOLOGIA,
    _normalizar_texto_chave,
    _texto_limpo,
    agendamento_pertence_ao_turno_pcpi,
    nome_turno_pcpi,
    turno_agendamento_pertence_ao_turno_pcpi,
    validar_data_pcpi,
    validar_turno_pcpi,
)
from services.pcpi_texto_service import gerar_texto_base_pcpi


def classificar_categoria_uso(recurso_nome: str, recurso_tipo: str) -> str:
    chave = _normalizar_texto_chave(f"{recurso_nome} {recurso_tipo}")
    if any(
        token in chave for token in ("ste", "sala de tecnologia", "sala de tecnologia educacional")
    ):
        return GRUPO_AUTOMATICO_STE
    if any(
        token in chave
        for token in ("notebook", "tablet", "laboratorio", "maker", "computador", "tecnologia")
    ):
        return GRUPO_AUTOMATICO_TECNOLOGIA
    if any(
        token in chave
        for token in ("projetor", "datashow", "audio", "video", "som", "caixa de som")
    ):
        return GRUPO_AUTOMATICO_AUDIOVISUAL
    return GRUPO_AUTOMATICO_APOIO


def normalizar_agendamento_pcpi(
    agendamento: dict,
    carga_professor: dict | None = None,
    turno_pcpi: str | None = None,
) -> dict:
    carga = carga_professor or {}
    componentes = [
        _texto_limpo(item) for item in (carga.get("disciplinas") or []) if _texto_limpo(item)
    ]

    recurso_nome = _texto_limpo(agendamento.get("recurso_nome"))
    recurso_tipo = _texto_limpo(agendamento.get("recurso_tipo"))
    turno = _texto_limpo(turno_pcpi or agendamento.get("turno")).upper()

    return {
        "agendamento_id": int(agendamento["id"]),
        "data": _texto_limpo(agendamento.get("data")),
        "turno": turno,
        "turno_nome": nome_turno_pcpi(turno),
        "aula": _texto_limpo(agendamento.get("aula")),
        "faixa_global": int(agendamento.get("faixa_global") or 0),
        "recurso_id": int(agendamento["recurso_id"]),
        "recurso_nome": recurso_nome,
        "recurso_tipo": recurso_tipo,
        "professor_id": int(agendamento["usuario_id"]),
        "professor_nome": _texto_limpo(agendamento.get("professor_nome")),
        "componentes": componentes,
        "turma": _texto_limpo(agendamento.get("turma")),
        "tema_aula": _texto_limpo(agendamento.get("tema_aula")),
        "observacao": _texto_limpo(agendamento.get("observacao")),
        "categoria_uso": classificar_categoria_uso(recurso_nome, recurso_tipo),
    }


def _montar_resumo_sugestoes(itens: list[dict]) -> dict:
    recursos = []
    professores = []
    turmas = []
    categorias = []
    for item in itens:
        recurso = _texto_limpo(item.get("recurso_nome"))
        professor = _texto_limpo(item.get("professor_nome"))
        turma = _texto_limpo(item.get("turma"))
        categoria = _texto_limpo(item.get("categoria_uso"))
        if recurso and recurso not in recursos:
            recursos.append(recurso)
        if professor and professor not in professores:
            professores.append(professor)
        if turma and turma not in turmas:
            turmas.append(turma)
        if categoria and categoria not in categorias:
            categorias.append(categoria)
    return {
        "total_agendamentos": len(itens),
        "total_professores": len(professores),
        "total_turmas": len(turmas),
        "recursos": recursos,
        "categorias_uso": categorias,
    }


def montar_sugestoes_pcpi(
    data: str,
    turno: str,
    agendamentos: list[dict],
    cargas_professores: dict[int, dict] | None = None,
) -> dict:
    cargas = cargas_professores or {}
    itens = []

    for agendamento in sorted(
        agendamentos,
        key=lambda item: (
            int(item.get("faixa_global") or 0),
            _texto_limpo(item.get("recurso_nome")),
            _texto_limpo(item.get("turma")),
        ),
    ):
        usuario_id = int(agendamento.get("usuario_id") or 0)
        itens.append(normalizar_agendamento_pcpi(agendamento, cargas.get(usuario_id), turno))

    return {
        "data": data,
        "turno": _texto_limpo(turno).upper(),
        "turno_nome": nome_turno_pcpi(turno),
        "resumo": _montar_resumo_sugestoes(itens),
        "itens": itens,
        "texto_base": gerar_texto_base_pcpi(data, turno, itens),
    }


def normalizar_registros_manuais_pcpi(registros: list[dict], turno: str) -> list[dict]:
    turno_norm = validar_turno_pcpi(turno)
    registros_turno = [
        dict(item)
        for item in (registros or [])
        if turno_agendamento_pertence_ao_turno_pcpi(item.get("turno"), turno_norm)
    ]
    for registro in registros_turno:
        registro["turno"] = turno_norm
    return registros_turno


def montar_listagem_registros_manuais_pcpi(data: str, turno: str, registros: list[dict]) -> dict:
    data_norm = validar_data_pcpi(data)
    turno_norm = validar_turno_pcpi(turno)
    registros_norm = normalizar_registros_manuais_pcpi(registros, turno_norm)
    return {
        "data": data_norm,
        "turno": turno_norm,
        "turno_nome": nome_turno_pcpi(turno_norm),
        "total_registros": len(registros_norm),
        "itens": registros_norm,
    }


def montar_contexto_pcpi(
    data: str,
    turno: str,
    agendamentos_dia: list[dict],
    cargas_professores: dict[int, dict] | None,
    registros_manuais: list[dict],
) -> tuple[dict, list[dict]]:
    data_norm = validar_data_pcpi(data)
    turno_norm = validar_turno_pcpi(turno)
    agendamentos_turno = [
        item
        for item in (agendamentos_dia or [])
        if agendamento_pertence_ao_turno_pcpi(item, turno_norm)
    ]
    sugestoes = montar_sugestoes_pcpi(
        data_norm,
        turno_norm,
        agendamentos_turno,
        cargas_professores or {},
    )
    registros_norm = normalizar_registros_manuais_pcpi(registros_manuais, turno_norm)
    return sugestoes, registros_norm


def filtrar_itens_automaticos_pcpi(
    itens: list[dict],
    agendamento_ids: list[int] | None,
) -> list[dict]:
    if agendamento_ids is None:
        return list(itens or [])

    ids_validos = {
        int(valor) for valor in agendamento_ids if isinstance(valor, int) and int(valor) > 0
    }
    if not ids_validos:
        return []

    return [item for item in (itens or []) if int(item.get("agendamento_id") or 0) in ids_validos]
