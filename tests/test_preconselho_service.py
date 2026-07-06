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
                "descricao": "Não fez a prova bimestral",
            },
            {
                "categoria": "avaliacao",
                "codigo": "nao_entregou_trabalho",
                "descricao": "Não entregou o trabalho",
            },
            {
                "categoria": "participacao",
                "codigo": "baixa_participacao_aula",
                "descricao": "Baixa participação em aula",
            },
        ]

        resultado = gerar_texto_pre_conselho_individual(
            motivos=motivos,
            observacao_professor="desorganizacao quanto ao cumprimento de prazos",
            nivel_atencao="alto",
            estudante_nome="Ana",
            disciplina_nome="Matematica",
            pos_preconselho_recuperado=True,
            pos_preconselho_observacao="conseguiu responder melhor as atividades de retomada",
        )

        self.assertIn(
            "O estudante Ana obteve baixo rendimento na disciplina de Matematica",
            resultado["texto"],
        )
        self.assertIn("em razão de", resultado["texto"])
        self.assertIn("ausência na realização da prova bimestral", resultado["texto"])
        self.assertIn("não entrega de trabalhos propostos", resultado["texto"])
        self.assertIn("baixa participação nas aulas", resultado["texto"])
        self.assertIn("Como relato complementar do professor", resultado["texto"])
        self.assertIn("prioridade no acompanhamento individualizado", resultado["texto"])
        self.assertIn("foi recuperado por meio da recuperação paralela", resultado["texto"])
        self.assertIn("No pós-pré-conselho, observou-se ainda que", resultado["texto"])
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
                "professores_turma": ["Prof. Ana", "Prof. Bruno"],
                "corpo_docente_turma": [
                    {"professor_nome": "João Batista Gomes", "disciplinas": ["Matematica"]},
                    {"professor_nome": "Pamela Sabrina Araujo Silva", "disciplinas": ["Historia"]},
                    {
                        "professor_nome": "Alex Borges",
                        "disciplinas": ["Lingua Portuguesa", "R.A Lingua Portuguesa"],
                    },
                ],
                "nivel_atencao": "medio",
                "motivos": [
                    {"codigo": "nao_fez_prova_bimestral", "descricao": "Não fez a prova bimestral"},
                    {
                        "codigo": "baixa_participacao_aula",
                        "descricao": "Baixa participação em aula",
                    },
                ],
                "observacao_professor": "precisa retomar a rotina de estudos",
                "pos_preconselho_recuperado": False,
                "pos_preconselho_observacao": "segue precisando de retomada frequente",
            },
            {
                "estudante_nome": "Ana",
                "estudante_id": 1,
                "turma_nome": "7A",
                "disciplina_nome": "Historia",
                "professor_nome": "Prof. Ana",
                "professores_turma": ["Prof. Ana", "Prof. Bruno"],
                "nivel_atencao": "alto",
                "motivos": [
                    {"codigo": "nao_entregou_trabalho", "descricao": "Não entregou o trabalho"},
                ],
                "observacao_professor": "",
                "pos_preconselho_recuperado": True,
                "pos_preconselho_observacao": "",
            },
            {
                "estudante_nome": "Beatriz",
                "estudante_id": 2,
                "turma_nome": "7A",
                "disciplina_nome": "Lingua Portuguesa",
                "professor_nome": "Alex Borges",
                "nivel_atencao": "baixo",
                "motivos": [
                    {"codigo": "nao_entregou_trabalho", "descricao": "Não entregou o trabalho"},
                ],
                "observacao_professor": "",
            },
            {
                "estudante_nome": "Clara",
                "estudante_id": 3,
                "turma_nome": "7A",
                "disciplina_nome": "R.A Lingua Portuguesa",
                "professor_nome": "Alex Borges",
                "nivel_atencao": "baixo",
                "motivos": [
                    {"codigo": "nao_entregou_trabalho", "descricao": "Não entregou o trabalho"},
                ],
                "observacao_professor": "",
            },
        ]

        resultado = gerar_texto_consolidado_pre_conselho(
            periodo_nome="1º Bimestre 2032",
            turma_nome="7A",
            disciplina_nome="Todas as disciplinas",
            registros=registros,
            professor_nome="João Batista Gomes",
        )

        self.assertEqual(resultado["total_registros"], 4)
        self.assertEqual(resultado["total_estudantes"], 3)
        self.assertIn("No período 1º Bimestre 2032", resultado["texto"])
        self.assertIn("7A", resultado["texto"])
        self.assertNotIn("A turma do 7A, composta pelo seguinte corpo docente:", resultado["texto"])
        self.assertIn("JOÃO BATISTA GOMES", resultado["texto"])
        self.assertNotIn("Pamela Sabrina Araujo Silva (Historia)", resultado["texto"])
        self.assertIn("PROF. ANA (Matematica e Historia)", resultado["texto"])
        self.assertIn(
            "ALEX BORGES (Lingua Portuguesa e R.A Lingua Portuguesa)",
            resultado["texto"],
        )
        self.assertIn("Não entregou o trabalho", resultado["motivos_frequentes"][0])
        self.assertEqual(len(resultado["itens_agrupados"]), 3)
        self.assertEqual(resultado["itens_agrupados"][0]["estudante_nome"], "ANA")
        self.assertEqual(resultado["itens_agrupados"][0]["professores"], ["PROF. ANA"])
        self.assertIn(
            "Relatos complementares registrados", resultado["itens_agrupados"][0]["texto"]
        )
        self.assertIn(
            "em Matematica, Prof ANA relatou que precisa retomar a rotina de estudos",
            resultado["itens_agrupados"][0]["texto"],
        )
        self.assertIn("em razão de", resultado["itens_agrupados"][0]["texto"])
        self.assertIn("No pós-pré-conselho, registrou-se que", resultado["itens_agrupados"][0]["texto"])
        self.assertNotIn("Os professores que atuam na turma", resultado["itens_agrupados"][0]["texto"])

    def test_gera_texto_consolidado_vazio_com_acentuacao(self):
        resultado = gerar_texto_consolidado_pre_conselho(
            periodo_nome="1º Bimestre 2032",
            turma_nome="7A",
            disciplina_nome="Matematica",
            registros=[],
        )

        self.assertEqual(resultado["total_registros"], 0)
        self.assertIn("No período 1º Bimestre 2032", resultado["texto"])
        self.assertIn("não há registros de estudantes sinalizados no pré-conselho", resultado["texto"])


if __name__ == "__main__":
    unittest.main()
