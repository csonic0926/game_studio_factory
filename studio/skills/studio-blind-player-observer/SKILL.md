---
name: studio-blind-player-observer
description: Perform Phase A of the Studio blind player-perspective gate using only an exact build/start state, legitimate prior knowledge, normal controls, and player-facing screen/audio. Never read the Card, interaction contract, state ledger, tests, code, or author explanation before freezing the observation record.
---

# Studio Blind Player Observer

Use only as a fresh context with a validated
`PLAYER_FACING_BLIND_OBSERVATION_INPUT.json`. Before writing the observation,
do **not** read the Gameplay Decision Card, Player-Facing Interaction Contract,
Studio gameplay system, state objects, tests, code, debug logs, task text, or
any author explanation. If any answer-bearing authority was exposed, stop and
require a new fresh observer.

Use only the exact build/start state, the de-identified `player_prior_knowledge`
string list, normal player controls, and raw player-facing screen/audio/video
artifacts. The input must not expose design beat ids, sequence labels, intended
answers, or future-beat knowledge in any start-state/control string or artifact
path, not only the knowledge list. Require the preparation attestation to name
a different preparer context and affirm that all answer-bearing ids, intended
answers, future knowledge, and non-Phase-A materials were removed. Record each real interaction attempt as a
neutral contiguous `attempt.N` entry. It must bind exactly runtime trace `N`'s
byte-distinct before/during/after player-surface refs; the last attempt also
binds the returned/localization surface. The blind input must contain the exact
complete runtime surface, not a selected screenshot. For every attempt record:

- perceived cause, goal, and affordance;
- input/judgment actually attempted and visible response actually observed;
- persistent change, next motive, and localization readability;
- every point where the player became lost, passive, or dependent on evidence
  unavailable on the player surface.

Write `PLAYER_FACING_BLIND_OBSERVATION.json`, bind the exact blind input SHA,
and attest that design authority and author explanations were not read. Do not
compare against intended answers. Phase B belongs to a different fresh
comparison reviewer after this artifact is immutable.
