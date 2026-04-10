import importlib
import os
import sys
import tempfile
import unittest


def _reload_modulos(db_path: str):
    os.environ["DB_PATH"] = db_path
    os.environ["ENABLE_EMBEDDED_WORKER"] = "0"

    for nome_modulo in (
        "services.atribuicoes_docentes_import_service",
        "database",
    ):
        if nome_modulo in sys.modules:
            del sys.modules[nome_modulo]

    database = importlib.import_module("database")
    import_service = importlib.import_module("services.atribuicoes_docentes_import_service")
    return database, import_service


class AtribuicoesDocentesImportServiceTest(unittest.TestCase):
    def setUp(self):
        self._old_db_path = os.environ.get("DB_PATH")
        self._old_embedded_worker = os.environ.get("ENABLE_EMBEDDED_WORKER")

    def tearDown(self):
        if self._old_db_path is None:
            os.environ.pop("DB_PATH", None)
        else:
            os.environ["DB_PATH"] = self._old_db_path

        if self._old_embedded_worker is None:
            os.environ.pop("ENABLE_EMBEDDED_WORKER", None)
        else:
            os.environ["ENABLE_EMBEDDED_WORKER"] = self._old_embedded_worker

    def test_importa_atribuicoes_docentes_json_e_sincroniza_turmas(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, import_service = _reload_modulos(db_path)
            database.criar_tabelas()

            professor_id = int(
                database.criar_professor(
                    nome="Professor Alex",
                    email="alex@escola.local",
                    senha_hash=database.hash_senha("Senha@123"),
                    data_nascimento="1987-04-11",
                    aulas_semanais=12,
                    turmas_quantidade=3,
                    turmas=["1 EM A", "1 EM B", "6 ano A"],
                    disciplinas=["Geometria", "Letramento e Raciocinio Matematico"],
                )
            )
            turma_em_a_id = int(database.criar_turma("1 EM A", "VESPERTINO_EM", 30))
            turma_em_b_id = int(database.criar_turma("1 EM B", "VESPERTINO_EM", 30))
            turma_fund_id = int(database.criar_turma("6 ano A", "MATUTINO", 28))
            geometria_id = int(database.criar_disciplina("Geometria", 3))
            letramento_id = int(database.criar_disciplina("Letramento e Raciocinio Matematico", 5))

            resultado_inicial = import_service.importar_atribuicoes_docentes_arquivo(
                (
                    "{"
                    "\"atribuicoes\": ["
                    "  {"
                    "    \"professor_nome\": \"Professor Alex\","
                    "    \"disciplina\": \"Geometria\","
                    "    \"turmas\": [\"1 EM A\", \"1 EM B\"]"
                    "  },"
                    "  {"
                    "    \"professor_nome\": \"Professor Alex\","
                    "    \"disciplina\": \"Letramento e Raciocinio Matematico\","
                    "    \"turmas\": [\"6 ano A\"]"
                    "  }"
                    "]"
                    "}"
                ).encode("utf-8"),
                nome_arquivo="atribuicoes_docentes.json",
                tipo_conteudo="application/json",
            )

            self.assertEqual(resultado_inicial["importados"], 2)
            self.assertEqual(resultado_inicial["erros"], 0)

            atribuicoes_iniciais = database.listar_atribuicoes_docentes(
                professor_id=professor_id,
                incluir_inativos=True,
            )
            pares_iniciais = {
                (int(item["disciplina_id"]), int(item["turma_id"]))
                for item in atribuicoes_iniciais
            }
            self.assertEqual(
                pares_iniciais,
                {
                    (geometria_id, turma_em_a_id),
                    (geometria_id, turma_em_b_id),
                    (letramento_id, turma_fund_id),
                },
            )

            resultado_reenvio = import_service.importar_atribuicoes_docentes_arquivo(
                (
                    "{"
                    "\"atribuicoes\": ["
                    "  {"
                    "    \"professor_nome\": \"Professor Alex\","
                    "    \"disciplina\": \"Geometria\","
                    "    \"turmas\": [\"1 EM B\"]"
                    "  }"
                    "]"
                    "}"
                ).encode("utf-8"),
                nome_arquivo="atribuicoes_docentes.json",
                tipo_conteudo="application/json",
            )

            self.assertEqual(resultado_reenvio["importados"], 1)
            self.assertEqual(resultado_reenvio["removidos"], 1)

            atribuicoes_geometria = database.listar_atribuicoes_docentes(
                professor_id=professor_id,
                disciplina_id=geometria_id,
                incluir_inativos=True,
            )
            turma_ids_geometria = [int(item["turma_id"]) for item in atribuicoes_geometria]
            self.assertEqual(turma_ids_geometria, [turma_em_b_id])


if __name__ == "__main__":
    unittest.main()
