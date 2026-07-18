import re
import sqlite3
import uuid
from pathlib import Path

from fastapi import HTTPException

from modules.printing import repository
from modules.printing.jobs import (
    cancel_print_job,
    copy_job_pdf_to_spool,
    create_job_from_ready_pdf,
    get_job_with_access,
    read_reusable_job_pdf_content,
    reprint_job_from_history,
)
from modules.printing.policies import (
    TAGS_IMPRESSAO_DISPONIVEIS,
    build_cups_options,
    build_print_status_alert,
    count_interval_pages,
    ensure_print_is_available,
    extract_job_tags,
    normalize_print_tags,
    print_job_can_be_reused,
    resolve_job_pdf_path,
    resolve_print_tags,
    sanitize_file_name,
    serialize_print_job,
    validate_print_parameters,
    validate_required_tags,
)


class PrinterConflictError(Exception):
    pass


class PrinterNotFoundError(Exception):
    pass


def prepare_uploaded_file_for_print(
    *,
    nome_arquivo: str,
    conteudo_arquivo: bytes,
    spool_dir: Path,
    obter_extensao_arquivo,
    converter_para_pdf,
    remover_arquivo_se_existir,
):
    if not conteudo_arquivo:
        raise HTTPException(400, "Arquivo vazio")

    extensao_arquivo = obter_extensao_arquivo(nome_arquivo)
    nome_arquivo_spool = f"{uuid.uuid4().hex}_{sanitize_file_name(nome_arquivo)}"
    caminho_arquivo_original = spool_dir / nome_arquivo_spool

    try:
        with caminho_arquivo_original.open("wb") as destino:
            destino.write(conteudo_arquivo)
    except OSError as exc:
        raise HTTPException(500, "Falha ao armazenar o arquivo para impressão.") from exc

    caminho_arquivo = caminho_arquivo_original
    caminho_convertido = caminho_arquivo_original.with_suffix(".pdf")
    try:
        caminho_arquivo = converter_para_pdf(caminho_arquivo_original, extensao_arquivo)
    except ValueError as exc:
        remover_arquivo_se_existir(caminho_arquivo_original)
        raise HTTPException(400, str(exc)) from exc
    except RuntimeError as exc:
        remover_arquivo_se_existir(caminho_arquivo_original)
        if caminho_convertido != caminho_arquivo_original:
            remover_arquivo_se_existir(caminho_convertido)
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        remover_arquivo_se_existir(caminho_arquivo_original)
        if caminho_convertido != caminho_arquivo_original:
            remover_arquivo_se_existir(caminho_convertido)
        raise HTTPException(500, "Falha ao preparar o arquivo para impressão.") from exc

    if caminho_arquivo != caminho_arquivo_original:
        remover_arquivo_se_existir(caminho_arquivo_original)

    return {
        "extensao_arquivo": extensao_arquivo,
        "caminho_arquivo": caminho_arquivo,
    }


def prepare_uploaded_file_for_preview(
    *,
    nome_arquivo: str,
    conteudo_arquivo: bytes,
    spool_dir: Path,
    obter_extensao_arquivo,
    converter_para_pdf,
    remover_arquivo_se_existir,
):
    if not conteudo_arquivo:
        raise HTTPException(400, "Arquivo vazio")

    extensao_arquivo = obter_extensao_arquivo(nome_arquivo)
    nome_arquivo_spool = f"preview_{uuid.uuid4().hex}_{sanitize_file_name(nome_arquivo)}"
    caminho_arquivo_original = spool_dir / nome_arquivo_spool

    try:
        with caminho_arquivo_original.open("wb") as destino:
            destino.write(conteudo_arquivo)
    except OSError as exc:
        raise HTTPException(500, "Falha ao armazenar arquivo para pré-visualização.") from exc

    caminho_arquivo_pdf = caminho_arquivo_original
    caminho_convertido = caminho_arquivo_original.with_suffix(".pdf")

    try:
        caminho_arquivo_pdf = converter_para_pdf(caminho_arquivo_original, extensao_arquivo)
        conteudo_pdf = caminho_arquivo_pdf.read_bytes()
        if not conteudo_pdf:
            raise HTTPException(500, "Falha ao gerar PDF de pré-visualização.")
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, "Falha ao gerar pré-visualização do documento.") from exc
    finally:
        remover_arquivo_se_existir(caminho_arquivo_original)
        if caminho_convertido != caminho_arquivo_original:
            remover_arquivo_se_existir(caminho_convertido)

    return {
        "extensao_arquivo": extensao_arquivo,
        "conteudo_pdf": conteudo_pdf,
    }


