import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class P2UiContractTest(unittest.TestCase):
    def test_assets_criticos_sao_locais_e_comprimidos(self):
        main = (ROOT / "main.py").read_text(encoding="utf-8")
        templates = [
            ROOT / "templates" / "relatorios.html",
            ROOT / "templates" / "apc.html",
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

    def test_central_usa_imagens_otimizadas_sem_deslocamento(self):
        template = (ROOT / "templates" / "servicos.html").read_text(encoding="utf-8")
        images = re.findall(r'<img class="service-img"[^>]+>', template)

        self.assertEqual(len(images), 10)
        for image in images:
            self.assertIn('.webp"', image)
            self.assertIn('width="512"', image)
            self.assertIn('height="512"', image)
            self.assertIn('decoding="async"', image)
        self.assertGreaterEqual(sum('loading="lazy"' in image for image in images), 8)

    def test_cards_da_central_sao_links_nativos(self):
        template = (ROOT / "templates" / "servicos.html").read_text(encoding="utf-8")

        self.assertEqual(len(re.findall(r'<a id="card\w+" class="service-card"[^>]+href="/[^"]+"', template)), 10)
        self.assertNotIn('<article id="card', template)

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


if __name__ == "__main__":
    unittest.main()
