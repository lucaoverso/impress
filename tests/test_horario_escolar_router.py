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
        "services.horario_escolar_service",
        "auth",
        "database",
        "models",
        "routers.horario_escolar_router",
    ):
        if module_name in sys.modules:
            del sys.modules[module_name]

    database = importlib.import_module("database")
    models = importlib.import_module("models")
    horario_router = importlib.import_module("routers.horario_escolar_router")
    return database, models, horario_router


class HorarioEscolarRouterTest(unittest.TestCase):
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

    def _usuario_coord(self, usuario_id: int = 1) -> dict:
        return {"id": usuario_id, "nome": "Coord", "cargo": "COORDENADOR"}

    def test_crud_basico_do_horario_escolar(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, models, horario_router = _reload_modules(db_path)
            database.criar_tabelas()

            turma_id = int(database.criar_turma("7A", "MATUTINO", 30))
            disciplina_id = int(database.criar_disciplina("Matematica", 5))
            professor_id = int(
                database.criar_professor(
                    nome="Professor Horario",
                    email="horario@escola.local",
                    senha_hash=database.hash_senha("Senha@123"),
                    data_nascimento="1990-03-21",
                    aulas_semanais=10,
                    turmas_quantidade=1,
                    turmas=["7A"],
                    disciplinas=["Matematica"],
                )
            )
            database.criar_atribuicao_docente(professor_id, turma_id, disciplina_id)

            contexto = horario_router.obter_contexto_horario_escolar_api(
                usuario=self._usuario_coord(),
            )
            self.assertTrue(any(int(item["id"]) == turma_id for item in contexto["turmas"]))
            self.assertTrue(any(int(item["id"]) == professor_id for item in contexto["professores"]))

            criado = horario_router.criar_horario_escolar_api(
                payload=models.HorarioEscolarRegistroIn(
                    ano_letivo=2031,
                    turma_id=turma_id,
                    disciplina_id=disciplina_id,
                    professor_id=professor_id,
                    dia_semana="sexta",
                    aula_numero=3,
                ),
                usuario=self._usuario_coord(),
            )
            self.assertEqual(int(criado["ano_letivo"]), 2031)
            self.assertEqual(criado["dia_semana"], "SEXTA")
            self.assertEqual(criado["dia_semana_nome"], "Sexta-feira")

            listagem = horario_router.listar_horarios_escolares_api(
                ano_letivo=2031,
                usuario=self._usuario_coord(),
            )
            self.assertEqual(int(listagem["total_registros"]), 1)
            self.assertEqual(len(listagem["grupos_turma"]), 1)
            self.assertEqual(len(listagem["grupos_professor"]), 1)

            atualizado = horario_router.atualizar_horario_escolar_api(
                registro_id=int(criado["id"]),
                payload=models.HorarioEscolarRegistroUpdateIn(
                    ano_letivo=2031,
                    turma_id=turma_id,
                    disciplina_id=disciplina_id,
                    professor_id=professor_id,
                    dia_semana="quinta",
                    aula_numero=2,
                ),
                usuario=self._usuario_coord(),
            )
            self.assertEqual(atualizado["dia_semana"], "QUINTA")
            self.assertEqual(int(atualizado["aula_numero"]), 2)

            professores_do_dia = horario_router.listar_professores_do_dia_api(
                data="2031-05-08",
                ano_letivo=2031,
                usuario=self._usuario_coord(),
            )
            self.assertEqual(professores_do_dia["dia_semana"], "QUINTA")
            self.assertEqual(int(professores_do_dia["total_professores"]), 1)

            resposta = horario_router.excluir_horario_escolar_api(
                registro_id=int(criado["id"]),
                usuario=self._usuario_coord(),
            )
            self.assertEqual(
                resposta["mensagem"],
                "Registro do horario escolar removido com sucesso.",
            )
            self.assertEqual(database.listar_horarios_escolares(ano_letivo=2031), [])

    def test_matriz_da_turma_retorna_cards_por_carga_horaria(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, models, horario_router = _reload_modules(db_path)
            database.criar_tabelas()

            turma_id = int(database.criar_turma("8B", "MATUTINO", 32))
            disciplina_id = int(database.criar_disciplina("Matematica", 5))
            professor_id = int(
                database.criar_professor(
                    nome="Professor Matriz",
                    email="matriz@escola.local",
                    senha_hash=database.hash_senha("Senha@123"),
                    data_nascimento="1988-07-19",
                    aulas_semanais=20,
                    turmas_quantidade=1,
                    turmas=["8B"],
                    disciplinas=["Matematica"],
                )
            )

            database.criar_ou_atualizar_turma_disciplina(
                turma_id=turma_id,
                disciplina_id=disciplina_id,
                carga_horaria=4,
                professor_usuario_id=professor_id,
            )

            horario_router.criar_horario_escolar_api(
                payload=models.HorarioEscolarRegistroIn(
                    ano_letivo=2032,
                    turma_id=turma_id,
                    disciplina_id=disciplina_id,
                    professor_id=professor_id,
                    dia_semana="segunda",
                    aula_numero=1,
                ),
                usuario=self._usuario_coord(),
            )

            matriz = horario_router.obter_matriz_horario_turma_api(
                turma_id=turma_id,
                ano_letivo=2032,
                usuario=self._usuario_coord(),
            )

            self.assertEqual(int(matriz["ano_letivo"]), 2032)
            self.assertEqual(int(matriz["turma"]["id"]), turma_id)
            self.assertEqual(int(matriz["turma"]["total_aulas"]), 5)
            self.assertEqual(matriz["aulas"], [1, 2, 3, 4, 5])
            self.assertEqual([item["faixa_global"] for item in matriz["faixas"]], [1, 2, 3, 4, 5])
            self.assertEqual(len(matriz["registros"]), 1)
            self.assertEqual(len(matriz["cards_disponiveis"]), 3)
            self.assertEqual(len(matriz["cards_resumo"]), 1)

            resumo = matriz["cards_resumo"][0]
            self.assertEqual(int(resumo["disciplina_id"]), disciplina_id)
            self.assertEqual(int(resumo["professor_id"]), professor_id)
            self.assertEqual(int(resumo["quantidade_total"]), 4)
            self.assertEqual(int(resumo["quantidade_alocada"]), 1)
            self.assertEqual(int(resumo["quantidade_disponivel"]), 3)

            card = matriz["cards_disponiveis"][0]
            self.assertEqual(int(card["turma_id"]), turma_id)
            self.assertEqual(int(card["disciplina_id"]), disciplina_id)
            self.assertEqual(int(card["professor_id"]), professor_id)
            self.assertEqual(int(card["quantidade_total"]), 4)
            self.assertEqual(int(card["indice_disponivel"]), 1)
            self.assertEqual(matriz["alertas"], [])


if __name__ == "__main__":
    unittest.main()
