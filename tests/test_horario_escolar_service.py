import unittest

from services import horario_escolar_service as service


class HorarioEscolarServiceTest(unittest.TestCase):
    def test_listar_faixas_turno_horario_respeita_turnos_do_sistema(self):
        matutino = service.listar_faixas_turno_horario("MATUTINO")
        vespertino = service.listar_faixas_turno_horario("VESPERTINO")
        vespertino_em = service.listar_faixas_turno_horario("VESPERTINO_EM")
        integral = service.listar_faixas_turno_horario("INTEGRAL")

        self.assertEqual([item["faixa_global"] for item in matutino], [1, 2, 3, 4, 5])
        self.assertEqual([item["faixa_global"] for item in vespertino], [6, 7, 8, 9, 10])
        self.assertEqual([item["faixa_global"] for item in vespertino_em], [6, 7, 8, 9, 10, 11])
        self.assertEqual([item["faixa_global"] for item in integral], [1, 2, 3, 4, 5, 7, 8, 9])

    def test_enriquecer_horario_escolar_inclui_faixa_e_label(self):
        item = service.enriquecer_horario_escolar(
            {
                "id": 10,
                "ano_letivo": 2031,
                "turma_id": 3,
                "disciplina_id": 8,
                "professor_id": 5,
                "dia_semana": "quinta",
                "aula_numero": 1,
                "turno": "VESPERTINO_EM",
            }
        )

        self.assertEqual(item["dia_semana"], "QUINTA")
        self.assertEqual(item["faixa_global"], 6)
        self.assertEqual(item["aula_label"], "1a aula (faixa 6)")
        self.assertEqual(item["turno_nome"], "Vespertino E.M.")


if __name__ == "__main__":
    unittest.main()
