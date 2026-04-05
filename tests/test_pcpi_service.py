import unittest

from services.pcpi_service import (
    GRUPO_AUTOMATICO_AUDIOVISUAL,
    GRUPO_AUTOMATICO_STE,
    gerar_texto_pcpi,
)


def _agendamento(
    *,
    agendamento_id: int,
    categoria_uso: str,
    professor_nome: str,
    componentes: list[str],
    turma: str,
    aula: str,
    recurso_nome: str,
) -> dict:
    return {
        "agendamento_id": agendamento_id,
        "data": "2026-04-03",
        "turno": "MATUTINO",
        "turno_nome": "Matutino",
        "aula": aula,
        "faixa_global": int(aula),
        "recurso_id": agendamento_id,
        "recurso_nome": recurso_nome,
        "recurso_tipo": "Tecnologico",
        "professor_id": agendamento_id,
        "professor_nome": professor_nome,
        "componentes": componentes,
        "turma": turma,
        "tema_aula": "Atividade planejada",
        "observacao": "",
        "categoria_uso": categoria_uso,
    }


class PcpiServiceTest(unittest.TestCase):
    def test_agrupa_agendamentos_automaticos_por_tipo_de_acao(self):
        itens = [
            _agendamento(
                agendamento_id=1,
                categoria_uso=GRUPO_AUTOMATICO_STE,
                professor_nome="Ana",
                componentes=["Matematica"],
                turma="7A",
                aula="1",
                recurso_nome="STE Sala 1",
            ),
            _agendamento(
                agendamento_id=2,
                categoria_uso=GRUPO_AUTOMATICO_AUDIOVISUAL,
                professor_nome="Bruno",
                componentes=["Historia"],
                turma="8A",
                aula="2",
                recurso_nome="Projetor Multiuso",
            ),
            _agendamento(
                agendamento_id=3,
                categoria_uso=GRUPO_AUTOMATICO_AUDIOVISUAL,
                professor_nome="Carla",
                componentes=["Geografia"],
                turma="9A",
                aula="3",
                recurso_nome="Caixa de Som Bluetooth",
            ),
        ]

        resultado = gerar_texto_pcpi("2026-04-03", "MATUTINO", itens, [])

        self.assertEqual(resultado["total_agendamentos"], 3)
        self.assertEqual(len(resultado["frases_automaticas"]), 2)
        self.assertIn("Sala de Tecnologia Educacional (STE)", resultado["frases_automaticas"][0])
        self.assertIn("Entrega e recebimento de equipamentos tecnologicos", resultado["frases_automaticas"][1])
        self.assertIn("Bruno", resultado["frases_automaticas"][1])
        self.assertIn("Carla", resultado["frases_automaticas"][1])

    def test_gera_frases_manuais_por_tipo_e_agrupa_itens_tecnicos(self):
        registros = [
            {
                "tipo_acao": "impressao",
                "descricao_curta": "avaliacoes adaptadas",
                "observacoes": "demanda do 7A",
            },
            {
                "tipo_acao": "impressao",
                "descricao_curta": "roteiros de estudo",
                "observacoes": "",
            },
            {
                "tipo_acao": "orientacao",
                "professor_nome": "Daniela",
                "componente": "Google Apresentacoes",
                "descricao_curta": "uso de recursos visuais em aula",
                "observacoes": "",
            },
            {
                "tipo_acao": "formulario2",
                "descricao_curta": "Feira de Ciencias",
                "observacoes": "",
            },
        ]

        resultado = gerar_texto_pcpi("2026-04-03", "MATUTINO", [], registros)

        self.assertEqual(resultado["total_registros_manuais"], 4)
        self.assertEqual(len(resultado["frases_manuais"]), 3)
        self.assertIn("Producao e organizacao de impressoes", resultado["frases_manuais"][0])
        self.assertIn("Orientacao ao(à) professor(a) Daniela", resultado["frases_manuais"][1])
        self.assertIn("Elaboracao do Formulario II", resultado["frases_manuais"][2])

    def test_adiciona_fechamento_quando_turno_tem_pouco_conteudo(self):
        registros = [
            {
                "tipo_acao": "registro",
                "descricao_curta": "lancamento de informacoes do turno",
                "observacoes": "",
            }
        ]

        resultado = gerar_texto_pcpi("2026-04-03", "VESPERTINO", [], registros)

        self.assertTrue(resultado["frase_fechamento"])
        self.assertIn("Acompanhamento continuo das demandas do turno", resultado["frase_fechamento"])
        self.assertIn(resultado["frase_fechamento"], resultado["texto"])


if __name__ == "__main__":
    unittest.main()
