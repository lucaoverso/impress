import importlib
import os
import sys
import tempfile
import unittest


def _reload_modulos(db_path: str):
    os.environ["DB_PATH"] = db_path
    for nome_modulo in ("database", "ocorrencias_router"):
        if nome_modulo in sys.modules:
            del sys.modules[nome_modulo]
    database = importlib.import_module("database")
    ocorrencias_router = importlib.import_module("ocorrencias_router")
    return database, ocorrencias_router


class OcorrenciasRouterTest(unittest.TestCase):
    def setUp(self):
        self._old_db_path = os.environ.get("DB_PATH")

    def tearDown(self):
        if self._old_db_path is None:
            os.environ.pop("DB_PATH", None)
        else:
            os.environ["DB_PATH"] = self._old_db_path

    def _criar_professor(self, database, nome: str, email: str) -> dict:
        database.criar_usuario(nome, email, "senha123", "professor", "PROFESSOR")
        professor = database.buscar_usuario_por_email(email)
        self.assertIsNotNone(professor)
        return professor

    def test_criar_ocorrencia_persiste_base_legal(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, ocorrencias_router = _reload_modulos(db_path)
            database.criar_tabelas()

            turma_id = int(database.criar_turma("Turma Teste Router", "MATUTINO", 30))
            item_id = database.criar_regimento_item(
                lei_nome="Regimento Interno",
                artigo_numero="76",
                artigo_descricao="Dos deveres do estudante.",
                inciso_numero="VII",
                inciso_descricao="Integrar-se ao processo pedagogico desenvolvido pela unidade escolar.",
            )

            payload = ocorrencias_router.OcorrenciaCreateIn(
                nome_estudante="Estudante Teste",
                estudante_id=None,
                turma_id=turma_id,
                professor_requerente="Professor Teste",
                professor_requerente_id=None,
                disciplina="Portugues",
                data_ocorrencia="2026-03-20",
                aula="2",
                horario_ocorrencia="07:30",
                descricao="Descricao em negrito e marcada.",
                descricao_formatada=(
                    "<p><strong>Descricao</strong> em "
                    '<span style="background-color: rgb(255, 243, 163);">negrito</span>'
                    "<script>alert(1)</script></p>"
                ),
                regimento_item_ids=[item_id],
                acao_aplicada="advertencia",
                status="registrado",
            )

            resposta = ocorrencias_router.criar_ocorrencia_api(
                payload,
                usuario={"cargo": "ADMIN"},
            )

            self.assertEqual(
                [item["regimento_item_id"] for item in resposta["regimento_itens"]],
                [item_id],
            )
            self.assertEqual(resposta["regimento_itens"][0]["tipo"], "inciso")

            conn = database.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT regimento_item_id
                FROM ocorrencia_regimento_itens
                WHERE ocorrencia_id = ?
                ORDER BY ordem
                """,
                (int(resposta["id"]),),
            )
            self.assertEqual([row["regimento_item_id"] for row in cursor.fetchall()], [item_id])
            conn.close()

    def test_criar_registro_individual_de_professor_sem_turma_ou_base_legal(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, ocorrencias_router = _reload_modulos(db_path)
            database.criar_tabelas()

            professor = self._criar_professor(
                database,
                "Professor Alinhamento",
                "professor.alinhamento@escola.test",
            )

            payload = ocorrencias_router.OcorrenciaCreateIn(
                tipo_registro="professor",
                nome_estudante=None,
                estudante_id=None,
                turma_id=None,
                professor_requerente=professor["nome"],
                professor_requerente_id=int(professor["id"]),
                disciplina="Alinhamento pedagogico",
                data_ocorrencia="2026-03-24",
                aula=None,
                horario_ocorrencia="09:00",
                descricao="Registro individual de orientacao ao professor.",
                regimento_item_ids=[],
                acao_aplicada="orientacao_professor",
                status="registrado",
            )

            resposta = ocorrencias_router.criar_ocorrencia_api(
                payload,
                usuario={"cargo": "ADMIN"},
            )

            self.assertEqual(resposta["tipo_registro"], "professor")
            self.assertEqual(resposta["nome_estudante"], professor["nome"])
            self.assertEqual(resposta["professor_requerente"], professor["nome"])
            self.assertEqual(int(resposta["professor_requerente_id"]), int(professor["id"]))
            self.assertIsNone(resposta["turma_id"])
            self.assertEqual(resposta["aula"], "")
            self.assertEqual(resposta["disciplina"], "Alinhamento pedagogico")
            self.assertEqual(resposta["regimento_itens"], [])

    def test_criar_registro_geral_docentes_sem_professor_individual(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, ocorrencias_router = _reload_modulos(db_path)
            database.criar_tabelas()

            payload = ocorrencias_router.OcorrenciaCreateIn(
                tipo_registro="geral",
                nome_estudante="Orientacoes gerais para fechamento do bimestre",
                estudante_id=None,
                turma_id=None,
                professor_requerente=None,
                professor_requerente_id=None,
                disciplina="Pauta institucional",
                data_ocorrencia="2026-03-25",
                aula=None,
                horario_ocorrencia="17:30",
                descricao="Registro geral para alinhamento com todo o corpo docente.",
                regimento_item_ids=[],
                acao_aplicada="orientacao_geral_docentes",
                status="registrado",
            )

            resposta = ocorrencias_router.criar_ocorrencia_api(
                payload,
                usuario={"cargo": "ADMIN"},
            )

            self.assertEqual(resposta["tipo_registro"], "geral")
            self.assertEqual(
                resposta["nome_estudante"],
                "Orientacoes gerais para fechamento do bimestre",
            )
            self.assertEqual(resposta["professor_requerente"], "Todos os professores")
            self.assertIsNone(resposta["professor_requerente_id"])
            self.assertIsNone(resposta["turma_id"])
            self.assertEqual(resposta["aula"], "")
            self.assertEqual(resposta["regimento_itens"], [])

    def test_criar_ocorrencia_exige_base_legal(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, ocorrencias_router = _reload_modulos(db_path)
            database.criar_tabelas()

            turma_id = int(database.criar_turma("Turma Sem Base Legal", "MATUTINO", 30))
            payload = ocorrencias_router.OcorrenciaCreateIn(
                nome_estudante="Estudante Sem Base",
                estudante_id=None,
                turma_id=turma_id,
                professor_requerente="Professor Teste",
                professor_requerente_id=None,
                disciplina="Portugues",
                data_ocorrencia="2026-03-20",
                aula="2",
                horario_ocorrencia="07:30",
                descricao="Descricao valida para ocorrencia sem base.",
                regimento_item_ids=[],
                acao_aplicada="registro_informativo",
                status="registrado",
            )

            with self.assertRaises(ocorrencias_router.HTTPException) as ctx:
                ocorrencias_router.criar_ocorrencia_api(
                    payload,
                    usuario={"cargo": "ADMIN"},
                )

            self.assertEqual(ctx.exception.status_code, 400)
            self.assertIn("base legal", str(ctx.exception.detail).lower())

            conn = database.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS total FROM ocorrencias")
            self.assertEqual(int(cursor.fetchone()["total"]), 0)
            conn.close()

    def test_atualizar_ocorrencia_nao_permite_remover_base_legal(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, ocorrencias_router = _reload_modulos(db_path)
            database.criar_tabelas()

            turma_id = int(database.criar_turma("Turma Update Router", "MATUTINO", 30))
            item_id = database.criar_regimento_item(
                lei_nome="Regimento Interno",
                artigo_numero="77",
                artigo_descricao="Da conservacao do patrimonio escolar.",
            )
            payload = ocorrencias_router.OcorrenciaCreateIn(
                nome_estudante="Estudante Update",
                estudante_id=None,
                turma_id=turma_id,
                professor_requerente="Professor Teste",
                professor_requerente_id=None,
                disciplina="Portugues",
                data_ocorrencia="2026-03-21",
                aula="2",
                horario_ocorrencia="07:30",
                descricao="Descricao com base legal.",
                regimento_item_ids=[item_id],
                acao_aplicada="orientacao_verbal",
                status="registrado",
            )
            resposta = ocorrencias_router.criar_ocorrencia_api(
                payload,
                usuario={"cargo": "ADMIN"},
            )

            update_payload = ocorrencias_router.OcorrenciaUpdateIn(regimento_item_ids=[])
            with self.assertRaises(ocorrencias_router.HTTPException) as ctx:
                ocorrencias_router.atualizar_ocorrencia_parcial_api(
                    int(resposta["id"]),
                    update_payload,
                    usuario={"cargo": "ADMIN"},
                )

            self.assertEqual(ctx.exception.status_code, 400)
            self.assertIn("base legal", str(ctx.exception.detail).lower())

            conn = database.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT regimento_item_id
                FROM ocorrencia_regimento_itens
                WHERE ocorrencia_id = ?
                ORDER BY ordem
                """,
                (int(resposta["id"]),),
            )
            self.assertEqual([row["regimento_item_id"] for row in cursor.fetchall()], [item_id])
            conn.close()


if __name__ == "__main__":
    unittest.main()
