import unittest
from unittest.mock import patch

from modules.printing.service import list_formatted_print_classes


class PrintingServiceTest(unittest.TestCase):
    def test_list_formatted_print_classes_uses_active_student_count_with_registered_students(self):
        turmas = [
            {
                "id": 1,
                "nome": "6 Ano A",
                "turno": "matutino",
                "quantidade_estudantes": 35,
            },
            {
                "id": 2,
                "nome": "7 Ano B",
                "turno": "vespertino",
                "quantidade_estudantes": 28,
            },
        ]

        with patch("modules.printing.repository.list_active_classes", return_value=turmas), patch(
            "modules.printing.repository.count_active_students_by_class",
            return_value={1: 2},
        ):
            resultado = list_formatted_print_classes()

        self.assertEqual(resultado[0]["quantidade_estudantes"], 2)
        self.assertEqual(resultado[1]["quantidade_estudantes"], 28)
        self.assertEqual(resultado[0]["turno"], "MATUTINO")

    def test_list_formatted_print_classes_keeps_zero_when_registered_students_are_inactive(self):
        turmas = [
            {
                "id": 1,
                "nome": "8 Ano C",
                "turno": "vespertino",
                "quantidade_estudantes": 30,
            },
        ]

        with patch("modules.printing.repository.list_active_classes", return_value=turmas), patch(
            "modules.printing.repository.count_active_students_by_class",
            return_value={1: 0},
        ):
            resultado = list_formatted_print_classes()

        self.assertEqual(resultado[0]["quantidade_estudantes"], 0)


if __name__ == "__main__":
    unittest.main()
