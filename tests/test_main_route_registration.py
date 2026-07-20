import unittest
from collections import Counter

import main


class MainRouteRegistrationTest(unittest.TestCase):
    def test_registra_modulos_recuperados_sem_rotas_duplicadas(self):
        routes = [
            (method, route.path)
            for route in main.app.routes
            for method in getattr(route, "methods", set())
        ]
        registered = set(routes)

        self.assertIn(("GET", "/admin"), registered)
        self.assertIn(("GET", "/admin/turmas"), registered)
        self.assertIn(("GET", "/admin/recursos"), registered)
        self.assertIn(("PATCH", "/me/profile"), registered)
        self.assertIn(("GET", "/impressao/impressoras"), registered)
        self.assertIn(("GET", "/impressao/historico"), registered)
        self.assertIn(("GET", "/agendamento/meus-agendamentos"), registered)
        self.assertIn(("GET", "/agendamento/calendario"), registered)
        self.assertIn(("GET", "/preconselho/consolidacao"), registered)
        self.assertIn(("GET", "/preconselho/reavaliacao"), registered)
        self.assertIn(("GET", "/preconselho/relatorios"), registered)
        self.assertIn(("GET", "/preconselho/rav"), registered)
        self.assertIn(("GET", "/preconselho/configuracoes"), registered)
        self.assertFalse([route for route, count in Counter(routes).items() if count > 1])


if __name__ == "__main__":
    unittest.main()
