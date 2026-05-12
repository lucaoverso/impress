import os
import re
import uuid
from datetime import datetime

from services.horario_escolar_service import (
    dia_semana_por_data,
    nome_dia_semana,
    ordenar_horarios_escolares,
    validar_ano_letivo,
)

APC_PUBLICO_ALVO_TODOS_PROFESSORES = "TODOS_PROFESSORES"
APC_PUBLICO_ALVO_HORARIO_DIA = "HORARIO_DIA"
APC_PUBLICOS_ALVO_VALIDOS = (
    APC_PUBLICO_ALVO_TODOS_PROFESSORES,
    APC_PUBLICO_ALVO_HORARIO_DIA,
)
APC_PUBLICO_ALVO_LABELS = {
    APC_PUBLICO_ALVO_TODOS_PROFESSORES: "Todos os professores",
    APC_PUBLICO_ALVO_HORARIO_DIA: "Professores com aula na data",
}


def validar_mes_referencia(valor: str) -> str:
    try:
        return datetime.strptime(str(valor or "").strip(), "%Y-%m").strftime("%Y-%m")
    except ValueError as exc:
        raise ValueError("Mês inválido. Use o formato YYYY-MM.") from exc


def intervalo_mes_referencia(valor: str) -> tuple[str, str]:
    mes = validar_mes_referencia(valor)
    inicio = datetime.strptime(f"{mes}-01", "%Y-%m-%d").date()
    if inicio.month == 12:
        proximo_mes = inicio.replace(year=inicio.year + 1, month=1, day=1)
    else:
        proximo_mes = inicio.replace(month=inicio.month + 1, day=1)
    fim = proximo_mes.fromordinal(proximo_mes.toordinal() - 1)
    return inicio.isoformat(), fim.isoformat()


def normalizar_data_apc(valor: str) -> str:
    try:
        return datetime.strptime(str(valor or "").strip(), "%Y-%m-%d").date().isoformat()
    except ValueError as exc:
        raise ValueError("Data inválida. Use o formato YYYY-MM-DD.") from exc


def _parse_datetime_local(valor: str) -> datetime:
    texto = str(valor or "").strip()
    formatos = (
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
    )
    for formato in formatos:
        try:
            return datetime.strptime(texto, formato)
        except ValueError:
            continue
    raise ValueError("Prazo inválido. Use o formato YYYY-MM-DDTHH:MM.")


def normalizar_prazo_envio(data_referencia: str, prazo_envio: str = "") -> str:
    data_norm = normalizar_data_apc(data_referencia)
    texto = str(prazo_envio or "").strip()
    if not texto:
        return f"{data_norm} 23:59:00"

    prazo = _parse_datetime_local(texto)
    if prazo.date().isoformat() < data_norm:
        raise ValueError("O prazo de envio não pode ser anterior à data de referência.")
    return prazo.strftime("%Y-%m-%d %H:%M:%S")


def normalizar_publico_alvo(valor: str) -> str:
    publico = str(valor or "").strip().upper()
    if not publico:
        return APC_PUBLICO_ALVO_TODOS_PROFESSORES
    if publico not in APC_PUBLICOS_ALVO_VALIDOS:
        raise ValueError("Público-alvo inválido.")
    return publico


def nome_publico_alvo(publico_alvo: str) -> str:
    publico = normalizar_publico_alvo(publico_alvo)
    return APC_PUBLICO_ALVO_LABELS.get(publico, publico)


def _parse_sqlite_datetime(valor: str):
    texto = str(valor or "").strip()
    if not texto:
        return None
    for formato in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M"):
        try:
            return datetime.strptime(texto, formato)
        except ValueError:
            continue
    return None


def prazo_envio_input(valor: str) -> str:
    prazo = _parse_sqlite_datetime(valor)
    if not prazo:
        return ""
    return prazo.strftime("%Y-%m-%dT%H:%M")


def periodo_apc_aberto(item: dict, agora: datetime | None = None) -> bool:
    prazo = _parse_sqlite_datetime((item or {}).get("prazo_envio"))
    if not prazo:
        return False
    referencia = agora or datetime.now()
    return referencia <= prazo


