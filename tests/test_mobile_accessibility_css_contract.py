import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MobileAccessibilityCssContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = (ROOT / "static" / "css" / "base.css").read_text(encoding="utf-8")
        cls.mobile = (
            ROOT / "static" / "css" / "components" / "mobile-accessibility.css"
        ).read_text(encoding="utf-8")
        cls.bundle = (ROOT / "templates" / "includes" / "style_bundle.html").read_text(
            encoding="utf-8"
        )

    def test_mobile_contract_is_loaded_after_all_other_styles(self):
        mobile_position = self.bundle.index("css/components/mobile-accessibility.css")
        self.assertGreater(mobile_position, self.bundle.index("css/components/app-sidebar.css"))
        self.assertEqual(self.bundle.find('<link rel="stylesheet"', mobile_position + 1), -1)

    def test_ios_controls_have_single_mobile_font_size_contract(self):
        self.assertNotIn("font-size: 16px !important", self.base)
        self.assertIn("font-size: 16px !important", self.mobile)
        self.assertIn("-webkit-text-size-adjust: 100%", self.mobile)

        catalog = (ROOT / "static" / "css" / "pages" / "scheduling-catalog.css").read_text(
            encoding="utf-8"
        )
        ocorrencias = (
            ROOT / "static" / "css" / "coordenacao" / "ocorrencias.css"
        ).read_text(encoding="utf-8")
        self.assertNotIn(
            "color: var(--text-main); font: inherit; font-size:",
            catalog,
        )
        self.assertNotIn(".coordenacao-filter-grid select {\n    min-height: 42px;\n    font-size", ocorrencias)

    def test_double_tap_is_disabled_without_disabling_pinch_zoom(self):
        self.assertIn("touch-action: manipulation", self.mobile)
        self.assertNotIn("user-scalable", self.mobile)
        self.assertNotIn("maximum-scale", self.mobile)


if __name__ == "__main__":
    unittest.main()
