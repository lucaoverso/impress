import importlib
import os
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path


def _importar_worker():
    modulo_original = sys.modules.get("services.printer")
    stub_printer = types.ModuleType("services.printer")
    stub_printer.imprimir_job = lambda job: {}
    sys.modules["services.printer"] = stub_printer

    if "services.worker" in sys.modules:
        del sys.modules["services.worker"]

    try:
        return importlib.import_module("services.worker")
    finally:
        if modulo_original is None:
            del sys.modules["services.printer"]
        else:
            sys.modules["services.printer"] = modulo_original


worker = _importar_worker()


class WorkerSpoolRetentionTest(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        sys.modules.pop("services.worker", None)

    def setUp(self):
        self._old_spool_dir = worker.DIRETORIO_SPOOL
        self._old_retencao = worker.RETENCAO_SPOOL_DIAS
        self._old_listar_protegidos = worker.listar_arquivo_paths_jobs_em_andamento

    def tearDown(self):
        worker.DIRETORIO_SPOOL = self._old_spool_dir
        worker.RETENCAO_SPOOL_DIAS = self._old_retencao
        worker.listar_arquivo_paths_jobs_em_andamento = self._old_listar_protegidos

    def _ajustar_mtime_antigo(self, caminho: Path, *, dias: int):
        instante = time.time() - (dias * 86400)
        os.utime(caminho, (instante, instante))

    def test_limpeza_remove_arquivos_expirados_e_preserva_jobs_em_andamento(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            spool_dir = Path(tmp_dir)
            antigo = spool_dir / "diagnostico.pdf"
            protegido = spool_dir / "pendente.pdf"
            recente = spool_dir / "recente.pdf"
            youtube_antigo = spool_dir / "youtube" / "video.mp4"

            antigo.write_text("antigo", encoding="utf-8")
            protegido.write_text("pendente", encoding="utf-8")
            recente.write_text("recente", encoding="utf-8")
            youtube_antigo.parent.mkdir(parents=True, exist_ok=True)
            youtube_antigo.write_text("video", encoding="utf-8")

            self._ajustar_mtime_antigo(antigo, dias=5)
            self._ajustar_mtime_antigo(protegido, dias=5)
            self._ajustar_mtime_antigo(youtube_antigo, dias=5)

            worker.DIRETORIO_SPOOL = spool_dir
            worker.RETENCAO_SPOOL_DIAS = 2
            worker.listar_arquivo_paths_jobs_em_andamento = lambda: [str(protegido)]

            removidos = worker.limpar_spool_expirado()

            self.assertEqual(removidos, 2)
            self.assertFalse(antigo.exists())
            self.assertTrue(protegido.exists())
            self.assertTrue(recente.exists())
            self.assertFalse(youtube_antigo.exists())
            self.assertFalse((spool_dir / "youtube").exists())

    def test_limpeza_ignora_spool_quando_retencao_esta_desativada(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            spool_dir = Path(tmp_dir)
            arquivo = spool_dir / "diagnostico.pdf"
            arquivo.write_text("antigo", encoding="utf-8")
            self._ajustar_mtime_antigo(arquivo, dias=10)

            worker.DIRETORIO_SPOOL = spool_dir
            worker.RETENCAO_SPOOL_DIAS = 0
            worker.listar_arquivo_paths_jobs_em_andamento = lambda: []

            removidos = worker.limpar_spool_expirado()

            self.assertEqual(removidos, 0)
            self.assertTrue(arquivo.exists())


class WorkerKeepSpoolDefaultTest(unittest.TestCase):
    def setUp(self):
        self._old_keep_spool_files = os.environ.get("KEEP_SPOOL_FILES")

    def tearDown(self):
        if self._old_keep_spool_files is None:
            os.environ.pop("KEEP_SPOOL_FILES", None)
        else:
            os.environ["KEEP_SPOOL_FILES"] = self._old_keep_spool_files
        sys.modules.pop("services.worker", None)

    def test_keep_spool_files_ativo_por_padrao(self):
        os.environ.pop("KEEP_SPOOL_FILES", None)

        worker_mod = _importar_worker()

        self.assertTrue(worker_mod.MANTER_ARQUIVOS_SPOOL)


if __name__ == "__main__":
    unittest.main()
