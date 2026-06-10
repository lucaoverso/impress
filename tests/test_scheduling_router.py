import importlib
import os
import sys
import tempfile
import unittest

from fastapi.testclient import TestClient


def _reload_app_modules(db_path: str):
    os.environ["DB_PATH"] = db_path

    modules_to_reload = [
        "database",
        "db._proxy",
        "db.catalogos",
        "db.usuarios",
        "db.agendamento",
        "routers.common",
        "auth",
        "modules.scheduling.policies",
        "modules.scheduling.dependencies",
        "modules.scheduling.repository",
        "modules.scheduling.router",
        "main",
    ]

    for module_name in modules_to_reload:
        if module_name in sys.modules:
            del sys.modules[module_name]

    main = importlib.import_module("main")
    database = importlib.import_module("database")
    return main, database


class SchedulingRouterIntegrationTest(unittest.TestCase):
    def setUp(self):
        self._old_db_path = os.environ.get("DB_PATH")

    def tearDown(self):
        if self._old_db_path is None:
            os.environ.pop("DB_PATH", None)
        else:
            os.environ["DB_PATH"] = self._old_db_path

    def _login_admin(self, client: TestClient) -> str:
        response = client.post(
            "/login",
            json={"email": "admin@escola", "senha": "admin123"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("token", payload)
        return f"Bearer {payload['token']}"

    def test_agendamento_get_endpoints_return_expected_payloads(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "impressao.db")
            main, database = _reload_app_modules(db_path)
            database.criar_tabelas()
            database.seed_recursos_padrao()

            with TestClient(main.app) as client:
                authorization = self._login_admin(client)
                headers = {"Authorization": authorization}

                recurso_resp = client.get("/agendamento/recursos", headers=headers)
                self.assertEqual(recurso_resp.status_code, 200)
                recursos = recurso_resp.json()
                self.assertIsInstance(recursos, list)
                self.assertGreaterEqual(len(recursos), 1)
                self.assertIn("id", recursos[0])
                self.assertIn("nome", recursos[0])
                self.assertIn("tipo", recursos[0])

                opcoes_resp = client.get("/agendamento/opcoes", headers=headers)
                self.assertEqual(opcoes_resp.status_code, 200)
                opcoes = opcoes_resp.json()
                self.assertIsInstance(opcoes, dict)
                self.assertIn("turnos", opcoes)
                self.assertIn("turmas", opcoes)
                self.assertIsInstance(opcoes["turnos"], list)
                self.assertIsInstance(opcoes["turmas"], list)

                professores_resp = client.get("/agendamento/professores", headers=headers)
                self.assertEqual(professores_resp.status_code, 200)
                professores = professores_resp.json()
                self.assertIsInstance(professores, list)
                self.assertGreaterEqual(len(professores), 1)
                self.assertIn("id", professores[0])
                self.assertIn("nome", professores[0])
                self.assertIn("email", professores[0])

    def test_agendamento_create_and_cancel_reservation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "impressao.db")
            main, database = _reload_app_modules(db_path)
            database.criar_tabelas()
            database.seed_recursos_padrao()
            database.criar_turma(nome="7 Ano A", turno="MATUTINO", quantidade_estudantes=30)

            with TestClient(main.app) as client:
                authorization = self._login_admin(client)
                headers = {"Authorization": authorization}

                recursos_resp = client.get("/agendamento/recursos", headers=headers)
                self.assertEqual(recursos_resp.status_code, 200)
                recursos = recursos_resp.json()
                self.assertGreaterEqual(len(recursos), 1)
                recurso_id = recursos[0]["id"]

                payload = {
                    "recurso_id": int(recurso_id),
                    "data": "2099-01-01",
                    "aula": "1",
                    "turma": "7 Ano A",
                    "tema_aula": "Planejamento",
                    "professor_id": None,
                    "observacao": "Teste de integração",
                }

                criar_resp = client.post(
                    "/agendamento/reservas",
                    json=payload,
                    headers=headers,
                )
                self.assertEqual(criar_resp.status_code, 200)
                criar_json = criar_resp.json()
                self.assertEqual(
                    criar_json.get("mensagem"),
                    "Agendamento realizado com sucesso.",
                )
                self.assertIsInstance(criar_json.get("agendamento_id"), int)
                agendamento_id = criar_json["agendamento_id"]

                cancelar_resp = client.post(
                    f"/agendamento/reservas/{agendamento_id}/cancelar",
                    headers=headers,
                )
                self.assertEqual(cancelar_resp.status_code, 200)
                cancelar_json = cancelar_resp.json()
                self.assertEqual(
                    cancelar_json.get("mensagem"),
                    "Agendamento cancelado com sucesso.",
                )
