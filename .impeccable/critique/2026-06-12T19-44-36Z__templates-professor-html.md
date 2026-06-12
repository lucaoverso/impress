---
target: templates/professor.html
total_score: 22
p0_count: 0
p1_count: 4
timestamp: 2026-06-12T19-44-36Z
slug: templates-professor-html
---
## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|---|---:|---|
| 1 | Visibility of System Status | 2 | No visible global progress; important messages are visually hidden |
| 2 | Match System / Real World | 3 | Mostly school language, but "tag" and internal job terminology leak through |
| 3 | User Control and Freedom | 2 | Back and cancel exist, but drawers and dialogs have incomplete focus handling |
| 4 | Consistency and Standards | 2 | Local tokens, shapes and custom selection states diverge from the new system |
| 5 | Error Prevention | 2 | Progressive blocking exists, but the final review omits essential choices |
| 6 | Recognition Rather Than Recall | 2 | Users must remember teacher, class and selected pages |
| 7 | Flexibility and Efficiency | 3 | Paste, history reuse and automatic copy count are strong accelerators |
| 8 | Aesthetic and Minimalist Design | 2 | Nested elevated cards and decorative gradients fragment the task |
| 9 | Error Recovery | 2 | Messages exist, but several are hidden from sighted users |
| 10 | Help and Documentation | 2 | Local hints help, but mandatory material classification arrives late |
| **Total** | | **22/40** | **Acceptable: significant improvements needed** |

## Anti-Patterns Verdict

The interface has a solid product workflow, but the visual language still looks
like an older generated dashboard pattern: multiple gradients, 24px card radii,
wide shadows paired with borders, nested cards and repeated "Etapa X" kickers.
This conflicts with the continuous-workspace direction in `UI_GUIDELINES.md`.

The deterministic HTML detector returned zero findings. That is not a visual
approval: the main conflicts live in CSS and runtime-generated states, which
the markup-only scan does not evaluate.

## Overall Impression

The module understands printing well. Preview, quota, history reuse, automatic
copy count, high-consumption warning and the temporary cancellation window are
valuable domain features. The largest opportunity is to make that competence
legible through one continuous workspace with visible progress, persistent
context and a complete final review.

## What's Working

1. Progressive validation prevents users from advancing with invalid data.
2. Persistent desktop preview and structural mobile adaptation reduce mistakes.
3. History reuse, smart copy defaults and consumption warnings improve daily
   efficiency without requiring technical knowledge.

## Priority Issues

### [P1] The wizard does not expose the full journey

The template shows only repeated "Etapa X" labels. CSS and JavaScript reference
a stepper that is not present in the template, and the old progress CSS models
four steps while the workflow has five.

Why it matters: users cannot estimate effort or quickly reconstruct their
position after an interruption.

Fix: add the shared workspace header and a five-state semantic stepper, keeping
existing step IDs and state transitions.

Suggested command: `$impeccable layout`

### [P1] Final review is incomplete

The review shows file, copies, layout and estimated total, but omits teacher,
class, selected page range and material classification.

Why it matters: the final step does not protect against the most consequential
printing mistakes.

Fix: create persistent selection context and a complete definition list at the
review step. Place material classification before or clearly within the review,
with its requirement explained before submission.

Suggested command: `$impeccable clarify`

### [P1] Custom controls and secondary layers are not fully accessible

Layout and orientation buttons do not expose pressed state; preview cells are
clickable non-button elements; the history drawer lacks dialog semantics,
`inert`, focus containment and focus return.

Why it matters: keyboard and screen-reader users cannot reliably complete or
understand the same flow.

Fix: use native controls or complete ARIA state synchronization, make page
selection keyboard operable, and adopt the focus-management pattern used by
the scheduling drawers.

Suggested command: `$impeccable harden`

### [P1] Important feedback is visually hidden

Several validations write to `#msg`, but its parent `.print-legacy-support` is a
visually hidden 1px region.

Why it matters: sighted users may encounter disabled actions without a visible
reason or recovery instruction.

Fix: retain compatibility with the legacy message IDs while mirroring messages
into visible, contextual feedback regions near the active step and field.

Suggested command: `$impeccable clarify`

### [P2] Visual composition contradicts the continuous-surface system

The page defines its own palette, 24px radii and broad shadows, then nests
bordered configuration sections inside elevated step cards.

Why it matters: the module feels like a separate product and creates more
visual hierarchy than the task needs.

Fix: alias or remove local visual tokens, use the global semantic tokens, build
one workspace surface and separate internal groups with spacing, dividers and
subtle tonal backgrounds.

Suggested command: `$impeccable quieter`

## Cognitive Load

Three of eight checks fail, producing moderate cognitive load:

- material classification presents nine options at once;
- the final review requires recall of previous choices;
- configuration is dense on mobile despite being grouped.

The emotional low point is after upload, when the user loses sight of overall
progress. The intended confidence peak at review is weakened by missing data.

## Persona Red Flags

**Jordan, first-time teacher:** no page title or visible journey map; disabled
Continue actions can lack visible explanation; the mandatory material type is
discovered only at the end.

**Sam, keyboard and screen-reader user:** cannot select preview pages
reliably by keyboard; custom selection controls do not expose state; the drawer
does not isolate background content or restore focus.

**Casey, distracted mobile teacher:** nine material choices create a long final
decision; history actions are only 34px high; no global indicator helps recover
context after an interruption.

## Minor Observations

- The document title omits the accent in "Impressao".
- "Pedido", "impressao", "tag" and internal job terminology are inconsistent.
- `professor.css` contains duplicate visual systems and obsolete selectors.
- Some CSS variables referenced by the progress styles are not defined locally.
- The preview should support the current decision rather than compete for half
  of the desktop workspace in every post-upload step.

## Questions to Consider

- Should material classification become part of configuration, leaving review
  purely for confirmation?
- Which preview facts are needed in each step, and when can the preview become
  secondary?
- Can every current DOM ID remain stable while the visual structure is rebuilt
  around a single workspace?
