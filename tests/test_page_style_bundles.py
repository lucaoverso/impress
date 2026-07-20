import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PageStyleBundlesTest(unittest.TestCase):
    def test_telas_declaram_estilos_do_proprio_modulo(self):
        templates = [
            *ROOT.glob("templates/*.html"),
            *ROOT.glob("templates/*/*.html"),
            *ROOT.glob("modules/admin/templates/admin/*.html"),
        ]
        consumers = [
            template for template in templates
            if 'include "includes/style_bundle.html"' in template.read_text(encoding="utf-8")
        ]

        self.assertEqual(len(consumers), 23)
        for template in consumers:
            with self.subTest(template=template.relative_to(ROOT)):
                self.assertIn("set page_styles", template.read_text(encoding="utf-8"))

    def test_bundle_compartilhado_nao_carrega_css_de_modulos(self):
        bundle = (ROOT / "templates" / "includes" / "style_bundle.html").read_text(encoding="utf-8")

        self.assertIn("for page_style in page_styles", bundle)
        self.assertNotIn("css/pages/auth.css", bundle)
        self.assertNotIn("css/pages/professor.css", bundle)
        self.assertNotIn("css/pages/coordenacao.css", bundle)
        self.assertNotIn("css/pages/apc.css", bundle)

    def test_estilos_de_uso_cruzado_estao_na_camada_compartilhada(self):
        components = (ROOT / "static" / "css" / "components.css").read_text(encoding="utf-8")

        for class_name in ("auth-badge", "btn-destaque", "print-secondary-btn", "booking-detail"):
            with self.subTest(class_name=class_name):
                self.assertRegex(components, rf"(?m)^\.{re.escape(class_name)}\s*\{{")


if __name__ == "__main__":
    unittest.main()
