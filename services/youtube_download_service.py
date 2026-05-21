import os
import re
import shutil
import ssl
import threading
import time
import uuid
from copy import deepcopy
from pathlib import Path
from urllib.error import URLError

BASE_DIR = Path(__file__).resolve().parent.parent
DOWNLOAD_DIR = Path(os.getenv("SPOOL_DIR", str(BASE_DIR / "spool"))) / "youtube"
URL_REGEX = re.compile(r"^https?://", re.IGNORECASE)
QUALIDADES_MP4_FIXAS = (
    ("720p", "720p"),
    ("1080p", "1080p"),
    ("2160p", "2160p (4K)"),
)
QUALIDADE_ALTURAS_MP4 = {
    "720p": 720,
    "1080p": 1080,
    "2160p": 2160,
}
FORMATOS_VALIDOS_DOWNLOAD = {"mp4", "mp3"}
_INFO_VIDEO_CACHE: dict[str, tuple[float, dict]] = {}
_INFO_VIDEO_CACHE_LOCK = threading.Lock()


class YoutubeDownloadError(RuntimeError):
    pass


def _resolver_env_int(nome: str, padrao: int, minimo: int = 0) -> int:
    valor_bruto = str(os.getenv(nome, str(padrao)) or "").strip()
    try:
        valor = int(valor_bruto)
    except ValueError:
        return padrao
    return max(valor, minimo)


_INFO_VIDEO_CACHE_TTL_SEGUNDOS = _resolver_env_int("YOUTUBE_INFO_CACHE_TTL_SECONDS", 600, 0)
_YTDLP_FRAGMENTOS_CONCORRENTES = _resolver_env_int("YTDLP_CONCURRENT_FRAGMENTS", 4, 1)


def _resolver_player_clients_youtube() -> list[str]:
    valor_bruto = str(os.getenv("YTDLP_YOUTUBE_PLAYER_CLIENTS", "") or "").strip()
    if not valor_bruto:
        return []

    clientes = []
    for item in valor_bruto.split(","):
        cliente = item.strip()
        if cliente:
            clientes.append(cliente)
    return clientes


def _resolver_js_runtimes_youtube() -> dict[str, dict]:
    valor_bruto = str(os.getenv("YTDLP_JS_RUNTIMES", "") or "").strip()
    if valor_bruto:
        runtimes = {}
        for item in valor_bruto.split(","):
            runtime_bruto = item.strip()
            if not runtime_bruto:
                continue
            nome, separador, caminho = runtime_bruto.partition(":")
            nome_limpo = nome.strip().lower()
            if not nome_limpo:
                continue
            config = {}
            if separador and caminho.strip():
                config["path"] = caminho.strip()
            runtimes[nome_limpo] = config
        return runtimes

    if shutil.which("node"):
        return {"node": {}}

    return {}


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


def normalizar_formato_download(formato: str | None) -> str:
    formato_limpo = str(formato or "").strip().lower()
    if formato_limpo not in FORMATOS_VALIDOS_DOWNLOAD:
        raise YoutubeDownloadError("Formato invalido. Escolha MP4 ou MP3.")
    return formato_limpo


def normalizar_qualidade_mp4(qualidade: str | None) -> str:
    qualidade_limpa = str(qualidade or "").strip().lower()
    qualidades_validas = {valor for valor, _rotulo in QUALIDADES_MP4_FIXAS}
    if qualidade_limpa not in qualidades_validas:
        raise YoutubeDownloadError("Selecione uma qualidade MP4 valida: 720p, 1080p ou 2160p.")
    return qualidade_limpa


def preparar_solicitacao_download(
    url: str,
    formato: str | None,
    qualidade: str | None = None,
) -> tuple[str, str, str | None]:
    url_validada = validar_url_youtube(url)
    formato_limpo = normalizar_formato_download(formato)
    if formato_limpo == "mp4":
        return url_validada, formato_limpo, normalizar_qualidade_mp4(qualidade)
    return url_validada, formato_limpo, None


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


def _importar_yt_dlp():
    try:
        import yt_dlp
    except ImportError as exc:
        raise YoutubeDownloadError(
            "A dependencia yt-dlp nao esta instalada. Adicione-a ao ambiente antes de usar este modulo."
        ) from exc
    return yt_dlp


def _traduzir_erro_rede(exc: Exception) -> YoutubeDownloadError:
    motivo = getattr(exc, "reason", exc)
    if isinstance(motivo, ssl.SSLCertVerificationError):
        return YoutubeDownloadError(
            "Falha na validacao SSL ao acessar o YouTube. Instale ou atualize a dependencia certifi e tente novamente."
        )
    return YoutubeDownloadError(
        "Nao foi possivel acessar o YouTube no momento. Verifique a conexao do servidor e tente novamente."
    )


