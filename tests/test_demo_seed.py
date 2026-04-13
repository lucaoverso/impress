import importlib
import os
import sys
import tempfile
import unittest


def _reload_modulos(db_path: str):
    os.environ["DB_PATH"] = db_path
    for nome_modulo in ("database", "db.demo_seed"):
        if nome_modulo in sys.modules:
            del sys.modules[nome_modulo]

    database = importlib.import_module("database")
    demo_seed = importlib.import_module("db.demo_seed")
    return database, demo_seed


class DemoSeedTest(unittest.TestCase):
    def setUp(self):
        self._old_db_path = os.environ.get("DB_PATH")

    def tearDown(self):
        if self._old_db_path is None:
            os.environ.pop("DB_PATH", None)
        else:
            os.environ["DB_PATH"] = self._old_db_path

    def test_seed_demo_popula_banco_sem_duplicar_registros(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, demo_seed = _reload_modulos(db_path)

            resumo_1 = demo_seed.seed_demo_data()
            resumo_2 = demo_seed.seed_demo_data()

            self.assertEqual(resumo_1, resumo_2)
            self.assertEqual(resumo_2["usuarios_demo"], 4)
            self.assertEqual(resumo_2["turmas_demo"], 3)
            self.assertEqual(resumo_2["disciplinas_demo"], 5)
            self.assertEqual(resumo_2["estudantes_demo"], 12)
            self.assertEqual(resumo_2["atribuicoes_demo"], 6)
            self.assertEqual(resumo_2["agendamentos_demo"], 3)
            self.assertEqual(resumo_2["pcpi_demo"], 3)
            self.assertEqual(resumo_2["pre_conselho_demo"], 4)
            self.assertEqual(resumo_2["ocorrencias_demo"], 3)
            self.assertEqual(resumo_2["jobs_demo"], 3)

            conn = database.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(*) AS total
                FROM turmas
                WHERE nome LIKE '%- Demo'
                """
            )
            self.assertEqual(int(cursor.fetchone()["total"]), 3)

            cursor.execute(
                """
                SELECT COUNT(*) AS total
                FROM jobs
                WHERE arquivo LIKE 'demo-%'
                """
            )
            self.assertEqual(int(cursor.fetchone()["total"]), 3)
            conn.close()


if __name__ == "__main__":
    unittest.main()
