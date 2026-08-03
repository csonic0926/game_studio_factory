# Gameplay Factory Guide and AI Entry

This file is the canonical entry for an AI caller. Gameplay Factory exposes
one initialization entry, two ongoing production workflows, and one
just-in-time UI realization preflight:

1. **Factory initialization** — route a total-new project to game definition,
   reconstruct an existing repo joining in the middle, or recognize an already
   initialized repo.
2. **Progression production** — make/complete the primary progression's next
   unit and its gameplay.
3. **Gap repair** — close one concrete missing or broken gameplay contract
   inside an already-authored progression unit.
4. **UI production adapter** — before any UI-changing production plan,
   reconstruct and bind this repo's layout/state/scene construction grammar.

Runtime evidence reading remains independently invoked. Product/game direction
is owned by the umbrella Idea Factory; Gameplay initialization must not invent
it.

## 1. Resolve the target before routing

Resolve the game repo from explicit path -> current Git root -> ignored local
registry for an explicit project id. Never scan sibling repos.

Set:

```text
<GAMEPLAY_ROOT> = <GAME_REPO>/design/gameplay
```

Reject:

- this factory repo or any child as the game repo;
- any output outside the game repo;
- a blank or uninitialized repo disguised as factory-ready;
- committed absolute developer paths.

Determine initialization state before demanding adapters:

- blank/genre-only repo: `NEW_PROJECT_DEFINITION_REQUIRED`;
- existing game missing factory-readable state:
  `EXISTING_PROJECT_INIT_INPUT_REQUIRED`;
- complete trustworthy adapters/model/state: ordinary production.

Before routing, read `design/product/PRODUCT_THESIS.md` and applicable
`design/product/FACTORY_CONSTRAINTS.json` entries when present. If high-level
commercial/experiential direction is explicitly unresolved or Gameplay would
need to invent it, invoke the `idea-factory` skill first. Existing code alone
does not prove a product commitment.

For ordinary production, read the game-owned adapters/model:

```text
<GAMEPLAY_ROOT>/adapter/PROJECT_GAMEPLAY_PROFILE.md
<GAMEPLAY_ROOT>/adapter/PRODUCTION_ADAPTER.md
<GAMEPLAY_ROOT>/adapter/OBSERVATION_ADAPTER.md
<GAMEPLAY_ROOT>/adapter/GAMEPLAY_DESIGN_MODEL.json
```

Missing answers route an existing repo through initialization. Differing or
inconsistent existing factory state blocks for explicit remediation; ordinary
production never creates or overwrites it implicitly.

## 2. Route to exactly one workflow

| Current need | Operation | Workflow |
| --- | --- | --- |
| Initialize a new, existing, or already-ready game repo | `init_gameplay_factory` | [`docs/GAMEPLAY_FACTORY_INIT_WORKFLOW.md`](docs/GAMEPLAY_FACTORY_INIT_WORKFLOW.md) |
| Only repeat the bounded existing-project probe | `probe_existing_project` | Init Step 1 |
| Compile or check an existing-project init handoff | `compile_init` / `check_init` | Init Steps 3–4 |
| No concrete unresolved gap is known; continue or complete the main progression | `produce_objective` | [`docs/OBJECTIVE_GAMEPLAY_WORKFLOW.md`](docs/OBJECTIVE_GAMEPLAY_WORKFLOW.md) |
| A concrete player-visible causal contract is missing/broken inside an existing objective | `repair_gameplay_gap` | [`docs/GAMEPLAY_REPAIR_WORKFLOW.md`](docs/GAMEPLAY_REPAIR_WORKFLOW.md) |
| Only compile forward context | `prepare_objective` | Objective workflow Step 1 |
| Only author the forward gameplay table | `author_objective` | Objective workflow Step 2 |
| Explicit plan-only request for forward production | `plan_production` | Objective workflow Step 3 |
| Only compile a known repair context | `prepare_repair` | Repair workflow Step 1 |
| Explicit plan-only request for a repair | `plan_repair` | Repair workflow Step 3 |
| Prepare/check/refresh repo-specific UI construction before a UI-changing plan | `prepare_ui_production` / `check_ui_production` / `refresh_ui_production` | [`docs/UI_PRODUCTION_WORKFLOW.md`](docs/UI_PRODUCTION_WORKFLOW.md) |
| Validate/read runtime evidence | `observe_runtime` / `runtime_acceptance` | Reader/acceptance docs; never a creative entry |

