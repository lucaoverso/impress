import unittest
from unittest.mock import patch

from services.preconselho_consolidado_service import gerar_consolidado_preconselho_service


class PreConselhoConsolidadoServiceTest(unittest.TestCase):
    @patch("services.preconselho_consolidado_service.gerar_texto_consolidado_pre_conselho")
    @patch("services.preconselho_consolidado_service._enriquecer_professores_turma_registros")
    @patch("services.preconselho_consolidado_service.enriquecer_editavel_preconselho")
    @patch("services.preconselho_consolidado_service.listar_registros_pre_conselho")
    @patch("services.preconselho_consolidado_service.resolver_professor_preconselho")
    @patch("services.preconselho_consolidado_service.validar_disciplina_preconselho")
    @patch("services.preconselho_consolidado_service.validar_turma_preconselho")
    @patch("services.preconselho_consolidado_service.validar_periodo_preconselho")
    def test_gera_consolidado_com_filtros(
        self,
        mock_periodo,
        mock_turma,
        mock_disciplina,
        mock_professor,
        mock_listar,
        mock_editavel,
        mock_enriquecer,
        mock_texto,
    ):
        mock_periodo.return_value = {"id": 3, "nome": "1 Bimestre"}
        mock_turma.return_value = {"id": 4, "nome": "7A"}
        mock_disciplina.return_value = {"id": 5, "nome": "Matematica"}
        mock_professor.return_value = {"id": 7, "nome": "Prof Ana"}
        mock_listar.return_value = [{"id": 1}]
        mock_editavel.return_value = [{"id": 1, "editavel": True}]
        mock_enriquecer.return_value = [{"id": 1, "editavel": True, "professores_turma": []}]
        mock_texto.return_value = {
            "total_registros": 1,
            "total_estudantes": 1,
            "motivos_frequentes": [],
            "texto": "texto",
            "itens_agrupados": [],
        }

        resposta = gerar_consolidado_preconselho_service(
            periodo_id=3,
            turma_id=4,
            disciplina_id=5,
            professor_id=7,
            usuario={"id": "9", "cargo": "COORDENADOR"},
        )

        mock_listar.assert_called_once_with(
            periodo_id=3,
            turma_id=4,
            disciplina_id=5,
            professor_usuario_id=7,
        )
        self.assertEqual(resposta["professor_id"], 7)
        self.assertEqual(resposta["total_registros"], 1)


if __name__ == "__main__":
    unittest.main()
