# AI caller landing — Game Studio Factory

This repository has two layers:

```text
Game Studio Factory   = autonomous whole-game operator
Game AI Factories     = specialist capabilities
```

## Choose the entry by responsibility

| User intent | Entry |
| --- | --- |
| “Make/continue this game”, a multi-day autonomous goal, or any request whose success is the whole playable game | skill `game-studio-factory` → `studio/AGENTS.md` |
| Initialize/link a game repo | skill `init-game-studio-factory` |
| Decide product direction | skill `idea-factory` → `idea/AGENTS.md` |
| Produce/repair progression gameplay or inspect gameplay evidence | skill `gameplay-factory` → `gameplay/AGENTS.md` |
| Produce world/character/chapter narrative | skill `game-story-factory` → `story/AGENTS.md` |
| Produce visual assets | `asset/docs/AI_CALLER_LANDING.md` |
| Produce SFX | `sound/docs/AI_CALLER_LANDING.md` |

The Studio is the default for open-ended intent. Direct specialist invocation
is correct for deliberately bounded expert work.

## Whole-game delivery invariant

Game Studio Factory may narrow content, asset fidelity, spatial scale, or the
requested production horizon. It may not narrow “game” into a runnable
interactive software demo. Studio delivery requires a runnable **Accepted
Playable Baseline** with:

- at least one complete, accepted gameplay loop;
- fresh acceptance for newly introduced gameplay;
- regression evidence for previously accepted gameplay;
- no blocking known gap;
- exact build and game-revision provenance.

Read [`studio/docs/AI_CALLER_LANDING.md`](studio/docs/AI_CALLER_LANDING.md) for
the baseline/ratchet/research/production loop.

## Specialist capability model

The Game AI Factories remain independently callable and keep their own stable
contracts:

```text
idea/       open product exploration + explicit product commission
story/      world, character, cast, chapter, staged narrative
gameplay/   progression units, new gameplay, gap repair, UI production,
            runtime evidence
asset/      tiles, walls, props, sprites, visual production
sound/      SFX generation and normalization
```

Filled product authority, Studio state, designs, plans, evidence, code, data,
assets, and sound always land in the target game repo. This checkout owns only
reusable skills, tools, schemas, templates, tests, and contracts.

## Setup and compatibility

One-time after cloning:

```bash
python3 setup.py install
```

In a target game repo invoke `init-game-studio-factory`, which runs:

```bash
python3 <STUDIO_ROOT>/setup.py link --game-repo <GAME_REPO>
```

New links use the git-ignored `design/STUDIO_FACTORY.local.md`. Existing
`design/AI_FACTORY.local.md`, `init-game-ai-factory`, old managed-block markers,
and the old installed-skills manifest remain readable compatibility surfaces.

## Current implementation boundary

The specialist factories are operational at their documented maturity. The
Studio folder establishes the operator contract, durable state, and two-case
baseline admission compiler/checker. A persistent autonomous scheduler remains
to be implemented and proven on real game repos; the name/structure must not be
mistaken for that proof.
