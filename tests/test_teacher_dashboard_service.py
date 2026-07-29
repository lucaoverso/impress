import unittest
from datetime import datetime

from modules.scheduling.teacher_dashboard_service import selecionar_proximas_aulas


class TeacherDashboardServiceTest(unittest.TestCase):
    def test_seleciona_aula_em_andamento_e_proxima_aula(self):
        itens = [
            {
                "id": 1,
                "dia_semana": "SEGUNDA",
                "aula_numero": 1,
                "horario_inicio": "07:00",
                "horario_fim": "07:50",
                "turma_nome": "7º A",
                "disciplina_nome": "Matemática",
            },
            {
                "id": 2,
                "dia_semana": "SEGUNDA",
                "aula_numero": 3,
                "horario_inicio": "09:00",
                "horario_fim": "09:50",
                "turma_nome": "8º B",
                "disciplina_nome": "Matemática",
            },
            {
                "id": 3,
                "dia_semana": "TERCA",
                "aula_numero": 1,
                "horario_inicio": "07:00",
                "horario_fim": "07:50",
                "turma_nome": "9º A",
                "disciplina_nome": "Física",
            },
        ]

        aulas = selecionar_proximas_aulas(
            itens,
            agora=datetime(2026, 7, 27, 9, 10),
            limite=2,
        )

        self.assertEqual([item["id"] for item in aulas], [2, 3])
        self.assertTrue(aulas[0]["em_andamento"])
        self.assertEqual(aulas[0]["data_rotulo"], "Hoje")
        self.assertEqual(aulas[1]["data_rotulo"], "Amanhã")


if __name__ == "__main__":
    unittest.main()
