import importlib.util
from pathlib import Path
import sqlite3
import unittest


def _load_migration():
    path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "20260615_repair_global_schedule_config.py"
    )
    spec = importlib.util.spec_from_file_location("test_schedule_repair_migration", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ScheduleRepairMigrationTest(unittest.TestCase):
    def test_repara_grade_vazia_e_janela_vespertina(self):
        migration = _load_migration()
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        try:
            conn.executescript(
                """
                CREATE TABLE configuracao_aulas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ordem_visual INTEGER NOT NULL,
                    tipo TEXT NOT NULL,
                    aula_numero INTEGER,
                    nome TEXT NOT NULL,
                    horario_inicio TEXT NOT NULL,
                    horario_fim TEXT NOT NULL,
                    ativo INTEGER NOT NULL DEFAULT 1
                );
                CREATE TABLE turmas (
                    id INTEGER PRIMARY KEY,
                    turno TEXT NOT NULL,
                    aula_inicial INTEGER NOT NULL,
                    aula_final INTEGER NOT NULL
                );
                CREATE TABLE horarios_escolares (
                    id INTEGER PRIMARY KEY,
                    aula_numero INTEGER NOT NULL,
                    faixa_global INTEGER NOT NULL
                );
                INSERT INTO turmas VALUES (1, 'VESPERTINO', 1, 5);
                INSERT INTO turmas VALUES (2, 'VESPERTINO_EM', 1, 5);
                INSERT INTO turmas VALUES (3, '', 1, 5);
                INSERT INTO horarios_escolares VALUES (1, 6, 6);
                """
            )

            migration.upgrade(conn)
            migration.upgrade(conn)

            aulas = conn.execute(
                """
                SELECT aula_numero
                FROM configuracao_aulas
                WHERE tipo = 'AULA'
                ORDER BY aula_numero
                """
            ).fetchall()
            turmas = conn.execute(
                "SELECT id, aula_inicial, aula_final FROM turmas ORDER BY id"
            ).fetchall()
        finally:
            conn.close()

        self.assertEqual([int(row["aula_numero"]) for row in aulas], list(range(1, 12)))
        self.assertEqual(
            [(int(row["aula_inicial"]), int(row["aula_final"])) for row in turmas],
            [(6, 10), (6, 11), (1, 5)],
        )


if __name__ == "__main__":
    unittest.main()
