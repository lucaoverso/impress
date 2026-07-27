import os
import tempfile
import unittest

from fastapi import HTTPException

from tests.test_horario_escolar_router import _reload_modules, _seed_grade_aulas


class HorarioEscolarAulaAtividadeTest(unittest.TestCase):
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

    def test_cria_aloca_desaloca_e_exclui_aula_atividade(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, models, horario_router = _reload_modules(db_path)
            database.criar_tabelas()
            _seed_grade_aulas(database)

            professor_id = int(
                database.criar_professor(
                    nome="Professor Planejamento",
                    email="planejamento@escola.local",
                    senha_hash=database.hash_senha("Senha@123"),
                    data_nascimento="1990-01-10",
                    aulas_semanais=10,
                    turmas_quantidade=0,
                    turmas=[],
                    disciplinas=[],
                )
            )
            usuario_gestor = {"id": 1, "nome": "Coord", "cargo": "COORDENADOR"}

            criada = horario_router.criar_aula_atividade_professor_api(
                payload=models.AulaAtividadeProfessorCreateIn(
                    ano_letivo=2037,
                    professor_id=professor_id,
                ),
                usuario=usuario_gestor,
            )
            self.assertFalse(criada["alocada"])
            self.assertEqual(criada["tipo_registro"], "AULA_ATIVIDADE")

            alocada = horario_router.atualizar_aula_atividade_professor_api(
                registro_id=int(criada["id"]),
                payload=models.AulaAtividadeProfessorUpdateIn(
                    dia_semana="segunda",
                    aula_numero=1,
                ),
                usuario=usuario_gestor,
            )
            self.assertTrue(alocada["alocada"])
            self.assertEqual(alocada["dia_semana"], "SEGUNDA")
            self.assertEqual(int(alocada["faixa_global"]), 1)

            listagem = horario_router.listar_horarios_escolares_api(
                ano_letivo=2037,
                professor_id=professor_id,
                usuario=usuario_gestor,
            )
            self.assertEqual(int(listagem["total_aulas_atividade"]), 1)
            self.assertEqual(listagem["aulas_atividade"][0]["titulo"], "Aula atividade")

            desalocada = horario_router.atualizar_aula_atividade_professor_api(
                registro_id=int(criada["id"]),
                payload=models.AulaAtividadeProfessorUpdateIn(),
                usuario=usuario_gestor,
            )
            self.assertFalse(desalocada["alocada"])

            resposta = horario_router.excluir_aula_atividade_professor_api(
                registro_id=int(criada["id"]),
                usuario=usuario_gestor,
            )
            self.assertEqual(resposta["mensagem"], "Aula atividade excluída com sucesso.")

    def test_conflito_bloqueia_aula_comum_e_aula_atividade_no_mesmo_horario(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, models, horario_router = _reload_modules(db_path)
            database.criar_tabelas()
            _seed_grade_aulas(database)

            turma_id = int(database.criar_turma("7A", "MATUTINO", 30))
            disciplina_id = int(database.criar_disciplina("Matematica", 5))
            professor_id = int(
                database.criar_professor(
                    nome="Professor Conflito",
                    email="conflito.atividade@escola.local",
                    senha_hash=database.hash_senha("Senha@123"),
                    data_nascimento="1987-06-15",
                    aulas_semanais=10,
                    turmas_quantidade=1,
                    turmas=["7A"],
                    disciplinas=["Matematica"],
                )
            )
            database.criar_atribuicao_docente(professor_id, turma_id, disciplina_id)
            usuario_gestor = {"id": 1, "nome": "Coord", "cargo": "COORDENADOR"}

            atividade = horario_router.criar_aula_atividade_professor_api(
                payload=models.AulaAtividadeProfessorCreateIn(
                    ano_letivo=2038,
                    professor_id=professor_id,
                ),
                usuario=usuario_gestor,
            )
            horario_router.atualizar_aula_atividade_professor_api(
                registro_id=int(atividade["id"]),
                payload=models.AulaAtividadeProfessorUpdateIn(
                    dia_semana="terca",
                    aula_numero=2,
                ),
                usuario=usuario_gestor,
            )

            with self.assertRaises(HTTPException) as atividade_primeiro:
                horario_router.criar_horario_escolar_api(
                    payload=models.HorarioEscolarRegistroIn(
                        ano_letivo=2038,
                        turma_id=turma_id,
                        disciplina_id=disciplina_id,
                        professor_id=professor_id,
                        dia_semana="terca",
                        aula_numero=2,
                    ),
                    usuario=usuario_gestor,
                )
            self.assertEqual(int(atividade_primeiro.exception.status_code), 409)

            horario_router.atualizar_aula_atividade_professor_api(
                registro_id=int(atividade["id"]),
                payload=models.AulaAtividadeProfessorUpdateIn(),
                usuario=usuario_gestor,
            )
            horario_router.criar_horario_escolar_api(
                payload=models.HorarioEscolarRegistroIn(
                    ano_letivo=2038,
                    turma_id=turma_id,
                    disciplina_id=disciplina_id,
                    professor_id=professor_id,
                    dia_semana="terca",
                    aula_numero=2,
                ),
                usuario=usuario_gestor,
            )

            with self.assertRaises(HTTPException) as aula_primeiro:
                horario_router.atualizar_aula_atividade_professor_api(
                    registro_id=int(atividade["id"]),
                    payload=models.AulaAtividadeProfessorUpdateIn(
                        dia_semana="terca",
                        aula_numero=2,
                    ),
                    usuario=usuario_gestor,
                )
            self.assertEqual(int(aula_primeiro.exception.status_code), 409)


if __name__ == "__main__":
    unittest.main()
