import importlib
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, UTC
from types import SimpleNamespace

from fastapi.responses import JSONResponse


def _reload_modulos(db_path: str):
    os.environ["DB_PATH"] = db_path
    for nome_modulo in ("database", "db.core", "db.schema_migrations", "routers.system_router"):
        if nome_modulo in sys.modules:
            del sys.modules[nome_modulo]

    database = importlib.import_module("database")
    system_router = importlib.import_module("routers.system_router")
    return database, system_router


def _criar_request_fake(*, started_at, boot_status: str, worker_mode: str):
    app = SimpleNamespace(
        state=SimpleNamespace(
            started_at=started_at,
            boot_status=boot_status,
            worker_mode=worker_mode,
        )
    )
    return SimpleNamespace(app=app)


class SystemHealthTest(unittest.TestCase):
    def setUp(self):
        self._old_db_path = os.environ.get("DB_PATH")

    def tearDown(self):
        if self._old_db_path is None:
            os.environ.pop("DB_PATH", None)
        else:
            os.environ["DB_PATH"] = self._old_db_path

    def test_health_retorna_ok_quando_bootstrap_esta_pronto(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, system_router = _reload_modulos(db_path)
            database.criar_tabelas()

            request = _criar_request_fake(
                started_at=datetime.now(UTC) - timedelta(seconds=12),
                boot_status="ready",
                worker_mode="external",
            )
            resposta = system_router.health(request)

            self.assertEqual(resposta["status"], "ok")
            self.assertEqual(resposta["service"], "api")
            self.assertEqual(resposta["boot_status"], "ready")
            self.assertEqual(resposta["worker_mode"], "external")
            self.assertEqual(resposta["checks"]["database"], "ok")
            self.assertEqual(resposta["checks"]["migrations"], "ok")
            self.assertIsInstance(resposta["uptime_seconds"], int)
            self.assertGreaterEqual(resposta["uptime_seconds"], 0)
            self.assertTrue(str(resposta["started_at"]).endswith("Z"))

    def test_health_retorna_503_quando_boot_nao_esta_ready(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, system_router = _reload_modulos(db_path)
            database.criar_tabelas()

            request = _criar_request_fake(
                started_at=datetime.now(UTC),
                boot_status="starting",
                worker_mode="embedded",
            )
            resposta = system_router.health(request)

            self.assertIsInstance(resposta, JSONResponse)
            self.assertEqual(resposta.status_code, 503)
            self.assertIn('"status":"degraded"', resposta.body.decode("utf-8"))
            self.assertIn('"boot_status":"starting"', resposta.body.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
