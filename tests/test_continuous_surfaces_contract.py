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
        self.assertIn("background: var(--surface-2, #eef3f8)", sidebar)

    def test_continuous_surface_rules_load_after_page_styles(self):
        bundle = (ROOT / "templates/includes/style_bundle.html").read_text(encoding="utf-8")
        stylesheet = (ROOT / "static/css/components/continuous-surfaces.css").read_text(encoding="utf-8")

        self.assertGreater(bundle.index("continuous-surfaces.css"), bundle.index("{% endfor %}"))
        self.assertIn('main :where([class*="card"], [class*="panel"], [class*="surface"])', stylesheet)
        self.assertIn('background-color: transparent', stylesheet)
        self.assertIn('box-shadow: none', stylesheet)

    def test_shared_navbar_is_fixed_and_reserves_its_space(self):
        navbar = (ROOT / "static/css/components/app-navbar.css").read_text(encoding="utf-8")
        sidebar = (ROOT / "static/css/components/app-sidebar.css").read_text(encoding="utf-8")

        self.assertIn("position: fixed", navbar)
        self.assertIn("body:has(> .app-navbar)", navbar)
        self.assertIn("padding-top: var(--app-navbar-height)", navbar)
        self.assertIn("--app-navbar-height: 81px", sidebar)


if __name__ == "__main__":
    unittest.main()
