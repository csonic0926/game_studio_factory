# Objective-gameplay workflow

This is the **progression-production** workflow: it makes or completes the
primary progression's next unit. A concrete gameplay gap inside an existing
unit belongs to
[`GAMEPLAY_REPAIR_WORKFLOW.md`](GAMEPLAY_REPAIR_WORKFLOW.md)
instead. If both are active, repair the known gap first unless the user
explicitly defers it.

This is the current token-efficiency pilot for a game repo that Gameplay
Factory can already continue. It replaces repeated repo study and the previous
multi-author design front end with one mechanical context compilation, one
compact human decision surface, one full spec, two exact conformance checks,
and one persistent production-planning contract.

It does not initialize a blank or foreign repo and does not change the independent
runtime evidence reader. It also does not rewrite an already-authored objective
merely to close one local runtime/design omission.

## Readiness boundary

If the primary progression driver, objective source, or action/reward source
cannot be established, run Gameplay Factory initialization rather than
authoring an objective.

If the requested work instead names a concrete player-visible causal break
inside an existing `OBJECTIVE_GAMEPLAY.md`, the operation is
`repair_gameplay_gap`, not `produce_objective`.

## Object model

The primary progression driver is the outer state transition:

```text
progression unit N -> completion -> progression unit N+1
```

It may be a linear mission chain, stage sequence, scenario sequence without a
level menu, or a spatial next-point-of-interest frontier. It answers **what is
next**; it need not branch and is not itself the meaningful choice.

Gameplay is the inner path:

```text
next objective
  -> player actions and their rewards/consequences
  -> concrete problems, activities, pressure, desires, and decisions
  -> objective completion
```

For Studio-routed work, both sit inside a prior gameplay-system cycle:

```text
decision -> commitment -> resolution -> reward -> reinvestment
  -> changed next decision
```

Studio owns that system. The objective may be a bounded vertical slice of it,
but may not cut a load-bearing edge and turn it into a linear episode.

## Step 1 — prepare the next gameplay unit

Step 1 is script-first and non-creative. A stable game-owned
`<GAMEPLAY_ROOT>/adapter/GAMEPLAY_DESIGN_MODEL.json` records once:

- the primary progression driver and exact repo evidence;
- implemented player actions and their rewards/consequences;
- project-wide recent patterns and constraints.

A small per-objective input then declares:

- whether the factory must complete the active unit or advance one unit;
- the player-facing objective locale key and expected text;
- runtime objective-selection and completion evidence;
- whether the post-completion successor is wired;
- applicable action ids selected from the stable model;
- objective-local recent patterns and constraints.

Use the schema/template:

- `schemas/next_gameplay_unit_input.schema.json`
- `schemas/gameplay_design_model.schema.json`
- `templates/GAMEPLAY_DESIGN_MODEL.json`
- `templates/NEXT_GAMEPLAY_UNIT_INPUT.json`

Then run:

```bash
python3 gameplay/prepare.py context \
  --game-repo <GAME_REPO> \
  --input design/gameplay/objective_gameplay/<objective_id>/NEXT_GAMEPLAY_UNIT_INPUT.json \
  --out design/gameplay/objective_gameplay/<objective_id>/NEXT_GAMEPLAY_UNIT_CONTEXT.md
```

`prepare.py` resolves ownership before any mkdir/write, merges the stable model
without sending it to a creative worker, checks every repo path
and exact evidence token, reads the locale CSV, requires runtime selection and
completion proof, validates actions/rewards, and emits one compact context.

### Readiness states

- `READY_FOR_HOW_DESIGN` — objective and action/reward materials are proven.
- `READY_FOR_NEW_GAMEPLAY_DESIGN` — objective materials are proven but no
  applicable implemented action exists; this is a legitimate new-gameplay
  trigger, not missing evidence.
- `BLOCKED_BY_MATERIAL` — the progression/objective/action declaration is
  missing, stale, text-only, or cannot be verified against the repo.

The script checks structural/evidential readiness. It does not decide whether
the actions make good gameplay.

## Step 2 — freeze the compact human decision surface

