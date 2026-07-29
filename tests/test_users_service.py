import unittest
from unittest.mock import patch

from fastapi import HTTPException

from modules.users.schemas import ProfileUpdateIn
from modules.users.service import get_own_profile_overview, update_own_profile


class UsersServiceTests(unittest.TestCase):
    @patch("modules.users.service.repository.update_profile", return_value=True)
    @patch("modules.users.service.repository.email_belongs_to_another_user", return_value=False)
    def test_updates_only_editable_profile_fields(self, _email_exists, update_profile):
        payload = ProfileUpdateIn(nome="  Ana   Silva  ", email="ANA@ESCOLA.COM")

        update_own_profile({"id": 7, "cargo": "PROFESSOR"}, payload)

        update_profile.assert_called_once_with(
            7, "Ana Silva", "ana@escola.com", password_hash=None, nt_hash=None
        )

    @patch("modules.users.service.repository.email_belongs_to_another_user", return_value=True)
    def test_rejects_email_used_by_another_user(self, _email_exists):
        payload = ProfileUpdateIn(nome="Ana Silva", email="ana@escola.com")

        with self.assertRaises(HTTPException) as raised:
            update_own_profile({"id": 7}, payload)

        self.assertEqual(raised.exception.status_code, 409)

    @patch("modules.users.service.repository.list_teacher_links")
    @patch("modules.users.service.repository.get_profile_identity")
    def test_non_teacher_receives_only_personal_identity(self, get_identity, list_links):
        get_identity.return_value = {
            "id": 3,
            "nome": "Coordenação",
            "email": "coord@escola.com",
            "perfil": "coordenador",
            "cargo": "COORDENADOR",
            "data_nascimento": "1985-04-12",
        }

        overview = get_own_profile_overview({"id": 3, "cargo": "COORDENADOR"}, 2026)

        self.assertIsNone(overview["teacher_dashboard"])
        self.assertEqual(overview["usuario"]["cargo"], "COORDENADOR")
        list_links.assert_not_called()

    def test_teacher_overview_limits_activity_and_deduplicates_supports(self):
        identity = {
            "id": 7,
            "nome": "Ana Silva",
            "email": "ana@escola.com",
            "perfil": "professor",
            "cargo": "PROFESSOR",
            "data_nascimento": "1990-02-03",
        }
        students = [
            {
                "estudante_id": 11,
                "estudante_nome": "João Souza",
                "turma_id": 4,
                "turma_nome": "8º A",
                "apoio_nome": "Tempo ampliado",
                "recomendacoes_pedagogicas": "Instruções em etapas",
            },
            {
                "estudante_id": 11,
                "estudante_nome": "João Souza",
                "turma_id": 4,
                "turma_nome": "8º A",
                "apoio_nome": "Tempo ampliado",
                "recomendacoes_pedagogicas": "Instruções em etapas",
            },
        ]
        activities = [
            {"id": index, "arquivo": f"arquivo-{index}", "status": "pendente"}
            for index in range(1, 5)
        ]

        with (
            patch("modules.users.service.repository.get_profile_identity", return_value=identity),
            patch("modules.users.service.repository.list_teacher_links", return_value=[]),
            patch("modules.users.service.repository.list_teacher_student_supports", return_value=students),
            patch("modules.users.service.repository.list_teacher_schedule", return_value=[]),
            patch("modules.users.service.repository.list_schedule_slots", return_value=[]),
            patch("modules.users.service.repository.list_recent_apc_submissions", return_value=activities),
            patch("modules.users.service.repository.list_recent_print_jobs", return_value=[]),
            patch("modules.users.service.repository.list_upcoming_bookings", return_value=[]),
        ):
            overview = get_own_profile_overview({"id": 7, "cargo": "PROFESSOR"}, 2026)

        dashboard = overview["teacher_dashboard"]
        self.assertEqual(len(dashboard["envios_apc"]), 3)
        self.assertEqual(dashboard["envios_apc"][0]["status_label"], "Aguardando revisão")
        self.assertEqual(dashboard["estudantes"]["total"], 1)
        self.assertEqual(dashboard["estudantes"]["itens"][0]["apoios"], ["Tempo ampliado"])
        self.assertNotIn("cid", dashboard["estudantes"]["itens"][0])


if __name__ == "__main__":
    unittest.main()
