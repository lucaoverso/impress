import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PreConselhoMobileUiTest(unittest.TestCase):
    def test_selecao_de_turma_leva_a_lista_de_estudantes(self):
        template = (ROOT / "templates" / "preconselho" / "index.html").read_text(encoding="utf-8")
        script = "\n".join(
            (ROOT / "static" / "js" / "preconselho" / nome).read_text(encoding="utf-8")
            for nome in ("docente.js", "events.js")
        )

        self.assertIn('id="preconselhoSecaoEstudantes"', template)
        self.assertIn("function levarProfessorParaListaEstudantes()", script)
        self.assertIn('window.matchMedia("(max-width: 980px)").matches', script)
        self.assertIn("secao.scrollIntoView", script)
        self.assertIn("levarProfessorParaListaEstudantes();", script)

    def test_modal_mobile_respeita_viewport_e_nao_sobrepoe_acoes(self):
        css = (ROOT / "static" / "css" / "pages" / "pcpi-preconselho.css").read_text(encoding="utf-8")

        self.assertIn("height: 100dvh", css)
        self.assertIn("overscroll-behavior: contain", css)
        self.assertIn(".preconselho-modal-actions {\n        position: static;", css)
        self.assertIn("@media (pointer: coarse)", css)


if __name__ == "__main__":
    unittest.main()
