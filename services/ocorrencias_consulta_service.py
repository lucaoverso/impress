from db.catalogos import listar_disciplinas_ativas, listar_turmas_ativas
from db.usuarios import listar_professores_agendamento
from repositories.ocorrencias_repository import (
    STATUS_OCORRENCIA_REGISTRADO,
    STATUS_OCORRENCIA_VALIDOS,
    TIPOS_REGISTRO_OCORRENCIA,
    buscar_estudantes_ocorrencia,
    buscar_ocorrencia_por_id,
    buscar_professores_ocorrencia,
    listar_alineas,
    listar_artigos,
    listar_incisos,
    listar_leis,
    listar_ocorrencias,
    listar_regimento_itens,
)
from services.ocorrencia_disciplina_service import listar_acoes_aplicadas

STATUS_ROTULOS_OCORRENCIA = {
    "registrado": "Registrado",
    "em_acompanhamento": "Em acompanhamento",
    "aguardando_responsavel": "Aguardando responsavel",
    "resolvido": "Resolvido",
}

TIPOS_REGISTRO_ROTULOS_OCORRENCIA = {
    "estudante": "Estudante",
    "professor": "Professor",
    "geral": "Geral",
}

TURNOS_CONFIG_OCORRENCIA = {
    "MATUTINO": {"nome": "Matutino", "aulas": 5},
    "VESPERTINO": {"nome": "Vespertino", "aulas": 5},
    "NOTURNO": {"nome": "Noturno", "aulas": 4},
    "INTEGRAL": {"nome": "Integral", "aulas": 10},
}


def normalizar_turno_ocorrencia(valor: str | None) -> str:
    texto = str(valor or "").strip().upper()
    if not texto:
        return ""
    aliases = {
        "MATUTINO": "MATUTINO",
        "VESPERTINO": "VESPERTINO",
        "NOTURNO": "NOTURNO",
        "INTEGRAL": "INTEGRAL",
        "MATUTINO_EM": "MATUTINO",
        "VESPERTINO_EM": "VESPERTINO",
    }
    return aliases.get(texto, texto)


def faixas_disponiveis_turno_ocorrencia(turno: str | None) -> list[int]:
    turno_normalizado = normalizar_turno_ocorrencia(turno)
    config_turno = TURNOS_CONFIG_OCORRENCIA.get(turno_normalizado)
    total_aulas = int(config_turno["aulas"]) if config_turno else 0
    return list(range(1, total_aulas + 1))


def _formatar_professor_ocorrencia(professor: dict) -> dict:
    email = str(professor.get("email", "") or "").strip()
    nome = str(professor.get("nome") or "").strip()
    return {
        "id": professor["id"],
        "nome": nome,
        "email": email,
        "label": f"{nome} ({email})" if email else nome,
    }


def _formatar_estudante_ocorrencia(estudante: dict) -> dict:
    nome = str(estudante.get("nome") or "").strip()
    turma_nome = str(estudante.get("turma_nome") or "").strip()
    return {
        "id": estudante["id"],
        "nome": nome,
        "turma_id": estudante["turma_id"],
        "turma_nome": turma_nome,
        "label": f"{nome} ({turma_nome or 'Sem turma'})",
    }


def _formatar_turma_ocorrencia(turma: dict) -> dict:
    turno_turma = normalizar_turno_ocorrencia(turma.get("turno"))
    config_turno = TURNOS_CONFIG_OCORRENCIA.get(turno_turma)
    return {
        "id": turma["id"],
        "nome": turma["nome"],
        "turno": turno_turma,
        "turno_nome": config_turno["nome"] if config_turno else "Turno nao configurado",
        "aulas": int(config_turno["aulas"]) if config_turno else 0,
        "turno_valido": bool(config_turno),
        "faixas_disponiveis": faixas_disponiveis_turno_ocorrencia(turno_turma),
    }


def listar_opcoes_ocorrencias_service() -> dict:
    return {
        "status_padrao": STATUS_OCORRENCIA_REGISTRADO,
        "tipos_registro": [
            {
                "id": tipo,
                "nome": TIPOS_REGISTRO_ROTULOS_OCORRENCIA.get(tipo, tipo),
            }
            for tipo in TIPOS_REGISTRO_OCORRENCIA
        ],
        "acoes_aplicadas": listar_acoes_aplicadas(),
        "status": [
            {"id": status, "nome": STATUS_ROTULOS_OCORRENCIA.get(status, status)}
            for status in STATUS_OCORRENCIA_VALIDOS
        ],
        "turmas": [_formatar_turma_ocorrencia(item) for item in listar_turmas_ativas()],
        "professores": [
            _formatar_professor_ocorrencia(item) for item in listar_professores_agendamento()
        ],
        "disciplinas": [
            {
                "id": disciplina["id"],
                "nome": disciplina["nome"],
                "label": disciplina["nome"],
            }
            for disciplina in listar_disciplinas_ativas()
        ],
        "leis": listar_leis(),
        "artigos": listar_artigos(),
        "incisos": listar_incisos(),
        "alineas": listar_alineas(),
        "regimento_itens": [
            {**item, "label": item["artigo"]}
            for item in listar_regimento_itens(incluir_inativos=True)
        ],
    }


def buscar_professores_ocorrencia_service(*, termo: str, limite: int = 20) -> list[dict]:
    return [
        _formatar_professor_ocorrencia(item)
        for item in buscar_professores_ocorrencia(termo=termo, limite=limite)
    ]


def buscar_estudantes_ocorrencia_service(*, termo: str, limite: int = 20) -> list[dict]:
    return [
        _formatar_estudante_ocorrencia(item)
        for item in buscar_estudantes_ocorrencia(termo=termo, limite=limite)
    ]


def listar_ocorrencias_service(**filtros) -> list[dict]:
    return listar_ocorrencias(**filtros)


def buscar_ocorrencia_service(ocorrencia_id: int) -> dict:
    ocorrencia = buscar_ocorrencia_por_id(ocorrencia_id)
    if not ocorrencia:
        raise ValueError("Ocorrencia nao encontrada.")
    return ocorrencia
