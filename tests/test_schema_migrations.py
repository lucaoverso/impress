import importlib
import importlib.util
import os
from pathlib import Path
import sqlite3
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


def _load_migration_module(filename: str):
    migration_path = Path(__file__).resolve().parents[1] / "migrations" / filename
    spec = importlib.util.spec_from_file_location(f"test_migration_{migration_path.stem}", migration_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


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

    def test_migration_20260613_remove_colisao_legada_antes_de_globalizar_horario(self):
        migration = _load_migration_module("20260613_create_global_schedule_config.py")
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE turmas (
                    id INTEGER PRIMARY KEY,
                    turno TEXT NOT NULL,
                    aula_inicial INTEGER NOT NULL DEFAULT 1,
                    aula_final INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE horarios_escolares (
                    id INTEGER PRIMARY KEY,
                    ano_letivo INTEGER NOT NULL,
                    turma_id INTEGER NOT NULL,
                    disciplina_id INTEGER NOT NULL,
                    professor_usuario_id INTEGER NOT NULL,
                    dia_semana TEXT NOT NULL,
                    aula_numero INTEGER NOT NULL DEFAULT 1,
                    faixa_global INTEGER NOT NULL DEFAULT 0,
                    criado_em TEXT NOT NULL DEFAULT '',
                    atualizado_em TEXT NOT NULL DEFAULT ''
                )
                """
            )
            cursor.execute(
                """
                CREATE UNIQUE INDEX idx_horarios_escolares_turma_slot
                ON horarios_escolares(ano_letivo, turma_id, dia_semana, aula_numero)
                """
            )
            cursor.execute(
                """
                INSERT INTO turmas (id, turno, aula_inicial, aula_final)
                VALUES (1, 'VESPERTINO', 6, 10)
                """
            )
            cursor.execute(
                """
                INSERT INTO horarios_escolares (
                    id,
                    ano_letivo,
                    turma_id,
                    disciplina_id,
                    professor_usuario_id,
                    dia_semana,
                    aula_numero,
                    faixa_global,
                    criado_em,
                    atualizado_em
                )
                VALUES (1, 2026, 1, 11, 21, 'SEGUNDA', 4, 9, '2026-06-13 09:00:00', '2026-06-13 09:00:00')
                """
            )
            cursor.execute(
                """
                INSERT INTO horarios_escolares (
                    id,
                    ano_letivo,
                    turma_id,
                    disciplina_id,
                    professor_usuario_id,
                    dia_semana,
                    aula_numero,
                    faixa_global,
                    criado_em,
                    atualizado_em
                )
                VALUES (2, 2026, 1, 12, 22, 'SEGUNDA', 9, 9, '2026-06-13 10:00:00', '2026-06-13 10:00:00')
                """
            )
            conn.commit()

            migration.upgrade(conn)

            rows = conn.execute(
                """
                SELECT id, aula_numero, faixa_global, disciplina_id, professor_usuario_id
                FROM horarios_escolares
                ORDER BY id ASC
                """
            ).fetchall()
        finally:
            conn.close()

        self.assertEqual(len(rows), 1)
        self.assertEqual(int(rows[0]["id"]), 2)
        self.assertEqual(int(rows[0]["aula_numero"]), 9)
        self.assertEqual(int(rows[0]["faixa_global"]), 9)
        self.assertEqual(int(rows[0]["disciplina_id"]), 12)
        self.assertEqual(int(rows[0]["professor_usuario_id"]), 22)

    def test_migration_20260613_resolve_colisao_transitoria_durante_update(self):
        migration = _load_migration_module("20260613_create_global_schedule_config.py")
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE turmas (
                    id INTEGER PRIMARY KEY,
                    turno TEXT NOT NULL,
                    aula_inicial INTEGER NOT NULL DEFAULT 1,
                    aula_final INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE horarios_escolares (
                    id INTEGER PRIMARY KEY,
                    ano_letivo INTEGER NOT NULL,
                    turma_id INTEGER NOT NULL,
                    disciplina_id INTEGER NOT NULL,
                    professor_usuario_id INTEGER NOT NULL,
                    dia_semana TEXT NOT NULL,
                    aula_numero INTEGER NOT NULL DEFAULT 1,
                    faixa_global INTEGER NOT NULL DEFAULT 0,
                    criado_em TEXT NOT NULL DEFAULT '',
                    atualizado_em TEXT NOT NULL DEFAULT ''
                )
                """
            )
            cursor.execute(
                """
                CREATE UNIQUE INDEX idx_horarios_escolares_turma_slot
                ON horarios_escolares(ano_letivo, turma_id, dia_semana, aula_numero)
                """
            )
            cursor.execute(
                """
                INSERT INTO turmas (id, turno, aula_inicial, aula_final)
                VALUES (1, 'VESPERTINO', 6, 10)
                """
            )
            cursor.execute(
                """
                INSERT INTO horarios_escolares (
                    id,
                    ano_letivo,
                    turma_id,
                    disciplina_id,
                    professor_usuario_id,
                    dia_semana,
                    aula_numero,
                    faixa_global,
                    criado_em,
                    atualizado_em
                )
                VALUES (1, 2026, 1, 11, 21, 'SEGUNDA', 0, 1, '2026-06-13 09:00:00', '2026-06-13 09:00:00')
                """
            )
            cursor.execute(
                """
                INSERT INTO horarios_escolares (
                    id,
                    ano_letivo,
                    turma_id,
                    disciplina_id,
                    professor_usuario_id,
                    dia_semana,
                    aula_numero,
                    faixa_global,
                    criado_em,
                    atualizado_em
                )
                VALUES (2, 2026, 1, 12, 22, 'SEGUNDA', 1, 2, '2026-06-13 10:00:00', '2026-06-13 10:00:00')
                """
            )
            conn.commit()

            migration.upgrade(conn)

            rows = conn.execute(
                """
                SELECT id, aula_numero, faixa_global
                FROM horarios_escolares
                ORDER BY id ASC
                """
            ).fetchall()
        finally:
            conn.close()

        self.assertEqual([(1, 1, 1), (2, 2, 2)], [(int(row["id"]), int(row["aula_numero"]), int(row["faixa_global"])) for row in rows])


if __name__ == "__main__":
    unittest.main()
