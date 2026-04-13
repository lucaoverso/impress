import importlib
import os
import sys
import tempfile
import unittest


def _reload_modulos(db_path: str):
    os.environ["DB_PATH"] = db_path
    for nome_modulo in ("database", "db.schema_migrations"):
        if nome_modulo in sys.modules:
            del sys.modules[nome_modulo]

    database = importlib.import_module("database")
    schema_migrations = importlib.import_module("db.schema_migrations")
    return database, schema_migrations


class SchemaMigrationsTest(unittest.TestCase):
    def setUp(self):
        self._old_db_path = os.environ.get("DB_PATH")

    def tearDown(self):
        if self._old_db_path is None:
            os.environ.pop("DB_PATH", None)
        else:
            os.environ["DB_PATH"] = self._old_db_path

    def test_criar_tabelas_registra_todas_as_migrations(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, schema_migrations = _reload_modulos(db_path)

            database.criar_tabelas()

            conn = database.get_connection()
            try:
                aplicadas = schema_migrations.get_applied_migration_names(conn)
            finally:
                conn.close()

            self.assertEqual(aplicadas, schema_migrations.list_migration_names())

    def test_criar_tabelas_nao_duplica_historico_de_migrations(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, schema_migrations = _reload_modulos(db_path)

            database.criar_tabelas()
            database.criar_tabelas()

            status = schema_migrations.get_migration_status(db_path)
            self.assertEqual(status["pending"], [])
            self.assertEqual(status["applied"], schema_migrations.list_migration_names())


if __name__ == "__main__":
    unittest.main()
