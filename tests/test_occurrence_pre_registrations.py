import importlib
import os
import sys
import tempfile
import unittest

from fastapi import HTTPException


MODULES_TO_RELOAD = (
    "database",
    "db.core",
    "modules.occurrences.repository",
    "modules.occurrences.service",
    "ocorrencias_router",
)


def _reload_modules(db_path: str):
    os.environ["DB_PATH"] = db_path
    for module_name in MODULES_TO_RELOAD:
        sys.modules.pop(module_name, None)
    database = importlib.import_module("database")
    service = importlib.import_module("modules.occurrences.service")
    router = importlib.import_module("ocorrencias_router")
    return database, service, router


class OccurrencePreRegistrationsTest(unittest.TestCase):
    def setUp(self):
        self._old_db_path = os.environ.get("DB_PATH")

    def tearDown(self):
        if self._old_db_path is None:
            os.environ.pop("DB_PATH", None)
        else:
            os.environ["DB_PATH"] = self._old_db_path

    def _create_context(self, database):
        database.criar_tabelas()
        turma_id = int(database.criar_turma("Turma Pre Registro", "MATUTINO", 25))
        student_id = int(database.criar_estudante("Estudante Pre Registro", turma_id))
        database.criar_usuario(
            "Professor Pre Registro",
            "professor.pre.registro@escola.test",
            "senha123",
            "professor",
            "PROFESSOR",
        )
        professor = database.buscar_usuario_por_email(
            "professor.pre.registro@escola.test"
        )
        return turma_id, student_id, professor

    def test_professor_creates_pre_registration_and_only_lists_own(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            database, service, _ = _reload_modules(
                os.path.join(tmp_dir, "impressao.db")
            )
            _, student_id, professor = self._create_context(database)
            reason = service.create_reason(
                {"cargo": "ADMIN"},
                "Uso indevido de celular",
            )

            created = service.create_pre_registration(
                professor,
                student_id=student_id,
                reason_id=reason["id"],
                responsible_contact="communicate",
            )
            listed = service.list_pre_registrations(professor)

            self.assertEqual(created["student_id"], student_id)
            self.assertEqual(created["responsible_contact"], "communicate")
            self.assertEqual([item["id"] for item in listed], [created["id"]])

    def test_inactive_reason_cannot_be_used(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            database, service, _ = _reload_modules(
                os.path.join(tmp_dir, "impressao.db")
            )
            _, student_id, professor = self._create_context(database)
            reason = service.create_reason({"cargo": "ADMIN"}, "Atraso recorrente")
            service.update_reason(
                {"cargo": "ADMIN"},
                reason["id"],
                name=None,
                active=False,
            )

            with self.assertRaises(HTTPException) as context:
                service.create_pre_registration(
                    professor,
                    student_id=student_id,
                    reason_id=reason["id"],
                    responsible_contact="none",
                )

            self.assertEqual(context.exception.status_code, 400)

    def test_manager_completes_pre_registration_with_created_occurrence(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            database, service, router = _reload_modules(
                os.path.join(tmp_dir, "impressao.db")
            )
            turma_id, student_id, professor = self._create_context(database)
            reason = service.create_reason(
                {"cargo": "ADMIN"},
                "Desrespeito aos combinados da turma",
            )
            pre_registration = service.create_pre_registration(
                professor,
                student_id=student_id,
                reason_id=reason["id"],
                responsible_contact="summon",
            )
            legal_basis_id = database.criar_regimento_item(
                lei_nome="Regimento Interno",
                artigo_numero="76",
                artigo_descricao="Dos deveres do estudante.",
            )
            payload = router.OcorrenciaCreateIn(
                pre_registration_id=pre_registration["id"],
                tipo_registro="estudante",
                nome_estudante="Estudante Pre Registro",
                estudante_id=student_id,
                turma_id=turma_id,
                professor_requerente=professor["nome"],
                professor_requerente_id=professor["id"],
                disciplina="Matematica",
                data_ocorrencia="2026-06-11",
                aula="2",
                horario_ocorrencia="08:00",
                descricao="Texto complementado pela coordenacao.",
                regimento_item_ids=[legal_basis_id],
                acao_aplicada="advertencia",
                status="registrado",
            )

            occurrence = router.criar_ocorrencia_api(
                payload,
                usuario={"cargo": "ADMIN"},
            )
            completed = service.list_pre_registrations(
                {"cargo": "ADMIN"},
                status="completed",
            )

            self.assertEqual(len(completed), 1)
            self.assertEqual(completed[0]["id"], pre_registration["id"])
            self.assertEqual(completed[0]["occurrence_id"], occurrence["id"])


if __name__ == "__main__":
    unittest.main()
