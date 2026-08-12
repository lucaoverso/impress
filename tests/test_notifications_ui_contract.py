import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class NotificationsUiContractTest(unittest.TestCase):
    def test_navbar_orders_help_bell_profile_and_exposes_accessibility_contract(self):
        template = (ROOT / "templates/includes/app_navbar.html").read_text(encoding="utf-8")
        help_index = template.index("appNavbarHelpToggle")
        bell_index = template.index("appNavbarNotificationsToggle")
        profile_index = template.index("appNavbarProfileToggle")
        self.assertLess(help_index, bell_index)
        self.assertLess(bell_index, profile_index)
        self.assertIn('aria-controls="appNavbarNotificationsPanel"', template)
        self.assertIn('aria-label="Abrir notificações"', template)

    def test_public_auth_pages_do_not_receive_notification_assets(self):
        bundle = (ROOT / "templates/includes/style_bundle.html").read_text(encoding="utf-8")
        self.assertIn('request.url.path not in ["/login-page", "/cadastro-professor"]', bundle)
        self.assertIn("app-notifications.css", bundle)
        self.assertIn("app_notifications_drawer.js", bundle)
        self.assertIn("app_notifications.js", bundle)

    def test_service_worker_has_no_offline_cache_and_handles_push_click(self):
        worker = (ROOT / "static/service-worker.js").read_text(encoding="utf-8")
        self.assertIn('addEventListener("push"', worker)
        self.assertIn('addEventListener("notificationclick"', worker)
        self.assertNotIn('addEventListener("fetch"', worker)
        self.assertNotIn("caches.open", worker)

    def test_notification_pages_declare_module_style_and_permission_is_user_initiated(self):
        inbox = (ROOT / "templates/notifications/index.html").read_text(encoding="utf-8")
        core = (ROOT / "static/js/core/app_notifications.js").read_text(encoding="utf-8")
        self.assertIn('page_styles = ["css/pages/notifications.css"]', inbox)
        self.assertIn("Ativar neste dispositivo", inbox)
        self.assertIn("Notification.requestPermission()", core)
        self.assertIn('addEventListener("click"', core)
        self.assertNotIn("requestPermission();\n        init", core)

    def test_drawer_completion_keeps_history_and_management_exposes_receipts(self):
        core = (ROOT / "static/js/core/app_notifications.js").read_text(encoding="utf-8")
        drawer = (ROOT / "static/js/core/app_notifications_drawer.js").read_text(encoding="utf-8")
        central = (ROOT / "static/js/notifications/inbox.js").read_text(encoding="utf-8")
        manage = (ROOT / "static/js/notifications/manage.js").read_text(encoding="utf-8")
        details = (ROOT / "static/js/notifications/manage_details.js").read_text(encoding="utf-8")
        template = (ROOT / "templates/notifications/manage.html").read_text(encoding="utf-8")

        self.assertIn("/notifications?filter=unread&page_size=8", core)
        self.assertIn("app-notification-complete", drawer)
        self.assertIn("Marcar como lida", drawer)
        self.assertIn('filter: "all"', central)
        self.assertIn("NotificationsManageDetails.open", manage)
        self.assertIn("/recipients`,", details)
        self.assertIn("notificationBatchRecipientsBody", template)
        self.assertIn("Dispositivos", template)

    def test_services_invites_push_without_repeating_on_every_visit(self):
        template = (ROOT / "templates/servicos.html").read_text(encoding="utf-8")
        prompt = (ROOT / "static/js/services_notifications_prompt.js").read_text(
            encoding="utf-8"
        )
        styles = (ROOT / "static/css/pages/services-notifications-prompt.css").read_text(
            encoding="utf-8"
        )

        self.assertIn("servicesNotificationsPrompt", template)
        self.assertIn("Ativar notificações", template)
        self.assertIn("Agora não", template)
        self.assertIn('role="dialog" aria-modal="true"', template)
        self.assertIn("SNOOZE_DAYS = 7", prompt)
        self.assertIn("getSubscription()", prompt)
        self.assertIn('Notification.permission === "denied"', prompt)
        self.assertIn("window.AppNotifications.activatePush()", prompt)
        self.assertIn("prefers-reduced-motion", styles)

    def test_services_guides_iphone_install_before_requesting_push(self):
        template = (ROOT / "templates/servicos.html").read_text(encoding="utf-8")
        prompt = (ROOT / "static/js/services_notifications_prompt.js").read_text(
            encoding="utf-8"
        )
        manifest = json.loads(
            (ROOT / "static/manifest.webmanifest").read_text(encoding="utf-8")
        )

        self.assertIn("Adicionar à Tela de Início", template)
        self.assertIn("Abrir como App da Web", template)
        self.assertIn("servicesNotificationsInstallSteps", template)
        self.assertIn("MODE_IOS_INSTALL", prompt)
        self.assertIn("MODE_IOS_BROWSER", prompt)
        self.assertIn("services-install-prompt-snooze", prompt)
        self.assertIn('matchMedia("(display-mode: standalone)")', prompt)
        self.assertIn("navigator.maxTouchPoints > 1", prompt)
        self.assertIn("INSTALL_ACK_HOURS = 24", prompt)
        self.assertEqual(manifest["display"], "standalone")
        self.assertEqual(manifest["start_url"], "/servicos")


if __name__ == "__main__":
    unittest.main()
