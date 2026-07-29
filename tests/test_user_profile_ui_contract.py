import unittest
from pathlib import Path

from fastapi.testclient import TestClient

import main


ROOT = Path(__file__).resolve().parents[1]


class UserProfileUiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(main.app)

    def test_profile_page_loads_declared_assets(self):
        response = self.client.get("/meu-perfil")

        self.assertEqual(response.status_code, 200)
        self.assertIn('id="profileTeacherDashboard"', response.text)
        self.assertIn('id="profileScheduleMobile"', response.text)
        for asset in (
            "/static/css/pages/user-profile.css",
            "/static/js/users/profile_renderers.js",
            "/static/js/users/profile.js",
        ):
            self.assertIn(asset, response.text)
            self.assertEqual(self.client.get(asset).status_code, 200)

    def test_navbar_links_profile_and_no_longer_contains_editor_dialog(self):
        template = (ROOT / "templates/includes/app_navbar.html").read_text()
        script = (ROOT / "static/js/core/app_navbar.js").read_text()

        self.assertIn('href="/meu-perfil"', template)
        self.assertIn('id="appNavbarToggleName"', template)
        self.assertNotIn("appNavbarProfileDialog", template)
        self.assertNotIn("openProfileDialog", script)

    def test_profile_has_mobile_schedule_and_reduced_motion_rules(self):
        css = (ROOT / "static/css/pages/user-profile.css").read_text()
        renderer = (ROOT / "static/js/users/profile_renderers.js").read_text()

        self.assertIn("@media (max-width: 720px)", css)
        self.assertIn(".profile-schedule-mobile:not([hidden])", css)
        self.assertIn("@media (prefers-reduced-motion: reduce)", css)
        self.assertIn('"Aula / horário"', renderer)
        self.assertIn("schedule.dias_semana.some", renderer)
        self.assertIn("slot.horario_fim", renderer)
        self.assertIn('`${number}ª aula`', renderer)


if __name__ == "__main__":
    unittest.main()
