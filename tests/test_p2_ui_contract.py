import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class P2UiContractTest(unittest.TestCase):
    def test_assets_criticos_sao_locais_e_comprimidos(self):
        main = (ROOT / "main.py").read_text(encoding="utf-8")
        templates = [
            ROOT / "templates" / "relatorios.html",
            ROOT / "templates" / "apc" / "index.html",
            ROOT / "templates" / "printing" / "index.html",
        ]
        vendor_assets = [
            ROOT / "static" / "vendor" / "chartjs" / "chart.umd.min.js",
            ROOT / "static" / "vendor" / "pdfjs" / "pdf.min.js",
            ROOT / "static" / "vendor" / "pdfjs" / "pdf.worker.min.js",
        ]

        self.assertIn("GZipMiddleware", main)
        self.assertIn("minimum_size=1000", main)
        for template in templates:
            self.assertNotRegex(template.read_text(encoding="utf-8"), r'<script[^>]+src="https?://')
        for template in templates[1:]:
            content = template.read_text(encoding="utf-8")
            self.assertIn('src="/static/vendor/pdfjs/pdf.min.js?v=3.11.174"', content)
            self.assertIn('"/static/vendor/pdfjs/pdf.worker.min.js?v=3.11.174"', content)
        for asset in vendor_assets:
            self.assertTrue(asset.is_file())
            self.assertGreater(asset.stat().st_size, 10_000)

    def test_logo_do_frontend_usa_variante_dimensionada(self):
        optimized = ROOT / "static" / "img" / "logo_escola-256.webp"
        original = ROOT / "static" / "img" / "logo_escola.PNG"
        consumers = [
            ROOT / "templates" / "includes" / "app_navbar.html",
            ROOT / "templates" / "login.html",
            ROOT / "templates" / "coordenacao.html",
        ]

        self.assertTrue(optimized.is_file())
        self.assertLess(optimized.stat().st_size, original.stat().st_size // 5)
        for consumer in consumers:
            template = consumer.read_text(encoding="utf-8")
            self.assertIn("logo_escola-256.webp", template)
            self.assertRegex(template, r'width="\d+"')
            self.assertRegex(template, r'height="\d+"')

    def test_central_usa_icones_semanticos_sem_dependencia_externa(self):
        template = (ROOT / "templates" / "servicos.html").read_text(encoding="utf-8")
        icons = re.findall(r'<span class="service-card-icon [^"]+" aria-hidden="true">', template)

        self.assertEqual(len(icons), 10)
        self.assertNotIn("fonts.googleapis.com", template)
        self.assertNotIn("tailwindcss.com", template)

    def test_cards_da_central_sao_links_nativos(self):
        template = (ROOT / "templates" / "servicos.html").read_text(encoding="utf-8")

        self.assertEqual(len(re.findall(r'<a id="card\w+" class="service-card"[^>]+href="/[^"]+"', template)), 10)
        self.assertNotIn('<article id="card', template)

    def test_cards_da_central_usam_grade_responsiva_de_tres_colunas(self):
        css = (ROOT / "static" / "css" / "pages" / "services-scheduler.css").read_text(encoding="utf-8")

        self.assertIn("grid-template-columns: repeat(3, minmax(0, 1fr));", css)
        self.assertIn("grid-template-columns: repeat(2, minmax(0, 1fr));", css)
        self.assertIn(".service-card-icon", css)

    def test_atalhos_da_central_respeitam_o_atributo_hidden(self):
        css = (ROOT / "static" / "css" / "components" / "app-sidebar.css").read_text(encoding="utf-8")

        self.assertIn(".app-sidebar-link[hidden] { display: none; }", css)

    def test_central_mobile_reutiliza_sidebar_compartilhada(self):
        template = (ROOT / "templates" / "servicos.html").read_text(encoding="utf-8")
        css = (ROOT / "static" / "css" / "pages" / "services-scheduler.css").read_text(encoding="utf-8")

        self.assertIn("viewport-fit=cover", template)
        self.assertNotIn(".services-dashboard-body .app-sidebar {", css)
        self.assertNotIn(".services-dashboard-body .app-topbar.app-navbar", css)
        self.assertIn("grid-template-columns: 48px minmax(0, 1fr) 20px;", css)
        self.assertIn('mobile_label": "Início"', (ROOT / "templates" / "includes" / "app_sidebar_config.html").read_text(encoding="utf-8"))

    def test_tokens_semanticos_tem_uma_unica_vocabulario(self):
        css = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "static" / "css").rglob("*.css"))

        for obsolete in ("--text-soft", "--surface-muted", "--surface-subtle", "--danger"):
            with self.subTest(obsolete=obsolete):
                self.assertNotIn(f"var({obsolete}", css)

    def test_padroes_compartilhados_sem_consumidor_foram_removidos(self):
        components = (ROOT / "static" / "css" / "components.css").read_text(encoding="utf-8")

        self.assertNotIn(".app-navbar-drawer", components)
        self.assertNotIn(".app-navbar-toggle", components)
        self.assertNotIn(".stat-grid", components)
        self.assertFalse((ROOT / "templates" / "includes" / "ui" / "action_button.html").exists())

    def test_agendamento_e_historico_oferecem_recuperacao_de_erro(self):
        scheduling = (ROOT / "static" / "js" / "scheduling" / "bookings_pages.js").read_text(encoding="utf-8")
        history = (ROOT / "static" / "js" / "printing" / "history.js").read_text(encoding="utf-8")

        self.assertIn("renderLoadError", scheduling)
        self.assertIn('retry.textContent = "Tentar novamente"', scheduling)
        self.assertIn("renderLoadError", history)
        self.assertIn('retry.textContent = "Tentar novamente"', history)

    def test_controles_principais_de_agendamento_e_historico_tem_44_px(self):
        scheduling = (ROOT / "static" / "css" / "pages" / "scheduling-pages.css").read_text(encoding="utf-8")
        history = (ROOT / "static" / "css" / "printing" / "history.css").read_text(encoding="utf-8")

        self.assertIn(".booking-sort-controls button {\n    min-height: 44px;", scheduling)
        self.assertIn(".booking-item-actions .print-secondary-btn { min-height: 44px; }", scheduling)
        self.assertRegex(history, r"\.print-history-item-actions button \{\n    min-height: 44px;")

    def test_catalogo_de_recursos_nao_forca_selecao_e_aceita_clique_no_card(self):
        script = (ROOT / "static" / "js" / "scheduling" / "resource_catalog.js").read_text(encoding="utf-8")

        self.assertIn('article.addEventListener("click"', script)
        self.assertIn('article.addEventListener("keydown"', script)
        self.assertIn('article.setAttribute("aria-pressed"', script)
        self.assertIn("resetDrawer();", script)
        self.assertNotIn("selectedResourceId = Number(filtered[0].id)", script)
        self.assertNotIn("openDrawer(selected, null, true)", script)

    def test_acoes_de_revisao_apc_ficam_ocultas_para_professores(self):
        template = (ROOT / "templates" / "apc" / "index.html").read_text(encoding="utf-8")
        script = (ROOT / "static" / "js" / "apc.js").read_text(encoding="utf-8")
        stylesheet = (ROOT / "static" / "css" / "apc" / "dialogs.css").read_text(encoding="utf-8")

        self.assertIn('id="formApcReview" class="apc-review-form" hidden', template)
        self.assertIn('id="btnSalvarReviewApc" class="btn-destaque"', template)
        self.assertIn("form.hidden = !gestaoAtiva;", script)
        self.assertIn('el("btnSalvarReviewApc").hidden = !gestaoAtiva;', script)
        self.assertIn(".apc-review-panel[hidden], .apc-review-form[hidden],", stylesheet)
        self.assertIn("#btnSalvarReviewApc[hidden] { display: none; }", stylesheet)

    def test_historico_apc_identifica_decisao_data_e_responsavel(self):
        script = (ROOT / "static" / "js" / "apc.js").read_text(encoding="utf-8")
        stylesheet = (ROOT / "static" / "css" / "apc" / "dialogs.css").read_text(encoding="utf-8")

        self.assertIn('if (statusNormalizado === "APROVADO") return "Aprovado";', script)
        self.assertIn('cargo === "COORDENADOR"', script)
        self.assertIn('? "Coord."', script)
        self.assertIn('cargo === "ADMIN"', script)
        self.assertIn('? "PCPI"', script)
        self.assertIn('responsavel ? `Por ${responsavel}` : ""', script)
        self.assertIn("envio.reviewed_at", script)
        self.assertIn(".apc-review-history-event::before", stylesheet)


if __name__ == "__main__":
    unittest.main()
