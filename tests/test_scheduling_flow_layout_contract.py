import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SchedulingFlowLayoutContractTest(unittest.TestCase):
    def test_fluxo_troca_conteudo_principal_apos_selecao_do_recurso(self):
        template = (ROOT / "templates/scheduling/index.html").read_text(encoding="utf-8")
        script = (ROOT / "static/js/agendamento.js").read_text(encoding="utf-8")
        styles = (ROOT / "static/css/pages/scheduling-stitch.css").read_text(encoding="utf-8")

        self.assertIn('id="schedulerPrimarySlot"', template)
        self.assertIn('id="schedulerSecondarySlot"', template)
        self.assertIn('id="schedulerResourceSurface"', template)
        self.assertIn('primarySlot.appendChild(sideWizard);', script)
        self.assertIn('secondarySlot.appendChild(resourceSurface);', script)
        self.assertIn('layout?.classList.toggle("is-flow-active", wizardAtivo);', script)
        self.assertIn(".scheduler-booking-layout.is-flow-active .scheduler-workspace .scheduler-side-wizard", styles)
        self.assertIn(
            ".scheduling-new-page #schedulerResourceSurface { padding: 0; border: 0; }",
            styles,
        )

    def test_painel_lateral_permite_selecao_multipla_sem_agenda_geral(self):
        template = (ROOT / "templates/scheduling/index.html").read_text(encoding="utf-8")
        script = (ROOT / "static/js/agendamento.js").read_text(encoding="utf-8")

        self.assertNotIn("Agenda geral", template)
        self.assertIn("const selecionado = recursosSelecionadosAgendamento.has(id);", script)
        self.assertIn("recursosSelecionadosAgendamento.delete(id);", script)
        self.assertIn("recursosSelecionadosAgendamento.add(id);", script)
        self.assertIn("não está disponível em todas as aulas selecionadas.", script)

    def test_etapas_removem_elementos_redundantes_e_destacam_calendario(self):
        template = (ROOT / "templates/scheduling/index.html").read_text(encoding="utf-8")
        flow_styles = (ROOT / "static/css/pages/scheduling-flow.css").read_text(encoding="utf-8")
        repeat_styles = (ROOT / "static/css/pages/scheduling-repeat.css").read_text(encoding="utf-8")

        self.assertNotIn("scheduler-mobile-resource-hero", template)
        self.assertNotIn("Adicionar outros recursos", template)
        self.assertIn("Escolha o dia", template)
        self.assertIn("grid-template-columns: repeat(7, minmax(0, 1fr));", flow_styles)
        self.assertIn(".scheduler-repeat-final {\n    display: grid;\n    gap: 16px;\n    padding: 0;\n    border: 0;", repeat_styles)

    def test_agendamento_nao_sobrescreve_componentes_globais_do_app_shell(self):
        stitch_styles = (
            ROOT / "static" / "css" / "pages" / "scheduling-stitch.css"
        ).read_text(encoding="utf-8")
        flow_styles = (
            ROOT / "static" / "css" / "pages" / "scheduling-flow.css"
        ).read_text(encoding="utf-8")
        legacy_styles = (
            ROOT / "static" / "css" / "pages" / "services-scheduler.css"
        ).read_text(encoding="utf-8")

        self.assertNotIn("--app-navbar-height:", stitch_styles)
        self.assertNotIn("--app-sidebar-width:", stitch_styles)
        self.assertNotIn(".scheduling-module .app-", stitch_styles)
        self.assertNotIn("font-family:", stitch_styles)
        self.assertNotIn(
            ".scheduler-flow-page .scheduler-page-header h1",
            flow_styles,
        )
        self.assertIn(
            ".scheduler-flow-page .scheduler-page-header h1:not(.page-title)",
            legacy_styles,
        )
        self.assertIn(
            ".scheduler-flow-page .scheduler-page-lead:not(.page-lead)",
            legacy_styles,
        )


if __name__ == "__main__":
    unittest.main()