def enriquecer_periodo_apc(item: dict, agora: datetime | None = None) -> dict:
    periodo = dict(item or {})
    data_referencia = normalizar_data_apc(periodo.get("data_referencia"))
    dia_semana = dia_semana_por_data(data_referencia)
    prazo = str(periodo.get("prazo_envio") or "").strip()
    publico_alvo = normalizar_publico_alvo(periodo.get("publico_alvo"))
    return {
        **periodo,
        "id": int(periodo.get("id") or 0),
        "ano_letivo": int(periodo.get("ano_letivo") or 0),
        "criado_por_usuario_id": int(periodo.get("criado_por_usuario_id") or 0),
        "data_referencia": data_referencia,
        "dia_semana": dia_semana,
        "dia_semana_nome": nome_dia_semana(dia_semana),
        "prazo_envio": prazo,
        "prazo_envio_input": prazo_envio_input(prazo),
        "prazo_expirado": not periodo_apc_aberto({"prazo_envio": prazo}, agora=agora),
        "titulo": str(periodo.get("titulo") or "Documento").strip() or "Documento",
        "observacao": str(periodo.get("observacao") or "").strip(),
        "publico_alvo": publico_alvo,
        "publico_alvo_label": nome_publico_alvo(publico_alvo),
        "criado_em": str(periodo.get("criado_em") or "").strip(),
        "atualizado_em": str(periodo.get("atualizado_em") or "").strip(),
    }


def ordenar_periodos_apc(itens: list[dict]) -> list[dict]:
    enriquecidos = [enriquecer_periodo_apc(item) for item in (itens or [])]
    return sorted(
        enriquecidos,
        key=lambda item: (
            str(item.get("data_referencia") or ""),
            int(item.get("id") or 0),
        ),
    )


def enriquecer_envio_apc(item: dict) -> dict:
    envio = dict(item or {})
    return {
        **envio,
        "id": int(envio.get("id") or 0),
        "periodo_id": int(envio.get("periodo_id") or 0),
        "professor_id": int(envio.get("professor_id") or 0),
        "turma_id": int(envio.get("turma_id") or 0),
        "turma_nome": str(envio.get("turma_nome") or "").strip(),
        "disciplina_id": int(envio.get("disciplina_id") or 0),
        "disciplina_nome": str(envio.get("disciplina_nome") or "").strip(),
        "arquivo_tamanho": int(envio.get("arquivo_tamanho") or 0),
        "arquivo_nome_original": str(envio.get("arquivo_nome_original") or "").strip(),
        "arquivo_tipo": str(envio.get("arquivo_tipo") or "").strip(),
        "arquivo_path": str(envio.get("arquivo_path") or "").strip(),
        "professor_nome": str(envio.get("professor_nome") or "").strip(),
        "professor_email": str(envio.get("professor_email") or "").strip(),
        "enviado_em": str(envio.get("enviado_em") or "").strip(),
        "atualizado_em": str(envio.get("atualizado_em") or "").strip(),
    }


def chave_entrega_apc(
    professor_id: int,
    turma_id: int | None = None,
    disciplina_id: int | None = None,
) -> tuple[int, int, int]:
    return (
        int(professor_id or 0),
        int(turma_id or 0),
        int(disciplina_id or 0),
    )


