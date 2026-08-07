import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CadastroProfessorAccessibilityContractTests(unittest.TestCase):
    def test_required_inputs_have_persistent_labels(self):
        html = (ROOT / "templates" / "cadastro_professor.html").read_text(encoding="utf-8")

        for field_id in (
            "cadNome",
            "cadEmail",
            "cadSenha",
            "cadSenhaConfirmacao",
            "cadDataNascimento",
            "cadAulas",
        ):
            self.assertIn(f'<label for="{field_id}">', html)

    def test_checkbox_groups_and_errors_are_semantically_connected(self):
        html = (ROOT / "templates" / "cadastro_professor.html").read_text(encoding="utf-8")

        self.assertIn('<fieldset id="cadTurmasGrupo"', html)
        self.assertIn('<fieldset id="cadDisciplinasGrupo"', html)
        self.assertIn('aria-describedby="cadTurmasErro"', html)
        self.assertIn('aria-describedby="cadDisciplinasErro"', html)
        self.assertIn('aria-describedby="cadSenhaHint cadSenhaErro"', html)

    def test_validation_marks_invalid_fields_and_focuses_correction(self):
        script = (ROOT / "static" / "js" / "cadastro-professor.js").read_text(encoding="utf-8")

        self.assertIn('input.setAttribute("aria-invalid", texto ? "true" : "false")', script)
        self.assertIn('if (texto) input.focus()', script)
        self.assertIn('event.currentTarget.setAttribute("aria-busy", "true")', script)
        self.assertIn("if (!cadastroConcluido)", script)


if __name__ == "__main__":
    unittest.main()
