from pathlib import Path
import unittest


BASE_DIR = Path(__file__).resolve().parents[1]


class SchedulingDayOverviewTest(unittest.TestCase):
    def test_renderer_agrupa_por_aula_professor_e_recursos(self):
        script = (
            BASE_DIR / "static" / "js" / "scheduling" / "day_overview.js"
        ).read_text(encoding="utf-8")

        self.assertIn("agruparReservasVisaoDia", script)
        self.assertIn("chaveProfessorVisaoDia", script)
        self.assertIn("recursos: new Set()", script)
        self.assertIn("aulaLabel(grupoAula.aulaNumero)", script)
        self.assertIn("carregarReservasProximosDias", script)
        self.assertIn("somarDiasDataLocal(dataBase, 30)", script)
        self.assertIn(".slice(0, 5)", script)

    def test_template_carrega_renderer_antes_do_script_principal(self):
        template = (BASE_DIR / "templates" / "agendamento.html").read_text(encoding="utf-8")

        overview_index = template.index("js/scheduling/day_overview.js")
        main_index = template.index("js/agendamento.js")
        self.assertLess(overview_index, main_index)
        self.assertIn('id="schedulerUpcomingOverviewList"', template)

    def test_troca_de_data_recarrega_proximos_agendamentos(self):
        script = (BASE_DIR / "static" / "js" / "agendamento.js").read_text(
            encoding="utf-8"
        )

        inicio = script.index("async function selecionarDataAgendamento")
        fim = script.index("function renderSemanaAgendamento", inicio)
        trecho = script[inicio:fim]
        self.assertIn("await carregarReservasProximosDias()", trecho)
        self.assertIn("renderVisaoProximosAgendamentos()", trecho)


if __name__ == "__main__":
    unittest.main()
