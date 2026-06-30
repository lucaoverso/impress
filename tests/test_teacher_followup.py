import importlib
import os
import sys
import tempfile
import unittest

from fastapi import HTTPException


def _reload_modules(db_path: str):
    os.environ["DB_PATH"] = db_path
    for module_name in (
        "database",
        "db._proxy",
        "routers.common",
        "modules.teacher_followup.repository",
        "modules.teacher_followup.service",
        "modules.teacher_followup.router",
    ):
        if module_name in sys.modules:
            del sys.modules[module_name]
    database = importlib.import_module("database")
    schemas = importlib.import_module("modules.teacher_followup.schemas")
    router = importlib.import_module("modules.teacher_followup.router")
    return database, schemas, router


class TeacherFollowupTest(unittest.TestCase):
    def setUp(self):
        self._old_db_path = os.environ.get("DB_PATH")

    def tearDown(self):
        if self._old_db_path is None:
            os.environ.pop("DB_PATH", None)
        else:
            os.environ["DB_PATH"] = self._old_db_path

    def _coord_user(self, user_id: int = 900):
        return {"id": user_id, "nome": "Coord", "cargo": "COORDENADOR"}

    def _teacher_user(self, user_id: int):
        return {"id": user_id, "nome": "Professor", "cargo": "PROFESSOR"}

    def test_coordination_lists_records_and_profile_with_deadline_metrics(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, schemas, router = _reload_modules(db_path)
            database.criar_tabelas()
            coord_id = int(
                database.criar_coordenador(
                    nome="Coord Acompanhamento",
                    email="coord.acompanhamento@escola.local",
                    senha_hash=database.hash_senha("Senha@123"),
                    data_nascimento="1980-01-01",
                )
            )

            professor_id = int(
                database.criar_professor(
                    nome="Ana Docente",
                    email="ana.docente@escola.local",
                    senha_hash=database.hash_senha("Senha@123"),
                    data_nascimento="1987-03-12",
                    aulas_semanais=12,
                    turmas_quantidade=1,
                    turmas=["8A"],
                    disciplinas=["Matematica"],
                )
            )
            periodo_no_prazo = database.criar_apc_periodo(
                ano_letivo=2035,
                data_referencia="2035-05-10",
                prazo_envio="2035-05-10T23:59",
                titulo="Entrega semanal",
                observacao="",
                publico_alvo="TODOS_PROFESSORES",
                tipo_entrega="GERAL",
                criado_por_usuario_id=coord_id,
            )
            periodo_atrasado = database.criar_apc_periodo(
                ano_letivo=2035,
                data_referencia="2035-05-11",
                prazo_envio="2035-05-11T12:00",
                titulo="Entrega com atraso",
                observacao="",
                publico_alvo="TODOS_PROFESSORES",
                tipo_entrega="GERAL",
                criado_por_usuario_id=coord_id,
            )
            database.criar_apc_periodo(
                ano_letivo=2035,
                data_referencia="2035-05-12",
                prazo_envio="2035-05-12T18:00",
                titulo="Entrega pendente",
                observacao="",
                publico_alvo="TODOS_PROFESSORES",
                tipo_entrega="GERAL",
                criado_por_usuario_id=coord_id,
            )
            database.criar_apc_periodo(
                ano_letivo=2035,
                data_referencia="2035-06-01",
                prazo_envio="2035-06-01T18:00",
                titulo="Fora do filtro",
                observacao="",
                publico_alvo="TODOS_PROFESSORES",
                tipo_entrega="GERAL",
                criado_por_usuario_id=coord_id,
            )
            turma_id = int(database.criar_turma("8A", "MATUTINO", 30))
            disciplina_id = int(database.criar_disciplina("Matematica Followup", 4))
            envio = database.criar_apc_envio(
                periodo_id=int(periodo_no_prazo["id"]),
                professor_usuario_id=professor_id,
                turma_id=turma_id,
                disciplina_id=disciplina_id,
                arquivo_nome_cliente="atividade.pdf",
                arquivo_nome_original="atividade.pdf",
                arquivo_path=os.path.join(tmp_dir, "atividade.pdf"),
                arquivo_tamanho=10,
                arquivo_tipo="application/pdf",
            )
            envio_atrasado = database.criar_apc_envio(
                periodo_id=int(periodo_atrasado["id"]),
                professor_usuario_id=professor_id,
                turma_id=turma_id,
                disciplina_id=disciplina_id,
                arquivo_nome_cliente="atividade-atrasada.pdf",
                arquivo_nome_original="atividade-atrasada.pdf",
                arquivo_path=os.path.join(tmp_dir, "atividade-atrasada.pdf"),
                arquivo_tamanho=10,
                arquivo_tipo="application/pdf",
            )
            conn = database.get_connection()
            try:
                conn.execute(
                    """
                    UPDATE apc_envios
                    SET primeiro_envio_em = ?, enviado_em = ?
                    WHERE id = ?
                    """,
                    ("2035-05-10 10:00:00", "2035-05-10 10:00:00", int(envio["id"])),
                )
                conn.execute(
                    """
                    UPDATE apc_envios
                    SET primeiro_envio_em = ?, enviado_em = ?
                    WHERE id = ?
                    """,
                    (
                        "2035-05-11 14:00:00",
                        "2035-05-11 14:00:00",
                        int(envio_atrasado["id"]),
                    ),
                )
                conn.commit()
            finally:
                conn.close()

            payload = schemas.FollowupRecordCreate(
                teacher_id=professor_id,
                record_type="positive",
                category="Planejamento",
                description="Entregou os materiais com antecedencia.",
                record_date="2035-05-11",
            )
            created = router.create_record(payload=payload, user=self._coord_user(coord_id))
            self.assertEqual(created["record"]["type"], "positive")

            listing = router.list_teachers(
                q="mate",
                date_from="2035-05-10",
                date_to="2035-05-12",
                user=self._coord_user(coord_id),
            )
            self.assertEqual(len(listing["teachers"]), 1)
            teacher = listing["teachers"][0]
            self.assertEqual(teacher["name"], "Ana Docente")
            self.assertEqual(teacher["positive_count"], 1)
            self.assertEqual(teacher["attention_count"], 0)
            self.assertEqual(teacher["deadline_indicators"]["expected"], 3)
            self.assertEqual(teacher["deadline_indicators"]["on_time"], 1)
            self.assertEqual(teacher["deadline_indicators"]["late"], 1)
            self.assertEqual(teacher["deadline_indicators"]["pending"], 1)
            self.assertEqual(teacher["on_time_percent"], 33.3)
            self.assertEqual(listing["period_summary"]["expected"], 3)

            profile = router.get_teacher_profile(
                teacher_id=professor_id,
                type=None,
                date_from="2035-05-10",
                date_to="2035-05-12",
                user=self._coord_user(coord_id),
            )
            self.assertEqual(profile["teacher"]["id"], professor_id)
            self.assertEqual(profile["period_summary"]["positives"], 1)
            self.assertEqual(profile["period_summary"]["deadline_summary"]["expected"], 3)
            self.assertEqual(profile["period_summary"]["deadline_summary"]["on_time_percent"], 33.3)
            self.assertEqual(len(profile["timeline"]), 1)
            self.assertEqual(profile["previous_evaluations"], [])

            filtered = router.list_teachers(
                q="mate",
                date_from="2035-05-10",
                date_to="2035-05-10",
                user=self._coord_user(coord_id),
            )
            self.assertEqual(filtered["teachers"][0]["deadline_indicators"]["expected"], 1)
            self.assertEqual(filtered["teachers"][0]["deadline_indicators"]["on_time"], 1)
            self.assertEqual(filtered["period_summary"]["on_time_percent"], 100.0)

    def test_teacher_without_coordination_access_is_denied(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, _schemas, router = _reload_modules(db_path)
            database.criar_tabelas()
            professor_id = int(
                database.criar_professor(
                    nome="Bruno Docente",
                    email="bruno.docente@escola.local",
                    senha_hash=database.hash_senha("Senha@123"),
                    data_nascimento="1988-04-18",
                    aulas_semanais=10,
                    turmas_quantidade=1,
                )
            )

            with self.assertRaises(HTTPException) as ctx:
                router.list_teachers(q="", user=self._teacher_user(professor_id))

            self.assertEqual(ctx.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
