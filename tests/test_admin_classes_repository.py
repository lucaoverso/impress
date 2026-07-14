import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database
from modules.admin.classes import repository


class AdminClassesRepositoryTests(unittest.TestCase):
    def test_crud_e_compatibilidade_legada(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(
            database, "DB_PATH", Path(directory) / "turmas.db"
        ):
            conn = sqlite3.connect(database.DB_PATH)
            conn.executescript(
                """
                CREATE TABLE turmas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT UNIQUE NOT NULL,
                    turno TEXT,
                    aula_inicial INTEGER,
                    aula_final INTEGER,
                    quantidade_estudantes INTEGER,
                    ativo INTEGER NOT NULL DEFAULT 1,
                    criado_em TEXT
                );
                CREATE TABLE horarios_escolares (
                    id INTEGER PRIMARY KEY,
                    turma_id INTEGER,
                    aula_numero INTEGER,
                    faixa_global INTEGER
                );
                """
            )
            conn.close()

            turma_id = repository.criar_turma("7º A", "MATUTINO", 30)
            self.assertEqual(database.buscar_turma_por_id(turma_id)["aula_final"], 5)
            self.assertTrue(database.atualizar_turma_dados(turma_id, "INTEGRAL", 31, 1, 9))
            self.assertEqual(repository.buscar_turma_por_nome("7º a")["quantidade_estudantes"], 31)
            self.assertTrue(repository.atualizar_status_turma(turma_id, False))
            self.assertEqual(repository.listar_turmas_ativas(), [])


if __name__ == "__main__":
    unittest.main()
