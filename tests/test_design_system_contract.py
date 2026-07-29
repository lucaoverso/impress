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

    def test_product_pages_use_the_canonical_shell_and_heading(self):
        paths = (
            "templates/download.html",
            "templates/horario_escolar.html",
            "templates/apc/index.html",
            "templates/apc/calendario/index.html",
            "templates/coordenacao.html",
            "templates/notifications/index.html",
            "templates/notifications/manage.html",
            "templates/users/profile.html",
            "modules/admin/templates/admin/professores.html",
            "modules/admin/templates/admin/atribuicoes.html",
            "modules/admin/templates/admin/turmas.html",
            "modules/admin/templates/admin/aulas.html",
            "modules/admin/templates/admin/impressao.html",
            "modules/admin/templates/admin/recursos.html",
            "modules/admin/templates/admin/relatorios.html",
            "modules/admin/templates/admin/auditoria.html",
        )

        for relative_path in paths:
            with self.subTest(relative_path=relative_path):
                template = (ROOT / relative_path).read_text(encoding="utf-8")
                self.assertIn("page-shell", template)
                self.assertIn("page-title", template)

    def test_shared_shell_owns_content_width_and_heading_scale(self):
        sidebar = (ROOT / "static/css/components/app-sidebar.css").read_text(encoding="utf-8")
        design_system = (ROOT / "static/css/design-system.css").read_text(encoding="utf-8")

        self.assertIn("var(--app-main-max-width, var(--page-width))", sidebar)
        self.assertIn("main.page-shell--wide", sidebar)
        self.assertIn("main.page-shell--medium", sidebar)
        self.assertIn("main.page-shell--compact", sidebar)
        self.assertIn("h1.page-title {\n    font-size: 2.125rem;", design_system)
        self.assertIn("h1.page-title { font-size: 1.5rem;", design_system)

    def test_shared_components_own_control_and_surface_geometry(self):
        base = (ROOT / "static/css/base.css").read_text(encoding="utf-8")
        design_system = (ROOT / "static/css/design-system.css").read_text(encoding="utf-8")
        surfaces = (
            ROOT / "static/css/components/continuous-surfaces.css"
        ).read_text(encoding="utf-8")

        for contract in (
            "--control-height: 44px;",
            "--field-height: 48px;",
            "--radius-control: var(--radius-md);",
            "--radius-surface: var(--radius-lg);",
            "--radius-modal: 20px;",
        ):
            self.assertIn(contract, base)

        self.assertIn("Shared field contract", design_system)
        self.assertIn("Legacy action names", surfaces)
        self.assertIn("min-height: var(--control-height);", surfaces)
        self.assertIn("height: var(--field-height);", design_system)
        self.assertIn("border-radius: var(--radius-control);", design_system)
        self.assertIn("border-radius: var(--radius-surface);", surfaces)
        self.assertIn("box-shadow: none;", surfaces)

    def test_scheduling_does_not_import_printing_page_styles(self):
        template = (ROOT / "templates/scheduling/index.html").read_text(encoding="utf-8")

        self.assertNotIn('"css/printing/', template)
        self.assertNotIn('"css/pages/professor.css"', template)

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

    def test_printing_pages_and_dynamic_items_use_shared_classes(self):
        flow_template = (ROOT / "templates/printing/index.html").read_text(encoding="utf-8")
        history_template = (ROOT / "templates/printing/history.html").read_text(encoding="utf-8")
        flow_script = (ROOT / "static/js/professor.js").read_text(encoding="utf-8")
        history_script = (ROOT / "static/js/printing/history.js").read_text(encoding="utf-8")

        for template in (flow_template, history_template):
            self.assertIn("page-shell", template)
            self.assertIn("page-header", template)
            self.assertIn("page-title", template)
            self.assertIn("button", template)
        self.assertIn('"css/printing/history.css"', history_template)
        self.assertNotIn('<link rel="stylesheet"', history_template)
        self.assertIn('print-job-item list-item', flow_script)
        self.assertIn('print-history-item list-item', history_script)
        self.assertIn('print-history-empty empty-state', history_script)

        for template in (flow_template, history_template):
            self.assertIn('"css/printing/typography.css"', template)


if __name__ == "__main__":
    unittest.main()
