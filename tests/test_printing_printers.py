import sqlite3
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from modules.printing import service


class PrintingPrintersTest(unittest.TestCase):
    def test_normaliza_e_rejeita_nome_cups_invalido(self):
        self.assertEqual(service.normalize_printer_name(" HP_Secretaria "), "HP_Secretaria")
        with self.assertRaises(HTTPException):
            service.normalize_printer_name("HP Secretaria")

    @patch("modules.printing.service.repository.list_printers", return_value=[])
    def test_lista_impressora_do_ambiente_como_fallback(self, _list_printers):
        self.assertEqual(
            service.list_available_printers("HP_PADRAO"),
            [{"id": 0, "name": "HP_PADRAO", "active": 1, "source": "environment"}],
        )

    @patch(
        "modules.printing.service.repository.list_printers",
        return_value=[{"id": 2, "name": "HP_Secretaria", "active": 1}],
    )
    def test_resolve_apenas_impressora_ativa_cadastrada(self, _list_printers):
        self.assertEqual(
            service.resolve_active_printer("hp_secretaria", "OUTRA"),
            "HP_Secretaria",
        )
        with self.assertRaises(HTTPException):
            service.resolve_active_printer("OUTRA", "OUTRA")

    @patch(
        "modules.printing.service.repository.create_printer",
        side_effect=sqlite3.IntegrityError,
    )
    def test_converte_duplicidade_em_erro_de_dominio(self, _create_printer):
        with self.assertRaises(service.PrinterConflictError):
            service.create_registered_printer("HP_Secretaria")

    @patch("modules.printing.service.repository.update_printer_status", return_value=False)
    def test_informa_impressora_inexistente(self, _update_status):
        with self.assertRaises(service.PrinterNotFoundError):
            service.update_registered_printer_status(999, True)


if __name__ == "__main__":
    unittest.main()
