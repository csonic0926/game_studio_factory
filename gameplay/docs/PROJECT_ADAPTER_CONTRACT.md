# Gameplay Project Adapter Contract v1

## Ownership model

Gameplay Factory core is project-agnostic. The factory owns contracts,
schemas, reader tools, and blank answer sheets. Each game repo owns filled
answers and versions them beside the code/data/evidence they describe.

There are four initialization/pre-Card answer surfaces and one just-in-time UI
production surface:

1. **Project Gameplay Profile** — player frames, verbs, systems, spaces,
   engagement generators, presentation/control, grammar, budgets, and review.
2. **Project Gameplay Decision Card Authoring Standard** — the game-owned,
   human/project-adopted vocabulary, composition granularity, player-work,
   resolution/failure/validation rules, and finite rendered-Card checklist.
3. **Production Adapter** — how approved packets land into runtime code/data,
   other factories, and mechanical validation.
4. **Observation Adapter** — how instrumentation captures actual play, maps it
   to canonical evidence, supports reproducible sessions/probes, and blinds
   the runtime reader.
5. **UI Production Adapter** — how this repo owns layout, view state/refresh,
   scene lifecycle, input/layers, responsive/localized composition, accepted
   visual grammar/exemplar provenance, and split structural/visual UI
   validation. It is required only before UI work.

Production tests cannot substitute for observation. The Observation Adapter
may physically be a mandatory independent section of the Production Adapter,
but its ownership, completeness, version, and blocker semantics remain
separate. The factory blank template uses a separate file.

Objective authoring additionally requires a compact machine-checked
projection, `GAMEPLAY_DESIGN_MODEL.json`. It does not replace the four answer
surfaces; it records the primary progression driver plus implemented player
actions/rewards once so every objective worker does not reread and summarize
the full profile/codebase.

## Canonical location

```text
<GAME_REPO>/design/gameplay/adapter/
  PROJECT_GAMEPLAY_PROFILE.md
  PROJECT_GAMEPLAY_DECISION_CARD_STANDARD.json
  PRODUCTION_ADAPTER.md
  OBSERVATION_ADAPTER.md
  GAMEPLAY_DESIGN_MODEL.json
  UI_PRODUCTION_ADAPTER.json       # just-in-time when UI production is needed
  UI_PRODUCTION_ADAPTER.md         # derived readable projection
```

Factory blanks remain under `gameplay/adapters/_template/`.

## Portable roots and resolution

`<GAME_REPO>` is an active-call absolute Git root. `<GAMEPLAY_ROOT>` is the
fixed `<GAME_REPO>/design/gameplay`. Neither absolute path is stored in filled
answers. Versioned paths are relative to the game repo.

Resolve in this order:

1. explicit game-repo path in the invocation;
2. current working directory's Git root;
3. ignored `gameplay/adapters/registry.local.md`, only for an explicit
   project id.

Then read all four answer surfaces at the fixed adapter location. Objective
preparation additionally reads `GAMEPLAY_DESIGN_MODEL.json`. Reject
a game root inside this factory. Never scan siblings, borrow another factory's
registry, infer a game from engine code, or commit developer paths.

A missing initialization-time file, `TBD`, inconsistent version, missing referenced file, or
undeclared capability produces `BLOCKED_BY_ADAPTER`. A required acceptance
kernel that the Observation Adapter cannot support produces
`BLOCKED_BY_OBSERVABILITY` before packet production.

The optional UI adapter is not required to author gameplay. It is a hard gate
before a UI-changing production plan. Run `UI_PRODUCTION_WORKFLOW.md` to create
or refresh it; do not inflate existing-project initialization by reconstructing
UI when the next production change does not touch UI.

## Project Gameplay Profile answers

The profile declares:

- project id and authoritative story/current-state sources;
- primary locale, game mode/platform assumptions, and target player frames;
- core fantasy/player desires and gameplay sovereignty/red lines;
- implemented or production-approved verbs and their preconditions/results;
- systems, spaces, engagement/decision/challenge generators, and
  failure/retry conventions;
- presentation modes, control ownership, camera/HUD/feedback capabilities;
- gameplay grammar/rhythm/repetition/expectation/handoff conventions;
- explicit time, complexity, content, asset, sound, engineering, and
  attention budgets;
