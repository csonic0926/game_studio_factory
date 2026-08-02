# Gameplay Factory initialization workflow

This is the single initialization entry for Gameplay Factory. It distinguishes
a total-new project, an existing project joining in the middle, and a repo that
is already factory-readable. Users do not select numbered cases.

```text
init.py start
  -> NEW_PROJECT_DEFINITION_REQUIRED
     OR existing-project probe -> investigation -> compile -> check
     OR GAMEPLAY_FACTORY_ALREADY_READY
```

Initialization does not invent a game, author meaningful choices, improve weak
gameplay, or silently choose between conflicting runtime systems.

## Initialization branches

### Total-new project

When no implemented runtime is present, `start` returns
`NEW_PROJECT_DEFINITION_REQUIRED`. Route to game/idea definition. A genre-only
request is not enough authority to create progression, actions, rewards, or
adapters.

### Existing project joining in the middle

When real code/data/content exists but factory state does not, `start` creates
the bounded probe and returns `EXISTING_PROJECT_INIT_INPUT_REQUIRED`. Continue
the evidence-focused reconstruction below.

### Already initialized

When all canonical adapter/model/state files exist, `start` returns
`GAMEPLAY_FACTORY_ALREADY_READY`. Return to [`../AGENTS.md`](../AGENTS.md).
Current production material checks still decide whether the state is
trustworthy; initialization never overwrites invalid pre-existing state.

## Authority and non-design rule

Existing-project initialization may reconstruct only existing, evidenced semantics:

- the live primary progression driver and progression unit;
- the current objective/frontier, locale text, runtime selection, completion,
  and successor handoff;
- implemented player actions, exact availability, and actual
  consequences/rewards;
- runtime/code/data ownership and validation commands;
- current presentation/control behavior;
- currently available or explicitly unavailable observation capability.

Repository names, comments, locales, and tests are evidence, not automatic
authority. A locale key alone does not prove a live objective. A dormant or
legacy system does not become the progression driver because its file name
looks relevant.

When evidence conflicts or a material semantic decision is absent, record the
gap and stop `BLOCKED_BY_INIT_MATERIAL`. Obtain exact runtime evidence or
a persisted user ruling; never use an AI assumption to make the repo pass.

## Game-owned layout

The initialization workspace and outputs live only in the game repo:

```text
design/gameplay/
  init/
    GAMEPLAY_FACTORY_REPO_PROBE.json
    GAMEPLAY_FACTORY_INIT_INPUT.json
    GAMEPLAY_FACTORY_INIT_RESULT.json
  adapter/
    PROJECT_GAMEPLAY_PROFILE.md
    PRODUCTION_ADAPTER.md
    OBSERVATION_ADAPTER.md
    GAMEPLAY_DESIGN_MODEL.json
  state/
    GAMEPLAY_GRAMMAR_STATE.md
    EXPERIENCE_LESSONS.md
  objective_gameplay/<objective_dir>/
    NEXT_GAMEPLAY_UNIT_INPUT.json
```

The Factory repo owns only tools, schemas, contracts, tests, and blank
templates.

## Routing link before initialization

If the game repo has not been linked to the umbrella, run this once before
initialization:

```bash
python3 <FACTORY_REPO>/setup.py link --game-repo <GAME_REPO>
```

This managed routing link may update the game repo's `AGENTS.md`, `.gitignore`,
and an absent `CLAUDE.md`, while keeping the absolute factory checkout only in
git-ignored `design/AI_FACTORY.local.md`. It does not create gameplay
authority. Run `start` after linkage so any intentional repo changes are
included in the study binding.

## Step 1 — start and classify

Run from the Factory repo or with equivalent absolute script resolution:

```bash
python3 gameplay/init.py start --game-repo <GAME_REPO>
```

For the existing-project branch, `start` writes
`design/gameplay/init/GAMEPLAY_FACTORY_REPO_PROBE.json`. The probe records:

- exact Git revision, branch, dirty paths, and a dirty working-tree content
  fingerprint;
- common engine/project markers;
- a bounded, scored list of code/data/test path candidates;
- locale CSV candidates;
- likely sources of build/test commands.

Candidate paths and scores are search hints only. The probe assigns no
gameplay meaning and reads no sibling repo. Generated initialization paths are
excluded from dirty-state comparison so the probe/input/output causal chain
remains stable.

Start results:

- `NEW_PROJECT_DEFINITION_REQUIRED` — route to game definition;
- `EXISTING_PROJECT_INIT_INPUT_REQUIRED` — continue the investigation;
- `GAMEPLAY_FACTORY_ALREADY_READY` — return to production routing;
- command error — wrong ownership, non-Git repo, illegal path, or
  conflicting existing probe.

`probe-existing` is an internal repeat operation, not a normal user command.

