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
   `design/AI_FACTORY.local.md`, the installed-skills manifest, or this skill's
   real source path. If the game repo is unlinked, follow
   `init-game-ai-factory` first and continue in the same call.
3. Read `<FACTORY_ROOT>/gameplay/AGENTS.md`. It is the routing authority. Read
   only the selected workflow contract it names; do not duplicate its whole
   workflow from memory.

## Always initialize before production routing

Run:

```bash
python3 <FACTORY_ROOT>/gameplay/init.py start --game-repo <GAME_REPO>
```

Continue the returned branch:

- `NEW_PROJECT_DEFINITION_REQUIRED`: stop before inventing progression,
  actions, or rewards; route to game/idea definition when available.
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

## Boundaries

- Write game outputs only inside `<GAME_REPO>`; the factory checkout owns only
  reusable tools, schemas, templates, tests, and contracts.
- Initialization never overwrites differing existing factory state or fills
  semantic gaps with AI assumptions.
- Known player-visible gaps precede forward progression.
- Planning does not redesign; a missing design decision returns to its owning
  workflow.
- Passing implementation tests is not a final gameplay-experience verdict.
