# game_ai_factory

Umbrella for one product-definition factory plus four production factories,
each callable by an AI agent through a skill/landing contract:

- **`idea/`** — Idea Factory. An AI producer openly explores sparse user intent,
  references, and/or an early repo without forcing a product answer. No-fit,
  unresolved, and multiple-direction states are valid; only a separately
  commissioned emerged direction becomes a product thesis and cross-factory
  constraints.
- **`asset/`** — game asset factory. Blender-first isometric tile/wall reference
  pairs, prop/object sprites, tile re-skin, chroma-key cleanup. Python CLI
  (`itf.py` + spec JSON). *(retains this repo's original git history)*
- **`story/`** — game story factory. World / character / cast / chapter narrative
  production with hard `.5` review gates and file-based handoff, driven by the
  `game-story-factory` Claude skill and per-project adapters.
- **`gameplay/`** — gameplay factory. Initializes a new or existing game repo,
  continues its primary progression one
  objective at a time, or repairs a concrete gameplay gap inside an existing
  objective. Uses bounded script-first context, persistent model-independent
  production plans, a just-in-time repo-specific UI realization adapter, and
  automatic caller handoff to normal
  code/data/asset/sound production.
- **`sound/`** — game sound factory. Text→SFX via ElevenLabs, then de-silence +
  peak-normalize so clips are drop-in. Python CLI (`sfx.py` + spec JSON).

Start at [`AI_CALLER_LANDING.md`](AI_CALLER_LANDING.md) to route to the right one.

## Quick start

One-time per machine, after cloning this repo:

```bash
git clone https://github.com/csonic0926/game_ai_factory.git
cd game_ai_factory
python3 setup.py install
```

`install` installs these user-facing skills:

- `init-game-ai-factory` — connect the current game repo to the umbrella;
- `idea-factory` — explore, then optionally commission the product direction;
- `gameplay-factory` — initialize and run Gameplay Factory;
- `game-story-factory` — run Story Factory.

By default they are symlinked into `~/.claude/skills` and `~/.codex/skills`, so
`git pull` updates existing skills immediately. Rerun `install` after a pull
that adds, removes, or renames a skill. Use `install --copy` only where
symlinks are unavailable, then rerun `install --copy` after updates. The old
`sync` command remains an alias. Installation creates missing skill
directories, deduplicates targets that resolve to the same place, and never
replaces a foreign entry.

Then open the target game repo and tell the AI:

```text
Init Game AI Factory in this repo.
```

The `init-game-ai-factory` skill resolves the current Git root and cloned
factory automatically. It writes the harness-agnostic routing block, preserves
existing repo instructions, and verifies the link. Direct invocation also
works: `/init-game-ai-factory`.

After that, ordinary requests are enough:

```text
Use Idea Factory to help decide what product this early repo should become.
Use Gameplay Factory to continue the next objective.
Use Gameplay Factory to repair this broken campfire step.
```

The `idea-factory` skill works even when code already exists: its trigger is an
open product question or missing/contradictory **product authority**, not an
empty repo. It first writes non-binding `IDEA_EXPLORATION` state and may validly
stop at no-fit or multiple live directions. Only explicit post-exploration
commission produces `PRODUCT_THESIS.md` and `FACTORY_CONSTRAINTS.json`.

The `gameplay-factory` skill routes total-new repos to Idea Factory, initializes
existing repos, recognizes already-ready repos, writes persistent plans, and
continues ordinary production through implementation unless the user
explicitly asks for plan-only. Direct invocation also works:
`/gameplay-factory ...`.

### Manual/CI fallback

The skills call these dependency-free commands internally; humans normally do
not need them:

```bash
python3 setup.py link --game-repo <GAME_REPO>
python3 gameplay/init.py start --game-repo <GAME_REPO>
```

`install`, `link`, and their supported operations accept `--dry-run` where
shown by `--help`.

## Gameplay Factory — initialize once, then produce

The installed `gameplay-factory` skill is the normal AI entry. It resolves and
obeys [`gameplay/AGENTS.md`](gameplay/AGENTS.md), the canonical Gameplay
Factory routing contract, then runs initialization automatically.

`start` chooses one of three states without asking the user to know internal
migration categories:

- `NEW_PROJECT_DEFINITION_REQUIRED` — no implemented game exists yet; route to
  `idea-factory` before creating gameplay authority;
- `EXISTING_PROJECT_INIT_INPUT_REQUIRED` — reconstruct the existing runtime
  through one bounded evidence pass, then compile factory state;
- `GAMEPLAY_FACTORY_ALREADY_READY` — initialization is complete; continue
  ordinary production.

For an AI caller, `EXISTING_PROJECT_INIT_INPUT_REQUIRED` is intermediate: the
caller follows
[`GAMEPLAY_FACTORY_INIT_WORKFLOW.md`](gameplay/docs/GAMEPLAY_FACTORY_INIT_WORKFLOW.md)
through `compile` and `check`. The human does not paste the internal probe,
schema, and evidence instructions.

After initialization, the same entry routes ongoing work:

| Need | Operation | Contract |
| --- | --- | --- |
| Initialize Gameplay Factory for a new or existing repo | `init_gameplay_factory` | [`GAMEPLAY_FACTORY_INIT_WORKFLOW.md`](gameplay/docs/GAMEPLAY_FACTORY_INIT_WORKFLOW.md) |
| Complete or advance the primary progression's next unit | `produce_objective` | [`OBJECTIVE_GAMEPLAY_WORKFLOW.md`](gameplay/docs/OBJECTIVE_GAMEPLAY_WORKFLOW.md) |
| Repair one evidenced player-visible gap inside an existing objective | `repair_gameplay_gap` | [`GAMEPLAY_REPAIR_WORKFLOW.md`](gameplay/docs/GAMEPLAY_REPAIR_WORKFLOW.md) |
| Prepare/check/refresh repo-specific UI construction before a UI-changing plan | `prepare_ui_production` | [`UI_PRODUCTION_WORKFLOW.md`](gameplay/docs/UI_PRODUCTION_WORKFLOW.md) |

If both are active, a concrete known gap is repaired before forward expansion
unless the user explicitly defers it.

### Existing-project initialization

```text
init.py start
  -> bounded mechanical probe
  -> one evidence-focused init input
  -> init.py compile
  -> missing adapters/model/empty state + initial objective frontier
  -> init.py check
  -> GAMEPLAY_FACTORY_READY
```

Existing-project initialization reconstructs runtime meaning rather than
deciding what the game should become. It binds the Git revision plus dirty working-tree state,
requires exact repo-relative evidence, creates only missing canonical files,
and blocks rather than inventing semantics or overwriting foreign state.

### Progression production

```text
stable GAMEPLAY_DESIGN_MODEL.json + objective frontier
  -> prepare.py context
  -> NEXT_GAMEPLAY_UNIT_CONTEXT.md
  -> one complete OBJECTIVE_GAMEPLAY.md authoring pass
  -> user-selected Plan Mode or ordinary planner
  -> PRODUCTION_PLAN_MANIFEST.json + production_plans/*.md
  -> plan.py validate
  -> original caller automatically executes production
```

The primary progression answers **what the player does next**. Gameplay is the
**how** between objective issue and completion: player actions, problems,
information, consequences/rewards, and meaningful decisions or execution.

```bash
python3 gameplay/prepare.py context \
  --game-repo <GAME_REPO> \
  --input design/gameplay/objective_gameplay/<objective_id>/NEXT_GAMEPLAY_UNIT_INPUT.json \
  --out design/gameplay/objective_gameplay/<objective_id>/NEXT_GAMEPLAY_UNIT_CONTEXT.md

python3 gameplay/plan.py validate \
  --game-repo <GAME_REPO> \
  --manifest design/gameplay/objective_gameplay/<objective_id>/PRODUCTION_PLAN_MANIFEST.json
```

### Gameplay-gap repair

```text
exact existing OBJECTIVE_GAMEPLAY.md + one evidenced gap
  -> repair.py context
  -> GAMEPLAY_REPAIR_CONTEXT.md
  -> direct planning when authority already exists
     OR one bounded GAMEPLAY_REPAIR.md authoring pass
  -> REPAIR_PLAN_MANIFEST.json + production_plans/*.md
  -> repair_plan.py validate
  -> original caller automatically executes repair production
```

A repair is SHA-bound to both the base objective and its repair authority. It
does not rewrite the whole objective, redesign unrelated rows, or invent the
successor progression unit.

```bash
python3 gameplay/repair.py context \
  --game-repo <GAME_REPO> \
  --input design/gameplay/repairs/<gap_id>/GAMEPLAY_GAP_INPUT.json \
  --out design/gameplay/repairs/<gap_id>/GAMEPLAY_REPAIR_CONTEXT.md

python3 gameplay/repair_plan.py validate \
  --game-repo <GAME_REPO> \
  --manifest design/gameplay/repairs/<gap_id>/REPAIR_PLAN_MANIFEST.json
```

Gap state persists as `OPEN`, `IMPLEMENTED_PENDING_ACCEPTANCE`, `CLOSED`, or
user-authorized `DEFERRED`. Passing implementation tests may advance a gap to
pending acceptance, but cannot self-award experiential closure.

### UI production preflight

When objective or repair production will touch UI, the caller first runs a
bounded, one-investigator preflight:

```text
ui.py start -> non-semantic repo probe -> UI adapter input
            -> ui.py compile/check -> UI_PRODUCTION_ADAPTER.json/.md
            -> manifest v2 binds adapter SHA + rule/exemplar/scenario ids
```

This records the game's actual layout hierarchy, state/refresh ownership,
scene lifecycle, input/modal/layers, responsive/localized composition, working
exemplars, and stateful validation matrix. It is not run for non-UI work, and
it does not redesign the feature. See
[`UI_PRODUCTION_WORKFLOW.md`](gameplay/docs/UI_PRODUCTION_WORKFLOW.md).

### Runtime evidence remains separate

[`gameplay/reader.py`](gameplay/reader.py) validates and transforms runtime
evidence, reconstructs same-run causal chains, produces blind-reader input, and
measures declared budgets. It does not invent gameplay or issue a final
experience verdict.

## Design principle

One umbrella, one product-definition layer, four production factories, and
**one ownership model**: an AI caller resolves the factory contract and project
inputs, produces and validates the requested artifact, and versions the result
with the game. Nothing produced for a game lands under this umbrella. Factory
contracts, schemas, tools, and blank templates remain here; filled product
authority, designs, plans, runtime evidence, code, data, assets, and sound land
in the game repo.

## Layout

```
AI_CALLER_LANDING.md     route here first
skills/  init-game-ai-factory
idea/    idea.py, skill idea-factory, product-definition workflow, schemas/tests
asset/   itf.py, pipeline/, docs/, examples/ …   (original git history)
story/   skills/, core/steps|craft|schemas/, adapters/
gameplay/ skills/gameplay-factory, AGENTS.md, init.py, prepare.py, plan.py, repair.py, repair_plan.py, ui.py,
          reader.py, docs/, schemas/, adapters/, templates/, tests/
sound/   sfx.py, pipeline/, docs/, examples/
```

## Compatibility

`tools/game_asset_factory` and `tools/game_story_factory` are kept as symlinks
into `asset/` and `story/` for any caller still using the old paths. Remove when
no longer referenced.
