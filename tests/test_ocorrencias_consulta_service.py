import unittest
from unittest.mock import patch

from services.ocorrencias_consulta_service import (
    buscar_estudantes_ocorrencia_service,
    buscar_ocorrencia_service,
    buscar_professores_ocorrencia_service,
    listar_ocorrencias_service,
    listar_opcoes_ocorrencias_service,
)


class OcorrenciasConsultaServiceTest(unittest.TestCase):
    @patch("services.ocorrencias_consulta_service.listar_regimento_itens")
    @patch("services.ocorrencias_consulta_service.listar_alineas")
    @patch("services.ocorrencias_consulta_service.listar_incisos")
    @patch("services.ocorrencias_consulta_service.listar_artigos")
    @patch("services.ocorrencias_consulta_service.listar_leis")
    @patch("services.ocorrencias_consulta_service.listar_disciplinas_ativas")
    @patch("services.ocorrencias_consulta_service.listar_professores_agendamento")
    @patch("services.ocorrencias_consulta_service.listar_turmas_ativas")
    @patch("services.ocorrencias_consulta_service.listar_acoes_aplicadas")
    def test_lista_opcoes_formatadas_no_service(
        self,
        mock_acoes,
        mock_turmas,
        mock_professores,
        mock_disciplinas,
        mock_leis,
        mock_artigos,
        mock_incisos,
        mock_alineas,
        mock_regimento,
    ):
        mock_acoes.return_value = [{"id": "advertencia", "nome": "Advertencia"}]
        mock_turmas.return_value = [{"id": 1, "nome": "7A", "turno": "MATUTINO"}]
        mock_professores.return_value = [{"id": 9, "nome": "Ana", "email": "ana@escola.test"}]
        mock_disciplinas.return_value = [{"id": 3, "nome": "Portugues"}]
        mock_leis.return_value = [{"id": 4, "nome": "Regimento Interno"}]
        mock_artigos.return_value = [{"id": 5, "numero": "76"}]
        mock_incisos.return_value = [{"id": 6, "numero": "VII"}]
        mock_alineas.return_value = []
        mock_regimento.return_value = [{"id": 7, "artigo": "Art. 76 - VII", "lei_nome": "Regimento"}]

        resposta = listar_opcoes_ocorrencias_service()

        self.assertEqual(resposta["status_padrao"], "registrado")
        self.assertEqual(resposta["turmas"][0]["turno_nome"], "Matutino")
        self.assertEqual(resposta["turmas"][0]["faixas_disponiveis"], [1, 2, 3, 4, 5])
        self.assertEqual(resposta["professores"][0]["label"], "Ana (ana@escola.test)")
        self.assertEqual(resposta["disciplinas"][0]["label"], "Portugues")
        self.assertEqual(resposta["regimento_itens"][0]["label"], "Art. 76 - VII")
        mock_regimento.assert_called_once_with(incluir_inativos=True)

    @patch("services.ocorrencias_consulta_service.buscar_professores_ocorrencia")
    def test_busca_professores_formatada_no_service(self, mock_buscar):
        mock_buscar.return_value = [{"id": 1, "nome": "Bruno", "email": ""}]

        resposta = buscar_professores_ocorrencia_service(termo="bru", limite=10)

        mock_buscar.assert_called_once_with(termo="bru", limite=10)
        self.assertEqual(resposta, [{"id": 1, "nome": "Bruno", "email": "", "label": "Bruno"}])

    @patch("services.ocorrencias_consulta_service.buscar_estudantes_ocorrencia")
    def test_busca_estudantes_formatada_no_service(self, mock_buscar):
        mock_buscar.return_value = [{"id": 2, "nome": "Carla", "turma_id": 8, "turma_nome": "8A"}]

        resposta = buscar_estudantes_ocorrencia_service(termo="car", limite=5)

        mock_buscar.assert_called_once_with(termo="car", limite=5)
        self.assertEqual(
            resposta,
            [
                {
                    "id": 2,
                    "nome": "Carla",
                    "turma_id": 8,
                    "turma_nome": "8A",
                    "label": "Carla (8A)",
                }
            ],
        )

    @patch("services.ocorrencias_consulta_service.listar_ocorrencias")
    def test_lista_ocorrencias_delega_para_repository(self, mock_listar):
        mock_listar.return_value = [{"id": 11}]

        resposta = listar_ocorrencias_service(status="registrado", tipo_registro="estudante")

        mock_listar.assert_called_once_with(status="registrado", tipo_registro="estudante")
        self.assertEqual(resposta, [{"id": 11}])

    @patch("services.ocorrencias_consulta_service.buscar_ocorrencia_por_id")
    def test_busca_ocorrencia_retorna_detalhe(self, mock_buscar):
        mock_buscar.return_value = {"id": 12, "nome_estudante": "Daniel"}

        resposta = buscar_ocorrencia_service(12)

        mock_buscar.assert_called_once_with(12)
        self.assertEqual(resposta["nome_estudante"], "Daniel")

    @patch("services.ocorrencias_consulta_service.buscar_ocorrencia_por_id")
    def test_busca_ocorrencia_levanta_erro_quando_nao_existe(self, mock_buscar):
        mock_buscar.return_value = None

        with self.assertRaisesRegex(ValueError, "Ocorrencia nao encontrada."):
            buscar_ocorrencia_service(77)


if __name__ == "__main__":
    unittest.main()
