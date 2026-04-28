from pydantic import BaseModel

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from auth import get_usuario_logado
from services.auth_service import validar_token
from services.youtube_download_jobs import (
    YoutubeDownloadJobNotFoundError,
    YoutubeDownloadJobNotReadyError,
    YoutubeDownloadTicketInvalidError,
    criar_job_download,
    criar_ticket_download,
    obter_arquivo_job_download,
    obter_job_download,
    validar_ticket_download,
)
from services.youtube_download_service import (
    YoutubeDownloadError,
    baixar_arquivo,
    obter_info_video,
    remover_arquivo_se_existir,
)

router = APIRouter()


class YoutubeInfoIn(BaseModel):
    url: str


class YoutubeDownloadIn(BaseModel):
    url: str
    formato: str
    qualidade: str | None = None


def _resolver_usuario_download(job_id: str, authorization: str | None, ticket: str | None) -> int:
    if ticket:
        try:
            return validar_ticket_download(job_id, ticket)
        except YoutubeDownloadTicketInvalidError as exc:
            raise HTTPException(403, str(exc)) from exc

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Token invalido")

    usuario = validar_token(authorization.replace("Bearer ", ""))
    if not usuario:
        raise HTTPException(401, "Token invalido")
    return int(usuario["id"])


@router.post("/download/info")
def obter_info_download(payload: YoutubeInfoIn, _usuario=Depends(get_usuario_logado)):
    try:
        return obter_info_video(payload.url)
    except YoutubeDownloadError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/download/jobs")
def criar_download_job_api(payload: YoutubeDownloadIn, usuario=Depends(get_usuario_logado)):
    try:
        return criar_job_download(
            int(usuario["id"]),
            payload.url,
            payload.formato,
            payload.qualidade,
        )
    except YoutubeDownloadError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/download/jobs/{job_id}")
def obter_download_job_api(job_id: str, usuario=Depends(get_usuario_logado)):
    try:
        return obter_job_download(job_id, int(usuario["id"]))
    except YoutubeDownloadJobNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/download/jobs/{job_id}/ticket")
def criar_ticket_download_api(job_id: str, usuario=Depends(get_usuario_logado)):
    try:
        return criar_ticket_download(job_id, int(usuario["id"]))
    except YoutubeDownloadJobNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except YoutubeDownloadJobNotReadyError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.get("/download/jobs/{job_id}/arquivo")
def baixar_arquivo_job_api(
    job_id: str,
    authorization: str | None = Header(None),
    ticket: str | None = None,
):
    usuario_id = _resolver_usuario_download(job_id, authorization, ticket)
    try:
        caminho, nome_arquivo, media_type = obter_arquivo_job_download(job_id, usuario_id)
    except YoutubeDownloadJobNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except YoutubeDownloadJobNotReadyError as exc:
        raise HTTPException(409, str(exc)) from exc

    return FileResponse(
        path=str(caminho),
        filename=nome_arquivo,
        media_type=media_type,
    )


@router.post("/download/arquivo")
def baixar_video_youtube(payload: YoutubeDownloadIn, _usuario=Depends(get_usuario_logado)):
    try:
        caminho, nome_arquivo, media_type = baixar_arquivo(
            payload.url,
            payload.formato,
            payload.qualidade,
        )
    except YoutubeDownloadError as exc:
        raise HTTPException(400, str(exc)) from exc

    return FileResponse(
        path=str(caminho),
        filename=nome_arquivo,
        media_type=media_type,
        background=BackgroundTask(remover_arquivo_se_existir, caminho),
    )
