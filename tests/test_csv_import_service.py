import importlib
import os
import sys
import tempfile
import unittest


def _reload_modulos(db_path: str):
    os.environ["DB_PATH"] = db_path
    for nome_modulo in ("database", "services.csv_import_service"):
        if nome_modulo in sys.modules:
            del sys.modules[nome_modulo]
    database = importlib.import_module("database")
    csv_import_service = importlib.import_module("services.csv_import_service")
    return database, csv_import_service


class CsvImportServiceTest(unittest.TestCase):
    def setUp(self):
        self._old_db_path = os.environ.get("DB_PATH")

    def tearDown(self):
        if self._old_db_path is None:
            os.environ.pop("DB_PATH", None)
        else:
            os.environ["DB_PATH"] = self._old_db_path

    def test_importa_estudantes_csv_criando_e_atualizando_sem_duplicar(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, csv_import_service = _reload_modulos(db_path)
            database.criar_tabelas()
            turma_id = database.criar_turma("8 B")

            resultado_inicial = csv_import_service.importar_estudantes_csv(
                ("nome,turma,ativo\nAna Maria Souza,8 B,ativo\nBruno Lima,8 B,inativo\n").encode(
                    "utf-8"
                )
            )

            self.assertEqual(resultado_inicial["criados"], 2)
            self.assertEqual(resultado_inicial["atualizados"], 0)
            self.assertEqual(resultado_inicial["erros"], 0)

            resultado_reenvio = csv_import_service.importar_estudantes_csv(
                ("nome,turma,ativo\nAna Maria Souza,8 B,inativo\nBruno Lima,8 B,ativo\n").encode(
                    "utf-8"
                )
            )

            self.assertEqual(resultado_reenvio["criados"], 0)
            self.assertEqual(resultado_reenvio["atualizados"], 2)
            self.assertEqual(resultado_reenvio["erros"], 0)

            estudantes = database.listar_estudantes(
                incluir_inativos=True,
                turma_id=turma_id,
            )
            self.assertEqual(len(estudantes), 2)
            estudante_ana = next(item for item in estudantes if item["nome"] == "Ana Maria Souza")
            estudante_bruno = next(item for item in estudantes if item["nome"] == "Bruno Lima")
            self.assertEqual(int(estudante_ana["ativo"]), 0)
            self.assertEqual(int(estudante_bruno["ativo"]), 1)

    def test_importa_base_legal_csv_hierarquica_e_atualiza_item_existente(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, csv_import_service = _reload_modulos(db_path)
            database.criar_tabelas()

            resultado_inicial = csv_import_service.importar_base_legal_csv(
                (
                    "lei;artigo_numero;artigo_descricao;inciso_numero;inciso_descricao\n"
                    "Regimento Interno;76;Dos deveres do estudante.;VII;Integrar-se ao processo pedagogico desenvolvido pela unidade escolar.\n"
                ).encode("utf-8")
            )

            self.assertEqual(resultado_inicial["criados"], 1)
            self.assertEqual(resultado_inicial["atualizados"], 0)
            self.assertEqual(resultado_inicial["erros"], 0)

            resultado_reenvio = csv_import_service.importar_base_legal_csv(
                (
                    "lei,artigo_numero,artigo_descricao,inciso_numero,inciso_descricao\n"
                    '"Regimento Interno",76,"Dos deveres do estudante.",VII,"Descricao atualizada para o inciso."\n'
                ).encode("utf-8")
            )

            self.assertEqual(resultado_reenvio["criados"], 0)
            self.assertEqual(resultado_reenvio["atualizados"], 1)
            self.assertEqual(resultado_reenvio["erros"], 0)

            itens = database.listar_regimento_itens(incluir_inativos=True)
            self.assertEqual(len(itens), 2)
            inciso = next(item for item in itens if item["tipo"] == "inciso")
            self.assertEqual(inciso["lei_nome"], "Regimento Interno")
            self.assertEqual(inciso["artigo"], "Regimento Interno - Art. 76, inciso VII")
            self.assertEqual(inciso["descricao"], "Descricao atualizada para o inciso.")

    def test_importa_base_legal_json_hierarquico_sem_repetir_lei_em_cada_item(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, csv_import_service = _reload_modulos(db_path)
            database.criar_tabelas()

            resultado = csv_import_service.importar_base_legal_arquivo(
                (
                    "{"
                    '"lei": "Regimento Escolar",'
                    '"artigos": ['
                    "  {"
                    '    "numero": 76,'
                    '    "descricao": "Sao deveres do estudante.",'
                    '    "incisos": ['
                    "      {"
                    '        "numero": "I",'
                    '        "descricao": "Comparecer pontualmente."'
                    "      },"
                    "      {"
                    '        "numero": "IV",'
                    '        "descricao": "Apresentar-se adequadamente trajado.",'
                    '        "alineas": ['
                    "          {"
                    '            "identificador": "a",'
                    '            "descricao": "Short e bermuda."'
                    "          },"
                    "          {"
                    '            "identificador": "b",'
                    '            "descricao": "Oculos escuros, salvo recomendacao medica."'
                    "          }"
                    "        ]"
                    "      }"
                    "    ]"
                    "  }"
                    "]"
                    "}"
                ).encode("utf-8"),
                nome_arquivo="base_legal.json",
                tipo_conteudo="application/json",
            )

            self.assertEqual(resultado["criados"], 5)
            self.assertEqual(resultado["atualizados"], 0)
            self.assertEqual(resultado["erros"], 0)

            itens = database.listar_regimento_itens(incluir_inativos=True)
            self.assertEqual(len(itens), 5)
            artigo = next(item for item in itens if item["tipo"] == "artigo")
            inciso = next(
                item for item in itens if item["tipo"] == "inciso" and item["inciso_numero"] == "IV"
            )
            alinea = next(
                item
                for item in itens
                if item["tipo"] == "alinea" and item["alinea_identificador"] == "b"
            )
            self.assertEqual(artigo["lei_nome"], "Regimento Escolar")
            self.assertEqual(inciso["artigo"], "Regimento Escolar - Art. 76, inciso IV")
            self.assertEqual(alinea["artigo"], "Regimento Escolar - Art. 76, inciso IV, alinea b")
            self.assertEqual(alinea["descricao"], "Oculos escuros, salvo recomendacao medica.")

    def test_importa_estudantes_csv_com_sucesso_parcial(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, csv_import_service = _reload_modulos(db_path)
            database.criar_tabelas()
            database.criar_turma("9 A")

            resultado = csv_import_service.importar_estudantes_csv(
                (
                    "nome,turma,ativo\nClara Alves,9 A,ativo\nDiego Souza,Turma Inexistente,ativo\n"
                ).encode("utf-8")
            )

            self.assertEqual(resultado["criados"], 1)
            self.assertEqual(resultado["atualizados"], 0)
            self.assertEqual(resultado["erros"], 1)
            self.assertEqual(len(resultado["detalhes_erros"]), 1)
            self.assertIn("Linha 3", resultado["detalhes_erros"][0])

    def test_importa_estudantes_json_por_turma_sem_duplicar(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, csv_import_service = _reload_modulos(db_path)
            database.criar_tabelas()
            turma_id = database.criar_turma("6o Ano A")

            resultado_inicial = csv_import_service.importar_estudantes_arquivo(
                (
                    "{"
                    '"turma": "6o Ano A",'
                    '"turno": "Integral",'
                    '"ano_letivo": 2026,'
                    '"estudantes": ['
                    "  {"
                    '    "matricula": "1428172",'
                    '    "nome": "Adam Jose Marques Machado",'
                    '    "situacao": "Em curso",'
                    '    "faltas": 0'
                    "  },"
                    "  {"
                    '    "matricula": "1474330",'
                    '    "nome": "Bianca Oliveira de Souza",'
                    '    "situacao": "Em curso",'
                    '    "faltas": 0'
                    "  },"
                    "  {"
                    '    "matricula": "1465299",'
                    '    "nome": "Davi Yudi Kimura",'
                    '    "situacao": "Remanejado",'
                    '    "faltas": 0'
                    "  }"
                    "]"
                    "}"
                ).encode("utf-8"),
                nome_arquivo="estudantes.json",
                tipo_conteudo="application/json",
            )

            self.assertEqual(resultado_inicial["criados"], 3)
            self.assertEqual(resultado_inicial["atualizados"], 0)
            self.assertEqual(resultado_inicial["erros"], 0)

            resultado_reenvio = csv_import_service.importar_estudantes_arquivo(
                (
                    "{"
                    '"turma": "6o Ano A",'
                    '"turno": "Integral",'
                    '"ano_letivo": 2026,'
                    '"estudantes": ['
                    "  {"
                    '    "matricula": "1428172",'
                    '    "nome": "Adam Jose Marques Machado",'
                    '    "situacao": "Remanejado",'
                    '    "faltas": 2'
                    "  },"
                    "  {"
                    '    "matricula": "1474330",'
                    '    "nome": "Bianca Oliveira de Souza",'
                    '    "situacao": "Em curso",'
                    '    "faltas": 1'
                    "  },"
                    "  {"
                    '    "matricula": "1465299",'
                    '    "nome": "Davi Yudi Kimura",'
                    '    "situacao": "Em curso",'
                    '    "faltas": 0'
                    "  }"
                    "]"
                    "}"
                ).encode("utf-8"),
                nome_arquivo="estudantes.json",
                tipo_conteudo="application/json",
            )

            self.assertEqual(resultado_reenvio["criados"], 0)
            self.assertEqual(resultado_reenvio["atualizados"], 3)
            self.assertEqual(resultado_reenvio["erros"], 0)

            estudantes = database.listar_estudantes(
                incluir_inativos=True,
                turma_id=turma_id,
            )
            self.assertEqual(len(estudantes), 3)
            estudante_adam = next(
                item for item in estudantes if item["nome"] == "Adam Jose Marques Machado"
            )
            estudante_bianca = next(
                item for item in estudantes if item["nome"] == "Bianca Oliveira de Souza"
            )
            estudante_davi = next(item for item in estudantes if item["nome"] == "Davi Yudi Kimura")
            self.assertEqual(int(estudante_adam["ativo"]), 0)
            self.assertEqual(int(estudante_bianca["ativo"]), 1)
            self.assertEqual(int(estudante_davi["ativo"]), 1)


if __name__ == "__main__":
    unittest.main()
