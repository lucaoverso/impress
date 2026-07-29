import unittest

from modules.admin import router as admin_pages
from routers.config import templates


class AdminPagesRouterTests(unittest.TestCase):
    def test_rotas_e_templates_do_admin(self):
        caminhos = {route.path for route in admin_pages.router.routes}
        esperados = {f"/admin/{pagina}" for pagina in admin_pages.PAGE_TITLES}

        self.assertEqual(caminhos, esperados)
        for pagina in admin_pages.PAGE_TITLES:
            template = admin_pages.DEDICATED_TEMPLATES[pagina]
            self.assertIsNotNone(templates.get_template(template))

        self.assertEqual(set(admin_pages.DEDICATED_TEMPLATES), set(admin_pages.PAGE_TITLES))


if __name__ == "__main__":
    unittest.main()
