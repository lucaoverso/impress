import importlib
import os
import sys
import tempfile
import unittest

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request


def _reload_modulos(db_path: str):
    os.environ["DB_PATH"] = db_path
    for nome_modulo in (
        "database",
        "db._proxy",
        "db.relatorios",
        "routers.relatorios_router",
    ):
        if nome_modulo in sys.modules:
            del sys.modules[nome_modulo]

    database = importlib.import_module("database")
    relatorios_router = importlib.import_module("routers.relatorios_router")
    return database, relatorios_router


class RelatoriosRouterTest(unittest.TestCase):
    def setUp(self):
        self._old_db_path = os.environ.get("DB_PATH")
        self._old_static_asset_version = os.environ.get("STATIC_ASSET_VERSION")

    def tearDown(self):
        if self._old_db_path is None:
            os.environ.pop("DB_PATH", None)
        else:
            os.environ["DB_PATH"] = self._old_db_path

        if self._old_static_asset_version is None:
            os.environ.pop("STATIC_ASSET_VERSION", None)
        else:
            os.environ["STATIC_ASSET_VERSION"] = self._old_static_asset_version

    def _usuario_gestor(self) -> dict:
        return {
            "id": 1,
            "nome": "Administrador",
            "perfil": "admin",
            "cargo": "ADMIN",
        }

    def _criar_request(self, app: FastAPI, path: str) -> Request:
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

    def test_dashboard_retorna_zeros_quando_nao_ha_dados(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, relatorios_router = _reload_modulos(db_path)
            database.criar_tabelas()
            database.seed_recursos_padrao()

            resposta = relatorios_router.dashboard_relatorios_api(
                data_inicio="2026-05-01",
                data_fim="2026-05-31",
                usuario=self._usuario_gestor(),
            )

            self.assertEqual(resposta["periodo"]["data_inicio"], "2026-05-01")
            self.assertEqual(resposta["periodo"]["data_fim"], "2026-05-31")
            self.assertEqual(resposta["impressoes"]["resumo"]["total_paginas"], 0)
            self.assertEqual(resposta["impressoes"]["resumo"]["total_jobs"], 0)
            self.assertEqual(resposta["recursos"]["resumo"]["total_reservas"], 0)
            self.assertEqual(resposta["cards"][2]["valor"], "Sem dados")
            self.assertEqual(resposta["cards"][3]["valor"], "Sem dados")
            self.assertEqual(
                resposta["dashboard_geral"]["insights"][0]["texto"],
                "Ainda não há dados suficientes para gerar insights neste período.",
            )
            self.assertGreaterEqual(len(resposta["recursos"]["ranking_recursos"]), 1)
            self.assertEqual(
                resposta["dashboard_geral"]["graficos"]["movimento_periodo"]["paginas"],
                [0] * 31,
            )

    def test_api_dashboard_retorna_json_valido(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, relatorios_router = _reload_modulos(db_path)
            database.criar_tabelas()
            database.seed_recursos_padrao()

            payload = relatorios_router.dashboard_relatorios_api(
                data_inicio="2026-05-01",
                data_fim="2026-05-31",
                usuario=self._usuario_gestor(),
            )

            self.assertIsInstance(payload, dict)
            self.assertIn("periodo", payload)
            self.assertIn("cards", payload)
            self.assertIn("impressoes", payload)
            self.assertIn("recursos", payload)
            self.assertIn(
                "/api/relatorios/dashboard",
                [route.path for route in relatorios_router.router.routes],
            )

    def test_dashboard_consolida_impressoes_e_recursos_reais(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, relatorios_router = _reload_modulos(db_path)
            database.criar_tabelas()
            database.seed_recursos_padrao()

            database.criar_usuario_se_nao_existir(
                nome="Ana Souza",
                email="ana@escola",
                senha_hash="hash-ana",
                perfil="professor",
                cargo="PROFESSOR",
            )
            database.criar_usuario_se_nao_existir(
                nome="Bruno Lima",
                email="bruno@escola",
                senha_hash="hash-bruno",
                perfil="professor",
                cargo="PROFESSOR",
            )

            professora_ana = database.buscar_usuario_por_email("ana@escola")
            professor_bruno = database.buscar_usuario_por_email("bruno@escola")
            recurso = database.listar_recursos_ativos()[0]

            job_ana = database.criar_job(
                usuario_id=int(professora_ana["id"]),
                arquivo="atividade-ana.pdf",
                arquivo_path="/tmp/atividade-ana.pdf",
                copias=1,
                paginas_totais=20,
            )
            database.atualizar_status(job_ana, database.STATUS_CONCLUIDO)

            job_bruno = database.criar_job(
                usuario_id=int(professor_bruno["id"]),
                arquivo="atividade-bruno.pdf",
                arquivo_path="/tmp/atividade-bruno.pdf",
                copias=1,
                paginas_totais=12,
            )
            database.atualizar_status(job_bruno, database.STATUS_CONCLUIDO)

            database.criar_agendamento(
                recurso_id=int(recurso["id"]),
                usuario_id=int(professora_ana["id"]),
                data="2026-05-05",
                turno="MATUTINO",
                aula="1",
                faixa_global=1,
                turma="7 Ano A",
                tema_aula="Pesquisa guiada",
            )
            database.criar_agendamento(
                recurso_id=int(recurso["id"]),
                usuario_id=int(professora_ana["id"]),
                data="2026-05-06",
                turno="MATUTINO",
                aula="2",
                faixa_global=2,
                turma="7 Ano A",
                tema_aula="Producao textual",
            )
            database.criar_agendamento(
                recurso_id=int(recurso["id"]),
                usuario_id=int(professor_bruno["id"]),
                data="2026-05-07",
                turno="MATUTINO",
                aula="3",
                faixa_global=3,
                turma="8 Ano B",
                tema_aula="Roteiro de estudos",
            )

            resposta = relatorios_router.dashboard_relatorios_api(
                data_inicio="2026-05-01",
                data_fim="2026-05-31",
                usuario=self._usuario_gestor(),
            )

            self.assertEqual(resposta["impressoes"]["resumo"]["total_paginas"], 32)
            self.assertEqual(resposta["impressoes"]["resumo"]["total_jobs"], 2)
            self.assertEqual(resposta["recursos"]["resumo"]["total_reservas"], 3)
            self.assertEqual(resposta["cards"][2]["valor"], "Ana Souza")
            self.assertEqual(resposta["cards"][3]["valor"], "Ana Souza")
            self.assertEqual(
                resposta["dashboard_geral"]["graficos"]["impressoes_por_professor"]["valores"],
                [20, 12],
            )
            self.assertEqual(
                resposta["recursos"]["ranking_recursos"][0]["total_reservas"],
                3,
            )
            self.assertEqual(
                resposta["recursos"]["ranking_professores"][0]["total_reservas"],
                2,
            )

    def test_dashboard_gera_insights_da_gestao_por_regras(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, relatorios_router = _reload_modulos(db_path)
            database.criar_tabelas()
            database.seed_recursos_padrao()

            database.criar_usuario_se_nao_existir(
                nome="Ana Souza",
                email="ana@escola",
                senha_hash="hash-ana",
                perfil="professor",
                cargo="PROFESSOR",
            )
            database.criar_usuario_se_nao_existir(
                nome="Bruno Lima",
                email="bruno@escola",
                senha_hash="hash-bruno",
                perfil="professor",
                cargo="PROFESSOR",
            )

            professora_ana = database.buscar_usuario_por_email("ana@escola")
            professor_bruno = database.buscar_usuario_por_email("bruno@escola")
            sala_tecnologia_id = int(
                database.criar_recurso(
                    nome="Sala de Tecnologia 1",
                    tipo="Laboratorio",
                    descricao="Espaco para atividades digitais.",
                    quantidade_itens=1,
                )
            )

            job_ana = database.criar_job(
                usuario_id=int(professora_ana["id"]),
                arquivo="atividade-alta.pdf",
                arquivo_path="/tmp/atividade-alta.pdf",
                copias=1,
                paginas_totais=150,
            )
            database.atualizar_status(job_ana, database.STATUS_CONCLUIDO)

            job_bruno = database.criar_job(
                usuario_id=int(professor_bruno["id"]),
                arquivo="atividade-baixa.pdf",
                arquivo_path="/tmp/atividade-baixa.pdf",
                copias=1,
                paginas_totais=10,
            )
            database.atualizar_status(job_bruno, database.STATUS_CONCLUIDO)
            conn = database.get_connection()
            try:
                conn.execute(
                    """
                    UPDATE jobs
                    SET criado_em = ?, finalizado_em = ?
                    WHERE id = ?
                    """,
                    ("2026-05-02 08:00:00", "2026-05-02 08:30:00", int(job_ana)),
                )
                conn.execute(
                    """
                    UPDATE jobs
                    SET criado_em = ?, finalizado_em = ?
                    WHERE id = ?
                    """,
                    ("2026-05-03 09:00:00", "2026-05-03 09:15:00", int(job_bruno)),
                )
                conn.commit()
            finally:
                conn.close()

            datas = [
                "2026-05-01",
                "2026-05-01",
                "2026-05-01",
                "2026-05-01",
                "2026-05-01",
                "2026-05-04",
                "2026-05-04",
                "2026-05-04",
                "2026-05-04",
                "2026-05-04",
                "2026-05-05",
                "2026-05-05",
            ]
            aulas = ["1", "2", "3", "4", "5", "1", "2", "3", "4", "5", "1", "2"]
            faixas = [1, 2, 3, 4, 5, 1, 2, 3, 4, 5, 1, 2]

            for data_agendada, aula, faixa in zip(datas, aulas, faixas):
                database.criar_agendamento(
                    recurso_id=sala_tecnologia_id,
                    usuario_id=int(professora_ana["id"]),
                    data=data_agendada,
                    turno="MATUTINO",
                    aula=aula,
                    faixa_global=faixa,
                    turma="7 Ano A",
                    tema_aula="Pesquisa guiada",
                )

            resposta = relatorios_router.dashboard_relatorios_api(
                data_inicio="2026-05-01",
                data_fim="2026-05-05",
                usuario=self._usuario_gestor(),
            )

            textos_insights = {
                item["texto"] for item in resposta["dashboard_geral"]["insights"]
            }
            self.assertIn(
                (
                    "O volume de impressões no período está elevado. Recomenda-se acompanhar "
                    "o uso de papel e estimular alternativas digitais quando possível."
                ),
                textos_insights,
            )
            self.assertIn(
                "Há concentração significativa de impressões em poucos professores.",
                textos_insights,
            )
            self.assertIn(
                "A Sala de Tecnologia apresentou alta demanda no período.",
                textos_insights,
            )
            self.assertIn(
                "Existem recursos tecnológicos com baixa utilização no período.",
                textos_insights,
            )

    def test_dashboard_aplica_filtros_de_periodo(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, relatorios_router = _reload_modulos(db_path)
            database.criar_tabelas()
            database.seed_recursos_padrao()

            database.criar_usuario_se_nao_existir(
                nome="Ana Souza",
                email="ana@escola",
                senha_hash="hash-ana",
                perfil="professor",
                cargo="PROFESSOR",
            )
            professora_ana = database.buscar_usuario_por_email("ana@escola")
            recurso = database.listar_recursos_ativos()[0]

            database.criar_agendamento(
                recurso_id=int(recurso["id"]),
                usuario_id=int(professora_ana["id"]),
                data="2026-05-05",
                turno="MATUTINO",
                aula="1",
                faixa_global=1,
                turma="7 Ano A",
                tema_aula="Pesquisa guiada",
            )
            database.criar_agendamento(
                recurso_id=int(recurso["id"]),
                usuario_id=int(professora_ana["id"]),
                data="2026-05-25",
                turno="MATUTINO",
                aula="2",
                faixa_global=2,
                turma="7 Ano A",
                tema_aula="Revisao final",
            )

            resposta = relatorios_router.dashboard_relatorios_api(
                data_inicio="2026-05-01",
                data_fim="2026-05-10",
                usuario=self._usuario_gestor(),
            )

            self.assertEqual(resposta["recursos"]["resumo"]["total_reservas"], 1)
            self.assertEqual(
                resposta["recursos"]["ranking_recursos"][0]["total_reservas"],
                1,
            )

    def test_dashboard_rejeita_periodo_invalido(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, relatorios_router = _reload_modulos(db_path)
            database.criar_tabelas()

            with self.assertRaises(HTTPException) as ctx:
                relatorios_router.dashboard_relatorios_api(
                    data_inicio="2026-05-31",
                    data_fim="2026-05-01",
                    usuario=self._usuario_gestor(),
                )

            self.assertEqual(ctx.exception.status_code, 400)
            self.assertIn("Periodo invalido", str(ctx.exception.detail))

    def test_rota_relatorios_responde_html(self):
        os.environ["STATIC_ASSET_VERSION"] = "build-relatorios-http"
        for nome_modulo in ("routers.config", "routers.pages_router"):
            if nome_modulo in sys.modules:
                del sys.modules[nome_modulo]

        config = importlib.import_module("routers.config")
        pages_router = importlib.import_module("routers.pages_router")

        app = FastAPI()
        app.mount("/static", StaticFiles(directory=str(config.STATIC_DIR)), name="static")
        resposta = pages_router.relatorios_page(self._criar_request(app, "/relatorios"))
        html = resposta.body.decode("utf-8")

        self.assertEqual(resposta.status_code, 200)
        self.assertIn("text/html", resposta.headers.get("content-type", "").lower())
        self.assertIn("Relatorios gerenciais", html)
        self.assertIn("js/relatorios.js?v=build-relatorios-http", html)
        self.assertIn("/relatorios", [route.path for route in pages_router.router.routes])


if __name__ == "__main__":
    unittest.main()
