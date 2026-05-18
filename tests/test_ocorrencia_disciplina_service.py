import unittest

from services.ocorrencia_disciplina_service import (
    acao_permitida_para_tipo_registro,
    acao_compativel_com_gravidade,
    inferir_gravidade_item_base_legal,
    inferir_gravidade_ocorrencia,
)


class OcorrenciaDisciplinaServiceTest(unittest.TestCase):
    def test_inferir_gravidade_por_intervalo_do_artigo_77(self):
        self.assertEqual(
            inferir_gravidade_item_base_legal({"artigo_numero": "77", "inciso_numero": "III"}),
            "leve",
        )
        self.assertEqual(
            inferir_gravidade_item_base_legal({"artigo_numero": "77", "inciso_numero": "X"}),
            "grave",
        )
        self.assertEqual(
            inferir_gravidade_item_base_legal({"artigo_numero": "77", "inciso_numero": "XV"}),
            "gravissima",
        )

    def test_inferir_gravidade_da_ocorrencia_considera_a_mais_alta(self):
        gravidade = inferir_gravidade_ocorrencia(
            [
                {"artigo_numero": "76"},
                {"artigo_numero": "77", "inciso_numero": "XIV"},
            ]
        )
        self.assertEqual(gravidade, "gravissima")

    def test_acao_detalhada_precisa_ser_compativel_com_a_gravidade(self):
        self.assertTrue(acao_compativel_com_gravidade("advertencia_verbal", "leve"))
        self.assertFalse(acao_compativel_com_gravidade("advertencia_verbal", "grave"))
        self.assertTrue(acao_compativel_com_gravidade("advertencia", "grave"))

    def test_acao_e_validada_pelo_tipo_de_registro(self):
        self.assertTrue(acao_permitida_para_tipo_registro("orientacao_professor", "professor"))
        self.assertTrue(acao_permitida_para_tipo_registro("orientacao_geral_docentes", "geral"))
        self.assertFalse(acao_permitida_para_tipo_registro("advertencia", "professor"))


if __name__ == "__main__":
    unittest.main()
