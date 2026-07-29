import re
import unittest

from fastapi.testclient import TestClient

import main


class AdminPageAssetsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(main.app)

    def test_admin_redireciona_para_professores(self):
        response = self.client.get("/admin", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["location"], "/admin/professores")

    def test_paginas_renderizam_e_carregam_apenas_scripts_existentes(self):
        scripts_por_pagina = {
            "professores": {"professores-form.js", "professores-lista.js", "professores.js", "professores-page.js"},
            "atribuicoes": {"atribuicoes-form.js", "atribuicoes.js", "atribuicoes-page.js"},
            "turmas": {"grade-aulas.js", "turmas-disciplinas-base.js", "turmas-disciplinas.js", "turmas-cadastro.js", "disciplinas.js", "turmas-page.js"},
            "aulas": {"grade-aulas.js", "aulas.js", "aulas-page.js"},
            "recursos": {"recursos.js", "recursos-page.js"},
            "impressao": {"impressao.js", "impressao-page.js"},
            "relatorios": {"relatorios.js", "relatorios-page.js"},
            "auditoria": {"audit.js", "auditoria-page.js"},
        }

        for pagina, esperados in scripts_por_pagina.items():
            with self.subTest(pagina=pagina):
                response = self.client.get(f"/admin/{pagina}")
                self.assertEqual(response.status_code, 200)
                fontes = re.findall(r'<script[^>]+src="([^"]+)"', response.text)
                scripts_admin = {
                    fonte.split("/js/admin/", 1)[1].split("?", 1)[0]
                    for fonte in fontes
                    if "/js/admin/" in fonte
                }
                self.assertEqual(scripts_admin, {"core.js", *esperados})
                for fonte in fontes:
                    self.assertEqual(self.client.get(fonte).status_code, 200, fonte)


if __name__ == "__main__":
    unittest.main()
