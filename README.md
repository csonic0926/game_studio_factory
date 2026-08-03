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

## Architecture

```text
studio/       whole-game operator
  Accepted Playable Baseline
  Gameplay Ratchet
  Design Token Research
  Autonomous Production Loop

idea/         product direction capability
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

The installed `init-game-studio-factory` skill writes a git-ignored local
checkout pointer and one managed routing block while preserving existing agent
instructions. The old `init-game-ai-factory` name remains a compatibility
alias.

For whole-game production:

```text
Use Game Studio Factory to make/continue this game. Do not stop at an
interactive demo; deliver only after gameplay acceptance.
```

For deliberately bounded expert work, the specialist skills remain directly
callable:

```text
Use Idea Factory to decide what product this should become.
Use Gameplay Factory to continue the next objective.
Use Gameplay Factory to repair this broken gameplay step.
Use Story Factory to produce the next chapter.
```

Start at [`STUDIO_CALLER_LANDING.md`](STUDIO_CALLER_LANDING.md).

## Whole-game production model

Let `B_t` be the current Accepted Playable Baseline:

```text
B_t
→ diagnose the next gameplay pressure
→ web research for same-type, cross-genre, and non-game design tokens
→ select one bounded gameplay unit
→ specialist design/planning/production
→ integration
→ fresh new-gameplay acceptance + regression(B_t)
→ promote B_(t+1)
→ repeat
```

### Accepted Playable Baseline

A baseline is an exact reproducible game revision with a runnable build,
complete accepted gameplay loop(s), fresh acceptance evidence, prior-gameplay
regression, and no blocking gap. It is not a branch, plan, screenshot, build
success, combat sandbox, character controller, or interactive demo.

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
| Progression gameplay, new systems, repair, UI production, runtime evidence | `gameplay-factory` |
| World, character, cast, chapter, staged narrative | `game-story-factory` |
| Tiles, walls, props, sprites | `asset/docs/AI_CALLER_LANDING.md` |
| SFX generation and normalization | `sound/docs/AI_CALLER_LANDING.md` |

Specialist maturity and detailed workflows remain documented in their own
folders. Passing production tests is never automatically a final gameplay
experience verdict.

## Install and game-repo linking

```bash
python3 setup.py install
python3 setup.py link --game-repo <GAME_REPO>
```

New links write:

```text
design/STUDIO_FACTORY.local.md   # git-ignored, machine-specific
AGENTS.md                        # one managed Studio routing block
CLAUDE.md                        # pointer only when the repo had none
```

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
  init-game-studio-factory     canonical linker
  init-game-ai-factory         compatibility alias
studio/
  skills/game-studio-factory
  AGENTS.md
  docs/
  schemas/
  templates/
  tests/
idea/                           specialist Game AI Factory
gameplay/                       specialist Game AI Factory
story/                          specialist Game AI Factory
asset/                          specialist Game AI Factory
sound/                          specialist Game AI Factory
setup.py                        install/link migration-safe tooling
```

All filled Studio/factory artifacts land in the game repo. This checkout owns
only reusable contracts, tools, templates, schemas, and tests.

## Current boundary

The specialist factories are operational at their documented maturity. The
Studio layer is currently a **v0 foundation**: naming, routing, operator
invariants, skill, and durable state schemas/templates exist. The persistent
autonomous scheduler and automatic baseline compiler/checker are not yet
implemented or real-project proven. The repository name does not waive that
boundary.

## History and compatibility

This repository began as `game_asset_factory`, expanded into
`game_ai_factory`, and is now promoted to `game_studio_factory`. Git history is
retained. GitHub redirects and the compatibility skill/pointer surfaces keep
older clones and linked games operable while new usage adopts Studio naming.
