import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import services.youtube_download_jobs as youtube_download_jobs


class YoutubeDownloadJobsTest(unittest.TestCase):
    def tearDown(self):
        with youtube_download_jobs._LOCK:
            for job in youtube_download_jobs._JOBS.values():
                arquivo_path = job.get("arquivo_path")
                if arquivo_path:
                    youtube_download_jobs.remover_arquivo_se_existir(Path(arquivo_path))
            youtube_download_jobs._JOBS.clear()
            youtube_download_jobs._TICKETS.clear()

    def _aguardar_status(self, job_id: str, usuario_id: int, status_esperado: str, timeout: float = 3.0):
        limite = time.time() + timeout
        while time.time() < limite:
            job = youtube_download_jobs.obter_job_download(job_id, usuario_id)
            if job["status"] == status_esperado:
                return job
            time.sleep(0.05)
        self.fail(f"Job {job_id} nao chegou ao status {status_esperado}.")

    def test_criar_job_reutiliza_download_em_andamento_do_mesmo_usuario(self):
        liberar_download = threading.Event()

        with tempfile.TemporaryDirectory() as tmp_dir:
            caminho_arquivo = Path(tmp_dir) / "video.mp4"

            def fake_baixar_arquivo(url: str, formato: str, qualidade: str | None):
                self.assertEqual(url, "https://www.youtube.com/watch?v=abc")
                self.assertEqual(formato, "mp4")
                self.assertEqual(qualidade, "720p")
                liberar_download.wait(timeout=2)
                caminho_arquivo.write_text("video", encoding="utf-8")
                return caminho_arquivo, "video.mp4", "video/mp4"

            with (
                patch(
                    "services.youtube_download_jobs.preparar_solicitacao_download",
                    return_value=("https://www.youtube.com/watch?v=abc", "mp4", "720p"),
                ),
                patch("services.youtube_download_jobs.baixar_arquivo", side_effect=fake_baixar_arquivo),
            ):
                job1 = youtube_download_jobs.criar_job_download(
                    7,
                    "https://www.youtube.com/watch?v=abc",
                    "mp4",
                    "720p",
                )
                job2 = youtube_download_jobs.criar_job_download(
                    7,
                    "https://www.youtube.com/watch?v=abc",
                    "mp4",
                    "720p",
                )

                self.assertEqual(job1["id"], job2["id"])
                liberar_download.set()
                concluido = self._aguardar_status(
                    job1["id"],
                    7,
                    youtube_download_jobs.STATUS_DOWNLOAD_CONCLUIDO,
                )

        self.assertTrue(concluido["pronto"])

    def test_obter_arquivo_job_download_retorna_arquivo_pronto(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            caminho_arquivo = Path(tmp_dir) / "aula.mp3"
            caminho_arquivo.write_text("audio", encoding="utf-8")

            with (
                patch(
                    "services.youtube_download_jobs.preparar_solicitacao_download",
                    return_value=("https://www.youtube.com/watch?v=abc", "mp3", None),
                ),
                patch(
                    "services.youtube_download_jobs.baixar_arquivo",
                    return_value=(caminho_arquivo, "aula.mp3", "audio/mpeg"),
                ),
            ):
                job = youtube_download_jobs.criar_job_download(3, "https://www.youtube.com/watch?v=abc", "mp3")
                concluido = self._aguardar_status(
                    job["id"],
                    3,
                    youtube_download_jobs.STATUS_DOWNLOAD_CONCLUIDO,
                )
                caminho, nome_arquivo, media_type = youtube_download_jobs.obter_arquivo_job_download(
                    concluido["id"],
                    3,
                )

        self.assertEqual(caminho, caminho_arquivo)
        self.assertEqual(nome_arquivo, "aula.mp3")
        self.assertEqual(media_type, "audio/mpeg")

    def test_criar_ticket_download_retorna_url_temporaria(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            caminho_arquivo = Path(tmp_dir) / "aula.mp4"
            caminho_arquivo.write_text("video", encoding="utf-8")

            with (
                patch(
                    "services.youtube_download_jobs.preparar_solicitacao_download",
                    return_value=("https://www.youtube.com/watch?v=abc", "mp4", "720p"),
                ),
                patch(
                    "services.youtube_download_jobs.baixar_arquivo",
                    return_value=(caminho_arquivo, "aula.mp4", "video/mp4"),
                ),
            ):
                job = youtube_download_jobs.criar_job_download(9, "https://www.youtube.com/watch?v=abc", "mp4", "720p")
                concluido = self._aguardar_status(
                    job["id"],
                    9,
                    youtube_download_jobs.STATUS_DOWNLOAD_CONCLUIDO,
                )
                ticket = youtube_download_jobs.criar_ticket_download(concluido["id"], 9)
                usuario_ticket = youtube_download_jobs.validar_ticket_download(concluido["id"], ticket["ticket"])

        self.assertEqual(usuario_ticket, 9)
        self.assertIn(f"/download/jobs/{job['id']}/arquivo?ticket=", ticket["download_url"])


if __name__ == "__main__":
    unittest.main()
