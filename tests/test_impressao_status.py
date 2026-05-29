import importlib
import io
import os
import sys
import tempfile
import types
import unittest

from fastapi import HTTPException, UploadFile


def _reload_modulos(db_path: str, spool_dir: str):
    os.environ["DB_PATH"] = db_path

    config_stub = types.ModuleType("routers.config")
    config_stub.DEFAULT_PRINTER_NAME = "HP_LaserJet"
    config_stub.FORMATOS_UPLOAD_DESCRICAO = "PDF, DOCX, DOC, PNG, JPG ou JPEG"
    config_stub.SPOOL_DIR = spool_dir

    pdf_service_stub = types.ModuleType("services.pdf_service")
    pdf_service_stub.contar_paginas_pdf = lambda _caminho: 2

    sys.modules["routers.config"] = config_stub
    sys.modules["services.pdf_service"] = pdf_service_stub

    for nome_modulo in (
        "database",
        "db.core",
        "db.schema_migrations",
        "routers.common",
        "routers.admin_router",
        "routers.impressao_router",
    ):
        if nome_modulo in sys.modules:
            del sys.modules[nome_modulo]

    database = importlib.import_module("database")
    admin_router = importlib.import_module("routers.admin_router")
    impressao_router = importlib.import_module("routers.impressao_router")
    return database, admin_router, impressao_router


class ImpressaoStatusTest(unittest.TestCase):
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

    def test_status_impressao_padrao_e_atualizacao_admin(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            spool_dir = os.path.join(tmp_dir, "spool")

            database, admin_router, impressao_router = _reload_modulos(db_path, spool_dir)
            database.criar_tabelas()
            database.criar_usuario("Admin", "admin@example.com", "senha123", "admin")
            admin = database.buscar_usuario_por_email("admin@example.com")

            status_inicial = impressao_router.status_impressao(_usuario=admin)
            self.assertFalse(status_inicial["sem_papel"])

            payload = types.SimpleNamespace(
                sem_papel=True,
                mensagem="Impressora sem papel. Aguarde a reposicao.",
            )
            atualizado = admin_router.atualizar_status_impressao_admin(payload, usuario=admin)

            self.assertTrue(atualizado["sem_papel"])
            self.assertEqual(atualizado["mensagem"], "Impressora sem papel. Aguarde a reposicao.")

            status_final = impressao_router.status_impressao(_usuario=admin)
            self.assertTrue(status_final["sem_papel"])
            self.assertEqual(status_final["mensagem"], "Impressora sem papel. Aguarde a reposicao.")

    def test_imprimir_retorna_409_quando_sem_papel(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            spool_dir = os.path.join(tmp_dir, "spool")

            database, _admin_router, impressao_router = _reload_modulos(db_path, spool_dir)
            database.criar_tabelas()
            database.criar_professor(
                nome="Professor Teste",
                email="prof@example.com",
                senha_hash=database.hash_senha("Senha@123"),
                data_nascimento="1990-01-10",
                aulas_semanais=10,
                turmas_quantidade=1,
                turmas=["7A"],
                disciplinas=["Matematica"],
            )
            professor = database.buscar_usuario_por_email("prof@example.com")
            database.atualizar_status_impressao(
                sem_papel=True,
                mensagem="Sem papel no momento.",
            )

            arquivo = UploadFile(filename="atividade.pdf", file=io.BytesIO(b"pdf-falso"))

            with self.assertRaises(HTTPException) as ctx:
                impressao_router.imprimir(
                    copias=1,
                    arquivo=arquivo,
                    paginas_por_folha=1,
                    duplex=False,
                    orientacao="retrato",
                    intervalo_paginas="",
                    tags=["Atividade"],
                    professor_id=None,
                    usuario=professor,
                )

            self.assertEqual(ctx.exception.status_code, 409)
            self.assertEqual(ctx.exception.detail, "Sem papel no momento.")

    def test_coordenador_tem_cota_ilimitada_na_impressao(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            spool_dir = os.path.join(tmp_dir, "spool")

            database, _admin_router, impressao_router = _reload_modulos(db_path, spool_dir)
            database.criar_tabelas()
            database.criar_coordenador(
                nome="Coordenadora",
                email="coord@example.com",
                senha_hash=database.hash_senha("Senha@123"),
                data_nascimento="1988-03-12",
            )
            coordenadora = database.buscar_usuario_por_email("coord@example.com")

            cota = impressao_router.minha_cota(professor_id=None, usuario=coordenadora)

            self.assertTrue(cota["ilimitada"])
            self.assertIsNone(cota["limite"])
            self.assertIsNone(cota["restante"])


if __name__ == "__main__":
    unittest.main()
