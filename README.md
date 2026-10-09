# Game Studio Factory

An autonomous whole-game operator backed by specialist Game AI Factories.

```text
Game Studio Factory   = autonomous whole-game operator
Game AI Factories     = specialist capabilities
```

The Studio contract is the authority for high-level intent such as “make this
game” or “continue production for three days”: product routing,
gameplay-first production, external reference research, specialist
coordination, integration, regression, and delivery qualification. It may
reduce scope or fidelity. It may not present an interactive software demo as a
completed game.

## Required: run every idea through Idea Factory

Use `idea-factory` to substantively question **every proposed game-design idea**,
including AI-generated mechanics, ideas already implemented but never examined,
and later additions or material revisions. Do this before treating the idea as a
design premise. Reading Factory docs, a one-time whole-direction review, existing
code, and a Product value assessment do not count as this inquiry.

For each idea, explain the concrete player reason, mechanism and consequence;
the real cost or sacrifice; alternatives or counterexamples that could change the
choice; and what is known, inferred or unresolved. Preserve its judgment, reasons
and open questions in a small game-owned record through the
[Idea inquiry workflow](idea/docs/PRODUCT_DEFINITION_WORKFLOW.md#every-idea-receives-substantive-inquiry).
Then examine how the ideas depend on, reinforce or undermine each other in the
whole game. Fifteen individually plausible features do not prove a good game.

Depth is proportional to the decision; “just a small idea” cannot excuse an
unexamined critical premise. Reuse still-applicable reasoning, reopen assumptions
when an idea materially changes, and keep `OPEN`, no-fit and rejection as valid
outcomes. No per-idea Thesis, fixed test quota or compulsory convergence is needed.
Technical repairs that preserve player-facing design do not restart discovery.
`MIGRATION_REQUIRED` and no formal commission do not excuse skipping nonbinding
inquiry. Product judges the whole offer and price; it does not replace Idea's
causal questioning. Neither an AI hypothesis nor a validator PASS grants USER
authority or proves the idea is good.

## Architecture

```text
factory.py    inspect / context / checkpoint / migrate / benchmark
factory_core/ versioned state, dependency closure and context views
studio/       whole-game operator
  Accepted Playable Baseline
  Gameplay Ratchet
  Design Token Research
  Independent Complete-Design Boundary Reviews
  Godot Automation and Execution Evidence
  Autonomous Production Loop

idea/         per-idea causal inquiry / product direction and commission
product/      early whole-value intent / experienced value judgment / claim gate
gameplay/     progression/new-system/repair/UI/evidence capability
story/        narrative capability
asset/        visual-asset capability
sound/        SFX capability
```

The specialist folders remain top-level so existing game-repo links, installed
skills, commands, and factory contracts continue to work.

## Quick start

One-time after cloning:

```bash
git clone https://github.com/csonic0926/game_studio_factory.git
cd game_studio_factory
python3 setup.py install
```

Then open a target game repo and say:

```text
Init Game Studio Factory in this repo.
```

The installed `init-game-studio-factory` skill runs `setup.py init`: it writes a
git-ignored local checkout pointer and managed routing block, establishes missing
Idea work, and seeds nonbinding Product value intent while preserving existing
instructions and authored work. It then continues into bounded Idea exploration
and real whole-offer value hypotheses, unknowns and a useful next experiment.
Unknown buyer/price and explicit scenarios are legal; initialization grants no
commission, acceptance or production authority. The old `init-game-ai-factory`
name remains a compatibility alias. See
[the initialization workflow](product/docs/PROJECT_INITIALIZATION_WORKFLOW.md).

For whole-game production:

```text
Use Game Studio Factory to make/continue this game. Do not stop at an
interactive demo; deliver only after gameplay acceptance.
```

For deliberately bounded expert work, the specialist skills remain directly
callable:

```text
Use Idea Factory to decide what product this should become.
Use Product Factory to establish the early whole-value hypotheses.
Use Product Factory to judge whether this whole game earns its price.
Use Gameplay Factory to continue the next objective.
Use Gameplay Factory to repair this broken gameplay step.
Use Story Factory to produce the next chapter.
```

Start at [`STUDIO_CALLER_LANDING.md`](STUDIO_CALLER_LANDING.md).

## Explicit workflow versions

`python3 factory.py inspect --game-repo <root>` is read-only. Unmigrated games
return `MIGRATION_REQUIRED`; standalone nonbinding Idea exploration and Product
intent can continue without migration. `migrate --check` previews an explicit
activation, then `--apply --expected <digest>` applies only that preflighted
transaction.
Historic approvals, rejections and accepted baselines are not reissued.
See [the v2 process contract](factory_core/docs/WORKFLOW.md). Older workflow
references are retained under each department's `docs/*_V1.md` for compatibility.

## Whole-game production model (v2)

Let `B_t` be the current Accepted Playable Baseline:

```text
B_t
→ diagnose the next gameplay pressure
→ web research for same-type, cross-genre, and non-game design tokens
→ select one bounded gameplay unit
→ active game-owned Card standard + required pre-Card composition
→ one full design + project compositions + player-facing interaction contract
→ two independent complete-design reviews
→ checked human decision view + required USER ruling
→ continuing primary-agent production within the reviewed scope
→ integration
→ exact-build interaction evidence + blind observation/comparison
→ fresh new-gameplay acceptance + regression(B_t)
→ promote B_(t+1)
→ repeat
```

### Accepted Playable Baseline

A baseline is an exact reproducible game revision with a runnable build,
complete accepted gameplay loop(s), fresh acceptance evidence, prior-gameplay
regression, and no blocking gap. It is not a branch, plan, screenshot, build
success, combat sandbox, character controller, or interactive demo.

Baseline admission has two cases behind one entry:

- **RECONSTRUCT** — rebuild the complete accepted game state when no baseline
  exists (or an explicit rebuild supersedes one without editing it);
- **PROMOTE** — after a Game AI Factory workflow, merge only freshly accepted
  new/repaired units and require regression of every predecessor unit.

```bash
python3 studio/baseline.py start --game-repo <GAME_REPO>
```

See [`studio/docs/BASELINE_ADMISSION_WORKFLOW.md`](studio/docs/BASELINE_ADMISSION_WORKFLOW.md)
and [`studio/docs/PLAYER_FACING_GAMEPLAY_EVIDENCE_GATE.md`](studio/docs/PLAYER_FACING_GAMEPLAY_EVIDENCE_GATE.md).

### Gameplay Ratchet

A locally complete system does not automatically enter the game. Promotion
requires that the new gameplay is accepted and the predecessor's accepted
loops still pass. Sunk production cost is not evidence.

### Design Token Research

The Studio searches the web only after diagnosing a gameplay pressure. It
extracts transferable mechanisms rather than copying surface content and
searches beyond the same genre:

1. same-type references — conventions and sameness risks;
2. cross-genre games — decision/reward/progression mechanisms;
3. non-game references — information, ritual, spatial, emotional, and human
   behavior structures.

`NO_FIT` is valid. A reference never becomes a mandatory feature merely because
it was researched.

### Scale out and scale up

- **Scale out** repeats accepted-baseline promotion and safely increases
  accepted gameplay units/workstreams.
- **Scale up** increases unit depth, system coupling, 3D/asset fidelity,
  spatial scale, and causal horizon.

Both preserve the minimum accepted-gameplay floor.

## Specialist Game AI Factories

| Capability | Entry |
| --- | --- |
| Product exploration and explicit commission | `idea-factory` |
| Nonbinding whole-value intent and experienced purchase judgment | `product-factory` |
| Progression gameplay, new systems, repair, UI production, runtime evidence | `gameplay-factory` |
| World, character, cast, chapter, staged narrative | `game-story-factory` |
| Tiles, walls, props, sprites | `asset/docs/AI_CALLER_LANDING.md` |
| SFX generation and normalization | `sound/docs/AI_CALLER_LANDING.md` |

Specialist maturity and detailed workflows remain documented in their own
folders. Passing production tests is never automatically a final gameplay
experience verdict.

## Install, initialize and relink

```bash
python3 setup.py install
python3 setup.py init --game-repo <GAME_REPO>
```

Use the exact existing game Git root outside Factory; an empty Git history is
valid. `--project-root` aliases `--game-repo`; `init --dry-run` validates and
previews without creating files. Existing authored Idea/Product material is
preserved on rerun. Neither initialization nor relinking changes workflow version.
For an explicit routing-only relink use `setup.py link --game-repo <GAME_REPO>`;
install/sync remains unchanged.

Routing writes:

```text
design/STUDIO_FACTORY.local.md   # git-ignored, machine-specific
AGENTS.md                        # one managed Studio routing block
CLAUDE.md                        # pointer only when the repo had none
```

Initialization also creates the normal Idea repo probe only when Idea work is
absent, plus `design/product_value/PRODUCT_VALUE_INTENT.json` only when absent.
`product/product.py start --game-repo <GAME_REPO>` is the additive intent-only
entry for an existing Idea game. Inspect and reconcile changed sources before
using the intent; bind it as an exact input when a material design relies on it.
It never becomes canonical product authority or current-build value evidence.

Compatibility is fail-soft:

- legacy `design/AI_FACTORY.local.md` remains readable;
- legacy `init-game-ai-factory` remains installed;
- old managed routing markers are reused and replaced in place;
- specialist paths such as `$STUDIO_ROOT/gameplay` remain stable.

## Repository layout

```text
STUDIO_CALLER_LANDING.md       canonical root entry
AI_CALLER_LANDING.md           compatibility entry
skills/
  init-game-studio-factory     joint Idea/Product initializer
  init-game-ai-factory         compatibility alias
studio/
  alignment.py
  baseline.py
  skills/game-studio-factory
  skills/studio-semantic-alignment-reviewer
  AGENTS.md
  docs/
  schemas/
  templates/
  tests/
idea/                           specialist Game AI Factory
product/                        specialist Game AI Factory
gameplay/                       specialist Game AI Factory
story/                          specialist Game AI Factory
asset/                          specialist Game AI Factory
sound/                          specialist Game AI Factory
setup.py                        install/init/link migration-safe tooling
```

All filled Studio/factory artifacts land in the game repo. This checkout owns
only reusable contracts, tools, templates, schemas, and tests.

## Current boundary

The specialist factories are operational at their documented maturity. The
Studio layer now includes naming, routing, operator invariants, durable state,
the deterministic two-case baseline admission compiler/checker, and a desktop
Godot automation/evidence platform for bounded runs, frame-bound scenarios,
live debug sessions, capture, visual regression, and build smoke. The adapter
still issues technical evidence only; it never supplies gameplay acceptance or
a human verdict. Execution stays with the caller’s continuing primary agent; no standalone
model API executor or persistent scheduler is introduced. Total-token savings
and equivalent creative quality require the fixed benchmark plus USER review;
they are not inferred from shorter entry documents.

## History and compatibility

This repository began as `game_asset_factory`, expanded into
`game_ai_factory`, and is now promoted to `game_studio_factory`. Git history is
retained. GitHub redirects and the compatibility skill/pointer surfaces keep
older clones and linked games operable while new usage adopts Studio naming.
