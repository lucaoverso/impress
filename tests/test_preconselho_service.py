import unittest

from services.preconselho_service import (
    gerar_texto_consolidado_pre_conselho,
    gerar_texto_pre_conselho_individual,
)


class PreConselhoServiceTest(unittest.TestCase):
    def test_gera_texto_individual_com_categorias_e_observacao(self):
        motivos = [
            {
                "categoria": "avaliacao",
                "codigo": "nao_fez_prova_bimestral",
                "descricao": "Nao fez a prova bimestral",
            },
            {
                "categoria": "avaliacao",
                "codigo": "nao_entregou_trabalho",
                "descricao": "Nao entregou o trabalho",
            },
            {
                "categoria": "participacao",
                "codigo": "baixa_participacao_aula",
                "descricao": "Baixa participacao em aula",
            },
        ]

        resultado = gerar_texto_pre_conselho_individual(
            motivos=motivos,
            observacao_professor="desorganizacao quanto ao cumprimento de prazos",
            nivel_atencao="alto",
            estudante_nome="Ana",
            disciplina_nome="Matematica",
        )

        self.assertIn(
            "O estudante Ana obteve baixo rendimento na disciplina de Matematica",
            resultado["texto"],
        )
        self.assertIn("ausencia na realizacao da prova bimestral", resultado["texto"])
        self.assertIn("nao entrega de trabalhos propostos", resultado["texto"])
        self.assertIn("baixa participacao nas aulas", resultado["texto"])
        self.assertIn("Como relato complementar do professor", resultado["texto"])
        self.assertIn("prioridade no acompanhamento individualizado", resultado["texto"])
        self.assertGreaterEqual(len(resultado["fragmentos"]), 2)

    def test_texto_individual_exige_motivo(self):
        with self.assertRaises(ValueError):
            gerar_texto_pre_conselho_individual(motivos=[])

    def test_gera_texto_consolidado_com_motivos_frequentes(self):
        registros = [
            {
                "estudante_nome": "Ana",
                "estudante_id": 1,
                "turma_nome": "7A",
                "disciplina_nome": "Matematica",
                "professor_nome": "Prof. Ana",
                "nivel_atencao": "medio",
                "motivos": [
                    {"codigo": "nao_fez_prova_bimestral", "descricao": "Nao fez a prova bimestral"},
                    {
                        "codigo": "baixa_participacao_aula",
                        "descricao": "Baixa participacao em aula",
                    },
                ],
                "observacao_professor": "precisa retomar a rotina de estudos",
            },
            {
                "estudante_nome": "Ana",
                "estudante_id": 1,
                "turma_nome": "7A",
                "disciplina_nome": "Historia",
                "professor_nome": "Prof. Ana",
                "nivel_atencao": "alto",
                "motivos": [
                    {"codigo": "nao_entregou_trabalho", "descricao": "Nao entregou o trabalho"},
                ],
                "observacao_professor": "",
            },
        ]

        resultado = gerar_texto_consolidado_pre_conselho(
            periodo_nome="1o Bimestre 2032",
            turma_nome="7A",
            disciplina_nome="Todas as disciplinas",
            registros=registros,
            professor_nome="Prof. Ana",
        )

        self.assertEqual(resultado["total_registros"], 2)
        self.assertEqual(resultado["total_estudantes"], 1)
        self.assertIn("1o Bimestre 2032", resultado["texto"])
        self.assertIn("7A", resultado["texto"])
        self.assertIn("Matematica e Historia", resultado["texto"])
        self.assertIn("Prof. Ana", resultado["texto"])
        self.assertIn("Nao fez a prova bimestral", resultado["motivos_frequentes"][0])
        self.assertEqual(len(resultado["itens_agrupados"]), 1)
        self.assertEqual(resultado["itens_agrupados"][0]["estudante_nome"], "Ana")
        self.assertIn(
            "Relatos complementares registrados", resultado["itens_agrupados"][0]["texto"]
        )


if __name__ == "__main__":
    unittest.main()
