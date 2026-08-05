# Gameplay Factory

Gameplay Factory has one initialization entry, two compact gameplay-production
paths, and one just-in-time UI production preflight. The installed
`gameplay-factory` skill is the normal user/AI entry; it loads the canonical
router in [`AGENTS.md`](AGENTS.md).

Normal usage from the game repo is simply:

```text
/gameplay-factory <what gameplay to make, continue, or repair>
```

The skill links the repo if necessary and runs the internal initialization
entry. It distinguishes a total-new project, an existing project joining in
the middle, and an already initialized repo. Users do not select numbered
cases or type the internal commands. A new project routes to the specialist Idea
Factory for product definition; an existing project reconstructs existing
runtime meaning without designing gameplay:

```text
init.py start
  -> bounded repo probe
  -> one evidence-focused GAMEPLAY_FACTORY_INIT_INPUT.json
  -> init.py compile
  -> adapters + GAMEPLAY_DESIGN_MODEL + empty state + initial frontier
  -> init.py check
  -> GAMEPLAY_FACTORY_READY
```

The probe binds revision plus working-tree state. The compiler creates only
missing canonical files, refuses differing existing state, rejects unresolved
material gaps and AI assumptions, and reuses the production material gate.

**Progression production** makes/completes the primary progression's next unit:

```text
stable game-owned progression/action model + objective frontier
  -> prepare.py context                         # Step 1, mechanical
  -> NEXT_GAMEPLAY_UNIT_CONTEXT.md
  -> compact decision card + human verdict     # Step 2
  -> separate author -> OBJECTIVE_GAMEPLAY.md  # Step 2.5
  -> dual exact conformance reviews
  -> user-selected planner                     # Step 3
  -> PRODUCTION_PLAN_MANIFEST.json + production_plans/*.md
  -> plan.py validate
  -> original caller executes plans            # Step 4, automatic
```

**Gap repair** closes one evidenced player-visible break inside an existing
objective without regenerating it:

```text
exact existing OBJECTIVE_GAMEPLAY.md + one evidenced gap
  -> repair.py context
  -> GAMEPLAY_REPAIR_CONTEXT.md
  -> direct planning when authority already exists
     OR one bounded author -> GAMEPLAY_REPAIR.md
  -> user-selected repair planner
  -> REPAIR_PLAN_MANIFEST.json + production_plans/*.md
  -> repair_plan.py validate
  -> original caller executes repair plans
```

When both a concrete known gap and forward progression are active, repair the
gap first unless the user explicitly defers it.

**UI production preflight** runs only when an objective or repair will change
UI. It reconstructs this repo's working UI construction grammar once and binds
it into the production plan:

```text
ui.py start
  -> bounded non-semantic UI file probe
  -> one evidence-focused UI_PRODUCTION_ADAPTER_INPUT.json
  -> ui.py compile + check
  -> UI_PRODUCTION_ADAPTER.json/.md
  -> v2 plan selects exact adapter SHA + rule/exemplar/scenario ids
```

The investigation is revision/dirty-byte bound. Reuse is narrower: exact
fingerprints on cited UI convention sources mean unrelated commits do not
force another study, while a changed exemplar/state/scene source fails closed
and requires the explicit, integrity-checked `ui.py refresh` path.

This separates feature intent from UI realization. It prevents the production
model from guessing container/anchor structure, duplicating state/refresh
logic, breaking node paths/lifecycle/input/layers, or validating only one
viewport/locale/happy state. See
[`docs/UI_PRODUCTION_WORKFLOW.md`](docs/UI_PRODUCTION_WORKFLOW.md).

The previous quant-first chain remains present for existing pilot artifacts:

```text
Span Quant -> Gameplay Experience Beat Sheet -> walkthrough -> packets
```

It is not automatically run for new objective design while the compact
format is measured on real repos. Runtime evidence validation and blinded
acceptance remain separate downstream concerns.

## Initialization states

- `NEW_PROJECT_DEFINITION_REQUIRED` — a blank/genre-only repo routes to
  `idea-factory`; initial progression/action bootstrap remains distinct from
  product definition.
