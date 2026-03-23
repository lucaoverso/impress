import importlib
import os
import sys
import tempfile
import unittest


def _reload_modulos(db_path: str):
    os.environ["DB_PATH"] = db_path
    for nome_modulo in ("database", "ocorrencias_router"):
        if nome_modulo in sys.modules:
            del sys.modules[nome_modulo]
    database = importlib.import_module("database")
    ocorrencias_router = importlib.import_module("ocorrencias_router")
    return database, ocorrencias_router


class CoordenacaoOpcoesTest(unittest.TestCase):
    def setUp(self):
        self._old_db_path = os.environ.get("DB_PATH")

    def tearDown(self):
        if self._old_db_path is None:
            os.environ.pop("DB_PATH", None)
        else:
            os.environ["DB_PATH"] = self._old_db_path

    def test_opcoes_ocorrencias_incluem_disciplinas_ativas(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, ocorrencias_router = _reload_modulos(db_path)
            database.criar_tabelas()

            resposta = ocorrencias_router.listar_opcoes_ocorrencias(
                usuario={"cargo": "ADMIN"}
            )

            self.assertIn("disciplinas", resposta)
            self.assertTrue(isinstance(resposta["disciplinas"], list))
            self.assertGreater(len(resposta["disciplinas"]), 0)
            nomes = {item["nome"] for item in resposta["disciplinas"]}
            self.assertIn("Português", nomes)


if __name__ == "__main__":
    unittest.main()
