# Studio semantic-alignment workflow

Studio must not require a user to know Factory terms before their input is
handled correctly. A message such as “I have some new ideas; you work out what
to do” is sufficient material input. The operator—not the user—owns routing,
authority continuity, and the decision to ask a genuinely unresolved question.

This workflow guards the transition that precedes product/gameplay reviewers:

```text
A_t + Q_t + U_t -> candidate transition/output O_t + authority changes C_t
                       -> fresh semantic review
                       -> present or revise
```

- `A_t`: exact active product, gameplay-system, baseline, and repository
  authority;
- `Q_t`: pending human decisions and their lifecycle state;
- `U_t`: the exact raw user input, without a rewritten brief;
- `O_t`: the exact proposed human-facing answer, question, or decision surface.
- `C_t`: every product/system/card/plan artifact changed by the interpretation.

The harness evaluates the transition. It does not approve product taste,
gameplay fun, a decision card, or a build.
It also does not turn later, not-yet-entered workflow stages into present
defects: a valid cycle may correctly exist before unit breakdown, plans, specs,
or implementation.

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
- any elliptical reply bound to the exact reviewed prior question and option
  that gives the reply meaning;
- every active authority actually consulted;
- every authority artifact the transition creates, revises, activates,
  supersedes, or archives;
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
authority remains active. AI framing is `AI_SYNTHESIS` and uncertain belief is
`AI_HYPOTHESIS`; neither is an implicit human decision.

Every visible line in the candidate surface is one mandatory material claim
unit except mechanical wrappers: mode headers, fence markers, source lists,
payload/reply tokens, and separately inventoried whole-line questions. Headings
remain covered because a title can itself smuggle a product conclusion.
`output_claims` must quote each unit in full; a selected list of convenient
claims is invalid. Distinguish:

- `NEW_USER_INPUT` — exact meaning supplied by the current user message;
- `BOUND_USER_RESPONSE` — meaning created when the current exact reply selects
  one exact option on a reviewed prior surface;
- `PRESERVED_AUTHORITY` — already-active authority;
- `REPO_EVIDENCE` — an exact repository fact;
- `REFERENCE_EVIDENCE` — what an external source actually establishes;
- `AI_SYNTHESIS` — a proposed framing or relation constructed from inputs;
- `AI_HYPOTHESIS` — an uncertain belief requiring validation.

Reference product existence does not prove player demand. A reusable scene
container does not prove a new landmark has no engineering risk. Conservative
provenance is required when one line combines user facts and AI synthesis.

### Elliptical replies are not self-interpreting

`b`, `yes`, `that one`, and similar replies do not carry their full meaning in
their own bytes. When a material delta depends on a prior menu/question, record
`response_bindings` with the prior alignment input/review, question id, selected
option id/quote, and accepted response token. The resulting user-owned claim is
`BOUND_USER_RESPONSE`, never `REPO_EVIDENCE` or unattributed AI synthesis.
A one-token alphanumeric reply is rejected mechanically without this binding.

The prior question must list exact `answer_options`. Do not reconstruct a menu
after the answer or attach a short reply to an option that was never shown.

### Internal authority changes are part of the output

Human-facing brevity does not exempt hidden authority artifacts from review.
List each changed Product input, Product Thesis, Factory Constraints, Studio
system, decision card, baseline, or production plan in `authority_changes`.
The fresh reviewer reads the exact SHA-bound artifacts and cites every change
in its findings. Product activation is fail-closed unless the exact canonical
Product package passed this review.

## Step 2 — use one fresh subagent/context

A subagent/context that did not author the candidate reads the raw input, every
bound authority, pending-decision state, and exact candidate output. It writes:

```text
design/studio/interaction_alignment/<interaction_id>/
  STUDIO_SEMANTIC_ALIGNMENT_REVIEW.json
```

Use `schemas/studio_semantic_alignment_review.schema.json`. The reviewer checks:

1. complete input-delta coverage;
2. fidelity of every short-answer binding;
3. preservation of authority not revoked by the user;
4. fidelity of every changed authority artifact;
5. provenance for every material output claim;
6. necessity of every human question;
7. absence of semantic proxy substitution—ledger is not gameplay, watching is
   not a battle move, replay is not a loop, implementation is not acceptance;
8. correct Studio/specialist route and scope;
9. a genuine human boundary rather than avoidable clarification;
10. a proportional user-facing surface;
11. explicit disposition of every pending card.

The reviewer must independently inventory every complete material candidate
line and match it to exactly one author claim. The validator compares this
inventory to the candidate itself. An omitted line, mixed/unclear provenance,
or disagreement with the author is blocking and requires a private rewrite.

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
