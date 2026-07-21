import importlib
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from modules.scheduling import repository


class SchedulingRepositoryIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "scheduling.db"
        self.database = importlib.import_module("database")
        self.db_patch = patch.object(self.database, "DB_PATH", self.db_path)
        self.db_patch.start()
        self.database.criar_tabelas()

        with closing(self.database.get_connection()) as conn:
            self.user_id = conn.execute(
                """INSERT INTO usuarios (nome, email, senha_hash, perfil, cargo, ativo)
                   VALUES ('Professora', 'prof@escola', 'hash', 'professor', 'PROFESSOR', 1)"""
            ).lastrowid
            self.resource_id = conn.execute(
                """INSERT INTO recursos (nome, tipo, quantidade_itens, ativo)
                   VALUES ('Projetor', 'Equipamento', 2, 1)"""
            ).lastrowid
            conn.commit()

    def tearDown(self):
        self.db_patch.stop()
        self.temp_dir.cleanup()

    def test_reservation_lifecycle_uses_real_sql(self):
        reservation_id = repository.create_reservation(
            recurso_id=self.resource_id,
            usuario_id=self.user_id,
            data="2099-01-10",
            turno="MATUTINO",
            aula="1",
            faixa_global=1,
            turma="7 Ano A",
            tema_aula="Planejamento",
        )

        self.assertEqual(
            repository.count_active_reservations_in_slot(
                self.resource_id, "2099-01-10", 1
            ),
            1,
        )
        [reservation] = repository.list_reservations(recurso_id=self.resource_id)
        self.assertEqual(reservation.id, reservation_id)
        self.assertEqual(reservation.professor_nome, "Professora")
        self.assertTrue(repository.cancel_reservation(reservation_id))
        self.assertEqual(repository.list_reservations(), [])

    def test_lesson_configuration_crud_uses_real_sql(self):
        created = repository.create_lesson_configuration(
            visual_order=1,
            entry_type="aula",
            lesson_number=1,
            name="Primeira aula",
            start_time="07:00",
            end_time="07:50",
        )
        updated = repository.update_lesson_configuration(
            configuration_id=created["id"],
            visual_order=2,
            entry_type="intervalo",
            lesson_number=None,
            name="Intervalo",
            start_time="07:50",
            end_time="08:00",
            active=False,
        )

        self.assertEqual(updated["tipo"], "INTERVALO")
        self.assertFalse(updated["ativo"])
        self.assertEqual(repository.list_lesson_configurations(include_inactive=False), [])


if __name__ == "__main__":
    unittest.main()