def _traduzir_erro_ytdlp(exc: Exception) -> YoutubeDownloadError:
    if isinstance(exc, YoutubeDownloadError):
        return exc

    motivo = getattr(exc, "reason", exc)
    if isinstance(exc, (URLError, ssl.SSLError)) or isinstance(motivo, ssl.SSLCertVerificationError):
        return _traduzir_erro_rede(exc)

    mensagem = str(exc or "").strip()
    mensagem_lower = mensagem.lower()

    if "requested format is not available" in mensagem_lower:
        return YoutubeDownloadError("A qualidade solicitada nao esta disponivel para este video.")
    if "ffmpeg is not installed" in mensagem_lower or "ffprobe is not installed" in mensagem_lower:
        return YoutubeDownloadError(
            "Este download exige ffmpeg no servidor para combinar ou converter as midias."
        )
    if "unsupported url" in mensagem_lower or "invalid url" in mensagem_lower:
        return YoutubeDownloadError("Cole um link valido do YouTube para continuar.")
    if "private video" in mensagem_lower or "sign in to confirm your age" in mensagem_lower:
        return YoutubeDownloadError("Este video nao permite download com a configuracao atual do servidor.")
    if "video unavailable" in mensagem_lower or "unable to extract" in mensagem_lower:
        return YoutubeDownloadError(
            "Nao foi possivel ler os dados do video. Verifique se o link esta correto e tente novamente."
        )

    return YoutubeDownloadError(
        "Nao foi possivel acessar o YouTube no momento. Verifique a conexao do servidor e tente novamente."
    )


def _opcoes_ytdlp_base() -> dict:
    opcoes = {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "noplaylist": True,
        "cachedir": False,
        "extract_flat": False,
        "retries": 3,
        "fragment_retries": 3,
        "socket_timeout": 15,
        "concurrent_fragment_downloads": _YTDLP_FRAGMENTOS_CONCORRENTES,
    }
    js_runtimes = _resolver_js_runtimes_youtube()
    if js_runtimes:
        opcoes["js_runtimes"] = js_runtimes
    player_clients = _resolver_player_clients_youtube()
    if player_clients:
        opcoes["extractor_args"] = {"youtube": {"player_client": player_clients}}
    return opcoes


def _normalizar_info_extraida(info):
    info_normalizada = info
    if isinstance(info_normalizada, dict) and info_normalizada.get("_type") == "playlist":
        for entrada in info_normalizada.get("entries") or []:
            if isinstance(entrada, dict):
                info_normalizada = entrada
                break

    if not isinstance(info_normalizada, dict):
        raise YoutubeDownloadError(
            "Nao foi possivel ler os dados do video. Verifique se o link esta correto e tente novamente."
        )

    return info_normalizada


def _extrair_info_bruta(url: str, *, download: bool = False, extra_opts: dict | None = None) -> dict:
    yt_dlp = _importar_yt_dlp()
    opcoes = _opcoes_ytdlp_base()
    if extra_opts:
        opcoes.update(extra_opts)

    try:
        with yt_dlp.YoutubeDL(opcoes) as ydl:
            info = ydl.extract_info(url, download=download)
            if isinstance(info, dict):
                try:
                    info = ydl.sanitize_info(info)
                except Exception:
                    pass
            return _normalizar_info_extraida(info)
    except Exception as exc:
        raise _traduzir_erro_ytdlp(exc) from exc


def _executar_download_yt_dlp(url: str, opcoes: dict) -> dict:
    return _extrair_info_bruta(url, download=True, extra_opts=opcoes)


def _buscar_info_video_em_cache(url: str) -> dict | None:
    if _INFO_VIDEO_CACHE_TTL_SEGUNDOS <= 0:
        return None

    agora = time.time()
    with _INFO_VIDEO_CACHE_LOCK:
        item = _INFO_VIDEO_CACHE.get(url)
        if not item:
            return None

        expiracao, info = item
        if expiracao <= agora:
            _INFO_VIDEO_CACHE.pop(url, None)
            return None

        return deepcopy(info)


def _salvar_info_video_em_cache(url: str, info: dict):
    if _INFO_VIDEO_CACHE_TTL_SEGUNDOS <= 0:
        return

    expiracao = time.time() + _INFO_VIDEO_CACHE_TTL_SEGUNDOS
    with _INFO_VIDEO_CACHE_LOCK:
        _INFO_VIDEO_CACHE[url] = (expiracao, deepcopy(info))


def _normalizar_codec(valor) -> str:
    return str(valor or "").strip().lower()


def _normalizar_ext(valor) -> str:
    return str(valor or "").strip().lower()


