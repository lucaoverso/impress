import os
import re
import shutil
import ssl
import subprocess
import uuid
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen as urllib_urlopen

BASE_DIR = Path(__file__).resolve().parent.parent
DOWNLOAD_DIR = Path(os.getenv("SPOOL_DIR", str(BASE_DIR / "spool"))) / "youtube"
URL_REGEX = re.compile(r"^https?://", re.IGNORECASE)
QUALIDADES_MP4_FIXAS = (
    ("720p", "720p"),
    ("1080p", "1080p"),
    ("2160p", "2160p (4K)"),
)


class YoutubeDownloadError(RuntimeError):
    pass


def remover_arquivo_se_existir(caminho: Path):
    try:
        caminho.unlink()
    except FileNotFoundError:
        return
    except OSError:
        return


def garantir_diretorio_download() -> Path:
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    return DOWNLOAD_DIR


def validar_url_youtube(url: str) -> str:
    url_limpa = str(url or "").strip()
    if not url_limpa or not URL_REGEX.match(url_limpa):
        raise YoutubeDownloadError("Cole um link valido do YouTube para continuar.")
    return url_limpa


def sanitizar_nome_arquivo(nome: str) -> str:
    nome_limpo = re.sub(r"[^\w.\- ]+", "", str(nome or "").strip(), flags=re.ASCII)
    nome_limpo = re.sub(r"\s+", " ", nome_limpo).strip().replace(" ", "_")
    return nome_limpo[:120] or "youtube_video"


def formatar_duracao(segundos: int | None) -> str:
    total = max(int(segundos or 0), 0)
    horas, resto = divmod(total, 3600)
    minutos, segundos_restantes = divmod(resto, 60)
    if horas:
        return f"{horas:02d}:{minutos:02d}:{segundos_restantes:02d}"
    return f"{minutos:02d}:{segundos_restantes:02d}"


def ffmpeg_disponivel() -> bool:
    return shutil.which("ffmpeg") is not None


def normalizar_qualidade_mp4(qualidade: str | None) -> str:
    qualidade_limpa = str(qualidade or "").strip().lower()
    qualidades_validas = {valor for valor, _rotulo in QUALIDADES_MP4_FIXAS}
    if qualidade_limpa not in qualidades_validas:
        raise YoutubeDownloadError("Selecione uma qualidade MP4 valida: 720p, 1080p ou 2160p.")
    return qualidade_limpa


def montar_opcoes_qualidade_mp4(
    qualidades_progressivas: set[str],
    qualidades_adaptativas: set[str],
    ffmpeg_ativo: bool,
) -> list[dict]:
    opcoes = []
    for valor, rotulo in QUALIDADES_MP4_FIXAS:
        disponivel_progressivo = valor in qualidades_progressivas
        disponivel_adaptativo = valor in qualidades_adaptativas
        disponivel = disponivel_progressivo or disponivel_adaptativo
        requer_ffmpeg = bool(disponivel_adaptativo and not disponivel_progressivo)
        habilitado = disponivel and (ffmpeg_ativo or not requer_ffmpeg)

        if not disponivel:
            detalhe = "Qualidade indisponivel para este video."
        elif requer_ffmpeg and not ffmpeg_ativo:
            detalhe = "Esta qualidade precisa de ffmpeg para mesclar video e audio."
        elif requer_ffmpeg:
            detalhe = "Baixa video em alta qualidade e mescla o audio automaticamente."
        else:
            detalhe = "Qualidade pronta para download direto em MP4."

        opcoes.append(
            {
                "valor": valor,
                "rotulo": rotulo,
                "disponivel": disponivel,
                "requer_ffmpeg": requer_ffmpeg,
                "habilitado": habilitado,
                "detalhe": detalhe,
            }
        )
    return opcoes


def _configurar_ssl_pytubefix():
    try:
        import certifi
        import pytubefix.request as pytubefix_request
    except ImportError:
        return

    contexto = ssl.create_default_context(cafile=certifi.where())

    def _urlopen_com_contexto(*args, **kwargs):
        kwargs.setdefault("context", contexto)
        return urllib_urlopen(*args, **kwargs)

    pytubefix_request.urlopen = _urlopen_com_contexto


def _traduzir_erro_rede(exc: Exception) -> YoutubeDownloadError:
    motivo = getattr(exc, "reason", exc)
    if isinstance(motivo, ssl.SSLCertVerificationError):
        return YoutubeDownloadError(
            "Falha na validacao SSL ao acessar o YouTube. Instale ou atualize a dependencia certifi e tente novamente."
        )
    return YoutubeDownloadError(
        "Nao foi possivel acessar o YouTube no momento. Verifique a conexao do servidor e tente novamente."
    )