- `EXISTING_PROJECT_INIT_INPUT_REQUIRED` — one investigator reconstructs the
  existing progression/actions/rewards and adapters.
- `GAMEPLAY_FACTORY_ALREADY_READY` — use objective production or gap repair.
- `GAMEPLAY_FACTORY_READY` — the existing-project compile/check handoff is
  complete.

## Objective production — Step 1

`GAMEPLAY_DESIGN_MODEL.json` stores the primary progression driver and
action/reward vocabulary once. `prepare.py context` merges it with a small
per-objective frontier input, then verifies game-repo ownership, progression evidence,
locale text plus runtime wiring, the current/next objective, completion state,
and player actions with rewards. It emits:

- `READY_FOR_HOW_DESIGN`
- `READY_FOR_NEW_GAMEPLAY_DESIGN`
- `BLOCKED_BY_MATERIAL`

It never treats locale-only text as implemented gameplay and never creates an
output directory before ownership validation.

## Objective production — Steps 2 and 2.5

The human first approves a compact `GAMEPLAY_DECISION_CARD.json`. Studio-routed
cards bind a validated cycle-complete Studio gameplay-system manifest; direct
specialist cards bind the user's explicit bounded request. A separate author
then writes `OBJECTIVE_GAMEPLAY.md`. Two different fresh reviewers map every
card claim into the spec and every material spec item back to card claims. The
pair mappings must be exact inverses before
`GAMEPLAY_DESIGN_VERDICT.json` v2 can pass. From-scratch new gameplay cannot
substitute prior delegation for approval on the card, and the human is not
asked to review the generated full spec.

## Objective production — Step 3

The factory user may choose a Plan Mode model or an ordinary model. Both must
write the same persistent game-owned contract: one
`PRODUCTION_PLAN_MANIFEST.json` plus `N` Markdown plans split by coherent
change/file/state ownership. `plan.py validate` binds them to the exact
Factory revision, `OBJECTIVE_GAMEPLAY.md` SHA-256, and design verdict; it
requires coverage for every numbered row,
checks dependencies and portable repo paths, and rejects shared planned-file
ownership. The plans compile design into production requirements; they may
return `BLOCKED_BY_PLAN_GAP` but may not redesign gameplay silently.

Manifest v3 retains mandatory `ui_impact` and adds the design-verdict gate.
Non-UI plans explicitly declare false.
UI plans require a checked game-owned UI adapter, exact hash, selected rule/
exemplar/validation ids, and matching Markdown contract. Legacy v1/v2 manifests
are readable only through `check-historical` and cannot authorize execution.

## Objective production — Step 4

`READY_FOR_EXECUTION` is an intermediate control signal, not a final answer to
an ordinary "make gameplay" request. The original caller automatically
executes dependency-ready plans with normal coding/data work and invokes asset,
story, or sound factories when the plan requires them. Only an explicit
plan-only request stops after Step 3. Step 4 adds no Gameplay Factory reviewer;
normal production tests and validation remain part of the implementation work.

See [`docs/OBJECTIVE_GAMEPLAY_WORKFLOW.md`](docs/OBJECTIVE_GAMEPLAY_WORKFLOW.md).

## Gap repair

`repair.py context` binds an exact existing objective id/path/SHA and affected
rows to one concrete gap, exact runtime/implementation/test evidence, and only
the affected actions from the stable project model. It emits:

- `READY_FOR_DIRECT_REPAIR_PLAN`
- `READY_FOR_REPAIR_DESIGN`
- `BLOCKED_BY_REPAIR_MATERIAL`

Explicit existing requirements and persisted user rulings skip creative
authoring. Missing/ambiguous design gets one compact `GAMEPLAY_REPAIR.md`; the
base `OBJECTIVE_GAMEPLAY.md` remains unchanged.

`repair_plan.py validate` binds every repair plan to both the exact base
objective and exact repair source SHA-256, requires coverage for every repair
row, and enforces dependencies, portable ownership, and non-overlapping
planned paths. `READY_FOR_EXECUTION` automatically returns to production.
Tests prove implementation behavior but do not self-award final experiential
closure. Gap inputs persist routing state: `OPEN` enters repair,
`IMPLEMENTED_PENDING_ACCEPTANCE` waits for the named closure authority, and
only that user/fresh reviewer may mark `CLOSED`; `DEFERRED` requires a user
decision.

