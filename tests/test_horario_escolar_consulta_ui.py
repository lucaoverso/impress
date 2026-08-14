import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HorarioEscolarConsultaUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = (ROOT / "templates/horario_escolar.html").read_text(encoding="utf-8")
        cls.script = (ROOT / "static/js/horario_escolar.js").read_text(encoding="utf-8")
        cls.styles = (ROOT / "static/css/pages/horario-escolar.css").read_text(
            encoding="utf-8"
        )

    def test_consulta_publica_tem_filtro_minimalista(self):
        self.assertIn('id="filtroHorarioProfessorBusca"', self.template)
        self.assertIn('id="filtroHorarioVisualizacao"', self.template)
        self.assertIn('<option value="turmas">Por turma</option>', self.template)
        self.assertIn('<option value="professores">Por professor</option>', self.template)
        self.assertIn('<option value="atividades">Por aula-atividade</option>', self.template)
        self.assertIn('class="button button--primary btn-destaque horario-consulta-submit"', self.template)

    def test_consulta_remove_escopos_meu_horario_e_colegas(self):
        self.assertNotIn('name="horarioEscopoProfessor"', self.template)
        self.assertNotIn("Somente colegas", self.template)
        self.assertNotIn("Ver meu horario", self.template)

    def test_script_filtra_professor_e_renderiza_aula_atividade_por_faixa(self):
        self.assertIn("function filtrarPorProfessorHorario", self.script)
        self.assertIn("function renderizarConsultaAulaAtividade", self.script)
        self.assertIn('professores.join(", ")', self.script)
        self.assertIn("Nenhum professor neste horário", self.script)
        self.assertIn('params.set("incluir_aulas_atividade", "true")', self.script)

    def test_aula_do_professor_usa_apenas_negrito_na_consulta(self):
        self.assertIn(".horario-readonly .horario-professor-grid td.is-own", self.styles)
        self.assertIn("font-weight: 700;", self.styles)
        self.assertIn("box-shadow: none;", self.styles)
        self.assertNotIn("Minha aula", self.template)

    def test_consulta_usa_tokens_e_tem_regras_responsivas(self):
        for token in (
            "var(--font-sans)",
            "var(--brand)",
            "var(--brand-soft)",
            "var(--text-main)",
            "var(--line)",
            "var(--radius-control)",
            "var(--field-height)",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.styles)
        self.assertIn("@media (max-width: 760px)", self.styles)
        self.assertIn("@media (prefers-reduced-motion: reduce)", self.styles)


if __name__ == "__main__":
    unittest.main()
