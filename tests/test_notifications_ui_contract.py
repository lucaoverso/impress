import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class NotificationsUiContractTest(unittest.TestCase):
    def test_navbar_orders_help_bell_profile_and_exposes_accessibility_contract(self):
        template = (ROOT / "templates/includes/app_navbar.html").read_text()
        help_index = template.index("appNavbarHelpToggle")
        bell_index = template.index("appNavbarNotificationsToggle")
        profile_index = template.index("appNavbarProfileToggle")
        self.assertLess(help_index, bell_index)
        self.assertLess(bell_index, profile_index)
        self.assertIn('aria-controls="appNavbarNotificationsPanel"', template)
        self.assertIn('aria-label="Abrir notificações"', template)

    def test_public_auth_pages_do_not_receive_notification_assets(self):
        bundle = (ROOT / "templates/includes/style_bundle.html").read_text()
        self.assertIn('request.url.path not in ["/login-page", "/cadastro-professor"]', bundle)
        self.assertIn("app-notifications.css", bundle)
        self.assertIn("app_notifications.js", bundle)

    def test_service_worker_has_no_offline_cache_and_handles_push_click(self):
        worker = (ROOT / "static/service-worker.js").read_text()
        self.assertIn('addEventListener("push"', worker)
        self.assertIn('addEventListener("notificationclick"', worker)
        self.assertNotIn('addEventListener("fetch"', worker)
        self.assertNotIn("caches.open", worker)

    def test_notification_pages_declare_module_style_and_permission_is_user_initiated(self):
        inbox = (ROOT / "templates/notifications/index.html").read_text()
        core = (ROOT / "static/js/core/app_notifications.js").read_text()
        self.assertIn('page_styles = ["css/pages/notifications.css"]', inbox)
        self.assertIn("Ativar neste dispositivo", inbox)
        self.assertIn("Notification.requestPermission()", core)
        self.assertIn('addEventListener("click"', core)
        self.assertNotIn("requestPermission();\n        init", core)


if __name__ == "__main__":
    unittest.main()
