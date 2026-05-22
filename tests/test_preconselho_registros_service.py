import unittest
from types import SimpleNamespace
from unittest.mock import patch

from services.preconselho_registros_service import (
    excluir_registro_preconselho_service,
    listar_registros_preconselho_service,
    salvar_registro_preconselho,
)


class PreConselhoRegistrosServiceTest(unittest.TestCase):
    @patch("services.preconselho_registros_service.buscar_registro_pre_conselho_por_id")
    @patch("services.preconselho_registros_service.criar_ou_atualizar_registro_pre_conselho")
    @patch("services.preconselho_registros_service.gerar_texto_pre_conselho_individual")
    @patch("services.preconselho_registros_service.validar_motivos_pos_pre_conselho")
    @patch("services.preconselho_registros_service.validar_nivel_atencao_pre_conselho")
    @patch("services.preconselho_registros_service.validar_texto_opcional_preconselho")
    @patch("services.preconselho_registros_service.motivos_ativos_validos_preconselho")
    @patch("services.preconselho_registros_service.validar_escopo_professor_preconselho")
    @patch("services.preconselho_registros_service.resolver_professor_preconselho")
    @patch("services.preconselho_registros_service.validar_estudante_na_turma_preconselho")
    @patch("services.preconselho_registros_service.validar_disciplina_preconselho")
    @patch("services.preconselho_registros_service.validar_turma_preconselho")
    @patch("services.preconselho_registros_service.validar_periodo_preconselho")
    def test_salva_registro_no_service(
        self,
        mock_periodo,
        mock_turma,
        mock_disciplina,
        mock_estudante,
        mock_professor,
        mock_escopo,
        mock_motivos,
        mock_texto_opcional,
        mock_nivel,
        mock_pos,
        mock_gerar,
        mock_salvar,
        mock_buscar,
    ):
        payload = SimpleNamespace(
            periodo_id=3,
            turma_id=4,
            disciplina_id=5,
            estudante_id=6,
            professor_id=None,
            sinalizar=True,
            motivo_ids=[8, 9],
            observacao_professor="observacao",
            nivel_atencao="alto",
            pos_preconselho_motivo_ids=[12],
            pos_preconselho_recuperado=False,
            pos_preconselho_observacao="acompanhar",
        )
        mock_periodo.return_value = {"id": 3, "ano_letivo": 2035, "etapa": 2, "status": "ABERTO"}
        mock_turma.return_value = {"id": 4}
        mock_disciplina.return_value = {"id": 5, "nome": "Matematica"}
        mock_estudante.return_value = {"id": 6, "nome": "Ana"}
        mock_professor.return_value = {"id": 7, "nome": "Prof. Ana"}
        mock_motivos.return_value = [{"id": 8}, {"id": 9}]
        mock_texto_opcional.side_effect = ["observacao", "acompanhar"]
        mock_nivel.return_value = "alto"
        mock_pos.return_value = (False, [12], [{"id": "x"}])
        mock_gerar.return_value = {"texto": "texto pronto"}
        mock_salvar.return_value = 99
        mock_buscar.return_value = {
            "id": 99,
            "professor_id": 7,
            "periodo_status": "ABERTO",
            "texto_gerado": "texto pronto",
        }

        resposta = salvar_registro_preconselho(
            payload,
            {"id": "7", "cargo": "PROFESSOR"},
        )

        mock_escopo.assert_called_once_with(7, 4, 5)
        mock_salvar.assert_called_once()
        self.assertEqual(resposta["id"], 99)
        self.assertTrue(resposta["editavel"])

    @patch("services.preconselho_registros_service.excluir_registro_pre_conselho")
    @patch("services.preconselho_registros_service.listar_registros_pre_conselho")
    @patch("services.preconselho_registros_service.validar_escopo_professor_preconselho")
    @patch("services.preconselho_registros_service.resolver_professor_preconselho")
    @patch("services.preconselho_registros_service.validar_estudante_na_turma_preconselho")
    @patch("services.preconselho_registros_service.validar_disciplina_preconselho")
    @patch("services.preconselho_registros_service.validar_turma_preconselho")
    @patch("services.preconselho_registros_service.validar_periodo_preconselho")
    def test_remove_registro_quando_sinalizar_false(
        self,
        mock_periodo,
        mock_turma,
        mock_disciplina,
        mock_estudante,
        mock_professor,
        mock_escopo,
        mock_listar,
        mock_excluir,
    ):
        payload = SimpleNamespace(
            periodo_id=3,
            turma_id=4,
            disciplina_id=5,
            estudante_id=6,
            professor_id=None,
            sinalizar=False,
            motivo_ids=[],
            observacao_professor="",
            nivel_atencao=None,
            pos_preconselho_motivo_ids=[],
            pos_preconselho_recuperado=None,
            pos_preconselho_observacao="",
        )
        mock_periodo.return_value = {"id": 3, "status": "ABERTO"}
        mock_turma.return_value = {"id": 4}
        mock_disciplina.return_value = {"id": 5}
        mock_estudante.return_value = {"id": 6}
        mock_professor.return_value = {"id": 7}
        mock_listar.return_value = [{"id": 12, "professor_id": 7, "periodo_status": "ABERTO"}]
        mock_excluir.return_value = True

        resposta = salvar_registro_preconselho(
            payload,
            {"id": "7", "cargo": "PROFESSOR"},
        )

        mock_escopo.assert_called_once_with(7, 4, 5)
        mock_excluir.assert_called_once_with(12, professor_usuario_id=7)
        self.assertEqual(resposta["id"], 12)
        self.assertFalse(resposta["editavel"])

    @patch("services.preconselho_registros_service.enriquecer_editavel_preconselho")
    @patch("services.preconselho_registros_service.listar_registros_pre_conselho")
    @patch("services.preconselho_registros_service.validar_filtros_professor_preconselho")
    @patch("services.preconselho_registros_service.validar_periodo_preconselho")
    def test_lista_registros_forca_professor_logado(
        self,
        mock_periodo,
        mock_validar_filtros,
        mock_listar,
        mock_enriquecer,
    ):
        mock_periodo.return_value = {"id": 3}
        mock_listar.return_value = [{"id": 1}]
        mock_enriquecer.return_value = [{"id": 1, "editavel": True}]

        resposta = listar_registros_preconselho_service(
            periodo_id=3,
            turma_id=4,
            disciplina_id=5,
            professor_id=999,
            usuario={"id": "7", "cargo": "PROFESSOR"},
        )

        mock_validar_filtros.assert_called_once_with(7, turma_id=4, disciplina_id=5)
        mock_listar.assert_called_once_with(
            periodo_id=3,
            turma_id=4,
            disciplina_id=5,
            professor_usuario_id=7,
        )
        self.assertEqual(resposta["total_registros"], 1)

    @patch("services.preconselho_registros_service.excluir_registro_pre_conselho")
    @patch("services.preconselho_registros_service.buscar_registro_pre_conselho_por_id")
    def test_exclui_registro_no_service(self, mock_buscar, mock_excluir):
        mock_buscar.return_value = {"id": 12, "professor_id": 7, "periodo_status": "ABERTO"}
        mock_excluir.return_value = True

        resposta = excluir_registro_preconselho_service(
            12,
            {"id": "7", "cargo": "PROFESSOR"},
        )

        mock_excluir.assert_called_once_with(12, professor_usuario_id=7)
        self.assertEqual(resposta, {"ok": True})


if __name__ == "__main__":
    unittest.main()
