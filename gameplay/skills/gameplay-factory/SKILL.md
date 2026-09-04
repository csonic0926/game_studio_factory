---
name: gameplay-factory
description: Initialize or run Gameplay Factory for a game repository. Use when the user asks to make/add/continue gameplay, advance the main progression or next objective, repair a broken or incomplete gameplay step, initialize Gameplay Factory for a new/existing repo, or inspect runtime gameplay evidence. Automatically links and initializes the repo before routing; ordinary production continues through implementation unless plan-only was explicitly requested.
---

# Gameplay Factory

This skill is the user-facing entry. Do not make the user choose lifecycle
cases, paste internal schemas, or issue a second “write the code” prompt.

## Resolve and load the contract

1. Resolve `<GAME_REPO>` from an explicit path, otherwise the current Git root.
   Never scan siblings; reject the factory checkout itself.
2. Resolve `<FACTORY_ROOT>` from the game repo's
   `design/STUDIO_FACTORY.local.md`, legacy
   `design/AI_FACTORY.local.md`, the installed-skills manifest, or this skill's
   real source path. If the game repo is unlinked, follow
   `init-game-studio-factory` (or legacy `init-game-ai-factory`) first and
   continue in the same call.
3. Read `<FACTORY_ROOT>/gameplay/AGENTS.md`. It is the routing authority. Read
   only the selected workflow contract it names; do not duplicate its whole
   workflow from memory.

Before Gameplay initialization, inspect product authority when present:

```text
design/product/PRODUCT_AUTHORITY_REGISTER.json   # when present; must be ACTIVE
design/product/PRODUCT_THESIS.md
design/product/FACTORY_CONSTRAINTS.json
```

If the register says `NO_ACTIVE_PRODUCT_AUTHORITY`, stop and return to Studio /
Idea exploration. Historical code, baselines, or objectives do not restore
production authority.

If the user says the product's commercial/experiential direction is unresolved,
or Gameplay would have to invent audience, monetization, retention/replay,
expression/emotion, differentiation, or scope priorities, invoke
`idea-factory` first and continue in the same call. Do not infer product
direction from an early mechanic merely because code exists.

## Always initialize before production routing

Run:

```bash
python3 <FACTORY_ROOT>/gameplay/init.py start --game-repo <GAME_REPO>
```

Continue the returned branch:

- `PROJECT_CARD_AUTHORING_STANDARD_REQUIRED`: run
  `python3 gameplay/init.py seed-card-standard --game-repo <GAME_REPO>`, then
  fill and human/project-adopt the game-owned blank,
  point the committed root collaboration contract to it, and exact-bind its
  path/version/SHA/`ACTIVE` status from the Project Gameplay Profile. Do not
  self-activate reconstructed or Factory example rules.
- `NEW_PROJECT_DEFINITION_REQUIRED`: invoke `idea-factory`; after
  `IDEA_FACTORY_READY`, continue through Studio gameplay-system/Card authority.
  Open/no-fit/multiple-direction Idea states remain in exploration and must not
  be force-commissioned to unblock Gameplay. Do not invent progression,
  actions, or rewards inside initialization.
- `NEW_PROJECT_GAMEPLAY_AUTHORITY_REQUIRED`: continue the Studio gameplay-system
  and registered `USER_APPROVED` Card route; do not substitute Product prose or
  an AI-selected mechanic for the missing decision authority.
- `NEW_PROJECT_BOOTSTRAP_INPUT_REQUIRED`: follow the total-new branch in
  `GAMEPLAY_FACTORY_INIT_WORKFLOW.md`, author the one explicit technical/frontier
  input from approved claim ids, then run `compile-new` and `check-new`.
- `EXISTING_PROJECT_INIT_INPUT_REQUIRED`: follow
  `GAMEPLAY_FACTORY_INIT_WORKFLOW.md` with one bounded evidence investigator,
  then run `compile` and `check`. This is reconstruction, not design.
- `GAMEPLAY_FACTORY_ALREADY_READY`: return to ordinary Gameplay routing.
- `GAMEPLAY_FACTORY_READY`: initialization just completed; continue the user's
  requested production in the same call.

Do not treat an intermediate status as the answer when the current branch can
be completed without user input.

## Route the user's need

- Concrete evidenced gap inside an existing objective: repair first with
  `GAMEPLAY_REPAIR_WORKFLOW.md`, unless the user explicitly deferred it.
- Otherwise make/complete the primary progression's next unit with
  `OBJECTIVE_GAMEPLAY_WORKFLOW.md`.