def agrupar_horarios_professor_dia(horarios: list[dict]) -> list[dict]:
    grupos: dict[tuple[int, int, int], dict] = {}
    for item in ordenar_horarios_escolares(horarios):
        professor_id = int(item.get("professor_id") or 0)
        turma_id = int(item.get("turma_id") or 0)
        disciplina_id = int(item.get("disciplina_id") or 0)
        if professor_id <= 0:
            continue
        if turma_id <= 0 or disciplina_id <= 0:
            continue

        chave = chave_entrega_apc(professor_id, turma_id, disciplina_id)

        grupo = grupos.setdefault(
            chave,
            {
                "professor_id": professor_id,
                "professor_nome": str(item.get("professor_nome") or "").strip(),
                "professor_email": str(item.get("professor_email") or "").strip(),
                "turma_id": turma_id,
                "turma_nome": str(item.get("turma_nome") or "").strip(),
                "disciplina_id": disciplina_id,
                "disciplina_nome": str(item.get("disciplina_nome") or "").strip(),
                "turmas": [],
                "disciplinas": [],
                "horarios": [],
            },
        )

        turma_nome = str(item.get("turma_nome") or "").strip()
        disciplina_nome = str(item.get("disciplina_nome") or "").strip()

        if turma_nome and turma_nome not in grupo["turmas"]:
            grupo["turmas"].append(turma_nome)
        if disciplina_nome and disciplina_nome not in grupo["disciplinas"]:
            grupo["disciplinas"].append(disciplina_nome)

        grupo["horarios"].append(
            {
                "registro_id": int(item.get("id") or 0),
                "aula_numero": int(item.get("aula_numero") or 0),
                "turma_id": int(item.get("turma_id") or 0),
                "turma_nome": turma_nome,
                "disciplina_id": int(item.get("disciplina_id") or 0),
                "disciplina_nome": disciplina_nome,
                "dia_semana": str(item.get("dia_semana") or "").strip(),
                "dia_semana_nome": str(item.get("dia_semana_nome") or "").strip(),
            }
        )

    itens = list(grupos.values())
    itens.sort(
        key=lambda item: (
            item["professor_nome"].casefold(),
            item["turma_nome"].casefold(),
            item["disciplina_nome"].casefold(),
            item["professor_id"],
            item["turma_id"],
            item["disciplina_id"],
        )
    )
    return itens


def agrupar_professores_elegiveis(professores: list[dict]) -> list[dict]:
    itens = []
    for item in sorted(
        [dict(item) for item in (professores or []) if int(item.get("id") or 0) > 0],
        key=lambda prof: (
            str(prof.get("nome") or "").casefold(),
            int(prof.get("id") or 0),
        ),
    ):
        itens.append(
            {
                "professor_id": int(item.get("id") or 0),
                "professor_nome": str(item.get("nome") or "").strip(),
                "professor_email": str(item.get("email") or "").strip(),
                "turma_id": 0,
                "turma_nome": "",
                "disciplina_id": 0,
                "disciplina_nome": "",
                "turmas": [],
                "disciplinas": [],
                "horarios": [],
            }
        )
    return itens


def montar_painel_periodo_apc(periodo: dict, elegiveis: list[dict], envios: list[dict]) -> dict:
    periodo_norm = enriquecer_periodo_apc(periodo)
    envios_por_professor = {
        chave_entrega_apc(
            int(item.get("professor_id") or 0),
            int(item.get("turma_id") or 0),
            int(item.get("disciplina_id") or 0),
        ): enriquecer_envio_apc(item)
        for item in (envios or [])
    }

    itens = []
    for item in elegiveis:
        envio = envios_por_professor.get(
            chave_entrega_apc(
                int(item["professor_id"]),
                int(item.get("turma_id") or 0),
                int(item.get("disciplina_id") or 0),
            )
        )
        itens.append(
            {
                **item,
                "total_aulas": len(item["horarios"]),
                "enviado": envio is not None,
                "envio": envio,
            }
        )

    return {
        "periodo": periodo_norm,
        "total_elegiveis": len(itens),
        "total_enviados": sum(1 for item in itens if item["enviado"]),
        "total_pendentes": sum(1 for item in itens if not item["enviado"]),
        "itens": itens,
    }


