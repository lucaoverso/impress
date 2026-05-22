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


class AdminAtribuicoesDocentesTest(unittest.TestCase):
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

    def test_admin_gerencia_atribuicoes_docentes(self):
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
                    turmas_quantidade=2,
                    turmas=["1 EM A", "6 ano A"],
                    disciplinas=["Geometria", "Letramento e Raciocinio Matematico"],
                )
            )
            turma_em_id = int(database.criar_turma("1 EM A", "VESPERTINO_EM", 30))
            turma_fund_id = int(database.criar_turma("6 ano A", "MATUTINO", 28))
            geometria_id = int(database.criar_disciplina("Geometria", 3))
            letramento_id = int(database.criar_disciplina("Letramento e Raciocinio Matematico", 5))

            contexto = main.listar_contexto_atribuicoes_docentes_admin(
                usuario=self._usuario_admin()
            )
            self.assertTrue(
                any(int(item["id"]) == professor_id for item in contexto["professores"])
            )
            self.assertTrue(any(int(item["id"]) == turma_em_id for item in contexto["turmas"]))
            self.assertTrue(
                any(int(item["id"]) == geometria_id for item in contexto["disciplinas"])
            )

            atribuicao_em = main.criar_atribuicao_docente_admin_api(
                payload=models.ProfessorTurmaDisciplinaCreateIn(
                    professor_id=professor_id,
                    turma_id=turma_em_id,
                    disciplina_id=geometria_id,
                ),
                usuario=self._usuario_admin(),
            )
            atribuicao_fund = main.criar_atribuicao_docente_admin_api(
                payload=models.ProfessorTurmaDisciplinaCreateIn(
                    professor_id=professor_id,
                    turma_id=turma_fund_id,
                    disciplina_id=letramento_id,
                ),
                usuario=self._usuario_admin(),
            )

            self.assertEqual(int(atribuicao_em["professor_id"]), professor_id)
            self.assertEqual(atribuicao_em["turma_nome"], "1 EM A")
            self.assertEqual(
                atribuicao_fund["disciplina_nome"], "Letramento e Raciocinio Matematico"
            )

            listagem = main.listar_atribuicoes_docentes_admin_api(usuario=self._usuario_admin())
            self.assertEqual(len(listagem), 2)

            listagem_filtrada = main.listar_atribuicoes_docentes_admin_api(
                professor_id=professor_id,
                turma_id=turma_em_id,
                usuario=self._usuario_admin(),
            )
            self.assertEqual(len(listagem_filtrada), 1)
            self.assertEqual(int(listagem_filtrada[0]["disciplina_id"]), geometria_id)

            with self.assertRaises(main.HTTPException) as ctx:
                main.criar_atribuicao_docente_admin_api(
                    payload=models.ProfessorTurmaDisciplinaCreateIn(
                        professor_id=professor_id,
                        turma_id=turma_em_id,
                        disciplina_id=geometria_id,
                    ),
                    usuario=self._usuario_admin(),
                )
            self.assertEqual(ctx.exception.status_code, 409)

            resposta_exclusao = main.excluir_atribuicao_docente_admin_api(
                atribuicao_id=int(atribuicao_em["id"]),
                usuario=self._usuario_admin(),
            )
            self.assertEqual(
                resposta_exclusao["mensagem"], "Atribuicao docente removida com sucesso."
            )

            listagem_final = main.listar_atribuicoes_docentes_admin_api(
                usuario=self._usuario_admin()
            )
            self.assertEqual(len(listagem_final), 1)
            self.assertEqual(int(listagem_final[0]["turma_id"]), turma_fund_id)

    def test_admin_sincroniza_turmas_por_professor_e_disciplina(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, main, models = _reload_modules(db_path)
            database.criar_tabelas()

            professor_id = int(
                database.criar_professor(
                    nome="Professor Lote",
                    email="lote@escola.local",
                    senha_hash=database.hash_senha("Senha@123"),
                    data_nascimento="1988-03-18",
                    aulas_semanais=15,
                    turmas_quantidade=3,
                    turmas=["7A", "7B", "8A"],
                    disciplinas=["Matematica"],
                )
            )
            turma_a_id = int(database.criar_turma("7A", "MATUTINO", 30))
            turma_b_id = int(database.criar_turma("7B", "MATUTINO", 30))
            turma_c_id = int(database.criar_turma("8A", "VESPERTINO", 28))
            disciplina_id = int(database.criar_disciplina("Matematica", 5))

            resposta_inicial = main.sincronizar_atribuicoes_docentes_admin_api(
                payload=models.ProfessorDisciplinaTurmasSyncIn(
                    professor_id=professor_id,
                    disciplina_id=disciplina_id,
                    turma_ids=[turma_a_id, turma_b_id],
                ),
                usuario=self._usuario_admin(),
            )
            self.assertEqual(int(resposta_inicial["criados"]), 2)
            self.assertEqual(int(resposta_inicial["removidos"]), 0)
            self.assertEqual(int(resposta_inicial["total_ativo"]), 2)

            resposta_atualizacao = main.sincronizar_atribuicoes_docentes_admin_api(
                payload=models.ProfessorDisciplinaTurmasSyncIn(
                    professor_id=professor_id,
                    disciplina_id=disciplina_id,
                    turma_ids=[turma_b_id, turma_c_id],
                ),
                usuario=self._usuario_admin(),
            )
            self.assertEqual(int(resposta_atualizacao["criados"]), 1)
            self.assertEqual(int(resposta_atualizacao["removidos"]), 1)
            self.assertEqual(int(resposta_atualizacao["total_ativo"]), 2)

            listagem = main.listar_atribuicoes_docentes_admin_api(
                professor_id=professor_id,
                disciplina_id=disciplina_id,
                usuario=self._usuario_admin(),
            )
            turma_ids = sorted(int(item["turma_id"]) for item in listagem)
            self.assertEqual(turma_ids, sorted([turma_b_id, turma_c_id]))


if __name__ == "__main__":
    unittest.main()
