---
type: "query"
date: "2026-07-24T00:05:37.096802+00:00"
question: "Faça mais uma passada focando em deixar as telas mais parecidas com o stich, remover o número de cards/bordas e deixar a tela ajustada sem vazamento no desktop"
contributor: "graphify"
outcome: "useful"
source_nodes: ["Central de Registros da Coordenação", "coordenacao.js", "ocorrencias_router.py"]
---

# Q: Faça mais uma passada focando em deixar as telas mais parecidas com o stich, remover o número de cards/bordas e deixar a tela ajustada sem vazamento no desktop

## Answer

Expanded from original query via vocab: [coordenacao, ocorrencia, layout, css, template, table, filter, drawer, panel]. The relevant surface is templates/coordenacao.html with behavior in painel.js and scoped CSS. Reduced nested surfaces and borders, made the coordination workspace shrinkable with width 100% and min-width 0, compacted the filter grid and table columns, shortened occurrence type labels, and converted row actions to accessible icon controls. Browser validation confirmed document width equals viewport and filter/table scroll widths equal client widths at 1280px; drawer and editor also remain within viewport.

## Outcome

- Signal: useful

## Source Nodes

- Central de Registros da Coordenação
- coordenacao.js
- ocorrencias_router.py