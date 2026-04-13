import importlib
import os
import sqlite3
import sys
import tempfile
import unittest

from security.nt_hash import generate_nt_hash


def _reload_modules(db_path: str):
    os.environ["DB_PATH"] = db_path
    os.environ["ENABLE_EMBEDDED_WORKER"] = "0"

    for module_name in (
        "services.auth_service",
        "services.radius_service",
        "auth",
        "ocorrencias_router",
        "database",
        "main",
    ):
        if module_name in sys.modules:
            del sys.modules[module_name]

    database = importlib.import_module("database")
    main = importlib.import_module("main")
    auth_service = importlib.import_module("services.auth_service")
    return database, main, auth_service


class ExclusaoProfessorTest(unittest.TestCase):
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

    def test_migracao_adiciona_coluna_ativo_em_usuarios(self):
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
            conn.execute("""
                INSERT INTO usuarios (nome, email, senha_hash, perfil, cargo, data_nascimento)
                VALUES ('Professor Legado', 'legado@escola.local', 'hash', 'professor', 'PROFESSOR', '1990-01-01')
            """)
            conn.commit()
            conn.close()

            database, _, _ = _reload_modules(db_path)
            database.criar_tabelas()

            conn = database.get_connection()
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(usuarios)")
            colunas = {row["name"] for row in cursor.fetchall()}
            self.assertIn("ativo", colunas)

            cursor.execute("SELECT ativo FROM usuarios WHERE email = ?", ("legado@escola.local",))
            row = cursor.fetchone()
            conn.close()

            self.assertIsNotNone(row)
            self.assertEqual(int(row["ativo"]), 1)

    def test_delete_professor_route_desativa_acesso_e_remove_das_listas(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            database, main, auth_service = _reload_modules(db_path)
            database.criar_tabelas()
            database.criar_usuario_se_nao_existir(
                nome="Administrador",
                email="admin@escola",
                senha_hash=database.hash_senha("admin123"),
                senha_plana="admin123",
                perfil="admin",
                cargo="ADMIN",
            )

            senha_professor = "Senha@123"
            email_professor = "saida@escola.local"
            professor_id = database.criar_professor(
                nome="Professor Saida",
                email=email_professor,
                senha_hash=database.hash_senha(senha_professor),
                nt_hash=generate_nt_hash(senha_professor),
                data_nascimento="1991-05-10",
                aulas_semanais=12,
                turmas_quantidade=2,
                turmas=["6A", "7A"],
                disciplinas=["Matematica"],
            )

            resultado_login = auth_service.autenticar_usuario(email_professor, senha_professor)
            self.assertIsNotNone(resultado_login)
            token_professor = resultado_login[0]
            self.assertIsNotNone(auth_service.validar_token(token_professor))

            resposta = main.excluir_professor_painel(
                professor_id=professor_id,
                usuario={"id": 1, "perfil": "admin", "cargo": "ADMIN"},
            )
            self.assertEqual(resposta["mensagem"], "Professor excluido com sucesso.")

            self.assertIsNone(database.buscar_usuario_por_email(email_professor))
            usuario_inativo = database.buscar_usuario_por_email(
                email_professor,
                incluir_inativos=True,
            )
            self.assertIsNotNone(usuario_inativo)
            self.assertEqual(int(usuario_inativo["ativo"]), 0)

            self.assertIsNone(auth_service.validar_token(token_professor))
            self.assertIsNone(auth_service.autenticar_usuario(email_professor, senha_professor))

            professores_painel = main.listar_professores_painel(
                usuario={"id": 1, "perfil": "admin", "cargo": "ADMIN"},
            )
            emails_painel = {item["email"] for item in professores_painel["professores"]}
            self.assertNotIn(email_professor, emails_painel)

            emails_agendamento = {
                item["email"] for item in database.listar_professores_agendamento()
            }
            self.assertNotIn(email_professor, emails_agendamento)

            emails_ocorrencia = {
                item["email"] for item in database.buscar_professores_ocorrencia("saida")
            }
            self.assertNotIn(email_professor, emails_ocorrencia)


if __name__ == "__main__":
    unittest.main()