def _extrair_altura(formato: dict) -> int:
    try:
        return int(formato.get("height") or 0)
    except (TypeError, ValueError):
        return 0


def _extrair_abr(formato: dict) -> float:
    try:
        return float(formato.get("abr") or 0)
    except (TypeError, ValueError):
        return 0.0


def _eh_formato_audio(formato: dict) -> bool:
    acodec = _normalizar_codec(formato.get("acodec"))
    vcodec = _normalizar_codec(formato.get("vcodec"))
    return acodec not in {"", "none"} and vcodec in {"", "none"}


def _tem_audio_disponivel(formato: dict) -> bool:
    return _normalizar_codec(formato.get("acodec")) not in {"", "none"}


def _eh_formato_video(formato: dict) -> bool:
    return _normalizar_codec(formato.get("vcodec")) not in {"", "none"} and _extrair_altura(formato) > 0


def _eh_formato_mp4_progressivo(formato: dict) -> bool:
    return (
        _eh_formato_video(formato)
        and _normalizar_ext(formato.get("ext")) == "mp4"
        and _normalizar_codec(formato.get("acodec")) not in {"", "none"}
    )


def _eh_formato_mp4_adaptativo(formato: dict) -> bool:
    return (
        _eh_formato_video(formato)
        and _normalizar_ext(formato.get("ext")) == "mp4"
        and _normalizar_codec(formato.get("acodec")) in {"", "none"}
    )


def _rotulo_qualidade_por_altura(altura: int) -> str | None:
    if altura in {720, 1080, 2160}:
        return f"{altura}p"
    return None


def _rotulo_resolucao_video_maxima(formatos: list[dict]) -> str:
    melhor_altura = max((_extrair_altura(formato) for formato in formatos if _eh_formato_video(formato)), default=0)
    if melhor_altura <= 0:
        return "-"
    return f"{melhor_altura}p"


def _audio_bitrate_melhor(formatos: list[dict]) -> str:
    melhor_abr = max((_extrair_abr(formato) for formato in formatos if _eh_formato_audio(formato)), default=0.0)
    if melhor_abr <= 0:
        return "-"
    return f"{int(round(melhor_abr))}kbps"


def _mapear_qualidades_mp4(formatos: list[dict]) -> tuple[set[str], set[str], bool]:
    qualidades_progressivas = set()
    qualidades_adaptativas = set()
    audio_disponivel = any(_tem_audio_disponivel(formato) for formato in formatos)

    for formato in formatos:
        altura = _extrair_altura(formato)
        rotulo = _rotulo_qualidade_por_altura(altura)
        if not rotulo:
            continue
        if _eh_formato_mp4_progressivo(formato):
            qualidades_progressivas.add(rotulo)
        elif _eh_formato_mp4_adaptativo(formato):
            qualidades_adaptativas.add(rotulo)

    return qualidades_progressivas, qualidades_adaptativas, audio_disponivel


def _obter_formatos(info: dict) -> list[dict]:
    formatos = info.get("formats") or []
    return [formato for formato in formatos if isinstance(formato, dict)]


def obter_info_video(url: str) -> dict:
    url_validada = validar_url_youtube(url)
    info_cache = _buscar_info_video_em_cache(url_validada)
    if info_cache is not None:
        return info_cache

    info_bruta = _extrair_info_bruta(url_validada, download=False)
    formatos = _obter_formatos(info_bruta)
    qualidades_progressivas, qualidades_adaptativas, audio_disponivel = _mapear_qualidades_mp4(formatos)
    ffmpeg_ativo = ffmpeg_disponivel()

    info = {
        "url": url_validada,
        "titulo": str(info_bruta.get("title") or "Video sem titulo").strip(),
        "duracao_segundos": int(info_bruta.get("duration") or 0),
        "duracao_texto": formatar_duracao(info_bruta.get("duration")),
        "miniatura_url": str(info_bruta.get("thumbnail") or "").strip(),
        "autor": str(info_bruta.get("channel") or info_bruta.get("uploader") or "").strip(),
        "resolucao_maxima_video": _rotulo_resolucao_video_maxima(formatos),
        "audio_bitrate": _audio_bitrate_melhor(formatos),
        "ffmpeg_disponivel": ffmpeg_ativo,
        "mp3_disponivel": ffmpeg_ativo and audio_disponivel,
        "qualidades_mp4": montar_opcoes_qualidade_mp4(
            qualidades_progressivas,
            qualidades_adaptativas,
            ffmpeg_ativo,
        ),
    }
    _salvar_info_video_em_cache(url_validada, info)
    return info


def _montar_outtmpl(caminho_base: Path) -> str:
    return str(caminho_base.parent / f"{caminho_base.name}.%(ext)s")


