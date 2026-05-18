import io
import unittest

from pypdf import PdfReader

from services.ocorrencia_pdf_service import (
    _montar_blocos_base_legal,
    _obter_runs_descricao_formatada,
    _obter_gravidade_ocorrencia,
    _obter_titulo_documento,
    gerar_pdf_ocorrencia_registro,
)


def _ocorrencia_base(descricao: str) -> dict:
    return {
        "id": 1,
        "nome_estudante": "Geovanna Correia Galeano",
        "turma_id": 7,
        "turma_nome": "8 B",
        "professor_requerente": "Iara Cristini da Silva Cavalcante",
        "disciplina": "Leitura e Producao Textual",
        "data_ocorrencia": "2026-03-10",
        "aula": "2",
        "horario_ocorrencia": "14:10",
        "descricao": descricao,
        "regimento_itens": [],
        "acao_aplicada": "advertencia",
        "status": "registrado",
        "criado_em": "2026-03-10 14:30:00",
        "atualizado_em": "2026-03-10 14:35:00",
    }


class OcorrenciaPdfServiceTest(unittest.TestCase):
    def test_obtem_titulo_do_documento_a_partir_da_acao_aplicada(self):
        ocorrencia = _ocorrencia_base("Descricao qualquer.")
        ocorrencia["acao_aplicada"] = "suspensao_orientada_2_dias"
        self.assertEqual(
            _obter_titulo_documento(ocorrencia),
            "SUSPENSAO ORIENTADA DAS AULAS (ATE 2 DIAS LETIVOS)",
        )

    def test_obtem_titulo_padrao_para_registro_individual_de_professor(self):
        ocorrencia = _ocorrencia_base("Descricao qualquer.")
        ocorrencia["tipo_registro"] = "professor"
        ocorrencia["acao_aplicada"] = ""
        self.assertEqual(
            _obter_titulo_documento(ocorrencia),
            "REGISTRO INDIVIDUAL DE PROFESSOR",
        )

    def test_gravidade_fica_nula_para_registro_de_professor(self):
        ocorrencia = _ocorrencia_base("Descricao qualquer.")
        ocorrencia["tipo_registro"] = "professor"
        ocorrencia["acao_aplicada"] = "orientacao_professor"
        ocorrencia["regimento_itens"] = [
            {
                "regimento_item_id": 1,
                "artigo_numero": "77",
                "inciso_numero": "XII",
                "artigo": "Regimento Escolar - Art. 77, inciso XII",
                "descricao": "Descricao qualquer.",
                "ordem": 1,
                "tipo": "inciso",
            }
        ]
        self.assertIsNone(_obter_gravidade_ocorrencia(ocorrencia))

    def test_obtem_runs_de_descricao_formatada_para_pdf(self):
        runs = _obter_runs_descricao_formatada(
            "<p><strong>Aluno</strong> <em>orientado</em> "
            '<span style="background-color: #fff3a3;">com destaque</span></p>'
        )

        self.assertTrue(any(run.texto == "Aluno" and run.negrito for run in runs))
        self.assertTrue(any(run.texto == "orientado" and run.italico for run in runs))
        self.assertTrue(
            any(run.texto == "com destaque" and run.cor_fundo == (255, 243, 163) for run in runs)
        )

    def test_obtem_gravidade_a_partir_da_base_legal(self):
        ocorrencia = _ocorrencia_base("Descricao qualquer.")
        ocorrencia["regimento_itens"] = [
            {
                "regimento_item_id": 1,
                "artigo_numero": "77",
                "inciso_numero": "XII",
                "artigo": "Regimento Escolar - Art. 77, inciso XII",
                "descricao": "Descricao qualquer.",
                "ordem": 1,
                "tipo": "inciso",
            }
        ]
        self.assertEqual(_obter_gravidade_ocorrencia(ocorrencia), "grave")

    def test_monta_blocos_base_legal_agrupa_itens_legados_por_artigo(self):
        blocos = _montar_blocos_base_legal(
            [
                {
                    "regimento_item_id": 2,
                    "artigo": "Art. 76 - VII",
                    "descricao": "Integrar-se ao processo pedagogico desenvolvido pela unidade escolar.",
                    "ordem": 1,
                },
                {
                    "regimento_item_id": 3,
                    "artigo": "Art. 76 - X",
                    "descricao": "Atender convocacao da Direcao Escolar e Coordenacao Pedagogica.",
                    "ordem": 2,
                },
            ]
        )

        self.assertEqual(
            blocos,
            [
                {
                    "tipo": "artigo",
                    "texto": "Art. 76.",
                },
                {
                    "tipo": "inciso",
                    "texto": "VII - Integrar-se ao processo pedagogico desenvolvido pela unidade escolar.",
                },
                {
                    "tipo": "inciso",
                    "texto": "X - Atender convocacao da Direcao Escolar e Coordenacao Pedagogica.",
                },
            ],
        )

    def test_monta_blocos_base_legal_agrupando_incisos_do_mesmo_artigo(self):
        blocos = _montar_blocos_base_legal(
            [
                {
                    "regimento_item_id": 10,
                    "lei_nome": "Regimento Escolar",
                    "artigo_id": 76,
                    "artigo_numero": "76",
                    "artigo_descricao": "Sao deveres do estudante, alem daqueles previstos na legislacao vigente, os seguintes:",
                    "inciso_id": 1,
                    "inciso_numero": "I",
                    "inciso_descricao": "comparecer, pontualmente, as aulas, provas e outras atividades preparadas e programadas pelo professor;",
                    "artigo": "Regimento Escolar - Art. 76, inciso I",
                    "descricao": "comparecer, pontualmente, as aulas, provas e outras atividades preparadas e programadas pelo professor;",
                    "ordem": 1,
                    "tipo": "inciso",
                },
                {
                    "regimento_item_id": 11,
                    "lei_nome": "Regimento Escolar",
                    "artigo_id": 76,
                    "artigo_numero": "76",
                    "artigo_descricao": "Sao deveres do estudante, alem daqueles previstos na legislacao vigente, os seguintes:",
                    "inciso_id": 2,
                    "inciso_numero": "III",
                    "inciso_descricao": "respeitar a decisao da Direcao Escolar, do Colegiado Escolar e da APM referente ao uso do uniforme na unidade escolar;",
                    "artigo": "Regimento Escolar - Art. 76, inciso III",
                    "descricao": "respeitar a decisao da Direcao Escolar, do Colegiado Escolar e da APM referente ao uso do uniforme na unidade escolar;",
                    "ordem": 2,
                    "tipo": "inciso",
                },
            ]
        )

        self.assertEqual(
            blocos,
            [
                {
                    "tipo": "artigo",
                    "texto": "Art. 76. Sao deveres do estudante, alem daqueles previstos na legislacao vigente, os seguintes:",
                },
                {
                    "tipo": "inciso",
                    "texto": "I - comparecer, pontualmente, as aulas, provas e outras atividades preparadas e programadas pelo professor;",
                },
                {
                    "tipo": "inciso",
                    "texto": "III - respeitar a decisao da Direcao Escolar, do Colegiado Escolar e da APM referente ao uso do uniforme na unidade escolar;",
                },
            ],
        )

    def test_monta_blocos_base_legal_incluindo_inciso_e_alineas(self):
        blocos = _montar_blocos_base_legal(
            [
                {
                    "regimento_item_id": 12,
                    "lei_nome": "Regimento Escolar",
                    "artigo_id": 76,
                    "artigo_numero": "76",
                    "artigo_descricao": "Sao deveres do estudante, alem daqueles previstos na legislacao vigente, os seguintes:",
                    "inciso_id": 4,
                    "inciso_numero": "IV",
                    "inciso_descricao": "apresentar-se, adequadamente, trajado para as aulas...",
                    "alinea_id": 20,
                    "alinea_identificador": "a",
                    "alinea_descricao": "short e bermuda (5 (cinco) centimetros acima do joelho);",
                    "artigo": "Regimento Escolar - Art. 76, inciso IV, alinea a",
                    "descricao": "short e bermuda (5 (cinco) centimetros acima do joelho);",
                    "ordem": 1,
                    "tipo": "alinea",
                },
                {
                    "regimento_item_id": 13,
                    "lei_nome": "Regimento Escolar",
                    "artigo_id": 76,
                    "artigo_numero": "76",
                    "artigo_descricao": "Sao deveres do estudante, alem daqueles previstos na legislacao vigente, os seguintes:",
                    "inciso_id": 4,
                    "inciso_numero": "IV",
                    "inciso_descricao": "apresentar-se, adequadamente, trajado para as aulas...",
                    "alinea_id": 21,
                    "alinea_identificador": "b",
                    "alinea_descricao": "oculos escuros, salvo se recomendacao medica;",
                    "artigo": "Regimento Escolar - Art. 76, inciso IV, alinea b",
                    "descricao": "oculos escuros, salvo se recomendacao medica;",
                    "ordem": 2,
                    "tipo": "alinea",
                },
            ]
        )

        self.assertEqual(
            blocos,
            [
                {
                    "tipo": "artigo",
                    "texto": "Art. 76. Sao deveres do estudante, alem daqueles previstos na legislacao vigente, os seguintes:",
                },
                {
                    "tipo": "inciso",
                    "texto": "IV - apresentar-se, adequadamente, trajado para as aulas...",
                },
                {
                    "tipo": "alinea",
                    "texto": "a) short e bermuda (5 (cinco) centimetros acima do joelho);",
                },
                {
                    "tipo": "alinea",
                    "texto": "b) oculos escuros, salvo se recomendacao medica;",
                },
            ],
        )

    def test_gera_pdf_valido_para_impressao(self):
        pdf_bytes = gerar_pdf_ocorrencia_registro(
            _ocorrencia_base(
                "Na data de hoje a docente acionou esta Coordenacao para registrar "
                "comportamento inadequado durante a aula."
            ),
            turma={"turno": "MATUTINO"},
        )

        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        reader = PdfReader(io.BytesIO(pdf_bytes))
        self.assertEqual(len(reader.pages), 1)

    def test_gera_pdf_valido_com_itens_do_regimento(self):
        ocorrencia = _ocorrencia_base("Descricao com apoio do regimento escolar.")
        ocorrencia["regimento_itens"] = [
            {
                "regimento_item_id": 2,
                "artigo": "Art. 76 - VII",
                "descricao": "Integrar-se ao processo pedagogico desenvolvido pela unidade escolar.",
                "ordem": 1,
            },
            {
                "regimento_item_id": 3,
                "artigo": "Art. 76 - X",
                "descricao": "Atender convocacao da Direcao Escolar e Coordenacao Pedagogica.",
                "ordem": 2,
            },
        ]

        pdf_bytes = gerar_pdf_ocorrencia_registro(ocorrencia, turma={"turno": "MATUTINO"})
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        reader = PdfReader(io.BytesIO(pdf_bytes))
        self.assertGreaterEqual(len(reader.pages), 1)

    def test_paginas_adicionais_quando_descricao_ultrapassa_uma_folha(self):
        descricao_longa = " ".join(
            [
                "O estudante permaneceu disperso, interrompeu a aula e nao atendeu as orientacoes da professora."
                for _ in range(700)
            ]
        )
        pdf_bytes = gerar_pdf_ocorrencia_registro(
            _ocorrencia_base(descricao_longa),
            turma={"turno": "MATUTINO"},
        )

        reader = PdfReader(io.BytesIO(pdf_bytes))
        self.assertGreaterEqual(len(reader.pages), 2)


if __name__ == "__main__":
    unittest.main()