See
[`docs/GAMEPLAY_REPAIR_WORKFLOW.md`](docs/GAMEPLAY_REPAIR_WORKFLOW.md).

## Existing-project initialization internals

The `gameplay-factory` skill/AI caller, not the human user, continues an
`EXISTING_PROJECT_INIT_INPUT_REQUIRED` result through these internal commands:

```bash
python3 setup.py link --game-repo <GAME_REPO>

python3 gameplay/init.py compile \
  --game-repo <GAME_REPO> \
  --input design/gameplay/init/GAMEPLAY_FACTORY_INIT_INPUT.json

python3 gameplay/init.py check \
  --game-repo <GAME_REPO> \
  --input design/gameplay/init/GAMEPLAY_FACTORY_INIT_INPUT.json
```

See [`docs/GAMEPLAY_FACTORY_INIT_WORKFLOW.md`](docs/GAMEPLAY_FACTORY_INIT_WORKFLOW.md).

## Runtime evidence tooling

`reader.py` remains the dependency-free evidence tool. It validates raw
evidence, normalizes project mappings, reconstructs timelines, produces
runtime-blind inputs, prepares same-run causal evidence chains, and measures
declared budgets. It does not create gameplay or claim that an experience is
fun.

## Layout

```text
AGENTS.md                              hard caller rules
docs/GAMEPLAY_FACTORY_INIT_WORKFLOW.md
docs/OBJECTIVE_GAMEPLAY_WORKFLOW.md
docs/GAMEPLAY_REPAIR_WORKFLOW.md
init.py                             initialization router/probe/compiler/checker
prepare.py                             Step 1 context validator/compiler
plan.py                                Step 3 production-plan validator
design_gate.py                         exact design review/human verdict gate
repair.py                              repair context validator/compiler
repair_plan.py                         repair production-plan validator
ui.py                                  UI repo probe/compiler/checker
ui_binding.py                          shared plan-to-UI-adapter validator
schemas/next_gameplay_unit_input.schema.json
schemas/gameplay_design_model.schema.json
schemas/gameplay_factory_repo_probe.schema.json
schemas/gameplay_factory_init_input.schema.json
schemas/gameplay_factory_init_result.schema.json
schemas/production_plan_manifest.schema.json
schemas/gameplay_decision_card.schema.json
schemas/gameplay_design_conformance_review.schema.json
schemas/gameplay_design_verdict.schema.json
schemas/gameplay_gap_input.schema.json
schemas/repair_plan_manifest.schema.json
schemas/ui_production_repo_probe.schema.json
schemas/ui_production_adapter_input.schema.json
schemas/ui_production_adapter.schema.json
schemas/ui_production_adapter_result.schema.json
templates/GAMEPLAY_DESIGN_MODEL.json
templates/GAMEPLAY_FACTORY_INIT_INPUT.json
templates/NEXT_GAMEPLAY_UNIT_INPUT.json
templates/OBJECTIVE_GAMEPLAY.md
templates/GAMEPLAY_DECISION_CARD.json
templates/GAMEPLAY_DESIGN_CONFORMANCE_REVIEW.json
templates/GAMEPLAY_DESIGN_VERDICT.json
templates/PRODUCTION_PLAN_MANIFEST.json
templates/PRODUCTION_PLAN.md
templates/GAMEPLAY_GAP_INPUT.json
templates/GAMEPLAY_REPAIR.md
templates/REPAIR_PLAN_MANIFEST.json
templates/REPAIR_PRODUCTION_PLAN.md
templates/UI_PRODUCTION_ADAPTER_INPUT.json
reader.py                              runtime evidence reference tool
tests/                                 preparation + planning + reader tests
docs/*_CONTRACT.md                     current and previous-pilot contracts
```

Factory-side files are project-agnostic. Filled inputs, contexts, objective
gameplay, implementation artifacts, and evidence always land in the game repo.
