import importlib.util
import io
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from auth import get_usuario_logado
from modules.finance import pdf_service, repository, service
from modules.finance.router import router
from modules.finance.schemas import FinanceTransactionCreateIn, FinanceTransactionUpdateIn


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "20260814_create_finance_module.py"
)


def load_migration():
    spec = importlib.util.spec_from_file_location("test_finance_migration", MIGRATION_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Nao foi possivel carregar a migration financeira.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def png_bytes() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (80, 60), (15, 118, 110)).save(output, format="PNG")
    return output.getvalue()


class FinanceTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "finance.db"
        self.attachment_dir = Path(self.temp_dir.name) / "attachments"
        conn = self.connect()
        conn.execute("CREATE TABLE usuarios (id INTEGER PRIMARY KEY)")
        conn.execute("INSERT INTO usuarios (id) VALUES (7)")
        load_migration().upgrade(conn)
        conn.close()
        self.connection_patch = patch(
            "modules.finance.repository.get_connection", side_effect=self.connect
        )
        self.directory_patch = patch(
            "modules.finance.attachment_service.FINANCE_ATTACHMENT_DIR",
            self.attachment_dir,
        )
        self.connection_patch.start()
        self.directory_patch.start()

    def tearDown(self):
        self.directory_patch.stop()
        self.connection_patch.stop()
        self.temp_dir.cleanup()

    def connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def payload(self, **changes):
        values = {
            "transaction_type": "EXPENSE",
            "occurred_on": "2026-08-14",
            "description": "Materiais para biblioteca",
            "category": "Material pedagogico",
            "amount_cents": 12550,
            "counterparty": "Papelaria Central",
            "notes": "Compra aprovada pela direcao",
        }
        values.update(changes)
        return values


class FinanceMigrationTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("CREATE TABLE usuarios (id INTEGER PRIMARY KEY)")
        self.conn.execute("INSERT INTO usuarios (id) VALUES (7)")
        self.migration = load_migration()

    def tearDown(self):
        self.conn.close()

    def test_migration_is_idempotent_and_enforces_money_constraints(self):
        self.migration.upgrade(self.conn)
        self.migration.upgrade(self.conn)
        tables = {
            row[0]
            for row in self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        self.assertIn("finance_transactions", tables)
        self.assertIn("finance_attachments", tables)
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                """
                INSERT INTO finance_transactions (
                    created_by_user_id, transaction_type, occurred_on,
                    description, category, amount_cents
                ) VALUES (7, 'EXPENSE', '2026-08-14', 'Teste', 'Outros', 0)
                """
            )


class FinanceServiceTests(FinanceTestCase):
    def test_month_summary_uses_active_income_and_expense_in_cents(self):
        expense = service.create_transaction(
            actor_user_id=7,
            payload=FinanceTransactionCreateIn(**self.payload()),
        )
        service.create_transaction(
            actor_user_id=7,
            payload=FinanceTransactionCreateIn(
                **self.payload(
                    transaction_type="INCOME",
                    description="Repasse mensal",
                    category="Repasses",
                    amount_cents=50000,
                )
            ),
        )
        overview = service.get_month_overview("2026-08")
        self.assertEqual(overview["income_cents"], 50000)
        self.assertEqual(overview["expense_cents"], 12550)
        self.assertEqual(overview["balance_cents"], 37450)

        service.cancel_transaction(expense["id"], actor_user_id=7, reason="Duplicado")
        updated = service.get_month_overview("2026-08")
        self.assertEqual(updated["expense_cents"], 0)
        self.assertEqual(updated["canceled_count"], 1)

    def test_canceled_transaction_cannot_be_edited(self):
        item = service.create_transaction(
            actor_user_id=7,
            payload=FinanceTransactionCreateIn(**self.payload()),
        )
        service.cancel_transaction(item["id"], actor_user_id=7, reason="Correcao")
        with self.assertRaises(service.FinanceConflictError):
            service.update_transaction(
                item["id"], FinanceTransactionUpdateIn(**self.payload(amount_cents=20000))
            )

    def test_valid_attachment_is_private_and_linked_to_transaction(self):
        item = service.create_transaction(
            actor_user_id=7,
            payload=FinanceTransactionCreateIn(**self.payload()),
        )
        attachment = service.add_attachment(
            item["id"], content=png_bytes(), original_filename="nota.png"
        )
        stored, path = service.get_attachment(attachment["token"])
        self.assertEqual(stored["original_name"], "nota.png")
        self.assertTrue(path.is_file())
        self.assertNotIn("static", str(path))

    def test_month_report_generates_readable_pdf(self):
        service.create_transaction(
            actor_user_id=7,
            payload=FinanceTransactionCreateIn(**self.payload()),
        )
        content = pdf_service.generate_month_report_pdf(
            service.build_month_report("2026-08")
        )
        self.assertTrue(content.startswith(b"%PDF"))
        self.assertGreater(len(content), 1500)


class FinanceRouterTests(FinanceTestCase):
    def setUp(self):
        super().setUp()
        self.app = FastAPI()
        self.app.include_router(router)
        self.app.dependency_overrides[get_usuario_logado] = lambda: {
            "id": 7,
            "perfil": "admin",
            "cargo": "ADMIN",
        }
        self.audit_patch = patch("modules.finance.router._audit")
        self.audit_patch.start()
        self.client = TestClient(self.app)

    def tearDown(self):
        self.client.close()
        self.audit_patch.stop()
        super().tearDown()

    def create_transaction(self):
        response = self.client.post(
            "/api/admin/finance/transactions", json=self.payload()
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    def test_admin_can_create_attach_cancel_and_generate_report(self):
        item = self.create_transaction()
        upload = self.client.post(
            f"/api/admin/finance/transactions/{item['id']}/attachments",
            files={"file": ("nota.png", png_bytes(), "image/png")},
        )
        self.assertEqual(upload.status_code, 201)
        token = upload.json()["token"]
        download = self.client.get(f"/api/admin/finance/attachments/{token}")
        self.assertEqual(download.status_code, 200)
        self.assertEqual(download.headers["cache-control"], "private, no-store")

        summary = self.client.get("/api/admin/finance/summary?month=2026-08")
        self.assertEqual(summary.json()["expense_cents"], 12550)
        report = self.client.get("/api/admin/finance/report.pdf?month=2026-08")
        self.assertEqual(report.status_code, 200)
        self.assertTrue(report.content.startswith(b"%PDF"))

        canceled = self.client.post(
            f"/api/admin/finance/transactions/{item['id']}/cancel",
            json={"reason": "Lancamento duplicado"},
        )
        self.assertEqual(canceled.status_code, 200)
        self.assertEqual(canceled.json()["status"], "CANCELED")

    def test_non_admin_is_denied(self):
        self.app.dependency_overrides[get_usuario_logado] = lambda: {
            "id": 7,
            "perfil": "coordenador",
            "cargo": "COORDENADOR",
        }
        response = self.client.get("/api/admin/finance/transactions?month=2026-08")
        self.assertEqual(response.status_code, 403)

    def test_invalid_file_and_month_are_rejected(self):
        item = self.create_transaction()
        invalid = self.client.post(
            f"/api/admin/finance/transactions/{item['id']}/attachments",
            files={"file": ("nota.pdf", b"not-a-pdf", "application/pdf")},
        )
        self.assertEqual(invalid.status_code, 400)
        month = self.client.get("/api/admin/finance/summary?month=2026-99")
        self.assertEqual(month.status_code, 400)


if __name__ == "__main__":
    unittest.main()
