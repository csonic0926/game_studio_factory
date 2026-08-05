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
  -> fresh semantic alignment of material input/output
  -> product authority when missing
  -> synthesize and validate the exact gameplay system/cycle
  -> compact human-approved gameplay decision card
  -> Accepted Playable Baseline
  -> diagnose the next gameplay pressure
  -> web research for external design tokens
  -> select one minimum cycle-complete gameplay unit
  -> specialist planning and production
  -> integration
  -> new gameplay acceptance + old-baseline regression
  -> promote the next baseline
  -> repeat until the requested production horizon is satisfied
```

Before baseline routing, run `studio/product.py status`. An explicit
whole-direction revocation follows
[`PRODUCT_AUTHORITY_LIFECYCLE.md`](PRODUCT_AUTHORITY_LIFECYCLE.md); do not
manually relocate an entire design tree or manufacture card verdict tokens.
`NO_ACTIVE_PRODUCT_AUTHORITY` routes to Idea exploration and makes old
baselines historical rather than trusted predecessors.

The specialist capability layer is:

| Need | Specialist |
| --- | --- |
| Product direction and commercial/experiential constraints | `idea-factory` |
| Progression gameplay, new systems, repair, UI production, runtime evidence | `gameplay-factory` |
| World, characters, chapters, staged narrative | `game-story-factory` |
| Tiles, props, sprites, visual assets | `asset/` landing |
| SFX production | `sound/` landing |

The boundary between the first two rows is strict: Idea owns the Product
Thesis; **Studio** owns Product Thesis -> exact gameplay system; Gameplay owns
the bounded objective/spec and implementation. Read
[`GAMEPLAY_SYSTEM_WORKFLOW.md`](GAMEPLAY_SYSTEM_WORKFLOW.md). Do not route a
whole-game thesis directly into a convenient Gameplay objective.

Material user input and material human-facing output also obey
[`SEMANTIC_ALIGNMENT_WORKFLOW.md`](SEMANTIC_ALIGNMENT_WORKFLOW.md). Ordinary
user language is sufficient: the Studio owns authority-delta reconstruction,
workflow routing, and proof that a blocking question is not already answered.

## Entry states

A Studio call classifies the game repo before scaling:

- `STUDIO_NEEDS_PRODUCT_AUTHORITY` — Idea Factory must openly explore and then
  receive an explicit commission and `product.py activate`; Studio may not
  invent a hidden thesis or reuse an archived one.
- `BLOCKED_BY_LINEAR_GAMEPLAY` — the proposed system ends at a result/replay
  sequence, cuts a product-level coupling, or cannot show how lap-one state
  materially changes lap two.
- `STUDIO_NEEDS_ACCEPTED_BASELINE` — establish the minimum cycle-complete
  genuine playable baseline. A software demo or linear result/replay sequence
  does not satisfy this state.
- `STUDIO_READY_TO_SCALE` — a checked baseline exists; diagnose the next
  pressure and start the production loop.
- `STUDIO_BLOCKED` — exact external authority, capability, evidence, or
  acceptance is unavailable.
- `STUDIO_GOAL_DELIVERED` — the requested horizon is represented by an accepted
  baseline and runnable build, not merely completed production tasks.

## Research placement

Research occurs **after** a concrete gameplay pressure or missing cycle edge is
diagnosed and **before** the gameplay system/unit is frozen. Search all three
rings:

1. same-type references for conventions, expectations, and sameness risks;
2. cross-genre games for transferable decision/reward/progression mechanisms;
3. non-game domains for information structures, rituals, spatial organization,
   emotional rhythm, and human behavior.

Persist observations and translations with
`schemas/design_token_research.schema.json`. `NO_FIT` and rejected tokens are
valid. Do not browse broadly without a pressure question and do not turn search
results into mandatory features.

## Baseline and ratchet

Run the single admission entry before scaling and after each completed
gameplay-production workflow:

```bash
python3 <STUDIO_ROOT>/studio/baseline.py start --game-repo <GAME_REPO>
```

It routes mechanically to:

- complete `RECONSTRUCT` when there is no accepted baseline;
- incremental `PROMOTE` when an exact current baseline exists.

Read [`BASELINE_ADMISSION_WORKFLOW.md`](BASELINE_ADMISSION_WORKFLOW.md). The
compiler cannot convert tests, implementation completion, Reader output, or an
AI review into a human gameplay verdict. It binds the exact unit experience
authority, validated Studio gameplay-system manifest, Factory revision, fresh
reviewer decision, observed two-lap feedback cycle, and explicit user playtest
verdict.

The game repo owns Studio state under:

```text
design/studio/
  STUDIO_RUN_STATE.json
  STUDIO_DECISION_CARD_REGISTER.json
  interaction_alignment/<interaction_id>/STUDIO_SEMANTIC_ALIGNMENT_REVIEW.json
  gameplay_system/<system_id>/STUDIO_GAMEPLAY_SYSTEM_MANIFEST.json
  admissions/<admission_id>/BASELINE_ADMISSION_INPUT.json
  baselines/<baseline_id>/ACCEPTED_PLAYABLE_BASELINE.json
  research/<pressure_id>/DESIGN_TOKEN_RESEARCH.json
```

`ACCEPTED_PLAYABLE_BASELINE.json` is immutable historical authority. Promotion
creates a new baseline; it does not rewrite the predecessor. New gameplay must
receive fresh acceptance and every prior accepted loop must retain regression
evidence.

## v0 limitation

The durable state model and two-case baseline admission compiler/checker are
implemented. Until the persistent scheduler and real multi-cycle pilots pass,
the caller must not claim that Game Studio Factory already guarantees
unattended multi-cycle delivery.
