from pathlib import Path
import unittest


BASE_DIR = Path(__file__).resolve().parents[1]


class SchedulingRepeatStepTest(unittest.TestCase):
    def test_template_declara_quinta_etapa_e_assets(self):
        template = (BASE_DIR / "templates" / "scheduling" / "index.html").read_text(encoding="utf-8")
        repeat_template = (
            BASE_DIR / "templates" / "includes" / "scheduling_repeat_step.html"
        ).read_text(encoding="utf-8")

        self.assertIn('id="stepperAgendamentoRepetir"', template)
        self.assertIn("includes/scheduling_repeat_step.html", template)
        self.assertIn('id="etapaAgendamentoRepetir"', repeat_template)
        self.assertIn('id="listaAulasRepeticaoAgendamento"', repeat_template)
        self.assertIn('id="listaDetalhesRepeticaoAgendamento"', repeat_template)
        self.assertIn("js/scheduling/repeat_step.js", template)

    def test_controlador_filtra_por_disponibilidade_dos_recursos(self):
        script = (
            BASE_DIR / "static" / "js" / "scheduling" / "repeat_step.js"
        ).read_text(encoding="utf-8")

        self.assertIn("aulaSuportaRecursosSelecionados", script)
        self.assertIn("obterRecursosSelecionadosAgendamento", script)
        self.assertIn("detalhesAulasAgendamento", script)


if __name__ == "__main__":
    unittest.main()
