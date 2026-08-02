# Case 2 foreign-repo onboarding workflow

This workflow converts an existing non-blank game repo into the exact
factory-readable state required by the compact Case 3 workflows. It is an
engineering and semantic-reconstruction operation, not gameplay creation.

```text
existing foreign game repo
  -> bounded mechanical probe
  -> one evidence-focused onboarding investigation
  -> preflighted adapter/model/state/frontier compilation
  -> Case 3 material-gate check
  -> CASE3_READY
```

It does not decide what game should exist, author meaningful choices, improve
weak gameplay, or silently choose between conflicting runtime systems.

## Case boundary

Route here only when:

- the target is an existing Git game repo with real code/data/content;
- some or all canonical Gameplay Factory adapters/state are missing;
- the repo is not a blank/genre-only Case 1 request;
- the user explicitly wants onboarding or asks Gameplay Factory to operate on
  the foreign repo.

If all Case 3 adapter/model/state files already exist, the probe returns
`ALREADY_CASE3`; return to [`../AGENTS.md`](../AGENTS.md) rather than compiling
onboarding again. This status means onboarding found canonical state and will
not overwrite it; the Case 3 material/adapter checks still decide whether that
state is trustworthy. Invalid pre-existing state blocks for explicit repair
instead of looping through onboarding.

## Authority and non-design rule

Case 2 may reconstruct only existing, evidenced semantics:

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
gap and stop `BLOCKED_BY_ONBOARDING_MATERIAL`. Obtain exact runtime evidence or
a persisted user ruling; never use an AI assumption to make the repo pass.

## Game-owned layout

The onboarding workspace and outputs live only in the game repo:

```text
design/gameplay/
  onboarding/
    CASE2_REPO_PROBE.json
    CASE2_ONBOARDING_INPUT.json
    CASE2_ONBOARDING_RESULT.json
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

## Routing link before the probe

If the foreign repo has not been linked to the umbrella, run this once before
capturing the Case 2 probe:

```bash
python3 <FACTORY_REPO>/setup.py link --game-repo <GAME_REPO>
```

This managed routing link may update the game repo's `AGENTS.md`, `.gitignore`,
and an absent `CLAUDE.md`, while keeping the absolute factory checkout only in
git-ignored `design/AI_FACTORY.local.md`. It does not create gameplay
authority. Run the probe after linkage so any intentional repo changes are
included in the study binding.

## Step 0 — bounded mechanical probe

Run from the Factory repo or with equivalent absolute script resolution:

```bash
python3 gameplay/onboard.py probe \
  --game-repo <GAME_REPO> \
  --out design/gameplay/onboarding/CASE2_REPO_PROBE.json
```

The probe records:

- exact Git revision, branch, dirty paths, and a dirty working-tree content
  fingerprint;
- common engine/project markers;
- a bounded, scored list of code/data/test path candidates;
- locale CSV candidates;
- likely sources of build/test commands.

Candidate paths and scores are search hints only. The probe assigns no
gameplay meaning and reads no sibling repo. Generated onboarding paths are
excluded from dirty-state comparison so the probe/input/output causal chain
remains stable.

Results:

- `CASE2_PROBE_READY` — continue the onboarding investigation;
- `ALREADY_CASE3` — canonical state already exists; stop onboarding and return
  to the Case 3 router for trust validation;
- command error — wrong ownership, non-Git/blank repo, illegal path, or
  conflicting existing probe.

## Step 1 — one evidence-focused investigation

Use:

- `schemas/case2_onboarding_input.schema.json`
- `templates/CASE2_ONBOARDING_INPUT.json`

One investigator reads the probe, then opens only the source files needed to
settle the Case 3 prerequisites. It writes the canonical
`CASE2_ONBOARDING_INPUT.json` with:

1. the exact probe revision, declared dirty paths, and working-tree
   fingerprint;
2. a complete `GAMEPLAY_DESIGN_MODEL` projection;
3. one initial objective frontier ready for Case 3 Step 1;
4. concise project-profile answers;
5. exact production surfaces/mappings/commands;
6. an honest observation adapter (`AVAILABLE` or `NOT_AVAILABLE`);
7. separate user rulings;
8. empty `unresolved_material_gaps` and `ai_assumptions` before handoff.

Do not ask several workers to rediscover progression, actions, rewards, and
adapters independently. Do not copy the whole repo or all locale text into the
input. Every material claim uses a repo-relative path plus exact UTF-8 token.

## Step 2 — preflighted compile

```bash
python3 gameplay/onboard.py compile \
  --game-repo <GAME_REPO> \
  --input design/gameplay/onboarding/CASE2_ONBOARDING_INPUT.json
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
- the compiled projection passes the existing Case 3 `prepare.py` material
  gate.

The compiler renders all artifacts in memory, resolves and compares all
targets before its first write, and then:

- creates only missing files;
- accepts exact existing files idempotently;
- returns `BLOCKED_BY_EXISTING_FACTORY_STATE` before any write when one
  existing canonical file differs;
- never overwrites an adapter, state ledger, model, or objective input.

Successful compile returns `CASE3_READY` and writes SHA-256 for every generated
artifact into `CASE2_ONBOARDING_RESULT.json`.

### Observation capability

`OBSERVATION_ADAPTER.md` is always explicit. `NOT_AVAILABLE` may still produce
`CASE3_READY` for compact Case 3 design/production, but the result carries a
warning and runtime evidence/acceptance remains blocked until instrumentation
and normalization mapping are implemented. Missing evidence is never upgraded
to a claim.

## Step 3 — exact handoff check

```bash
python3 gameplay/onboard.py check \
  --game-repo <GAME_REPO> \
  --input design/gameplay/onboarding/CASE2_ONBOARDING_INPUT.json
```

`check` revalidates the repository binding and Case 3 material gate, rebuilds
the expected artifacts in memory, and compares every byte. Any stale evidence,
modified artifact, unresolved assumption, or source revision/dirty-path change
returns `BLOCKED_BY_ONBOARDING_MATERIAL`.

Only `CASE3_READY` completes Case 2.

## Handoff to Case 3

After `CASE3_READY`, return to [`../AGENTS.md`](../AGENTS.md):

1. if an evidenced `OPEN` gameplay gap is already recorded, use Case 3 repair;
2. otherwise run Case 3 progression production using the generated
   `NEXT_GAMEPLAY_UNIT_INPUT.json`;
3. do not run onboarding again merely because later gameplay state changes.

Case 2 produces factory readability, not gameplay acceptance and not a claim
that the reconstructed design is good.

## Technical remediation boundary

Sometimes the foreign repo cannot satisfy a Case 3 prerequisite—for example,
objective text exists but no live selection/completion wiring exists. The
onboarding result must block. An ordinary engineering refactor may then add
missing localization, runtime wiring, tests, or instrumentation **only when the
intended semantics are already explicit in runtime authority or a user
ruling**. After that refactor, regenerate the probe/input and compile again.

If remediation requires deciding what the player should do or what a system
should mean, it has crossed into design and cannot be invented by Case 2.

## Token discipline

- Probe paths mechanically before semantic investigation.
- Use one investigator and one structured input.
- Read exact candidate sources, not the whole repo or every locale row.
- Store stable progression/action/reward vocabulary once.
- Generate prose adapters mechanically from structured facts.
- Reuse the existing Case 3 material validator instead of adding a review
  tower.
- Fail closed instead of spending creative tokens to fill missing authority.
