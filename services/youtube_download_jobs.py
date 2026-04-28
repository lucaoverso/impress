import logging
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

from services.youtube_download_service import (
    YoutubeDownloadError,
    baixar_arquivo,
    preparar_solicitacao_download,
    remover_arquivo_se_existir,
)

STATUS_DOWNLOAD_PENDENTE = "PENDENTE"
STATUS_DOWNLOAD_PROCESSANDO = "PROCESSANDO"
STATUS_DOWNLOAD_CONCLUIDO = "CONCLUIDO"
STATUS_DOWNLOAD_ERRO = "ERRO"
STATUS_DOWNLOAD_FINALIZADOS = {STATUS_DOWNLOAD_CONCLUIDO, STATUS_DOWNLOAD_ERRO}
_MAX_WORKERS_PADRAO = 2
_TTL_JOB_PADRAO_SEGUNDOS = 1800
_TTL_TICKET_PADRAO_SEGUNDOS = 120
logger = logging.getLogger(__name__)


def _resolver_env_int(nome: str, padrao: int, minimo: int) -> int:
    valor_bruto = str(os.getenv(nome, str(padrao)) or "").strip()
    try:
        valor = int(valor_bruto)
    except ValueError:
        return padrao
    return max(valor, minimo)


MAX_WORKERS_DOWNLOAD = _resolver_env_int(
    "YOUTUBE_DOWNLOAD_MAX_WORKERS",
    _MAX_WORKERS_PADRAO,
    1,
)
TTL_JOB_DOWNLOAD_SEGUNDOS = _resolver_env_int(
    "YOUTUBE_DOWNLOAD_JOB_TTL_SECONDS",
    _TTL_JOB_PADRAO_SEGUNDOS,
    60,
)
TTL_TICKET_DOWNLOAD_SEGUNDOS = _resolver_env_int(
    "YOUTUBE_DOWNLOAD_TICKET_TTL_SECONDS",
    _TTL_TICKET_PADRAO_SEGUNDOS,
    30,
)
_EXECUTOR = ThreadPoolExecutor(
    max_workers=MAX_WORKERS_DOWNLOAD,
    thread_name_prefix="youtube-download",
)
_JOBS: dict[str, dict] = {}
_TICKETS: dict[str, dict] = {}
_LOCK = threading.Lock()


class YoutubeDownloadJobError(RuntimeError):
    pass


class YoutubeDownloadJobNotFoundError(YoutubeDownloadJobError):
    pass


class YoutubeDownloadJobNotReadyError(YoutubeDownloadJobError):
    pass


class YoutubeDownloadTicketInvalidError(YoutubeDownloadJobError):
    pass


def _agora_ts() -> float:
    return time.time()