- approval owner, USER-ruling evidence, and human playtest evidence;
- the canonical game-repo-relative path, exact version, SHA-256, and `ACTIVE`
  status of the project-owned Gameplay Decision Card authoring standard.

Project-specific verbs, modes, budgets, or commercial/fantasy rulings in
factory core are defects.

## Project Gameplay Decision Card authoring answers

The standard is a mandatory versioned game-repo artifact for every new or
materially revised Card under both `STUDIO_WHOLE_GAME` and
`DIRECT_SPECIALIST`. It declares the project's vocabulary, repeatable-lap
meaning, player-work boundary, required composition/interaction granularity,
control/input/judgment/response/persistent-return detail, resolution and
time/resource settlement, failure/recovery/replay,
project-permitted validation methods, reviewer independence, synchronization,
composition artifact kinds, complete requirement inventory, and finite
render-only checklist.

The Factory provides only a blank answer sheet. `DRAFT_NOT_ADOPTED`, `TBD`,
missing, absolute-path, machine-local, Factory-owned, another-project, or
AI-inferred standards are not active. The active standard must record explicit
human/project adoption and bind a committed collaboration contract that points
back to its canonical path. Read
[`PROJECT_CARD_AUTHORING_STANDARD_WORKFLOW.md`](PROJECT_CARD_AUTHORING_STANDARD_WORKFLOW.md).

## Production Adapter answers

The production adapter declares:

- target runtime files/schemas and id/reference/order grammar;
- exact mappings for triggers, actions, control, camera, presentation, HUD,
  objectives, state transitions, feedback, failure/recovery, and handoff;
- how runtime/world deltas are asserted and validated;
- asset, sound, story, localization, and code integration surfaces while
  preserving Beat Sheet/beat/packet provenance;
- exact integrity, build, launch, headless, screenshot, and playtest commands;
- instrumentation landing surfaces shared with the Observation Adapter;
- unsupported capabilities and escalation owner.

Implementation must land gameplay and required instrumentation together.
Mechanical tests can prove state/reference behavior but not player reception.

## UI Production Adapter answers

The UI adapter is narrower and more structural than the general Production
Adapter. It records:

- owned surfaces and exact accepted repo exemplars whose bytes are proven at an
  accepted baseline revision or explicitly accepted by a user ruling;
- container/anchor/offset/sizing and responsive-composition grammar;
- authoritative state, state-to-view refresh, signal order, and forbidden
  duplicate view state/logic;
- scene/node ownership, lifecycle, input/focus, modal/canvas/layer/z-order;
- viewport/input profiles and localization fit/stress profiles;
- separate structural-fit and visual-consistency scenarios that cover those
  profiles, with mechanical style comparison before screenshot review;
- target-to-exemplar mappings and exhaustive new/modified/reopened-batch style
  blast radii in each consuming production plan;
- evidenced anti-patterns and exact repo/user/factory authority for each rule.

Objective/repair design owns **what** the player should see and do. This
adapter owns **how this repository safely realizes that UI**. Production plans
bind its exact SHA and select relevant ids; the plan may not rewrite it.

## Observation Adapter answers

The observation adapter declares:

- instrumentation enablement, source log/capture schemas and paths;
- build/session/save/checkpoint/seed/locale/input/platform/viewport provenance;
- raw input versus resolved action, control, camera, HUD/modal, presentation,
  state before/delta/after, feedback/reward, audio/VFX, spatial, timing, and
  capture mappings;
- append-only order, monotonic clock, frame/sequence, and correlation rules;
- reproducible `LIVE_BLIND_RUN`, `RECORDED_RUN`,
  `CONTROLLED_BRANCH_PROBE`, and `STATIC_RUNTIME_ASSERTION` procedures;
- machine-readable normalization mapping or equivalent adapter tool;
- machine-readable exact-span boundary, control, presentation, traversal,
  non-gameplay activity, and acceptance-kernel measurement selectors used by
  the Quantitative Experience Budget gate;
- public observable versus hidden/private provenance fields;
- blind redaction and capture rules;
- observability matrix and explicit `NOT_OBSERVABLE` gaps;
- reader/integrity commands and evidence destinations.

Raw evidence and blind payloads never contain design intent, semantic
sheet/beat ids, canonical expected action, future data, or mental/evaluative
claims.

## State partitions

- runtime/world sources remain authoritative execution state;
- Span Quant Sheets, Beat Sheets, walkthroughs, packets, and plans are
  authority/decision state;