### Routing priority

Initialization precedes production routing. Run `init.py start` once. A new
project routes to game definition; an existing project continues until
`GAMEPLAY_FACTORY_READY`; an already-ready repo proceeds directly. Do not
disguise missing adapters as objective authoring.

If a concrete repair gap and a request to advance progression are both active,
repair the known gap first unless the user explicitly defers it. Do not keep
advancing the main progression while leaving a known player-visible break
behind.

A gap must be concrete and evidenced. It may come from the user, runtime
observation, implementation research, a test failure, or fresh acceptance. Do
not invent a repair merely because a system could be improved.

For a continuing call, inspect the explicitly named/current game-owned
`design/gameplay/repairs/*/GAMEPLAY_GAP_INPUT.json` files:

- `OPEN` routes to repair before forward progression;
- `IMPLEMENTED_PENDING_ACCEPTANCE` routes to the named user/fresh-review
  closure boundary, not another production pass;
- `CLOSED` and user-authorized `DEFERRED` do not block forward progression.

Never scan sibling game repos for gaps.

If several gaps are `OPEN`, execute one repair at a time against the refreshed
repo. Prefer the gap that breaks the earliest currently reachable progression
window unless the user supplies another priority. Do not merge unrelated gaps
into one repair artifact or run overlapping repair plans concurrently.

### Fast distinction

Use **progression production** when the question is:

> What should the game's primary progression ask the player to do next, and
> what gameplay carries them to its completion?

Use **gap repair** when the question is:

> Within an existing objective, what promised action/consequence/state
> transition is missing or broken, and what is the smallest closure?

Use neither when:

- the request is only a genre/blank project — initialize, then route to game
  definition;
- it is an ordinary code bug with no material player-visible gameplay effect;
- it requests an unanchored new feature rather than a next objective or an
  evidenced existing gap.

Use **Factory initialization** when the repo lacks verified
adapters/model/state required to answer either production question.

## 3. Gameplay Factory initialization

The installed `gameplay-factory` skill is the normal user-facing entry. It
resolves the target/link and invokes this internal command automatically:

```bash
python3 gameplay/init.py start --game-repo <GAME_REPO>
```

Read the full initialization workflow and continue the returned branch without
asking the user to paste internal instructions.

### Total-new project

`NEW_PROJECT_DEFINITION_REQUIRED` routes to the installed `idea-factory` skill.
Do not create fake progression, actions, rewards, or adapters from only a genre
request. `IDEA_FACTORY_READY` establishes product direction; a separate
new-game Gameplay bootstrap remains responsible for initial progression and
action/reward design.

Open/no-fit/live-direction Idea Factory states are not failures and are not
product authority. Remain in product exploration; Gameplay must not force them
into `IDEA_FACTORY_READY` merely to continue its own workflow.

### Existing project joining in the middle

```text
existing foreign game repo
  -> init.py start
  -> GAMEPLAY_FACTORY_REPO_PROBE.json
  -> one evidence-focused investigator
  -> GAMEPLAY_FACTORY_INIT_INPUT.json
  -> init.py compile
  -> adapters + GAMEPLAY_DESIGN_MODEL + empty state ledgers
     + initial NEXT_GAMEPLAY_UNIT_INPUT
  -> init.py check
  -> GAMEPLAY_FACTORY_READY
```

The probe assigns no semantic authority. One investigator reconstructs only
existing runtime facts with exact repo-relative evidence. If the foreign repo
is not linked to this umbrella, run root `setup.py link` before `start`;
linkage supplies routing only and grants no gameplay authority. `compile`
creates only missing canonical files, never overwrites differing state,
rejects AI assumptions/unresolved material gaps, and reuses the production
material gate.

`NOT_AVAILABLE` observation capability is honest and may permit objective
design/production, but it blocks runtime evidence/acceptance claims until
instrumentation exists.

### Already initialized

`GAMEPLAY_FACTORY_ALREADY_READY` returns to this router. Validate current
materials, then route an `OPEN` repair first; otherwise use the current
objective frontier for progression production.

## 4. Progression production — mainline next unit

Read the full objective workflow. Its compact path is:

