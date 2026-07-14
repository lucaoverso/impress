import importlib
import os
import re
import sys
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request


def _reload_modulos(asset_version: str | None):
    if asset_version is None:
        os.environ.pop("STATIC_ASSET_VERSION", None)
    else:
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

    def test_impressao_renderiza_fluxo_guiado_e_revisao_completa(self):
        config, pages_router = _reload_modulos("build-print-789")
        app = FastAPI()
        app.mount("/static", StaticFiles(directory=str(config.STATIC_DIR)), name="static")

        resposta = pages_router.impressao_page(_criar_request(app, "/impressao"))
        html = resposta.body.decode("utf-8")

        self.assertEqual(resposta.headers.get("Cache-Control"), "no-store")
        self.assertIn("css/pages/professor.css?v=build-print-789", html)
        self.assertIn("js/printing/index.js?v=build-print-789", html)
        self.assertIn('id="printStepperCard"', html)
        self.assertIn('id="printSelectionContext"', html)
        self.assertIn('id="resumoDuplex"', html)
        self.assertIn('id="resumoTags"', html)
        self.assertIn('id="printFeedbackVisible"', html)
        self.assertIn('role="dialog"', html)
        self.assertLess(html.index('id="tagsConferencia"'), html.index('id="etapaConferencia"'))

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
        self.assertIn('id="btnVoltarServicos"', html)
        self.assertIn("Serviços", html)
        self.assertIn('id="apcUsuario"', html)
        self.assertIn("<h1>Central de Anexos</h1>", html)
        self.assertNotIn('id="apcModeTabs"', html)
        self.assertIn('id="btnAlternarCalendarioApc"', html)
        self.assertIn('id="apcCalendarDrawer"', html)
        self.assertIn('id="apcDocenteDetalhe"', html)
        self.assertIn('id="apcArquivoPreviewModal"', html)
        self.assertIn('id="apcArquivoPreviewFrame"', html)
        self.assertIn('id="btnApcImprimirArquivo"', html)
        self.assertIn('id="apcPrintWizardModal"', html)
        self.assertIn('id="formApcImpressao"', html)
        self.assertIn('id="apcActivityModal"', html)
        self.assertIn('id="apcActivityFormSlot"', html)
        self.assertIn('id="apcActivityPreviewPages"', html)
        self.assertIn('id="btnSalvarActivityModalApc"', html)
        self.assertIn('id="btnAbrirNovaApc"', html)
        self.assertIn('id="apcGestaoFiltros"', html)
        self.assertIn('id="apcFiltroProfessor"', html)
        self.assertIn('id="apcFiltroDisciplina"', html)
        self.assertIn('id="apcFiltroTurma"', html)
        self.assertIn('id="apcOrdenacaoGestao"', html)
        self.assertIn('id="apcGestaoDetalhe"', html)
        self.assertNotIn('id="apcTabBtnArquivos"', html)
        self.assertNotIn('id="apcArquivosLista"', html)

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
        self.assertIn('id="anexosResumo"', html)
        self.assertIn("Insights da Gestao", html)

    def test_login_page_gera_asset_version_dinamico_quando_configurado(self):
        config, pages_router = _reload_modulos("dynamic")
        app = FastAPI()
        app.mount("/static", StaticFiles(directory=str(config.STATIC_DIR)), name="static")

        with patch("routers.config.time.time_ns", side_effect=[111111, 222222]):
            resposta_a = pages_router.login_page(_criar_request(app, "/login-page"))
            resposta_b = pages_router.login_page(_criar_request(app, "/login-page"))

        html_a = resposta_a.body.decode("utf-8")
        html_b = resposta_b.body.decode("utf-8")

        versao_a = re.search(r"js/app\.js\?v=(\d+)", html_a)
        versao_b = re.search(r"js/app\.js\?v=(\d+)", html_b)

        self.assertIsNotNone(versao_a)
        self.assertIsNotNone(versao_b)
        self.assertEqual(versao_a.group(1), "111111")
        self.assertEqual(versao_b.group(1), "222222")


if __name__ == "__main__":
    unittest.main()
