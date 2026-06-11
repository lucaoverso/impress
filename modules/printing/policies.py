import json
import os
import re
from pathlib import Path

from fastapi import HTTPException

TAGS_IMPRESSAO_DISPONIVEIS = (
    "Prova bimestral",
    "Trabalho avaliativo",
    "Lista de exercicios",
    "Recuperação",
    "Simulado",
    "Material de apoio",
    "Comunicado",
    "Registro",
    "CAED",
)


def count_interval_pages(intervalo: str, total_paginas: int) -> int:
    if not intervalo or not intervalo.strip():
        return total_paginas

    paginas = set()
    partes = [p.strip() for p in intervalo.split(",") if p.strip()]

    for parte in partes:
        if "-" in parte:
            pedacos = [n.strip() for n in parte.split("-")]
            if len(pedacos) != 2:
                raise HTTPException(400, f'Intervalo invalido: "{parte}"')
            inicio, fim = pedacos
            if not inicio.isdigit() or not fim.isdigit():
                raise HTTPException(400, f'Intervalo invalido: "{parte}"')
            inicio_num = int(inicio)
            fim_num = int(fim)
            if inicio_num <= 0 or fim_num <= 0 or inicio_num > fim_num:
                raise HTTPException(400, f'Intervalo invalido: "{parte}"')
            if fim_num > total_paginas:
                raise HTTPException(400, f"Pagina {fim_num} nao existe no documento")
            for pagina in range(inicio_num, fim_num + 1):
                paginas.add(pagina)
        else:
            if not parte.isdigit():
                raise HTTPException(400, f'Pagina invalida: "{parte}"')
            pagina = int(parte)
            if pagina <= 0 or pagina > total_paginas:
                raise HTTPException(400, f"Pagina {pagina} nao existe no documento")
            paginas.add(pagina)

    if not paginas:
        raise HTTPException(400, "Nenhuma pagina valida informada")

    return len(paginas)


def sanitize_file_name(nome_arquivo: str) -> str:
    nome_base = os.path.basename(nome_arquivo or "").strip().replace(" ", "_")
    nome_limpo = re.sub(r"[^A-Za-z0-9._-]", "_", nome_base)
    if not nome_limpo:
        return "documento.pdf"
    if "." not in nome_limpo:
        return f"{nome_limpo}.pdf"
    return nome_limpo


def get_two_up_layout(orientacao: str) -> str:
    if orientacao == "retrato":
        return "tblr"
    return "lrtb"


def build_cups_options(
    paginas_por_folha: int,
    duplex: bool,
    orientacao: str,
    intervalo_paginas: str,
):
    if duplex:
        sides = "two-sided-short-edge" if orientacao == "paisagem" else "two-sided-long-edge"
    else:
        sides = "one-sided"

    orientacao_cups = 4 if orientacao == "paisagem" else 3
    opcoes = {
        "number-up": paginas_por_folha,
        "sides": sides,
        "orientation-requested": orientacao_cups,
    }

    if orientacao == "paisagem":
        opcoes["landscape"] = True

    if paginas_por_folha == 2:
        opcoes["number-up-layout"] = get_two_up_layout(orientacao)

    intervalo = (intervalo_paginas or "").strip()
    if intervalo:
        opcoes["page-ranges"] = intervalo

    return opcoes


def build_print_status_alert(status: dict) -> dict:
    mensagem = str(status.get("mensagem") or "").strip()
    if not mensagem:
        mensagem = "Impressao indisponivel no momento: a escola esta sem papel."
    return {
        "sem_papel": bool(status.get("sem_papel")),
        "mensagem": mensagem,
        "atualizado_em": status.get("atualizado_em") or "",
    }


def ensure_print_is_available(alerta: dict):
    if alerta["sem_papel"]:
        raise HTTPException(409, alerta["mensagem"])


def validate_print_parameters(copias: int, paginas_por_folha: int, orientacao: str):
    if copias <= 0:
        raise HTTPException(400, "Quantidade invalida")
    if paginas_por_folha not in (1, 2, 4):
        raise HTTPException(400, "Paginacao por folha invalida")
    if orientacao not in ("retrato", "paisagem"):
        raise HTTPException(400, "Orientacao invalida")


def normalize_print_tags(tags: list[str] | None) -> list[str]:
    if tags is None:
        return []

    if isinstance(tags, str):
        tags_iteraveis = [tags]
    elif isinstance(tags, (list, tuple, set)):
        tags_iteraveis = list(tags)
    else:
        return []

    catalogo = {item.casefold(): item for item in TAGS_IMPRESSAO_DISPONIVEIS}
    tags_normalizadas = []
    vistos = set()
    for item in tags_iteraveis:
        tag = str(item or "").strip()
        if not tag:
            continue
        chave = tag.casefold()
        if chave not in catalogo:
            raise HTTPException(400, f"Tag de impressao invalida: {tag}")
        if chave in vistos:
            continue
        vistos.add(chave)
        tags_normalizadas.append(catalogo[chave])
    return tags_normalizadas


def extract_job_tags(job: dict | None) -> list[str]:
    try:
        tags = json.loads(str((job or {}).get("tags_json") or "[]"))
    except (TypeError, ValueError, json.JSONDecodeError):
        return []

    if not isinstance(tags, list):
        return []

    return [str(item).strip() for item in tags if str(item or "").strip()]


def resolve_print_tags(tags: list[str] | None, job_base: dict | None = None) -> list[str]:
    tags_normalizadas = normalize_print_tags(tags)
    if tags_normalizadas:
        return tags_normalizadas
    if job_base:
        return extract_job_tags(job_base)
    return []


def validate_required_tags(tags: list[str] | None):
    if tags:
        return
    raise HTTPException(400, "Selecione ao menos uma tag para identificar a impressao.")


def serialize_print_job(job: dict, spool_dir: Path | None = None) -> dict:
    payload = dict(job)
    payload["tags"] = extract_job_tags(job)
    payload["pode_reutilizar"] = False
    payload["motivo_reuso_indisponivel"] = ""

    if not print_job_can_be_reused(job):
        payload["motivo_reuso_indisponivel"] = "Apenas impressoes concluidas podem ser reutilizadas."
        return payload

    if spool_dir is None:
        payload["pode_reutilizar"] = True
        return payload

    try:
        resolve_job_pdf_path(job, spool_dir)
    except HTTPException as exc:
        payload["motivo_reuso_indisponivel"] = str(exc.detail)
    else:
        payload["pode_reutilizar"] = True

    return payload


def print_job_can_be_reused(job: dict) -> bool:
    status = str(job.get("status") or "").strip().upper()
    return status in {"CONCLUIDO", "FINALIZADO"}


def resolve_job_pdf_path(job: dict, spool_dir: Path) -> Path:
    arquivo_path = str(job.get("arquivo_path") or "").strip()
    if not arquivo_path:
        raise HTTPException(404, "Este job nao possui arquivo disponivel para reutilizacao.")

    caminho_spool = spool_dir.resolve(strict=False)
    caminho_job = Path(arquivo_path).resolve(strict=False)
    try:
        caminho_job.relative_to(caminho_spool)
    except ValueError as exc:
        raise HTTPException(409, "O arquivo vinculado a este job esta fora do spool configurado.") from exc

    if not caminho_job.exists() or not caminho_job.is_file():
        raise HTTPException(404, "O arquivo deste job nao esta mais disponivel no spool.")

    return caminho_job
