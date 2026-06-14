import unittest
from types import SimpleNamespace

from fastapi import HTTPException

from modules.scheduling.schemas import SchedulingReservationCreate
from modules.scheduling.service import (
    build_scheduling_options,
    cancel_scheduling_reservation,
    create_scheduling_reservation,
    ensure_resource_is_active,
    ensure_slot_has_capacity,
    validate_scheduling_period,
)


class SchedulingServiceTest(unittest.TestCase):
    def test_build_scheduling_options_returns_turnos_and_turmas(self):
        turnos_config = {
            "MATUTINO": {"nome": "Matutino", "aulas": 5},
            "VESPERTINO": {"nome": "Vespertino", "aulas": 6},
        }
        turmas_ativas = [
            {"nome": "7A", "turno": "MATUTINO", "quantidade_estudantes": 25},
            {"nome": "8B", "turno": "VESPERTINO", "quantidade_estudantes": 20},
        ]

        resultado = build_scheduling_options(turnos_config, turmas_ativas)

        self.assertIn("turnos", resultado)
        self.assertIn("grade_aulas", resultado)
        self.assertIn("aulas_globais", resultado)
        self.assertIn("turmas", resultado)
        self.assertEqual(len(resultado["turnos"]), 2)
        self.assertEqual(len(resultado["turmas"]), 2)
        self.assertEqual(resultado["turmas"][0]["turno_nome"], "Matutino")

    def test_validate_scheduling_period_accepts_valid_dates(self):
        periodo = validate_scheduling_period(
            data_inicio="2026-06-01",
            data_fim="2026-06-08",
            validar_data_agendamento=lambda value: value,
        )

        self.assertEqual(periodo["data_inicio"], "2026-06-01")
        self.assertEqual(periodo["data_fim"], "2026-06-08")

    def test_validate_scheduling_period_rejects_invalid_range(self):
        with self.assertRaises(HTTPException):
            validate_scheduling_period(
                data_inicio="2026-06-10",
                data_fim="2026-06-01",
                validar_data_agendamento=lambda value: value,
            )

    def test_ensure_resource_is_active_accepts_active_resource(self):
        recurso = {"ativo": 1}
        self.assertEqual(ensure_resource_is_active(recurso), recurso)

    def test_ensure_resource_is_active_rejects_inactive_resource(self):
        with self.assertRaises(HTTPException):
            ensure_resource_is_active({"ativo": 0})

    def test_ensure_slot_has_capacity_accepts_available_slot(self):
        recurso = {"quantidade_itens": 2}
        capacidade = ensure_slot_has_capacity(recurso, reservas_ativas_faixa=1)
        self.assertEqual(capacidade, 2)

    def test_ensure_slot_has_capacity_rejects_full_slot(self):
        with self.assertRaises(HTTPException):
            ensure_slot_has_capacity({"quantidade_itens": 1}, reservas_ativas_faixa=1)

    def test_create_scheduling_reservation_calls_repository_functions(self):
        payload = SchedulingReservationCreate(
            recurso_id=1,
            data="2026-06-10",
            aula="2",
            turma="7A",
            tema_aula="Planejamento",
            professor_id=None,
            observacao="Teste",
        )
        usuario = {"id": 1}

        buscar_recurso_called = []
        contar_reservas_called = []
        criar_agendamento_called = []

        def buscar_recurso_por_id(recurso_id):
            buscar_recurso_called.append(recurso_id)
            return {"id": recurso_id, "ativo": 1, "quantidade_itens": 3}

        def validar_turma(turma):
            return {"nome": turma, "turno": "MATUTINO"}

        def validar_data_agendamento(data_txt):
            return data_txt

        def validar_tema_aula(tema_aula):
            return tema_aula

        def validar_aula(aula, turno):
            return aula

        def calcular_faixa_global(turno, aula):
            return 2

        def resolver_usuario_professor_selecionado(usuario, professor_id, contexto=None):
            return {"id": usuario["id"]}

        def contar_agendamentos_ativos_faixa(recurso_id, data, faixa_global):
            contar_reservas_called.append((recurso_id, data, faixa_global))
            return 1

        def criar_agendamento(**kwargs):
            criar_agendamento_called.append(kwargs)
            return 42

        resultado = create_scheduling_reservation(
            payload=payload,
            usuario=usuario,
            turnos_config={"MATUTINO": {"nome": "Matutino", "aulas": 5}},
            validar_data_agendamento=validar_data_agendamento,
            validar_turma=validar_turma,
            validar_tema_aula=validar_tema_aula,
            validar_aula=validar_aula,
            calcular_faixa_global=calcular_faixa_global,
            resolver_usuario_professor_selecionado=resolver_usuario_professor_selecionado,
            buscar_recurso_por_id=buscar_recurso_por_id,
            contar_agendamentos_ativos_faixa=contar_agendamentos_ativos_faixa,
            criar_agendamento=criar_agendamento,
        )

        self.assertEqual(resultado["mensagem"], "Agendamento realizado com sucesso.")
        self.assertEqual(resultado["agendamento_id"], 42)
        self.assertEqual(buscar_recurso_called, [1])
        self.assertEqual(len(criar_agendamento_called), 1)

    def test_cancel_scheduling_reservation_calls_repository_functions(self):
        usuario = {"id": 1}

        def buscar_agendamento_por_id(agendamento_id):
            return {"id": agendamento_id, "status": "ATIVO", "data": "2099-06-12", "usuario_id": 1}

        def cancelar_agendamento(agendamento_id):
            return True

        resultado = cancel_scheduling_reservation(
            agendamento_id=5,
            usuario=usuario,
            usuario_eh_admin=lambda usuario: False,
            buscar_agendamento_por_id=buscar_agendamento_por_id,
            cancelar_agendamento=cancelar_agendamento,
        )

        self.assertEqual(resultado["mensagem"], "Agendamento cancelado com sucesso.")

    def test_cancel_scheduling_reservation_rejects_non_owner(self):
        with self.assertRaises(HTTPException):
            cancel_scheduling_reservation(
                agendamento_id=5,
                usuario={"id": 2},
                usuario_eh_admin=lambda usuario: False,
                buscar_agendamento_por_id=lambda agendamento_id: {"id": agendamento_id, "status": "ATIVO", "data": "2099-06-12", "usuario_id": 1},
                cancelar_agendamento=lambda agendamento_id: True,
            )
