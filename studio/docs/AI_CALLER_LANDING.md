# AI caller landing — Game Studio Factory

Use the installed `game-studio-factory` skill for open-ended whole-game intent:

```text
Game Studio Factory，做一隻 COT-like 3D shooting game，完成後交一個真正可玩的 build。
```

Use a specialist Game AI Factory directly only when the user deliberately asks
for one bounded capability or artifact.

## Studio responsibility

Game Studio Factory owns the long-horizon control loop:

```text
human product intent
  -> product authority when missing
  -> Accepted Playable Baseline
  -> diagnose the next gameplay pressure
  -> web research for external design tokens
  -> select one bounded gameplay unit
  -> specialist planning and production
  -> integration
  -> new gameplay acceptance + old-baseline regression
  -> promote the next baseline
  -> repeat until the requested production horizon is satisfied
```

The specialist capability layer is:

| Need | Specialist |
| --- | --- |
| Product direction and commercial/experiential constraints | `idea-factory` |
| Progression gameplay, new systems, repair, UI production, runtime evidence | `gameplay-factory` |
| World, characters, chapters, staged narrative | `game-story-factory` |
| Tiles, props, sprites, visual assets | `asset/` landing |
| SFX production | `sound/` landing |

## Entry states

A Studio call classifies the game repo before scaling:

- `STUDIO_NEEDS_PRODUCT_AUTHORITY` — Idea Factory must openly explore and then
  receive an explicit commission; Studio may not invent a hidden thesis.
- `STUDIO_NEEDS_ACCEPTED_BASELINE` — establish the smallest genuine playable
  baseline. A software demo does not satisfy this state.
- `STUDIO_READY_TO_SCALE` — a checked baseline exists; diagnose the next
  pressure and start the production loop.
- `STUDIO_BLOCKED` — exact external authority, capability, evidence, or
  acceptance is unavailable.
- `STUDIO_GOAL_DELIVERED` — the requested horizon is represented by an accepted
  baseline and runnable build, not merely completed production tasks.

## Research placement

Research occurs **after** a concrete gameplay pressure is diagnosed and
**before** the next unit is selected. Search all three rings:

1. same-type references for conventions, expectations, and sameness risks;
2. cross-genre games for transferable decision/reward/progression mechanisms;
3. non-game domains for information structures, rituals, spatial organization,
   emotional rhythm, and human behavior.

Persist observations and translations with
`schemas/design_token_research.schema.json`. `NO_FIT` and rejected tokens are
valid. Do not browse broadly without a pressure question and do not turn search
results into mandatory features.

## Baseline and ratchet

The game repo owns Studio state under:

```text
design/studio/
  STUDIO_RUN_STATE.json
  baselines/<baseline_id>/ACCEPTED_PLAYABLE_BASELINE.json
  research/<pressure_id>/DESIGN_TOKEN_RESEARCH.json
```

`ACCEPTED_PLAYABLE_BASELINE.json` is immutable historical authority. Promotion
creates a new baseline; it does not rewrite the predecessor. New gameplay must
receive fresh acceptance and every prior accepted loop must retain regression
evidence.

## v0 limitation

This landing defines the intended autonomous operator and durable state model.
Until the scheduler/compiler/checker is implemented and real-project pilots
pass, the caller may use the specialist factories manually but must not claim
that Game Studio Factory already guarantees unattended multi-cycle delivery.
