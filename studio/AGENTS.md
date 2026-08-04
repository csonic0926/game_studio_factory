# AGENTS — Game Studio Factory

Game Studio Factory is the autonomous whole-game operator. The specialist Game
AI Factories (`idea/`, `gameplay/`, `story/`, `asset/`, `sound/`) are its
capability layer; they do not independently own whole-game delivery.

Read [`docs/AI_CALLER_LANDING.md`](docs/AI_CALLER_LANDING.md), then preserve
these invariants:

1. **A runnable demo is not a delivered game.** The Studio may reduce content,
   fidelity, breadth, or production horizon, but it may not reinterpret
   “game” as interactive software without accepted gameplay.
2. **Operate from an Accepted Playable Baseline.** Each production cycle starts
   from one reproducible accepted game revision and promotes exactly one next
   accepted baseline after new-gameplay acceptance plus prior-baseline
   regression.
3. **Gameplay Ratchet.** Completed code/assets/plans do not earn promotion. A
   candidate that weakens the existing game is repaired, rejected, or narrowed.
   Every acceptance review binds the unit's exact experience authority and
   Factory revision; AI review evidence cannot substitute for a recorded human
   playtest verdict on the exact build.
4. **Research before repetition.** After diagnosing the active gameplay
   pressure, use web research to acquire external design tokens from same-type,
   cross-genre, and non-game references. Extract transferable mechanisms; never
   force a reference into production merely because it was researched.
5. **Parallelize production, not conflicting authority.** Workstreams may run
   concurrently only when their state writes, player-attention surfaces,
   reward/decision systems, and file ownership do not conflict.
6. **Specialists retain their contracts.** Studio selects and composes work;
   each specialist factory still validates its own artifacts and writes outputs
   only into the target game repo.
7. **Delivery is a promotion decision.** Only a checked accepted baseline with
   a runnable build, accepted gameplay units, regression evidence, and no
   blocking gap can be presented as Studio delivery.
8. **Admission has two cases only.** `RECONSTRUCT` inventories and freshly
   accepts the complete current game. `PROMOTE` consumes one exact predecessor,
   a revision-pinned completed workflow handoff, authority-bound fresh
   acceptance plus human playtest verdict for changed gameplay, and regression
   of every predecessor unit. Never use reconstruction to erase a
   valid ratchet history or promotion to inherit unreviewed gameplay.

## Formal production transition

Let `B_t` be the current Accepted Playable Baseline, `P_t` the diagnosed
pressure, `R_t` the external reference-token set, and `U_t` one bounded gameplay
unit. The only legal promotion is:

```text
B_t + P_t + R_t -> design(U_t) -> production(U_t) -> integration
    -> fresh gameplay acceptance + regression(B_t)
    -> B_(t+1)
```

Forbidden transitions:

- brief -> code/assets -> delivery;
- several locally complete systems -> assumed whole-game quality;
- failed/inconclusive gameplay acceptance -> accepted baseline;
- reference surface/theme -> copied feature without mechanism translation;
- candidate implementation state -> mutation of the prior accepted baseline
  record.

## Current foundation boundary

The baseline admission compiler/checker is operational and owns only evidence
binding plus state promotion; it does not issue gameplay verdicts. A persistent
autonomous multi-cycle scheduler is not implemented yet. Never describe this
bounded admission workflow as proof that unattended multi-day production is
already operational.
