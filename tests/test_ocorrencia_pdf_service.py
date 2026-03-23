import io
import unittest

from pypdf import PdfReader

from services.ocorrencia_pdf_service import gerar_pdf_ocorrencia_registro


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
