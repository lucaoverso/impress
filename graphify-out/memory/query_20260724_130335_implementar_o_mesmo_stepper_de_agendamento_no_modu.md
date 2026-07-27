---
type: "query"
date: "2026-07-24T13:03:35.874728+00:00"
question: "Implementar o mesmo stepper de agendamento no modulo de impressao mantendo o mesmo design"
contributor: "graphify"
outcome: "useful"
source_nodes: ["workflow.js", "index.js", "agendamento.js", "impressao_router.py"]
---

# Q: Implementar o mesmo stepper de agendamento no modulo de impressao mantendo o mesmo design

## Answer

Expanded from original query via vocab: agendamento, impressao, printing, step, workflow, flow, template, index. O modulo de impressao ja possui um fluxo funcional de cinco etapas e atualiza is-current, is-ready e aria-current em static/js/printing/index.js. A diferenca principal e visual: o agendamento usa resumo textual da etapa e uma barra segmentada em templates/scheduling/index.html e static/css/pages/scheduling-stitch.css, enquanto a impressao ainda exibe circulos e rotulos. A menor mudanca e reaproveitar a mesma composicao no template e CSS de impressao, atualizando o resumo no JS, sem mudar rotas, backend ou regras do fluxo.

## Outcome

- Signal: useful

## Source Nodes

- workflow.js
- index.js
- agendamento.js
- impressao_router.py