Do not ask a human to validate a generated full spec. First author the bounded
`GAMEPLAY_DECISION_CARD.json` using
`schemas/gameplay_decision_card.schema.json` and its template. It contains only:

- one player promise;
- three to six core-cycle steps;
- one to five load-bearing commitments;
- one to four red lines;
- at most three explicitly falsifiable hypotheses.

For `STUDIO_WHOLE_GAME`, the card binds the exact validated
`STUDIO_GAMEPLAY_SYSTEM_MANIFEST.json`; `studio/cycle.py` must return
`STUDIO_GAMEPLAY_SYSTEM_READY`. Its player promise and ordered core cycle are a
deterministic projection of the system promise and cycle transitions
(`player_action -> visible_consequence -> motivation_effect`); every coupled
system and forbidden linearization must appear verbatim. Objective-specific
commitments may be added only as visible `scope.*` claims. Thus the card cannot
silently rewrite the validated system before the human sees it. For
`DIRECT_SPECIALIST`, the card must derive
from an explicit bounded user request rather than an inferred whole-game
system.

The human rules on this card. `READY_FOR_NEW_GAMEPLAY_DESIGN` requires
`USER_APPROVED`; delegation is insufficient. The card is not a summary
generated after the full spec—it is the material authority the full spec must
refine.

`decision_payload_sha256` hashes only the compact material fields, not the
later recorded verdict. When requesting the ruling, show only the rendered
promise/cycle/commitments/red-lines/hypotheses card—do not dump reconstruction,
research, or the future full spec—and request exactly:

```text
USER_APPROVED <decision_payload_sha256>
```

Render the short card and token deterministically:

```bash
python3 gameplay/design_gate.py render-card \
  --card design/gameplay/objective_gameplay/<objective_id>/GAMEPLAY_DECISION_CARD.json
```

Persist that exact token as `human_verdict.source_text`. The validator
recomputes the payload hash, avoiding the circular error where recording the
verdict changes the artifact SHA that the user supposedly approved.

## Step 2.5 — author the full spec and prove exact refinement

A different creative context reads the approved card plus
`NEXT_GAMEPLAY_UNIT_CONTEXT.md` and writes `OBJECTIVE_GAMEPLAY.md`. It may infer
operational detail needed to realize the commitments, but it may not introduce
a new material design decision. The full spec records an `Author context id`
and contains only the canonical material sections:

```text
Objective
Expected player experience
numbered gameplay rows
New gameplay additions
Completion handoff
```

Free prose and extra headings are forbidden in this compact authority. This is
not stylistic: the validator inventories every allowed material line so a
generated paragraph cannot hide an unapproved mechanic outside the
spec-to-card mapping.

Two different fresh reviewer contexts—neither author nor either prior Studio
system reviewer—then write:

```text
GAMEPLAY_CONFORMANCE_CARD_TO_SPEC.json
GAMEPLAY_CONFORMANCE_SPEC_TO_CARD.json
```

The first maps **every card claim id** to exact finite spec refs. The second
inventories **every material spec ref** and maps it back to card claim ids. The
validator requires the two pair sets to be exact inverses, with no
contradiction, ambiguity, unsupported material decision, or blocker.
Validation hypotheses may map only to `expected.*` acceptance claims; they
cannot by themselves authorize a gameplay row, addition, or completion rule.

This relation is refinement, not identity:

```text
FullSpec refines DecisionCard
  = card->spec completeness
  + spec->card non-expansion
```

Only then write `GAMEPLAY_DESIGN_VERDICT.json` v2 with
`PASS_DESIGN_CONFORMANCE`. It binds the exact card, objective, both reviews,
and Factory revision. Any material edit changes a SHA and invalidates planning.
Legacy v1 verdicts are historical-only; they cannot authorize new production.

## Step 3 — compile persistent production plans

Step 3 leaves creative design and inspects the real repo to translate
`OBJECTIVE_GAMEPLAY.md` into executable change units. The factory user chooses
the planning model and protocol:

- a Plan Mode model may investigate and author the files;
- a model without Plan Mode may author the same files directly.