def _montar_seletor_progressivo_mp4(altura: int) -> str:
    return (
        f"best[ext=mp4][vcodec!=none][acodec!=none][height={altura}]"
        f"/best[ext=mp4][vcodec!=none][acodec!=none][height<={altura}]"
    )


def _montar_seletor_mp4(altura: int, ffmpeg_ativo: bool) -> str:
    seletor_progressivo = _montar_seletor_progressivo_mp4(altura)
    if not ffmpeg_ativo:
        return seletor_progressivo

    return (
        f"bestvideo[ext=mp4][height={altura}]+bestaudio[ext=m4a]"
        f"/bestvideo[ext=mp4][height={altura}]+bestaudio"
        f"/bestvideo[ext=mp4][height<={altura}]+bestaudio[ext=m4a]"
        f"/bestvideo[ext=mp4][height<={altura}]+bestaudio"
        f"/{seletor_progressivo}"
    )


def _montar_seletor_mp3() -> str:
    return "bestaudio[ext=m4a]/bestaudio/best"


def _localizar_arquivo_saida(
    pasta_destino: Path,
    prefixo: str,
    extensoes_preferidas: tuple[str, ...],
) -> Path:
    ignoradas = {
        ".part",
        ".ytdl",
        ".json",
        ".info.json",
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".vtt",
        ".srt",
    }
    candidatos = []
    for caminho in pasta_destino.glob(f"{prefixo}*"):
        if not caminho.is_file():
            continue
        if any(caminho.name.endswith(sufixo) for sufixo in ignoradas):
            continue
        candidatos.append(caminho)

    if not candidatos:
        raise YoutubeDownloadError("O servidor nao encontrou o arquivo final gerado pelo yt-dlp.")

    for extensao in extensoes_preferidas:
        extensao_normalizada = f".{extensao.lstrip('.').lower()}"
        candidatos_ext = [caminho for caminho in candidatos if caminho.suffix.lower() == extensao_normalizada]
        if candidatos_ext:
            return max(candidatos_ext, key=lambda item: item.stat().st_mtime)

    return max(candidatos, key=lambda item: item.stat().st_mtime)


def _obter_opcao_qualidade(info: dict, qualidade: str) -> dict | None:
    for opcao in info.get("qualidades_mp4") or []:
        if opcao.get("valor") == qualidade:
            return opcao
    return None


def baixar_arquivo(url: str, formato: str, qualidade: str | None = None) -> tuple[Path, str, str]:
    url_validada, formato_limpo, qualidade_mp4 = preparar_solicitacao_download(url, formato, qualidade)
    info = obter_info_video(url_validada)
    pasta_destino = garantir_diretorio_download()
    nome_base = sanitizar_nome_arquivo(info.get("titulo"))
    token = uuid.uuid4().hex
    ffmpeg_ativo = ffmpeg_disponivel()

    if formato_limpo == "mp4":
        opcao = _obter_opcao_qualidade(info, qualidade_mp4)
        if not opcao or not opcao.get("disponivel"):
            raise YoutubeDownloadError(f"A qualidade {qualidade_mp4} nao esta disponivel para este video.")
        if not opcao.get("habilitado"):
            raise YoutubeDownloadError(
                "As qualidades MP4 em HD e 4K exigem ffmpeg para mesclar video e audio."
            )

        altura = QUALIDADE_ALTURAS_MP4[qualidade_mp4]
        prefixo = f"{nome_base}_{qualidade_mp4}_{token}"
        _executar_download_yt_dlp(
            url_validada,
            {
                "format": _montar_seletor_mp4(altura, ffmpeg_ativo),
                "outtmpl": _montar_outtmpl(pasta_destino / prefixo),
                "merge_output_format": "mp4",
                "overwrites": True,
            },
        )
        caminho_saida = _localizar_arquivo_saida(pasta_destino, prefixo, ("mp4",))
        return caminho_saida, f"{nome_base}_{qualidade_mp4}.mp4", "video/mp4"

    if not info.get("mp3_disponivel"):
        raise YoutubeDownloadError(
            "Conversao para MP3 indisponivel neste servidor. Instale o ffmpeg para habilitar essa opcao."
        )

    prefixo = f"{nome_base}_{token}"
    _executar_download_yt_dlp(
        url_validada,
        {
            "format": _montar_seletor_mp3(),
            "outtmpl": _montar_outtmpl(pasta_destino / prefixo),
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "0",
                }
            ],
            "overwrites": True,
        },
    )
    caminho_saida = _localizar_arquivo_saida(pasta_destino, prefixo, ("mp3",))
    return caminho_saida, f"{nome_base}.mp3", "audio/mpeg"
