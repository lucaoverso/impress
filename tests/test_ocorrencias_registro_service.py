import unittest
from types import SimpleNamespace
from unittest.mock import patch

from services.ocorrencias_registro_service import (
    atualizar_ocorrencia_parcial_service,
    criar_ocorrencia_service,
    remover_ocorrencia_service,
)


class OcorrenciasRegistroServiceTest(unittest.TestCase):
    @patch("services.ocorrencias_registro_service.buscar_ocorrencia_service")
    @patch("services.ocorrencias_registro_service.criar_ocorrencia")
    @patch("services.ocorrencias_registro_service.validar_data_iso_ocorrencia")
    @patch("services.ocorrencias_registro_service.validar_horario_ocorrencia_service")
    @patch("services.ocorrencias_registro_service.validar_faixa_aula_por_turma_ocorrencia")
    @patch("services.ocorrencias_registro_service.resolver_contexto_registro_ocorrencia")
    @patch("services.ocorrencias_registro_service.normalizar_regimento_item_ids_ocorrencia")
    @patch("services.ocorrencias_registro_service.buscar_regimento_itens_por_ids")
    def test_cria_ocorrencia_de_estudante_no_service(
        self,
        mock_buscar_itens,
        mock_normalizar_ids,
        mock_contexto,
        mock_aula,
        mock_horario,
        mock_data,
        mock_criar,
        mock_buscar_resposta,
    ):
        mock_normalizar_ids.return_value = [91]
        mock_buscar_itens.return_value = [{"id": 91}]
        mock_contexto.return_value = {
            "nome_estudante": "Aluno Um",
            "estudante_id": 5,
            "estudantes_vinculados": [{"estudante_id": 5, "nome": "Aluno Um", "turma_id": 9}],
            "turma_id": 9,
            "professor_requerente": "Prof Teste",
            "professor_requerente_id": None,
            "professores_vinculados": [],
        }
        mock_aula.return_value = "2"
        mock_horario.return_value = "07:30"
        mock_data.return_value = "2026-03-20"
        mock_criar.return_value = 77
        mock_buscar_resposta.return_value = {"id": 77, "nome_estudante": "Aluno Um"}
        payload = SimpleNamespace(
            tipo_registro="estudante",
            nome_estudante="Aluno Um",
            estudante_id=5,
            estudantes_vinculados=None,
            turma_id=9,
            professor_requerente="Prof Teste",
            professor_requerente_id=None,
            professores_vinculados=None,
            disciplina="Portugues",
            data_ocorrencia="2026-03-20",
            aula="2",
            horario_ocorrencia="07:30",
            descricao="Descricao valida",
            regimento_item_ids=[91],
            acao_aplicada="advertencia",
            status="registrado",
        )
        resposta = criar_ocorrencia_service(payload)
        self.assertEqual(mock_criar.call_args.kwargs["regimento_item_ids"], [91])
        self.assertEqual(mock_criar.call_args.kwargs["aula"], "2")
        self.assertEqual(resposta["id"], 77)

    @patch("services.ocorrencias_registro_service.buscar_ocorrencia_service")
    @patch("services.ocorrencias_registro_service.criar_ocorrencia")
    @patch("services.ocorrencias_registro_service.validar_data_iso_ocorrencia")
    @patch("services.ocorrencias_registro_service.validar_horario_ocorrencia_service")
    @patch("services.ocorrencias_registro_service.resolver_contexto_registro_ocorrencia")
    @patch("services.ocorrencias_registro_service.normalizar_regimento_item_ids_ocorrencia")
    @patch("services.ocorrencias_registro_service.buscar_regimento_itens_por_ids")
    def test_cria_ocorrencia_de_professor_limpa_base_legal_e_aula(
        self,
        mock_buscar_itens,
        mock_normalizar_ids,
        mock_contexto,
        mock_horario,
        mock_data,
        mock_criar,
        mock_buscar_resposta,
    ):
        mock_normalizar_ids.return_value = [55]
        mock_contexto.return_value = {
            "nome_estudante": "Professor Um",
            "estudante_id": None,
            "estudantes_vinculados": [],
            "turma_id": None,
            "professor_requerente": "Professor Um",
            "professor_requerente_id": 8,
            "professores_vinculados": [{"professor_id": 8, "nome": "Professor Um", "email": ""}],
        }
        mock_horario.return_value = "09:00"
        mock_data.return_value = "2026-03-24"
        mock_criar.return_value = 88
        mock_buscar_resposta.return_value = {"id": 88, "tipo_registro": "professor"}
        mock_buscar_itens.return_value = [{"id": 55}]
        payload = SimpleNamespace(
            tipo_registro="professor",
            nome_estudante=None,
            estudante_id=None,
            estudantes_vinculados=None,
            turma_id=None,
            professor_requerente="Professor Um",
            professor_requerente_id=8,
            professores_vinculados=None,
            disciplina="Alinhamento",
            data_ocorrencia="2026-03-24",
            aula="3",
            horario_ocorrencia="09:00",
            descricao="Registro de professor",
            regimento_item_ids=[55],
            acao_aplicada="orientacao_professor",
            status="registrado",
        )
        criar_ocorrencia_service(payload)
        self.assertEqual(mock_criar.call_args.kwargs["regimento_item_ids"], [])
        self.assertEqual(mock_criar.call_args.kwargs["aula"], "")

    @patch("services.ocorrencias_registro_service.buscar_ocorrencia_por_id")
    def test_atualizar_ocorrencia_rejeita_payload_vazio(self, mock_buscar):
        mock_buscar.return_value = {"id": 10, "tipo_registro": "estudante"}
        with self.assertRaisesRegex(ValueError, "Informe ao menos um campo"):
            atualizar_ocorrencia_parcial_service(10, SimpleNamespace())

    @patch("services.ocorrencias_registro_service.buscar_ocorrencia_service")
    @patch("services.ocorrencias_registro_service.salvar_regimento_itens_ocorrencia")
    @patch("services.ocorrencias_registro_service.salvar_ocorrencia_professores_vinculados")
    @patch("services.ocorrencias_registro_service.salvar_ocorrencia_estudantes_vinculados")
    @patch("services.ocorrencias_registro_service.atualizar_ocorrencia")
    @patch("services.ocorrencias_registro_service.resolver_contexto_registro_ocorrencia")
    @patch("services.ocorrencias_registro_service.buscar_ocorrencia_por_id")
    def test_atualizar_tipo_para_professor_limpa_base_legal_no_service(
        self,
        mock_buscar_atual,
        mock_contexto,
        _mock_atualizar,
        _mock_salvar_estudantes,
        mock_salvar_professores,
        mock_salvar_regimento,
        mock_buscar_resposta,
    ):
        mock_buscar_atual.return_value = {
            "id": 12,
            "tipo_registro": "estudante",
            "nome_estudante": "Aluno",
            "estudante_id": 3,
            "turma_id": 4,
            "professor_requerente": "Prof",
            "professor_requerente_id": None,
            "disciplina": "Portugues",
            "aula": "2",
            "acao_aplicada": "orientacao_verbal",
            "regimento_itens": [{"id": 7}],
        }
        mock_contexto.return_value = {
            "nome_estudante": "Professor Um",
            "estudante_id": None,
            "estudantes_vinculados": [],
            "turma_id": None,
            "professor_requerente": "Professor Um",
            "professor_requerente_id": 8,
            "professores_vinculados": [{"professor_id": 8, "nome": "Professor Um", "email": ""}],
        }
        mock_buscar_resposta.return_value = {"id": 12, "tipo_registro": "professor", "regimento_itens": []}
        payload = {
            "tipo_registro": "professor",
            "professor_requerente": "Professor Um",
            "professor_requerente_id": 8,
            "professores_vinculados": [{"professor_id": 8, "nome": "Professor Um"}],
            "disciplina": "Acompanhamento funcional",
            "acao_aplicada": "orientacao_professor",
        }
        resposta = atualizar_ocorrencia_parcial_service(12, payload)
        self.assertEqual(mock_salvar_regimento.call_args.args[1], [])
        self.assertEqual(mock_salvar_professores.call_args.args[0], 12)
        self.assertEqual(resposta["tipo_registro"], "professor")

    @patch("services.ocorrencias_registro_service.remover_ocorrencia")
    def test_remove_ocorrencia_retorna_lookup_quando_nao_remove(self, mock_remover):
        mock_remover.return_value = False

        with self.assertRaisesRegex(LookupError, "Registro nao encontrado."):
            remover_ocorrencia_service(44)


if __name__ == "__main__":
    unittest.main()
