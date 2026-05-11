import unittest
from services.pcpi_service import (
    GRUPO_AUTOMATICO_AUDIOVISUAL,
    GRUPO_AUTOMATICO_STE,
    agendamento_pertence_ao_turno_pcpi,
    gerar_texto_pcpi,
    turno_agendamento_pertence_ao_turno_pcpi,
)

SIMBOLO_ORDINAL_FEMININO = "\u00AA"
SIMBOLO_ORDINAL_MASCULINO = "\u00BA"


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
        self.assertIn("equipamentos audiovisuais", resultado["frases_automaticas"][1])
        self.assertIn("Bruno", resultado["frases_automaticas"][1])
        self.assertIn("Carla", resultado["frases_automaticas"][1])

    def test_preserva_simbolos_de_turma_e_formata_aula_com_ordinal(self):
        itens = [
            {
                "agendamento_id": 1,
                "data": "2026-04-03",
                "turno": "MATUTINO",
                "turno_nome": "Matutino",
                "aula": f"1{SIMBOLO_ORDINAL_FEMININO} aula",
                "faixa_global": 1,
                "recurso_id": 1,
                "recurso_nome": "STE Sala 1",
                "recurso_tipo": "Tecnologico",
                "professor_id": 1,
                "professor_nome": "Ana",
                "componentes": ["Matematica"],
                "turma": f"6{SIMBOLO_ORDINAL_MASCULINO} A",
                "tema_aula": "Atividade planejada",
                "observacao": "",
                "categoria_uso": GRUPO_AUTOMATICO_STE,
            },
            {
                "agendamento_id": 2,
                "data": "2026-04-03",
                "turno": "MATUTINO",
                "turno_nome": "Matutino",
                "aula": f"3{SIMBOLO_ORDINAL_FEMININO} aula",
                "faixa_global": 3,
                "recurso_id": 2,
                "recurso_nome": "STE Sala 1",
                "recurso_tipo": "Tecnologico",
                "professor_id": 2,
                "professor_nome": "Bianca",
                "componentes": ["Fisica"],
                "turma": f"3{SIMBOLO_ORDINAL_MASCULINO} EM A",
                "tema_aula": "Atividade planejada",
                "observacao": "",
                "categoria_uso": GRUPO_AUTOMATICO_STE,
            },
        ]

        resultado = gerar_texto_pcpi("2026-04-03", "MATUTINO", itens, [])

        frase = resultado["frases_automaticas"][0]
        self.assertIn(f"1{SIMBOLO_ORDINAL_FEMININO} aula", frase)
        self.assertIn(f"3{SIMBOLO_ORDINAL_FEMININO} aula", frase)
        self.assertIn(f"6{SIMBOLO_ORDINAL_MASCULINO} A", frase)
        self.assertIn(f"3{SIMBOLO_ORDINAL_MASCULINO} EM A", frase)

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
        self.assertIn("Impressao e organizacao de materiais pedagogicos", resultado["frases_manuais"][0])
        self.assertIn("Orientacao ao professor Daniela", resultado["frases_manuais"][1])
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
        self.assertIn("Acompanhamento cont", resultado["frase_fechamento"])
        self.assertIn(resultado["frase_fechamento"], resultado["texto"])

    def test_pcpi_usa_apenas_matutino_e_vespertino_com_equivalencias_do_agendamento(self):
        self.assertTrue(turno_agendamento_pertence_ao_turno_pcpi("MATUTINO", "MATUTINO"))
        self.assertTrue(turno_agendamento_pertence_ao_turno_pcpi("INTEGRAL", "MATUTINO"))
        self.assertTrue(turno_agendamento_pertence_ao_turno_pcpi("VESPERTINO_EM", "VESPERTINO"))
        self.assertTrue(turno_agendamento_pertence_ao_turno_pcpi("INTEGRAL", "VESPERTINO"))
        self.assertFalse(turno_agendamento_pertence_ao_turno_pcpi("VESPERTINO", "MATUTINO"))

    def test_pcpi_separa_aulas_do_integral_por_turno(self):
        agendamento_matutino = {"turno": "INTEGRAL", "aula": "5"}
        agendamento_vespertino = {"turno": "INTEGRAL", "aula": "6"}
        agendamento_matutino_ordinal = {
            "turno": "INTEGRAL",
            "aula": f"5{SIMBOLO_ORDINAL_FEMININO} aula",
        }
        agendamento_vespertino_ordinal = {
            "turno": "INTEGRAL",
            "aula": f"6{SIMBOLO_ORDINAL_FEMININO} aula",
        }

        self.assertTrue(agendamento_pertence_ao_turno_pcpi(agendamento_matutino, "MATUTINO"))
        self.assertFalse(agendamento_pertence_ao_turno_pcpi(agendamento_matutino, "VESPERTINO"))
        self.assertFalse(agendamento_pertence_ao_turno_pcpi(agendamento_vespertino, "MATUTINO"))
        self.assertTrue(agendamento_pertence_ao_turno_pcpi(agendamento_vespertino, "VESPERTINO"))
        self.assertTrue(agendamento_pertence_ao_turno_pcpi(agendamento_matutino_ordinal, "MATUTINO"))
        self.assertFalse(agendamento_pertence_ao_turno_pcpi(agendamento_matutino_ordinal, "VESPERTINO"))
        self.assertFalse(agendamento_pertence_ao_turno_pcpi(agendamento_vespertino_ordinal, "MATUTINO"))
        self.assertTrue(agendamento_pertence_ao_turno_pcpi(agendamento_vespertino_ordinal, "VESPERTINO"))


if __name__ == "__main__":
    unittest.main()