def montar_painel_professor_apc(
    periodo: dict,
    professor_id: int,
    elegiveis: list[dict],
    envios: list[dict] | None,
) -> dict | None:
    grupos = [
        item for item in (elegiveis or [])
        if int(item.get("professor_id") or 0) == int(professor_id)
    ]
    if not grupos:
        return None

    envios_por_chave = {
        chave_entrega_apc(
            int(item.get("professor_id") or 0),
            int(item.get("turma_id") or 0),
            int(item.get("disciplina_id") or 0),
        ): enriquecer_envio_apc(item)
        for item in (envios or [])
    }

    itens = []
    turmas: list[str] = []
    disciplinas: list[str] = []
    horarios: list[dict] = []

    for grupo in grupos:
        turma_nome = str(grupo.get("turma_nome") or "").strip()
        disciplina_nome = str(grupo.get("disciplina_nome") or "").strip()
        if turma_nome and turma_nome not in turmas:
            turmas.append(turma_nome)
        if disciplina_nome and disciplina_nome not in disciplinas:
            disciplinas.append(disciplina_nome)
        horarios.extend(list(grupo.get("horarios") or []))

        envio = envios_por_chave.get(
            chave_entrega_apc(
                int(grupo.get("professor_id") or 0),
                int(grupo.get("turma_id") or 0),
                int(grupo.get("disciplina_id") or 0),
            )
        )
        itens.append(
            {
                **grupo,
                "total_aulas": len(grupo["horarios"]),
                "enviado": envio is not None,
                "envio": envio,
            }
        )

    itens.sort(
        key=lambda item: (
            str(item.get("turma_nome") or "").casefold(),
            str(item.get("disciplina_nome") or "").casefold(),
            int(item.get("turma_id") or 0),
            int(item.get("disciplina_id") or 0),
        )
    )

    return {
        "periodo": enriquecer_periodo_apc(periodo),
        "professor_id": int(professor_id),
        "professor_nome": str(grupos[0].get("professor_nome") or "").strip(),
        "professor_email": str(grupos[0].get("professor_email") or "").strip(),
        "turmas": turmas,
        "disciplinas": disciplinas,
        "horarios": horarios,
        "total_aulas": len(horarios),
        "total_entregas": len(itens),
        "total_enviadas": sum(1 for item in itens if item["enviado"]),
        "total_pendentes": sum(1 for item in itens if not item["enviado"]),
        "envio": itens[0]["envio"] if len(itens) == 1 else None,
        "itens": itens,
    }


def sanitizar_nome_arquivo(nome_arquivo: str) -> str:
    nome_base = os.path.basename(nome_arquivo or "").strip().replace(" ", "_")
    nome_limpo = re.sub(r"[^A-Za-z0-9._-]", "_", nome_base)
    if not nome_limpo:
        return "documento.pdf"
    return nome_limpo


def _normalizar_trecho_nome_arquivo(texto: str, fallback: str) -> str:
    valor = str(texto or "").strip()
    valor = re.sub(r"\s+", " ", valor)
    valor = re.sub(r"[\\/:*?\"<>|]+", "-", valor)
    valor = valor.strip(" .-_")
    return valor or fallback


def nome_publico_arquivo_apc(
    titulo: str,
    professor_nome: str,
    data_referencia: str,
    nome_original: str,
) -> str:
    extensao = os.path.splitext(os.path.basename(str(nome_original or "").strip()))[1].strip()
    extensao = re.sub(r"[^A-Za-z0-9.]", "", extensao)
    if not extensao.startswith("."):
        extensao = f".{extensao}" if extensao else ""
    if not extensao:
        extensao = ".pdf"

    titulo_base = _normalizar_trecho_nome_arquivo(titulo, "Documento")
    professor_base = _normalizar_trecho_nome_arquivo(professor_nome, "Professor")
    data_base = normalizar_data_apc(data_referencia)
    return f"{titulo_base} - {professor_base} - {data_base}{extensao.lower()}"


def nome_arquivo_armazenado(
    periodo_id: int,
    professor_id: int,
    nome_original: str,
    *,
    turma_id: int = 0,
    disciplina_id: int = 0,
) -> str:
    nome_limpo = sanitizar_nome_arquivo(nome_original)
    return (
        f"apc_{int(periodo_id)}_{int(professor_id)}_"
        f"{int(turma_id or 0)}_{int(disciplina_id or 0)}_"
        f"{uuid.uuid4().hex}_{nome_limpo}"
    )


def contexto_apc_anos(anos_existentes: list[int] | None = None) -> list[int]:
    anos = set()
    agora = datetime.now().year
    anos.update({agora - 1, agora, agora + 1})
    for valor in anos_existentes or []:
        try:
            anos.add(validar_ano_letivo(valor))
        except ValueError:
            continue
    return sorted(anos)
