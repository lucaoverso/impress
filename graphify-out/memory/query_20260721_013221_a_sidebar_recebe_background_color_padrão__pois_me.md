---
type: "query"
date: "2026-07-21T01:32:21.670239+00:00"
question: "a sidebar recebe background color padrão? Pois me parece haver divergencia entre as cores de acordo com o módulo. Em coordenacacao parece ter uma cor deferente de impressão. Vamos fazer uma rodada focada em aplicar nossas tokens corretamente, e evitar as cores literais no código css"
contributor: "graphify"
outcome: "dead_end"
source_nodes: ["coordenacao.js", "impressao_router.py"]
---

# Q: a sidebar recebe background color padrão? Pois me parece haver divergencia entre as cores de acordo com o módulo. Em coordenacacao parece ter uma cor deferente de impressão. Vamos fazer uma rodada focada em aplicar nossas tokens corretamente, e evitar as cores literais no código css

## Answer

Expanded from original query via graph vocab: [coordenacao, impressao, menu, token, tokens]. A travessia não localizou o CSS da sidebar; a inspeção direta encontrou static/css/components/app-sidebar.css e demonstrou que a diferença vinha do body de impressão usando surface-2. A correção centralizou a sidebar em --surface-sidebar e o body de impressão em --bg-main.

## Outcome

- Signal: dead_end

## Source Nodes

- coordenacao.js
- impressao_router.py