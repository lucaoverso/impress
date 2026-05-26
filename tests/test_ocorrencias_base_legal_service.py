import unittest
from unittest.mock import patch

from services.ocorrencias_base_legal_service import (
    atualizar_alinea_service,
    atualizar_artigo_service,
    atualizar_inciso_service,
    atualizar_lei_service,
    buscar_lei_service,
    criar_alinea_service,
    criar_artigo_service,
    criar_inciso_service,
    criar_lei_service,
    listar_artigos_service,
    listar_leis_service,
    remover_alinea_service,
    remover_lei_service,
)


class OcorrenciasBaseLegalServiceTest(unittest.TestCase):
    @patch("services.ocorrencias_base_legal_service.listar_leis")
    def test_lista_leis_delega_para_repository(self, mock_listar):
        mock_listar.return_value = [{"id": 1, "nome": "Regimento"}]

        resposta = listar_leis_service()

        mock_listar.assert_called_once_with()
        self.assertEqual(resposta[0]["nome"], "Regimento")

    @patch("services.ocorrencias_base_legal_service.buscar_lei_por_id")
    def test_busca_lei_levanta_lookup_quando_nao_existe(self, mock_buscar):
        mock_buscar.return_value = None

        with self.assertRaisesRegex(LookupError, "Lei nao encontrada."):
            buscar_lei_service(99)

    @patch("services.ocorrencias_base_legal_service.buscar_lei_por_id")
    @patch("services.ocorrencias_base_legal_service.criar_lei")
    def test_cria_lei_valida_e_retorna_registro(self, mock_criar, mock_buscar):
        mock_criar.return_value = 4
        mock_buscar.return_value = {"id": 4, "nome": "Lei X"}

        resposta = criar_lei_service(nome="Lei X")

        mock_criar.assert_called_once_with(nome="Lei X")
        self.assertEqual(resposta["id"], 4)

    @patch("services.ocorrencias_base_legal_service.buscar_artigo_por_id")
    @patch("services.ocorrencias_base_legal_service.buscar_lei_por_id")
    @patch("services.ocorrencias_base_legal_service.atualizar_artigo")
    def test_atualiza_artigo_validando_dependencias(
        self,
        mock_atualizar,
        mock_buscar_lei,
        mock_buscar_artigo,
    ):
        mock_buscar_artigo.side_effect = [
            {"id": 7, "lei_id": 2, "numero": "10"},
            {"id": 7, "lei_id": 2, "numero": "11"},
        ]
        mock_buscar_lei.return_value = {"id": 2, "nome": "Lei"}
        mock_atualizar.return_value = True

        resposta = atualizar_artigo_service(
            artigo_id=7,
            lei_id=2,
            numero="11",
            descricao="Descricao atualizada",
        )

        mock_atualizar.assert_called_once_with(
            artigo_id=7,
            lei_id=2,
            numero="11",
            descricao="Descricao atualizada",
        )
        self.assertEqual(resposta["id"], 7)

    @patch("services.ocorrencias_base_legal_service.buscar_artigo_por_id")
    @patch("services.ocorrencias_base_legal_service.criar_inciso")
    def test_cria_inciso_rejeita_artigo_inexistente(self, mock_criar, mock_buscar_artigo):
        mock_buscar_artigo.return_value = None

        with self.assertRaisesRegex(LookupError, "Artigo nao encontrado."):
            criar_inciso_service(artigo_id=15, numero="I", descricao="Descricao")

        mock_criar.assert_not_called()

    @patch("services.ocorrencias_base_legal_service.buscar_inciso_por_id")
    @patch("services.ocorrencias_base_legal_service.criar_alinea")
    def test_cria_alinea_rejeita_identificador_vazio(self, mock_criar, mock_buscar_inciso):
        mock_buscar_inciso.return_value = {"id": 3, "numero": "I"}

        with self.assertRaisesRegex(ValueError, "Identificador da alinea e obrigatorio."):
            criar_alinea_service(inciso_id=3, identificador=" ", descricao="Descricao")

        mock_criar.assert_not_called()

    @patch("services.ocorrencias_base_legal_service.buscar_alinea_por_id")
    @patch("services.ocorrencias_base_legal_service.atualizar_alinea")
    @patch("services.ocorrencias_base_legal_service.buscar_inciso_por_id")
    def test_atualiza_alinea_retorna_lookup_se_repository_nao_altera(
        self,
        mock_buscar_inciso,
        mock_atualizar,
        mock_buscar_alinea,
    ):
        mock_buscar_alinea.return_value = {"id": 8, "inciso_id": 4}
        mock_buscar_inciso.return_value = {"id": 4}
        mock_atualizar.return_value = False

        with self.assertRaisesRegex(LookupError, "Alinea nao encontrada."):
            atualizar_alinea_service(
                alinea_id=8,
                inciso_id=4,
                identificador="a",
                descricao="Descricao",
            )

    @patch("services.ocorrencias_base_legal_service.remover_lei")
    def test_remove_lei_retorna_lookup_quando_repository_nao_remove(self, mock_remover):
        mock_remover.return_value = False

        with self.assertRaisesRegex(LookupError, "Lei nao encontrada."):
            remover_lei_service(3)

    @patch("services.ocorrencias_base_legal_service.remover_alinea")
    def test_remove_alinea_delega_quando_sucesso(self, mock_remover):
        mock_remover.return_value = True

        remover_alinea_service(9)

        mock_remover.assert_called_once_with(9)

    @patch("services.ocorrencias_base_legal_service.listar_artigos")
    def test_lista_artigos_aceita_filtro_de_lei(self, mock_listar):
        mock_listar.return_value = [{"id": 1, "lei_id": 2}]

        resposta = listar_artigos_service(lei_id=2)

        mock_listar.assert_called_once_with(lei_id=2)
        self.assertEqual(resposta[0]["lei_id"], 2)

    @patch("services.ocorrencias_base_legal_service.buscar_lei_por_id")
    @patch("services.ocorrencias_base_legal_service.atualizar_lei")
    def test_atualiza_lei_rejeita_nome_vazio(self, mock_atualizar, mock_buscar):
        mock_buscar.return_value = {"id": 1, "nome": "Lei Atual"}

        with self.assertRaisesRegex(ValueError, "Nome da lei e obrigatorio."):
            atualizar_lei_service(lei_id=1, nome=" ")

        mock_atualizar.assert_not_called()


if __name__ == "__main__":
    unittest.main()
