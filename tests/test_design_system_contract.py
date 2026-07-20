import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DesignSystemContractTests(unittest.TestCase):
    def test_shared_design_system_is_loaded_after_page_styles(self):
        bundle = (ROOT / "templates/includes/style_bundle.html").read_text(encoding="utf-8")

        self.assertGreater(bundle.index("css/design-system.css"), bundle.index("{% endfor %}"))
        self.assertLess(bundle.index("css/design-system.css"), bundle.index("continuous-surfaces.css"))

    def test_resources_page_uses_the_canonical_foundation(self):
        template = (ROOT / "modules/admin/templates/admin/recursos.html").read_text(encoding="utf-8")
        script = (ROOT / "static/js/admin/recursos.js").read_text(encoding="utf-8")

        for class_name in (
            "page-shell",
            "page-header",
            "page-section",
            "form-grid",
            "field",
            "button--primary",
            "feedback",
            "item-list",
        ):
            self.assertIn(class_name, template)
        self.assertIn("list-item", script)
        self.assertIn("action-group", script)
        self.assertNotIn("btnCancelar.style.display", script)

    def test_hidden_buttons_remain_out_of_layout(self):
        stylesheet = (ROOT / "static/css/design-system.css").read_text(encoding="utf-8")

        self.assertIn(".button[hidden] { display: none; }", stylesheet)

    def test_scheduling_pages_use_the_canonical_foundation(self):
        templates = [
            (ROOT / "templates/scheduling/index.html").read_text(encoding="utf-8"),
            (ROOT / "templates/scheduling/calendar.html").read_text(encoding="utf-8"),
            (ROOT / "templates/scheduling/my_bookings.html").read_text(encoding="utf-8"),
        ]

        for template in templates:
            self.assertIn("page-shell", template)
            self.assertIn("page-header", template)
            self.assertIn("page-title", template)
            self.assertIn("button", template)

        for template in templates[1:]:
            self.assertIn('"css/pages/scheduling-pages.css"', template)
            self.assertIn("item-list", template)
            self.assertIn("empty-state", template)

    def test_scheduling_dynamic_content_keeps_shared_classes(self):
        bookings = (ROOT / "static/js/scheduling/bookings_pages.js").read_text(encoding="utf-8")
        flow = (ROOT / "static/js/agendamento.js").read_text(encoding="utf-8")

        self.assertIn('booking-item list-item', bookings)
        self.assertIn('booking-item-actions action-group', bookings)
        self.assertIn('booking-empty empty-state', bookings)
        self.assertIn('btn-destaque button button--primary', flow)

    def test_reports_use_shared_navigation_data_and_feedback_patterns(self):
        template = (ROOT / "templates/relatorios.html").read_text(encoding="utf-8")
        script = (ROOT / "static/js/relatorios.js").read_text(encoding="utf-8")

        for class_name in (
            "page-section",
            "tab-list",
            "tab-button",
            "metric-grid",
            "data-table",
            "feedback",
        ):
            self.assertIn(class_name, template)
        self.assertIn('reports-metric-card metric-item', script)
        self.assertIn('reports-insight-item list-item', script)
        self.assertIn('reports-empty-cell empty-state', script)

    def test_every_canonical_class_is_documented(self):
        stylesheet = (ROOT / "static/css/design-system.css").read_text(encoding="utf-8")
        documentation = (
            ROOT / "docs/09-frontend/design-system-classes.md"
        ).read_text(encoding="utf-8")
        class_names = set(re.findall(r"\.([a-z][a-z0-9_-]*)", stylesheet))

        for class_name in sorted(class_names):
            with self.subTest(class_name=class_name):
                self.assertIn(f"`.{class_name}`", documentation)


if __name__ == "__main__":
    unittest.main()
