import importlib
import os
import sys
import tempfile
import types
import unittest
from fastapi import HTTPException


def _reload_modules(db_path: str):
    os.environ["DB_PATH"] = db_path
    os.environ["ENABLE_EMBEDDED_WORKER"] = "0"

    for module_name in (
        "services.auth_service",
        "services.pcpi_service",
        "auth",
        "pcpi_router",
        "ocorrencias_router",
        "database",
    ):
        if module_name in sys.modules:
            del sys.modules[module_name]

    if "pypdf" not in sys.modules:
        sys.modules["pypdf"] = types.SimpleNamespace(
            PdfReader=object,
            PdfWriter=object,
            Transformation=object,
        )

    database = importlib.import_module("database")
    pcpi_router = importlib.import_module("pcpi_router")
    models = importlib.import_module("models")
    return database, pcpi_router, models


class PcpiRegistroTest(unittest.TestCase):
    def setUp(self):
        self._old_db_path = os.environ.get("DB_PATH")
        self._old_embedded_worker = os.environ.get("ENABLE_EMBEDDED_WORKER")

    def tearDown(self):
        if self._old_db_path is None:
            os.environ.pop("DB_PATH", None)
        else:
            os.environ["DB_PATH"] = self._old_db_path

        if self._old_embedded_worker is None:
            os.environ.pop("ENABLE_EMBEDDED_WORKER", None)
        else:
            os.environ["ENABLE_EMBEDDED_WORKER"] = self._old_embedded_worker

    def test_router_pcpi_expoe_endpoints_minimos(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, pcpi_router, _models = _reload_modules(db_path)
            database.criar_tabelas()

            rotas = {route.path for route in pcpi_router.router.routes}
            self.assertIn("/pcpi/sugestoes", rotas)
            self.assertIn("/pcpi/registros-manuais", rotas)
            self.assertIn("/pcpi/texto", rotas)
            self.assertIn("/pcpi/texto/preview", rotas)

    def test_listar_sugestoes_pcpi_retorna_agendamentos_normalizados(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, pcpi_router, _models = _reload_modules(db_path)
            database.criar_tabelas()
            database.seed_recursos_padrao()

            database.criar_usuario_se_nao_existir(
                nome="Administrador",
                email="admin@escola",
                senha_hash=database.hash_senha("admin123"),
                senha_plana="admin123",
                perfil="admin",
                cargo="ADMIN",
            )

            professor_id = database.criar_professor(
                nome="Professor PCPI",
                email="pcpi.prof@escola.local",
                senha_hash=database.hash_senha("Senha@123"),
                data_nascimento="1990-10-01",
                aulas_semanais=12,
                turmas_quantidade=1,
                turmas=["Turma PCPI 7A"],
                disciplinas=["Matematica", "Fisica"],
            )
            database.criar_turma("Turma PCPI 7A", "MATUTINO", 32)

            recurso = next(
                item
                for item in database.listar_recursos_ativos()
                if "Notebook" in str(item.get("nome") or "")
            )

            database.criar_agendamento(
                recurso_id=int(recurso["id"]),
                usuario_id=professor_id,
                data="2026-04-03",
                turno="MATUTINO",
                aula="2",
                faixa_global=2,
                turma="Turma PCPI 7A",
                tema_aula="Exploracao de planilhas",
                observacao="Separar navegadores para pesquisa orientada.",
            )

            resposta = pcpi_router.listar_sugestoes_pcpi_api(
                data="2026-04-03",
                turno="MATUTINO",
                usuario={"id": 1, "cargo": "ADMIN"},
            )

            self.assertEqual(resposta["data"], "2026-04-03")
            self.assertEqual(resposta["turno"], "MATUTINO")
            self.assertEqual(resposta["resumo"]["total_agendamentos"], 1)
            self.assertEqual(len(resposta["itens"]), 1)

            item = resposta["itens"][0]
            self.assertEqual(item["professor_nome"], "Professor PCPI")
            self.assertEqual(item["turma"], "Turma PCPI 7A")
            self.assertEqual(item["tema_aula"], "Exploracao de planilhas")
            self.assertEqual(item["categoria_uso"], "tecnologia_educacional")
            self.assertEqual(item["componentes"], ["Matematica", "Fisica"])
            self.assertIn("Disponibilizacao e acompanhamento", resposta["texto_base"])

    def test_criar_e_listar_registros_manuais_pcpi(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, pcpi_router, models = _reload_modules(db_path)
            database.criar_tabelas()
            coordenador_id = database.criar_coordenador(
                nome="Coordenadora PCPI",
                email="coordenadora.pcpi@escola.local",
                senha_hash=database.hash_senha("Senha@123"),
                data_nascimento="1988-04-10",
            )

            payload = models.PcpiRegistroManualIn(
                data="2026-04-03",
                turno="MATUTINO",
                tipo_acao="planejamento",
                professor_nome="Equipe PCPI",
                componente="Tecnologia Educacional",
                turma="7A",
                descricao_curta="Planejamento das atividades e organizacao dos recursos.",
                observacoes="Definicao das demandas do turno e suporte ao agendamento.",
            )

            criado = pcpi_router.criar_registro_manual_pcpi_api(
                payload=payload,
                usuario={"id": coordenador_id, "cargo": "COORDENADOR"},
            )

            self.assertGreater(int(criado["id"]), 0)
            self.assertEqual(criado["tipo_acao"], "planejamento")
            self.assertEqual(criado["criado_por_usuario_id"], coordenador_id)
            self.assertEqual(criado["atualizado_por_usuario_id"], coordenador_id)

            listagem = pcpi_router.listar_registros_manuais_pcpi_api(
                data="2026-04-03",
                turno="MATUTINO",
                usuario={"id": coordenador_id, "cargo": "COORDENADOR"},
            )

            self.assertEqual(listagem["data"], "2026-04-03")
            self.assertEqual(listagem["turno"], "MATUTINO")
            self.assertEqual(listagem["total_registros"], 1)
            self.assertEqual(len(listagem["itens"]), 1)
            self.assertEqual(listagem["itens"][0]["descricao_curta"], payload.descricao_curta)

    def test_endpoint_texto_pcpi_combina_agendamentos_e_registros_manuais(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, pcpi_router, models = _reload_modules(db_path)
            database.criar_tabelas()
            database.seed_recursos_padrao()

            professor_id = database.criar_professor(
                nome="Professor Texto",
                email="texto.prof@escola.local",
                senha_hash=database.hash_senha("Senha@123"),
                data_nascimento="1991-03-11",
                aulas_semanais=10,
                turmas_quantidade=1,
                turmas=["8A"],
                disciplinas=["Ciencias"],
            )
            coordenador_id = database.criar_coordenador(
                nome="Coordenadora Texto",
                email="coordenadora.texto@escola.local",
                senha_hash=database.hash_senha("Senha@123"),
                data_nascimento="1987-09-01",
            )
            database.criar_turma("8A", "MATUTINO", 28)

            recurso = next(
                item
                for item in database.listar_recursos_ativos()
                if "Projetor" in str(item.get("nome") or "")
            )

            database.criar_agendamento(
                recurso_id=int(recurso["id"]),
                usuario_id=professor_id,
                data="2026-04-03",
                turno="MATUTINO",
                aula="3",
                faixa_global=3,
                turma="8A",
                tema_aula="Mostra de experimentos",
                observacao="Necessidade de apoio com projetor.",
            )

            payload = models.PcpiRegistroManualIn(
                data="2026-04-03",
                turno="MATUTINO",
                tipo_acao="planejamento",
                professor_nome="Equipe PCPI",
                componente="Tecnologia Educacional",
                turma="8A",
                descricao_curta="Ajuste do atendimento pedagógico do turno.",
                observacoes="Organizacao das demandas tecnicas e administrativas.",
            )
            pcpi_router.criar_registro_manual_pcpi_api(
                payload=payload,
                usuario={"id": coordenador_id, "cargo": "COORDENADOR"},
            )

            resposta = pcpi_router.gerar_texto_pcpi_api(
                data="2026-04-03",
                turno="MATUTINO",
                usuario={"id": coordenador_id, "cargo": "COORDENADOR"},
            )

            self.assertEqual(resposta["total_agendamentos"], 1)
            self.assertEqual(resposta["total_registros_manuais"], 1)
            self.assertIn("Entrega e recebimento de equipamentos tecnologicos", resposta["texto"])
            self.assertIn("Planejamento e organizacao", resposta["texto"])

    def test_preview_texto_pcpi_respeita_agendamentos_selecionados(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, pcpi_router, models = _reload_modules(db_path)
            database.criar_tabelas()
            database.seed_recursos_padrao()

            professor_id = database.criar_professor(
                nome="Professor Selecao",
                email="selecao.prof@escola.local",
                senha_hash=database.hash_senha("Senha@123"),
                data_nascimento="1992-08-20",
                aulas_semanais=8,
                turmas_quantidade=1,
                turmas=["9A"],
                disciplinas=["Biologia"],
            )

            database.criar_turma("9A", "MATUTINO", 30)

            recurso_notebook = next(
                item
                for item in database.listar_recursos_ativos()
                if "Notebook" in str(item.get("nome") or "")
            )
            recurso_projetor = next(
                item
                for item in database.listar_recursos_ativos()
                if "Projetor" in str(item.get("nome") or "")
            )

            agendamento_ste = database.criar_agendamento(
                recurso_id=int(recurso_notebook["id"]),
                usuario_id=professor_id,
                data="2026-04-03",
                turno="MATUTINO",
                aula="1",
                faixa_global=1,
                turma="9A",
                tema_aula="Pesquisa guiada",
                observacao="Apoio em atividade digital.",
            )
            database.criar_agendamento(
                recurso_id=int(recurso_projetor["id"]),
                usuario_id=professor_id,
                data="2026-04-03",
                turno="MATUTINO",
                aula="4",
                faixa_global=4,
                turma="9A",
                tema_aula="Exibicao de video",
                observacao="Uso de recurso audiovisual.",
            )

            payload = models.PcpiTextoPreviewIn(
                data="2026-04-03",
                turno="MATUTINO",
                agendamento_ids=[agendamento_ste],
            )

            resposta = pcpi_router.gerar_texto_pcpi_preview_api(
                payload=payload,
                usuario={"id": 1, "cargo": "ADMIN"},
            )

            self.assertEqual(resposta["total_agendamentos"], 1)
            self.assertIn("Disponibilizacao e acompanhamento", resposta["texto"])
            self.assertNotIn("Entrega e recebimento de equipamentos tecnologicos", resposta["texto"])

    def test_criar_registro_manual_pcpi_valida_turno_invalido(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, pcpi_router, models = _reload_modules(db_path)
            database.criar_tabelas()

            payload = models.PcpiRegistroManualIn(
                data="2026-04-03",
                turno="NOITE",
                tipo_acao="planejamento",
                descricao_curta="Planejamento do turno.",
            )

            with self.assertRaises(HTTPException) as contexto:
                pcpi_router.criar_registro_manual_pcpi_api(
                    payload=payload,
                    usuario={"id": 1, "cargo": "ADMIN"},
                )

            self.assertEqual(contexto.exception.status_code, 400)
            self.assertIn("Turno invalido", str(contexto.exception.detail))


if __name__ == "__main__":
    unittest.main()
