import importlib
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path

PDF_MINIMO = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


def _reload_modulos(db_path: str, spool_dir: str):
    os.environ["DB_PATH"] = db_path

    config_stub = types.ModuleType("routers.config")
    config_stub.DEFAULT_PRINTER_NAME = "HP_LaserJet"
    config_stub.FORMATOS_UPLOAD_DESCRICAO = "PDF, DOCX, DOC, PNG, JPG ou JPEG"
    config_stub.SPOOL_DIR = spool_dir

    pdf_service_stub = types.ModuleType("services.pdf_service")
    pdf_service_stub.contar_paginas_pdf = lambda _caminho: 4

    sys.modules["routers.config"] = config_stub
    sys.modules["services.pdf_service"] = pdf_service_stub

    for nome_modulo in (
        "database",
        "db.core",
        "db.schema_migrations",
        "routers.common",
        "routers.impressao_router",
    ):
        if nome_modulo in sys.modules:
            del sys.modules[nome_modulo]

    database = importlib.import_module("database")
    impressao_router = importlib.import_module("routers.impressao_router")
    return database, impressao_router


class ImpressaoReusoHistoricoTest(unittest.TestCase):
    def setUp(self):
        self._old_db_path = os.environ.get("DB_PATH")
        self._old_router_config = sys.modules.get("routers.config")
        self._old_pdf_service = sys.modules.get("services.pdf_service")

    def tearDown(self):
        if self._old_db_path is None:
            os.environ.pop("DB_PATH", None)
        else:
            os.environ["DB_PATH"] = self._old_db_path

        if self._old_router_config is None:
            sys.modules.pop("routers.config", None)
        else:
            sys.modules["routers.config"] = self._old_router_config

        if self._old_pdf_service is None:
            sys.modules.pop("services.pdf_service", None)
        else:
            sys.modules["services.pdf_service"] = self._old_pdf_service

    def _criar_cenario_base(self, database, spool_dir: Path):
        database.criar_tabelas()
        database.criar_usuario("Admin", "admin@example.com", "senha123", "admin")
        admin = database.buscar_usuario_por_email("admin@example.com")

        caminho_pdf = spool_dir / "historico.pdf"
        caminho_pdf.write_bytes(PDF_MINIMO)

        job_id = database.criar_job(
            usuario_id=int(admin["id"]),
            arquivo="atividade.docx",
            arquivo_path=str(caminho_pdf),
            copias=1,
            paginas_totais=4,
        )
        database.atualizar_status(job_id, "CONCLUIDO")
        return admin, job_id, caminho_pdf

    def test_preview_job_historico_retorna_pdf_do_spool(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            spool_dir = Path(tmp_dir) / "spool"
            spool_dir.mkdir(parents=True, exist_ok=True)

            database, impressao_router = _reload_modulos(db_path, str(spool_dir))
            admin, job_id, caminho_pdf = self._criar_cenario_base(database, spool_dir)

            resposta = impressao_router.preview_job_historico(job_id, usuario=admin)

            self.assertEqual(resposta.media_type, "application/pdf")
            self.assertEqual(resposta.headers.get("Cache-Control"), "no-store")
            self.assertEqual(resposta.body, caminho_pdf.read_bytes())

    def test_reimprimir_job_historico_cria_novo_job_com_copia_no_spool(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            spool_dir = Path(tmp_dir) / "spool"
            spool_dir.mkdir(parents=True, exist_ok=True)

            database, impressao_router = _reload_modulos(db_path, str(spool_dir))
            admin, job_id, caminho_pdf = self._criar_cenario_base(database, spool_dir)

            resposta = impressao_router.reimprimir_job_historico(
                job_id=job_id,
                copias=2,
                paginas_por_folha=2,
                duplex=True,
                orientacao="retrato",
                intervalo_paginas="1-2",
                professor_id=None,
                usuario=admin,
            )

            self.assertEqual(resposta["mensagem"], "Job criado com sucesso")
            self.assertEqual(resposta["paginas_documento"], 4)
            self.assertEqual(resposta["paginas_selecionadas"], 2)
            self.assertEqual(resposta["paginas_consumidas"], 2)
            self.assertTrue(resposta["cota_ilimitada"])

            jobs = database.listar_jobs_por_usuario(int(admin["id"]))
            self.assertEqual(len(jobs), 2)

            novo_job = next(job for job in jobs if int(job["id"]) != int(job_id))
            self.assertEqual(novo_job["arquivo"], "atividade.docx")
            self.assertEqual(novo_job["status"], "PENDENTE")

            caminho_novo = Path(str(novo_job["arquivo_path"]))
            self.assertTrue(caminho_novo.exists())
            self.assertNotEqual(caminho_novo.resolve(), caminho_pdf.resolve())
            self.assertEqual(caminho_novo.read_bytes(), PDF_MINIMO)


if __name__ == "__main__":
    unittest.main()
