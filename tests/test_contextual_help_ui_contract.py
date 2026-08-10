import json
import re
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

import main


ROOT = Path(__file__).resolve().parents[1]


class ContextualHelpUiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(main.app)
        cls.payload = json.loads(
            (ROOT / "static/data/help-contexts.json").read_text(encoding="utf-8")
        )

    def test_help_content_has_valid_contract_and_no_html(self):
        self.assertEqual(self.payload["version"], 1)
        contexts = self.payload["contexts"]
        self.assertIsInstance(contexts, dict)
        self.assertTrue(contexts)

        for key, content in contexts.items():
            with self.subTest(context=key):
                self.assertTrue(key.startswith("/"))
                for field in ("title", "objective"):
                    self.assertIsInstance(content.get(field), str)
                    self.assertTrue(content[field].strip())
                for field in ("decisions", "steps"):
                    self.assertIsInstance(content.get(field), list)
                    self.assertTrue(content[field])
                    self.assertTrue(all(isinstance(item, str) and item.strip() for item in content[field]))
                self.assertIsInstance(content.get("cautions", []), list)
                serialized = json.dumps(content, ensure_ascii=False)
                self.assertNotRegex(serialized, r"</?[a-z][^>]*>", re.IGNORECASE)

    def test_help_content_covers_routes_tabs_and_steps(self):
        required = {
            "/servicos",
            "/meu-perfil",
            "/impressao",
            "/impressao/historico",
            *{f"/impressao|step={step}" for step in range(1, 6)},
            "/agendamento",
            "/agendamento/meus-agendamentos",
            "/agendamento/calendario",
            "/agendamento/catalogo",
            *{f"/agendamento|step={step}" for step in range(1, 6)},
            "/apc",
            "/apc/calendario",
            "/download",
            "/download/detalhes",
            "/horario-escolar",
            "/pcpi",
            "/coordenacao",
            *{
                f"/coordenacao|tab={tab}"
                for tab in (
                    "ocorrencias",
                    "registros-pendentes",
                    "pre-registros",
                    "regimento",
                    "estudantes",
                    "acompanhamento-docente",
                    "relatorios",
                )
            },
            *{
                f"/coordenacao|tab=ocorrencias|step={step}"
                for step in range(1, 4)
            },
            "/relatorios",
            *{
                f"/relatorios|tab={tab}"
                for tab in ("dashboard", "impressoes", "recursos", "anexos", "professores")
            },
            "/preconselho",
            *{
                f"/preconselho/{page}"
                for page in ("consolidacao", "reavaliacao", "relatorios", "rav", "configuracoes")
            },
            *{
                f"/admin/{page}"
                for page in (
                    "professores",
                    "atribuicoes",
                    "turmas",
                    "aulas",
                    "recursos",
                    "impressao",
                    "relatorios",
                    "auditoria",
                )
            },
        }

        missing = required - set(self.payload["contexts"])
        self.assertFalse(missing, f"Contextos de ajuda ausentes: {sorted(missing)}")

    def test_shared_navbar_exposes_accessible_help_dialog(self):
        navbar = (ROOT / "templates/includes/app_navbar.html").read_text(encoding="utf-8")
        script = (ROOT / "static/js/core/app_help.js").read_text(encoding="utf-8")

        self.assertLess(navbar.index('id="appNavbarHelpToggle"'), navbar.index('id="appNavbarProfileToggle"'))
        for fragment in (
            'aria-label="Ajuda desta tela"',
            'aria-controls="appHelpDialog"',
            'id="appHelpDialog"',
            'role="dialog"',
            'aria-modal="true"',
            'id="appHelpClose"',
            "data/help-contexts.json",
        ):
            self.assertIn(fragment, navbar)
        self.assertIn("dialog.showModal()", script)
        self.assertIn('event.preventDefault()', script)
        self.assertIn('event.key === "Escape"', script)
        self.assertIn('toggle.focus({ preventScroll: true })', script)
        self.assertNotIn("innerHTML", script)

    def test_help_assets_only_load_on_authenticated_surfaces(self):
        authenticated = self.client.get("/servicos")
        self.assertEqual(authenticated.status_code, 200)
        for asset in (
            "/static/css/components/app-help.css",
            "/static/js/core/app_help.js",
            "/static/data/help-contexts.json",
        ):
            if asset.endswith(".json"):
                self.assertEqual(self.client.get(asset).status_code, 200)
            else:
                self.assertIn(asset, authenticated.text)
        self.assertIn('id="appNavbarHelpToggle"', authenticated.text)

        for path in ("/login-page", "/cadastro-professor"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertNotIn("app-help.css", response.text)
            self.assertNotIn("app_help.js", response.text)
            self.assertNotIn('id="appNavbarHelpToggle"', response.text)
            self.assertNotIn('id="appHelpDialog"', response.text)

    def test_all_current_navbar_consumers_receive_help(self):
        templates = [
            *ROOT.glob("templates/**/*.html"),
            *ROOT.glob("modules/admin/templates/admin/*.html"),
        ]
        consumers = [
            path
            for path in templates
            if 'include "includes/app_navbar.html"' in path.read_text(encoding="utf-8")
        ]

        self.assertEqual(len(consumers), 27)
        for template in consumers:
            with self.subTest(template=template.relative_to(ROOT)):
                text = template.read_text(encoding="utf-8")
                self.assertIn('include "includes/style_bundle.html"', text)


if __name__ == "__main__":
    unittest.main()
