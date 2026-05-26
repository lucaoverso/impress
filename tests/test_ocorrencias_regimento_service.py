import unittest
from types import SimpleNamespace
from unittest.mock import patch

from services.ocorrencias_regimento_service import (
    atualizar_regimento_item_service,
    atualizar_status_regimento_item_service,
    buscar_regimento_item_service,
    criar_regimento_item_service,
    importar_regimento_itens_arquivo_service,
    listar_regimento_itens_service,
    remover_regimento_item_service,
)


class OcorrenciasRegimentoServiceTest(unittest.TestCase):
    @patch("services.ocorrencias_regimento_service.listar_regimento_itens")
    def test_lista_regimento_itens_delega_para_repository(self, mock_listar):
        mock_listar.return_value = [{"id": 1, "artigo": "Art. 10"}]

        resposta = listar_regimento_itens_service(incluir_inativos=False)

        mock_listar.assert_called_once_with(incluir_inativos=False)
        self.assertEqual(resposta[0]["id"], 1)

    @patch("services.ocorrencias_regimento_service.buscar_regimento_item_por_id")
    def test_busca_regimento_item_retorna_lookup_quando_nao_existe(self, mock_buscar):
        mock_buscar.return_value = None

        with self.assertRaisesRegex(LookupError, "Item do regimento nao encontrado."):
            buscar_regimento_item_service(50)

    @patch("services.ocorrencias_regimento_service.buscar_regimento_item_service")
    @patch("services.ocorrencias_regimento_service.criar_regimento_item")
    @patch("services.ocorrencias_regimento_service._normalizar_payload_regimento")
    def test_cria_regimento_item_valida_payload_e_retorna_detalhe(
        self,
        mock_normalizar,
        mock_criar,
        mock_buscar,
    ):
        mock_normalizar.return_value = {
            "lei_nome": "Lei X",
            "artigo_numero": "10",
            "artigo_descricao": "Descricao",
            "inciso_numero": "I",
            "inciso_descricao": "Inciso",
            "alinea_identificador": "a",
            "alinea_descricao": "Alinea",
        }
        mock_criar.return_value = 7
        mock_buscar.return_value = {"id": 7}

        resposta = criar_regimento_item_service(SimpleNamespace())

        self.assertEqual(mock_criar.call_args.kwargs["lei_nome"], "Lei X")
        self.assertEqual(resposta["id"], 7)

    @patch("services.ocorrencias_regimento_service.importar_base_legal_arquivo")
    def test_importa_regimento_arquivo_delega_para_csv_service(self, mock_importar):
        mock_importar.return_value = {"importados": 3}

        resposta = importar_regimento_itens_arquivo_service(
            conteudo=b"{}",
            nome_arquivo="base.json",
            tipo_conteudo="application/json",
        )

        mock_importar.assert_called_once_with(
            b"{}",
            nome_arquivo="base.json",
            tipo_conteudo="application/json",
        )
        self.assertEqual(resposta["importados"], 3)

    @patch("services.ocorrencias_regimento_service.buscar_regimento_item_service")
    @patch("services.ocorrencias_regimento_service.buscar_regimento_item_por_id")
    @patch("services.ocorrencias_regimento_service.atualizar_regimento_item")
    @patch("services.ocorrencias_regimento_service._normalizar_payload_regimento")
    def test_atualiza_regimento_item_retorna_lookup_quando_nao_altera(
        self,
        mock_normalizar,
        mock_atualizar,
        mock_buscar_por_id,
        mock_buscar_service,
    ):
        mock_buscar_service.return_value = {"id": 9}
        mock_normalizar.return_value = {
            "lei_nome": "Lei Y",
            "artigo_numero": "11",
            "artigo_descricao": "Descricao",
            "inciso_numero": None,
            "inciso_descricao": None,
            "alinea_identificador": None,
            "alinea_descricao": None,
        }
        mock_atualizar.return_value = False

        with self.assertRaisesRegex(LookupError, "Item do regimento nao encontrado."):
            atualizar_regimento_item_service(
                regimento_item_id=9,
                payload=SimpleNamespace(ativo=True),
            )

    @patch("services.ocorrencias_regimento_service.atualizar_status_regimento_item")
    def test_atualiza_status_regimento_item_levanta_lookup_quando_nao_encontra(
        self,
        mock_atualizar,
    ):
        mock_atualizar.return_value = False

        with self.assertRaisesRegex(LookupError, "Item do regimento nao encontrado."):
            atualizar_status_regimento_item_service(regimento_item_id=4, ativo=False)

    @patch("services.ocorrencias_regimento_service.remover_regimento_item")
    def test_remove_regimento_item_levanta_lookup_quando_nao_remove(self, mock_remover):
        mock_remover.return_value = False

        with self.assertRaisesRegex(LookupError, "Item do regimento nao encontrado."):
            remover_regimento_item_service(8)


if __name__ == "__main__":
    unittest.main()
