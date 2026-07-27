---
type: "query"
date: "2026-07-21T15:18:04.565685+00:00"
question: "Mapear as telas e regras do módulo de agendamento para gerar no Stitch versões desktop e mobile de Novo agendamento, Meus agendamentos, Calendário geral e Catálogo de recursos"
contributor: "graphify"
outcome: "useful"
source_nodes: ["agendamento.js", "recursos_agendamento()", "SchedulingServiceTest"]
---

# Q: Mapear as telas e regras do módulo de agendamento para gerar no Stitch versões desktop e mobile de Novo agendamento, Meus agendamentos, Calendário geral e Catálogo de recursos

## Answer

Expanded from original query via vocab: [agendamento, agendamentos, agendar, calendario, catalogo, recurso, recursos, reserva, reservar, scheduling, template, router]. O fluxo existente usa templates/scheduling/index.html, my_bookings.html e calendar.html, com módulos/scheduling/router.py e static/js/agendamento.js. As regras preservadas incluem recurso ativo, capacidade por faixa, data ISO, turma ativa, aula permitida, tema obrigatório, professor resolvido por permissão, resumo antes de confirmar e cancelamento apenas de reserva futura pelo dono ou admin. O catálogo é conceitual e apenas docente, sem ações administrativas.

## Outcome

- Signal: useful

## Source Nodes

- agendamento.js
- recursos_agendamento()
- SchedulingServiceTest