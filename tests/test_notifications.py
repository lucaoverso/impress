import importlib
import json
import os
import sqlite3
import sys
import tempfile
import types
import unittest
from datetime import UTC, datetime, timedelta

from pydantic import ValidationError
from fastapi import HTTPException


def _reload(db_path: str):
    os.environ["DB_PATH"] = db_path
    os.environ["APP_TIMEZONE"] = "America/Campo_Grande"
    os.environ["ENABLE_EMBEDDED_WORKER"] = "0"
    for name in list(sys.modules):
        if name == "database" or name.startswith("modules.notifications"):
            del sys.modules[name]
    database = importlib.import_module("database")
    database.criar_tabelas()
    service = importlib.import_module("modules.notifications.service")
    repository = importlib.import_module("modules.notifications.repository")
    integration = importlib.import_module("modules.notifications.apc_integration")
    return database, service, repository, integration


class NotificationsTest(unittest.TestCase):
    def setUp(self):
        self.old_env = {
            name: os.environ.get(name)
            for name in (
                "DB_PATH",
                "APP_TIMEZONE",
                "ENABLE_EMBEDDED_WORKER",
                "WEB_PUSH_ENABLED",
                "VAPID_PUBLIC_KEY",
                "VAPID_PRIVATE_KEY",
            )
        }

    def tearDown(self):
        for name, value in self.old_env.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    def _teacher(self, database, suffix: str = "one") -> int:
        return int(
            database.criar_professor(
                nome=f"Professor {suffix}",
                email=f"professor-{suffix}@escola.local",
                senha_hash=database.hash_senha("Senha@123"),
                data_nascimento="1990-01-01",
                aulas_semanais=10,
                turmas_quantidade=1,
            )
        )

    def test_inbox_isolates_users_marks_items_and_deduplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            database, service, repository, _integration = _reload(
                os.path.join(tmp, "db.sqlite")
            )
            first = self._teacher(database, "first")
            second = self._teacher(database, "second")
            item = service.create_notification(
                recipient_user_id=first,
                category="manual",
                title="Novo aviso",
                body="Consulte a informação no sistema.",
                dedupe_key="same-key",
            )
            duplicate = service.create_notification(
                recipient_user_id=first,
                category="manual",
                title="Novo aviso",
                body="Consulte a informação no sistema.",
                dedupe_key="same-key",
            )
            service.create_notification(
                recipient_user_id=second,
                category="manual",
                title="Outro aviso",
                body="Este item pertence a outra pessoa.",
            )

            self.assertEqual(item["id"], duplicate["id"])
            self.assertEqual(service.list_inbox(first, filter_name="all", page=1, page_size=20)["total"], 1)
            self.assertEqual(service.list_inbox(second, filter_name="all", page=1, page_size=20)["total"], 1)
            self.assertFalse(repository.mark_read(item["id"], second))
            self.assertTrue(repository.mark_read(item["id"], first))
            self.assertEqual(repository.unread_count(first), 0)

    def test_audience_union_and_internal_url_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            database, service, _repository, _integration = _reload(
                os.path.join(tmp, "db.sqlite")
            )
            teacher = self._teacher(database, "audience")
            manager = int(
                database.criar_coordenador(
                    nome="Coord",
                    email="coord-notifications@escola.local",
                    senha_hash=database.hash_senha("Senha@123"),
                )
            )
            estimate = service.resolve_estimate(
                ["teachers", "managers"], [teacher, manager]
            )
            self.assertIn(teacher, estimate["recipient_ids"])
            self.assertIn(manager, estimate["recipient_ids"])
            self.assertEqual(len(estimate["recipient_ids"]), len(set(estimate["recipient_ids"])))

            schemas = importlib.import_module("modules.notifications.schemas")
            with self.assertRaises(ValidationError):
                schemas.BatchCreateIn(
                    audiences=["all"],
                    title="Aviso",
                    body="Mensagem",
                    action_url="https://example.com",
                )
            with self.assertRaises(ValidationError):
                schemas.BatchCreateIn(
                    audiences=["all"],
                    title="Aviso",
                    body="Mensagem",
                    action_url="//example.com",
                )

    def test_subscription_endpoint_is_reassigned_to_current_user(self):
        with tempfile.TemporaryDirectory() as tmp:
            database, _service, _repository, _integration = _reload(
                os.path.join(tmp, "db.sqlite")
            )
            delivery_repo = importlib.import_module(
                "modules.notifications.delivery_repository"
            )
            first = self._teacher(database, "device-first")
            second = self._teacher(database, "device-second")
            endpoint = "https://push.example/shared-device"
            delivery_repo.upsert_subscription(
                first, endpoint, "p256dh-value-that-is-long-enough", "auth-value", "test"
            )
            delivery_repo.upsert_subscription(
                second, endpoint, "new-p256dh-value-that-is-long", "new-auth-value", "test"
            )
            conn = database.get_connection()
            try:
                row = conn.execute(
                    "SELECT user_id, active, COUNT(*) OVER () AS total "
                    "FROM push_subscriptions WHERE endpoint = ?",
                    (endpoint,),
                ).fetchone()
            finally:
                conn.close()
            self.assertEqual(row["user_id"], second)
            self.assertEqual(row["active"], 1)
            self.assertEqual(row["total"], 1)

    def test_batch_recipient_status_reports_reads_and_active_devices(self):
        with tempfile.TemporaryDirectory() as tmp:
            database, service, repository, _integration = _reload(
                os.path.join(tmp, "db.sqlite")
            )
            delivery_repo = importlib.import_module(
                "modules.notifications.delivery_repository"
            )
            first = self._teacher(database, "receipt-first")
            second = self._teacher(database, "receipt-second")
            batch_id = "batch-read-receipts"
            first_notice = service.create_notification(
                recipient_user_id=first,
                category="manual",
                title="Reunião pedagógica",
                body="Confira o horário da reunião.",
                batch_id=batch_id,
            )
            service.create_notification(
                recipient_user_id=second,
                category="manual",
                title="Reunião pedagógica",
                body="Confira o horário da reunião.",
                batch_id=batch_id,
            )
            repository.mark_read(first_notice["id"], first)
            delivery_repo.upsert_subscription(
                first, "https://push.example/device-one",
                "p256dh-value-that-is-long-enough", "auth-value", "device one",
            )
            delivery_repo.upsert_subscription(
                first, "https://push.example/device-two",
                "p256dh-value-that-is-long-enough", "auth-value", "device two",
            )

            result = service.list_batch_recipients(batch_id)
            recipients = {item["user_id"]: item for item in result["items"]}
            self.assertEqual(result["total"], 2)
            self.assertEqual(result["read_count"], 1)
            self.assertEqual(result["push_active_count"], 1)
            self.assertIsNotNone(recipients[first]["read_at"])
            self.assertEqual(recipients[first]["active_devices"], 2)
            self.assertTrue(recipients[first]["push_active"])
            self.assertIsNone(recipients[second]["read_at"])
            self.assertEqual(recipients[second]["active_devices"], 0)
            self.assertFalse(recipients[second]["push_active"])

            with self.assertRaises(HTTPException) as context:
                service.list_batch_recipients("missing-batch")
            self.assertEqual(context.exception.status_code, 404)

    def test_apc_creates_initial_and_two_deadline_markers_without_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            database, _service, _repository, integration = _reload(
                os.path.join(tmp, "db.sqlite")
            )
            teacher = self._teacher(database, "apc")
            coordinator = int(
                database.criar_coordenador(
                    nome="Coord APC",
                    email="coord-apc-notifications@escola.local",
                    senha_hash=database.hash_senha("Senha@123"),
                )
            )
            local_now = datetime.now(integration.app_timezone())
            deadline = local_now + timedelta(days=5)
            period = database.criar_apc_periodo(
                ano_letivo=deadline.year,
                data_referencia=deadline.date().isoformat(),
                prazo_envio=deadline.strftime("%Y-%m-%d %H:%M:%S"),
                titulo="APC 21/07",
                observacao="",
                publico_alvo="PROFESSORES_SELECIONADOS",
                tipo_entrega="GERAL",
                criado_por_usuario_id=coordinator,
            )
            class_id = int(database.criar_turma("9A Notifications", "MATUTINO", 30))
            subject_id = int(database.criar_disciplina("Matematica Notifications", 4))
            database.substituir_apc_destinatarios(
                period["id"],
                [{
                    "professor_id": teacher,
                    "turma_id": class_id,
                    "disciplina_id": subject_id,
                }],
            )

            integration.sync_apc_period(period["id"])
            integration.sync_apc_period(period["id"])
            conn = database.get_connection()
            try:
                rows = conn.execute(
                    """
                    SELECT priority, dedupe_key, metadata_json
                    FROM notifications WHERE source_id = ? AND cancelled_at IS NULL
                    ORDER BY available_at
                    """,
                    (str(period["id"]),),
                ).fetchall()
            finally:
                conn.close()
            self.assertEqual(len(rows), 3)
            self.assertEqual([row["priority"] for row in rows].count("urgent"), 1)
            metadata = json.loads(rows[0]["metadata_json"])
            self.assertEqual(metadata["obligations"], [[class_id, subject_id]])

    def test_apc_short_deadline_does_not_create_retroactive_reminders(self):
        with tempfile.TemporaryDirectory() as tmp:
            database, _service, _repository, integration = _reload(
                os.path.join(tmp, "db.sqlite")
            )
            teacher = self._teacher(database, "short")
            deadline = datetime.now(integration.app_timezone()) + timedelta(hours=12)
            period = database.criar_apc_periodo(
                ano_letivo=deadline.year,
                data_referencia=deadline.date().isoformat(),
                prazo_envio=deadline.strftime("%Y-%m-%d %H:%M:%S"),
                titulo="Prazo curto",
                observacao="",
                publico_alvo="TODOS_PROFESSORES",
                tipo_entrega="GERAL",
                criado_por_usuario_id=teacher,
            )
            integration.sync_apc_period(period["id"])
            conn = database.get_connection()
            try:
                total = conn.execute(
                    "SELECT COUNT(*) FROM notifications WHERE source_id = ?",
                    (str(period["id"]),),
                ).fetchone()[0]
            finally:
                conn.close()
            self.assertEqual(total, 1)

    def test_apc_completion_deadline_change_recipient_removal_and_delete(self):
        with tempfile.TemporaryDirectory() as tmp:
            database, _service, _repository, integration = _reload(
                os.path.join(tmp, "db.sqlite")
            )
            teacher = self._teacher(database, "lifecycle")
            local_now = datetime.now(integration.app_timezone())
            deadline = local_now + timedelta(days=5)
            period = database.criar_apc_periodo(
                ano_letivo=deadline.year,
                data_referencia=deadline.date().isoformat(),
                prazo_envio=deadline.strftime("%Y-%m-%d %H:%M:%S"),
                titulo="Ciclo APC",
                observacao="",
                publico_alvo="PROFESSORES_SELECIONADOS",
                tipo_entrega="GERAL",
                criado_por_usuario_id=teacher,
            )
            class_id = int(database.criar_turma("8A Lifecycle", "MATUTINO", 30))
            subject_id = int(database.criar_disciplina("Historia Lifecycle", 3))
            database.substituir_apc_destinatarios(
                period["id"],
                [{"professor_id": teacher, "turma_id": class_id, "disciplina_id": subject_id}],
            )
            integration.sync_apc_period(period["id"])
            conn = database.get_connection()
            try:
                due_id = int(
                    conn.execute(
                        """
                        SELECT id FROM notifications
                        WHERE source_id = ? AND dedupe_key LIKE '%72h:%'
                        """,
                        (str(period["id"]),),
                    ).fetchone()["id"]
                )
                conn.execute(
                    "UPDATE notifications SET available_at = datetime('now') WHERE id = ?",
                    (due_id,),
                )
                conn.commit()
            finally:
                conn.close()
            submission = database.criar_apc_envio(
                periodo_id=period["id"],
                professor_usuario_id=teacher,
                turma_id=class_id,
                disciplina_id=subject_id,
                arquivo_nome_cliente="atividade.pdf",
                arquivo_nome_original="atividade.pdf",
                arquivo_path=os.path.join(tmp, "atividade.pdf"),
                arquivo_tamanho=10,
                arquivo_tipo="application/pdf",
            )
            integration.sync_apc_period(period["id"])
            conn = database.get_connection()
            try:
                self.assertIsNotNone(
                    conn.execute(
                        "SELECT cancelled_at FROM notifications WHERE id = ?", (due_id,)
                    ).fetchone()["cancelled_at"]
                )
            finally:
                conn.close()

            database.excluir_apc_envio(submission["id"])
            new_deadline = deadline + timedelta(days=2)
            database.atualizar_apc_periodo(
                periodo_id=period["id"],
                ano_letivo=new_deadline.year,
                data_referencia=new_deadline.date().isoformat(),
                prazo_envio=new_deadline.strftime("%Y-%m-%d %H:%M:%S"),
                titulo="Ciclo APC atualizado",
                observacao="",
                publico_alvo="PROFESSORES_SELECIONADOS",
                tipo_entrega="GERAL",
            )
            integration.sync_apc_period(period["id"])
            conn = database.get_connection()
            try:
                active_future = conn.execute(
                    """
                    SELECT COUNT(*) FROM notifications
                    WHERE source_id = ? AND cancelled_at IS NULL
                      AND available_at > datetime('now')
                    """,
                    (str(period["id"]),),
                ).fetchone()[0]
            finally:
                conn.close()
            self.assertEqual(active_future, 2)

            database.substituir_apc_destinatarios(period["id"], [])
            integration.sync_apc_period(period["id"])
            conn = database.get_connection()
            try:
                future_after_removal = conn.execute(
                    """
                    SELECT COUNT(*) FROM notifications
                    WHERE source_id = ? AND cancelled_at IS NULL
                      AND available_at > datetime('now')
                    """,
                    (str(period["id"]),),
                ).fetchone()[0]
            finally:
                conn.close()
            self.assertEqual(future_after_removal, 0)
            integration.cancel_apc_period(period["id"])
            conn = database.get_connection()
            try:
                visible = conn.execute(
                    "SELECT COUNT(*) FROM notifications WHERE source_id = ? AND cancelled_at IS NULL",
                    (str(period["id"]),),
                ).fetchone()[0]
            finally:
                conn.close()
            self.assertEqual(visible, 0)

    def test_professor_cannot_access_management_api(self):
        with tempfile.TemporaryDirectory() as tmp:
            _database, _service, _repository, _integration = _reload(
                os.path.join(tmp, "db.sqlite")
            )
            router = importlib.import_module("modules.notifications.router")
            with self.assertRaises(HTTPException) as context:
                router.get_recipients(
                    search="", user={"id": 1, "cargo": "PROFESSOR"}
                )
            self.assertEqual(context.exception.status_code, 403)
            with self.assertRaises(HTTPException) as context:
                router.get_notification_batch_recipients(
                    "batch-id", user={"id": 1, "cargo": "PROFESSOR"}
                )
            self.assertEqual(context.exception.status_code, 403)

    def test_push_success_retry_and_gone_subscription(self):
        with tempfile.TemporaryDirectory() as tmp:
            database, service, _repository, _integration = _reload(
                os.path.join(tmp, "db.sqlite")
            )
            delivery_repo = importlib.import_module(
                "modules.notifications.delivery_repository"
            )
            push = importlib.import_module("modules.notifications.push")
            success_teacher = self._teacher(database, "push-success")
            retry_teacher = self._teacher(database, "push-retry")
            gone_teacher = self._teacher(database, "push-gone")
            os.environ["WEB_PUSH_ENABLED"] = "true"
            os.environ["VAPID_PUBLIC_KEY"] = "public-key"
            os.environ["VAPID_PRIVATE_KEY"] = "private-key"

            def create_delivery(user_id: int, endpoint: str, key: str):
                delivery_repo.upsert_subscription(
                    user_id, endpoint, "p256dh-value-that-is-long-enough", "auth-value", "test"
                )
                service.create_notification(
                    recipient_user_id=user_id,
                    category="manual",
                    title="Aviso seguro",
                    body="Abra o sistema para consultar os detalhes.",
                    dedupe_key=key,
                )

            calls = []
            sys.modules["pywebpush"] = types.SimpleNamespace(
                webpush=lambda **kwargs: calls.append(kwargs)
            )
            create_delivery(success_teacher, "https://push.example/success", "push-success")
            self.assertTrue(push.process_one_delivery())
            self.assertEqual(len(calls), 1)
            self.assertNotIn("p256dh", calls[0]["data"])

            class PushError(Exception):
                def __init__(self, status):
                    self.response = types.SimpleNamespace(status_code=status)

            sys.modules["pywebpush"] = types.SimpleNamespace(
                webpush=lambda **_kwargs: (_ for _ in ()).throw(PushError(503))
            )
            create_delivery(retry_teacher, "https://push.example/retry", "push-retry")
            self.assertTrue(push.process_one_delivery())
            conn = database.get_connection()
            try:
                retry = conn.execute(
                    """
                    SELECT status, attempts FROM notification_push_deliveries
                    ORDER BY id DESC LIMIT 1
                    """
                ).fetchone()
            finally:
                conn.close()
            self.assertEqual(retry["status"], "failed")
            self.assertEqual(retry["attempts"], 1)
            for _ in range(4):
                conn = database.get_connection()
                try:
                    conn.execute(
                        """
                        UPDATE notification_push_deliveries
                        SET next_attempt_at = datetime('now')
                        WHERE status = 'failed'
                        """
                    )
                    conn.commit()
                finally:
                    conn.close()
                self.assertTrue(push.process_one_delivery())
            conn = database.get_connection()
            try:
                exhausted = conn.execute(
                    """
                    SELECT status, attempts FROM notification_push_deliveries
                    WHERE notification_id = (
                        SELECT id FROM notifications WHERE dedupe_key = 'push-retry'
                    )
                    """
                ).fetchone()
            finally:
                conn.close()
            self.assertEqual(exhausted["status"], "dead")
            self.assertEqual(exhausted["attempts"], 5)

            sys.modules["pywebpush"] = types.SimpleNamespace(
                webpush=lambda **_kwargs: (_ for _ in ()).throw(PushError(410))
            )
            create_delivery(gone_teacher, "https://push.example/gone", "push-gone")
            self.assertTrue(push.process_one_delivery())
            conn = database.get_connection()
            try:
                active = conn.execute(
                    "SELECT active FROM push_subscriptions WHERE endpoint = ?",
                    ("https://push.example/gone",),
                ).fetchone()[0]
            finally:
                conn.close()
            self.assertEqual(active, 0)


class NotificationMigrationTest(unittest.TestCase):
    def test_migration_is_idempotent(self):
        module = importlib.import_module(
            "migrations.20260726_create_notifications"
        )
        conn = sqlite3.connect(":memory:")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("CREATE TABLE usuarios (id INTEGER PRIMARY KEY)")
        try:
            module.upgrade(conn)
            module.upgrade(conn)
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
            self.assertTrue(
                {"notifications", "push_subscriptions", "notification_push_deliveries"}
                <= tables
            )
        finally:
            conn.close()