## Step 2 — one evidence-focused investigation

Use:

- `schemas/gameplay_factory_init_input.schema.json`
- `templates/GAMEPLAY_FACTORY_INIT_INPUT.json`

One investigator reads the probe, then opens only the source files needed to
settle the production prerequisites. It writes the canonical
`design/gameplay/init/GAMEPLAY_FACTORY_INIT_INPUT.json` with:

1. the exact probe revision, declared dirty paths, and working-tree
   fingerprint;
2. a complete `GAMEPLAY_DESIGN_MODEL` projection;
3. one initial objective frontier ready for objective-production Step 1;
4. concise project-profile answers;
5. exact production surfaces/mappings/commands;
6. an honest observation adapter (`AVAILABLE` or `NOT_AVAILABLE`);
7. separate user rulings;
8. empty `unresolved_material_gaps` and `ai_assumptions` before handoff.

Do not ask several workers to rediscover progression, actions, rewards, and
adapters independently. Do not copy the whole repo or all locale text into the
input. Every material claim uses a repo-relative path plus exact UTF-8 token.

## Step 3 — preflighted compile

```bash
python3 gameplay/init.py compile \
  --game-repo <GAME_REPO> \
  --input design/gameplay/init/GAMEPLAY_FACTORY_INIT_INPUT.json
```

Before any canonical output is created, `compile` verifies:

- the input matches the mechanical probe revision, dirty paths, and dirty
  working-tree content;
- every persisted path is portable and owned by the game repo;
- every exact evidence token still exists;
- the primary driver has `progression_authority` evidence;
- every action has runtime action evidence and a consequence/reward;
- the objective locale resolves exactly once with the expected text;
- runtime objective selection and completion are both proven;
- applicable action ids exist in the stable model;
- production mappings include objective selection, objective completion,
  player actions, and rewards/state;
- material gaps and AI assumptions are empty;
- the compiled projection passes the existing `prepare.py` production material
  gate.

The compiler renders all artifacts in memory, resolves and compares all
targets before its first write, and then:

- creates only missing files;
- accepts exact existing files idempotently;
- returns `BLOCKED_BY_EXISTING_FACTORY_STATE` before any write when one
  existing canonical file differs;
- never overwrites an adapter, state ledger, model, or objective input.

Successful compile returns `GAMEPLAY_FACTORY_READY` and writes SHA-256 for
every generated artifact into `GAMEPLAY_FACTORY_INIT_RESULT.json`.

### Observation capability

`OBSERVATION_ADAPTER.md` is always explicit. `NOT_AVAILABLE` may still produce
`GAMEPLAY_FACTORY_READY` for objective design/production, but the result
carries a warning and runtime evidence/acceptance remains blocked until
instrumentation and normalization mapping are implemented. Missing evidence is
never upgraded to a claim.

## Step 4 — exact handoff check

```bash
python3 gameplay/init.py check \
  --game-repo <GAME_REPO> \
  --input design/gameplay/init/GAMEPLAY_FACTORY_INIT_INPUT.json
```

`check` revalidates the repository binding and production material gate,
rebuilds the expected artifacts in memory, and compares every byte. Any stale
evidence, modified artifact, unresolved assumption, or source
revision/dirty-path change returns `BLOCKED_BY_INIT_MATERIAL`.

Only `GAMEPLAY_FACTORY_READY` completes Existing-project initialization.

## Handoff to production

After `GAMEPLAY_FACTORY_READY`, return to [`../AGENTS.md`](../AGENTS.md):

1. if an evidenced `OPEN` gameplay gap is already recorded, use gap repair;
2. otherwise run objective production using the generated
   `NEXT_GAMEPLAY_UNIT_INPUT.json`;
3. do not run initialization again merely because later gameplay state changes.

Existing-project initialization produces factory readability, not gameplay
acceptance and not a claim that the reconstructed design is good.

## Technical remediation boundary

Sometimes the existing repo cannot satisfy a production prerequisite—for example,
objective text exists but no live selection/completion wiring exists. The
initialization result must block. An ordinary engineering refactor may then add
missing localization, runtime wiring, tests, or instrumentation **only when the
intended semantics are already explicit in runtime authority or a user
ruling**. After that refactor, regenerate the probe/input and compile again.

If remediation requires deciding what the player should do or what a system
should mean, it has crossed into design and cannot be invented by
initialization.

## Token discipline

- Probe paths mechanically before semantic investigation.
- Use one investigator and one structured input.
- Read exact candidate sources, not the whole repo or every locale row.
- Store stable progression/action/reward vocabulary once.
- Generate prose adapters mechanically from structured facts.
- Reuse the existing production material validator instead of adding a review
  tower.
- Fail closed instead of spending creative tokens to fill missing authority.
