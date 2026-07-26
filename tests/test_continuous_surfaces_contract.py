import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ContinuousSurfacesContractTests(unittest.TestCase):
    def test_content_uses_one_background_and_sidebar_keeps_contrast(self):
        base = (ROOT / "static/css/base.css").read_text(encoding="utf-8")
        sidebar = (ROOT / "static/css/components/app-sidebar.css").read_text(encoding="utf-8")

        self.assertIn("--bg-main: #ffffff", base)
        self.assertIn("--card-bg: var(--bg-main)", base)
        self.assertIn("background: var(--bg-main)", base)
        self.assertIn("--surface-sidebar: var(--surface-2)", base)
        self.assertIn("background: var(--surface-sidebar)", sidebar)

    def test_sidebar_colors_come_only_from_design_tokens(self):
        sidebar = (ROOT / "static/css/components/app-sidebar.css").read_text(encoding="utf-8")

        self.assertNotRegex(sidebar, r"#[0-9a-fA-F]{3,8}|rgba?\(")
        self.assertIn("color: var(--text-disabled)", sidebar)
        self.assertIn("box-shadow: var(--shadow-floating)", sidebar)

    def test_continuous_surface_rules_load_after_page_styles_without_generic_card_reset(self):
        bundle = (ROOT / "templates/includes/style_bundle.html").read_text(encoding="utf-8")
        stylesheet = (ROOT / "static/css/components/continuous-surfaces.css").read_text(encoding="utf-8")

        self.assertGreater(bundle.index("continuous-surfaces.css"), bundle.index("{% endfor %}"))
        self.assertNotIn('main :where([class*="card"], [class*="panel"], [class*="surface"])', stylesheet)
        self.assertNotIn(".apc-pendencia-card", stylesheet)

    def test_density_tokens_are_shared_without_overriding_component_borders(self):
        base = (ROOT / "static/css/base.css").read_text(encoding="utf-8")
        stylesheet = (ROOT / "static/css/components/continuous-surfaces.css").read_text(encoding="utf-8")

        self.assertIn("--page-gutter: var(--space-4)", base)
        self.assertIn("--surface-padding: var(--space-3)", base)
        self.assertIn("padding: var(--surface-padding)", stylesheet)

    def test_shared_navbar_is_fixed_and_reserves_its_space(self):
        navbar = (ROOT / "static/css/components/app-navbar.css").read_text(encoding="utf-8")
        sidebar = (ROOT / "static/css/components/app-sidebar.css").read_text(encoding="utf-8")

        self.assertIn("position: fixed", navbar)
        self.assertIn("body:has(> .app-navbar)", navbar)
        self.assertIn("padding-top: var(--app-navbar-height)", navbar)
        self.assertIn("--app-navbar-height: 81px", sidebar)


if __name__ == "__main__":
    unittest.main()
