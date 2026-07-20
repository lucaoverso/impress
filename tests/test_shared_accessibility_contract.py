import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SharedAccessibilityContractTest(unittest.TestCase):
    def test_dialogos_customizados_carregam_contencao_de_foco(self):
        bundle = (ROOT / "templates" / "includes" / "style_bundle.html").read_text(encoding="utf-8")
        script = (ROOT / "static" / "js" / "core" / "dialog_accessibility.js").read_text(encoding="utf-8")

        self.assertIn("js/core/dialog_accessibility.js", bundle)
        self.assertIn('[role="dialog"][aria-modal="true"]', script)
        self.assertIn("event.key !== 'Tab'", script)
        self.assertIn("document.activeElement", script)

    def test_listas_carregadas_sao_anunciadas(self):
        for relative_path, element_id in (
            ("templates/scheduling/my_bookings.html", "listaMinhasReservas"),
            ("templates/scheduling/calendar.html", "listaReservasDia"),
            ("templates/printing/history.html", "printHistoryList"),
        ):
            with self.subTest(element_id=element_id):
                template = (ROOT / relative_path).read_text(encoding="utf-8")
                start = template.index(f'id="{element_id}"')
                opening_tag = template[start:template.index(">", start)]
                self.assertIn('aria-busy="true"', opening_tag)
                self.assertIn('aria-live="polite"', opening_tag)

    def test_textos_auxiliares_usam_token_com_contraste_aprovado(self):
        css = (ROOT / "static" / "css" / "pages" / "coordenacao.css").read_text(encoding="utf-8")

        self.assertIn(".coordenacao-autocomplete-empty {\n    color: var(--text-muted);", css)
        self.assertIn(".coordenacao-rich-editor-area:empty::before {\n    content: attr(data-placeholder);\n    color: var(--text-muted);", css)


if __name__ == "__main__":
    unittest.main()
