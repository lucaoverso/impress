import importlib
import os
import sys
import tempfile
import unittest


def _reload_modulos(db_path: str):
    os.environ["DB_PATH"] = db_path
    for nome_modulo in ("database", "services.csv_import_service"):
        if nome_modulo in sys.modules:
            del sys.modules[nome_modulo]
    database = importlib.import_module("database")
    csv_import_service = importlib.import_module("services.csv_import_service")
    return database, csv_import_service


class CsvImportServiceTest(unittest.TestCase):
    def setUp(self):
        self._old_db_path = os.environ.get("DB_PATH")

    def tearDown(self):
        if self._old_db_path is None:
            os.environ.pop("DB_PATH", None)
        else:
            os.environ["DB_PATH"] = self._old_db_path

    def test_importa_estudantes_csv_criando_e_atualizando_sem_duplicar(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, csv_import_service = _reload_modulos(db_path)
            database.criar_tabelas()
            turma_id = database.criar_turma("8 B")

            resultado_inicial = csv_import_service.importar_estudantes_csv(
                (
                    "nome,turma,ativo\n"
                    "Ana Maria Souza,8 B,ativo\n"
                    "Bruno Lima,8 B,inativo\n"
                ).encode("utf-8")
            )

            self.assertEqual(resultado_inicial["criados"], 2)
            self.assertEqual(resultado_inicial["atualizados"], 0)
            self.assertEqual(resultado_inicial["erros"], 0)

            resultado_reenvio = csv_import_service.importar_estudantes_csv(
                (
                    "nome,turma,ativo\n"
                    "Ana Maria Souza,8 B,inativo\n"
                    "Bruno Lima,8 B,ativo\n"
                ).encode("utf-8")
            )

            self.assertEqual(resultado_reenvio["criados"], 0)
            self.assertEqual(resultado_reenvio["atualizados"], 2)
            self.assertEqual(resultado_reenvio["erros"], 0)

            estudantes = database.listar_estudantes(
                incluir_inativos=True,
                turma_id=turma_id,
            )
            self.assertEqual(len(estudantes), 2)
            estudante_ana = next(item for item in estudantes if item["nome"] == "Ana Maria Souza")
            estudante_bruno = next(item for item in estudantes if item["nome"] == "Bruno Lima")
            self.assertEqual(int(estudante_ana["ativo"]), 0)
            self.assertEqual(int(estudante_bruno["ativo"]), 1)

    def test_importa_base_legal_csv_com_aliases_e_atualiza_item_existente(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, csv_import_service = _reload_modulos(db_path)
            database.criar_tabelas()

            resultado_inicial = csv_import_service.importar_base_legal_csv(
                (
                    "referencia;texto;status\n"
                    "Art. 76 - VII;Integrar-se ao processo pedagogico desenvolvido pela unidade escolar.;ativo\n"
                ).encode("utf-8")
            )

            self.assertEqual(resultado_inicial["criados"], 1)
            self.assertEqual(resultado_inicial["atualizados"], 0)
            self.assertEqual(resultado_inicial["erros"], 0)

            resultado_reenvio = csv_import_service.importar_base_legal_csv(
                (
                    "artigo,descricao,ativo\n"
                    "\"Art. 76 - VII\",\"Descricao atualizada para o item legal.\",inativo\n"
                ).encode("utf-8")
            )

            self.assertEqual(resultado_reenvio["criados"], 0)
            self.assertEqual(resultado_reenvio["atualizados"], 1)
            self.assertEqual(resultado_reenvio["erros"], 0)

            itens = database.listar_regimento_itens(incluir_inativos=True)
            self.assertEqual(len(itens), 1)
            self.assertEqual(itens[0]["artigo"], "Art. 76 - VII")
            self.assertEqual(itens[0]["descricao"], "Descricao atualizada para o item legal.")
            self.assertEqual(int(itens[0]["ativo"]), 0)

    def test_importa_estudantes_csv_com_sucesso_parcial(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, csv_import_service = _reload_modulos(db_path)
            database.criar_tabelas()
            database.criar_turma("9 A")

            resultado = csv_import_service.importar_estudantes_csv(
                (
                    "nome,turma,ativo\n"
                    "Clara Alves,9 A,ativo\n"
                    "Diego Souza,Turma Inexistente,ativo\n"
                ).encode("utf-8")
            )

            self.assertEqual(resultado["criados"], 1)
            self.assertEqual(resultado["atualizados"], 0)
            self.assertEqual(resultado["erros"], 1)
            self.assertEqual(len(resultado["detalhes_erros"]), 1)
            self.assertIn("Linha 3", resultado["detalhes_erros"][0])


if __name__ == "__main__":
    unittest.main()
