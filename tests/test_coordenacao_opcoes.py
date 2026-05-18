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
            database.criar_regimento_item(
                lei_nome="Regimento Interno",
                artigo_numero="76",
                artigo_descricao="Dos deveres do estudante.",
                inciso_numero="VII",
                inciso_descricao="Integrar-se ao processo pedagogico desenvolvido pela unidade escolar.",
            )

            resposta = ocorrencias_router.listar_opcoes_ocorrencias(usuario={"cargo": "ADMIN"})

            self.assertIn("disciplinas", resposta)
            self.assertTrue(isinstance(resposta["disciplinas"], list))
            self.assertGreater(len(resposta["disciplinas"]), 0)
            nomes = {item["nome"] for item in resposta["disciplinas"]}
            self.assertIn("Portugu\u00eas", nomes)
            self.assertIn("tipos_registro", resposta)
            self.assertEqual(
                {item["id"] for item in resposta["tipos_registro"]},
                {"estudante", "professor", "geral"},
            )
            self.assertIn("regimento_itens", resposta)
            self.assertTrue(
                any(item["lei_nome"] == "Regimento Interno" for item in resposta["regimento_itens"])
            )
            self.assertIn("leis", resposta)
            self.assertTrue(any(item["nome"] == "Regimento Interno" for item in resposta["leis"]))
            self.assertIn("artigos", resposta)
            self.assertTrue(any(item["numero"] == "76" for item in resposta["artigos"]))
            self.assertIn("incisos", resposta)
            self.assertTrue(any(item["numero"] == "VII" for item in resposta["incisos"]))
            self.assertIn("alineas", resposta)
            self.assertEqual(resposta["alineas"], [])


if __name__ == "__main__":
    unittest.main()
