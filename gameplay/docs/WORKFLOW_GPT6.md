# Gameplay — jointly authored full design

Process: factory_core/docs/WORKFLOW_GPT6.md. Design the player experience and
causal state changes together, not as a procession of workers/tables. Reuse the
adopted product, project standard and authorized repair scope. New meaning,
player work/outcomes, costs or material scope require the complete-design boundary.

The native design package contains the full authored work plus graph, actual
interaction contract and applicable composition artifacts. Their existing
validators remain; no fake v1 reviewer ids or rewritten historical hashes.
The Objective may be the natural full design text: the bridge no longer demands
legacy Markdown headings/table parsing to recover material decisions.

Human decision_sections must expose intent-scope, cycle-player-work,
two-lap-difference, alternatives-costs-recovery, scene-map, time-branches and
production-acceptance. These are output coverage categories, not thought order
or seven intermediate files. Each includes exact source text, linked decisions
and consequences. All project-specific material decisions must also appear.

System phases and player work are different. One work beat can cover several
ordered transitions. Automatic response, free looking, text, walking and return
prompts support the work but cannot pad required work counts. Meaningful options
must be distinct/reachable; show what changes, where/when it is perceived, why the
next action is available and how delays/failures alter legitimate knowledge.

Preserve complete causal loops, coupled product systems, concrete costs/recovery,
falsifiable hypotheses, two materially different laps and adopted project
composition requirements. Scene drawings must make current controls, distances,
obstacles, affordances and work visible; schematic boxes are not automatically
usable storyboards. Clock/phase and late-path work must agree with actual inputs.

UI production still follows UI_PRODUCTION_WORKFLOW.md, including scene/input/
logic boundaries, lifecycle, theme, locale and screenshots. Runtime still follows
RUNTIME_OBSERVATION_AND_ACCEPTANCE_CONTRACT.md and isolated blind/comparison
protocols. Produce within the reviewed paths; implementation completion is not
accepted gameplay. A failing test permits repair, not an invented design approval.

## Rules correctness (executable model)

Prose rules and worked examples drift apart. A design can bind an executable
rules model and a gameplay_rules_check.v1 record published by
`gameplay/rules_check.py run` (design field `rules_check`, also a design input).
The game-owned command prints a gameplay_rules_report.v1: invariants that must
hold in every reachable state, each with checked cases and violations, and every
worked example replayed as CONSISTENT or INCONSISTENT. The gate rejects a stale
model, any violation and any inconsistent example. It decides nothing about fun
or balance and never supplies game-specific invariants.

Required for studio/gameplay designs in the AUTONOMOUS authorship mode, with at
least one replayed example; optional and validated when present in COLLABORATIVE
mode. In AUTONOMOUS mode both reviewers judge `gameplay.rules_model_covers_design`:
the invariants cover the design's capacities, resources and legal-action states,
every worked example (laps, witnesses, mock frames) is replayed, and the model
states the same rules as the prose.

## Balance targets (declared by the design, not by the Factory)

Balance has no general rule, so the Factory supplies only a procedure. The same
report may carry `balance_targets`: each is the design's own measurable target
(metric, min/max bounds, how it was measured) and the value from each independent
run. A target is MET only when every run lies inside its bounds; an unmet target
blocks the design until it is retuned or the target itself is revised in a new
draft that reviewers see. In AUTONOMOUS mode at least one target is required and
each needs at least three independent runs (one seed's reading has misled before).
Both reviewers then judge `gameplay.balance_targets_declared_and_measured`: the
targets trace to the product promise and hypotheses, cover the design's main
levers (difficulty, dominant options, economy pacing) and use honest methods.

