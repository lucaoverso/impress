import importlib
import os
import sys
import tempfile
import unittest

from fastapi import HTTPException


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

    def tearDown(self):
        if self._old_db_path is None:
            os.environ.pop("DB_PATH", None)
        else:
            os.environ["DB_PATH"] = self._old_db_path

    def _usuario_gestor(self) -> dict:
        return {
            "id": 1,
            "nome": "Administrador",
            "perfil": "admin",
            "cargo": "ADMIN",
        }

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
            self.assertGreaterEqual(len(resposta["recursos"]["ranking_recursos"]), 1)
            self.assertEqual(
                resposta["dashboard_geral"]["graficos"]["movimento_periodo"]["paginas"],
                [0] * 31,
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


if __name__ == "__main__":
    unittest.main()
