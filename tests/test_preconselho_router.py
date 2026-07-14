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
            self.assertIn("Médio", [item["nome"] for item in resposta["niveis_atencao"]])
            self.assertIn("recuperado", resposta["motivos_pos_preconselho"])
            self.assertIn("nao_recuperado", resposta["motivos_pos_preconselho"])
            self.assertFalse(resposta["pode_relatorio"])

    def test_professor_salva_registro_e_coordenacao_consolida(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, preconselho_router, models = _reload_modulos(db_path)
            database.criar_tabelas()

            turma_id = int(database.criar_turma("7A", "MATUTINO", 30))
            disciplina_id = int(database.criar_disciplina("Matematica", 5))
            disciplina_historia_id = int(database.criar_disciplina("Historia", 3))
            disciplina_geografia_id = int(database.criar_disciplina("Geografia Aplicada", 2))
            estudante_id = int(database.criar_estudante("Ana", turma_id, sexo="F"))
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
            professor_sem_registro_id = int(
                database.criar_professor(
                    nome="Professora Sem Registro",
                    email="sem.registro@escola.local",
                    senha_hash=database.hash_senha("Senha@123"),
                    data_nascimento="1992-09-15",
                    aulas_semanais=8,
                    turmas_quantidade=1,
                    turmas=["7A"],
                    disciplinas=["Geografia Aplicada"],
                )
            )
            professor_estrutura_id = int(
                database.criar_professor(
                    nome="Professora Estrutural",
                    email="estrutural@escola.local",
                    senha_hash=database.hash_senha("Senha@123"),
                    data_nascimento="1990-12-20",
                    aulas_semanais=6,
                    turmas_quantidade=0,
                    turmas=[],
                    disciplinas=[],
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
                    nome="1º Bimestre 2032",
                    ano_letivo=2032,
                    etapa=1,
                    data_inicio="2032-01-20",
                    data_fim="2032-04-30",
                    status="ABERTO",
                    tem_rav=True,
                )
            )
            database.criar_ou_atualizar_turma_disciplina(
                turma_id=turma_id,
                disciplina_id=disciplina_geografia_id,
                carga_horaria=2,
                professor_usuario_id=professor_estrutura_id,
            )
            conn = database.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                DELETE FROM professores_turmas_disciplinas
                WHERE professor_usuario_id = ?
                  AND turma_id = ?
                  AND disciplina_id = ?
                """,
                (professor_estrutura_id, turma_id, disciplina_geografia_id),
            )
            conn.commit()
            conn.close()

            motivos = database.listar_motivos_pre_conselho()
            motivo_ids = [int(motivos[0]["id"]), int(motivos[1]["id"]), int(motivos[4]["id"])]
            habilidade = preconselho_router.criar_habilidade_rav_preconselho_api(
                payload=models.PreConselhoRavHabilidadeCreateIn(
                    periodo_id=periodo_id,
                    disciplina_id=disciplina_id,
                    codigo="MS.EF05MA01.s.01",
                    descricao="Resolver problemas com numeros racionais",
                    turma_ids=[turma_id],
                    ordem=10,
                ),
                usuario=self._usuario_admin(),
            )

            payload = models.PreConselhoRegistroSaveIn(
                periodo_id=periodo_id,
                turma_id=turma_id,
                disciplina_id=disciplina_id,
                estudante_id=estudante_id,
                sinalizar=True,
                motivo_ids=motivo_ids,
                observacao_professor="precisa retomar a rotina de estudos",
                nivel_atencao="medio",
                pos_preconselho_recuperado=False,
                pos_preconselho_observacao="segue precisando de retomada individual",
                estudante_em_rav=True,
                rav_habilidade_ids=[int(habilidade["id"])],
                rav_acoes="retomada guiada com lista de exercicios e atendimento em grupo",
            )

            salvo = preconselho_router.salvar_registro_preconselho_api(
                payload=payload,
                usuario=self._usuario_professor(professor_id, "Professor Registro"),
            )

            self.assertGreater(int(salvo["id"]), 0)
            self.assertEqual(int(salvo["estudante_id"]), estudante_id)
            self.assertEqual(int(salvo["disciplina_id"]), disciplina_id)
            self.assertIn(
                "A estudante Ana obteve baixo rendimento na disciplina de Matematica",
                salvo["texto_gerado"],
            )
            self.assertIn("em razão de", salvo["texto_gerado"])
            self.assertFalse(salvo["pos_preconselho_recuperado"])
            self.assertTrue(salvo["estudante_em_rav"])
            self.assertEqual(salvo["rav_habilidade_ids"], [int(habilidade["id"])])
            self.assertEqual(
                salvo["rav_acoes"],
                "retomada guiada com lista de exercicios e atendimento em grupo",
            )
            self.assertIn("Resolver problemas com numeros racionais", salvo["texto_gerado"])
            self.assertIn("retomada guiada", salvo["texto_gerado"])
            self.assertIn("Recuperar para Avançar (RAV)", salvo["texto_gerado"])
            self.assertIn("manteve baixo rendimento", salvo["texto_gerado"].lower())

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
                    pos_preconselho_recuperado=True,
                ),
                usuario=self._usuario_professor(professor_id, "Professor Registro"),
            )

            self.assertEqual(int(salvo_historia["disciplina_id"]), disciplina_historia_id)
            self.assertIn("a estudante foi recuperada", salvo_historia["texto_gerado"])

            listagem = preconselho_router.listar_registros_preconselho_api(
                periodo_id=periodo_id,
                turma_id=turma_id,
                disciplina_id=disciplina_id,
                professor_id=None,
                usuario=self._usuario_professor(professor_id, "Professor Registro"),
            )

            self.assertEqual(listagem["total_registros"], 1)
            self.assertEqual(listagem["itens"][0]["estudante_nome"], "Ana")
            self.assertFalse(listagem["itens"][0]["pos_preconselho_recuperado"])
            self.assertTrue(listagem["itens"][0]["estudante_em_rav"])
            self.assertEqual(listagem["itens"][0]["rav_habilidade_ids"], [int(habilidade["id"])])

            rav_turma = preconselho_router.visualizar_rav_turma_preconselho_api(
                periodo_id=periodo_id,
                turma_id=turma_id,
                usuario=self._usuario_coord(coordenador_id, "Coordenadora"),
            )

            self.assertEqual(rav_turma["total_estudantes"], 1)
            self.assertEqual(rav_turma["total_registros"], 1)
            self.assertEqual(rav_turma["itens"][0]["estudante_nome"], "Ana")
            self.assertEqual(
                rav_turma["itens"][0]["rav_habilidades"][0]["descricao"],
                "Resolver problemas com numeros racionais",
            )

            consolidado = preconselho_router.gerar_consolidado_preconselho_api(
                periodo_id=periodo_id,
                turma_id=turma_id,
                disciplina_id=None,
                professor_id=professor_id,
                usuario=self._usuario_coord(coordenador_id, "Coordenadora"),
            )

            self.assertEqual(consolidado["total_registros"], 2)
            self.assertEqual(consolidado["total_estudantes"], 1)
            self.assertIn("No período 1º Bimestre 2032", consolidado["texto"])
            self.assertIn("ANA", consolidado["texto"])
            self.assertIn("A estudante ANA obteve baixo rendimento", consolidado["texto"])
            self.assertIn("Historia", consolidado["texto"])
            self.assertIn("Matematica", consolidado["texto"])
            self.assertIn("Recuperar para Avançar (RAV)", consolidado["texto"])
            self.assertNotIn("A turma do 7A, composta pelo seguinte corpo docente:", consolidado["texto"])
            self.assertIn("PROFESSOR REGISTRO (Historia e Matematica)", consolidado["texto"])
            self.assertNotIn("Professora Estrutural (Geografia Aplicada)", consolidado["texto"])
            self.assertEqual(len(consolidado["itens_agrupados"]), 1)
            self.assertEqual(
                sorted(consolidado["itens_agrupados"][0]["disciplinas"]), ["Historia", "Matematica"]
            )
            self.assertEqual(
                sorted(consolidado["itens_agrupados"][0]["professores"]),
                ["PROFESSOR REGISTRO"],
            )
            self.assertNotIn(
                "No pós-pré-conselho, registrou-se que",
                consolidado["itens_agrupados"][0]["texto"],
            )
            self.assertNotIn("Por disciplina", consolidado["itens_agrupados"][0]["texto"])
            self.assertIn(
                "Professor Registro (Matematica), precisa retomar a rotina de estudos",
                consolidado["itens_agrupados"][0]["texto"],
            )
            self.assertIn(
                "Professor Registro (Historia), apresentou dificuldade para retomar os conteudos",
                consolidado["itens_agrupados"][0]["texto"],
            )
            self.assertNotIn("Professora Sem Registro", consolidado["itens_agrupados"][0]["texto"])
            self.assertNotIn("Professora Estrutural", consolidado["itens_agrupados"][0]["texto"])

            consolidado_conselho = preconselho_router.gerar_consolidado_preconselho_api(
                periodo_id=periodo_id,
                turma_id=turma_id,
                disciplina_id=None,
                professor_id=professor_id,
                versao="conselho",
                usuario=self._usuario_coord(coordenador_id, "Coordenadora"),
            )
            self.assertEqual(consolidado_conselho["total_registros"], 1)
            self.assertEqual(consolidado_conselho["total_recuperados"], 1)
            self.assertEqual(consolidado_conselho["total_mantidos"], 1)
            self.assertEqual(consolidado_conselho["total_pendentes"], 0)
            self.assertIn("Matematica", consolidado_conselho["texto"])
            self.assertIn("PROFESSOR REGISTRO (Matematica e Historia)", consolidado_conselho["texto"])
            self.assertNotIn("Historia", consolidado_conselho["itens_agrupados"][0]["texto"])
            self.assertNotIn(
                "No pós-pré-conselho, registrou-se que",
                consolidado_conselho["itens_agrupados"][0]["texto"],
            )
            self.assertNotIn(
                "Após o pré-conselho",
                consolidado_conselho["itens_agrupados"][0]["texto"],
            )

            texto_inicial = salvo["texto_gerado"]
            with self.assertRaises(preconselho_router.HTTPException) as ctx_reavaliacao:
                preconselho_router.reavaliar_registro_preconselho_api(
                    registro_id=int(salvo["id"]),
                    payload=models.PreConselhoReavaliacaoIn(
                        recuperado=True,
                        motivo_ids=["recuperou_nota"],
                    ),
                    usuario=self._usuario_professor(professor_id, "Professor Registro"),
                )
            self.assertEqual(ctx_reavaliacao.exception.status_code, 403)

            preconselho_router.atualizar_status_periodo_preconselho_api(
                periodo_id=periodo_id,
                payload=models.PreConselhoPeriodoStatusIn(status="EM_REAVALIACAO"),
                usuario=self._usuario_admin(),
            )
            motivo_personalizado = preconselho_router.criar_motivo_reavaliacao_api(
                payload=models.PreConselhoMotivoReavaliacaoCreateIn(
                    resultado="recuperado",
                    codigo="recuperou_com_projeto_personalizado",
                    descricao="Recuperou a aprendizagem por meio do projeto personalizado",
                    ordem=5,
                ),
                usuario=self._usuario_admin(),
            )
            motivo_recuperado = preconselho_router.obter_contexto_preconselho_api(
                usuario=self._usuario_professor(professor_id, "Professor Registro"),
            )["motivos_pos_preconselho"]["recuperado"]
            self.assertIn(
                motivo_personalizado["codigo"],
                [item["id"] for item in motivo_recuperado],
            )
            reavaliado = preconselho_router.reavaliar_registro_preconselho_api(
                registro_id=int(salvo["id"]),
                payload=models.PreConselhoReavaliacaoIn(
                    recuperado=True,
                    motivo_ids=[motivo_personalizado["codigo"]],
                    observacao="Recuperou após nova atividade avaliativa.",
                ),
                usuario=self._usuario_professor(professor_id, "Professor Registro"),
            )
            self.assertTrue(reavaliado["pos_preconselho_recuperado"])
            self.assertIn("projeto personalizado", reavaliado["pos_preconselho_motivos"][0])
            self.assertEqual(reavaliado["texto_gerado"], texto_inicial)

            motivo_inativo = preconselho_router.atualizar_status_motivo_reavaliacao_api(
                motivo_id=int(motivo_personalizado["id"]),
                payload=models.PreConselhoMotivoStatusIn(ativo=False),
                usuario=self._usuario_admin(),
            )
            self.assertEqual(int(motivo_inativo["ativo"]), 0)
            contexto_apos_inativar = preconselho_router.obter_contexto_preconselho_api(
                usuario=self._usuario_professor(professor_id, "Professor Registro"),
            )
            self.assertNotIn(
                motivo_personalizado["codigo"],
                [item["id"] for item in contexto_apos_inativar["motivos_pos_preconselho"]["recuperado"]],
            )
            self.assertIn(
                "projeto personalizado",
                database.buscar_registro_pre_conselho_por_id(int(salvo["id"]))["pos_preconselho_motivos"][0],
            )

            conselho_sem_mantidos = preconselho_router.gerar_consolidado_preconselho_api(
                periodo_id=periodo_id,
                turma_id=turma_id,
                disciplina_id=None,
                professor_id=professor_id,
                versao="conselho",
                usuario=self._usuario_coord(coordenador_id, "Coordenadora"),
            )
            self.assertEqual(conselho_sem_mantidos["total_registros"], 0)

            database.atualizar_status_estudante(estudante_id, False)
            self.assertEqual(
                database.contar_registros_pre_conselho_por_professor_periodo(
                    periodo_id,
                    professor_id,
                ),
                {},
            )
            self.assertEqual(
                database.listar_registros_pre_conselho(
                    periodo_id=periodo_id,
                    turma_id=turma_id,
                    professor_usuario_id=professor_id,
                ),
                [],
            )
            self.assertEqual(
                database.listar_estudantes_pre_conselho_painel(
                    periodo_id=periodo_id,
                    turma_id=turma_id,
                    disciplina_id=disciplina_id,
                    professor_usuario_id=professor_id,
                    status="sinalizados",
                ),
                [],
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
                    nome="1º Bimestre 2034",
                    ano_letivo=2034,
                    etapa=1,
                    data_inicio="2034-01-20",
                    data_fim="2034-04-30",
                    status="ABERTO",
                )
            )

            motivo_id = int(database.listar_motivos_pre_conselho()[0]["id"])
            salvo_sem_rav = preconselho_router.salvar_registro_preconselho_api(
                payload=models.PreConselhoRegistroSaveIn(
                    periodo_id=periodo_id,
                    turma_id=turma_id,
                    disciplina_id=disciplina_id,
                    estudante_id=estudante_id,
                    sinalizar=True,
                    motivo_ids=[motivo_id],
                    observacao_professor="precisa revisar os conceitos da unidade",
                    nivel_atencao="medio",
                    estudante_em_rav=True,
                ),
                usuario=self._usuario_professor(professor_colega_id, "Professora Colega"),
            )
            self.assertFalse(salvo_sem_rav["estudante_em_rav"])
            self.assertNotIn("Recuperar para Avançar (RAV)", salvo_sem_rav["texto_gerado"])

            usuario_hibrido = self._usuario_professor(
                professor_hibrido_id,
                "Professor Hibrido",
                acesso_coordenacao=True,
            )
            contexto = preconselho_router.obter_contexto_preconselho_api(usuario=usuario_hibrido)

            self.assertTrue(contexto["pode_consolidar"])
            self.assertTrue(contexto["pode_relatorio"])
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
            self.assertIn("CARLOS", consolidado["texto"])
            self.assertIn("PROFESSORA COLEGA (Biologia Experimental)", consolidado["texto"])

    def test_relatorio_institucional_destaca_turmas_estudantes_e_professores_relacionados(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, preconselho_router, models = _reload_modulos(db_path)
            database.criar_tabelas()

            turma_a_id = int(database.criar_turma("7A", "MATUTINO", 30))
            turma_b_id = int(database.criar_turma("8A", "VESPERTINO", 26))
            matematica_id = int(database.criar_disciplina("Matematica", 5))
            historia_id = int(database.criar_disciplina("Historia", 3))
            ciencias_id = int(database.criar_disciplina("Ciencias", 4))

            ana_id = int(database.criar_estudante("Ana", turma_a_id))
            bruno_id = int(database.criar_estudante("Bruno", turma_a_id))

            professor_principal_id = int(
                database.criar_professor(
                    nome="Professor Principal",
                    email="principal.relatorio@escola.local",
                    senha_hash=database.hash_senha("Senha@123"),
                    data_nascimento="1989-01-10",
                    aulas_semanais=12,
                    turmas_quantidade=1,
                    turmas=["7A"],
                    disciplinas=["Matematica", "Historia"],
                )
            )
            professora_apoio_id = int(
                database.criar_professor(
                    nome="Professora Apoio",
                    email="apoio.relatorio@escola.local",
                    senha_hash=database.hash_senha("Senha@123"),
                    data_nascimento="1990-02-20",
                    aulas_semanais=8,
                    turmas_quantidade=1,
                    turmas=["7A"],
                    disciplinas=["Ciencias"],
                )
            )
            professor_turma_b_id = int(
                database.criar_professor(
                    nome="Professor Turma B",
                    email="turmab.relatorio@escola.local",
                    senha_hash=database.hash_senha("Senha@123"),
                    data_nascimento="1991-03-30",
                    aulas_semanais=6,
                    turmas_quantidade=1,
                    turmas=["8A"],
                    disciplinas=["Ciencias"],
                )
            )
            coordenador_id = int(
                database.criar_coordenador(
                    nome="Coordenadora Relatorio",
                    email="coord.relatorio@escola.local",
                    senha_hash=database.hash_senha("Senha@123"),
                    data_nascimento="1985-04-12",
                )
            )
            periodo_id = int(
                database.criar_periodo_pre_conselho(
                    nome="2º Bimestre 2036",
                    ano_letivo=2036,
                    etapa=2,
                    data_inicio="2036-05-01",
                    data_fim="2036-06-30",
                    status="ABERTO",
                )
            )

            database.criar_atribuicao_docente(professor_principal_id, turma_a_id, matematica_id)
            database.criar_atribuicao_docente(professor_principal_id, turma_a_id, historia_id)
            database.criar_atribuicao_docente(professora_apoio_id, turma_a_id, ciencias_id)
            database.criar_atribuicao_docente(professor_turma_b_id, turma_b_id, ciencias_id)

            motivos = database.listar_motivos_pre_conselho()
            motivo_a = int(motivos[0]["id"])
            motivo_b = int(motivos[1]["id"])

            preconselho_router.salvar_registro_preconselho_api(
                payload=models.PreConselhoRegistroSaveIn(
                    periodo_id=periodo_id,
                    turma_id=turma_a_id,
                    disciplina_id=matematica_id,
                    estudante_id=ana_id,
                    sinalizar=True,
                    motivo_ids=[motivo_a],
                    nivel_atencao="alto",
                ),
                usuario=self._usuario_professor(professor_principal_id, "Professor Principal"),
            )
            preconselho_router.salvar_registro_preconselho_api(
                payload=models.PreConselhoRegistroSaveIn(
                    periodo_id=periodo_id,
                    turma_id=turma_a_id,
                    disciplina_id=historia_id,
                    estudante_id=ana_id,
                    sinalizar=True,
                    motivo_ids=[motivo_b],
                    nivel_atencao="medio",
                ),
                usuario=self._usuario_professor(professor_principal_id, "Professor Principal"),
            )
            preconselho_router.salvar_registro_preconselho_api(
                payload=models.PreConselhoRegistroSaveIn(
                    periodo_id=periodo_id,
                    turma_id=turma_a_id,
                    disciplina_id=ciencias_id,
                    estudante_id=bruno_id,
                    sinalizar=True,
                    motivo_ids=[motivo_a],
                    nivel_atencao="medio",
                    pos_preconselho_recuperado=False,
                ),
                usuario=self._usuario_professor(professora_apoio_id, "Professora Apoio"),
            )

            relatorio = preconselho_router.gerar_relatorio_preconselho_api(
                periodo_id=periodo_id,
                usuario=self._usuario_coord(coordenador_id, "Coordenadora Relatorio"),
            )

            self.assertEqual(relatorio["total_registros"], 3)
            self.assertEqual(relatorio["total_estudantes_sinalizados"], 2)
            self.assertEqual(relatorio["turma_destaque"]["nome"], "7A")
            self.assertEqual(relatorio["turma_destaque"]["total_registros"], 3)
            self.assertEqual(relatorio["professor_destaque"]["nome"], "Professor Principal")
            self.assertEqual(relatorio["professor_destaque"]["total_registros"], 2)
            self.assertTrue(
                any(
                    item["nome"] == "Ana" and int(item["total_registros"]) == 2
                    for item in relatorio["estudantes_destaque"]
                )
            )
            self.assertTrue(
                any("Motivos mais frequentes" in ponto for ponto in relatorio["pontos_criticos"])
            )

            turma_a = next(item for item in relatorio["turmas"] if item["turma_nome"] == "7A")
            turma_b = next(item for item in relatorio["turmas"] if item["turma_nome"] == "8A")

            self.assertEqual(turma_a["professor_destaque"]["nome"], "Professor Principal")
            self.assertEqual(turma_a["total_estudantes_sinalizados"], 2)
            self.assertTrue(
                any(
                    item["nome"] == "Ana" and int(item["total_registros"]) == 2
                    for item in turma_a["estudantes_destaque"]
                )
            )
            self.assertTrue(
                any(
                    item["nome"] == "Professora Apoio" and int(item["total_registros"]) == 1
                    for item in turma_a["professores_relacionados"]
                )
            )

            self.assertEqual(turma_b["total_registros"], 0)
            self.assertTrue(
                any(
                    item["nome"] == "Professor Turma B" and int(item["total_registros"]) == 0
                    for item in turma_b["professores_relacionados"]
                )
            )
            self.assertEqual(
                turma_b["pontos_atencao"],
                ["Nenhum registro lançado para esta turma no período selecionado."],
            )

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
                    nome="1º Bimestre 2033",
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
            self.assertIn("Período fechado", str(ctx.exception.detail))

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
                    nome="1º Bimestre 2035",
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
            self.assertIn("atribuição docente", str(ctx.exception.detail))

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
                    tem_rav=True,
                ),
                usuario=usuario_admin,
            )

            self.assertEqual(periodo["ano_letivo"], 2034)
            self.assertEqual(periodo["etapa"], 2)
            self.assertTrue(periodo["tem_rav"])

            periodo_atualizado = preconselho_router.atualizar_periodo_preconselho_api(
                periodo_id=int(periodo["id"]),
                payload=models.PreConselhoPeriodoUpdateIn(
                    nome="2o Bimestre 2034 - Ajustado",
                    ano_letivo=2034,
                    etapa=2,
                    data_inicio="2034-05-02",
                    data_fim="2034-06-29",
                    tem_rav=False,
                ),
                usuario=usuario_admin,
            )

            self.assertEqual(periodo_atualizado["nome"], "2o Bimestre 2034 - Ajustado")
            self.assertFalse(periodo_atualizado["tem_rav"])

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

    def test_admin_cadastra_e_importa_habilidade_rav_com_mil_caracteres(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, preconselho_router, models = _reload_modulos(db_path)
            database.criar_tabelas()

            turma_id = int(database.criar_turma("1 E.M Z", "VESPERTINO_EM", 30))
            disciplina_id = int(database.criar_disciplina("Lingua Portuguesa", 5))
            periodo = preconselho_router.criar_periodo_preconselho_api(
                payload=models.PreConselhoPeriodoCreateIn(
                    nome="1º Bimestre 2037",
                    ano_letivo=2037,
                    etapa=1,
                    data_inicio="2037-01-20",
                    data_fim="2037-04-30",
                    status="ABERTO",
                    tem_rav=True,
                ),
                usuario=self._usuario_admin(),
            )
            descricao_mil = "A" * 1000

            habilidade = preconselho_router.criar_habilidade_rav_preconselho_api(
                payload=models.PreConselhoRavHabilidadeCreateIn(
                    periodo_id=int(periodo["id"]),
                    disciplina_id=disciplina_id,
                    codigo="MS.TESTE.1000",
                    descricao=descricao_mil,
                    turma_ids=[turma_id],
                    ordem=10,
                ),
                usuario=self._usuario_admin(),
            )

            self.assertEqual(habilidade["descricao"], descricao_mil)
            self.assertEqual(len(habilidade["descricao"]), 1000)

            resultado = preconselho_router.importar_habilidades_rav_preconselho_api(
                payload=models.PreConselhoRavHabilidadeImportIn(
                    periodo="1º Bimestre 2037",
                    habilidades=[
                        models.PreConselhoRavHabilidadeJsonItemIn(
                            codigo="MS.TESTE.IMPORT.1000",
                            texto="B" * 1000,
                            disciplina="Lingua Portuguesa",
                            turma="1 E.M Z",
                        )
                    ],
                ),
                usuario=self._usuario_admin(),
            )

            self.assertEqual(resultado["criadas"], 1)
            self.assertEqual(resultado["ignoradas"], 0)
            self.assertEqual(resultado["erros"], [])


if __name__ == "__main__":
    unittest.main()
