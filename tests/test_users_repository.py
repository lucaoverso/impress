import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from modules.users import repository


class UsersRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "profile.db"
        conn = self._connect()
        conn.executescript(
            """
            CREATE TABLE usuarios (
                id INTEGER PRIMARY KEY, nome TEXT, email TEXT, perfil TEXT,
                cargo TEXT, data_nascimento TEXT, ativo INTEGER
            );
            CREATE TABLE turmas (
                id INTEGER PRIMARY KEY, nome TEXT, turno TEXT, ativo INTEGER
            );
            CREATE TABLE disciplinas (
                id INTEGER PRIMARY KEY, nome TEXT, ativo INTEGER
            );
            CREATE TABLE professores_turmas_disciplinas (
                id INTEGER PRIMARY KEY, professor_usuario_id INTEGER,
                turma_id INTEGER, disciplina_id INTEGER
            );
            CREATE TABLE horarios_escolares (
                id INTEGER PRIMARY KEY, professor_usuario_id INTEGER,
                turma_id INTEGER, disciplina_id INTEGER, ano_letivo INTEGER
            );
            CREATE TABLE estudantes (
                id INTEGER PRIMARY KEY, nome TEXT, turma_id INTEGER,
                possui_necessidade_especial INTEGER, ativo INTEGER
            );
            CREATE TABLE estudante_laudos (
                id INTEGER PRIMARY KEY, estudante_id INTEGER, cid TEXT,
                diagnostico TEXT, observacoes_restritas TEXT,
                recomendacoes_pedagogicas TEXT, ativo INTEGER
            );
            CREATE TABLE estudante_apoios_catalogo (
                id INTEGER PRIMARY KEY, nome TEXT, ativo INTEGER
            );
            CREATE TABLE estudante_laudo_apoios (
                laudo_id INTEGER, apoio_id INTEGER
            );
            CREATE TABLE apc_envios (
                id INTEGER PRIMARY KEY, professor_usuario_id INTEGER,
                turma_id INTEGER, disciplina_id INTEGER,
                arquivo_nome_cliente TEXT, arquivo_nome_original TEXT,
                enviado_em TEXT, review_status TEXT
            );
            CREATE TABLE jobs (
                id INTEGER PRIMARY KEY, usuario_id INTEGER, arquivo TEXT,
                copias INTEGER, paginas_totais INTEGER, criado_em TEXT, status TEXT
            );
            CREATE TABLE recursos (
                id INTEGER PRIMARY KEY, nome TEXT, tipo TEXT
            );
            CREATE TABLE configuracao_aulas (
                id INTEGER PRIMARY KEY, aula_numero INTEGER, ordem_visual INTEGER,
                nome TEXT, horario_inicio TEXT, horario_fim TEXT,
                ativo INTEGER, tipo TEXT
            );
            CREATE TABLE agendamentos (
                id INTEGER PRIMARY KEY, recurso_id INTEGER, usuario_id INTEGER,
                data TEXT, aula TEXT, faixa_global INTEGER, turma TEXT,
                tema_aula TEXT, status TEXT
            );
            """
        )
        conn.executemany(
            "INSERT INTO turmas VALUES (?, ?, ?, 1)",
            [(1, "8º A", "MATUTINO"), (2, "9º B", "MATUTINO")],
        )
        conn.execute("INSERT INTO disciplinas VALUES (1, 'Matemática', 1)")
        conn.executemany(
            "INSERT INTO professores_turmas_disciplinas VALUES (?, ?, ?, 1)",
            [(1, 7, 1), (2, 8, 2)],
        )
        conn.executemany(
            "INSERT INTO estudantes VALUES (?, ?, ?, ?, ?)",
            [
                (1, "Estudante autorizado", 1, 1, 1),
                (2, "Estudante inativo", 1, 1, 0),
                (3, "Outra turma", 2, 1, 1),
            ],
        )
        conn.executemany(
            "INSERT INTO estudante_laudos VALUES (?, ?, ?, ?, ?, ?, 1)",
            [
                (1, 1, "F00", "restrito", "não expor", "Instruções em etapas"),
                (2, 1, "F01", "restrito", "não expor", "Instruções em etapas"),
                (3, 3, "F02", "restrito", "não expor", "Outra recomendação"),
            ],
        )
        conn.execute("INSERT INTO estudante_apoios_catalogo VALUES (1, 'Tempo ampliado', 1)")
        conn.executemany(
            "INSERT INTO estudante_laudo_apoios VALUES (?, 1)",
            [(1,), (2,), (3,)],
        )
        conn.executemany(
            "INSERT INTO apc_envios VALUES (?, 7, 1, 1, ?, ?, ?, 'PENDENTE')",
            [(index, "", f"apc-{index}.pdf", f"2026-01-0{index} 08:00") for index in range(1, 5)],
        )
        conn.executemany(
            "INSERT INTO jobs VALUES (?, 7, ?, 1, 10, ?, 'CONCLUIDO')",
            [(index, f"job-{index}.pdf", f"2026-02-0{index} 08:00") for index in range(1, 5)],
        )
        conn.execute("INSERT INTO recursos VALUES (1, 'Laboratório', 'SALA')")
        conn.executemany(
            "INSERT INTO configuracao_aulas VALUES (?, ?, ?, ?, ?, ?, 1, 'AULA')",
            [
                (1, 1, 1, "1ª aula", "07:30", "08:20"),
                (2, 2, 2, "2ª aula", "08:20", "09:10"),
            ],
        )
        conn.executemany(
            "INSERT INTO agendamentos VALUES (?, 1, 7, ?, ?, ?, '8º A', '', 'ATIVO')",
            [
                (1, "2099-01-02", "1", 1),
                (2, "2099-01-01", "2", 2),
                (3, "2099-01-01", "1", 1),
                (4, "2099-01-03", "1", 1),
            ],
        )
        conn.commit()
        conn.close()
        self.connection_patch = patch(
            "modules.users.repository.get_connection", side_effect=self._connect
        )
        self.connection_patch.start()

    def tearDown(self):
        self.connection_patch.stop()
        self.temp_dir.cleanup()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def test_support_query_is_scoped_active_and_privacy_safe(self):
        rows = repository.list_teacher_student_supports(7, 2026)

        self.assertEqual({row["estudante_nome"] for row in rows}, {"Estudante autorizado"})
        self.assertEqual(len(rows), 2)
        self.assertEqual(
            set(rows[0]),
            {
                "estudante_id",
                "estudante_nome",
                "turma_id",
                "turma_nome",
                "recomendacoes_pedagogicas",
                "apoio_nome",
            },
        )
        serialized = str(rows).lower()
        self.assertNotIn("f00", serialized)
        self.assertNotIn("diagnostico", serialized)
        self.assertNotIn("não expor", serialized)

    def test_recent_activity_queries_order_and_limit_results(self):
        submissions = repository.list_recent_apc_submissions(7)
        jobs = repository.list_recent_print_jobs(7)
        bookings = repository.list_upcoming_bookings(7)

        self.assertEqual([item["id"] for item in submissions], [4, 3, 2])
        self.assertEqual([item["id"] for item in jobs], [4, 3, 2])
        self.assertEqual([item["id"] for item in bookings], [3, 2, 1])


if __name__ == "__main__":
    unittest.main()
