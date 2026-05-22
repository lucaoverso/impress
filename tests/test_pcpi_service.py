import unittest
from types import SimpleNamespace
from unittest.mock import patch

from services.pcpi_service import (
    GRUPO_AUTOMATICO_AUDIOVISUAL,
    GRUPO_AUTOMATICO_STE,
    agendamento_pertence_ao_turno_pcpi,
    carregar_contexto_pcpi,
    criar_registro_manual_pcpi,
    filtrar_itens_automaticos_pcpi,
    gerar_texto_completo_pcpi,
    gerar_texto_preview_pcpi,
    gerar_texto_pcpi,
    listar_registros_manuais_pcpi,
    montar_listagem_registros_manuais_pcpi,
    obter_usuario_id_pcpi,
    turno_agendamento_pertence_ao_turno_pcpi,
    validar_data_pcpi,
    validar_texto_obrigatorio_pcpi,
    validar_texto_opcional_pcpi,
    validar_turno_pcpi,
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

    def test_validadores_do_pcpi_normalizam_entradas(self):
        self.assertEqual(validar_data_pcpi("2026-04-03"), "2026-04-03")
        self.assertEqual(validar_turno_pcpi("matutino"), "MATUTINO")
        self.assertEqual(validar_texto_opcional_pcpi("  apoio  "), "apoio")
        self.assertEqual(
            validar_texto_obrigatorio_pcpi("  Planejamento  ", "Descricao curta"),
            "Planejamento",
        )

    def test_filtra_itens_automaticos_por_ids(self):
        itens = [
            {"agendamento_id": 1, "professor_nome": "Ana"},
            {"agendamento_id": 2, "professor_nome": "Bruno"},
        ]

        filtrados = filtrar_itens_automaticos_pcpi(itens, [2])
        self.assertEqual(len(filtrados), 1)
        self.assertEqual(filtrados[0]["professor_nome"], "Bruno")
        self.assertEqual(filtrar_itens_automaticos_pcpi(itens, []), [])

    def test_monta_listagem_de_registros_manuais_normalizando_turno(self):
        registros = [
            {"id": 1, "turno": "INTEGRAL", "descricao_curta": "Registro 1"},
            {"id": 2, "turno": "VESPERTINO", "descricao_curta": "Registro 2"},
        ]

        resposta = montar_listagem_registros_manuais_pcpi("2026-04-03", "VESPERTINO", registros)
        self.assertEqual(resposta["turno"], "VESPERTINO")
        self.assertEqual(resposta["turno_nome"], "Vespertino")
        self.assertEqual(resposta["total_registros"], 2)
        self.assertTrue(all(item["turno"] == "VESPERTINO" for item in resposta["itens"]))

    def test_obtem_usuario_id_positivo_ou_none(self):
        self.assertEqual(obter_usuario_id_pcpi({"id": "7"}), 7)
        self.assertIsNone(obter_usuario_id_pcpi({"id": 0}))
        self.assertIsNone(obter_usuario_id_pcpi({}))

    @patch("services.pcpi_service.listar_registros_pcpi_manuais_por_data")
    @patch("services.pcpi_service.listar_cargas_professores_pcpi_por_usuario_ids")
    @patch("services.pcpi_service.listar_agendamentos_pcpi_por_data")
    def test_carrega_contexto_usando_repository_no_service(
        self,
        mock_listar_agendamentos,
        mock_listar_cargas,
        mock_listar_registros,
    ):
        mock_listar_agendamentos.return_value = [
            {
                "id": 10,
                "usuario_id": 7,
                "turno": "MATUTINO",
                "aula": "1",
                "faixa_global": 1,
                "recurso_id": 3,
                "recurso_nome": "STE Sala 1",
                "recurso_tipo": "Tecnologico",
                "professor_nome": "Ana",
                "turma": "7A",
                "tema_aula": "Atividade",
                "observacao": "",
                "data": "2026-04-03",
            }
        ]
        mock_listar_cargas.return_value = {7: {"disciplinas": ["Matematica"]}}
        mock_listar_registros.return_value = [{"id": 1, "turno": "MATUTINO", "descricao_curta": "Apoio"}]

        sugestoes, registros = carregar_contexto_pcpi("2026-04-03", "MATUTINO")

        mock_listar_agendamentos.assert_called_once_with("2026-04-03")
        mock_listar_cargas.assert_called_once_with([7])
        mock_listar_registros.assert_called_once_with(data="2026-04-03")
        self.assertEqual(sugestoes["resumo"]["total_agendamentos"], 1)
        self.assertEqual(len(registros), 1)

    @patch("services.pcpi_service.listar_registros_pcpi_manuais_por_data")
    def test_lista_registros_manuais_no_service(self, mock_listar_registros):
        mock_listar_registros.return_value = [
            {"id": 1, "turno": "VESPERTINO", "descricao_curta": "Registro 1"},
            {"id": 2, "turno": "INTEGRAL", "descricao_curta": "Registro 2"},
        ]

        resposta = listar_registros_manuais_pcpi("2026-04-03", "VESPERTINO")

        self.assertEqual(resposta["total_registros"], 2)
        self.assertTrue(all(item["turno"] == "VESPERTINO" for item in resposta["itens"]))

    @patch("services.pcpi_service.criar_e_buscar_registro_pcpi_manual")
    def test_cria_registro_manual_no_service_com_campos_normalizados(self, mock_criar):
        mock_criar.return_value = {"id": 55, "descricao_curta": "Planejamento"}
        payload = SimpleNamespace(
            data="2026-04-03",
            turno="matutino",
            tipo_acao="planejamento",
            professor_nome="  Ana  ",
            componente="  Slides  ",
            turma=" 7A ",
            descricao_curta="  Planejamento  ",
            observacoes="  apoio  ",
        )

        resposta = criar_registro_manual_pcpi(payload, {"id": "9"})

        self.assertEqual(resposta["id"], 55)
        mock_criar.assert_called_once_with(
            data="2026-04-03",
            turno="MATUTINO",
            tipo_acao="planejamento",
            professor_nome="Ana",
            componente="Slides",
            turma="7A",
            descricao_curta="Planejamento",
            observacoes="apoio",
            criado_por_usuario_id=9,
            atualizado_por_usuario_id=9,
        )

    @patch("services.pcpi_service.carregar_contexto_pcpi")
    def test_gera_texto_completo_no_service(self, mock_carregar_contexto):
        mock_carregar_contexto.return_value = (
            {
                "itens": [
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
            },
            [{"tipo_acao": "registro", "descricao_curta": "apoio", "observacoes": ""}],
        )

        resposta = gerar_texto_completo_pcpi("2026-04-03", "MATUTINO")

        mock_carregar_contexto.assert_called_once_with("2026-04-03", "MATUTINO")
        self.assertEqual(resposta["total_agendamentos"], 1)
        self.assertEqual(resposta["total_registros_manuais"], 1)

    @patch("services.pcpi_service.carregar_contexto_pcpi")
    def test_gera_texto_preview_filtrando_ids_no_service(self, mock_carregar_contexto):
        mock_carregar_contexto.return_value = (
            {
                "itens": [
                    {"agendamento_id": 1, "professor_nome": "Ana", "categoria_uso": GRUPO_AUTOMATICO_STE},
                    {"agendamento_id": 2, "professor_nome": "Bruno", "categoria_uso": GRUPO_AUTOMATICO_STE},
                ]
            },
            [],
        )

        resposta = gerar_texto_preview_pcpi("2026-04-03", "MATUTINO", [2])

        self.assertEqual(resposta["total_agendamentos"], 1)
        self.assertIn("Bruno", resposta["texto"])


if __name__ == "__main__":
    unittest.main()
