import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from auth import get_usuario_logado
from modules.users.router import router


class UsersRouterTests(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(router)
        self.user = {
            "id": 3,
            "nome": "Coordenação",
            "email": "coord@escola.com",
            "perfil": "coordenador",
            "cargo": "COORDENADOR",
        }
        self.app.dependency_overrides[get_usuario_logado] = lambda: self.user
        self.client = TestClient(self.app)

    def tearDown(self):
        self.client.close()

    def test_non_teacher_overview_has_null_teacher_dashboard(self):
        with patch(
            "modules.users.service.repository.get_profile_identity",
            return_value={**self.user, "data_nascimento": "1985-04-12", "ativo": 1},
        ):
            response = self.client.get("/me/profile/overview")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIsNone(payload["teacher_dashboard"])
        self.assertEqual(payload["usuario"]["email"], "coord@escola.com")

    def test_overview_requires_authentication(self):
        protected_app = FastAPI()
        protected_app.include_router(router)
        with TestClient(protected_app) as client:
            response = client.get(
                "/me/profile/overview",
                headers={"Authorization": "Invalid token"},
            )

        self.assertEqual(response.status_code, 401)

    def test_non_teacher_cannot_load_teacher_students(self):
        response = self.client.get("/me/profile/students")

        self.assertEqual(response.status_code, 403)

    def test_duplicate_email_and_weak_password_keep_validation_contract(self):
        with patch(
            "modules.users.service.repository.email_belongs_to_another_user",
            return_value=True,
        ):
            duplicate = self.client.patch(
                "/me/profile",
                json={"nome": "Coordenação", "email": "usado@escola.com", "nova_senha": ""},
            )
        self.assertEqual(duplicate.status_code, 409)

        with (
            patch(
                "modules.users.service.repository.email_belongs_to_another_user",
                return_value=False,
            ),
            patch("modules.users.service.repository.update_profile") as update_profile,
        ):
            weak = self.client.patch(
                "/me/profile",
                json={"nome": "Coordenação", "email": "coord@escola.com", "nova_senha": "fraca123"},
            )
        self.assertEqual(weak.status_code, 400)
        update_profile.assert_not_called()


if __name__ == "__main__":
    unittest.main()
