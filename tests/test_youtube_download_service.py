import ssl
import tempfile
import unittest
from pathlib import Path
from urllib.error import URLError
from unittest.mock import patch

from services.youtube_download_service import (
    _INFO_VIDEO_CACHE,
    _INFO_VIDEO_CACHE_LOCK,
    QUALIDADES_MP4_FIXAS,
    YoutubeDownloadError,
    _traduzir_erro_rede,
    _opcoes_ytdlp_base,
    baixar_arquivo,
    formatar_duracao,
    montar_opcoes_qualidade_mp4,
    normalizar_qualidade_mp4,
    obter_info_video,
    preparar_solicitacao_download,
    sanitizar_nome_arquivo,
    validar_url_youtube,
)


class YoutubeDownloadServiceTest(unittest.TestCase):
    def tearDown(self):
        with _INFO_VIDEO_CACHE_LOCK:
            _INFO_VIDEO_CACHE.clear()

    def test_formatar_duracao_sem_horas(self):
        self.assertEqual(formatar_duracao(125), "02:05")

    def test_formatar_duracao_com_horas(self):
        self.assertEqual(formatar_duracao(3723), "01:02:03")

    def test_sanitizar_nome_remove_caracteres_invalidos(self):
        self.assertEqual(sanitizar_nome_arquivo("Aula: frações / 6º ano?"), "Aula_fraes_6_ano")

    def test_validar_url_rejeita_texto_sem_http(self):
        with self.assertRaises(YoutubeDownloadError):
            validar_url_youtube("youtube.com/watch?v=abc")

    def test_normalizar_qualidade_mp4_rejeita_valor_invalido(self):
        with self.assertRaises(YoutubeDownloadError):
            normalizar_qualidade_mp4("480p")

    def test_preparar_solicitacao_download_normaliza_campos(self):
        url, formato, qualidade = preparar_solicitacao_download(
            " https://www.youtube.com/watch?v=abc ",
            "MP4",
            "1080p",
        )

        self.assertEqual(url, "https://www.youtube.com/watch?v=abc")
        self.assertEqual(formato, "mp4")
        self.assertEqual(qualidade, "1080p")

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

    def test_opcoes_ytdlp_nao_forca_player_client_por_padrao(self):
        with patch.dict("os.environ", {}, clear=False):
            with patch("services.youtube_download_service.shutil.which", return_value=None):
                opcoes = _opcoes_ytdlp_base()

        self.assertNotIn("extractor_args", opcoes)
        self.assertNotIn("js_runtimes", opcoes)

    def test_opcoes_ytdlp_habilita_node_quando_disponivel_no_path(self):
        with patch.dict("os.environ", {}, clear=False):
            with patch("services.youtube_download_service.shutil.which", return_value="/usr/bin/node"):
                opcoes = _opcoes_ytdlp_base()

        self.assertEqual(opcoes["js_runtimes"], {"node": {}})

    def test_opcoes_ytdlp_aceita_player_client_por_variavel_de_ambiente(self):
        with patch.dict("os.environ", {"YTDLP_YOUTUBE_PLAYER_CLIENTS": "android,web"}, clear=False):
            with patch("services.youtube_download_service.shutil.which", return_value=None):
                opcoes = _opcoes_ytdlp_base()

        self.assertEqual(opcoes["extractor_args"], {"youtube": {"player_client": ["android", "web"]}})

    def test_opcoes_ytdlp_aceita_js_runtimes_por_variavel_de_ambiente(self):
        with patch.dict("os.environ", {"YTDLP_JS_RUNTIMES": "node:/usr/bin/node,bun"}, clear=False):
            with patch("services.youtube_download_service.shutil.which", return_value=None):
                opcoes = _opcoes_ytdlp_base()

        self.assertEqual(
            opcoes["js_runtimes"],
            {
                "node": {"path": "/usr/bin/node"},
                "bun": {},
            },
        )

    def test_obter_info_video_reaproveita_cache_curto(self):
        info_bruta = {
            "title": "Aula Teste",
            "duration": 125,
            "thumbnail": "https://img.example/thumb.jpg",
            "channel": "Canal Teste",
            "formats": [
                {
                    "ext": "mp4",
                    "height": 720,
                    "vcodec": "avc1",
                    "acodec": "mp4a",
                },
                {
                    "ext": "mp4",
                    "height": 1080,
                    "vcodec": "avc1",
                    "acodec": "none",
                },
                {
                    "ext": "m4a",
                    "vcodec": "none",
                    "acodec": "mp4a",
                    "abr": 128,
                },
            ],
        }
        url = "https://www.youtube.com/watch?v=abc"

        with patch("services.youtube_download_service._extrair_info_bruta", return_value=info_bruta) as extrair:
            with patch("services.youtube_download_service.ffmpeg_disponivel", return_value=True):
                info1 = obter_info_video(url)
                info2 = obter_info_video(url)

        self.assertEqual(extrair.call_count, 1)
        self.assertEqual(info1["titulo"], "Aula Teste")
        self.assertEqual(info2["titulo"], "Aula Teste")
        self.assertEqual(info2["resolucao_maxima_video"], "1080p")
        self.assertEqual(info2["audio_bitrate"], "128kbps")
        self.assertTrue(info2["mp3_disponivel"])

    def test_obter_info_video_mantem_mp3_quando_video_tem_audio_embutido(self):
        info_bruta = {
            "title": "Aula Curta",
            "duration": 45,
            "thumbnail": "https://img.example/thumb.jpg",
            "channel": "Canal Teste",
            "formats": [
                {
                    "ext": "mp4",
                    "height": 360,
                    "vcodec": "avc1",
                    "acodec": "mp4a",
                    "abr": 96,
                },
            ],
        }

        with patch("services.youtube_download_service._extrair_info_bruta", return_value=info_bruta):
            with patch("services.youtube_download_service.ffmpeg_disponivel", return_value=True):
                info = obter_info_video("https://www.youtube.com/watch?v=abc")

        self.assertEqual(info["resolucao_maxima_video"], "360p")
        self.assertTrue(info["mp3_disponivel"])
        self.assertTrue(info["ffmpeg_disponivel"])

    def test_baixar_arquivo_mp4_retorna_arquivo_final(self):
        info = {
            "titulo": "Aula Teste",
            "mp3_disponivel": True,
            "qualidades_mp4": [
                {"valor": "720p", "disponivel": True, "habilitado": True},
            ],
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            pasta = Path(tmp_dir)

            def fake_download(_url: str, _opts: dict):
                (pasta / "Aula_Teste_720p_token.mp4").write_text("video", encoding="utf-8")
                return {}

            with (
                patch("services.youtube_download_service.obter_info_video", return_value=info),
                patch("services.youtube_download_service.garantir_diretorio_download", return_value=pasta),
                patch("services.youtube_download_service.uuid.uuid4", return_value=_FakeUuid("token")),
                patch("services.youtube_download_service.ffmpeg_disponivel", return_value=True),
                patch("services.youtube_download_service._executar_download_yt_dlp", side_effect=fake_download),
            ):
                caminho, nome_arquivo, media_type = baixar_arquivo(
                    "https://www.youtube.com/watch?v=abc",
                    "mp4",
                    "720p",
                )

        self.assertEqual(caminho.name, "Aula_Teste_720p_token.mp4")
        self.assertEqual(nome_arquivo, "Aula_Teste_720p.mp4")
        self.assertEqual(media_type, "video/mp4")

    def test_baixar_arquivo_mp4_sem_ffmpeg_quando_qualidade_desabilitada_falha(self):
        info = {
            "titulo": "Aula Teste",
            "mp3_disponivel": False,
            "qualidades_mp4": [
                {"valor": "1080p", "disponivel": True, "habilitado": False},
            ],
        }

        with patch("services.youtube_download_service.obter_info_video", return_value=info):
            with self.assertRaises(YoutubeDownloadError) as contexto:
                baixar_arquivo("https://www.youtube.com/watch?v=abc", "mp4", "1080p")

        self.assertIn("ffmpeg", str(contexto.exception))

    def test_baixar_arquivo_mp3_retorna_arquivo_convertido(self):
        info = {
            "titulo": "Aula Teste",
            "mp3_disponivel": True,
            "qualidades_mp4": [],
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            pasta = Path(tmp_dir)

            def fake_download(_url: str, _opts: dict):
                (pasta / "Aula_Teste_token.mp3").write_text("audio", encoding="utf-8")
                return {}

            with (
                patch("services.youtube_download_service.obter_info_video", return_value=info),
                patch("services.youtube_download_service.garantir_diretorio_download", return_value=pasta),
                patch("services.youtube_download_service.uuid.uuid4", return_value=_FakeUuid("token")),
                patch("services.youtube_download_service.ffmpeg_disponivel", return_value=True),
                patch("services.youtube_download_service._executar_download_yt_dlp", side_effect=fake_download),
            ):
                caminho, nome_arquivo, media_type = baixar_arquivo(
                    "https://www.youtube.com/watch?v=abc",
                    "mp3",
                )

        self.assertEqual(caminho.name, "Aula_Teste_token.mp3")
        self.assertEqual(nome_arquivo, "Aula_Teste.mp3")
        self.assertEqual(media_type, "audio/mpeg")


class _FakeUuid:
    def __init__(self, hex_value):
        self.hex = hex_value


if __name__ == "__main__":
    unittest.main()
