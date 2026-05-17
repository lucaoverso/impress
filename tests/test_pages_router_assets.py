import importlib
import os
import sys
import unittest

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request


def _reload_modulos(asset_version: str):
    os.environ["STATIC_ASSET_VERSION"] = asset_version

    for nome_modulo in ("routers.config", "routers.pages_router"):
        if nome_modulo in sys.modules:
            del sys.modules[nome_modulo]

    config = importlib.import_module("routers.config")
    pages_router = importlib.import_module("routers.pages_router")
    return config, pages_router


def _criar_request(app: FastAPI, path: str) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": [],
        "query_string": b"",
        "server": ("testserver", 80),
        "client": ("testclient", 50000),
        "scheme": "http",
        "root_path": "",
        "app": app,
    }
    return Request(scope)


class PagesRouterAssetsTest(unittest.TestCase):
    def setUp(self):
        self._old_static_asset_version = os.environ.get("STATIC_ASSET_VERSION")
        self._old_router_config = sys.modules.get("routers.config")
        self._old_pages_router = sys.modules.get("routers.pages_router")

    def tearDown(self):
        if self._old_static_asset_version is None:
            os.environ.pop("STATIC_ASSET_VERSION", None)
        else:
            os.environ["STATIC_ASSET_VERSION"] = self._old_static_asset_version

        if self._old_router_config is None:
            sys.modules.pop("routers.config", None)
        else:
            sys.modules["routers.config"] = self._old_router_config

        if self._old_pages_router is None:
            sys.modules.pop("routers.pages_router", None)
        else:
            sys.modules["routers.pages_router"] = self._old_pages_router

    def test_login_page_injeta_asset_version_e_no_store(self):
        config, pages_router = _reload_modulos("build-login-123")
        app = FastAPI()
        app.mount("/static", StaticFiles(directory=str(config.STATIC_DIR)), name="static")

        resposta = pages_router.login_page(_criar_request(app, "/login-page"))
        html = resposta.body.decode("utf-8")

        self.assertEqual(resposta.headers.get("Cache-Control"), "no-store")
        self.assertIn("css/base.css?v=build-login-123", html)
        self.assertIn("css/pages/auth.css?v=build-login-123", html)
        self.assertIn("js/app.js?v=build-login-123", html)

    def test_cadastro_professor_injeta_asset_version_e_no_store(self):
        config, pages_router = _reload_modulos("build-cadastro-456")
        app = FastAPI()
        app.mount("/static", StaticFiles(directory=str(config.STATIC_DIR)), name="static")

        resposta = pages_router.cadastro_professor_page(_criar_request(app, "/cadastro-professor"))
        html = resposta.body.decode("utf-8")

        self.assertEqual(resposta.headers.get("Cache-Control"), "no-store")
        self.assertIn("css/base.css?v=build-cadastro-456", html)
        self.assertIn("css/pages/professor.css?v=build-cadastro-456", html)
        self.assertIn("js/cadastro-professor.js?v=build-cadastro-456", html)

    def test_horario_escolar_injeta_asset_version_e_no_store(self):
        config, pages_router = _reload_modulos("build-horario-789")
        app = FastAPI()
        app.mount("/static", StaticFiles(directory=str(config.STATIC_DIR)), name="static")

        resposta = pages_router.horario_escolar_page(_criar_request(app, "/horario-escolar"))
        html = resposta.body.decode("utf-8")

        self.assertEqual(resposta.headers.get("Cache-Control"), "no-store")
        self.assertIn("charset=utf-8", resposta.headers.get("content-type", "").lower())
        self.assertIn("css/base.css?v=build-horario-789", html)
        self.assertIn("css/pages/horario-escolar.css?v=build-horario-789", html)
        self.assertIn("js/horario_escolar.js?v=build-horario-789", html)
        self.assertIn("Horário escolar", html)

    def test_apc_injeta_asset_version_e_no_store(self):
        config, pages_router = _reload_modulos("build-apc-321")
        app = FastAPI()
        app.mount("/static", StaticFiles(directory=str(config.STATIC_DIR)), name="static")

        resposta = pages_router.apc_page(_criar_request(app, "/apc"))
        html = resposta.body.decode("utf-8")

        self.assertEqual(resposta.headers.get("Cache-Control"), "no-store")
        self.assertIn("charset=utf-8", resposta.headers.get("content-type", "").lower())
        self.assertIn("css/base.css?v=build-apc-321", html)
        self.assertIn("css/pages/apc.css?v=build-apc-321", html)
        self.assertIn("js/apc.js?v=build-apc-321", html)
        self.assertIn("Voltar aos serviços", html)
        self.assertIn('id="apcUsuario"', html)

    def test_relatorios_injeta_asset_version_e_no_store(self):
        config, pages_router = _reload_modulos("build-relatorios-654")
        app = FastAPI()
        app.mount("/static", StaticFiles(directory=str(config.STATIC_DIR)), name="static")

        resposta = pages_router.relatorios_page(_criar_request(app, "/relatorios"))
        html = resposta.body.decode("utf-8")

        self.assertEqual(resposta.headers.get("Cache-Control"), "no-store")
        self.assertIn("charset=utf-8", resposta.headers.get("content-type", "").lower())
        self.assertIn("css/base.css?v=build-relatorios-654", html)
        self.assertIn("css/pages/relatorios.css?v=build-relatorios-654", html)
        self.assertIn("js/relatorios.js?v=build-relatorios-654", html)
        self.assertIn("cdn.jsdelivr.net/npm/chart.js", html)
        self.assertIn('id="relatoriosCards"', html)
        self.assertIn("Insights da Gestao", html)


if __name__ == "__main__":
    unittest.main()
