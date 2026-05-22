import unittest
from unittest.mock import patch

from services.preconselho_contexto_service import (
    listar_estudantes_painel_preconselho,
    obter_contexto_preconselho,
)
from services.preconselho_validacao_service import (
    obter_usuario_id_preconselho,
    validar_data_iso_preconselho,
    validar_escopo_professor_preconselho,
)


class PreConselhoContextoServiceTest(unittest.TestCase):
    def test_obtem_usuario_id_valido(self):
        self.assertEqual(obter_usuario_id_preconselho({"id": "7"}), 7)
        with self.assertRaises(ValueError):
            obter_usuario_id_preconselho({"id": 0})

    def test_valida_data_iso(self):
        self.assertEqual(
            validar_data_iso_preconselho("2026-05-22", "Data inicial"),
            "2026-05-22",
        )
        with self.assertRaises(ValueError):
            validar_data_iso_preconselho("22/05/2026", "Data inicial")

    @patch("services.preconselho_validacao_service.escopo_professor_preconselho")
    def test_valida_escopo_professor_combinacao_exata(self, mock_escopo):
        mock_escopo.return_value = {
            "turmas": [{"id": 1}],
            "disciplinas": [{"id": 2}],
            "usa_atribuicoes_exatas": True,
            "combinacoes": [{"turma_id": 1, "disciplina_id": 2}],
        }

        validar_escopo_professor_preconselho(9, 1, 2)

        with self.assertRaises(PermissionError):
            validar_escopo_professor_preconselho(9, 1, 3)

    @patch("services.preconselho_contexto_service.listar_motivos_pos_pre_conselho")
    @patch("services.preconselho_contexto_service.listar_niveis_atencao_pre_conselho")
    @patch("services.preconselho_contexto_service.listar_professores_agendamento")
    @patch("services.preconselho_contexto_service.listar_motivos_pre_conselho")
    @patch("services.preconselho_contexto_service.minhas_turmas_disciplinas_preconselho")
    @patch("services.preconselho_contexto_service.listar_periodos_pre_conselho")
    @patch("services.preconselho_contexto_service.opcoes_professor_preconselho")
    def test_obtem_contexto_para_professor(
        self,
        mock_opcoes,
        mock_periodos,
        mock_minhas,
        mock_motivos,
        _mock_professores,
        mock_niveis,
        mock_motivos_pos,
    ):
        mock_opcoes.return_value = ([{"id": 1, "nome": "7A"}], [{"id": 2, "nome": "Matematica"}])
        mock_periodos.return_value = [{"id": 5, "status": "ABERTO"}]
        mock_minhas.return_value = [{"turma_id": 1, "disciplina_id": 2}]
        mock_motivos.return_value = [{"id": 9, "descricao": "Motivo"}]
        mock_niveis.return_value = [{"id": "alto", "nome": "Alto"}]
        mock_motivos_pos.return_value = {"recuperado": [], "nao_recuperado": []}

        contexto = obter_contexto_preconselho(
            {"id": "7", "nome": "Ana", "cargo": "PROFESSOR"}
        )

        self.assertEqual(contexto["professor_id"], 7)
        self.assertEqual(contexto["professor_nome"], "Ana")
        self.assertEqual(contexto["turmas"][0]["nome"], "7A")
        self.assertEqual(contexto["disciplinas"][0]["nome"], "Matematica")
        self.assertEqual(contexto["minhas_turmas_disciplinas"][0]["turma_id"], 1)

    @patch("services.preconselho_contexto_service.listar_estudantes_pre_conselho_painel")
    @patch("services.preconselho_contexto_service.validar_escopo_professor_preconselho")
    @patch("services.preconselho_contexto_service.resolver_professor_preconselho")
    @patch("services.preconselho_contexto_service.validar_disciplina_preconselho")
    @patch("services.preconselho_contexto_service.validar_turma_preconselho")
    @patch("services.preconselho_contexto_service.validar_periodo_preconselho")
    def test_lista_estudantes_painel_no_service(
        self,
        mock_periodo,
        mock_turma,
        mock_disciplina,
        mock_professor,
        mock_escopo,
        mock_listar,
    ):
        mock_periodo.return_value = {"id": 3}
        mock_turma.return_value = {"id": 4}
        mock_disciplina.return_value = {"id": 5}
        mock_professor.return_value = {"id": 7, "nome": "Ana"}
        mock_listar.return_value = [{"estudante_id": 1, "nome": "Bruno"}]

        resposta = listar_estudantes_painel_preconselho(
            periodo_id=3,
            turma_id=4,
            disciplina_id=5,
            q="",
            status="todos",
            professor_id=None,
            usuario={"id": "7", "cargo": "PROFESSOR"},
        )

        mock_escopo.assert_called_once_with(7, 4, 5)
        mock_listar.assert_called_once_with(
            periodo_id=3,
            turma_id=4,
            disciplina_id=5,
            professor_usuario_id=7,
            busca_nome="",
            status="todos",
        )
        self.assertEqual(resposta[0]["nome"], "Bruno")


if __name__ == "__main__":
    unittest.main()