def _agora_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _ts_para_iso(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _mensagem_status(job: dict) -> str:
    status = str(job.get("status") or "").upper()
    if status == STATUS_DOWNLOAD_PENDENTE:
        return "Download entrou na fila do servidor."
    if status == STATUS_DOWNLOAD_PROCESSANDO:
        return "Preparando arquivo para download."
    if status == STATUS_DOWNLOAD_CONCLUIDO:
        return "Arquivo pronto para baixar."

    erro = str(job.get("erro_mensagem") or "").strip()
    if erro:
        return erro
    return "O download falhou."


def _job_publico(job: dict) -> dict:
    payload = {
        "id": job["id"],
        "status": job["status"],
        "url": job["url"],
        "formato": job["formato"],
        "qualidade": job.get("qualidade"),
        "arquivo_nome": job.get("arquivo_nome"),
        "media_type": job.get("media_type"),
        "erro_mensagem": job.get("erro_mensagem"),
        "criado_em": job["criado_em"],
        "atualizado_em": job["atualizado_em"],
        "mensagem_status": _mensagem_status(job),
        "pronto": job["status"] == STATUS_DOWNLOAD_CONCLUIDO and bool(job.get("arquivo_path")),
    }
    if payload["pronto"]:
        payload["download_url"] = f"/download/jobs/{job['id']}/arquivo"
    return payload


def _atualizar_job(job: dict, **campos):
    job.update(campos)
    job["atualizado_em"] = _agora_iso()
    job["updated_ts"] = _agora_ts()


def _job_expirado(job: dict, agora: float) -> bool:
    if job.get("status") not in STATUS_DOWNLOAD_FINALIZADOS:
        return False
    return (agora - float(job.get("updated_ts") or 0.0)) >= TTL_JOB_DOWNLOAD_SEGUNDOS


def _limpar_jobs_expirados_locked():
    agora = _agora_ts()
    removidos = []
    for job_id, job in _JOBS.items():
        if not _job_expirado(job, agora):
            continue
        removidos.append((job_id, job.get("arquivo_path")))

    for job_id, arquivo_path in removidos:
        _JOBS.pop(job_id, None)
        for ticket_id, ticket in list(_TICKETS.items()):
            if ticket.get("job_id") == job_id:
                _TICKETS.pop(ticket_id, None)
        if arquivo_path:
            remover_arquivo_se_existir(Path(arquivo_path))


def _limpar_tickets_expirados_locked():
    agora = _agora_ts()
    for ticket_id, ticket in list(_TICKETS.items()):
        if float(ticket.get("expira_ts") or 0.0) <= agora:
            _TICKETS.pop(ticket_id, None)


def _buscar_job_reutilizavel_locked(usuario_id: int, url: str, formato: str, qualidade: str | None) -> dict | None:
    for job in _JOBS.values():
        if int(job["usuario_id"]) != int(usuario_id):
            continue
        if job["url"] != url or job["formato"] != formato or job.get("qualidade") != qualidade:
            continue
        if job["status"] in {STATUS_DOWNLOAD_PENDENTE, STATUS_DOWNLOAD_PROCESSANDO}:
            return job
        if job["status"] == STATUS_DOWNLOAD_CONCLUIDO and job.get("arquivo_path"):
            caminho = Path(job["arquivo_path"])
            if caminho.exists():
                return job
    return None


def _obter_job_do_usuario_locked(job_id: str, usuario_id: int) -> dict:
    job = _JOBS.get(str(job_id))
    if job is None or int(job["usuario_id"]) != int(usuario_id):
        raise YoutubeDownloadJobNotFoundError("Download nao encontrado.")
    return job


def _processar_job(job_id: str):
    with _LOCK:
        job = _JOBS.get(job_id)
        if job is None:
            return
        _atualizar_job(job, status=STATUS_DOWNLOAD_PROCESSANDO, erro_mensagem=None)
        payload = {
            "url": job["url"],
            "formato": job["formato"],
            "qualidade": job.get("qualidade"),
        }

    try:
        caminho, nome_arquivo, media_type = baixar_arquivo(
            payload["url"],
            payload["formato"],
            payload["qualidade"],
        )
    except YoutubeDownloadError as exc:
        with _LOCK:
            job = _JOBS.get(job_id)
            if job is not None:
                _atualizar_job(
                    job,
                    status=STATUS_DOWNLOAD_ERRO,
                    erro_mensagem=str(exc),
                    arquivo_path=None,
                    arquivo_nome=None,
                    media_type=None,
                )
        return
    except Exception:
        logger.exception("Falha inesperada ao processar job de download %s", job_id)
        with _LOCK:
            job = _JOBS.get(job_id)
            if job is not None:
                _atualizar_job(
                    job,
                    status=STATUS_DOWNLOAD_ERRO,
                    erro_mensagem="Falha inesperada ao preparar o download.",
                    arquivo_path=None,
                    arquivo_nome=None,
                    media_type=None,
                )
        return

    with _LOCK:
        job = _JOBS.get(job_id)
        if job is None:
            remover_arquivo_se_existir(caminho)
            return
        _atualizar_job(
            job,
            status=STATUS_DOWNLOAD_CONCLUIDO,
            erro_mensagem=None,
            arquivo_path=str(caminho),
            arquivo_nome=nome_arquivo,
            media_type=media_type,
        )


def criar_job_download(usuario_id: int, url: str, formato: str, qualidade: str | None = None) -> dict:
    url_validada, formato_limpo, qualidade_limpa = preparar_solicitacao_download(url, formato, qualidade)

    with _LOCK:
        _limpar_jobs_expirados_locked()
        job_existente = _buscar_job_reutilizavel_locked(
            int(usuario_id),
            url_validada,
            formato_limpo,
            qualidade_limpa,
        )
        if job_existente is not None:
            return deepcopy(_job_publico(job_existente))

        job_id = uuid.uuid4().hex
        job = {
            "id": job_id,
            "usuario_id": int(usuario_id),
            "url": url_validada,
            "formato": formato_limpo,
            "qualidade": qualidade_limpa,
            "status": STATUS_DOWNLOAD_PENDENTE,
            "erro_mensagem": None,
            "arquivo_path": None,
            "arquivo_nome": None,
            "media_type": None,
            "criado_em": _agora_iso(),
            "atualizado_em": _agora_iso(),
            "updated_ts": _agora_ts(),
        }
        _JOBS[job_id] = job

    try:
        _EXECUTOR.submit(_processar_job, job_id)
    except Exception:
        with _LOCK:
            job = _JOBS.get(job_id)
            if job is not None:
                _atualizar_job(
                    job,
                    status=STATUS_DOWNLOAD_ERRO,
                    erro_mensagem="Nao foi possivel iniciar o processamento do download.",
                )
                return deepcopy(_job_publico(job))
        raise

    with _LOCK:
        return deepcopy(_job_publico(_JOBS[job_id]))


def obter_job_download(job_id: str, usuario_id: int) -> dict:
    with _LOCK:
        _limpar_jobs_expirados_locked()
        job = _obter_job_do_usuario_locked(job_id, int(usuario_id))
        if job["status"] == STATUS_DOWNLOAD_CONCLUIDO and job.get("arquivo_path"):
            if not Path(job["arquivo_path"]).exists():
                _atualizar_job(
                    job,
                    status=STATUS_DOWNLOAD_ERRO,
                    erro_mensagem="O arquivo expirou ou nao esta mais disponivel.",
                    arquivo_path=None,
                    arquivo_nome=None,
                    media_type=None,
                )
        return deepcopy(_job_publico(job))


def obter_arquivo_job_download(job_id: str, usuario_id: int) -> tuple[Path, str, str]:
    with _LOCK:
        _limpar_jobs_expirados_locked()
        job = _obter_job_do_usuario_locked(job_id, int(usuario_id))

        if job["status"] != STATUS_DOWNLOAD_CONCLUIDO or not job.get("arquivo_path"):
            raise YoutubeDownloadJobNotReadyError("O arquivo ainda esta sendo preparado.")

        caminho = Path(job["arquivo_path"])
        nome_arquivo = str(job.get("arquivo_nome") or caminho.name)
        media_type = str(job.get("media_type") or "application/octet-stream")

    if not caminho.exists():
        with _LOCK:
            job = _JOBS.get(str(job_id))
            if job is not None:
                _atualizar_job(
                    job,
                    status=STATUS_DOWNLOAD_ERRO,
                    erro_mensagem="O arquivo expirou ou nao esta mais disponivel.",
                    arquivo_path=None,
                    arquivo_nome=None,
                    media_type=None,
                )
        raise YoutubeDownloadJobNotFoundError("O arquivo expirou ou nao esta mais disponivel.")

    return caminho, nome_arquivo, media_type


def criar_ticket_download(job_id: str, usuario_id: int) -> dict:
    with _LOCK:
        _limpar_jobs_expirados_locked()
        _limpar_tickets_expirados_locked()
        job = _obter_job_do_usuario_locked(job_id, int(usuario_id))
        if job["status"] != STATUS_DOWNLOAD_CONCLUIDO or not job.get("arquivo_path"):
            raise YoutubeDownloadJobNotReadyError("O arquivo ainda esta sendo preparado.")

        caminho = Path(job["arquivo_path"])
        if not caminho.exists():
            _atualizar_job(
                job,
                status=STATUS_DOWNLOAD_ERRO,
                erro_mensagem="O arquivo expirou ou nao esta mais disponivel.",
                arquivo_path=None,
                arquivo_nome=None,
                media_type=None,
            )
            raise YoutubeDownloadJobNotFoundError("O arquivo expirou ou nao esta mais disponivel.")

        ticket = uuid.uuid4().hex
        expira_ts = _agora_ts() + TTL_TICKET_DOWNLOAD_SEGUNDOS
        _TICKETS[ticket] = {
            "ticket": ticket,
            "job_id": str(job_id),
            "usuario_id": int(usuario_id),
            "expira_ts": expira_ts,
            "criado_em": _agora_iso(),
        }
        return {
            "ticket": ticket,
            "arquivo_nome": str(job.get("arquivo_nome") or caminho.name),
            "download_url": f"/download/jobs/{job_id}/arquivo?ticket={ticket}",
            "expira_em": _ts_para_iso(expira_ts),
        }


def validar_ticket_download(job_id: str, ticket: str) -> int:
    with _LOCK:
        _limpar_jobs_expirados_locked()
        _limpar_tickets_expirados_locked()
        ticket_info = _TICKETS.get(str(ticket))
        if ticket_info is None or str(ticket_info.get("job_id")) != str(job_id):
            raise YoutubeDownloadTicketInvalidError("Ticket de download invalido ou expirado.")

        job = _JOBS.get(str(job_id))
        if job is None or job.get("arquivo_path") is None:
            raise YoutubeDownloadTicketInvalidError("Ticket de download invalido ou expirado.")

        return int(ticket_info["usuario_id"])