```text
stable GAMEPLAY_DESIGN_MODEL.json + small objective frontier input
  -> prepare.py context
  -> NEXT_GAMEPLAY_UNIT_CONTEXT.md
  -> one creative author
  -> OBJECTIVE_GAMEPLAY.md
  -> user-selected production planner
  -> PRODUCTION_PLAN_MANIFEST.json + production_plans/*.md
  -> plan.py validate
  -> original caller executes dependency-ready plans
```

The primary progression driver answers **what is next**. Gameplay is **how**
the player reaches it through actions and their consequences/rewards.

Only `READY_FOR_HOW_DESIGN` or `READY_FOR_NEW_GAMEPLAY_DESIGN` starts the one
Step 2 author. Only `READY_FOR_EXECUTION` starts production. For an ordinary
make/continue request, the caller executes the plans automatically rather than
asking the user to say “write the code”.

After design and before Step 3 planning, determine whether intended production
touches UI. If so, run the UI Production Adapter workflow first. Do not ask the
production planner to rediscover scene hierarchy, state ownership, responsive
composition, or validation conventions inside every plan. The adapter is
reusable game-owned production authority, and each UI plan selects the exact
relevant rule/exemplar/scenario ids plus adapter hash.

## 5. Gap repair — current/previous unit closure

Read the full repair workflow. It mirrors the compact four-step shape without
regenerating the base objective:

```text
exact existing OBJECTIVE_GAMEPLAY.md + one evidenced gap
  -> repair.py context
  -> GAMEPLAY_REPAIR_CONTEXT.md
  -> direct planning when authority already exists
     OR one bounded repair author -> GAMEPLAY_REPAIR.md
  -> user-selected repair planner
  -> REPAIR_PLAN_MANIFEST.json + production_plans/*.md
  -> repair_plan.py validate
  -> original caller executes dependency-ready repair plans
```

Step 1 returns:

- `READY_FOR_DIRECT_REPAIR_PLAN` — explicit design authority or a persisted
  user ruling already states the exact result; skip creative authoring;
- `READY_FOR_REPAIR_DESIGN` — the existing objective omitted or ambiguously
  specified the decision; author one small repair artifact;
- `BLOCKED_BY_REPAIR_MATERIAL` — evidence/anchor/authority is insufficient or
  conflicts with locked design.

The repair source and base objective are both SHA-bound. A bounded repair never
rewrites `OBJECTIVE_GAMEPLAY.md`, invents the successor progression unit, or
replans unrelated rows.

Only `READY_FOR_EXECUTION` begins implementation. Standard tests prove code,
data, and state behavior; final experiential closure remains with the user or
fresh acceptance reviewer named by the repair. Production changes the
game-owned gap status from `OPEN` to `IMPLEMENTED_PENDING_ACCEPTANCE`; it may
not self-mark `CLOSED`.

The same UI preflight applies to repair plans. A UI symptom does not authorize
the planner to patch only visible layout: it must preserve the adapter's state
ownership and scene-integration rules as well.

## Studio workflow-completion handoff

When either progression production or gap repair is owned by Game Studio
Factory, commit the runtime-affecting implementation before handoff and write
the small Studio-owned `STUDIO_WORKFLOW_COMPLETION.json` from
`studio/templates/STUDIO_WORKFLOW_COMPLETION.json`. It binds the exact revision,
design authorities, results, tests, unit ids, and production-context ids, while
remaining `IMPLEMENTED_PENDING_ACCEPTANCE`. Studio—not Gameplay—then obtains
fresh acceptance and promotes the baseline.

## Shared hard rules

- **Existing-project initialization reconstructs; it does not design.**
  Runtime evidence or persisted user rulings must settle every material claim.
- **Existing state is never overwritten.** After all-target preflight, init
  creates missing canonical files and blocks on any differing existing
  adapter/model/state.
- **Repository study stays bound.** Probe revision, declared dirty paths, and
  dirty working-tree content hash must still match at compile/check time.
- **Known gap before forward expansion.** Unless explicitly deferred, close a
  concrete known break before producing the next progression unit.
- **Primary progression first.** A mission, stage, spatial frontier, or
  equivalent driver answers what comes next; it need not branch.
- **What and how stay separate.** The progression objective is not itself the
  meaningful gameplay choice.
- **Script before creative tokens.** Never ask a creative worker to rediscover
  repo progression, scan all locales/code, or rebuild the stable action list.
- **Stable vocabulary is written once.** Keep progression/action/reward
  evidence in `GAMEPLAY_DESIGN_MODEL.json`; select ids per objective or repair.