def _importar_youtube():
    _configurar_ssl_pytubefix()
    try:
        from pytubefix import YouTube
    except ImportError as exc:
        raise YoutubeDownloadError(
            "A dependencia pytubefix nao esta instalada. Adicione-a ao ambiente antes de usar este modulo."
        ) from exc
    return YouTube


def _criar_objeto_youtube(url: str):
    YouTube = _importar_youtube()
    try:
        return YouTube(validar_url_youtube(url))
    except URLError as exc:
        raise _traduzir_erro_rede(exc) from exc
    except ssl.SSLError as exc:
        raise _traduzir_erro_rede(exc) from exc
    except Exception as exc:
        raise YoutubeDownloadError(
            "Nao foi possivel ler os dados do video. Verifique se o link esta correto e tente novamente."
        ) from exc


def _obter_stream_mp4(yt):
    stream = yt.streams.filter(progressive=True, file_extension="mp4").order_by("resolution").desc().first()
    if stream is None:
        raise YoutubeDownloadError("Nenhum stream MP4 compativel foi encontrado para este video.")
    return stream


def _listar_streams_progressivos_mp4(yt):
    return yt.streams.filter(progressive=True, subtype="mp4").order_by("resolution").desc()


def _listar_streams_video_adaptativos_mp4(yt):
    return yt.streams.filter(adaptive=True, only_video=True, subtype="mp4").order_by("resolution").desc()


def _obter_stream_video_por_qualidade(yt, qualidade: str):
    stream_progressivo = (
        yt.streams.filter(progressive=True, subtype="mp4", resolution=qualidade).order_by("fps").desc().first()
    )
    if stream_progressivo is not None:
        return stream_progressivo, False

    stream_adaptativo = (
        yt.streams.filter(adaptive=True, only_video=True, subtype="mp4", resolution=qualidade)
        .order_by("fps")
        .desc()
        .first()
    )
    if stream_adaptativo is not None:
        return stream_adaptativo, True

    return None, False


def _resolucao_stream(stream) -> str:
    return str(getattr(stream, "resolution", "") or "").strip()


def _listar_qualidades(streams) -> set[str]:
    return {_resolucao_stream(stream) for stream in streams if _resolucao_stream(stream)}


def _obter_melhor_stream_video_mp4(yt):
    stream_adaptativo = _listar_streams_video_adaptativos_mp4(yt).first()
    if stream_adaptativo is not None:
        return stream_adaptativo
    return _listar_streams_progressivos_mp4(yt).first()


def _obter_stream_audio(yt):
    stream = yt.streams.filter(only_audio=True, subtype="mp4").order_by("abr").desc().first()
    if stream is None:
        stream = yt.streams.filter(only_audio=True).order_by("abr").desc().first()
    if stream is None:
        raise YoutubeDownloadError("Nenhum stream de audio compativel foi encontrado para este video.")
    return stream


def obter_info_video(url: str) -> dict:
    yt = _criar_objeto_youtube(url)
    try:
        stream_video_maximo = _obter_melhor_stream_video_mp4(yt)
        audio_stream = _obter_stream_audio(yt)
        qualidades_progressivas = _listar_qualidades(_listar_streams_progressivos_mp4(yt))
        qualidades_adaptativas = _listar_qualidades(_listar_streams_video_adaptativos_mp4(yt))
        ffmpeg_ativo = ffmpeg_disponivel()
        return {
            "url": validar_url_youtube(url),
            "titulo": str(yt.title or "Video sem titulo").strip(),
            "duracao_segundos": int(yt.length or 0),
            "duracao_texto": formatar_duracao(yt.length),
            "miniatura_url": str(yt.thumbnail_url or "").strip(),
            "autor": str(getattr(yt, "author", "") or "").strip(),
            "resolucao_maxima_video": _resolucao_stream(stream_video_maximo) or "-",
            "audio_bitrate": str(getattr(audio_stream, "abr", "") or "").strip(),
            "mp3_disponivel": ffmpeg_ativo,
            "qualidades_mp4": montar_opcoes_qualidade_mp4(
                qualidades_progressivas,
                qualidades_adaptativas,
                ffmpeg_ativo,
            ),
        }
    except URLError as exc:
        raise _traduzir_erro_rede(exc) from exc
    except ssl.SSLError as exc:
        raise _traduzir_erro_rede(exc) from exc


