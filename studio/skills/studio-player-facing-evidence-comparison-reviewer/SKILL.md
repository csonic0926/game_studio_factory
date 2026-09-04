---
name: studio-player-facing-evidence-comparison-reviewer
description: Perform Phase B of the Studio player-facing evidence gate after an immutable blind observation. Freshly compare what the observer actually saw with the exact interaction contract, Decision Card, Studio system, and runtime evidence without rewriting missing observations from design prose.
---

# Studio Player-Facing Evidence Comparison Reviewer

Run only after a different fresh context has frozen a valid
`PLAYER_FACING_BLIND_OBSERVATION.json`. Bind the exact committed game revision,
build id, runtime interaction evidence, blind observation, Player-Facing
Interaction Contract and review, approved Decision Card, and Studio gameplay
system.

For every contract/runtime beat, cite unique existing neutral `attempt.N`
records from the sealed blind observation and every-and-only matching ordered
runtime trace sequence. Consume every sealed attempt exactly once across beat
comparisons; never reuse one generic attempt as proof for multiple beats. Mark
cause, goal, affordance, input/judgment, visible
response, persistent change, and next motive `OBSERVED` only when Phase A
actually recorded them in the cited structured attempt. Design prose, hidden
state, logs, tests, popup text, arbitrary citation strings, or code cannot fill
a missing observation.
Reject swapped attempts, reused underlying trace captures, a before-only blind
bundle, or arbitrary citations even if their prose describes the intended
answer.

Map every Card hypothesis from `TESTABLE_DESIGN` to exactly one runtime status:
`OBSERVED_SUPPORT` or `OBSERVED_REJECT`. Never call a design-stage `reject if`
statement passed. A passing comparison requires readable target localization,
all dimensions observed, all hypotheses supported, no blockers, and:

```text
verdict = PASS_PLAYER_FACING_COMPARISON
```

Write only `PLAYER_FACING_COMPARISON_REVIEW.json`. This review still cannot
supply the separate user-owned human playtest verdict.