- grammar/experience lessons are derived design state;
- raw evidence is append-only observation state;
- canonical timelines are derived observable state;
- blind reports/acceptance are interpretation/QA state.

No persisted object silently serves more than one role.

## Canonical game-owned layout

```text
design/gameplay/
  init/
    GAMEPLAY_FACTORY_REPO_PROBE.json
    GAMEPLAY_FACTORY_INIT_INPUT.json
    GAMEPLAY_FACTORY_INIT_RESULT.json
  adapter/
    PROJECT_GAMEPLAY_PROFILE.md
    PROJECT_GAMEPLAY_DECISION_CARD_STANDARD.json
    PRODUCTION_ADAPTER.md
    OBSERVATION_ADAPTER.md
    GAMEPLAY_DESIGN_MODEL.json
    UI_PRODUCTION_ADAPTER.json
    UI_PRODUCTION_ADAPTER.md
  ui/
    PROJECT_UI_REPO_PROBE.json
    UI_PRODUCTION_ADAPTER_INPUT.json
    UI_PRODUCTION_ADAPTER_RESULT.json
  span_quants/<span_id>.md
  experience_beat_sheets/<sheet_id>.md
  experience_beat_sheets/<sheet_id>_QUANTITATIVE_EXPERIENCE_BUDGET.json
  walkthroughs/<trace_id>/
    PLAYABLE_WALKTHROUGH_TRACE.md
    PAPER_BLIND_INPUT.md
    PAPER_BLIND_REPORT.md
  beat_packets/<packet_id>.md
  observation_plans/<packet_or_span_id>.md
  runtime_evidence/<run_id>/
    RAW_MANIFEST.json
    <project-native logs and captures>
    CANONICAL_EVENT_STREAM.json
    OBSERVED_GAMEPLAY_TRACE.json
    OBSERVED_GAMEPLAY_TRACE.md
    RUNTIME_BLIND_INPUT.json
    RUNTIME_BLIND_REPORT.md
    INTEGRITY_REPORT.json
    EXPERIENCE_BUDGET_RESULT.json
  qa/
    <span_id>_QUANT_REVIEW.md
    <span_id>_DESIGN_REVIEW.md
    <span_id>_REALIZATION_REVIEW.md
    <span_id>_PACKET_REVIEW.md
    <span_id>_LANDING_REVIEW.md
    <span_id>_RUNTIME_ACCEPTANCE.md
  state/
    GAMEPLAY_GRAMMAR_STATE.md
    EXPERIENCE_LESSONS.md
  objective_gameplay/
    <objective_id>/
      NEXT_GAMEPLAY_UNIT_INPUT.json
      NEXT_GAMEPLAY_UNIT_CONTEXT.md
      OBJECTIVE_GAMEPLAY.md
      PRODUCTION_PLAN_MANIFEST.json
      production_plans/
        <plan_id>_<change_unit>.md
```

## Story/gameplay/production boundary

- Story owns canon, causality, character meaning, approved prose, and story
  anchors/staging constraints.
- Gameplay owns the approved experience curve and concrete player work,
  continuous player time, control/action/reception contracts, observation
  requirements, readback, and conformance acceptance.
- Production owns implementation through declared capabilities and returns
  runtime plus evidence.
- Asset/sound factories receive provenance-preserving orders; no gameplay core
  hard-coupling is allowed.

Conflicts never silently override authority. Route the first blocked/lost
transformation to story, experience design, realization, production,
presentation/reception, or observation.

## Initialization

Only explicit Gameplay Factory initialization may create game-owned
adapter/state paths. Use
[`GAMEPLAY_FACTORY_INIT_WORKFLOW.md`](GAMEPLAY_FACTORY_INIT_WORKFLOW.md) and
`../init.py`; do not seed blanks and ask later workers to rediscover the
answers.

The existing-project probe is non-semantic and binds the exact Git revision plus dirty
working-tree state. One investigator supplies repo-relative exact evidence and
persisted user rulings. The compiler validates the production material projection,
creates only missing canonical adapter/model/state/frontier files, and refuses
all differing existing state. `NOT_AVAILABLE` Observation Adapter capability
is permitted only as an explicit blocker for runtime evidence/acceptance. Only
`GAMEPLAY_FACTORY_READY` enters ordinary production; ordinary production calls fail
closed rather than generating missing answers.
