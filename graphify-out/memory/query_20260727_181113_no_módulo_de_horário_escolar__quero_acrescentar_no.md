---
type: "query"
date: "2026-07-27T18:11:13.948623+00:00"
question: "No módulo de horário escolar. Quero acrescentar nos professores a aula atividade usada para planejamento, Preciso de um botão para criar aula atividade ai gera um cardzinho e eu consigo editar a grade do professor e alocar essa aula. Tem como implementar isso?"
contributor: "graphify"
outcome: "useful"
source_nodes: ["horario_escolar.js", "horario_escolar_router.py", "database.py"]
---

# Q: No módulo de horário escolar. Quero acrescentar nos professores a aula atividade usada para planejamento, Preciso de um botão para criar aula atividade ai gera um cardzinho e eu consigo editar a grade do professor e alocar essa aula. Tem como implementar isso?

## Answer

Expanded from original query via vocab: horario, escolar, professor, professores, aula, aulas, atividade, planejamento, grade, editar, router, service. Implementada persistência própria para aula atividade, rotas de criar, alocar, desalocar e excluir, integração na grade semanal por professor com card arrastável e controles acessíveis, validação de conflito com aulas comuns e migration automática. Testes do módulo, migrations e suíte completa passaram.

## Outcome

- Signal: useful

## Source Nodes

- horario_escolar.js
- horario_escolar_router.py
- database.py