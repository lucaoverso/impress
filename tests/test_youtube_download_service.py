import ssl
import unittest
from pathlib import Path
from urllib.error import URLError
from unittest.mock import patch

from services.youtube_download_service import (
    QUALIDADES_MP4_FIXAS,
    YoutubeDownloadError,
    _traduzir_erro_rede,
    baixar_arquivo,
    formatar_duracao,
    montar_opcoes_qualidade_mp4,
    normalizar_qualidade_mp4,
    sanitizar_nome_arquivo,
    validar_url_youtube,
)


class YoutubeDownloadServiceTest(unittest.TestCase):
    def test_formatar_duracao_sem_horas(self):
        self.assertEqual(formatar_duracao(125), "02:05")

    def test_formatar_duracao_com_horas(self):
        self.assertEqual(formatar_duracao(3723), "01:02:03")

    def test_sanitizar_nome_remove_caracteres_invalidos(self):
        self.assertEqual(sanitizar_nome_arquivo('Aula: frações / 6º ano?'), "Aula_fraes_6_ano")

    def test_validar_url_rejeita_texto_sem_http(self):
        with self.assertRaises(YoutubeDownloadError):
            validar_url_youtube("youtube.com/watch?v=abc")

    def test_normalizar_qualidade_mp4_rejeita_valor_invalido(self):
        with self.assertRaises(YoutubeDownloadError):
            normalizar_qualidade_mp4("480p")

    def test_montar_opcoes_qualidade_mp4_respeita_ffmpeg(self):
        opcoes = montar_opcoes_qualidade_mp4({"720p"}, {"1080p", "2160p"}, ffmpeg_ativo=False)
        mapa = {item["valor"]: item for item in opcoes}

        self.assertTrue(mapa["720p"]["habilitado"])
        self.assertFalse(mapa["1080p"]["habilitado"])
        self.assertFalse(mapa["2160p"]["habilitado"])
        self.assertEqual(len(opcoes), len(QUALIDADES_MP4_FIXAS))

    def test_traduz_erro_ssl_para_mensagem_amigavel(self):
        erro = URLError(ssl.SSLCertVerificationError("certificado invalido"))
        mensagem = _traduzir_erro_rede(erro)
        self.assertIsInstance(mensagem, YoutubeDownloadError)
        self.assertIn("SSL", str(mensagem))

    def test_baixar_arquivo_mp4_progressivo_retorna_arquivo_final(self):
        pasta = Path.cwd() / "fake_spool"
        yt = _FakeYoutube("Aula Teste")
        stream = _FakeStream(
            retorno_download=pasta / "Aula_Teste_720p_token.mp4",
            subtype="mp4",
            resolution="720p",
        )

        with (
            patch("services.youtube_download_service._criar_objeto_youtube", return_value=yt),
            patch("services.youtube_download_service.garantir_diretorio_download", return_value=pasta),
            patch("services.youtube_download_service.uuid.uuid4", return_value=_FakeUuid("token")),
            patch("services.youtube_download_service._obter_stream_video_por_qualidade", return_value=(stream, False)),
        ):
            caminho, nome_arquivo, media_type = baixar_arquivo(
                "https://www.youtube.com/watch?v=abc",
                "mp4",
                "720p",
            )

        self.assertEqual(caminho, pasta / "Aula_Teste_720p_token.mp4")
        self.assertEqual(nome_arquivo, "Aula_Teste_720p.mp4")
        self.assertEqual(media_type, "video/mp4")
        self.assertEqual(
            stream.download_calls,
            [(str(pasta), "Aula_Teste_720p_token.mp4")],
        )

    def test_baixar_arquivo_mp4_adaptativo_sem_ffmpeg_falha(self):
        yt = _FakeYoutube("Aula Teste")
        stream = _FakeStream(retorno_download=Path("video.mp4"), subtype="mp4", resolution="1080p")

        with (
            patch("services.youtube_download_service._criar_objeto_youtube", return_value=yt),
            patch("services.youtube_download_service._obter_stream_video_por_qualidade", return_value=(stream, True)),
            patch("services.youtube_download_service.ffmpeg_disponivel", return_value=False),
        ):
            with self.assertRaises(YoutubeDownloadError) as contexto:
                baixar_arquivo("https://www.youtube.com/watch?v=abc", "mp4", "1080p")

        self.assertIn("ffmpeg", str(contexto.exception))

    def test_baixar_arquivo_mp4_adaptativo_mescla_video_e_audio(self):
        pasta = Path.cwd() / "fake_spool"
        yt = _FakeYoutube("Aula Teste")
        stream_video = _FakeStream(
            retorno_download=pasta / "Aula_Teste_video_1080p_token.mp4",
            subtype="mp4",
            resolution="1080p",
        )
        stream_audio = _FakeStream(
            retorno_download=pasta / "Aula_Teste_audio_token.mp4",
            subtype="mp4",
        )

        with (
            patch("services.youtube_download_service._criar_objeto_youtube", return_value=yt),
            patch("services.youtube_download_service.garantir_diretorio_download", return_value=pasta),
            patch("services.youtube_download_service.uuid.uuid4", return_value=_FakeUuid("token")),
            patch("services.youtube_download_service._obter_stream_video_por_qualidade", return_value=(stream_video, True)),
            patch("services.youtube_download_service._obter_stream_audio", return_value=stream_audio),
            patch("services.youtube_download_service.ffmpeg_disponivel", return_value=True),
            patch("services.youtube_download_service._executar_ffmpeg_mp4") as executar_ffmpeg,
            patch("services.youtube_download_service.remover_arquivo_se_existir") as remover_arquivo,
        ):
            caminho, nome_arquivo, media_type = baixar_arquivo(
                "https://www.youtube.com/watch?v=abc",
                "mp4",
                "1080p",
            )

        caminho_video = pasta / "Aula_Teste_video_1080p_token.mp4"
        caminho_audio = pasta / "Aula_Teste_audio_token.mp4"
        caminho_saida = pasta / "Aula_Teste_1080p_token.mp4"
        self.assertEqual(caminho, caminho_saida)
        self.assertEqual(nome_arquivo, "Aula_Teste_1080p.mp4")
        self.assertEqual(media_type, "video/mp4")
        executar_ffmpeg.assert_called_once_with(caminho_video, caminho_audio, caminho_saida)
        self.assertEqual(remover_arquivo.call_count, 2)
        remover_arquivo.assert_any_call(caminho_video)
        remover_arquivo.assert_any_call(caminho_audio)

    def test_baixar_arquivo_mp3_converte_e_remove_temporario(self):
        pasta = Path.cwd() / "fake_spool"
        yt = _FakeYoutube("Aula Teste")
        stream_audio = _FakeStream(
            retorno_download=pasta / "Aula_Teste_token.webm",
            subtype="webm",
        )

        with (
            patch("services.youtube_download_service._criar_objeto_youtube", return_value=yt),
            patch("services.youtube_download_service.garantir_diretorio_download", return_value=pasta),
            patch("services.youtube_download_service.uuid.uuid4", return_value=_FakeUuid("token")),
            patch("services.youtube_download_service._obter_stream_audio", return_value=stream_audio),
            patch("services.youtube_download_service.ffmpeg_disponivel", return_value=True),
            patch("services.youtube_download_service._executar_ffmpeg_mp3") as executar_ffmpeg,
            patch("services.youtube_download_service.remover_arquivo_se_existir") as remover_arquivo,
        ):
            caminho, nome_arquivo, media_type = baixar_arquivo(
                "https://www.youtube.com/watch?v=abc",
                "mp3",
            )

        caminho_temporario = pasta / "Aula_Teste_token.webm"
        caminho_saida = pasta / "Aula_Teste_token.mp3"
        self.assertEqual(caminho, caminho_saida)
        self.assertEqual(nome_arquivo, "Aula_Teste.mp3")
        self.assertEqual(media_type, "audio/mpeg")
        executar_ffmpeg.assert_called_once_with(caminho_temporario, caminho_saida)
        remover_arquivo.assert_called_once_with(caminho_temporario)


class _FakeYoutube:
    def __init__(self, title):
        self.title = title


class _FakeUuid:
    def __init__(self, hex_value):
        self.hex = hex_value


class _FakeStream:
    def __init__(self, retorno_download: Path, subtype: str, resolution: str | None = None):
        self.retorno_download = Path(retorno_download)
        self.subtype = subtype
        self.resolution = resolution
        self.download_calls = []

    def download(self, output_path: str, filename: str):
        self.download_calls.append((output_path, filename))
        return str(self.retorno_download)


if __name__ == "__main__":
    unittest.main()
