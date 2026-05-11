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


def validar_mes_referencia(valor: str) -> str:
    try:
        return datetime.strptime(str(valor or "").strip(), "%Y-%m").strftime("%Y-%m")
    except ValueError as exc:
        raise ValueError("Mes invalido. Use o formato YYYY-MM.") from exc


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
        raise ValueError("Data invalida. Use o formato YYYY-MM-DD.") from exc


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
    raise ValueError("Prazo invalido. Use o formato YYYY-MM-DDTHH:MM.")


def normalizar_prazo_envio(data_referencia: str, prazo_envio: str = "") -> str:
    data_norm = normalizar_data_apc(data_referencia)
    texto = str(prazo_envio or "").strip()
    if not texto:
        return f"{data_norm} 23:59:00"

    prazo = _parse_datetime_local(texto)
    if prazo.date().isoformat() < data_norm:
        raise ValueError("O prazo de envio nao pode ser anterior a data da APC.")
    return prazo.strftime("%Y-%m-%d %H:%M:%S")


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
        "titulo": str(periodo.get("titulo") or "APC").strip() or "APC",
        "observacao": str(periodo.get("observacao") or "").strip(),
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
        "arquivo_tamanho": int(envio.get("arquivo_tamanho") or 0),
        "arquivo_nome_original": str(envio.get("arquivo_nome_original") or "").strip(),
        "arquivo_tipo": str(envio.get("arquivo_tipo") or "").strip(),
        "arquivo_path": str(envio.get("arquivo_path") or "").strip(),
        "professor_nome": str(envio.get("professor_nome") or "").strip(),
        "professor_email": str(envio.get("professor_email") or "").strip(),
        "enviado_em": str(envio.get("enviado_em") or "").strip(),
        "atualizado_em": str(envio.get("atualizado_em") or "").strip(),
    }


def agrupar_horarios_professor_dia(horarios: list[dict]) -> list[dict]:
    grupos: dict[int, dict] = {}
    for item in ordenar_horarios_escolares(horarios):
        professor_id = int(item.get("professor_id") or 0)
        if professor_id <= 0:
            continue

        grupo = grupos.setdefault(
            professor_id,
            {
                "professor_id": professor_id,
                "professor_nome": str(item.get("professor_nome") or "").strip(),
                "professor_email": str(item.get("professor_email") or "").strip(),
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
    itens.sort(key=lambda item: (item["professor_nome"].casefold(), item["professor_id"]))
    return itens


def montar_painel_periodo_apc(periodo: dict, horarios: list[dict], envios: list[dict]) -> dict:
    periodo_norm = enriquecer_periodo_apc(periodo)
    elegiveis = agrupar_horarios_professor_dia(horarios)
    envios_por_professor = {
        int(item.get("professor_id") or 0): enriquecer_envio_apc(item) for item in (envios or [])
    }

    itens = []
    for item in elegiveis:
        envio = envios_por_professor.get(int(item["professor_id"]))
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
    horarios: list[dict],
    envio: dict | None,
) -> dict | None:
    grupos = {
        int(item["professor_id"]): item for item in agrupar_horarios_professor_dia(horarios)
    }
    grupo = grupos.get(int(professor_id))
    if not grupo:
        return None

    return {
        "periodo": enriquecer_periodo_apc(periodo),
        "professor_id": int(professor_id),
        "professor_nome": grupo["professor_nome"],
        "professor_email": grupo["professor_email"],
        "turmas": grupo["turmas"],
        "disciplinas": grupo["disciplinas"],
        "horarios": grupo["horarios"],
        "total_aulas": len(grupo["horarios"]),
        "envio": enriquecer_envio_apc(envio) if envio else None,
    }


def sanitizar_nome_arquivo(nome_arquivo: str) -> str:
    nome_base = os.path.basename(nome_arquivo or "").strip().replace(" ", "_")
    nome_limpo = re.sub(r"[^A-Za-z0-9._-]", "_", nome_base)
    if not nome_limpo:
        return "apc.pdf"
    return nome_limpo


def nome_arquivo_armazenado(periodo_id: int, professor_id: int, nome_original: str) -> str:
    nome_limpo = sanitizar_nome_arquivo(nome_original)
    return f"apc_{int(periodo_id)}_{int(professor_id)}_{uuid.uuid4().hex}_{nome_limpo}"


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
