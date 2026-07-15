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

    def test_cadastro_estudante_permite_informar_e_editar_sexo(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, ocorrencias_router = _reload_modulos(db_path)
            database.criar_tabelas()
            turma_id = int(database.criar_turma("7A", "MATUTINO", 30))

            criado = ocorrencias_router.criar_estudante_api(
                ocorrencias_router.EstudanteCreateIn(
                    nome="Carina",
                    turma_id=turma_id,
                    sexo="F",
                    possui_necessidade_especial=True,
                    necessidade_especial="Baixa visão",
                ),
                usuario={"cargo": "ADMIN"},
            )
            self.assertEqual(criado["sexo"], "F")
            self.assertTrue(criado["possui_necessidade_especial"])
            self.assertEqual(criado["necessidade_especial"], "Baixa visão")

            database.criar_ou_atualizar_estudante_por_nome_turma(
                nome="Carina",
                turma_id=turma_id,
                ativo=True,
            )
            self.assertEqual(database.buscar_estudante_por_id(int(criado["id"]))["sexo"], "F")
            self.assertEqual(
                database.buscar_estudante_por_id(int(criado["id"]))["necessidade_especial"],
                "Baixa visão",
            )

            atualizado = ocorrencias_router.atualizar_estudante_api(
                int(criado["id"]),
                ocorrencias_router.EstudanteUpdateIn(
                    nome="Carina",
                    turma_id=turma_id,
                    sexo="M",
                    possui_necessidade_especial=False,
                    necessidade_especial="Este texto deve ser removido",
                    ativo=True,
                ),
                usuario={"cargo": "ADMIN"},
            )
            self.assertEqual(atualizado["sexo"], "M")
            self.assertFalse(atualizado["possui_necessidade_especial"])
            self.assertIsNone(atualizado["necessidade_especial"])

    def test_cadastro_estudante_exige_descricao_da_necessidade_especial(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, ocorrencias_router = _reload_modulos(db_path)
            database.criar_tabelas()
            turma_id = int(database.criar_turma("7B", "MATUTINO", 30))

            with self.assertRaises(ocorrencias_router.HTTPException) as contexto:
                ocorrencias_router.criar_estudante_api(
                    ocorrencias_router.EstudanteCreateIn(
                        nome="João",
                        turma_id=turma_id,
                        possui_necessidade_especial=True,
                    ),
                    usuario={"cargo": "ADMIN"},
                )

            self.assertEqual(contexto.exception.status_code, 400)

    def test_gerencia_multiplos_laudos_do_estudante(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, ocorrencias_router = _reload_modulos(db_path)
            database.criar_tabelas()
            turma_id = int(database.criar_turma("8A", "MATUTINO", 30))
            estudante_id = int(database.criar_estudante("Ana", turma_id))

            primeiro = ocorrencias_router.criar_laudo_estudante_api(
                estudante_id,
                ocorrencias_router.EstudanteLaudoCreateIn(
                    cid="F90.0",
                    titulo="TDAH",
                    observacoes="Acompanhamento pedagógico.",
                ),
                usuario={"cargo": "ADMIN"},
            )
            segundo = ocorrencias_router.criar_laudo_estudante_api(
                estudante_id,
                ocorrencias_router.EstudanteLaudoCreateIn(titulo="Baixa visão"),
                usuario={"cargo": "ADMIN"},
            )

            self.assertEqual(len(ocorrencias_router.listar_laudos_estudante_api(
                estudante_id, usuario={"cargo": "ADMIN"}
            )), 2)
            self.assertTrue(database.buscar_estudante_por_id(estudante_id)["possui_necessidade_especial"])

            atualizado = ocorrencias_router.atualizar_laudo_estudante_api(
                estudante_id,
                int(primeiro["id"]),
                ocorrencias_router.EstudanteLaudoUpdateIn(
                    cid="F90.1", titulo="TDAH atualizado", ativo=True
                ),
                usuario={"cargo": "ADMIN"},
            )
            self.assertEqual(atualizado["cid"], "F90.1")

            ocorrencias_router.remover_laudo_estudante_api(
                estudante_id, int(primeiro["id"]), usuario={"cargo": "ADMIN"}
            )
            ocorrencias_router.remover_laudo_estudante_api(
                estudante_id, int(segundo["id"]), usuario={"cargo": "ADMIN"}
            )
            self.assertFalse(database.buscar_estudante_por_id(estudante_id)["possui_necessidade_especial"])

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
            self.assertEqual(
                [item["nome"] for item in resposta["estudantes_vinculados"]],
                ["Estudante Teste"],
            )
            self.assertEqual(resposta["quem_assina"], "responsavel")

            conn = database.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT quem_assina
                FROM ocorrencias
                WHERE id = ?
                """,
                (int(resposta["id"]),),
            )
            self.assertEqual(cursor.fetchone()["quem_assina"], "responsavel")
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

    def test_criar_ocorrencia_permte_escolher_quem_assina(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, ocorrencias_router = _reload_modulos(db_path)
            database.criar_tabelas()

            turma_id = int(database.criar_turma("Turma Assinatura", "MATUTINO", 30))
            item_id = database.criar_regimento_item(
                lei_nome="Regimento Interno",
                artigo_numero="76",
                artigo_descricao="Dos deveres do estudante.",
            )

            payload = ocorrencias_router.OcorrenciaCreateIn(
                tipo_registro="estudante",
                quem_assina="estudante",
                nome_estudante="Estudante Assinante",
                estudante_id=None,
                turma_id=turma_id,
                professor_requerente="Professor Teste",
                professor_requerente_id=None,
                disciplina="Portugues",
                data_ocorrencia="2026-03-20",
                aula="2",
                horario_ocorrencia="07:30",
                descricao="Descricao em que o estudante assina.",
                regimento_item_ids=[item_id],
                acao_aplicada="advertencia",
                status="registrado",
            )

            resposta = ocorrencias_router.criar_ocorrencia_api(
                payload,
                usuario={"cargo": "ADMIN"},
            )

            self.assertEqual(resposta["quem_assina"], "estudante")

    def test_criar_ocorrencia_permite_assinatura_estudante_e_responsavel(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, ocorrencias_router = _reload_modulos(db_path)
            database.criar_tabelas()

            turma_id = int(database.criar_turma("Turma Ambos Assinam", "MATUTINO", 30))
            item_id = database.criar_regimento_item(
                lei_nome="Regimento Interno",
                artigo_numero="76",
                artigo_descricao="Dos deveres do estudante.",
            )

            payload = ocorrencias_router.OcorrenciaCreateIn(
                tipo_registro="estudante",
                quem_assina="ambos",
                nome_estudante="Estudante Com Responsavel",
                estudante_id=None,
                turma_id=turma_id,
                professor_requerente="Professor Teste",
                professor_requerente_id=None,
                disciplina="Portugues",
                data_ocorrencia="2026-03-20",
                aula="2",
                horario_ocorrencia="07:30",
                descricao="Descricao em que estudante e responsavel assinam.",
                regimento_item_ids=[item_id],
                acao_aplicada="advertencia",
                status="registrado",
            )

            resposta = ocorrencias_router.criar_ocorrencia_api(
                payload,
                usuario={"cargo": "ADMIN"},
            )

            self.assertEqual(resposta["quem_assina"], "ambos")

            conn = database.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT quem_assina FROM ocorrencias WHERE id = ?",
                (int(resposta["id"]),),
            )
            self.assertEqual(cursor.fetchone()["quem_assina"], "ambos")
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
            self.assertEqual(
                [item["nome"] for item in resposta["professores_vinculados"]],
                [professor["nome"]],
            )

    def test_criar_registro_de_professor_preserva_base_legal_opcional(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, ocorrencias_router = _reload_modulos(db_path)
            database.criar_tabelas()

            professor = self._criar_professor(
                database,
                "Professor Sem Base Legal",
                "professor.sem.base@escola.test",
            )
            item_id = database.criar_regimento_item(
                lei_nome="Regimento Interno",
                artigo_numero="77",
                artigo_descricao="Da conservacao do patrimonio escolar.",
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
                regimento_item_ids=[item_id],
                acao_aplicada="orientacao_professor",
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
            conn = database.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(*) AS total
                FROM ocorrencia_regimento_itens
                WHERE ocorrencia_id = ?
                """,
                (int(resposta["id"]),),
            )
            self.assertEqual(int(cursor.fetchone()["total"]), 1)
            conn.close()

    def test_criar_registro_de_estudante_com_multiplos_vinculados(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, ocorrencias_router = _reload_modulos(db_path)
            database.criar_tabelas()

            turma_id = int(database.criar_turma("Turma Multi", "MATUTINO", 30))
            item_id = database.criar_regimento_item(
                lei_nome="Regimento Interno",
                artigo_numero="76",
                artigo_descricao="Dos deveres do estudante.",
                inciso_numero="VII",
                inciso_descricao="Integrar-se ao processo pedagogico desenvolvido pela unidade escolar.",
            )
            estudante_1_id = int(database.criar_estudante("Estudante Um", turma_id))
            estudante_2_id = int(database.criar_estudante("Estudante Dois", turma_id))

            payload = ocorrencias_router.OcorrenciaCreateIn(
                tipo_registro="estudante",
                nome_estudante=None,
                estudante_id=None,
                estudantes_vinculados=[
                    {"estudante_id": estudante_1_id, "nome": "Ignorado", "turma_id": turma_id},
                    {"estudante_id": estudante_2_id, "nome": "Ignorado", "turma_id": turma_id},
                ],
                turma_id=turma_id,
                professor_requerente="Professor Teste",
                professor_requerente_id=None,
                disciplina="Portugues",
                data_ocorrencia="2026-03-26",
                aula="2",
                horario_ocorrencia="07:30",
                descricao="Registro envolvendo dois estudantes.",
                regimento_item_ids=[item_id],
                acao_aplicada="advertencia",
                status="registrado",
            )

            resposta = ocorrencias_router.criar_ocorrencia_api(payload, usuario={"cargo": "ADMIN"})

            self.assertEqual(resposta["nome_estudante"], "Estudante Um, Estudante Dois")
            self.assertEqual(
                [item["nome"] for item in resposta["estudantes_vinculados"]],
                ["Estudante Um", "Estudante Dois"],
            )
            self.assertEqual(
                [item["estudante_id"] for item in resposta["estudantes_vinculados"]],
                [estudante_1_id, estudante_2_id],
            )

    def test_criar_registro_de_professor_com_multiplos_vinculados(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, ocorrencias_router = _reload_modulos(db_path)
            database.criar_tabelas()

            professor_1 = self._criar_professor(database, "Professor Um", "prof.um@escola.test")
            professor_2 = self._criar_professor(database, "Professor Dois", "prof.dois@escola.test")

            payload = ocorrencias_router.OcorrenciaCreateIn(
                tipo_registro="professor",
                nome_estudante=None,
                estudante_id=None,
                turma_id=None,
                professor_requerente=None,
                professor_requerente_id=None,
                professores_vinculados=[
                    {"professor_id": int(professor_1["id"]), "nome": professor_1["nome"]},
                    {"professor_id": int(professor_2["id"]), "nome": professor_2["nome"]},
                ],
                disciplina="Orientacoes de fechamento",
                data_ocorrencia="2026-03-27",
                aula=None,
                horario_ocorrencia="10:15",
                descricao="Registro envolvendo dois professores.",
                regimento_item_ids=[],
                acao_aplicada="reuniao_alinhamento",
                status="registrado",
            )

            resposta = ocorrencias_router.criar_ocorrencia_api(payload, usuario={"cargo": "ADMIN"})

            self.assertEqual(resposta["professor_requerente"], "Professor Um, Professor Dois")
            self.assertEqual(
                [item["nome"] for item in resposta["professores_vinculados"]],
                ["Professor Um", "Professor Dois"],
            )

    def test_registro_de_professor_rejeita_acao_disciplinar_de_estudante(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, ocorrencias_router = _reload_modulos(db_path)
            database.criar_tabelas()

            professor = self._criar_professor(database, "Professor Restrito", "prof.restrito@escola.test")

            payload = ocorrencias_router.OcorrenciaCreateIn(
                tipo_registro="professor",
                nome_estudante=None,
                estudante_id=None,
                turma_id=None,
                professor_requerente=professor["nome"],
                professor_requerente_id=int(professor["id"]),
                professores_vinculados=[
                    {"professor_id": int(professor["id"]), "nome": professor["nome"]},
                ],
                disciplina="Assunto institucional",
                data_ocorrencia="2026-03-28",
                aula=None,
                horario_ocorrencia="08:40",
                descricao="Acao invalida para professor.",
                regimento_item_ids=[],
                acao_aplicada="advertencia",
                status="registrado",
            )

            with self.assertRaises(ocorrencias_router.HTTPException) as ctx:
                ocorrencias_router.criar_ocorrencia_api(payload, usuario={"cargo": "ADMIN"})

            self.assertEqual(ctx.exception.status_code, 400)
            self.assertIn("tipo de registro", str(ctx.exception.detail).lower())

    def test_criar_registro_geral_docentes_sem_professor_individual(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, ocorrencias_router = _reload_modulos(db_path)
            database.criar_tabelas()
            item_id = database.criar_regimento_item(
                lei_nome="Regimento Interno",
                artigo_numero="12",
                artigo_descricao="Das orientacoes institucionais ao corpo docente.",
            )

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
                regimento_item_ids=[item_id],
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
            self.assertEqual(
                [item["regimento_item_id"] for item in resposta["regimento_itens"]],
                [item_id],
            )

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

    def test_atualizar_tipo_para_professor_preserva_base_legal_existente(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, ocorrencias_router = _reload_modulos(db_path)
            database.criar_tabelas()

            turma_id = int(database.criar_turma("Turma Migracao", "MATUTINO", 30))
            professor = self._criar_professor(
                database,
                "Professor Migracao",
                "professor.migracao@escola.test",
            )
            item_id = database.criar_regimento_item(
                lei_nome="Regimento Interno",
                artigo_numero="77",
                artigo_descricao="Da conservacao do patrimonio escolar.",
            )
            payload = ocorrencias_router.OcorrenciaCreateIn(
                nome_estudante="Estudante Migracao",
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

            update_payload = ocorrencias_router.OcorrenciaUpdateIn(
                tipo_registro="professor",
                professor_requerente=professor["nome"],
                professor_requerente_id=int(professor["id"]),
                professores_vinculados=[
                    ocorrencias_router.OcorrenciaProfessorVinculadoIn(
                        professor_id=int(professor["id"]),
                        nome=professor["nome"],
                    )
                ],
                disciplina="Acompanhamento funcional",
                acao_aplicada="orientacao_professor",
            )
            atualizada = ocorrencias_router.atualizar_ocorrencia_parcial_api(
                int(resposta["id"]),
                update_payload,
                usuario={"cargo": "ADMIN"},
            )

            self.assertEqual(atualizada["tipo_registro"], "professor")
            self.assertEqual(
                [item["regimento_item_id"] for item in atualizada["regimento_itens"]],
                [item_id],
            )
            conn = database.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(*) AS total
                FROM ocorrencia_regimento_itens
                WHERE ocorrencia_id = ?
                """,
                (int(resposta["id"]),),
            )
            self.assertEqual(int(cursor.fetchone()["total"]), 1)
            conn.close()


if __name__ == "__main__":
    unittest.main()
