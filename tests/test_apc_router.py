import importlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException, UploadFile
from starlette.datastructures import Headers


def _reload_modules(db_path: str, apc_dir: str):
    os.environ["DB_PATH"] = db_path
    os.environ["APC_DIR"] = apc_dir
    os.environ["ENABLE_EMBEDDED_WORKER"] = "0"

    for module_name in (
        "services.auth_service",
        "services.horario_escolar_service",
        "services.apc_service",
        "auth",
        "database",
        "models",
        "routers.config",
        "routers.apc_router",
    ):
        if module_name in sys.modules:
            del sys.modules[module_name]

    database = importlib.import_module("database")
    models = importlib.import_module("models")
    apc_router = importlib.import_module("routers.apc_router")
    return database, models, apc_router


class ApcRouterTest(unittest.TestCase):
    def setUp(self):
        self._old_db_path = os.environ.get("DB_PATH")
        self._old_apc_dir = os.environ.get("APC_DIR")
        self._old_embedded_worker = os.environ.get("ENABLE_EMBEDDED_WORKER")

    def tearDown(self):
        if self._old_db_path is None:
            os.environ.pop("DB_PATH", None)
        else:
            os.environ["DB_PATH"] = self._old_db_path

        if self._old_apc_dir is None:
            os.environ.pop("APC_DIR", None)
        else:
            os.environ["APC_DIR"] = self._old_apc_dir

        if self._old_embedded_worker is None:
            os.environ.pop("ENABLE_EMBEDDED_WORKER", None)
        else:
            os.environ["ENABLE_EMBEDDED_WORKER"] = self._old_embedded_worker

    def _usuario_coord(self, usuario_id: int = 1) -> dict:
        return {"id": usuario_id, "nome": "Coord", "cargo": "COORDENADOR"}

    def _usuario_professor(self, usuario_id: int) -> dict:
        return {"id": usuario_id, "nome": "Professor", "cargo": "PROFESSOR"}

    def _usuario_professor_coordenacao(self, usuario_id: int) -> dict:
        return {
            "id": usuario_id,
            "nome": "Professor Coordenador",
            "cargo": "PROFESSOR",
            "acesso_coordenacao": 1,
        }

    def test_fluxo_apc_filtra_professor_por_horario_e_registra_envio(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            apc_dir = os.path.join(tmp_dir, "apc")
            database, models, apc_router = _reload_modules(db_path, apc_dir)
            database.criar_tabelas()

            turma_id = int(database.criar_turma("9A", "MATUTINO", 30))
            disciplina_id = int(database.criar_disciplina("Matematica", 5))
            professor_id = int(
                database.criar_professor(
                    nome="Professor APC",
                    email="apc@escola.local",
                    senha_hash=database.hash_senha("Senha@123"),
                    data_nascimento="1989-02-15",
                    aulas_semanais=12,
                    turmas_quantidade=1,
                    turmas=["9A"],
                    disciplinas=["Matematica"],
                )
            )

            database.criar_ou_atualizar_turma_disciplina(
                turma_id=turma_id,
                disciplina_id=disciplina_id,
                carga_horaria=4,
                professor_usuario_id=professor_id,
            )
            database.criar_horario_escolar(
                ano_letivo=2031,
                turma_id=turma_id,
                disciplina_id=disciplina_id,
                professor_usuario_id=professor_id,
                dia_semana="QUINTA",
                aula_numero=2,
            )

            contexto = apc_router.obter_contexto_apc_api(usuario=self._usuario_coord())
            self.assertIn("anos_letivos", contexto)
            self.assertGreater(len(contexto["publicos_alvo"]), 0)
            self.assertTrue(contexto["usuario"]["pode_gerir"])

            quinta = apc_router.criar_periodo_apc_api(
                payload=models.ApcPeriodoIn(
                    ano_letivo=2031,
                    data_referencia="2031-05-08",
                    prazo_envio="2031-05-08T23:59",
                    titulo="Atividade pedagogica semanal",
                    observacao="Entrega semanal",
                    publico_alvo="HORARIO_DIA",
                ),
                usuario=self._usuario_coord(),
            )
            sexta = apc_router.criar_periodo_apc_api(
                payload=models.ApcPeriodoIn(
                    ano_letivo=2031,
                    data_referencia="2031-05-09",
                    prazo_envio="2031-05-09T23:59",
                    titulo="Planejamento semanal",
                    observacao="Nao deve aparecer para este professor",
                    publico_alvo="HORARIO_DIA",
                ),
                usuario=self._usuario_coord(),
            )

            calendario_coord = apc_router.listar_calendario_apc_api(
                mes="2031-05",
                ano_letivo=2031,
                usuario=self._usuario_coord(),
            )
            self.assertEqual(len(calendario_coord["periodos"]), 2)

            calendario_professor = apc_router.listar_calendario_apc_api(
                mes="2031-05",
                ano_letivo=2031,
                usuario=self._usuario_professor(professor_id),
            )
            self.assertEqual(len(calendario_professor["periodos"]), 1)
            self.assertEqual(calendario_professor["periodos"][0]["data_referencia"], "2031-05-08")
            self.assertFalse(calendario_professor["periodos"][0]["enviado"])

            detalhe_gestao = apc_router.obter_periodo_apc_api(
                periodo_id=int(quinta["id"]),
                usuario=self._usuario_coord(),
            )
            self.assertEqual(int(detalhe_gestao["total_elegiveis"]), 1)
            self.assertEqual(int(detalhe_gestao["total_pendentes"]), 1)
            self.assertEqual(len(detalhe_gestao["itens"]), 1)

            upload = UploadFile(
                io.BytesIO(b"arquivo apc"),
                filename="atividade.pdf",
                headers=Headers({"content-type": "application/pdf"}),
            )
            envio = apc_router.enviar_arquivo_apc_api(
                periodo_id=int(quinta["id"]),
                arquivo=upload,
                usuario=self._usuario_professor(professor_id),
            )
            self.assertEqual(int(envio["periodo_id"]), int(quinta["id"]))
            self.assertEqual(int(envio["professor_id"]), professor_id)
            self.assertEqual(envio["arquivo_nome_cliente"], "atividade.pdf")
            self.assertEqual(
                envio["arquivo_nome_original"],
                "Atividade pedagogica semanal - Professor APC - 2031-05-08.pdf",
            )
            self.assertTrue(Path(str(envio["arquivo_path"])).exists())

            revisado = apc_router.revisar_envio_apc_api(
                envio_id=int(envio["id"]),
                payload=importlib.import_module(
                    "modules.apc_review.schemas"
                ).ApcReviewUpdateIn(
                    status="AJUSTE_SOLICITADO",
                    mensagem="Inclua a identificacao da turma na primeira pagina.",
                ),
                usuario=self._usuario_coord(),
            )
            self.assertEqual(revisado["review_status"], "AJUSTE_SOLICITADO")
            self.assertEqual(
                revisado["review_message"],
                "Inclua a identificacao da turma na primeira pagina.",
            )

            detalhe_professor = apc_router.obter_periodo_apc_api(
                periodo_id=int(quinta["id"]),
                usuario=self._usuario_professor(professor_id),
            )
            self.assertIsNotNone(detalhe_professor["envio"])
            self.assertEqual(detalhe_professor["envio"]["arquivo_nome_cliente"], "atividade.pdf")
            self.assertEqual(
                detalhe_professor["envio"]["review_status"],
                "AJUSTE_SOLICITADO",
            )
            self.assertEqual(int(detalhe_professor["total_ajustes"]), 1)

            novo_upload = UploadFile(
                io.BytesIO(b"arquivo corrigido"),
                filename="atividade-corrigida.pdf",
                headers=Headers({"content-type": "application/pdf"}),
            )
            reenviado = apc_router.enviar_arquivo_apc_api(
                periodo_id=int(quinta["id"]),
                turma_id=turma_id,
                disciplina_id=disciplina_id,
                arquivo=novo_upload,
                usuario=self._usuario_professor(professor_id),
            )
            self.assertEqual(reenviado["review_status"], "PENDENTE")
            self.assertEqual(reenviado["review_message"], "")
            self.assertIsNone(reenviado["reviewed_by_user_id"])

            aprovado = apc_router.revisar_envio_apc_api(
                envio_id=int(envio["id"]),
                payload=importlib.import_module(
                    "modules.apc_review.schemas"
                ).ApcReviewUpdateIn(
                    status="APROVADO",
                    mensagem="Material conferido.",
                ),
                usuario=self._usuario_coord(),
            )
            self.assertEqual(aprovado["review_status"], "APROVADO")

            impresso = apc_router.revisar_envio_apc_api(
                envio_id=int(envio["id"]),
                payload=importlib.import_module(
                    "modules.apc_review.schemas"
                ).ApcReviewUpdateIn(
                    status="IMPRESSO",
                    mensagem="Prova impressa pela coordenacao.",
                ),
                usuario=self._usuario_coord(),
            )
            self.assertEqual(impresso["review_status"], "IMPRESSO")

            with self.assertRaises(HTTPException) as review_ctx:
                apc_router.revisar_envio_apc_api(
                    envio_id=int(envio["id"]),
                    payload=importlib.import_module(
                        "modules.apc_review.schemas"
                    ).ApcReviewUpdateIn(
                        status="APROVADO",
                        mensagem="",
                    ),
                    usuario=self._usuario_professor(professor_id),
                )
            self.assertEqual(int(review_ctx.exception.status_code), 403)
            self.assertEqual(int(detalhe_professor["total_aulas"]), 1)

            detalhe_gestao_atualizado = apc_router.obter_periodo_apc_api(
                periodo_id=int(quinta["id"]),
                usuario=self._usuario_coord(),
            )
            self.assertEqual(int(detalhe_gestao_atualizado["total_enviados"]), 1)
            self.assertEqual(int(detalhe_gestao_atualizado["total_pendentes"]), 0)
            self.assertEqual(int(detalhe_gestao_atualizado["total_impressos"]), 1)
            self.assertEqual(
                int(detalhe_gestao_atualizado["itens"][0]["envio"]["id"]),
                int(envio["id"]),
            )

            resposta_arquivo = apc_router.baixar_arquivo_apc_api(
                envio_id=int(envio["id"]),
                usuario=self._usuario_professor(professor_id),
            )
            self.assertTrue(str(resposta_arquivo.path).endswith(".pdf"))

            self.assertEqual(int(sexta["id"]) > 0, True)

    def test_periodo_generico_pode_ser_liberado_para_todos_os_professores(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            apc_dir = os.path.join(tmp_dir, "apc")
            database, models, apc_router = _reload_modules(db_path, apc_dir)
            database.criar_tabelas()

            turma_id = int(database.criar_turma("1EM", "MATUTINO", 28))
            disciplina_id = int(database.criar_disciplina("Historia", 2))
            professor_horario_id = int(
                database.criar_professor(
                    nome="Professor Horario",
                    email="horario@escola.local",
                    senha_hash=database.hash_senha("Senha@123"),
                    data_nascimento="1986-01-10",
                    aulas_semanais=10,
                    turmas_quantidade=1,
                    turmas=["1EM"],
                    disciplinas=["Historia"],
                )
            )
            professor_geral_id = int(
                database.criar_professor(
                    nome="Professor Geral",
                    email="geral@escola.local",
                    senha_hash=database.hash_senha("Senha@123"),
                    data_nascimento="1985-05-11",
                    aulas_semanais=10,
                    turmas_quantidade=0,
                    turmas=[],
                    disciplinas=[],
                )
            )

            database.criar_atribuicao_docente(professor_horario_id, turma_id, disciplina_id)
            database.criar_horario_escolar(
                ano_letivo=2032,
                turma_id=turma_id,
                disciplina_id=disciplina_id,
                professor_usuario_id=professor_horario_id,
                dia_semana="TERCA",
                aula_numero=2,
            )

            entrega_geral = apc_router.criar_periodo_apc_api(
                payload=models.ApcPeriodoIn(
                    ano_letivo=2032,
                    data_referencia="2032-08-03",
                    prazo_envio="2032-08-03T23:59",
                    titulo="Prova bimestral",
                    observacao="Entrega para todos os professores.",
                    publico_alvo="TODOS_PROFESSORES",
                ),
                usuario=self._usuario_coord(),
            )
            entrega_horario = apc_router.criar_periodo_apc_api(
                payload=models.ApcPeriodoIn(
                    ano_letivo=2032,
                    data_referencia="2032-08-03",
                    prazo_envio="2032-08-03T23:59",
                    titulo="Atividade da turma",
                    observacao="Entrega vinculada ao horario.",
                    publico_alvo="HORARIO_DIA",
                ),
                usuario=self._usuario_coord(),
            )

            calendario_horario = apc_router.listar_calendario_apc_api(
                mes="2032-08",
                ano_letivo=2032,
                usuario=self._usuario_professor(professor_horario_id),
            )
            self.assertEqual(len(calendario_horario["periodos"]), 2)

            calendario_geral = apc_router.listar_calendario_apc_api(
                mes="2032-08",
                ano_letivo=2032,
                usuario=self._usuario_professor(professor_geral_id),
            )
            self.assertEqual(len(calendario_geral["periodos"]), 1)
            self.assertEqual(calendario_geral["periodos"][0]["titulo"], "Prova bimestral")

            detalhe_geral = apc_router.obter_periodo_apc_api(
                periodo_id=int(entrega_geral["id"]),
                usuario=self._usuario_coord(),
            )
            self.assertEqual(int(detalhe_geral["total_elegiveis"]), 2)

            detalhe_professor_geral = apc_router.obter_periodo_apc_api(
                periodo_id=int(entrega_geral["id"]),
                usuario=self._usuario_professor(professor_geral_id),
            )
            self.assertEqual(
                detalhe_professor_geral["periodo"]["publico_alvo"],
                "TODOS_PROFESSORES",
            )

            with self.assertRaises(HTTPException) as ctx:
                apc_router.obter_periodo_apc_api(
                    periodo_id=int(entrega_horario["id"]),
                    usuario=self._usuario_professor(professor_geral_id),
                )

            self.assertEqual(int(ctx.exception.status_code), 403)

    def test_periodo_com_professores_selecionados_exibe_apenas_destinatarios_configurados(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            apc_dir = os.path.join(tmp_dir, "apc")
            database, models, apc_router = _reload_modules(db_path, apc_dir)
            database.criar_tabelas()

            turma_8a_id = int(database.criar_turma("8A", "MATUTINO", 30))
            turma_9b_id = int(database.criar_turma("9B", "MATUTINO", 29))
            disciplina_matematica_id = int(database.criar_disciplina("Matematica", 5))
            disciplina_geometria_id = int(database.criar_disciplina("Geometria", 3))
            disciplina_historia_id = int(database.criar_disciplina("Historia", 2))

            paulo_id = int(
                database.criar_professor(
                    nome="Paulo",
                    email="paulo@escola.local",
                    senha_hash=database.hash_senha("Senha@123"),
                    data_nascimento="1987-04-10",
                    aulas_semanais=18,
                    turmas_quantidade=2,
                    turmas=["8A", "9B"],
                    disciplinas=["Matematica", "Geometria"],
                )
            )
            maria_id = int(
                database.criar_professor(
                    nome="Maria",
                    email="maria@escola.local",
                    senha_hash=database.hash_senha("Senha@123"),
                    data_nascimento="1986-06-12",
                    aulas_semanais=10,
                    turmas_quantidade=1,
                    turmas=["8A"],
                    disciplinas=["Historia"],
                )
            )

            database.criar_ou_atualizar_turma_disciplina(
                turma_id=turma_8a_id,
                disciplina_id=disciplina_matematica_id,
                carga_horaria=5,
                professor_usuario_id=paulo_id,
            )
            database.criar_ou_atualizar_turma_disciplina(
                turma_id=turma_9b_id,
                disciplina_id=disciplina_geometria_id,
                carga_horaria=3,
                professor_usuario_id=paulo_id,
            )
            database.criar_ou_atualizar_turma_disciplina(
                turma_id=turma_8a_id,
                disciplina_id=disciplina_historia_id,
                carga_horaria=2,
                professor_usuario_id=maria_id,
            )

            periodo = apc_router.criar_periodo_apc_api(
                payload=models.ApcPeriodoIn(
                    ano_letivo=2033,
                    data_referencia="2033-09-15",
                    prazo_envio="2033-09-16T18:00",
                    titulo="Prova",
                    observacao="Somente os componentes selecionados devem anexar.",
                    publico_alvo="PROFESSORES_SELECIONADOS",
                    destinatarios=[
                        models.ApcDestinatarioIn(
                            professor_id=paulo_id,
                            turma_id=turma_8a_id,
                            disciplina_id=disciplina_matematica_id,
                        ),
                        models.ApcDestinatarioIn(
                            professor_id=paulo_id,
                            turma_id=turma_9b_id,
                            disciplina_id=disciplina_geometria_id,
                        ),
                    ],
                ),
                usuario=self._usuario_coord(),
            )

            calendario_paulo = apc_router.listar_calendario_apc_api(
                mes="2033-09",
                ano_letivo=2033,
                usuario=self._usuario_professor(paulo_id),
            )
            self.assertEqual(len(calendario_paulo["periodos"]), 1)

            calendario_maria = apc_router.listar_calendario_apc_api(
                mes="2033-09",
                ano_letivo=2033,
                usuario=self._usuario_professor(maria_id),
            )
            self.assertEqual(len(calendario_maria["periodos"]), 0)

            detalhe_gestao = apc_router.obter_periodo_apc_api(
                periodo_id=int(periodo["id"]),
                usuario=self._usuario_coord(),
            )
            self.assertEqual(detalhe_gestao["periodo"]["publico_alvo"], "PROFESSORES_SELECIONADOS")
            self.assertEqual(int(detalhe_gestao["total_elegiveis"]), 2)
            self.assertEqual(len(detalhe_gestao["destinatarios_configurados"]), 2)

            detalhe_paulo = apc_router.obter_periodo_apc_api(
                periodo_id=int(periodo["id"]),
                usuario=self._usuario_professor(paulo_id),
            )
            self.assertEqual(int(detalhe_paulo["total_entregas"]), 2)
            self.assertEqual(
                {item["disciplina_nome"] for item in detalhe_paulo["itens"]},
                {"Matematica", "Geometria"},
            )

            upload = UploadFile(
                io.BytesIO(b"prova matematica"),
                filename="prova-matematica.pdf",
                headers=Headers({"content-type": "application/pdf"}),
            )
            envio = apc_router.enviar_arquivo_apc_api(
                periodo_id=int(periodo["id"]),
                turma_id=turma_8a_id,
                disciplina_id=disciplina_matematica_id,
                arquivo=upload,
                usuario=self._usuario_professor(paulo_id),
            )
            self.assertEqual(int(envio["professor_id"]), paulo_id)
            self.assertEqual(int(envio["turma_id"]), turma_8a_id)
            self.assertEqual(int(envio["disciplina_id"]), disciplina_matematica_id)

            with self.assertRaises(HTTPException) as ctx:
                apc_router.obter_periodo_apc_api(
                    periodo_id=int(periodo["id"]),
                    usuario=self._usuario_professor(maria_id),
                )

            self.assertEqual(int(ctx.exception.status_code), 403)

    def test_edicao_exibe_e_remove_destinatario_sem_vinculo_atual(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            apc_dir = os.path.join(tmp_dir, "apc")
            database, models, apc_router = _reload_modules(db_path, apc_dir)
            database.criar_tabelas()

            turma_id = int(database.criar_turma("8A", "MATUTINO", 30))
            matematica_id = int(database.criar_disciplina("Matematica", 5))
            historia_id = int(database.criar_disciplina("Historia", 3))
            antiga_id = int(
                database.criar_professor(
                    nome="Professora Antiga",
                    email="antiga@escola.local",
                    senha_hash=database.hash_senha("Senha@123"),
                    data_nascimento="1987-04-10",
                    aulas_semanais=10,
                    turmas_quantidade=1,
                    turmas=["8A"],
                    disciplinas=["Matematica"],
                )
            )
            atual_id = int(
                database.criar_professor(
                    nome="Professora Atual",
                    email="atual@escola.local",
                    senha_hash=database.hash_senha("Senha@123"),
                    data_nascimento="1988-05-11",
                    aulas_semanais=10,
                    turmas_quantidade=1,
                    turmas=["8A"],
                    disciplinas=["Historia"],
                )
            )

            vinculo_antigo = database.criar_ou_atualizar_turma_disciplina(
                turma_id=turma_id,
                disciplina_id=matematica_id,
                carga_horaria=5,
                professor_usuario_id=antiga_id,
            )
            database.criar_ou_atualizar_turma_disciplina(
                turma_id=turma_id,
                disciplina_id=historia_id,
                carga_horaria=3,
                professor_usuario_id=atual_id,
            )

            periodo = apc_router.criar_periodo_apc_api(
                payload=models.ApcPeriodoIn(
                    ano_letivo=2033,
                    data_referencia="2033-09-20",
                    prazo_envio="2033-09-21T18:00",
                    titulo="Documentos",
                    publico_alvo="PROFESSORES_SELECIONADOS",
                    destinatarios=[
                        models.ApcDestinatarioIn(
                            professor_id=antiga_id,
                            turma_id=turma_id,
                            disciplina_id=matematica_id,
                        ),
                        models.ApcDestinatarioIn(
                            professor_id=atual_id,
                            turma_id=turma_id,
                            disciplina_id=historia_id,
                        ),
                    ],
                ),
                usuario=self._usuario_coord(),
            )

            database.atualizar_turma_disciplina(
                int(vinculo_antigo["id"]),
                carga_horaria=5,
                professor_usuario_id=None,
            )

            opcoes = apc_router.listar_opcoes_destinatarios_apc_api(
                ano_letivo=2033,
                periodo_id=int(periodo["id"]),
                usuario=self._usuario_coord(),
            )
            itens = [
                item
                for professor in opcoes["professores"]
                for item in professor["destinatarios"]
            ]
            antigo = next(
                item
                for item in itens
                if int(item["professor_id"]) == antiga_id
            )
            self.assertFalse(antigo["vinculo_ativo"])

            apc_router.atualizar_periodo_apc_api(
                periodo_id=int(periodo["id"]),
                payload=models.ApcPeriodoUpdateIn(
                    ano_letivo=2033,
                    data_referencia="2033-09-20",
                    prazo_envio="2033-09-21T18:00",
                    titulo="Documentos",
                    publico_alvo="PROFESSORES_SELECIONADOS",
                    destinatarios=[
                        models.ApcDestinatarioIn(
                            professor_id=atual_id,
                            turma_id=turma_id,
                            disciplina_id=historia_id,
                        )
                    ],
                ),
                usuario=self._usuario_coord(),
            )

            destinatarios = database.listar_apc_destinatarios(
                periodo_id=int(periodo["id"])
            )
            self.assertEqual(len(destinatarios), 1)
            self.assertEqual(int(destinatarios[0]["professor_id"]), atual_id)

    def test_central_filtra_entregas_por_flag_da_disciplina_e_tipo_da_solicitacao(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            apc_dir = os.path.join(tmp_dir, "apc")
            database, models, apc_router = _reload_modules(db_path, apc_dir)
            database.criar_tabelas()

            turma_id = int(database.criar_turma("8C", "MATUTINO", 31))
            disciplina_apc_id = int(
                database.criar_disciplina(
                    "Projeto APC",
                    2,
                    tem_apc=True,
                )
            )
            disciplina_prova_id = int(
                database.criar_disciplina(
                    "Projeto Prova",
                    2,
                    tem_prova_bimestral=True,
                )
            )
            professor_id = int(
                database.criar_professor(
                    nome="Professor Filtro",
                    email="filtro@escola.local",
                    senha_hash=database.hash_senha("Senha@123"),
                    data_nascimento="1988-10-03",
                    aulas_semanais=12,
                    turmas_quantidade=1,
                    turmas=["8C"],
                    disciplinas=["Projeto APC", "Projeto Prova"],
                )
            )

            database.criar_ou_atualizar_turma_disciplina(
                turma_id=turma_id,
                disciplina_id=disciplina_apc_id,
                carga_horaria=2,
                professor_usuario_id=professor_id,
            )
            database.criar_ou_atualizar_turma_disciplina(
                turma_id=turma_id,
                disciplina_id=disciplina_prova_id,
                carga_horaria=2,
                professor_usuario_id=professor_id,
            )
            database.criar_horario_escolar(
                ano_letivo=2032,
                turma_id=turma_id,
                disciplina_id=disciplina_apc_id,
                professor_usuario_id=professor_id,
                dia_semana="SEGUNDA",
                aula_numero=1,
            )
            database.criar_horario_escolar(
                ano_letivo=2032,
                turma_id=turma_id,
                disciplina_id=disciplina_prova_id,
                professor_usuario_id=professor_id,
                dia_semana="SEGUNDA",
                aula_numero=2,
            )

            periodo_apc = apc_router.criar_periodo_apc_api(
                payload=models.ApcPeriodoIn(
                    ano_letivo=2032,
                    data_referencia="2032-08-02",
                    prazo_envio="2032-08-02T23:59",
                    titulo="Entrega de APC",
                    observacao="Somente disciplinas marcadas com APC.",
                    publico_alvo="HORARIO_DIA",
                    tipo_entrega="APC",
                ),
                usuario=self._usuario_coord(),
            )
            periodo_prova = apc_router.criar_periodo_apc_api(
                payload=models.ApcPeriodoIn(
                    ano_letivo=2032,
                    data_referencia="2032-08-02",
                    prazo_envio="2032-08-02T23:59",
                    titulo="Entrega de prova",
                    observacao="Somente disciplinas com prova bimestral.",
                    publico_alvo="HORARIO_DIA",
                    tipo_entrega="PROVA_BIMESTRAL",
                ),
                usuario=self._usuario_coord(),
            )

            detalhe_apc = apc_router.obter_periodo_apc_api(
                periodo_id=int(periodo_apc["id"]),
                usuario=self._usuario_professor(professor_id),
            )
            self.assertEqual(detalhe_apc["periodo"]["tipo_entrega"], "APC")
            self.assertEqual(int(detalhe_apc["total_entregas"]), 1)
            self.assertEqual(len(detalhe_apc["itens"]), 1)
            self.assertEqual(int(detalhe_apc["itens"][0]["disciplina_id"]), disciplina_apc_id)

            detalhe_prova = apc_router.obter_periodo_apc_api(
                periodo_id=int(periodo_prova["id"]),
                usuario=self._usuario_professor(professor_id),
            )
            self.assertEqual(detalhe_prova["periodo"]["tipo_entrega"], "PROVA_BIMESTRAL")
            self.assertEqual(int(detalhe_prova["total_entregas"]), 1)
            self.assertEqual(len(detalhe_prova["itens"]), 1)
            self.assertEqual(
                int(detalhe_prova["itens"][0]["disciplina_id"]),
                disciplina_prova_id,
            )

            detalhe_gestao_apc = apc_router.obter_periodo_apc_api(
                periodo_id=int(periodo_apc["id"]),
                usuario=self._usuario_coord(),
            )
            self.assertEqual(int(detalhe_gestao_apc["total_elegiveis"]), 1)

    def test_professor_envia_arquivos_separados_por_disciplina_no_mesmo_dia(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            apc_dir = os.path.join(tmp_dir, "apc")
            database, models, apc_router = _reload_modules(db_path, apc_dir)
            database.criar_tabelas()

            turma_id = int(database.criar_turma("7A", "MATUTINO", 32))
            disciplina_matematica_id = int(database.criar_disciplina("Matematica", 4))
            disciplina_ra_id = int(database.criar_disciplina("R.A Matematica", 2))
            professor_id = int(
                database.criar_professor(
                    nome="Professor Multiplas Disciplinas",
                    email="multiplas@escola.local",
                    senha_hash=database.hash_senha("Senha@123"),
                    data_nascimento="1987-07-21",
                    aulas_semanais=14,
                    turmas_quantidade=1,
                    turmas=["7A"],
                    disciplinas=["Matematica", "R.A Matematica"],
                )
            )

            database.criar_ou_atualizar_turma_disciplina(
                turma_id=turma_id,
                disciplina_id=disciplina_matematica_id,
                carga_horaria=4,
                professor_usuario_id=professor_id,
            )
            database.criar_ou_atualizar_turma_disciplina(
                turma_id=turma_id,
                disciplina_id=disciplina_ra_id,
                carga_horaria=2,
                professor_usuario_id=professor_id,
            )
            database.criar_horario_escolar(
                ano_letivo=2033,
                turma_id=turma_id,
                disciplina_id=disciplina_matematica_id,
                professor_usuario_id=professor_id,
                dia_semana="QUINTA",
                aula_numero=2,
            )
            database.criar_horario_escolar(
                ano_letivo=2033,
                turma_id=turma_id,
                disciplina_id=disciplina_ra_id,
                professor_usuario_id=professor_id,
                dia_semana="QUINTA",
                aula_numero=3,
            )

            periodo = apc_router.criar_periodo_apc_api(
                payload=models.ApcPeriodoIn(
                    ano_letivo=2033,
                    data_referencia="2033-04-14",
                    prazo_envio="2033-04-14T23:59",
                    titulo="Atividades da quinta",
                    observacao="Uma entrega por disciplina.",
                    publico_alvo="HORARIO_DIA",
                ),
                usuario=self._usuario_coord(),
            )

            detalhe_professor = apc_router.obter_periodo_apc_api(
                periodo_id=int(periodo["id"]),
                usuario=self._usuario_professor(professor_id),
            )
            self.assertEqual(int(detalhe_professor["total_entregas"]), 2)
            self.assertEqual(int(detalhe_professor["total_pendentes"]), 2)
            self.assertEqual(len(detalhe_professor["itens"]), 2)

            item_matematica = next(
                item for item in detalhe_professor["itens"]
                if int(item["disciplina_id"]) == disciplina_matematica_id
            )
            item_ra = next(
                item for item in detalhe_professor["itens"]
                if int(item["disciplina_id"]) == disciplina_ra_id
            )

            envio_matematica = apc_router.enviar_arquivo_apc_api(
                periodo_id=int(periodo["id"]),
                turma_id=int(item_matematica["turma_id"]),
                disciplina_id=int(item_matematica["disciplina_id"]),
                arquivo=UploadFile(
                    io.BytesIO(b"matematica"),
                    filename="matematica.pdf",
                    headers=Headers({"content-type": "application/pdf"}),
                ),
                usuario=self._usuario_professor(professor_id),
            )
            self.assertEqual(int(envio_matematica["disciplina_id"]), disciplina_matematica_id)

            detalhe_parcial = apc_router.obter_periodo_apc_api(
                periodo_id=int(periodo["id"]),
                usuario=self._usuario_professor(professor_id),
            )
            self.assertEqual(int(detalhe_parcial["total_enviadas"]), 1)
            self.assertEqual(int(detalhe_parcial["total_pendentes"]), 1)

            envio_ra = apc_router.enviar_arquivo_apc_api(
                periodo_id=int(periodo["id"]),
                turma_id=int(item_ra["turma_id"]),
                disciplina_id=int(item_ra["disciplina_id"]),
                arquivo=UploadFile(
                    io.BytesIO(b"ra matematica"),
                    filename="ra-matematica.pdf",
                    headers=Headers({"content-type": "application/pdf"}),
                ),
                usuario=self._usuario_professor(professor_id),
            )
            self.assertEqual(int(envio_ra["disciplina_id"]), disciplina_ra_id)

            detalhe_final = apc_router.obter_periodo_apc_api(
                periodo_id=int(periodo["id"]),
                usuario=self._usuario_professor(professor_id),
            )
            self.assertEqual(int(detalhe_final["total_enviadas"]), 2)
            self.assertEqual(int(detalhe_final["total_pendentes"]), 0)

            detalhe_gestao = apc_router.obter_periodo_apc_api(
                periodo_id=int(periodo["id"]),
                usuario=self._usuario_coord(),
            )
            self.assertEqual(int(detalhe_gestao["total_elegiveis"]), 2)
            self.assertEqual(int(detalhe_gestao["total_enviados"]), 2)
            self.assertEqual(len(detalhe_gestao["itens"]), 2)

    def test_professor_com_acesso_coordenacao_alterna_entre_visoes_docente_e_gestao(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            apc_dir = os.path.join(tmp_dir, "apc")
            database, models, apc_router = _reload_modules(db_path, apc_dir)
            database.criar_tabelas()

            turma_a_id = int(database.criar_turma("8A", "MATUTINO", 30))
            turma_b_id = int(database.criar_turma("8B", "MATUTINO", 31))
            disciplina_a_id = int(database.criar_disciplina("Matematica", 4))
            disciplina_b_id = int(database.criar_disciplina("Ciencias", 3))

            professor_coord_id = int(
                database.criar_professor(
                    nome="Professor Coordenador",
                    email="coord-prof@escola.local",
                    senha_hash=database.hash_senha("Senha@123"),
                    data_nascimento="1984-04-18",
                    aulas_semanais=12,
                    turmas_quantidade=1,
                    turmas=["8A"],
                    disciplinas=["Matematica"],
                )
            )
            professor_outro_id = int(
                database.criar_professor(
                    nome="Professor Outro",
                    email="outro@escola.local",
                    senha_hash=database.hash_senha("Senha@123"),
                    data_nascimento="1986-03-09",
                    aulas_semanais=10,
                    turmas_quantidade=1,
                    turmas=["8B"],
                    disciplinas=["Ciencias"],
                )
            )

            database.criar_ou_atualizar_turma_disciplina(
                turma_id=turma_a_id,
                disciplina_id=disciplina_a_id,
                carga_horaria=4,
                professor_usuario_id=professor_coord_id,
            )
            database.criar_ou_atualizar_turma_disciplina(
                turma_id=turma_b_id,
                disciplina_id=disciplina_b_id,
                carga_horaria=3,
                professor_usuario_id=professor_outro_id,
            )
            database.criar_horario_escolar(
                ano_letivo=2034,
                turma_id=turma_a_id,
                disciplina_id=disciplina_a_id,
                professor_usuario_id=professor_coord_id,
                dia_semana="SEGUNDA",
                aula_numero=1,
            )
            database.criar_horario_escolar(
                ano_letivo=2034,
                turma_id=turma_b_id,
                disciplina_id=disciplina_b_id,
                professor_usuario_id=professor_outro_id,
                dia_semana="SEGUNDA",
                aula_numero=2,
            )

            periodo = apc_router.criar_periodo_apc_api(
                payload=models.ApcPeriodoIn(
                    ano_letivo=2034,
                    data_referencia="2034-03-06",
                    prazo_envio="2034-03-06T23:59",
                    titulo="Entrega semanal",
                    observacao="Visoes separadas para professor coordenador.",
                    publico_alvo="HORARIO_DIA",
                ),
                usuario=self._usuario_coord(),
            )

            usuario_hibrido = self._usuario_professor_coordenacao(professor_coord_id)
            contexto = apc_router.obter_contexto_apc_api(usuario=usuario_hibrido)
            self.assertTrue(contexto["usuario"]["pode_gerir"])
            self.assertTrue(contexto["usuario"]["eh_professor"])

            calendario_docente = apc_router.listar_calendario_apc_api(
                mes="2034-03",
                ano_letivo=2034,
                visao="docente",
                usuario=usuario_hibrido,
            )
            self.assertEqual(len(calendario_docente["periodos"]), 1)
            self.assertEqual(int(calendario_docente["periodos"][0]["total_elegiveis"]), 1)

            calendario_gestao = apc_router.listar_calendario_apc_api(
                mes="2034-03",
                ano_letivo=2034,
                visao="gestao",
                usuario=usuario_hibrido,
            )
            self.assertEqual(len(calendario_gestao["periodos"]), 1)
            self.assertEqual(int(calendario_gestao["periodos"][0]["total_elegiveis"]), 2)

            detalhe_docente = apc_router.obter_periodo_apc_api(
                periodo_id=int(periodo["id"]),
                visao="docente",
                usuario=usuario_hibrido,
            )
            self.assertEqual(int(detalhe_docente["professor_id"]), professor_coord_id)
            self.assertEqual(int(detalhe_docente["total_entregas"]), 1)

            detalhe_gestao = apc_router.obter_periodo_apc_api(
                periodo_id=int(periodo["id"]),
                visao="gestao",
                usuario=usuario_hibrido,
            )
            self.assertEqual(int(detalhe_gestao["total_elegiveis"]), 2)
            self.assertEqual(len(detalhe_gestao["itens"]), 2)

    def test_professor_remove_envio_e_reenvia_arquivo_dentro_do_prazo(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            apc_dir = os.path.join(tmp_dir, "apc")
            database, models, apc_router = _reload_modules(db_path, apc_dir)
            database.criar_tabelas()

            turma_id = int(database.criar_turma("6A", "MATUTINO", 29))
            disciplina_id = int(database.criar_disciplina("Geografia APC Reenvio", 3))
            professor_id = int(
                database.criar_professor(
                    nome="Professor Reenvio",
                    email="reenvio@escola.local",
                    senha_hash=database.hash_senha("Senha@123"),
                    data_nascimento="1988-12-02",
                    aulas_semanais=9,
                    turmas_quantidade=1,
                    turmas=["6A"],
                    disciplinas=["Geografia APC Reenvio"],
                )
            )

            database.criar_ou_atualizar_turma_disciplina(
                turma_id=turma_id,
                disciplina_id=disciplina_id,
                carga_horaria=3,
                professor_usuario_id=professor_id,
            )
            database.criar_horario_escolar(
                ano_letivo=2035,
                turma_id=turma_id,
                disciplina_id=disciplina_id,
                professor_usuario_id=professor_id,
                dia_semana="QUARTA",
                aula_numero=2,
            )

            periodo = apc_router.criar_periodo_apc_api(
                payload=models.ApcPeriodoIn(
                    ano_letivo=2035,
                    data_referencia="2035-11-14",
                    prazo_envio="2035-11-14T23:59",
                    titulo="Atividade complementar",
                    observacao="Teste de remocao e novo envio.",
                    publico_alvo="HORARIO_DIA",
                ),
                usuario=self._usuario_coord(),
            )

            envio = apc_router.enviar_arquivo_apc_api(
                periodo_id=int(periodo["id"]),
                arquivo=UploadFile(
                    io.BytesIO(b"versao inicial"),
                    filename="atividade-inicial.pdf",
                    headers=Headers({"content-type": "application/pdf"}),
                ),
                usuario=self._usuario_professor(professor_id),
            )
            caminho_inicial = Path(str(envio["arquivo_path"]))
            self.assertTrue(caminho_inicial.exists())

            resposta_remocao = apc_router.excluir_envio_apc_api(
                envio_id=int(envio["id"]),
                usuario=self._usuario_professor(professor_id),
            )
            self.assertIn("sucesso", resposta_remocao["mensagem"].lower())
            self.assertFalse(caminho_inicial.exists())
            self.assertIsNone(database.buscar_apc_envio_por_id(int(envio["id"])))

            detalhe_pos_remocao = apc_router.obter_periodo_apc_api(
                periodo_id=int(periodo["id"]),
                usuario=self._usuario_professor(professor_id),
            )
            self.assertEqual(int(detalhe_pos_remocao["total_enviadas"]), 0)
            self.assertEqual(int(detalhe_pos_remocao["total_pendentes"]), 1)

            novo_envio = apc_router.enviar_arquivo_apc_api(
                periodo_id=int(periodo["id"]),
                arquivo=UploadFile(
                    io.BytesIO(b"versao corrigida"),
                    filename="atividade-corrigida.pdf",
                    headers=Headers({"content-type": "application/pdf"}),
                ),
                usuario=self._usuario_professor(professor_id),
            )
            self.assertTrue(Path(str(novo_envio["arquivo_path"])).exists())
            self.assertEqual(novo_envio["arquivo_nome_cliente"], "atividade-corrigida.pdf")
            self.assertEqual(
                novo_envio["arquivo_nome_original"],
                "Atividade complementar - Professor Reenvio - 2035-11-14.pdf",
            )

            detalhe_final = apc_router.obter_periodo_apc_api(
                periodo_id=int(periodo["id"]),
                usuario=self._usuario_professor(professor_id),
            )
            self.assertEqual(int(detalhe_final["total_enviadas"]), 1)
            self.assertEqual(int(detalhe_final["total_pendentes"]), 0)

    def test_preview_docx_reutiliza_conversao_para_pdf(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            apc_dir = os.path.join(tmp_dir, "apc")
            _database, _models, apc_router = _reload_modules(db_path, apc_dir)

            caminho_docx = Path(apc_dir) / "atividade.docx"
            caminho_docx.parent.mkdir(parents=True, exist_ok=True)
            caminho_docx.write_bytes(b"conteudo docx")
            envio = {
                "id": 91,
                "professor_id": 44,
                "arquivo_path": str(caminho_docx),
                "arquivo_nome_original": "Atividade - Professor - 2035-11-14.docx",
                "arquivo_tipo": (
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                ),
            }

            with (
                patch.object(apc_router, "buscar_apc_envio_por_id", return_value=envio),
                patch.object(
                    apc_router,
                    "gerar_preview_pdf_apc",
                    return_value=b"%PDF-preview",
                ) as gerar_preview,
            ):
                resposta = apc_router.visualizar_arquivo_apc_api(
                    envio_id=91,
                    usuario=self._usuario_professor(44),
                )

            self.assertEqual(resposta.media_type, "application/pdf")
            self.assertEqual(resposta.body, b"%PDF-preview")
            self.assertEqual(resposta.headers.get("Cache-Control"), "no-store")
            gerar_preview.assert_called_once_with(
                caminho_docx.resolve(),
                "Atividade - Professor - 2035-11-14.docx",
            )

    def test_coordenador_imprime_anexo_usando_fluxo_de_impressao(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            apc_dir = os.path.join(tmp_dir, "apc")
            _database, _models, apc_router = _reload_modules(db_path, apc_dir)

            caminho_pdf = Path(apc_dir) / "prova.pdf"
            caminho_pdf.parent.mkdir(parents=True, exist_ok=True)
            caminho_pdf.write_bytes(b"%PDF-anexo")
            envio = {
                "id": 92,
                "professor_id": 44,
                "arquivo_path": str(caminho_pdf),
                "arquivo_nome_original": "Prova bimestral.pdf",
                "arquivo_tipo": "application/pdf",
            }
            resultado = {"mensagem": "Impressao enviada", "job_id": 123}

            with (
                patch.object(apc_router, "buscar_apc_envio_por_id", return_value=envio),
                patch.object(
                    apc_router,
                    "gerar_preview_pdf_apc",
                    return_value=b"%PDF-normalizado",
                ) as gerar_pdf,
                patch.object(
                    apc_router,
                    "imprimir_anexo_pdf",
                    return_value=resultado,
                ) as imprimir,
            ):
                resposta = apc_router.imprimir_arquivo_apc_api(
                    envio_id=92,
                    copias=3,
                    paginas_por_folha=2,
                    duplex=True,
                    orientacao="paisagem",
                    intervalo_paginas="1-4",
                    tags=["PROVA"],
                    professor_id=None,
                    usuario=self._usuario_coord(),
                )

            self.assertEqual(resposta, resultado)
            gerar_pdf.assert_called_once_with(
                caminho_pdf.resolve(),
                "Prova bimestral.pdf",
            )
            imprimir.assert_called_once_with(
                conteudo_pdf=b"%PDF-normalizado",
                nome_arquivo="Prova bimestral.pdf",
                copias=3,
                paginas_por_folha=2,
                duplex=True,
                orientacao="paisagem",
                intervalo_paginas="1-4",
                tags=["PROVA"],
                professor_id=None,
                usuario=self._usuario_coord(),
            )

    def test_professor_nao_pode_imprimir_anexo_pela_gestao(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            apc_dir = os.path.join(tmp_dir, "apc")
            _database, _models, apc_router = _reload_modules(db_path, apc_dir)

            with self.assertRaises(HTTPException) as contexto:
                apc_router.imprimir_arquivo_apc_api(
                    envio_id=92,
                    copias=1,
                    paginas_por_folha=1,
                    duplex=False,
                    orientacao="retrato",
                    intervalo_paginas="",
                    tags=["ATIVIDADE"],
                    professor_id=None,
                    usuario=self._usuario_professor(44),
                )

            self.assertEqual(contexto.exception.status_code, 403)

    def test_listagem_anual_da_gestao_traz_dimensoes_para_filtros(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            apc_dir = os.path.join(tmp_dir, "apc")
            _database, _models, apc_router = _reload_modules(db_path, apc_dir)
            periodo = {
                "id": 77,
                "ano_letivo": 2035,
                "data_referencia": "2035-08-20",
                "prazo_envio": "2035-08-19 18:00:00",
                "titulo": "Prova bimestral",
                "publico_alvo": "TODOS_PROFESSORES",
                "tipo_entrega": "PROVA_BIMESTRAL",
            }
            painel = {
                "periodo": {**periodo, "prazo_expirado": False},
                "total_elegiveis": 2,
                "total_enviados": 1,
                "total_pendentes": 1,
                "itens": [
                    {
                        "professor_nome": "Ana",
                        "disciplina_nome": "Matematica",
                        "turma_nome": "9A",
                        "envio": {"enviado_em": "2035-08-18 10:00:00"},
                    },
                    {
                        "professor_nome": "Bruno",
                        "disciplina_nome": "Ciencias",
                        "turma_nome": "9B",
                        "envio": None,
                    },
                ],
            }

            with (
                patch.object(apc_router, "listar_apc_periodos", return_value=[periodo]),
                patch.object(apc_router, "_obter_elegiveis_periodo", return_value=[]),
                patch.object(apc_router, "listar_apc_envios", return_value=[]),
                patch.object(apc_router, "montar_painel_periodo_apc", return_value=painel),
            ):
                resposta = apc_router.listar_solicitacoes_gestao_apc_api(
                    ano_letivo=2035,
                    usuario=self._usuario_coord(),
                )

            self.assertEqual(resposta["ano_letivo"], 2035)
            self.assertEqual(len(resposta["periodos"]), 1)
            resumo = resposta["periodos"][0]
            self.assertEqual(resumo["professores"], ["Ana", "Bruno"])
            self.assertEqual(resumo["disciplinas"], ["Ciencias", "Matematica"])
            self.assertEqual(resumo["turmas"], ["9A", "9B"])
            self.assertEqual(resumo["ultimo_envio_em"], "2035-08-18 10:00:00")


if __name__ == "__main__":
    unittest.main()
