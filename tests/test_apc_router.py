import importlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path

from fastapi import UploadFile
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
            self.assertTrue(contexto["usuario"]["pode_gerir"])

            quinta = apc_router.criar_periodo_apc_api(
                payload=models.ApcPeriodoIn(
                    ano_letivo=2031,
                    data_referencia="2031-05-08",
                    prazo_envio="2031-05-08T23:59",
                    titulo="APC Quinta",
                    observacao="Entrega semanal",
                ),
                usuario=self._usuario_coord(),
            )
            sexta = apc_router.criar_periodo_apc_api(
                payload=models.ApcPeriodoIn(
                    ano_letivo=2031,
                    data_referencia="2031-05-09",
                    prazo_envio="2031-05-09T23:59",
                    titulo="APC Sexta",
                    observacao="Nao deve aparecer para este professor",
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
            self.assertEqual(envio["arquivo_nome_original"], "atividade.pdf")
            self.assertTrue(Path(str(envio["arquivo_path"])).exists())

            detalhe_professor = apc_router.obter_periodo_apc_api(
                periodo_id=int(quinta["id"]),
                usuario=self._usuario_professor(professor_id),
            )
            self.assertIsNotNone(detalhe_professor["envio"])
            self.assertEqual(int(detalhe_professor["total_aulas"]), 1)

            detalhe_gestao_atualizado = apc_router.obter_periodo_apc_api(
                periodo_id=int(quinta["id"]),
                usuario=self._usuario_coord(),
            )
            self.assertEqual(int(detalhe_gestao_atualizado["total_enviados"]), 1)
            self.assertEqual(int(detalhe_gestao_atualizado["total_pendentes"]), 0)
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


if __name__ == "__main__":
    unittest.main()
