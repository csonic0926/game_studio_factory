# Player-Facing Gameplay Evidence Gate

This gate keeps four different claims separate:

1. a design document is internally compliant;
2. the player-facing interaction is concretely designed;
3. an exact runtime build visibly implements that interaction; and
4. a human player accepts the experience.

No earlier claim is evidence for a later one.

## Design-time chain

Before a Studio-routed Gameplay Decision Card can be registered or rendered for
human approval, its objective directory must contain:

```text
PLAYER_FACING_INTERACTION_CONTRACT.json
PLAYER_FACING_INTERACTION_CONTRACT_REVIEW.json
GAMEPLAY_DECISION_CARD.json
GAMEPLAY_DECISION_CARD_FACTORY_REVIEW.json
```

The contract binds the current player surface, de-identified scenario-entry
knowledge, per-beat legitimate prior knowledge,
visible cause and goal, concrete inputs, player judgment, ordered
input-to-response steps, immediate visible response, persistent visible change,
changed next affordance, allowed text support, forbidden proxies, and future
capture plan for every claimed beat. Visual projects must use the current real
scene composition through in-engine frames, annotated current-scene frames, or
a faithful screen-flow prototype. The stored sequence must cover every beat in
contract order and, within each beat, `ENTRY -> AFFORDANCE ->
EXPECTED_RESPONSE -> PERSISTENT_RETURN`; one unstructured static screenshot,
prose, and state diagrams alone fail.
`player_entry_knowledge` is the only knowledge copied into the blind bundle;
it contains no beat ids, sequence labels, intended answer, or future-beat
knowledge. Per-beat design knowledge remains private to Phase B.

A fresh reviewer validates the whole sequence from the player's point of view
and may return only design-stage outcomes. The pass state is
`PASS_PLAYER_FACING_INTERACTION_DESIGN`; the contract itself remains
`TESTABLE_DESIGN`. Card hypotheses likewise use `TESTABLE_DESIGN`, never
`PASS`, `ACCEPTED`, or another observed-result label.

`gameplay/design_gate.py register-card` and checked Card rendering fail closed
when either artifact is missing, stale, hash-mismatched, blocked, or authored
and reviewed by a non-fresh context.

## Runtime chain

Every new gameplay acceptance uses four separate immutable artifacts for the
exact committed build:

```text
PLAYER_FACING_RUNTIME_INTERACTION_EVIDENCE.json
PLAYER_FACING_BLIND_OBSERVATION_INPUT.json
PLAYER_FACING_BLIND_OBSERVATION.json
PLAYER_FACING_COMPARISON_REVIEW.json
```

The runtime evidence contains a clean start identity, windowed in-engine
capture, ordered input trace, before/during/after frames, observable
character/object/location changes, structural control evidence where relevant,
and the changed next affordance. Every evidence path is repo-relative and
SHA-256 bound. A screenshot without input, an input trace without visible
response, or tests/logs/state JSON without the player surface fails.
Before/during/after bytes must differ, trace sequences cannot share frame bytes
even through copied/renamed paths, and typed evidence-file refs must exactly equal the structured trace
refs rather than merely carrying a matching label.

Blind review has two mechanically separated phases:

- **Phase A — observation:** the observer receives only the exact build/start
  state, the exact de-identified entry-knowledge list, normal controls, and
  actual player-facing output. Before delivery, a named preparation context
  must attest that answer-bearing ids, intended answers, future-beat knowledge,
  and all non-Phase-A materials were removed. The validator scans every
  Phase-A-visible start-state/control string and artifact path against the full
  contract beat/transition/step/scenario id set; the blind observer must be a
  different context from that preparer. It must attest that it did not read the Card,
  contract, beat inventory, state objects, tests, or author explanation. Each
  attempted interaction is frozen as a neutral `attempt.N` record with its
  exact player-surface artifacts and observations for cause, goal, affordance,
  input/judgment, response, persistence, next motive, and localization. The
  blind bundle exactly covers all runtime before/during/after, returned, and
  localization artifacts; `attempt.N` binds exactly trace sequence `N`'s
  capture, with the final attempt also binding returned/localization surfaces.
- **Phase B — comparison:** a different fresh reviewer reads the sealed blind
  observation and compares it with the interaction contract, Decision Card,
  and Studio gameplay system. Each beat must cite every and only its runtime
  trace sequences plus unique existing `attempt.N` records; all sealed attempts
  must be consumed exactly once across beats. It may not infer an unobserved
  result from prose or reuse one generic observation as proof for many beats.
  Blind and comparison contexts are also forbidden from reusing the registered
  Card's alignment author/reviewer, final Card reviewer, full-spec author, or
  conformance reviewers when those identities are present.

Only the comparison can move a hypothesis to `OBSERVED_SUPPORT` or
`OBSERVED_REJECT`. Human acceptance remains a later exact-build verdict.

## Automatic blockers

The validators reject, at minimum:

- no concrete visible entry state, input, or visible response;
- abstract verbs such as investigate/escort/track without an ordered sequence;
- cause, goal, consequence, or next affordance existing only in prose, hidden
  state, debug output, journal/task text, marker, or popup;
- dialogue advancing directly to a result without the claimed player work;
- screenshots-only or input/tests/logs/state-only runtime evidence;
- one static current-scene visual copied, renamed, or relabelled as several design moments, one
  static frame relabelled as before/during/after, reused trace capture, or a
  blind bundle that omits runtime surface moments;
- a blind observer reading answer-bearing authority before observation;
- a blind input whose start-state text, knowledge, controls, or artifact paths
  expose any design id, that injects intended answers/future knowledge, or that
  lacks the preparer's explicit de-identification attestation;
- a comparison citation absent from the sealed observation, missing a runtime
  trace, or reused across multiple beats;
- a design hypothesis labelled as an observed pass; and
- missing, fallback, or garbled target-locale text that blocks comprehension.

## Version and migration policy

Existing committed historical artifacts remain readable by their historical
validation paths, but they do not satisfy a new claim:

- regenerate every new/revised Card as `gameplay_decision_card.v3`, add its
  exact project-standard/composition/project-review bindings, and regenerate
  the final review as `gameplay_decision_card_factory_review.v3`;
- regenerate both design-conformance reviews as
  `gameplay_design_conformance_review.v2`; ordinary claims use
  `PASS_DESIGN_CLAIM`, while hypotheses remain `TESTABLE_DESIGN`;
- create and hash-bind the v1 interaction contract and fresh v1 interaction
  review before Card registration;
- regenerate each newly claimed acceptance input as
  `gameplay_acceptance_input.v3` and its review as
  `gameplay_acceptance_review.v4`;
- create and hash-bind all four v1 runtime/blind/comparison artifacts before
  compiling acceptance;
- never edit an accepted historical artifact to add these fields. Create a new
  revision/admission and supersede through the normal lifecycle instead;
- recompute all payload and file hashes after regeneration. Do not copy hashes
  from an old Card or acceptance packet.

Refresh installed/copied skills after pulling this Factory revision:

```bash
python3 setup.py install
```

Then use the normal checked workflows in
`gameplay/docs/OBJECTIVE_GAMEPLAY_WORKFLOW.md` and
`studio/docs/BASELINE_ADMISSION_WORKFLOW.md`.