- Runtime evidence or acceptance preparation: use `reader.py` and its evidence
  contracts; never let the reader self-award gameplay acceptance.

An ordinary “make/fix/continue gameplay” call proceeds from design authority
through validated persisted production plans into normal code/data/asset/sound
execution. Stop at plans only when the user explicitly asked for plan-only.
An objective authored by AI is not design authority until an objective-local
`GAMEPLAY_DESIGN_VERDICT.json` v2 binds its exact SHA, the compact human-approved
decision card, and two fresh inverse conformance reviews. Before either route
authors that Card, load the active project Card authoring standard and create
every project-required pre-Card composition artifact. Every v3 Card exact-binds
those artifacts and must pass a fresh
`PASS_PROJECT_CARD_AUTHORING_STANDARD` review by a context different from all
composition, Contract, and Card authors. The review inventories every project
requirement and finite render-only checklist item. Missing/stale project
authority blocks direct-specialist rendering just as it blocks Studio
registration; Factory core never fills the project's answers.

For both routes, then author a
`PLAYER_FACING_INTERACTION_CONTRACT.json` that makes the
current scene composition, ordered player inputs, in-engine responses,
persistent state change, and next affordance concrete. A fresh interaction
reviewer must return `PASS_PLAYER_FACING_INTERACTION_DESIGN`; dialogue,
instructions, markers, or result text without player work are blockers. The
Card must bind that contract/review. A Studio-routed Card additionally binds
the validated cycle-complete Studio gameplay-system manifest and passes a
separate fresh end-to-end Card
Factory-compliance review before a different fresh semantic-alignment reviewer
permits presentation. Card hypotheses remain `TESTABLE_DESIGN`; neither a
design artifact nor its reviewer may claim runtime `PASS`.
New gameplay design requires user approval on the card; the user is not asked
to review the generated full spec.

When Gameplay Factory was invoked by Game Studio Factory, implementation ends
at a committed runtime revision plus a checked
`design/studio/admissions/<admission_id>/STUDIO_WORKFLOW_COMPLETION.json` using
`studio/templates/STUDIO_WORKFLOW_COMPLETION.json`. Its status remains
`IMPLEMENTED_PENDING_ACCEPTANCE`. Return control to Studio for fresh gameplay
acceptance, predecessor regression, and baseline promotion; Gameplay Factory
must not promote or self-accept the baseline. Before acceptance, Studio records
the exact build's windowed player input trace with before/during/after frames,
then gives a fresh blind observer only the contract's de-identified entry
knowledge string list, controls, and the player surface—never beat ids,
sequence labels, or an intended answer anywhere in its start-state text,
controls, or artifact paths. A different preparation context must explicitly
attest that all answer-bearing ids, intended answers, future knowledge, and
non-Phase-A material were removed. Phase A freezes neutral structured
`attempt.N` records. A separate comparison reviewer may read the design
authority only after that observation is sealed and must bind every beat to
unique existing attempts plus its exact runtime trace sequences.
Screenshots-only, state-JSON-only, headless
tests, logs, or dialogue-only proof cannot satisfy this runtime gate.

Before planning any change that touches gameplay UI, read
`docs/UI_PRODUCTION_WORKFLOW.md` and run `gameplay/ui.py start`. Reuse a checked
game-owned UI Production Adapter when ready; otherwise complete its one bounded
repo-evidence investigation, compile, and check it in the same call. Then bind
each UI-changing objective-v4 / repair-v3 plan to the exact adapter SHA,
accepted target-to-exemplar mapping, complete style blast radius, relevant
visual-grammar rule, and separate structural/visual validation ids. Do not let
the coding model infer the project's scene hierarchy, state ownership, refresh
timing, responsive composition, localization fit, modal/layer behavior, or
visual identity from feature intent alone.

## Boundaries

- Write game outputs only inside `<GAME_REPO>`; the factory checkout owns only
  reusable tools, schemas, templates, tests, and contracts.
- Initialization never overwrites differing existing factory state or fills
  semantic gaps with AI assumptions.
- New-project initialization records planned ownership and design authority;
  it records zero implemented actions/rewards and no runtime or acceptance
  evidence.
- Known player-visible gaps precede forward progression.
- Planning does not redesign; a missing design decision returns to its owning
  workflow.
- UI design intent does not authorize a generic UI architecture. No UI-changing
  plan or write proceeds without the repo-specific checked UI adapter binding.
- Passing implementation tests is not a final gameplay-experience verdict.
