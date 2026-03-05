import importlib
import os
import sqlite3
import sys
import tempfile
import unittest

from security.nt_hash import generate_nt_hash


def _reload_modules(db_path: str):
    os.environ["DB_PATH"] = db_path
    for module_name in ("services.auth_service", "database"):
        if module_name in sys.modules:
            del sys.modules[module_name]

    database = importlib.import_module("database")
    auth_service = importlib.import_module("services.auth_service")
    return database, auth_service


class NtHashIntegrationTest(unittest.TestCase):
    def setUp(self):
        self._old_db_path = os.environ.get("DB_PATH")

    def tearDown(self):
        if self._old_db_path is None:
            os.environ.pop("DB_PATH", None)
        else:
            os.environ["DB_PATH"] = self._old_db_path

    def test_generate_nt_hash_known_vector(self):
        self.assertEqual(
            generate_nt_hash("password"),
            "8846f7eaee8fb117ad06bdd830b7586c"
        )

    def test_schema_migration_adds_nt_hash_and_index(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            conn = sqlite3.connect(db_path)
            conn.execute("""
                CREATE TABLE usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    senha_hash TEXT NOT NULL,
                    perfil TEXT NOT NULL,
                    cargo TEXT NOT NULL DEFAULT 'PROFESSOR',
                    data_nascimento TEXT
                )
            """)
            conn.commit()
            conn.close()

            database, _ = _reload_modules(db_path)
            database.criar_tabelas()

            conn = database.get_connection()
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(usuarios)")
            colunas = {row["name"] for row in cursor.fetchall()}
            self.assertIn("nt_hash", colunas)

            cursor.execute("PRAGMA index_list(usuarios)")
            indices = {row["name"] for row in cursor.fetchall()}
            self.assertIn("ix_usuarios_nt_hash", indices)
            conn.close()

    def test_login_preenche_nt_hash_se_ausente(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, auth_service = _reload_modules(db_path)
            database.criar_tabelas()

            senha = "Senha@123"
            database.criar_usuario_se_nao_existir(
                nome="Professor",
                email="professor@escola.local",
                senha_hash=auth_service.hash_senha(senha),
                perfil="professor",
                cargo="PROFESSOR",
            )
            usuario_antes = database.buscar_usuario_por_email("professor@escola.local")
            self.assertFalse(usuario_antes.get("nt_hash"))

            resultado = auth_service.autenticar_usuario("professor@escola.local", senha)
            self.assertIsNotNone(resultado)

            usuario_depois = database.buscar_usuario_por_email("professor@escola.local")
            self.assertEqual(usuario_depois.get("nt_hash"), generate_nt_hash(senha))

    def test_view_radcheck_retorna_apenas_usuarios_com_nt_hash(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, auth_service = _reload_modules(db_path)
            database.criar_tabelas()

            database.criar_usuario(
                nome="Com NT",
                email="com.nt@escola.local",
                senha="Senha@123",
                perfil="professor",
                cargo="PROFESSOR",
            )
            database.criar_usuario_se_nao_existir(
                nome="Sem NT",
                email="sem.nt@escola.local",
                senha_hash=auth_service.hash_senha("Senha@123"),
                perfil="professor",
                cargo="PROFESSOR",
            )

            conn = database.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT username, attribute, op, value FROM radcheck ORDER BY username ASC")
            rows = cursor.fetchall()
            conn.close()

            usernames = [row["username"] for row in rows]
            self.assertIn("com.nt@escola.local", usernames)
            self.assertNotIn("sem.nt@escola.local", usernames)

    def test_atualizar_senha_usuario_sincroniza_nt_hash(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, _ = _reload_modules(db_path)
            database.criar_tabelas()

            database.criar_usuario(
                nome="Coordenador",
                email="coord@escola.local",
                senha="Senha@123",
                perfil="coordenador",
                cargo="COORDENADOR",
            )
            usuario = database.buscar_usuario_por_email("coord@escola.local")

            nova_senha = "NovaSenha@456"
            alterado = database.atualizar_senha_usuario(usuario["id"], nova_senha)
            self.assertTrue(alterado)

            usuario_atualizado = database.buscar_usuario_por_email("coord@escola.local")
            self.assertEqual(usuario_atualizado["senha_hash"], database.hash_senha(nova_senha))
            self.assertEqual(usuario_atualizado["nt_hash"], generate_nt_hash(nova_senha))


if __name__ == "__main__":
    unittest.main()
