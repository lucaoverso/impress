import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ServicesProgressiveDisclosureContractTests(unittest.TestCase):
    def test_template_keeps_primary_and_secondary_catalogs(self):
        html = (ROOT / "templates" / "servicos.html").read_text(encoding="utf-8")

        self.assertIn('id="servicesPrimaryGrid"', html)
        self.assertIn('<details id="servicesMore"', html)
        self.assertIn('id="servicesMoreGrid"', html)
        self.assertEqual(html.count('data-modulo="'), 11)

    def test_role_priorities_and_fallback_keep_every_visible_module(self):
        script = (ROOT / "static" / "js" / "servicos.js").read_text(encoding="utf-8")

        self.assertIn("const MODULOS_PRIORITARIOS", script)
        self.assertIn('ADMIN: ["secretaria", "gestao", "relatorios"]', script)
        self.assertIn('COORDENADOR: ["secretaria", "coordenacao", "preconselho"]', script)
        self.assertIn('PROFESSOR: ["impressao", "agendamento", "horario"]', script)
        self.assertIn("disponiveis.filter((card) => !destaques.includes(card))", script)

    def test_more_services_summary_is_a_touch_target(self):
        css = (ROOT / "static" / "css" / "pages" / "services-scheduler.css").read_text(
            encoding="utf-8"
        )

        self.assertIn(".services-more > summary", css)
        self.assertIn("min-height: 44px;", css)


if __name__ == "__main__":
    unittest.main()
