# Studio semantic-alignment workflow

Studio must not require a user to know Factory terms before their input is
handled correctly. A message such as “I have some new ideas; you work out what
to do” is sufficient material input. The operator—not the user—owns routing,
authority continuity, and the decision to ask a genuinely unresolved question.

This workflow guards the transition that precedes product/gameplay reviewers:

```text
A_t + Q_t + U_t -> candidate transition/output O_t
                       -> fresh semantic review
                       -> present or revise
```

- `A_t`: exact active product, gameplay-system, baseline, and repository
  authority;
- `Q_t`: pending human decisions and their lifecycle state;
- `U_t`: the exact raw user input, without a rewritten brief;
- `O_t`: the exact proposed human-facing answer, question, or decision surface.

The harness evaluates the transition. It does not approve product taste,
gameplay fun, a decision card, or a build.

## When the gate is mandatory

Run it before presenting output when any of these is true:

- new user input may add, modify, revoke, or ambiguously affect product,
  gameplay-system, scope, or accepted-baseline authority;
- the operator reopens Idea exploration or revises a Studio gameplay system;
- the operator wants to ask a blocking product/gameplay question;
- a new or revised Studio decision card is about to be shown to the user.

Do not run it for an exact approval token already requested, mechanical command
output, or a non-material progress acknowledgement.

## Step 1 — author the exact transition input

The candidate-output author writes, in the game repo:

```text
design/studio/interaction_alignment/<interaction_id>/
  STUDIO_SEMANTIC_ALIGNMENT_INPUT.json
```

Use `schemas/studio_semantic_alignment_input.schema.json`. It binds:

- the exact raw user message and UTF-8 SHA;
- every active authority actually consulted;
- every pending decision card and whether it remains pending or is superseded;
- input deltas classified as `ADD`, `MODIFY`, `REVOKE`, or `AMBIGUOUS`, each
  with an exact user quote;
- the proposed workflow transition;
- the exact candidate output and SHA;
- material output claims with provenance;
- every proposed human question, the authorities searched, and why none of
  them answers it.

Authority is delta-updated. New input does not erase prior `USER_FIXED` or
repository authority merely because exploration is reopened. Untouched
authority remains active. AI interpretation is an `AI_HYPOTHESIS`, not an
implicit human decision.

## Step 2 — use one fresh subagent/context

A subagent/context that did not author the candidate reads the raw input, every
bound authority, pending-decision state, and exact candidate output. It writes:

```text
design/studio/interaction_alignment/<interaction_id>/
  STUDIO_SEMANTIC_ALIGNMENT_REVIEW.json
```

Use `schemas/studio_semantic_alignment_review.schema.json`. The reviewer checks:

1. complete input-delta coverage;
2. preservation of authority not revoked by the user;
3. provenance for every material output claim;
4. necessity of every human question;
5. absence of semantic proxy substitution—ledger is not gameplay, watching is
   not a battle move, replay is not a loop, implementation is not acceptance;
6. correct Studio/specialist route and scope;
7. a genuine human boundary rather than avoidable clarification;
8. a proportional user-facing surface;
9. explicit disposition of every pending card.

The candidate author may not self-review. If the runtime cannot provide a fresh
subagent/context, the Studio stops before presenting a material answer rather
than self-certifying it.

Review verdicts are:

- `PASS_ALIGNMENT` — the material response may be presented;
- `REVISE_BEFORE_USER` — return privately to the candidate author and rerun the
  review; do not show the rejected draft;
- `HUMAN_RULING_GENUINELY_REQUIRED` — the exact inventoried question or
  decision surface may be presented.

Validate the artifacts:

```bash
python3 <STUDIO_ROOT>/studio/alignment.py validate \
  --game-repo <GAME_REPO> \
  --input design/studio/interaction_alignment/<interaction_id>/STUDIO_SEMANTIC_ALIGNMENT_INPUT.json \
  --review design/studio/interaction_alignment/<interaction_id>/STUDIO_SEMANTIC_ALIGNMENT_REVIEW.json
```

## Decision-card presentation and supersession

Studio cards begin with `human_verdict.status = PENDING`. Generate the exact
candidate surface for the alignment input, but do not present it yet:

```bash
python3 <STUDIO_ROOT>/gameplay/design_gate.py draft-card-surface \
  --card <CARD_PATH>
```

After a fresh review returns `HUMAN_RULING_GENUINELY_REQUIRED`, register the
card. Every prior pending card marked `SUPERSEDE_PENDING` in the alignment
input must be named on the command:

```bash
python3 <STUDIO_ROOT>/gameplay/design_gate.py register-card \
  --game-repo <GAME_REPO> \
  --card <CARD_PATH> \
  --alignment-input <ALIGNMENT_INPUT_PATH> \
  --alignment-review <ALIGNMENT_REVIEW_PATH> \
  --supersede-payload <OLD_PENDING_PAYLOAD_SHA256> \
  --recorded-at <ISO_8601>
```

The game-owned
`design/studio/STUDIO_DECISION_CARD_REGISTER.json` is the lifecycle source of
truth. Supersession is symmetric and acyclic. A superseded payload remains
available as history but cannot be rendered, approved, or enter production.
The first register write may import an older pre-register `PENDING` card only
as `SUPERSEDED`, using the new transition review as invalidation evidence; it
can never import that legacy payload as pending or approved. Every revised card
uses a new `card_id`.

Only the checked renderer may now present the surface:

```bash
python3 <STUDIO_ROOT>/gameplay/design_gate.py render-card \
  --game-repo <GAME_REPO> \
  --card <CARD_PATH>
```

Record the exact ruling through the lifecycle command rather than editing the
card and register independently:

```bash
python3 <STUDIO_ROOT>/gameplay/design_gate.py record-card-verdict \
  --game-repo <GAME_REPO> \
  --card <CARD_PATH> \
  --verdict-token "USER_APPROVED <DECISION_PAYLOAD_SHA256>" \
  --recorded-at <ISO_8601>
```

Production validation requires both the exact `USER_APPROVED` card token and
an `USER_APPROVED` register entry. An older pending hash cannot regain authority
after a later aligned card supersedes it.
