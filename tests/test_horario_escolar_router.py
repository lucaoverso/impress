import importlib
import os
import sys
import tempfile
import unittest

from fastapi import HTTPException


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


def _seed_grade_aulas(database) -> None:
    itens = [
        (1, "AULA", 1, "Aula 1", "07:00", "07:50"),
        (2, "AULA", 2, "Aula 2", "07:50", "08:40"),
        (3, "INTERVALO", None, "Intervalo da manha", "08:40", "09:00"),
        (4, "AULA", 3, "Aula 3", "09:00", "09:50"),
        (5, "AULA", 4, "Aula 4", "09:50", "10:40"),
        (6, "AULA", 5, "Aula 5", "10:40", "11:30"),
        (7, "AULA", 6, "Aula 6", "13:00", "13:50"),
        (8, "AULA", 7, "Aula 7", "13:50", "14:40"),
        (9, "INTERVALO", None, "Intervalo da tarde", "14:40", "15:00"),
        (10, "AULA", 8, "Aula 8", "15:00", "15:50"),
        (11, "AULA", 9, "Aula 9", "15:50", "16:40"),
        (12, "AULA", 10, "Aula 10", "16:40", "17:30"),
        (13, "AULA", 11, "Aula 11", "17:30", "18:20"),
    ]
    for ordem_visual, tipo, aula_numero, nome, horario_inicio, horario_fim in itens:
        database.criar_configuracao_aula(
            ordem_visual=ordem_visual,
            tipo=tipo,
            aula_numero=aula_numero,
            nome=nome,
            horario_inicio=horario_inicio,
            horario_fim=horario_fim,
            ativo=True,
        )


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

    def _usuario_professor(self, usuario_id: int) -> dict:
        return {"id": usuario_id, "nome": "Professor", "cargo": "PROFESSOR"}

    def test_crud_basico_do_horario_escolar(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, models, horario_router = _reload_modules(db_path)
            database.criar_tabelas()
            _seed_grade_aulas(database)

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
            self.assertEqual(int(criado["faixa_global"]), 3)

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
                "Registro do horário escolar removido com sucesso.",
            )
            self.assertEqual(database.listar_horarios_escolares(ano_letivo=2031), [])

    def test_matriz_da_turma_retorna_cards_por_carga_horaria(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, models, horario_router = _reload_modules(db_path)
            database.criar_tabelas()
            _seed_grade_aulas(database)

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
            self.assertEqual(
                [item["tipo"] for item in matriz["faixas"]],
                ["AULA", "AULA", "INTERVALO", "AULA", "AULA", "AULA"],
            )
            self.assertEqual([item["faixa_global"] for item in matriz["faixas"]], [1, 2, 0, 3, 4, 5])
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

    def test_conflito_do_professor_considera_faixa_global_em_vez_de_aula_relativa(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, models, horario_router = _reload_modules(db_path)
            database.criar_tabelas()
            _seed_grade_aulas(database)

            turma_matutino_id = int(database.criar_turma("7A", "MATUTINO", 30))
            turma_vespertino_id = int(database.criar_turma("8A", "VESPERTINO", 30))
            turma_integral_id = int(database.criar_turma("9A", "INTEGRAL", 30))
            disciplina_id = int(database.criar_disciplina("Matematica", 5))
            professor_id = int(
                database.criar_professor(
                    nome="Professor Faixas",
                    email="faixas@escola.local",
                    senha_hash=database.hash_senha("Senha@123"),
                    data_nascimento="1987-09-17",
                    aulas_semanais=20,
                    turmas_quantidade=3,
                    turmas=["7A", "8A", "9A"],
                    disciplinas=["Matematica"],
                )
            )

            database.criar_atribuicao_docente(professor_id, turma_matutino_id, disciplina_id)
            database.criar_atribuicao_docente(professor_id, turma_vespertino_id, disciplina_id)
            database.criar_atribuicao_docente(professor_id, turma_integral_id, disciplina_id)

            matutino = horario_router.criar_horario_escolar_api(
                payload=models.HorarioEscolarRegistroIn(
                    ano_letivo=2033,
                    turma_id=turma_matutino_id,
                    disciplina_id=disciplina_id,
                    professor_id=professor_id,
                    dia_semana="segunda",
                    aula_numero=1,
                ),
                usuario=self._usuario_coord(),
            )
            self.assertEqual(int(matutino["faixa_global"]), 1)

            with self.assertRaises(HTTPException) as ctx_janela:
                horario_router.criar_horario_escolar_api(
                    payload=models.HorarioEscolarRegistroIn(
                        ano_letivo=2033,
                        turma_id=turma_vespertino_id,
                        disciplina_id=disciplina_id,
                        professor_id=professor_id,
                        dia_semana="segunda",
                        aula_numero=1,
                    ),
                    usuario=self._usuario_coord(),
                )
            self.assertEqual(int(ctx_janela.exception.status_code), 400)
            self.assertIn("janela", str(ctx_janela.exception.detail).lower())

            vespertino = horario_router.criar_horario_escolar_api(
                payload=models.HorarioEscolarRegistroIn(
                    ano_letivo=2033,
                    turma_id=turma_vespertino_id,
                    disciplina_id=disciplina_id,
                    professor_id=professor_id,
                    dia_semana="segunda",
                    aula_numero=6,
                ),
                usuario=self._usuario_coord(),
            )
            self.assertEqual(int(vespertino["faixa_global"]), 6)

            with self.assertRaises(HTTPException) as ctx_integral_seis:
                horario_router.criar_horario_escolar_api(
                    payload=models.HorarioEscolarRegistroIn(
                        ano_letivo=2033,
                        turma_id=turma_integral_id,
                        disciplina_id=disciplina_id,
                        professor_id=professor_id,
                        dia_semana="segunda",
                        aula_numero=6,
                    ),
                    usuario=self._usuario_coord(),
                )
            self.assertEqual(int(ctx_integral_seis.exception.status_code), 400)

            integral_vespertino = horario_router.criar_horario_escolar_api(
                payload=models.HorarioEscolarRegistroIn(
                    ano_letivo=2033,
                    turma_id=turma_integral_id,
                    disciplina_id=disciplina_id,
                    professor_id=professor_id,
                    dia_semana="segunda",
                    aula_numero=7,
                ),
                usuario=self._usuario_coord(),
            )
            self.assertEqual(int(integral_vespertino["faixa_global"]), 7)

            with self.assertRaises(HTTPException) as ctx:
                horario_router.criar_horario_escolar_api(
                    payload=models.HorarioEscolarRegistroIn(
                        ano_letivo=2033,
                        turma_id=turma_integral_id,
                        disciplina_id=disciplina_id,
                        professor_id=professor_id,
                        dia_semana="segunda",
                        aula_numero=1,
                    ),
                    usuario=self._usuario_coord(),
                )

            self.assertEqual(int(ctx.exception.status_code), 409)
            self.assertIn("faixa", str(ctx.exception.detail).lower())

    def test_matriz_integral_exibe_registro_legado_fora_da_janela(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, models, horario_router = _reload_modules(db_path)
            database.criar_tabelas()
            _seed_grade_aulas(database)

            turma_id = int(database.criar_turma("Integral A", "INTEGRAL", 28))
            disciplina_id = int(database.criar_disciplina("Matematica", 5))
            professor_id = int(
                database.criar_professor(
                    nome="Professor Integral",
                    email="integral@escola.local",
                    senha_hash=database.hash_senha("Senha@123"),
                    data_nascimento="1985-04-10",
                    aulas_semanais=20,
                    turmas_quantidade=1,
                    turmas=["Integral A"],
                    disciplinas=["Matematica"],
                )
            )
            database.criar_ou_atualizar_turma_disciplina(
                turma_id=turma_id,
                disciplina_id=disciplina_id,
                carga_horaria=8,
                professor_usuario_id=professor_id,
            )
            database.criar_horario_escolar(
                ano_letivo=2035,
                turma_id=turma_id,
                disciplina_id=disciplina_id,
                professor_usuario_id=professor_id,
                dia_semana="SEGUNDA",
                aula_numero=6,
                faixa_global=6,
            )

            matriz = horario_router.obter_matriz_horario_turma_api(
                turma_id=turma_id,
                ano_letivo=2035,
                usuario=self._usuario_coord(),
            )

            aulas_faixas = [int(item.get("aula_numero") or 0) for item in matriz["faixas"]]
            self.assertEqual(aulas_faixas, [1, 2, 0, 3, 4, 5, 6, 7, 0, 8, 9])

            faixa_legada = next(
                item for item in matriz["faixas"] if int(item.get("aula_numero") or 0) == 6
            )
            self.assertTrue(faixa_legada["fora_janela_turma"])
            self.assertFalse(faixa_legada["aceita_lancamento"])
            self.assertIn("fora da janela", faixa_legada["label"])
            self.assertEqual(len(matriz["registros"]), 1)
            self.assertEqual(int(matriz["registros"][0]["aula_numero"]), 6)

    def test_professor_pode_visualizar_grade_com_destaque_sem_edicao(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, models, horario_router = _reload_modules(db_path)
            database.criar_tabelas()
            _seed_grade_aulas(database)

            turma_a_id = int(database.criar_turma("7A", "MATUTINO", 30))
            turma_b_id = int(database.criar_turma("8A", "VESPERTINO", 30))
            disciplina_id = int(database.criar_disciplina("Matematica", 5))
            disciplina_colega_id = int(database.criar_disciplina("Historia", 2))
            professor_logado_id = int(
                database.criar_professor(
                    nome="Professor Logado",
                    email="prof.logado@escola.local",
                    senha_hash=database.hash_senha("Senha@123"),
                    data_nascimento="1991-02-14",
                    aulas_semanais=20,
                    turmas_quantidade=2,
                    turmas=["7A", "8A"],
                    disciplinas=["Matematica"],
                )
            )
            professor_colega_id = int(
                database.criar_professor(
                    nome="Professor Colega",
                    email="colega@escola.local",
                    senha_hash=database.hash_senha("Senha@123"),
                    data_nascimento="1989-04-09",
                    aulas_semanais=20,
                    turmas_quantidade=1,
                    turmas=["7A"],
                    disciplinas=["Historia"],
                )
            )

            database.criar_atribuicao_docente(professor_logado_id, turma_a_id, disciplina_id)
            database.criar_atribuicao_docente(professor_logado_id, turma_b_id, disciplina_id)
            database.criar_atribuicao_docente(professor_colega_id, turma_a_id, disciplina_colega_id)
            database.criar_ou_atualizar_turma_disciplina(
                turma_id=turma_a_id,
                disciplina_id=disciplina_id,
                carga_horaria=2,
                professor_usuario_id=professor_logado_id,
            )
            database.criar_ou_atualizar_turma_disciplina(
                turma_id=turma_b_id,
                disciplina_id=disciplina_id,
                carga_horaria=1,
                professor_usuario_id=professor_logado_id,
            )
            database.criar_ou_atualizar_turma_disciplina(
                turma_id=turma_a_id,
                disciplina_id=disciplina_colega_id,
                carga_horaria=1,
                professor_usuario_id=professor_colega_id,
            )

            horario_router.criar_horario_escolar_api(
                payload=models.HorarioEscolarRegistroIn(
                    ano_letivo=2034,
                    turma_id=turma_a_id,
                    disciplina_id=disciplina_id,
                    professor_id=professor_logado_id,
                    dia_semana="segunda",
                    aula_numero=1,
                ),
                usuario=self._usuario_coord(),
            )
            horario_router.criar_horario_escolar_api(
                payload=models.HorarioEscolarRegistroIn(
                    ano_letivo=2034,
                    turma_id=turma_b_id,
                    disciplina_id=disciplina_id,
                    professor_id=professor_logado_id,
                    dia_semana="terca",
                    aula_numero=7,
                ),
                usuario=self._usuario_coord(),
            )
            horario_router.criar_horario_escolar_api(
                payload=models.HorarioEscolarRegistroIn(
                    ano_letivo=2034,
                    turma_id=turma_a_id,
                    disciplina_id=disciplina_colega_id,
                    professor_id=professor_colega_id,
                    dia_semana="quarta",
                    aula_numero=3,
                ),
                usuario=self._usuario_coord(),
            )

            contexto = horario_router.obter_contexto_horario_escolar_api(
                usuario=self._usuario_professor(professor_logado_id),
            )
            self.assertEqual(contexto["modo_interface"], "professor")
            self.assertFalse(contexto["permite_edicao"])
            self.assertEqual(int(contexto["professor_logado_id"]), professor_logado_id)
            self.assertEqual(contexto["professores"], [])
            self.assertEqual(contexto["disciplinas"], [])

            listagem = horario_router.listar_horarios_escolares_api(
                ano_letivo=2034,
                usuario=self._usuario_professor(professor_logado_id),
            )
            self.assertEqual(listagem["modo_interface"], "professor")
            self.assertEqual(int(listagem["professor_logado_id"]), professor_logado_id)
            self.assertEqual(int(listagem["total_registros"]), 3)
            self.assertEqual(len(listagem["grupos_turma"]), 2)

            itens_proprios = [
                item for item in listagem["itens"] if bool(item["eh_do_professor_logado"])
            ]
            itens_colegas = [
                item for item in listagem["itens"] if not bool(item["eh_do_professor_logado"])
            ]
            self.assertEqual(len(itens_proprios), 2)
            self.assertEqual(len(itens_colegas), 1)

            with self.assertRaises(HTTPException) as ctx:
                horario_router.obter_matriz_horario_turma_api(
                    turma_id=turma_a_id,
                    ano_letivo=2034,
                    usuario=self._usuario_professor(professor_logado_id),
                )

            self.assertEqual(int(ctx.exception.status_code), 403)


if __name__ == "__main__":
    unittest.main()
