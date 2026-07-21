import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class P3UiPolishContractTest(unittest.TestCase):
    def test_tokens_compartilhados_cobrem_estados_e_camadas(self):
        base = (ROOT / "static" / "css" / "base.css").read_text(encoding="utf-8")
        css = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "static" / "css").rglob("*.css"))

        for token in (
            "--state-danger-bg",
            "--state-success-bg",
            "--surface-overlay",
            "--overlay-scrim",
            "--brand-outline",
            "--z-modal",
            "--z-modal-top",
        ):
            self.assertIn(token, base)
        self.assertNotRegex(css, r"z-index:\s*(?:[1-9]\d{2,})\b")

    def test_transicoes_e_markup_nao_usam_atalhos_arriscados(self):
        css = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "static" / "css").rglob("*.css"))
        login = (ROOT / "templates" / "login.html").read_text(encoding="utf-8")
        start = login.index('<img class="logo-escola')
        logo = login[start:login.index(">", start)]

        self.assertNotRegex(css, r"transition:\s*all\b")
        self.assertEqual(logo.count('class="'), 1)

    def test_preview_de_download_tem_estado_inicial_e_dimensoes(self):
        template = (ROOT / "templates" / "download.html").read_text(encoding="utf-8")
        script = (ROOT / "static" / "js" / "download.js").read_text(encoding="utf-8")
        start = template.index('id="previewMiniatura"')
        image = template[start:template.index(">", start)]

        for attribute in ('src="/static/img/download-videos.webp"', 'width="320"', 'height="180"', "hidden"):
            self.assertIn(attribute, image)
        self.assertIn("previewMiniatura.hidden = !info.miniatura_url", script)

    def test_progresso_de_impressao_anima_transform(self):
        css = (ROOT / "static" / "css" / "pages" / "professor.css").read_text(encoding="utf-8")
        start = css.index(".print-progress-steps::after {")
        progress = css[start:css.index(".print-progress-step {", start)]

        self.assertIn("transition: transform var(--motion-fast);", progress)
        self.assertIn("transform: scaleX(1);", progress)
        self.assertNotIn("transition: width", progress)

    def test_copias_prioritarias_estao_acentuadas(self):
        reports = (ROOT / "templates" / "relatorios.html").read_text(encoding="utf-8")
        audit = (ROOT / "templates" / "includes" / "admin_audit_panel.html").read_text(encoding="utf-8")
        report_script = (ROOT / "static" / "js" / "relatorios.js").read_text(encoding="utf-8")

        for text in ("Relatórios gerenciais", "Filtro por período", "Recursos tecnológicos", "Situação das entregas"):
            self.assertIn(text, reports)
        for text in ("Histórico de atividades", "Acompanhe acessos e operações", "Página 1", "Próxima"):
            self.assertIn(text, audit)
        for text in ("Atualizando relatórios...", "Relatórios atualizados.", "Relatório enviado com sucesso."):
            self.assertIn(text, report_script)

    def test_contexto_administrativo_usa_gestao_acentuada(self):
        templates = list((ROOT / "modules" / "admin" / "templates" / "admin").glob("*.html"))
        consumers = [path for path in templates if "navbar_context" in path.read_text(encoding="utf-8")]

        self.assertEqual(len(consumers), 8)
        for template in consumers:
            self.assertIn('navbar_context = "Painel de gestão"', template.read_text(encoding="utf-8"))

    def test_preview_de_impressao_se_adapta_a_desktop_e_mobile(self):
        template = (ROOT / "templates" / "printing" / "index.html").read_text(encoding="utf-8")
        css = (ROOT / "static" / "css" / "printing" / "experience.css").read_text(encoding="utf-8")
        mobile_css = (ROOT / "static" / "css" / "printing" / "mobile-controls.css").read_text(encoding="utf-8")
        desktop_css = (ROOT / "static" / "css" / "printing" / "desktop-carousel.css").read_text(encoding="utf-8")
        script = (ROOT / "static" / "js" / "professor.js").read_text(encoding="utf-8")

        self.assertIn("viewport-fit=cover", template)
        self.assertNotIn('href="/impressao/historico">\n                    Meus pedidos', template)
        self.assertIn('id="printPreviewSummary"', template)
        self.assertIn('id="btnVoltarAjustesPreview"', template)
        self.assertIn("grid-template-columns: minmax(390px, 0.9fr) minmax(500px, 1.1fr);", css)
        self.assertIn("height: 100dvh;", css)
        self.assertIn("env(safe-area-inset-bottom)", css)
        self.assertIn("css/printing/mobile-controls.css", template)
        self.assertIn("css/printing/desktop-carousel.css", template)
        self.assertIn("position: fixed;", mobile_css)
        self.assertIn(".professor-page .print-context-preview-btn svg", mobile_css)
        self.assertIn(".professor-page #etapaConfiguracoes .print-step-actions", mobile_css)
        self.assertIn("order: 2;", mobile_css)
        self.assertIn(".professor-page .print-selection-context", desktop_css)
        self.assertIn("scroll-snap-type: x mandatory;", desktop_css)
        self.assertIn('container.classList.add("is-carousel");', script)
        self.assertNotIn("obterDimensoesMiniaturaDesktop", script)
        self.assertIn('el("btnVoltarAjustesPreview")?.addEventListener("click", fecharPreviewMobile);', script)


if __name__ == "__main__":
    unittest.main()
