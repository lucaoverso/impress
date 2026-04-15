from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from auth import get_usuario_logado
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


@router.post("/download/info")
def obter_info_download(payload: YoutubeInfoIn, _usuario=Depends(get_usuario_logado)):
    try:
        return obter_info_video(payload.url)
    except YoutubeDownloadError as exc:
        raise HTTPException(400, str(exc)) from exc


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
