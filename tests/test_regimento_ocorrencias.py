import importlib
import os
import sqlite3
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
                lei_nome="Regimento Interno",
                artigo_numero="76",
                artigo_descricao="Dos deveres do estudante.",
                inciso_numero="VII",
                inciso_descricao="Integrar-se ao processo pedagogico desenvolvido pela unidade escolar.",
            )
            item_2_id = database.criar_regimento_item(
                lei_nome="Regimento Interno",
                artigo_numero="76",
                artigo_descricao="Dos deveres do estudante.",
                inciso_numero="X",
                inciso_descricao="Atender convocacao da Direcao Escolar e Coordenacao Pedagogica.",
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
            self.assertEqual(
                ocorrencia["regimento_itens"][0]["artigo_descricao"],
                "Dos deveres do estudante.",
            )

            database.atualizar_regimento_item(
                item_2_id,
                lei_nome="Regimento Interno",
                artigo_numero="76",
                artigo_descricao="Descricao alterada no artigo master.",
                inciso_numero="X",
                inciso_descricao="Descricao alterada no cadastro master.",
                ativo=True,
            )

            ocorrencia_atualizada = database.buscar_ocorrencia_por_id(ocorrencia_id)
            self.assertEqual(
                ocorrencia_atualizada["regimento_itens"][0]["descricao"],
                "Atender convocacao da Direcao Escolar e Coordenacao Pedagogica.",
            )
            self.assertEqual(
                ocorrencia_atualizada["regimento_itens"][0]["artigo_descricao"],
                "Dos deveres do estudante.",
            )

    def test_listar_ocorrencias_retorna_itens_do_regimento(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database = _reload_database(db_path)
            database.criar_tabelas()

            turma_id = int(database.listar_turmas_ativas()[0]["id"])
            item_id = database.criar_regimento_item(
                lei_nome="ECA",
                artigo_numero="80",
                artigo_descricao="Zelar pelo patrimonio e materiais da unidade escolar.",
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
            self.assertEqual(ocorrencia["regimento_itens"][0]["artigo"], "ECA - Art. 80")

    def test_nao_permite_excluir_item_da_base_legal_vinculado_a_ocorrencia(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database = _reload_database(db_path)
            database.criar_tabelas()

            turma_id = int(database.listar_turmas_ativas()[0]["id"])
            item_id = database.criar_regimento_item(
                lei_nome="ECA",
                artigo_numero="90",
                artigo_descricao="Registro protegido por vinculo de ocorrencia.",
            )
            ocorrencia_id = database.criar_ocorrencia(
                nome_estudante="Estudante Protegido",
                estudante_id=None,
                turma_id=turma_id,
                professor_requerente="Professor Teste",
                professor_requerente_id=None,
                disciplina="Historia",
                data_ocorrencia="2026-03-22",
                aula="4",
                horario_ocorrencia="10:15",
                descricao="Descricao protegida.",
                acao_aplicada="advertencia",
                status="registrado",
            )
            database.salvar_regimento_itens_ocorrencia(ocorrencia_id, [item_id])

            with self.assertRaisesRegex(ValueError, "vinculado a ocorrencias"):
                database.remover_regimento_item(item_id)

    def test_migra_fk_legada_de_regimento_item(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            conn = sqlite3.connect(db_path)
            conn.executescript("""
                CREATE TABLE regimento_itens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    artigo TEXT NOT NULL,
                    descricao TEXT NOT NULL
                );
                CREATE TABLE ocorrencia_regimento_itens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ocorrencia_id INTEGER NOT NULL,
                    regimento_item_id INTEGER,
                    artigo TEXT NOT NULL,
                    descricao TEXT NOT NULL,
                    ordem INTEGER NOT NULL DEFAULT 0,
                    criado_em TEXT NOT NULL DEFAULT (datetime('now')),
                    FOREIGN KEY(regimento_item_id) REFERENCES regimento_itens(id)
                );
            """)
            conn.close()

            database = _reload_database(db_path)
            database.criar_tabelas()

            conn = database.get_connection()
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_key_list(ocorrencia_regimento_itens)")
            fks = [dict(row) for row in cursor.fetchall()]
            self.assertFalse(
                any(
                    row["from"] == "regimento_item_id"
                    and row["table"] == "regimento_itens"
                    for row in fks
                )
            )
            conn.close()

            turma_id = int(database.listar_turmas_ativas()[0]["id"])
            item_id = database.criar_regimento_item(
                lei_nome="Regimento Interno",
                artigo_numero="78",
                artigo_descricao="Norma migrada sem FK legada.",
                inciso_numero="I",
                inciso_descricao="Descricao do inciso migrado.",
            )
            ocorrencia_id = database.criar_ocorrencia(
                nome_estudante="Estudante Migracao",
                estudante_id=None,
                turma_id=turma_id,
                professor_requerente="Professor Teste",
                professor_requerente_id=None,
                disciplina="Portugues",
                data_ocorrencia="2026-03-23",
                aula="2",
                horario_ocorrencia="07:30",
                descricao="Descricao protegida contra FK legada.",
                acao_aplicada="orientacao_verbal",
                status="registrado",
                regimento_item_ids=[item_id],
            )

            ocorrencia = database.buscar_ocorrencia_por_id(ocorrencia_id)
            self.assertEqual(
                [item["regimento_item_id"] for item in ocorrencia["regimento_itens"]],
                [item_id],
            )


if __name__ == "__main__":
    unittest.main()
