import importlib
import os
import sys
import tempfile
import unittest


def _reload_database(db_path: str):
    os.environ["DB_PATH"] = db_path
    if "database" in sys.modules:
        del sys.modules["database"]
    return importlib.import_module("database")


class RegimentoOcorrenciasTest(unittest.TestCase):
    def setUp(self):
        self._old_db_path = os.environ.get("DB_PATH")

    def tearDown(self):
        if self._old_db_path is None:
            os.environ.pop("DB_PATH", None)
        else:
            os.environ["DB_PATH"] = self._old_db_path

    def test_ocorrencia_preserva_snapshot_dos_itens_do_regimento(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database = _reload_database(db_path)
            database.criar_tabelas()

            turma_id = int(database.listar_turmas_ativas()[0]["id"])
            item_1_id = database.criar_regimento_item(
                "Art. 76 - VII",
                "Integrar-se ao processo pedagogico desenvolvido pela unidade escolar.",
            )
            item_2_id = database.criar_regimento_item(
                "Art. 76 - X",
                "Atender convocacao da Direcao Escolar e Coordenacao Pedagogica.",
            )

            ocorrencia_id = database.criar_ocorrencia(
                nome_estudante="Estudante Teste",
                estudante_id=None,
                turma_id=turma_id,
                professor_requerente="Professor Teste",
                professor_requerente_id=None,
                disciplina="Portugues",
                data_ocorrencia="2026-03-20",
                aula="2",
                horario_ocorrencia="07:30",
                descricao="Descricao da ocorrencia para validacao.",
                acao_aplicada="advertencia",
                status="registrado",
            )

            database.salvar_regimento_itens_ocorrencia(ocorrencia_id, [item_2_id, item_1_id])

            ocorrencia = database.buscar_ocorrencia_por_id(ocorrencia_id)
            self.assertEqual(
                [item["regimento_item_id"] for item in ocorrencia["regimento_itens"]],
                [item_2_id, item_1_id],
            )
            self.assertEqual(
                ocorrencia["regimento_itens"][0]["descricao"],
                "Atender convocacao da Direcao Escolar e Coordenacao Pedagogica.",
            )

            database.atualizar_regimento_item(
                item_2_id,
                "Art. 76 - X",
                "Descricao alterada no cadastro master.",
                True,
            )

            ocorrencia_atualizada = database.buscar_ocorrencia_por_id(ocorrencia_id)
            self.assertEqual(
                ocorrencia_atualizada["regimento_itens"][0]["descricao"],
                "Atender convocacao da Direcao Escolar e Coordenacao Pedagogica.",
            )

    def test_listar_ocorrencias_retorna_itens_do_regimento(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database = _reload_database(db_path)
            database.criar_tabelas()

            turma_id = int(database.listar_turmas_ativas()[0]["id"])
            item_id = database.criar_regimento_item(
                "Art. 80",
                "Zelar pelo patrimonio e materiais da unidade escolar.",
            )
            ocorrencia_id = database.criar_ocorrencia(
                nome_estudante="Outro Estudante",
                estudante_id=None,
                turma_id=turma_id,
                professor_requerente="Professor Teste",
                professor_requerente_id=None,
                disciplina="Historia",
                data_ocorrencia="2026-03-21",
                aula="3",
                horario_ocorrencia="09:15",
                descricao="Nova descricao.",
                acao_aplicada="orientacao_verbal",
                status="registrado",
            )
            database.salvar_regimento_itens_ocorrencia(ocorrencia_id, [item_id])

            ocorrencias = database.listar_ocorrencias()
            ocorrencia = next(item for item in ocorrencias if int(item["id"]) == int(ocorrencia_id))
            self.assertEqual(len(ocorrencia["regimento_itens"]), 1)
            self.assertEqual(ocorrencia["regimento_itens"][0]["artigo"], "Art. 80")


if __name__ == "__main__":
    unittest.main()
