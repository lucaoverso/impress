---
type: "query"
date: "2026-07-19T17:32:24.474435+00:00"
question: "Faça um impeccable audit para detectar padrões não usados ainda nas telas do nosso sistema"
contributor: "graphify"
outcome: "useful"
source_nodes: ["School Suite Design System", "app_navbar.js"]
---

# Q: Faça um impeccable audit para detectar padrões não usados ainda nas telas do nosso sistema

## Answer

Expanded from original query via graph vocab: [design, token, component, template, css, navbar, card, chip, modal, drawer, empty, loading]. Static verification across 23 active templates found strong navbar/sidebar adoption, partial shared shell/header/form adoption, an unused action_button macro, unused legacy navbar drawer CSS, unused shared stat-card CSS, 13 custom role=dialog implementations versus 2 native dialog definitions, zero skeleton patterns, a global 400985-byte CSS bundle, and inconsistent semantic token aliases.

## Outcome

- Signal: useful

## Source Nodes

- School Suite Design System
- app_navbar.js