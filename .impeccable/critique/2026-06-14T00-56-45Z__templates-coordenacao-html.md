---
target: coordenacao.html
total_score: 21
p0_count: 0
p1_count: 4
timestamp: 2026-06-14T00-56-45Z
slug: templates-coordenacao-html
---
#### Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 2 | Table row selection changes state, but the interface has no visible details panel to explain what changed. |
| 2 | Match System / Real World | 3 | School language is mostly strong, but legal-maintenance flows still expose system structure more than the user's task. |
| 3 | User Control and Freedom | 2 | The modal wizard offers back/cancel, but record selection lacks a clear in-page escape hatch or secondary inspection surface. |
| 4 | Consistency and Standards | 3 | Tokens and component vocabulary are coherent, but the module mixes dashboard, maintenance, import, and wizard patterns at the same visual weight. |
| 5 | Error Prevention | 1 | Critical prerequisites, especially in Base legal and required legal links, are explained only by hints instead of enforced UI guardrails. |
| 6 | Recognition Rather Than Recall | 2 | Users must remember where tasks live and how legal hierarchy works; the interface reveals too many choices at once. |
| 7 | Flexibility and Efficiency | 3 | Filters, autocompletes, and live preview help experienced users move quickly. |
| 8 | Aesthetic and Minimalist Design | 2 | The page is calmer now, but the module still tries to be too many tools at once, especially in Base legal and Reports. |
| 9 | Error Recovery | 2 | Cancel actions exist, but there is little recovery guidance when a user makes the wrong choice or misses a prerequisite. |
| 10 | Help and Documentation | 1 | Inline hints exist, but there is no contextual teaching for the densest workflows. |
| **Total** | | **21/40** | **Acceptable** |

#### Anti-Patterns Verdict

**LLM assessment**: This no longer reads as obvious AI slop. The palette is restrained, the component system is coherent, and the page avoids the worst generic tropes. The remaining AI-like smell is not visual styling; it is information architecture by accumulation. The module still feels like several separate products compressed into one tabbed surface, especially once the user reaches Base legal.

**Deterministic scan**: `detect.mjs` returned `[]` for `templates/coordenacao.html` and `static/css/pages/coordenacao.css`, so there were no automated hits for the detector's anti-pattern rules in this scope.

**Visual overlays**: No reliable overlay is available for this run. Browser automation was not available in this environment, so Assessment B used the CLI detector only.

#### Overall Impression

The interface is more disciplined than before and the main occurrence flow is much easier to trust, but the module still asks one screen to handle daily operations, reporting, student maintenance, legal cataloging, and pre-registration triage at nearly the same hierarchy. The biggest opportunity is to reduce cognitive load by separating high-frequency work from administrative maintenance.

#### What's Working

- The `Registros` tab establishes a clear primary action with `Novo registro`, then supports it with summary counts and filtering instead of decorative chrome.
- The occurrence modal has a meaningful 3-step structure and the live document preview gives strong reassurance for a high-stakes workflow.
- Mobile accommodations are thoughtful in several places: responsive tables, sticky footer actions in the modal, and a dedicated preview toggle reduce total friction.

#### Priority Issues

- **[P1] Row selection promises detail but the page has no visible detail surface**
  - **Why it matters**: Clicking a record highlights the row, so users expect context to appear. The JS tries to render details into `#detalhesOcorrencia`, but that container is missing from the page. This breaks trust and turns selection into a dead-end state.
  - **Fix**: Add an in-page detail panel beside or below the table, or remove row-selection styling and treat the table as action-only. Don't keep an affordance that suggests deeper inspection without a destination.
  - **Suggested command**: `/impeccable shape`

- **[P1] The Base legal tab is a cognitive-load cliff**
  - **Why it matters**: One screen stacks law creation, article creation, inciso creation, alinea creation, JSON import, and the catalog table in a single long maintenance surface. First-time users have to understand hierarchy, sequence, and terminology before they can even begin.
  - **Fix**: Collapse this into progressive disclosure. Start with one chooser for the item type to create, reveal only the active form, and demote import into a secondary utility area.
  - **Suggested command**: `/impeccable distill`

- **[P1] High-frequency work and low-frequency maintenance still compete at the same hierarchy**
  - **Why it matters**: `Registros`, `Relatórios`, `Estudantes`, `Base legal`, and `Pre-registros` all sit in one tab row with near-equal visual weight, even though their urgency and usage frequency are very different. The product loses focus.
  - **Fix**: Reframe the module around the main operational task first, then move maintenance-heavy areas into secondary navigation, subsections, or dedicated routes.
  - **Suggested command**: `/impeccable layout`

- **[P1] Mobile discoverability is weakened by horizontally scrolling tabs with hidden scrollbars**
  - **Why it matters**: On small screens the user gets a horizontal tab strip, but the scrollbar is hidden and there is no visual cue that more destinations exist. Secondary areas like `Base legal` and `Pre-registros` become easy to miss.
  - **Fix**: Add a visible overflow cue, scroll shadows, partial next-tab reveal, or switch to a stacked/mobile navigation pattern for these destinations.
  - **Suggested command**: `/impeccable adapt`

- **[P2] Copy consistency still undercuts perceived quality in key moments**
  - **Why it matters**: The page mixes polished Portuguese with unaccented labels and system-facing wording such as `JSON ou CSV`, `Referencia`, `Acoes`, `Identificacao`, and `Descricao`. In a school workflow, those slips make the product feel less finished than it is.
  - **Fix**: Run a dedicated copy pass for all visible labels, hints, button text, and table headers. Normalize accents, casing, and wording by task frequency.
  - **Suggested command**: `/impeccable clarify`

#### Persona Red Flags

**Alex (Power User)**: The table supports fast scanning, but clicking a row produces selection styling without a visible detail destination, which wastes time and forces Alex into trial-and-error. The Base legal tab is also a one-item-at-a-time maintenance workflow with no fast path, no bulk affordance, and too much vertical travel.

**Jordan (First-Timer)**: The first action in `Registros` is clear, but confidence drops sharply in `Base legal`, where the interface assumes Jordan already understands the law → article → inciso → alinea hierarchy. Hidden horizontal tabs on mobile also make it easy for Jordan to never discover some sections.

**Casey (Distracted Mobile User)**: The modal's sticky actions help, but the tab strip hides overflow and the legal-maintenance surface is too long for an interrupted mobile session. Casey is also forced into large text-entry workflows in places where guided selection or progressive disclosure would reduce effort.

#### Minor Observations

- The live-preview script tag pointing at `http://localhost:8400/live.js` is still present in the template and should not survive into normal app markup.
- Reports still feel like a sibling product rather than a lightweight extension of the main records workflow because they repeat a near-identical filter experience.
- The visual system is strongest in `Registros`; the farther the user moves toward maintenance tasks, the more the page starts reading like an admin back office instead of one calm operational surface.

#### Questions to Consider

- Does `Base legal` belong inside the same module entry point as day-to-day occurrence handling, or is that just where it accumulated over time?
- If a coordinator only had 30 seconds between interruptions, what is the one action this page should optimize above all others?
- Should record selection teach and reassure with inline details, or should the table stop pretending selection itself is meaningful?