First classify the intended work types. If any change touches UI, scene UI,
HUD, menu/modal/overlay, responsive composition, or localization fit, complete
[`UI_PRODUCTION_WORKFLOW.md`](UI_PRODUCTION_WORKFLOW.md) before authoring the
plans. This is a bounded reusable repo-convention preflight, not a new creative
review. It prevents the planner/coding model from inventing a generic scene,
layout, state-refresh, or input/layer architecture from the gameplay table.

The choice never changes the artifact contract. Before production, both write:

```text
<objective_dir>/PRODUCTION_PLAN_MANIFEST.json
<objective_dir>/production_plans/<plan_id>_<change_unit>.md
```

Use:

- `schemas/production_plan_manifest.schema.json`
- `templates/PRODUCTION_PLAN_MANIFEST.json`
- `templates/PRODUCTION_PLAN.md`

Manifest v3 binds the Factory Git revision, exact UTF-8 SHA-256 of
`OBJECTIVE_GAMEPLAY.md`, and objective-local `GAMEPLAY_DESIGN_VERDICT.json`. It maps
every numbered row to `IMPLEMENT`, `VERIFY_EXISTING`, or
`NO_CHANGE_REQUIRED`, declares dependencies and exclusive planned-path
ownership, and records any blocking gap. Each Markdown plan preserves the
player-visible result, exact repo reuse/evidence, owned production changes,
locked non-goals, deterministic verification, and handoff.

Manifest v3 requires `ui_impact` on every plan. Non-UI plans declare false
with empty binding fields. UI plans bind the exact checked
`UI_PRODUCTION_ADAPTER.json` SHA and select relevant rule, exemplar, and
validation-scenario ids; their Markdown repeats that selection under
`## UI realization contract`. Legacy v1/v2 manifests are historical-check
inputs only and cannot authorize new execution:

```bash
python3 gameplay/plan.py check-historical \
  --game-repo <GAME_REPO> --manifest <LEGACY_MANIFEST>
```

`N` is determined by coherent execution and verification boundaries. Do not
make one plan per table row, split two plans that both mutate the same file, or
leave essential planning knowledge only in ephemeral Plan Mode/session state.
The planner may identify a precise `BLOCKED_BY_PLAN_GAP`, but it may not
redesign gameplay or start a generic review loop.

Validate before execution:

```bash
python3 gameplay/plan.py validate \
  --game-repo <GAME_REPO> \
  --manifest design/gameplay/objective_gameplay/<objective_id>/PRODUCTION_PLAN_MANIFEST.json
```

Only `READY_FOR_EXECUTION` hands the persistent plans to production. This is
structural planning readiness, not a gameplay-experience verdict.

## Step 4 — automatically execute production

For a normal high-level request to create or continue gameplay,
`READY_FOR_EXECUTION` is not a valid stopping point. The same caller, or its
outer orchestrator when the planning model cannot mutate the repo, must
immediately:

1. select plans whose declared dependencies are complete;
2. execute their owned code/data/UI/localization work directly;
3. invoke asset, sound, story, or other factories only when the plan's work
   types require them;
4. run the standard project tests/build/asset validation belonging to that
   production work;
5. for UI plans, execute every selected adapter scenario across its states,
   viewport, input, and localization profile rather than accepting one
   happy-state screenshot;
6. continue until every plan is implemented or an exact external blocker is
   reached.

This step adds no new Gameplay Factory author, packet, reviewer, or runtime
acceptance gate; the exact design verdict was already required before planning.
It is the control-flow instruction that prevents a user who simply asks
the AI Factory to make gameplay from receiving plans and then having to ask a
second time for implementation. Stop after Step 3 only for an explicit
plan-only request or an environment that has no execution-capable caller; in
the latter case report that exact capability blocker and the persisted plan
paths rather than implying the gameplay was produced.

## Calibration boundary

Do not regenerate Span Quant, Beat Sheet, walkthroughs, or packets merely to
preserve the previous workflow shape. The human-facing surface is the compact
decision card; the full spec remains AI-operational detail and becomes
authority only after exact dual conformance. Runtime observation and post-build
human playtest acceptance remain separate from this pre-production gate and,
for Studio work, must demonstrate the same two-lap cycle on the exact build.
