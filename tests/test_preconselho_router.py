import importlib
import os
import sys
import tempfile
import types
import unittest


def _reload_modulos(db_path: str):
    os.environ["DB_PATH"] = db_path
    os.environ["ENABLE_EMBEDDED_WORKER"] = "0"

    for nome_modulo in (
        "services.auth_service",
        "services.preconselho_service",
        "auth",
        "preconselho_router",
        "database",
    ):
        if nome_modulo in sys.modules:
            del sys.modules[nome_modulo]

    if "pypdf" not in sys.modules:
        sys.modules["pypdf"] = types.SimpleNamespace(
            PdfReader=object,
            PdfWriter=object,
            Transformation=object,
        )

    database = importlib.import_module("database")
    preconselho_router = importlib.import_module("preconselho_router")
    models = importlib.import_module("models")
    return database, preconselho_router, models


class PreConselhoRouterTest(unittest.TestCase):
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

    def _usuario_professor(
        self,
        professor_id: int,
        nome: str,
        *,
        acesso_coordenacao: bool = False,
    ) -> dict:
        return {
            "id": professor_id,
            "nome": nome,
            "cargo": "PROFESSOR",
            "acesso_coordenacao": 1 if acesso_coordenacao else 0,
        }

    def _usuario_coord(self, coordenador_id: int, nome: str) -> dict:
        return {"id": coordenador_id, "nome": nome, "cargo": "COORDENADOR"}

    def _usuario_admin(self) -> dict:
        return {"id": 999, "nome": "Admin Teste", "cargo": "ADMIN"}

    def test_contexto_limita_turmas_e_disciplinas_do_professor(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, preconselho_router, _models = _reload_modulos(db_path)
            database.criar_tabelas()

            database.criar_turma("7A", "MATUTINO", 30)
            database.criar_turma("8A", "MATUTINO", 28)
            database.criar_disciplina("Matematica", 5)
            database.criar_disciplina("Ciencias", 4)
            database.criar_disciplina("Historia", 3)

            professor_id = int(
                database.criar_professor(
                    nome="Professor Contexto",
                    email="contexto.prof@escola.local",
                    senha_hash=database.hash_senha("Senha@123"),
                    data_nascimento="1990-05-20",
                    aulas_semanais=12,
                    turmas_quantidade=1,
                    turmas=["7A"],
                    disciplinas=["Matematica", "Ciencias"],
                )
            )

            resposta = preconselho_router.obter_contexto_preconselho_api(
                usuario=self._usuario_professor(professor_id, "Professor Contexto"),
            )

            self.assertEqual([item["nome"] for item in resposta["turmas"]], ["7A"])
            self.assertEqual(
                [item["nome"] for item in resposta["disciplinas"]],
                ["Ciencias", "Matematica"],
            )
            self.assertGreater(len(resposta["periodos"]), 0)
            self.assertGreater(len(resposta["motivos"]), 0)

    def test_professor_salva_registro_e_coordenacao_consolida(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, preconselho_router, models = _reload_modulos(db_path)
            database.criar_tabelas()

            turma_id = int(database.criar_turma("7A", "MATUTINO", 30))
            disciplina_id = int(database.criar_disciplina("Matematica", 5))
            disciplina_historia_id = int(database.criar_disciplina("Historia", 3))
            estudante_id = int(database.criar_estudante("Ana", turma_id))
            professor_id = int(
                database.criar_professor(
                    nome="Professor Registro",
                    email="registro.prof@escola.local",
                    senha_hash=database.hash_senha("Senha@123"),
                    data_nascimento="1991-04-11",
                    aulas_semanais=10,
                    turmas_quantidade=1,
                    turmas=["7A"],
                    disciplinas=["Matematica", "Historia"],
                )
            )
            coordenador_id = int(
                database.criar_coordenador(
                    nome="Coordenadora",
                    email="coord@escola.local",
                    senha_hash=database.hash_senha("Senha@123"),
                    data_nascimento="1988-08-10",
                )
            )
            periodo_id = int(
                database.criar_periodo_pre_conselho(
                    nome="1o Bimestre 2032",
                    ano_letivo=2032,
                    etapa=1,
                    data_inicio="2032-01-20",
                    data_fim="2032-04-30",
                    status="ABERTO",
                )
            )

            motivos = database.listar_motivos_pre_conselho()
            motivo_ids = [int(motivos[0]["id"]), int(motivos[1]["id"]), int(motivos[4]["id"])]

            payload = models.PreConselhoRegistroSaveIn(
                periodo_id=periodo_id,
                turma_id=turma_id,
                disciplina_id=disciplina_id,
                estudante_id=estudante_id,
                sinalizar=True,
                motivo_ids=motivo_ids,
                observacao_professor="precisa retomar a rotina de estudos",
                nivel_atencao="medio",
            )

            salvo = preconselho_router.salvar_registro_preconselho_api(
                payload=payload,
                usuario=self._usuario_professor(professor_id, "Professor Registro"),
            )

            self.assertGreater(int(salvo["id"]), 0)
            self.assertEqual(int(salvo["estudante_id"]), estudante_id)
            self.assertEqual(int(salvo["disciplina_id"]), disciplina_id)
            self.assertIn(
                "O estudante Ana obteve baixo rendimento na disciplina de Matematica",
                salvo["texto_gerado"],
            )

            salvo_historia = preconselho_router.salvar_registro_preconselho_api(
                payload=models.PreConselhoRegistroSaveIn(
                    periodo_id=periodo_id,
                    turma_id=turma_id,
                    disciplina_id=disciplina_historia_id,
                    estudante_id=estudante_id,
                    sinalizar=True,
                    motivo_ids=[motivo_ids[0]],
                    observacao_professor="apresentou dificuldade para retomar os conteudos",
                    nivel_atencao="alto",
                ),
                usuario=self._usuario_professor(professor_id, "Professor Registro"),
            )

            self.assertEqual(int(salvo_historia["disciplina_id"]), disciplina_historia_id)

            listagem = preconselho_router.listar_registros_preconselho_api(
                periodo_id=periodo_id,
                turma_id=turma_id,
                disciplina_id=disciplina_id,
                professor_id=None,
                usuario=self._usuario_professor(professor_id, "Professor Registro"),
            )

            self.assertEqual(listagem["total_registros"], 1)
            self.assertEqual(listagem["itens"][0]["estudante_nome"], "Ana")

            consolidado = preconselho_router.gerar_consolidado_preconselho_api(
                periodo_id=periodo_id,
                turma_id=turma_id,
                disciplina_id=None,
                professor_id=professor_id,
                usuario=self._usuario_coord(coordenador_id, "Coordenadora"),
            )

            self.assertEqual(consolidado["total_registros"], 2)
            self.assertEqual(consolidado["total_estudantes"], 1)
            self.assertIn("1o Bimestre 2032", consolidado["texto"])
            self.assertIn("Ana", consolidado["texto"])
            self.assertIn("Historia", consolidado["texto"])
            self.assertIn("Matematica", consolidado["texto"])
            self.assertEqual(len(consolidado["itens_agrupados"]), 1)
            self.assertEqual(
                sorted(consolidado["itens_agrupados"][0]["disciplinas"]), ["Historia", "Matematica"]
            )

    def test_professor_com_acesso_coordenacao_tem_visao_docente_e_consolidacao(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, preconselho_router, models = _reload_modulos(db_path)
            database.criar_tabelas()

            turma_id = int(database.criar_turma("9A", "MATUTINO", 32))
            disciplina_id = int(database.criar_disciplina("Biologia Experimental", 4))
            estudante_id = int(database.criar_estudante("Carlos", turma_id))

            professor_hibrido_id = int(
                database.criar_professor(
                    nome="Professor Hibrido",
                    email="hibrido@escola.local",
                    senha_hash=database.hash_senha("Senha@123"),
                    data_nascimento="1992-02-02",
                    aulas_semanais=10,
                    turmas_quantidade=1,
                    turmas=["9A"],
                    disciplinas=["Biologia Experimental"],
                    acesso_coordenacao=True,
                )
            )
            professor_colega_id = int(
                database.criar_professor(
                    nome="Professora Colega",
                    email="colega@escola.local",
                    senha_hash=database.hash_senha("Senha@123"),
                    data_nascimento="1990-03-03",
                    aulas_semanais=10,
                    turmas_quantidade=1,
                    turmas=["9A"],
                    disciplinas=["Biologia Experimental"],
                )
            )
            periodo_id = int(
                database.criar_periodo_pre_conselho(
                    nome="1o Bimestre 2034",
                    ano_letivo=2034,
                    etapa=1,
                    data_inicio="2034-01-20",
                    data_fim="2034-04-30",
                    status="ABERTO",
                )
            )

            motivo_id = int(database.listar_motivos_pre_conselho()[0]["id"])
            preconselho_router.salvar_registro_preconselho_api(
                payload=models.PreConselhoRegistroSaveIn(
                    periodo_id=periodo_id,
                    turma_id=turma_id,
                    disciplina_id=disciplina_id,
                    estudante_id=estudante_id,
                    sinalizar=True,
                    motivo_ids=[motivo_id],
                    observacao_professor="precisa revisar os conceitos da unidade",
                    nivel_atencao="medio",
                ),
                usuario=self._usuario_professor(professor_colega_id, "Professora Colega"),
            )

            usuario_hibrido = self._usuario_professor(
                professor_hibrido_id,
                "Professor Hibrido",
                acesso_coordenacao=True,
            )
            contexto = preconselho_router.obter_contexto_preconselho_api(usuario=usuario_hibrido)

            self.assertTrue(contexto["pode_consolidar"])
            self.assertEqual(contexto["professor_id"], professor_hibrido_id)
            self.assertEqual([item["nome"] for item in contexto["turmas"]], ["9A"])
            self.assertEqual(
                [item["nome"] for item in contexto["disciplinas"]],
                ["Biologia Experimental"],
            )

            consolidado = preconselho_router.gerar_consolidado_preconselho_api(
                periodo_id=periodo_id,
                turma_id=None,
                disciplina_id=None,
                professor_id=professor_colega_id,
                usuario=usuario_hibrido,
            )

            self.assertEqual(consolidado["professor_id"], professor_colega_id)
            self.assertEqual(consolidado["total_registros"], 1)
            self.assertIn("Carlos", consolidado["texto"])

    def test_professor_nao_pode_salvar_em_periodo_fechado(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, preconselho_router, models = _reload_modulos(db_path)
            database.criar_tabelas()

            turma_id = int(database.criar_turma("8A", "VESPERTINO", 28))
            disciplina_id = int(database.criar_disciplina("Historia", 3))
            estudante_id = int(database.criar_estudante("Bruno", turma_id))
            professor_id = int(
                database.criar_professor(
                    nome="Professor Fechado",
                    email="fechado.prof@escola.local",
                    senha_hash=database.hash_senha("Senha@123"),
                    data_nascimento="1993-06-02",
                    aulas_semanais=8,
                    turmas_quantidade=1,
                    turmas=["8A"],
                    disciplinas=["Historia"],
                )
            )
            periodo_id = int(
                database.criar_periodo_pre_conselho(
                    nome="1o Bimestre 2033",
                    ano_letivo=2033,
                    etapa=1,
                    data_inicio="2033-01-20",
                    data_fim="2033-04-30",
                    status="FECHADO",
                )
            )

            motivo_id = int(database.listar_motivos_pre_conselho()[0]["id"])
            payload = models.PreConselhoRegistroSaveIn(
                periodo_id=periodo_id,
                turma_id=turma_id,
                disciplina_id=disciplina_id,
                estudante_id=estudante_id,
                sinalizar=True,
                motivo_ids=[motivo_id],
            )

            with self.assertRaises(preconselho_router.HTTPException) as ctx:
                preconselho_router.salvar_registro_preconselho_api(
                    payload=payload,
                    usuario=self._usuario_professor(professor_id, "Professor Fechado"),
                )

            self.assertEqual(ctx.exception.status_code, 403)
            self.assertIn("Periodo fechado", str(ctx.exception.detail))

    def test_atribuicao_docente_exata_restringe_combinacoes_do_preconselho(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, preconselho_router, models = _reload_modulos(db_path)
            database.criar_tabelas()

            turma_em_id = int(database.criar_turma("1 EM A", "VESPERTINO_EM", 30))
            turma_fund_id = int(database.criar_turma("6 ano A", "MATUTINO", 28))
            geometria_id = int(database.criar_disciplina("Geometria", 3))
            letramento_id = int(database.criar_disciplina("Letramento e Raciocinio Matematico", 5))
            estudante_em_id = int(database.criar_estudante("Joao", turma_em_id))
            professor_id = int(
                database.criar_professor(
                    nome="Professor Alex",
                    email="alex.preconselho@escola.local",
                    senha_hash=database.hash_senha("Senha@123"),
                    data_nascimento="1987-04-11",
                    aulas_semanais=12,
                    turmas_quantidade=2,
                    turmas=["1 EM A", "6 ano A"],
                    disciplinas=["Geometria", "Letramento e Raciocinio Matematico"],
                )
            )
            periodo_id = int(
                database.criar_periodo_pre_conselho(
                    nome="1o Bimestre 2035",
                    ano_letivo=2035,
                    etapa=1,
                    data_inicio="2035-01-20",
                    data_fim="2035-04-30",
                    status="ABERTO",
                )
            )

            database.criar_atribuicao_docente(professor_id, turma_em_id, geometria_id)
            database.criar_atribuicao_docente(professor_id, turma_fund_id, letramento_id)

            minhas_turmas_disciplinas = (
                preconselho_router.listar_minhas_turmas_disciplinas_preconselho_api(
                    periodo_id=periodo_id,
                    usuario=self._usuario_professor(professor_id, "Professor Alex"),
                )
            )
            pares = {
                (int(item["turma_id"]), int(item["disciplina_id"]))
                for item in minhas_turmas_disciplinas
            }
            self.assertEqual(
                pares,
                {
                    (turma_em_id, geometria_id),
                    (turma_fund_id, letramento_id),
                },
            )

            motivo_id = int(database.listar_motivos_pre_conselho()[0]["id"])
            with self.assertRaises(preconselho_router.HTTPException) as ctx:
                preconselho_router.salvar_registro_preconselho_api(
                    payload=models.PreConselhoRegistroSaveIn(
                        periodo_id=periodo_id,
                        turma_id=turma_em_id,
                        disciplina_id=letramento_id,
                        estudante_id=estudante_em_id,
                        sinalizar=True,
                        motivo_ids=[motivo_id],
                    ),
                    usuario=self._usuario_professor(professor_id, "Professor Alex"),
                )

            self.assertEqual(ctx.exception.status_code, 403)
            self.assertIn("atribuicao docente", str(ctx.exception.detail))

    def test_admin_cria_e_atualiza_periodos_e_motivos(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            _database, preconselho_router, models = _reload_modulos(db_path)
            _database.criar_tabelas()
            usuario_admin = self._usuario_admin()

            periodo = preconselho_router.criar_periodo_preconselho_api(
                payload=models.PreConselhoPeriodoCreateIn(
                    nome="2o Bimestre 2034",
                    ano_letivo=2034,
                    etapa=2,
                    data_inicio="2034-05-01",
                    data_fim="2034-06-30",
                    status="ABERTO",
                ),
                usuario=usuario_admin,
            )

            self.assertEqual(periodo["ano_letivo"], 2034)
            self.assertEqual(periodo["etapa"], 2)

            periodo_atualizado = preconselho_router.atualizar_periodo_preconselho_api(
                periodo_id=int(periodo["id"]),
                payload=models.PreConselhoPeriodoUpdateIn(
                    nome="2o Bimestre 2034 - Ajustado",
                    ano_letivo=2034,
                    etapa=2,
                    data_inicio="2034-05-02",
                    data_fim="2034-06-29",
                ),
                usuario=usuario_admin,
            )

            self.assertEqual(periodo_atualizado["nome"], "2o Bimestre 2034 - Ajustado")

            motivo = preconselho_router.criar_motivo_preconselho_api(
                payload=models.PreConselhoMotivoCreateIn(
                    categoria="participacao",
                    codigo="sem_interacao_em_aula",
                    descricao="Sem interacao nas aulas",
                    ordem=500,
                ),
                usuario=usuario_admin,
            )

            self.assertEqual(motivo["categoria"], "participacao")

            motivo_atualizado = preconselho_router.atualizar_motivo_preconselho_api(
                motivo_id=int(motivo["id"]),
                payload=models.PreConselhoMotivoUpdateIn(
                    categoria="participacao",
                    descricao="Sem interacao nas atividades em aula",
                    ordem=520,
                ),
                usuario=usuario_admin,
            )

            self.assertEqual(motivo_atualizado["descricao"], "Sem interacao nas atividades em aula")

            motivo_inativo = preconselho_router.atualizar_status_motivo_preconselho_api(
                motivo_id=int(motivo["id"]),
                payload=models.PreConselhoMotivoStatusIn(ativo=False),
                usuario=usuario_admin,
            )

            self.assertEqual(int(motivo_inativo["ativo"]), 0)


if __name__ == "__main__":
    unittest.main()