def _executar_ffmpeg_mp3(origem: Path, destino: Path):
    comando = [
        "ffmpeg",
        "-y",
        "-i",
        str(origem),
        "-vn",
        "-codec:a",
        "libmp3lame",
        "-q:a",
        "0",
        str(destino),
    ]
    try:
        subprocess.run(comando, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise YoutubeDownloadError(
            "Conversao para MP3 indisponivel neste servidor. Instale o ffmpeg para habilitar essa opcao."
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise YoutubeDownloadError("Falha ao converter o audio para MP3.") from exc


def _executar_ffmpeg_mp4(video_path: Path, audio_path: Path, destino: Path):
    comando = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-i",
        str(audio_path),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
        str(destino),
    ]
    try:
        subprocess.run(comando, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise YoutubeDownloadError(
            "Qualidades MP4 em HD exigem ffmpeg para mesclar video e audio."
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise YoutubeDownloadError("Falha ao montar o arquivo MP4 na qualidade selecionada.") from exc


def baixar_arquivo(url: str, formato: str, qualidade: str | None = None) -> tuple[Path, str, str]:
    formato_limpo = str(formato or "").strip().lower()
    if formato_limpo not in {"mp4", "mp3"}:
        raise YoutubeDownloadError("Formato invalido. Escolha MP4 ou MP3.")

    yt = _criar_objeto_youtube(url)
    try:
        pasta_destino = garantir_diretorio_download()
        nome_base = sanitizar_nome_arquivo(yt.title)
        token = uuid.uuid4().hex

        if formato_limpo == "mp4":
            qualidade_mp4 = normalizar_qualidade_mp4(qualidade)
            stream_video, requer_mescla = _obter_stream_video_por_qualidade(yt, qualidade_mp4)
            if stream_video is None:
                raise YoutubeDownloadError(
                    f"A qualidade {qualidade_mp4} nao esta disponivel para este video."
                )

            if not requer_mescla:
                nome_saida = f"{nome_base}_{qualidade_mp4}_{token}.mp4"
                caminho_saida = Path(
                    stream_video.download(output_path=str(pasta_destino), filename=nome_saida)
                )
                return caminho_saida, f"{nome_base}_{qualidade_mp4}.mp4", "video/mp4"

            if not ffmpeg_disponivel():
                raise YoutubeDownloadError(
                    "As qualidades MP4 em HD e 4K exigem ffmpeg para mesclar video e audio."
                )

            stream_audio = _obter_stream_audio(yt)
            video_temporario = pasta_destino / f"{nome_base}_video_{qualidade_mp4}_{token}.{stream_video.subtype}"
            audio_temporario = pasta_destino / f"{nome_base}_audio_{token}.{stream_audio.subtype}"
            caminho_saida = pasta_destino / f"{nome_base}_{qualidade_mp4}_{token}.mp4"

            caminho_video = Path(
                stream_video.download(output_path=str(pasta_destino), filename=video_temporario.name)
            )
            caminho_audio = Path(
                stream_audio.download(output_path=str(pasta_destino), filename=audio_temporario.name)
            )

            try:
                _executar_ffmpeg_mp4(caminho_video, caminho_audio, caminho_saida)
            finally:
                remover_arquivo_se_existir(caminho_video)
                remover_arquivo_se_existir(caminho_audio)

            return caminho_saida, f"{nome_base}_{qualidade_mp4}.mp4", "video/mp4"

        if not ffmpeg_disponivel():
            raise YoutubeDownloadError(
                "Conversao para MP3 indisponivel neste servidor. Instale o ffmpeg para habilitar essa opcao."
            )

        stream_audio = _obter_stream_audio(yt)
        extensao_origem = str(getattr(stream_audio, "subtype", "") or "mp4").strip() or "mp4"
        nome_temporario = f"{nome_base}_{token}.{extensao_origem}"
        caminho_temporario = Path(
            stream_audio.download(output_path=str(pasta_destino), filename=nome_temporario)
        )
        caminho_saida = pasta_destino / f"{nome_base}_{token}.mp3"

        try:
            _executar_ffmpeg_mp3(caminho_temporario, caminho_saida)
        finally:
            remover_arquivo_se_existir(caminho_temporario)

        return caminho_saida, f"{nome_base}.mp3", "audio/mpeg"
    except URLError as exc:
        raise _traduzir_erro_rede(exc) from exc
    except ssl.SSLError as exc:
        raise _traduzir_erro_rede(exc) from exc
