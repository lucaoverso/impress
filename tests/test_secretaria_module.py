import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SecretariaModuleContractTests(unittest.TestCase):
    def test_routes_cover_school_life_configuration(self):
        secretaria = (ROOT / "modules" / "secretaria" / "router.py").read_text(encoding="utf-8")
        self.assertIn('@router.get("/secretaria")', secretaria)
        self.assertIn('@router.get("/secretaria/estudantes")', secretaria)
        self.assertIn('@router.get("/secretaria/horarios")', secretaria)
        for route in ("professores", "atribuicoes", "turmas", "aulas"):
            self.assertIn(f'@router.get("/secretaria/{route}")', secretaria)

        main = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn("app.include_router(secretaria_router)", main)

    def test_school_schedule_public_page_is_read_only(self):
        pages = (ROOT / "routers" / "pages_router.py").read_text(encoding="utf-8")
        template = (ROOT / "templates" / "horario_escolar.html").read_text(encoding="utf-8")
        css = (ROOT / "static" / "css" / "pages" / "horario-escolar.css").read_text(encoding="utf-8")
        self.assertIn('"somente_leitura": True', pages)
        self.assertIn("horario-readonly", template)
        self.assertIn(".horario-readonly #horarioBuilderGrid", css)

    def test_students_are_exposed_only_from_secretaria_navigation(self):
        sidebar = (ROOT / "templates" / "includes" / "app_sidebar_config.html").read_text(encoding="utf-8")
        coordinator_block = sidebar.split('{% elif navbar_current == "coordenacao" %}', 1)[1].split("{% elif", 1)[0]
        self.assertNotIn('tab_value": "estudantes"', coordinator_block)
        self.assertIn('href": "/secretaria/estudantes"', sidebar)

    def test_student_editor_has_responsive_non_cramped_actions(self):
        css = (ROOT / "static" / "css" / "pages" / "coordenacao.css").read_text(encoding="utf-8")
        self.assertIn("width: min(1160px, calc(100vw - 32px));", css)
        self.assertIn(".estudante-editor-content .coordenacao-form-actions", css)
        self.assertIn("min-width: 160px;", css)
        self.assertIn("width: 100%;", css)

    def test_student_editor_uses_accessible_tabs_and_progressive_import(self):
        template = (ROOT / "templates" / "coordenacao.html").read_text(encoding="utf-8")
        script = (ROOT / "static" / "js" / "coordenacao" / "cadastros.js").read_text(encoding="utf-8")
        self.assertIn('role="tablist"', template)
        self.assertEqual(template.count('role="tab"'), 2)
        self.assertIn('role="tabpanel"', template)
        self.assertIn('<details class="coordenacao-import-box">', template)
        self.assertIn('aria-atomic="true"', template)
        self.assertIn('botao.setAttribute("aria-selected", String(ativo))', script)
        self.assertIn('formulario.hidden = secao !== "dados"', script)

    def test_secretaria_forms_use_continuous_surfaces(self):
        css = (ROOT / "static" / "css" / "pages" / "secretaria.css").read_text(encoding="utf-8")
        self.assertIn(".secretaria-module-page .admin-card {", css)
        self.assertIn("border-bottom: 1px solid var(--line-soft);", css)
        self.assertIn("box-shadow: none;", css)
        self.assertIn(".secretaria-module-page .admin-fieldset", css)

    def test_unused_student_report_fields_are_removed_and_form_has_spacing(self):
        template = (ROOT / "templates" / "coordenacao.html").read_text(encoding="utf-8")
        script = (ROOT / "static" / "js" / "coordenacao" / "cadastros.js").read_text(encoding="utf-8")
        css = (ROOT / "static" / "css" / "pages" / "coordenacao.css").read_text(encoding="utf-8")
        for field_id in (
            "estudanteLaudoRelatoApoio",
            "estudanteLaudoRecomendacoes",
            "estudanteLaudoObservacoesRestritas",
        ):
            self.assertNotIn(field_id, template)
            self.assertNotIn(field_id, script)
        self.assertIn("#formLaudoEstudante .coordenacao-form-grid", css)
        self.assertIn("row-gap: 24px;", css)
        self.assertIn("gap: 32px;", css)
        self.assertIn("min-width: max-content;", css)
        self.assertIn("@media (max-width: 900px)", css)


if __name__ == "__main__":
    unittest.main()