def list_formatted_print_classes():
    turmas = []
    estudantes_ativos_por_turma = repository.count_active_students_by_class()
    for turma in repository.list_active_classes():
        turma_id = int(turma["id"])
        quantidade_cadastrada = max(int(turma.get("quantidade_estudantes") or 0), 0)
        turmas.append(
            {
                "id": turma_id,
                "nome": turma["nome"],
                "turno": str(turma.get("turno") or "").strip().upper(),
                "quantidade_estudantes": estudantes_ativos_por_turma.get(
                    turma_id,
                    quantidade_cadastrada,
                ),
            }
        )
    return turmas


def list_print_tags():
    return [{"id": item, "label": item} for item in TAGS_IMPRESSAO_DISPONIVEIS]


def get_formatted_print_status():
    return build_print_status_alert(repository.get_print_status())


def list_serialized_jobs_for_user(usuario_id: int, spool_dir: Path | None = None):
    return [
        serialize_print_job(job, spool_dir=spool_dir)
        for job in repository.list_jobs_by_user(usuario_id)
    ]


def get_print_quota_response(usuario_consulta: dict, obter_cota_atual, usuario_tem_cota_ilimitada):
    if usuario_tem_cota_ilimitada(usuario_consulta):
        return {
            "limite": None,
            "usadas": 0,
            "restante": None,
            "ilimitada": True,
        }

    cota = obter_cota_atual(usuario_consulta["id"])
    cota["ilimitada"] = False
    return cota


def normalize_printer_name(name: str) -> str:
    normalized = str(name or "").strip()
    if not normalized:
        raise HTTPException(400, "Informe o nome exato da impressora no CUPS.")
    if len(normalized) > 128 or not re.fullmatch(r"[A-Za-z0-9._-]+", normalized):
        raise HTTPException(400, "Nome CUPS inválido. Use letras, números, ponto, hífen ou sublinhado.")
    return normalized


def list_registered_printers(*, include_inactive: bool = False):
    return repository.list_printers(include_inactive=include_inactive)


def create_registered_printer(name: str):
    try:
        return repository.create_printer(normalize_printer_name(name))
    except sqlite3.IntegrityError as exc:
        raise PrinterConflictError("Essa impressora já está cadastrada.") from exc


def update_registered_printer_status(printer_id: int, active: bool) -> None:
    if not repository.update_printer_status(printer_id, active):
        raise PrinterNotFoundError("Impressora não encontrada.")


def delete_registered_printer(printer_id: int) -> None:
    if not repository.delete_printer(printer_id):
        raise PrinterNotFoundError("Impressora não encontrada.")


def list_available_printers(default_printer_name: str = ""):
    printers = repository.list_printers()
    fallback = str(default_printer_name or "").strip()
    if not printers and fallback:
        return [{"id": 0, "name": fallback, "active": 1, "source": "environment"}]
    return printers


def resolve_active_printer(name: str, default_printer_name: str = "") -> str:
    requested = str(name or "").strip()
    active_printers = repository.list_printers()
    if active_printers:
        selected = next(
            (item for item in active_printers if item["name"].casefold() == requested.casefold()),
            None,
        )
        if not selected:
            raise HTTPException(400, "Selecione uma impressora ativa cadastrada.")
        return selected["name"]
    fallback = str(default_printer_name or "").strip()
    if fallback and (not requested or requested.casefold() == fallback.casefold()):
        return fallback
    raise HTTPException(503, "Nenhuma impressora ativa foi cadastrada.")
