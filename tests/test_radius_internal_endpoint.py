import importlib
import os
import sys
import tempfile
import unittest

from security.nt_hash import generate_nt_hash


def _reload_modules(db_path: str):
    os.environ["DB_PATH"] = db_path

    for module_name in ("services.radius_service", "services.auth_service", "database"):
        if module_name in sys.modules:
            del sys.modules[module_name]

    database = importlib.import_module("database")
    radius_service = importlib.import_module("services.radius_service")
    return radius_service, database


class RadiusInternalServiceTest(unittest.TestCase):
    def setUp(self):
        self._old_db_path = os.environ.get("DB_PATH")

    def tearDown(self):
        if self._old_db_path is None:
            os.environ.pop("DB_PATH", None)
        else:
            os.environ["DB_PATH"] = self._old_db_path

    def test_ensure_nt_hash_service(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "impressao.db")
            radius_service, database = _reload_modules(db_path)
            database.criar_tabelas()

            senha = "Senha@123"
            username = "radius.prof@escola.local"
            database.criar_usuario_se_nao_existir(
                nome="Professor Radius",
                email=username,
                senha_hash=database.hash_senha(senha),
                perfil="professor",
                cargo="PROFESSOR",
            )

            usuario_antes = database.buscar_usuario_por_email(username)
            self.assertFalse(usuario_antes.get("nt_hash"))

            senha_errada = radius_service.ensure_nt_hash_for_radius(username, "SenhaErrada!")
            self.assertFalse(senha_errada)

            sucesso = radius_service.ensure_nt_hash_for_radius(username, senha)
            self.assertTrue(sucesso)

            usuario_depois = database.buscar_usuario_por_email(username)
            self.assertEqual(usuario_depois.get("nt_hash"), generate_nt_hash(senha))


if __name__ == "__main__":
    unittest.main()
