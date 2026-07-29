import os
import sys
import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException

from tests.test_impressao_reuso_historico import PDF_MINIMO, _reload_modulos


class PrintingDelegatedHistoryTest(unittest.TestCase):
    def setUp(self):
        self._old_db_path = os.environ.get("DB_PATH")
        self._old_router_config = sys.modules.get("routers.config")
        self._old_pdf_service = sys.modules.get("services.pdf_service")

    def tearDown(self):
        if self._old_db_path is None:
            os.environ.pop("DB_PATH", None)
        else:
            os.environ["DB_PATH"] = self._old_db_path

        for name, module in (
            ("routers.config", self._old_router_config),
            ("services.pdf_service", self._old_pdf_service),
        ):
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module

    @staticmethod
    def _create_professor(database, name: str, email: str) -> tuple[int, dict]:
        professor_id = int(
            database.criar_professor(
                nome=name,
                email=email,
                senha_hash=database.hash_senha("Senha@123"),
                data_nascimento="1990-01-10",
                aulas_semanais=10,
                turmas_quantidade=1,
                turmas=["7A"],
                disciplinas=["Matemática"],
            )
        )
        return professor_id, database.buscar_usuario_por_email(email)

    @staticmethod
    def _create_completed_job(database, spool_dir: Path, user_id: int, name: str) -> int:
        path = spool_dir / name
        path.write_bytes(PDF_MINIMO)
        job_id = database.criar_job(
            usuario_id=user_id,
            arquivo=name,
            arquivo_path=str(path),
            copias=1,
            paginas_totais=4,
            tags_json='["Simulado"]',
        )
        database.atualizar_status(job_id, "CONCLUIDO")
        return int(job_id)

    def test_admin_lists_own_and_selected_professor_history_with_origins(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            spool_dir = Path(tmp_dir) / "spool"
            spool_dir.mkdir()
            database, printing = _reload_modulos(
                os.path.join(tmp_dir, "impressao.db"),
                str(spool_dir),
            )
            database.criar_tabelas()
            database.criar_usuario("Admin", "admin@example.com", "senha123", "admin")
            admin = database.buscar_usuario_por_email("admin@example.com")
            professor_id, _professor = self._create_professor(
                database,
                "Professora Ana",
                "ana@example.com",
            )

            admin_job = self._create_completed_job(
                database,
                spool_dir,
                int(admin["id"]),
                "admin.pdf",
            )
            professor_job = self._create_completed_job(
                database,
                spool_dir,
                professor_id,
                "professora.pdf",
            )

            jobs = printing.meus_jobs(
                professor_id=professor_id,
                incluir_proprios=True,
                usuario=admin,
            )

            self.assertEqual({int(job["id"]) for job in jobs}, {admin_job, professor_job})
            self.assertEqual(int(jobs[0]["id"]), professor_job)
            origins = {int(job["id"]): job["origem_historico"] for job in jobs}
            self.assertEqual(origins[admin_job], "proprio")
            self.assertEqual(origins[professor_job], "professor")
            self.assertEqual(
                next(job for job in jobs if int(job["id"]) == professor_job)["origem_nome"],
                "Professora Ana",
            )

            only_professor = printing.meus_jobs(
                professor_id=professor_id,
                incluir_proprios=False,
                usuario=admin,
            )
            self.assertEqual([int(job["id"]) for job in only_professor], [professor_job])
            self.assertNotIn("origem_historico", only_professor[0])

    def test_cross_owner_reuse_is_assigned_and_charged_to_selected_professor(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            spool_dir = Path(tmp_dir) / "spool"
            spool_dir.mkdir()
            database, printing = _reload_modulos(
                os.path.join(tmp_dir, "impressao.db"),
                str(spool_dir),
            )
            database.criar_tabelas()
            database.criar_usuario("Admin", "admin@example.com", "senha123", "admin")
            admin = database.buscar_usuario_por_email("admin@example.com")
            professor_id, professor = self._create_professor(
                database,
                "Professor Bruno",
                "bruno@example.com",
            )
            outsider_id, outsider = self._create_professor(
                database,
                "Professor Sem Acesso",
                "sem-acesso@example.com",
            )

            admin_job = self._create_completed_job(
                database,
                spool_dir,
                int(admin["id"]),
                "origem-admin.pdf",
            )
            professor_job = self._create_completed_job(
                database,
                spool_dir,
                professor_id,
                "origem-professor.pdf",
            )

            with self.assertRaises(HTTPException) as denied:
                printing.meus_jobs(
                    professor_id=professor_id,
                    incluir_proprios=True,
                    usuario=outsider,
                )
            self.assertEqual(denied.exception.status_code, 403)
            self.assertNotEqual(outsider_id, professor_id)

            for source_job in (admin_job, professor_job):
                response = printing.reimprimir_job_historico(
                    job_id=source_job,
                    copias=1,
                    paginas_por_folha=1,
                    duplex=False,
                    orientacao="retrato",
                    intervalo_paginas="",
                    professor_id=professor_id,
                    usuario=admin,
                )
                self.assertFalse(response["cota_ilimitada"])

            professor_jobs = database.listar_jobs_por_usuario(professor_id)
            self.assertEqual(len(professor_jobs), 3)
            self.assertEqual(
                sum(job["status"] == "PENDENTE" for job in professor_jobs),
                2,
            )
            self.assertEqual(
                len(database.listar_jobs_por_usuario(int(admin["id"]))),
                1,
            )
            quota = printing.minha_cota(professor_id=professor_id, usuario=admin)
            self.assertEqual(quota["usadas"], 8)
            self.assertFalse(quota["ilimitada"])
            self.assertEqual(int(professor["id"]), professor_id)


if __name__ == "__main__":
    unittest.main()
