---
name: studio-gameplay-decision-card-reviewer
description: Fresh final Factory-compliance audit of one exact pending Studio Gameplay Decision Card. Use only when delegated by game-studio-factory after required system/stage reviews and before semantic alignment and human presentation; it rejects thin click/dialogue designs, missing causal gameplay, scope or red-line breaches, incomplete gates, and false completion claims without taking the human verdict.
---

# Studio Gameplay Decision Card Reviewer

This is the independent **final Card result audit**, not a Card author, a
step-local reviewer, or the semantic-alignment reviewer. Use it only as a fresh
subagent/context delegated by `game-studio-factory` for one exact pending
`STUDIO_WHOLE_GAME` Card.

## Resolve and bind the result

1. Resolve `<GAME_REPO>` and `<STUDIO_ROOT>` from the delegated task. Never scan
   sibling repos.
2. Read `<STUDIO_ROOT>/studio/AGENTS.md`,
   `<STUDIO_ROOT>/studio/docs/GAMEPLAY_SYSTEM_WORKFLOW.md`, the Gameplay Factory
   landing/AGENTS, and the exact workflow contracts applicable at this Card
   boundary.
3. Read the exact pending `GAMEPLAY_DECISION_CARD.json`, its Product authority,
   Factory constraints, Studio gameplay-system manifest/system, both system
   reviews, the exact Player-Facing Interaction Contract and fresh design
   review, and any already-due objective/span authority named by the Card.
4. Do not rely on the Card author's summary when a bound artifact exists.
5. Write only the objective-local
   `GAMEPLAY_DECISION_CARD_FACTORY_REVIEW.json` from the Factory template.

## Independence

- `reviewer_context_id` must differ from the Card author, gameplay-system
  author, product-fidelity reviewer, cycle-closure reviewer, and the later
  semantic-alignment reviewer.
- Do not edit the Card or its authorities. A failure returns privately to the
  author for revision and a new fresh review.
- Do not issue the human verdict, claim the gameplay is fun, accept a build, or
  substitute this audit for quant/experience/conformance/runtime reviews due at
  their own stages.

## Required end-to-end audit

Audit the **final Card as one result**, not merely whether each earlier file has
a passing label:

- active Product authority, constraints, scope, commitments, and red lines are
  preserved;
- the proposed first slice is still minimum **cycle-complete**, rather than a
  convenient isolated feature;
- the declared playable span has enough meaningful-choice supply for its scope
  and applicable Gameplay Profile cadence/override; a handful of clicks is not
  inflated into minutes of gameplay, and missing not-yet-due quant work is not
  falsely described as already validated;
- each claimed gameplay unit contains information, a real guess or judgment,
  commitment, consequence, and later-emotion influence; a certain-outcome
  click is not counted;
- dialogue advance, raw input, straight traversal, objective arrival, task,
  journal, hotspot, meter, or passive state change is not presented as gameplay
  without a complete player-engagement chain;
- the player performs legible work, receives a world/person response, and that
  response carries information or changed capacity into the next decision;
- reward/reinvestment changes state read by the next decision and the two-lap
  witness materially changes lap two;
- every declared option, posture, route, or strategy is materially distinct in
  work, cost, response, obligation, or reachable follow-up rather than reskinned
  prose, punishment, or a dead end;
- costs, obligations, failure/recovery, and validation hypotheses are concrete
  and falsifiable at the promised boundary;
- every Factory gate already due is present, valid, exact-SHA bound, and fresh;
- every claimed beat is concretely visible/interactable in the player-facing
  contract rather than explainable only through Card prose, state, popup,
  dialogue, task text, journal, marker, or code;
- work due only after human approval is not falsely claimed complete and its
  absence is not misreported as a present defect.

Independently inventory every Card claim exactly once. Non-hypothesis claims
use `PASS_DESIGN_CLAIM`; hypotheses use `TESTABLE_DESIGN` and must never be
labelled `PASS` or `ACCEPTED`. Map each claim to one or
more required Factory findings, record exact evidence-based rationale, and
inventory every Product causal-link id, applicable Factory-constraint id, and
Product non-goal id realized by the bound system. For each authority id, map
its exact system transition ids to the corresponding projected `cycle.*` Card
claims and the Factory findings it satisfies; do not cite one generic promise
or boilerplate rationale for unrelated requirements. Block on any unsupported
claim, missing authority/transition mapping, or omitted applicable requirement.
Passing step-local reviews do not override a contradictory final Card.

## Result

Only a review with:

```text
verdict = PASS_CARD_FACTORY_COMPLIANCE
blocking_findings = []
```

may proceed. Validate it before returning:

```bash
python3 <STUDIO_ROOT>/gameplay/design_gate.py validate-card-review \
  --game-repo <GAME_REPO> \
  --card design/gameplay/objective_gameplay/<OBJECTIVE_ID>/GAMEPLAY_DECISION_CARD.json \
  --review design/gameplay/objective_gameplay/<OBJECTIVE_ID>/GAMEPLAY_DECISION_CARD_FACTORY_REVIEW.json
```

Return only the checked review artifact/status to the Studio author. The
separate semantic-alignment gate still reviews the exact eventual human-facing
surface; neither review replaces the other. The later alignment input must bind
this exact review path/SHA as active `REPO_EVIDENCE` with authority id
`card.factory-compliance-review`; `register-card` rejects an unbound review.

When any check fails, record each exact blocker under `blocking_findings`, mark
the affected requirement/claim findings `BLOCK`, set
`verdict = REVISE_CARD_BEFORE_HUMAN`, and return it privately. It must not be
registered or shown to the human; the author revises the Card and delegates a
new fresh whole-result review.
