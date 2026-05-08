import importlib
import os
import sqlite3
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


class WorkerQueueNormalizationTest(unittest.TestCase):
    def setUp(self):
        self._old_db_path = os.environ.get("DB_PATH")

    def tearDown(self):
        if self._old_db_path is None:
            os.environ.pop("DB_PATH", None)
        else:
            os.environ["DB_PATH"] = self._old_db_path
        for nome_modulo in ("database", "db.core", "db.schema_migrations"):
            sys.modules.pop(nome_modulo, None)

    def test_normaliza_jobs_processando_e_datas_futuras(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            os.environ["DB_PATH"] = db_path

            database = importlib.import_module("database")
            database.criar_tabelas()
            database.criar_usuario("Admin", "admin@example.com", "senha123", "admin")
            usuario_id = int(database.buscar_usuario_por_email("admin@example.com")["id"])

            job_processando = database.criar_job(
                usuario_id=usuario_id,
                arquivo="processando.pdf",
                arquivo_path="spool/processando.pdf",
                copias=1,
                paginas_totais=1,
            )
            job_futuro = database.criar_job(
                usuario_id=usuario_id,
                arquivo="futuro.pdf",
                arquivo_path="spool/futuro.pdf",
                copias=1,
                paginas_totais=1,
            )

            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("UPDATE jobs SET status = 'PROCESSANDO' WHERE id = ?", (job_processando,))
            cur.execute(
                "UPDATE jobs SET criado_em = datetime('now', '+2 hours') WHERE id = ?",
                (job_futuro,),
            )
            conn.commit()
            conn.close()

            resultado = database.normalizar_jobs_impressao_pendentes(tolerancia_futuro_segundos=60)

            self.assertEqual(resultado["processando_normalizados"], 1)
            self.assertEqual(resultado["datas_normalizadas"], 1)

            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            processando = cur.execute("SELECT status FROM jobs WHERE id = ?", (job_processando,)).fetchone()
            futuro = cur.execute(
                "SELECT datetime(criado_em) <= datetime('now', '+60 seconds') AS ok FROM jobs WHERE id = ?",
                (job_futuro,),
            ).fetchone()
            conn.close()

            self.assertEqual(processando["status"], "PENDENTE")
            self.assertEqual(int(futuro["ok"]), 1)


if __name__ == "__main__":
    unittest.main()
