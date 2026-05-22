import importlib
import os
import sys
import tempfile
import unittest


def _reload_modules(db_path: str):
    os.environ["DB_PATH"] = db_path
    os.environ["ENABLE_EMBEDDED_WORKER"] = "0"

    for module_name in (
        "services.auth_service",
        "auth",
        "ocorrencias_router",
        "routers.ocorrencias_router",
        "pcpi_router",
        "routers.pcpi_router",
        "preconselho_router",
        "routers.preconselho_router",
        "database",
        "main",
        "models",
    ):
        if module_name in sys.modules:
            del sys.modules[module_name]

    database = importlib.import_module("database")
    main = importlib.import_module("main")
    models = importlib.import_module("models")
    return database, main, models


class AdminTurmasDisciplinasTest(unittest.TestCase):
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

    def _usuario_admin(self) -> dict:
        return {"id": 1, "perfil": "admin", "cargo": "ADMIN"}

    def test_admin_gerencia_turma_disciplina_com_carga_e_professor(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, main, models = _reload_modules(db_path)
            database.criar_tabelas()

            professor_id = int(
                database.criar_professor(
                    nome="Professor Alex",
                    email="alex@escola.local",
                    senha_hash=database.hash_senha("Senha@123"),
                    data_nascimento="1987-04-11",
                    aulas_semanais=12,
                    turmas_quantidade=1,
                    turmas=["1 EM A"],
                    disciplinas=["Geometria"],
                )
            )
            turma_id = int(database.criar_turma("1 EM A", "VESPERTINO_EM", 30))
            disciplina_id = int(database.criar_disciplina("Geometria", 3))

            contexto = main.listar_contexto_turmas_disciplinas_admin(usuario=self._usuario_admin())
            self.assertTrue(any(int(item["id"]) == turma_id for item in contexto["turmas"]))
            self.assertTrue(
                any(int(item["id"]) == disciplina_id for item in contexto["disciplinas"])
            )
            self.assertTrue(
                any(int(item["id"]) == professor_id for item in contexto["professores"])
            )

            vinculo = main.criar_turma_disciplina_admin_api(
                payload=models.TurmaDisciplinaCreateIn(
                    turma_id=turma_id,
                    disciplina_id=disciplina_id,
                    carga_horaria=4,
                    professor_id=professor_id,
                ),
                usuario=self._usuario_admin(),
            )
            self.assertEqual(int(vinculo["turma_id"]), turma_id)
            self.assertEqual(int(vinculo["disciplina_id"]), disciplina_id)
            self.assertEqual(int(vinculo["carga_horaria"]), 4)
            self.assertEqual(int(vinculo["professor_id"]), professor_id)

            atribuicoes = database.listar_atribuicoes_docentes(
                professor_id=professor_id,
                disciplina_id=disciplina_id,
                incluir_inativos=True,
            )
            self.assertEqual(len(atribuicoes), 1)
            self.assertEqual(int(atribuicoes[0]["turma_id"]), turma_id)

            atualizado = main.atualizar_turma_disciplina_admin_api(
                turma_disciplina_id=int(vinculo["id"]),
                payload=models.TurmaDisciplinaUpdateIn(
                    carga_horaria=5,
                    professor_id=None,
                ),
                usuario=self._usuario_admin(),
            )
            self.assertEqual(int(atualizado["carga_horaria"]), 5)
            self.assertIsNone(atualizado["professor_id"])

            atribuicoes_apos = database.listar_atribuicoes_docentes(
                professor_id=professor_id,
                disciplina_id=disciplina_id,
                incluir_inativos=True,
            )
            self.assertEqual(atribuicoes_apos, [])

            resposta = main.excluir_turma_disciplina_admin_api(
                turma_disciplina_id=int(vinculo["id"]),
                usuario=self._usuario_admin(),
            )
            self.assertEqual(resposta["mensagem"], "Disciplina removida da turma com sucesso.")
            self.assertEqual(database.listar_turmas_disciplinas_admin(incluir_inativos=True), [])

    def test_admin_pode_criar_disciplina_nova_direto_na_turma(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, main, models = _reload_modules(db_path)
            database.criar_tabelas()

            turma_id = int(database.criar_turma("6 ano A", "MATUTINO", 28))

            vinculo = main.criar_turma_disciplina_admin_api(
                payload=models.TurmaDisciplinaCreateIn(
                    turma_id=turma_id,
                    disciplina_nome="Projeto de Vida",
                    carga_horaria=2,
                    professor_id=None,
                ),
                usuario=self._usuario_admin(),
            )

            self.assertEqual(vinculo["disciplina_nome"], "Projeto de Vida")
            self.assertEqual(int(vinculo["carga_horaria"]), 2)
            self.assertIsNone(vinculo["professor_id"])

            disciplinas = database.listar_disciplinas(incluir_inativas=True)
            projeto = next(
                (item for item in disciplinas if item["nome"] == "Projeto de Vida"), None
            )
            self.assertIsNotNone(projeto)
            self.assertEqual(int(projeto["aulas_semanais"]), 2)
            self.assertFalse(bool(projeto["tem_apc"]))
            self.assertFalse(bool(projeto["tem_prova_bimestral"]))

            turma_disciplinas = database.listar_turmas_disciplinas_admin(
                turma_id=turma_id,
                incluir_inativos=True,
            )
            self.assertEqual(len(turma_disciplinas), 1)
            self.assertEqual(turma_disciplinas[0]["disciplina_nome"], "Projeto de Vida")

    def test_admin_define_flags_de_apc_e_prova_bimestral_na_disciplina(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, main, models = _reload_modules(db_path)
            database.criar_tabelas()

            resposta = main.criar_disciplina_admin(
                payload=models.DisciplinaCreateIn(
                    nome="Ciencias Aplicadas",
                    aulas_semanais=4,
                    tem_apc=True,
                    tem_prova_bimestral=False,
                ),
                usuario=self._usuario_admin(),
            )
            disciplina_id = int(resposta["disciplina_id"])

            disciplina = database.buscar_disciplina_por_id(disciplina_id)
            self.assertIsNotNone(disciplina)
            self.assertTrue(bool(disciplina["tem_apc"]))
            self.assertFalse(bool(disciplina["tem_prova_bimestral"]))

            retorno = main.atualizar_disciplina_admin(
                disciplina_id=disciplina_id,
                payload=models.DisciplinaUpdateIn(
                    aulas_semanais=5,
                    tem_apc=False,
                    tem_prova_bimestral=True,
                ),
                usuario=self._usuario_admin(),
            )
            self.assertEqual(
                retorno["mensagem"],
                "Dados da disciplina atualizados com sucesso.",
            )

            disciplina_atualizada = database.buscar_disciplina_por_id(disciplina_id)
            self.assertEqual(int(disciplina_atualizada["aulas_semanais"]), 5)
            self.assertFalse(bool(disciplina_atualizada["tem_apc"]))
            self.assertTrue(bool(disciplina_atualizada["tem_prova_bimestral"]))


if __name__ == "__main__":
    unittest.main()
