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
        self.assertIn(
            "aulaLabelComHorario(\n"
            "                grupoAula.aulaNumero,\n"
            "                grupoAula.faixa\n"
            "            )",
            script,
        )
        self.assertIn("carregarReservasProximosDias", script)
        self.assertIn("somarDiasDataLocal(dataBase, 30)", script)
        self.assertIn(".slice(0, 5)", script)
        self.assertIn("agruparReservasPorPeriodoVisao", script)
        self.assertIn("nomePeriodoAgendamento(periodo)", script)
        self.assertIn('"bi bi-sun-fill"', script)
        self.assertIn('"bi bi-sunset-fill"', script)

        scheduling_script = (
            BASE_DIR / "static" / "js" / "agendamento.js"
        ).read_text(encoding="utf-8")
        self.assertIn("function aulaLabelComHorario(aula, faixaGlobal = aula)", scheduling_script)
        self.assertIn("`${numeroAula}ª aula`", scheduling_script)
        self.assertIn("`${rotulo}: ${horarioInicio} - ${horarioFim}`", scheduling_script)

    def test_resumo_diario_alinha_no_topo_e_nao_usa_marcador_verde(self):
        flow_css = (
            BASE_DIR / "static" / "css" / "pages" / "scheduling-flow.css"
        ).read_text(encoding="utf-8")
        stitch_css = (
            BASE_DIR / "static" / "css" / "pages" / "scheduling-stitch.css"
        ).read_text(encoding="utf-8")

        self.assertIn(".scheduler-day-overview-period-title i", flow_css)
        self.assertIn(
            '.scheduler-day-overview-period[data-period="matutino"]',
            flow_css,
        )
        self.assertIn(
            '.scheduler-day-overview-period[data-period="vespertino"]',
            flow_css,
        )
        self.assertIn(
            ".scheduler-agenda-overview > section.scheduler-day-overview",
            stitch_css,
        )
        self.assertIn("align-content: start;", stitch_css)

    def test_template_carrega_renderer_antes_do_script_principal(self):
        template = (BASE_DIR / "templates" / "scheduling" / "index.html").read_text(encoding="utf-8")

        overview_index = template.index("js/scheduling/day_overview.js")
        main_index = template.index("js/agendamento.js")
        self.assertLess(overview_index, main_index)
        self.assertIn('id="schedulerUpcomingOverviewList"', template)
        self.assertIn("<details", template)
        self.assertIn('class="scheduler-upcoming-summary"', template)

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
