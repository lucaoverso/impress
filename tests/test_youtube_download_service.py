import ssl
import unittest
from urllib.error import URLError

from services.youtube_download_service import (
    QUALIDADES_MP4_FIXAS,
    YoutubeDownloadError,
    _traduzir_erro_rede,
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


if __name__ == "__main__":
    unittest.main()
