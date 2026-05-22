import unittest
from unittest.mock import patch

from services.preconselho_relatorio_service import gerar_relatorio_preconselho_service


class PreConselhoRelatorioServiceTest(unittest.TestCase):
    @patch("services.preconselho_relatorio_service._mapa_corpo_docente_por_turmas")
    @patch("services.preconselho_relatorio_service.listar_turmas_ativas")
    @patch("services.preconselho_relatorio_service.listar_niveis_atencao_pre_conselho")
    @patch("services.preconselho_relatorio_service.enriquecer_editavel_preconselho")
    @patch("services.preconselho_relatorio_service.listar_registros_pre_conselho")
    @patch("services.preconselho_relatorio_service.validar_periodo_preconselho")
    def test_gera_relatorio_resumo(
        self,
        mock_periodo,
        mock_listar_registros,
        mock_editavel,
        mock_niveis,
        mock_turmas,
        mock_mapa_docente,
    ):
        mock_periodo.return_value = {"id": 3, "nome": "2 Bimestre"}
        mock_listar_registros.return_value = [{"id": 1}]
        mock_editavel.return_value = [
            {
                "id": 1,
                "turma_id": 4,
                "turma_nome": "7A",
                "estudante_id": 9,
                "estudante_nome": "Ana",
                "professor_id": 7,
                "professor_nome": "Prof Ana",
                "disciplina_nome": "Matematica",
                "nivel_atencao": "alto",
                "motivos": [{"descricao": "Faltas"}],
                "pos_preconselho_recuperado": False,
            }
        ]
        mock_niveis.return_value = [{"id": "alto", "nome": "Alto"}]
        mock_turmas.return_value = [{"id": 4, "nome": "7A", "turno": "M", "quantidade_estudantes": 30}]
        mock_mapa_docente.return_value = {4: {"nomes": ["Prof Ana"], "corpo_docente": [{"professor_nome": "Prof Ana", "disciplinas": ["Matematica"]}]}}

        resposta = gerar_relatorio_preconselho_service(
            periodo_id=3,
            usuario={"id": "1", "cargo": "COORDENADOR"},
        )

        self.assertEqual(resposta["total_registros"], 1)
        self.assertEqual(resposta["total_estudantes_sinalizados"], 1)
        self.assertEqual(resposta["turma_destaque"]["nome"], "7A")
        self.assertEqual(resposta["professor_destaque"]["nome"], "Prof Ana")


if __name__ == "__main__":
    unittest.main()
