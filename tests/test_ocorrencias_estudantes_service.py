import unittest
from unittest.mock import patch

from services.ocorrencias_estudantes_service import (
    atualizar_estudante_service,
    atualizar_status_estudante_service,
    buscar_estudante_service,
    criar_estudante_service,
    importar_estudantes_arquivo_service,
    listar_estudantes_service,
    remover_estudante_service,
)


class OcorrenciasEstudantesServiceTest(unittest.TestCase):
    @patch("services.ocorrencias_estudantes_service.buscar_turma_por_id")
    @patch("services.ocorrencias_estudantes_service.listar_estudantes")
    def test_lista_estudantes_valida_turma_e_delega(
        self,
        mock_listar,
        mock_buscar_turma,
    ):
        mock_buscar_turma.return_value = {"id": 4, "nome": "8A"}
        mock_listar.return_value = [{"id": 1, "nome": "Ana"}]

        resposta = listar_estudantes_service(nome=" Ana ", turma_id=4, incluir_inativos=False)

        mock_listar.assert_called_once_with(
            incluir_inativos=False,
            nome="Ana",
            turma_id=4,
        )
        self.assertEqual(resposta[0]["id"], 1)

    @patch("services.ocorrencias_estudantes_service.buscar_estudante_por_id")
    def test_busca_estudante_retorna_lookup_quando_nao_existe(self, mock_buscar):
        mock_buscar.return_value = None

        with self.assertRaisesRegex(LookupError, "Estudante nao encontrado."):
            buscar_estudante_service(20)

    @patch("services.ocorrencias_estudantes_service.buscar_estudante_service")
    @patch("services.ocorrencias_estudantes_service.criar_estudante")
    @patch("services.ocorrencias_estudantes_service.buscar_turma_por_id")
    def test_cria_estudante_valida_turma_e_retorna_detalhe(
        self,
        mock_buscar_turma,
        mock_criar,
        mock_buscar_estudante,
    ):
        mock_buscar_turma.return_value = {"id": 3}
        mock_criar.return_value = 9
        mock_buscar_estudante.return_value = {"id": 9, "nome": "Bruno"}

        resposta = criar_estudante_service(nome="Bruno", turma_id=3)

        mock_criar.assert_called_once_with(nome="Bruno", turma_id=3, ativo=True)
        self.assertEqual(resposta["id"], 9)

    @patch("services.ocorrencias_estudantes_service.importar_estudantes_arquivo")
    def test_importa_estudantes_delega_para_csv_service(self, mock_importar):
        mock_importar.return_value = {"importados": 5}

        resposta = importar_estudantes_arquivo_service(
            conteudo=b"{}",
            nome_arquivo="estudantes.json",
            tipo_conteudo="application/json",
        )

        mock_importar.assert_called_once_with(
            b"{}",
            nome_arquivo="estudantes.json",
            tipo_conteudo="application/json",
        )
        self.assertEqual(resposta["importados"], 5)

    @patch("services.ocorrencias_estudantes_service.buscar_estudante_service")
    @patch("services.ocorrencias_estudantes_service.atualizar_estudante")
    @patch("services.ocorrencias_estudantes_service.buscar_turma_por_id")
    def test_atualiza_estudante_retorna_lookup_quando_repository_nao_altera(
        self,
        mock_buscar_turma,
        mock_atualizar,
        mock_buscar_estudante,
    ):
        mock_buscar_estudante.return_value = {"id": 7, "nome": "Carlos"}
        mock_buscar_turma.return_value = {"id": 2}
        mock_atualizar.return_value = False

        with self.assertRaisesRegex(LookupError, "Estudante nao encontrado."):
            atualizar_estudante_service(
                estudante_id=7,
                nome="Carlos",
                turma_id=2,
                ativo=True,
            )

    @patch("services.ocorrencias_estudantes_service.atualizar_status_estudante")
    def test_atualiza_status_retorna_lookup_quando_nao_encontra(self, mock_atualizar):
        mock_atualizar.return_value = False

        with self.assertRaisesRegex(LookupError, "Estudante nao encontrado."):
            atualizar_status_estudante_service(estudante_id=5, ativo=False)

    @patch("services.ocorrencias_estudantes_service.remover_estudante")
    def test_remove_estudante_retorna_qtd_desvinculada(self, mock_remover):
        mock_remover.return_value = (True, 3)

        resposta = remover_estudante_service(8)

        mock_remover.assert_called_once_with(8)
        self.assertEqual(resposta, 3)

    @patch("services.ocorrencias_estudantes_service.buscar_turma_por_id")
    def test_lista_estudantes_rejeita_turma_inexistente(self, mock_buscar_turma):
        mock_buscar_turma.return_value = None

        with self.assertRaisesRegex(ValueError, "Turma invalida."):
            listar_estudantes_service(turma_id=999)


if __name__ == "__main__":
    unittest.main()
