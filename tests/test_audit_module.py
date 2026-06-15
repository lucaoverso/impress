import importlib
import os
import sys
import tempfile
import unittest

try:
    from fastapi.testclient import TestClient
    TESTCLIENT_IMPORT_ERROR = None
except Exception as exc:  # pragma: no cover
    TestClient = None
    TESTCLIENT_IMPORT_ERROR = exc


def _reload_audit_modules(db_path: str):
    os.environ["DB_PATH"] = db_path
    module_names = [
        name
        for name in list(sys.modules)
        if name == "database"
        or name == "auth"
        or name == "main"
        or name.startswith("modules.audit")
    ]
    for module_name in module_names:
        del sys.modules[module_name]

    database = importlib.import_module("database")
    service = importlib.import_module("modules.audit.service")
    return database, service


class AuditServiceTest(unittest.TestCase):
    def setUp(self):
        self._old_db_path = os.environ.get("DB_PATH")

    def tearDown(self):
        if self._old_db_path is None:
            os.environ.pop("DB_PATH", None)
        else:
            os.environ["DB_PATH"] = self._old_db_path

    def test_records_filters_and_sanitizes_event_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "impressao.db")
            database, service = _reload_audit_modules(db_path)
            database.criar_tabelas()
            conn = database.get_connection()
            try:
                conn.execute(
                    """
                    INSERT INTO audit_events (
                        category, action, outcome, description, created_at
                    )
                    VALUES ('auth', 'old.event', 'success', 'Antigo', '2020-01-01 00:00:00')
                    """
                )
                conn.commit()
            finally:
                conn.close()

            event_id = service.record_event(
                category="auth",
                action="login.attempt",
                outcome="failure",
                actor_email="teacher@school.test",
                description="Tentativa recusada.",
                metadata={
                    "token": "secret",
                    "senha": "secret",
                    "reason": "invalid_credentials",
                },
            )

            self.assertIsInstance(event_id, int)
            result = service.list_audit_events(
                category="auth",
                outcome="failure",
                search="teacher@school.test",
            )
            self.assertEqual(result["total"], 1)
            event = result["items"][0]
            self.assertEqual(event["actor_email"], "teacher@school.test")
            self.assertNotIn("token", event["metadata"])
            self.assertNotIn("senha", event["metadata"])
            self.assertEqual(event["metadata"]["reason"], "invalid_credentials")
            all_events = service.list_audit_events()
            self.assertEqual(all_events["total"], 1)


@unittest.skipIf(
    TestClient is None,
    f"fastapi.testclient indisponivel neste ambiente: {TESTCLIENT_IMPORT_ERROR}",
)
class AuditRouterIntegrationTest(unittest.TestCase):
    def setUp(self):
        self._old_db_path = os.environ.get("DB_PATH")

    def tearDown(self):
        if self._old_db_path is None:
            os.environ.pop("DB_PATH", None)
        else:
            os.environ["DB_PATH"] = self._old_db_path

    def test_login_events_are_visible_only_to_admin(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "impressao.db")
            database, _service = _reload_audit_modules(db_path)
            main = importlib.import_module("main")

            with TestClient(main.app) as client:
                failed_login = client.post(
                    "/login",
                    json={"email": "unknown@school.test", "senha": "invalid"},
                )
                self.assertEqual(failed_login.status_code, 401)

                admin_login = client.post(
                    "/login",
                    json={"email": "admin@escola", "senha": "admin123"},
                )
                self.assertEqual(admin_login.status_code, 200)
                admin_headers = {
                    "Authorization": f"Bearer {admin_login.json()['token']}"
                }
                response = client.get(
                    "/admin/audit/events?category=auth",
                    headers=admin_headers,
                )
                self.assertEqual(response.status_code, 200)
                payload = response.json()
                self.assertGreaterEqual(payload["total"], 2)
                outcomes = {item["outcome"] for item in payload["items"]}
                self.assertIn("success", outcomes)
                self.assertIn("failure", outcomes)

                professor_login = client.post(
                    "/login",
                    json={"email": "professor@escola", "senha": "prof123"},
                )
                self.assertEqual(professor_login.status_code, 200)
                professor_headers = {
                    "Authorization": f"Bearer {professor_login.json()['token']}"
                }
                forbidden = client.get(
                    "/admin/audit/events",
                    headers=professor_headers,
                )
                self.assertEqual(forbidden.status_code, 403)


if __name__ == "__main__":
    unittest.main()
