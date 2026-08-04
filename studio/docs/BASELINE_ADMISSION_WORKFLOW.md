# Accepted Playable Baseline admission workflow

Baseline admission has one entry and exactly two causal cases. The caller does
not choose a convenient case to avoid evidence; `baseline.py start` checks the
current Studio state and routes it.

```bash
python3 <STUDIO_ROOT>/studio/baseline.py start --game-repo <GAME_REPO>
```

Possible ready states:

- `BASELINE_RECONSTRUCTION_INPUT_REQUIRED` — no trusted baseline exists, or
  the user explicitly requested `--reconstruct`;
- `BASELINE_PROMOTION_INPUT_REQUIRED` — an exact current baseline exists and
  the just-completed workflow must be admitted as its successor.

Invalid or hash-mismatched current state returns `BLOCKED_BY_BASELINE_STATE`.
It never silently falls back to a clean slate.

## Case 1 — complete reconstruction

`RECONSTRUCT` creates a complete accepted baseline from the current game, not
an incremental patch. It is used for initial Studio adoption or an explicitly
authorized rebuild.

It requires:

- a committed runtime revision with no non-Studio dirty source/data paths;
- exact Product Thesis authority;
- a reproducible launch command and hashed build artifact;
- the complete playable scope;
- a complete reconstruction inventory whose discovered unit ids exactly equal
  the admitted unit ids, with evidence for excluded candidates;
- every gameplay unit admitted into the baseline, each with an independent
  fresh `ACCEPTED` review, exact runtime evidence, canonical expected-experience
  authority, and a `USER`-owned `HUMAN_PLAYTEST_ACCEPTED` verdict on the exact
  build;
- deterministic verification commands and hashed results;
- only non-blocking known gaps.

It has no predecessor regression and no workflow-completion handoff. An
explicit rebuild records the exact superseded baseline but never edits it.

Use:

```text
studio/templates/BASELINE_RECONSTRUCTION_INPUT.json
studio/templates/BASELINE_RECONSTRUCTION_INVENTORY.json
studio/templates/GAMEPLAY_ACCEPTANCE_INPUT.json
studio/templates/GAMEPLAY_ACCEPTANCE_REVIEW.json
```

## Case 2 — post-workflow promotion

`PROMOTE` is the normal Studio ratchet after a Game AI Factory workflow and
ordinary production have finished:

```text
B_t + IMPLEMENTED_PENDING_ACCEPTANCE workflow completion
    + fresh acceptance(new/repaired units)
    + PASS regression(all units in B_t)
    -> B_(t+1)
```

It requires:

- the exact current baseline path and SHA;
- a `STUDIO_WORKFLOW_COMPLETION.json` bound to the committed implementation
  revision, exact Factory revision, source authorities, implementation results,
  tests, unit ids, and production-context ids;
- fresh acceptance reviews whose reviewer context is not any production
  context, whose admission-local `GAMEPLAY_ACCEPTANCE_INPUT_<unit_id>.json`
  binds the exact admitted unit authority and states the expected player
  experience, and whose human playtest verdict is explicitly accepted by the
  user;
- a fresh regression review covering **exactly every predecessor gameplay
  unit**;
- explicit gap resolution ids so old gaps cannot disappear by omission.

The compiler replaces accepted units only when their ids are explicitly
admitted, appends new units, preserves all other predecessor units, derives
the new gap ledger, and never mutates `B_t`.

Use:

```text
studio/templates/STUDIO_WORKFLOW_COMPLETION.json
studio/templates/GAMEPLAY_ACCEPTANCE_INPUT.json
studio/templates/GAMEPLAY_ACCEPTANCE_REVIEW.json
studio/templates/BASELINE_REGRESSION_REVIEW.json
studio/templates/BASELINE_PROMOTION_INPUT.json
```

## Compile and check

Inputs live in a unique admission directory:

```text
design/studio/admissions/<admission_id>/
  BASELINE_ADMISSION_INPUT.json
  ...review and completion records...
```

After fresh reviewers have written their evidence verdicts and the user has
recorded a playtest verdict on each exact build/authority pair:

```bash
python3 <STUDIO_ROOT>/studio/baseline.py compile \
  --game-repo <GAME_REPO> \
  --input design/studio/admissions/<admission_id>/BASELINE_ADMISSION_INPUT.json

python3 <STUDIO_ROOT>/studio/baseline.py check \
  --game-repo <GAME_REPO> \
  --input design/studio/admissions/<admission_id>/BASELINE_ADMISSION_INPUT.json
```

Successful compilation writes:

```text
design/studio/admissions/<admission_id>/BASELINE_ADMISSION_RESULT.json
design/studio/baselines/<baseline_id>/ACCEPTED_PLAYABLE_BASELINE.json
design/studio/STUDIO_RUN_STATE.json
```

Every path is resolved and every material is validated before any directory or
artifact is created. Baselines and admission results are immutable: exact
re-runs are idempotent; differing existing content fails closed. The mutable
run state may advance only from the exact predecessor.

Successful admission sets `STUDIO_READY_TO_SCALE`; it does not by itself claim
that the user's requested production horizon is complete or set
`STUDIO_GOAL_DELIVERED`.

## Acceptance boundary

`gameplay/reader.py` may prepare structurally valid runtime evidence, but it
does not issue the gameplay verdict. Production tests and
`IMPLEMENTED_PENDING_ACCEPTANCE` also do not issue it. A fresh reviewer may
write the evidence comparison `ACCEPTED`, but baseline promotion additionally
requires a `USER`-owned `HUMAN_PLAYTEST_ACCEPTED` verdict. The compiler merely
verifies and binds both decisions. Legacy v1 reviews and workflow completions
remain readable for historical `check` or exact idempotent re-runs; they cannot
authorize a new admission.