- **Locale text is not code.** Runtime selection/completion wiring must exist.
- **Use the smallest sufficient escalation.** Reconfigure a situation,
  action, target, or consequence before adding a new action/system.
- **Plans compile; they do not redesign.** A real gap returns to the relevant
  author/authority owner rather than being silently invented by the planner.
- **Planning files are mandatory; Plan Mode is optional.** Downstream
  execution reads persisted files, never private chat state.
- **UI intent and UI construction stay separate.** Objective/repair design
  owns the required player-visible result; the checked game-owned UI
  Production Adapter owns layout, state refresh, scene/lifecycle, input/layer,
  responsive/localization, exemplar, and validation conventions.
- **No UI writes before UI authority.** A UI-changing plan must use manifest
  v2, exact adapter SHA, relevant rule/exemplar/scenario ids, and the matching
  Markdown contract. `touches_ui: false` may not hide explicit UI work.
- **Plan ownership is exclusive.** Shared planned paths across plans are
  invalid.
- **Bind production to exact design authority.** A changed objective or repair
  source makes its plans stale.
- **`READY_FOR_EXECUTION` is intermediate.** Continue through standard
  production unless the user explicitly requested plan-only output.
- **Factory completion is not fun/acceptance.** Normal tests and structure do
  not self-award an experience verdict.
- **Studio handoff is not promotion.** A workflow-completion record proves
  what was produced at which revision; only Studio admission can combine it
  with fresh acceptance and predecessor regression.
- **Artifacts land in the game repo.** Factory owns blank templates, schemas,
  tools, contracts, and tests only.
- **Ownership precedes writes.** Resolve all paths before any mkdir/write.
- **Paths stay portable.** Persist game-repo-relative paths.

## Runtime evidence boundary

`reader.py` validates and transforms runtime evidence. It does not prepare
creative context, invent gameplay, or issue a final experience verdict.

- Raw events, derived timelines, blind interpretations, and acceptance
  comparisons remain separate.
- Blind input contains no design semantics or hidden/future state.
- Evidence chains stay within one run/session/correlation chain.
- Controlled branch probes require complete independent branches.
- Negative checks distinguish satisfied no-match, violation, and incomplete
  coverage.
- Runtime observation may reveal a repair candidate; a user or fresh reviewer
  must record the concrete gap before the repair workflow treats it as work.

## Current contracts

### Entry and workflow contracts

- `docs/AI_CALLER_LANDING.md`
- `docs/GAMEPLAY_FACTORY_INIT_WORKFLOW.md`
- `docs/OBJECTIVE_GAMEPLAY_WORKFLOW.md`
- `docs/GAMEPLAY_REPAIR_WORKFLOW.md`

### Gameplay Factory initialization

- `init.py`
- `schemas/gameplay_factory_repo_probe.schema.json`
- `schemas/gameplay_factory_init_input.schema.json`
- `schemas/gameplay_factory_init_result.schema.json`
- `templates/GAMEPLAY_FACTORY_INIT_INPUT.json`

### Progression production

- `prepare.py`
- `schemas/next_gameplay_unit_input.schema.json`
- `schemas/gameplay_design_model.schema.json`
- `templates/GAMEPLAY_DESIGN_MODEL.json`
- `templates/NEXT_GAMEPLAY_UNIT_INPUT.json`
- `templates/OBJECTIVE_GAMEPLAY.md`
- `plan.py`
- `schemas/production_plan_manifest.schema.json`
- `templates/PRODUCTION_PLAN_MANIFEST.json`
- `templates/PRODUCTION_PLAN.md`

### Gap repair

- `repair.py`
- `schemas/gameplay_gap_input.schema.json`
- `templates/GAMEPLAY_GAP_INPUT.json`
- `templates/GAMEPLAY_REPAIR.md`
- `repair_plan.py`
- `schemas/repair_plan_manifest.schema.json`
- `templates/REPAIR_PLAN_MANIFEST.json`
- `templates/REPAIR_PRODUCTION_PLAN.md`

### Runtime evidence

- `reader.py`
- `docs/RUNTIME_OBSERVATION_AND_ACCEPTANCE_CONTRACT.md`
- `docs/PROJECT_ADAPTER_CONTRACT.md`
- `docs/OBSERVATION_READER.md`

The older Span Quant / Beat Sheet / walkthrough / packet lineage remains for
existing pilot artifacts. It is not the default entry for either compact Case
3 workflow.
