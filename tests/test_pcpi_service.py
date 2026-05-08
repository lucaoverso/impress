import unittest
from unittest.mock import Mock, patch

from services.pcpi_ollama_service import PcpiOllamaError
from services.pcpi_service import (
    GRUPO_AUTOMATICO_AUDIOVISUAL,
    GRUPO_AUTOMATICO_STE,
    agendamento_pertence_ao_turno_pcpi,
    gerar_texto_base_pcpi,
    gerar_texto_pcpi,
    turno_agendamento_pertence_ao_turno_pcpi,
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

        self.assertEqual(resultado["origem_texto"], "local")
        self.assertEqual(resultado["total_agendamentos"], 3)
        self.assertEqual(len(resultado["frases_automaticas"]), 2)
        self.assertIn("Sala de Tecnologia Educacional (STE)", resultado["frases_automaticas"][0])
        self.assertIn("equipamentos audiovisuais", resultado["frases_automaticas"][1])
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

        self.assertEqual(resultado["origem_texto"], "local")
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

        self.assertEqual(resultado["origem_texto"], "local")
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

        self.assertTrue(agendamento_pertence_ao_turno_pcpi(agendamento_matutino, "MATUTINO"))
        self.assertFalse(agendamento_pertence_ao_turno_pcpi(agendamento_matutino, "VESPERTINO"))
        self.assertFalse(agendamento_pertence_ao_turno_pcpi(agendamento_vespertino, "MATUTINO"))
        self.assertTrue(agendamento_pertence_ao_turno_pcpi(agendamento_vespertino, "VESPERTINO"))

    def test_pcpi_usa_ollama_quando_habilitado(self):
        itens = [
            _agendamento(
                agendamento_id=1,
                categoria_uso=GRUPO_AUTOMATICO_STE,
                professor_nome="Ana",
                componentes=["Matematica"],
                turma="7A",
                aula="1",
                recurso_nome="STE Sala 1",
            )
        ]

        with patch.dict(
            gerar_texto_pcpi.__globals__,
            {
                "ollama_pcpi_habilitado": lambda: True,
                "gerar_texto_pcpi_ollama": lambda _contexto: "Texto final reescrito pela IA.",
            },
        ):
            resultado = gerar_texto_pcpi("2026-04-03", "MATUTINO", itens, [])

        self.assertEqual(resultado["origem_texto"], "ollama")
        self.assertEqual(resultado["texto"], "Texto final reescrito pela IA.")
        self.assertEqual(resultado["total_agendamentos"], 1)
        self.assertTrue(resultado["frases_automaticas"])

    def test_pcpi_mantem_fallback_local_quando_ollama_falha(self):
        itens = [
            _agendamento(
                agendamento_id=1,
                categoria_uso=GRUPO_AUTOMATICO_STE,
                professor_nome="Ana",
                componentes=["Matematica"],
                turma="7A",
                aula="1",
                recurso_nome="STE Sala 1",
            )
        ]

        def _falhar_ollama(_contexto):
            raise PcpiOllamaError("erro")

        with patch.dict(
            gerar_texto_pcpi.__globals__,
            {
                "ollama_pcpi_habilitado": lambda: True,
                "gerar_texto_pcpi_ollama": _falhar_ollama,
            },
        ):
            resultado = gerar_texto_pcpi("2026-04-03", "MATUTINO", itens, [])

        self.assertEqual(resultado["origem_texto"], "local")
        self.assertIn("Sala de Tecnologia Educacional", resultado["texto"])

    def test_texto_base_pcpi_permanece_deterministico_mesmo_com_ollama_habilitado(self):
        itens = [
            _agendamento(
                agendamento_id=1,
                categoria_uso=GRUPO_AUTOMATICO_STE,
                professor_nome="Ana",
                componentes=["Matematica"],
                turma="7A",
                aula="1",
                recurso_nome="STE Sala 1",
            )
        ]

        gerar_ia = Mock()
        with patch.dict(
            gerar_texto_base_pcpi.__globals__,
            {
                "ollama_pcpi_habilitado": lambda: True,
                "gerar_texto_pcpi_ollama": gerar_ia,
            },
        ):
            texto_base = gerar_texto_base_pcpi("2026-04-03", "MATUTINO", itens, [])

        gerar_ia.assert_not_called()
        self.assertIn("Sala de Tecnologia Educacional", texto_base)


if __name__ == "__main__":
    unittest.main()
