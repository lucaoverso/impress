import unittest
from unittest.mock import patch

from modules.preconselho.report_helpers import map_teaching_staff_by_classrooms
from services.preconselho_service import (
    gerar_texto_consolidado_pre_conselho,
    gerar_texto_pre_conselho_individual,
)


class PreConselhoServiceTest(unittest.TestCase):
    @patch("modules.preconselho.report_helpers.repository.list_teacher_workloads_by_user_ids")
    @patch("modules.preconselho.report_helpers.repository.list_available_teachers")
    @patch("modules.preconselho.report_helpers.repository.list_admin_classroom_disciplines")
    @patch("modules.preconselho.report_helpers.repository.list_teacher_assignments")
    def test_corpo_docente_mantem_disciplinas_especificas_de_cada_turma(
        self,
        list_teacher_assignments,
        list_admin_classroom_disciplines,
        list_available_teachers,
        list_teacher_workloads_by_user_ids,
    ):
        list_teacher_assignments.side_effect = lambda *, classroom_id, **_: (
            [
                {"professor_nome": "Professor Fulano", "disciplina_nome": "Matemática"},
                {"professor_nome": "Professor Fulano", "disciplina_nome": "Matemática R.A"},
            ]
            if classroom_id == 1
            else [
                {"professor_nome": "Professor Fulano", "disciplina_nome": "Matemática"}
            ]
        )
        list_admin_classroom_disciplines.return_value = []
        list_available_teachers.return_value = [{"id": 10, "nome": "Professor Fulano"}]
        list_teacher_workloads_by_user_ids.return_value = {
            10: {
                "turmas": ["6 A", "7 A"],
                "disciplinas": ["Matemática", "Matemática R.A"],
            }
        }

        resultado = map_teaching_staff_by_classrooms({1: "6 A", 2: "7 A"})

        self.assertEqual(
            resultado[1]["corpo_docente"][0]["disciplinas"],
            ["Matemática", "Matemática R.A"],
        )
        self.assertEqual(
            resultado[2]["corpo_docente"][0]["disciplinas"],
            ["Matemática"],
        )

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
            estudante_em_rav=True,
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
        self.assertIn("Recuperar para Avançar (RAV)", resultado["texto"])
        self.assertIn("prioridade no acompanhamento individualizado", resultado["texto"])
        self.assertIn("foi recuperado por meio da recuperação paralela", resultado["texto"])
        self.assertIn("No pós-pré-conselho, observou-se ainda que", resultado["texto"])
        self.assertGreaterEqual(len(resultado["fragmentos"]), 2)

    def test_texto_individual_exige_motivo(self):
        with self.assertRaises(ValueError):
            gerar_texto_pre_conselho_individual(motivos=[])

    def test_textos_usam_concordancia_feminina_quando_sexo_informado(self):
        motivo = {"codigo": "baixo_rendimento", "descricao": "Baixo rendimento"}
        individual = gerar_texto_pre_conselho_individual(
            motivos=[motivo],
            estudante_nome="Carina",
            estudante_sexo="F",
            disciplina_nome="Matemática",
            pos_preconselho_recuperado=True,
            estudante_em_rav=True,
        )
        consolidado = gerar_texto_consolidado_pre_conselho(
            periodo_nome="1º Bimestre 2032",
            turma_nome="7A",
            disciplina_nome="Matemática",
            registros=[
                {
                    "estudante_id": 1,
                    "estudante_nome": "Carina",
                    "estudante_sexo": "F",
                    "turma_nome": "7A",
                    "disciplina_nome": "Matemática",
                    "professor_nome": "Prof. Ana",
                    "motivos": [motivo],
                }
            ],
        )

        self.assertIn("A estudante Carina obteve baixo rendimento", individual["texto"])
        self.assertIn("A estudante encontra-se em", individual["texto"])
        self.assertIn("a estudante foi recuperada", individual["texto"])
        self.assertIn("A estudante CARINA obteve baixo rendimento", consolidado["texto"])

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
                "estudante_em_rav": True,
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
        self.assertTrue(resultado["itens_agrupados"][0]["estudante_em_rav"])
        self.assertEqual(resultado["itens_agrupados"][0]["professores"], ["PROF. ANA"])
        self.assertIn(
            "Relatos complementares registrados", resultado["itens_agrupados"][0]["texto"]
        )
        self.assertNotIn("Por disciplina", resultado["itens_agrupados"][0]["texto"])
        self.assertIn(
            "Prof. Ana (Matematica), precisa retomar a rotina de estudos",
            resultado["itens_agrupados"][0]["texto"],
        )
        self.assertIn("em razão de", resultado["itens_agrupados"][0]["texto"])
        self.assertIn("Recuperar para Avançar (RAV)", resultado["itens_agrupados"][0]["texto"])
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


    def test_conselho_lista_corpo_docente_e_omite_rav(self):
        registros = [
            {
                "estudante_nome": "Ana", "estudante_id": 1, "turma_nome": "7A",
                "disciplina_nome": "Matemática", "professor_nome": "Prof. Ana",
                "corpo_docente_turma": [
                    {"professor_nome": "Prof. Ana", "disciplinas": ["Matemática"]},
                    {"professor_nome": "Prof. Bruno", "disciplinas": ["História", "Geografia"]},
                ],
                "nivel_atencao": "alto",
                "motivos": [{"codigo": "baixo_rendimento", "descricao": "Baixo rendimento"}],
                "pos_preconselho_recuperado": False, "estudante_em_rav": True,
            },
            {
                "estudante_nome": "Ana", "estudante_id": 1, "turma_nome": "7A",
                "disciplina_nome": "História", "professor_nome": "Prof. Bruno",
                "nivel_atencao": "alto",
                "motivos": [{"codigo": "baixo_rendimento", "descricao": "Baixo rendimento"}],
                "pos_preconselho_recuperado": False, "estudante_em_rav": True,
            },
        ]

        resultado = gerar_texto_consolidado_pre_conselho(
            periodo_nome="1º Bimestre 2032", turma_nome="7A",
            disciplina_nome="Todas as disciplinas", registros=registros,
            versao="conselho",
        )

        self.assertIn("PROF. ANA (Matemática)", resultado["texto"])
        self.assertIn("PROF. BRUNO (História e Geografia)", resultado["texto"])
        self.assertNotIn("Recuperar para Avançar (RAV)", resultado["texto"])
        self.assertNotIn("No pós-pré-conselho", resultado["texto"])
        self.assertNotIn(
            "Após o pré-conselho",
            resultado["itens_agrupados"][0]["texto"],
        )

    def test_texto_consolidado_ordena_estudantes_por_nome(self):
        motivo = {"codigo": "nao_entregou_trabalho", "descricao": "NÃ£o entregou o trabalho"}
        registros = [
            {
                "estudante_nome": "Clara",
                "estudante_id": 3,
                "turma_nome": "7A",
                "disciplina_nome": "Historia",
                "professor_nome": "Prof. A",
                "motivos": [motivo],
            },
            {
                "estudante_nome": "Álvaro",
                "estudante_id": 2,
                "turma_nome": "7A",
                "disciplina_nome": "Matematica",
                "professor_nome": "Prof. B",
                "motivos": [motivo],
            },
            {
                "estudante_nome": "Beatriz",
                "estudante_id": 1,
                "turma_nome": "7A",
                "disciplina_nome": "Ciencias",
                "professor_nome": "Prof. C",
                "motivos": [motivo],
            },
        ]

        resultado = gerar_texto_consolidado_pre_conselho(
            periodo_nome="1Âº Bimestre 2032",
            turma_nome="7A",
            disciplina_nome="Todas as disciplinas",
            registros=registros,
        )

        self.assertEqual(
            [item["estudante_nome"] for item in resultado["itens_agrupados"]],
            ["ÁLVARO", "BEATRIZ", "CLARA"],
        )


if __name__ == "__main__":
    unittest.main()
