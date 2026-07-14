import tempfile
import unittest
import sqlite3
from pathlib import Path
from unittest.mock import patch

import database
from modules.admin.resources import service
from modules.admin.resources import repository
from modules.admin.resources.schemas import RecursoCreateIn


class AdminResourcesServiceTests(unittest.TestCase):
    def test_listagem_possui_rota_sem_colisao_com_a_pagina(self):
        from modules.admin.resources.router import router

        paths = {route.path for route in router.routes}
        self.assertIn("/admin/recursos/dados", paths)

    @patch("modules.admin.resources.service.repository.criar_recurso", return_value=7)
    def test_cria_recurso_normalizado(self, criar_recurso):
        recurso_id = service.create_resource(
            RecursoCreateIn(nome="  Projetor ", tipo=" Equipamento ", quantidade_itens=2)
        )

        self.assertEqual(recurso_id, 7)
        criar_recurso.assert_called_once_with(
            nome="Projetor",
            tipo="Equipamento",
            descricao="",
            quantidade_itens=2,
            imagem_capa="",
        )

    def test_salva_imagem_com_nome_seguro(self):
        with tempfile.TemporaryDirectory() as directory:
            path = service.save_resource_image(
                "Minha Imagem.JPG",
                "image/jpeg",
                b"imagem",
                Path(directory),
            )

            self.assertTrue(path.startswith("/static/img/resources/minha-imagem-"))
            self.assertEqual(len(list(Path(directory).iterdir())), 1)


class AdminResourcesRepositoryTests(unittest.TestCase):
    def test_crud_modular_e_compatibilidade_legada(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(
            database, "DB_PATH", Path(directory) / "recursos.db"
        ):
            conn = sqlite3.connect(database.DB_PATH)
            conn.execute(
                """CREATE TABLE recursos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT UNIQUE NOT NULL,
                    tipo TEXT NOT NULL,
                    descricao TEXT,
                    quantidade_itens INTEGER,
                    imagem_capa TEXT,
                    ativo INTEGER NOT NULL DEFAULT 1
                )"""
            )
            conn.close()

            recurso_id = repository.criar_recurso("Projetor", "Equipamento", quantidade_itens=2)
            self.assertEqual(database.buscar_recurso_por_id(recurso_id)["nome"], "Projetor")
            self.assertTrue(repository.atualizar_status_recurso(recurso_id, False))
            self.assertEqual(repository.listar_recursos_ativos(), [])
            self.assertEqual(len(database.listar_recursos(incluir_inativos=True)), 1)


if __name__ == "__main__":
    unittest.main()
