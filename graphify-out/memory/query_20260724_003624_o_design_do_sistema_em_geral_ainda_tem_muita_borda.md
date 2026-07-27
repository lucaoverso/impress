---
type: "query"
date: "2026-07-24T00:36:24.652939+00:00"
question: "O design do sistema em geral ainda tem muita borda desnecessária. Muito padding tomando espaçamento desnecessário nada de acordo com o nosso DEISGN.md"
contributor: "graphify"
outcome: "useful"
source_nodes: ["School Suite Design System", "Sprint 6 — CSS Modular", "render_template_response()"]
---

# Q: O design do sistema em geral ainda tem muita borda desnecessária. Muito padding tomando espaçamento desnecessário nada de acordo com o nosso DEISGN.md

## Answer

Expanded from original query via graph vocab: [base, card, cards, css, design, layout, system, template]. The shared continuous-surfaces layer was the highest-leverage source: it already removed backgrounds and shadows but left local borders and padding, producing outlined transparent boxes. Added semantic density tokens in base.css; applied 16px page gutters, 12px surface padding, compact mobile spacing, transparent borders and square geometry for non-interactive internal surfaces while excluding links, buttons, dialogs, drawers, previews, metrics and page sections. Preserved independent interactive service/resource cards. Flattened admin tabs and fieldsets, changed report metric/insight card grids into divider-based strips, and changed the primary button from decorative gradient to the solid semantic brand token. Browser validation covered services, coordination, scheduling, printing, admin, reports and APC at desktop and mobile with no document overflow or console warnings.

## Outcome

- Signal: useful

## Source Nodes

- School Suite Design System
- Sprint 6 — CSS Modular
- render_template_response()