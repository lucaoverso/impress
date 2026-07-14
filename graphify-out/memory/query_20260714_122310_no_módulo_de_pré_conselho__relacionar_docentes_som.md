---
type: "query"
date: "2026-07-14T12:23:10.749984+00:00"
question: "No módulo de pré conselho, relacionar docentes somente às disciplinas que lecionam na respectiva turma"
contributor: "graphify"
outcome: "useful"
source_nodes: ["map_teaching_staff_by_classrooms", "gerar_texto_consolidado_pre_conselho"]
---

# Q: No módulo de pré conselho, relacionar docentes somente às disciplinas que lecionam na respectiva turma

## Answer

Expansão usada: preconselho, conselho, consolidado, docentes, professor, disciplinas, turma, turmas. A causa estava em map_teaching_staff_by_classrooms: o fallback da carga geral acrescentava todas as disciplinas do docente mesmo quando já existiam vínculos específicos por turma. O fallback agora só atua quando o docente ainda não foi mapeado naquela turma. Testes do serviço e das rotas passaram.

## Outcome

- Signal: useful

## Source Nodes

- map_teaching_staff_by_classrooms
- gerar_texto_consolidado_pre_conselho