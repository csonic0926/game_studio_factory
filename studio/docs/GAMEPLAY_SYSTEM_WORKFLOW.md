# Idea-to-gameplay-system workflow

Studio owns the transition from a commissioned Product Thesis to one exact
gameplay system. Gameplay Factory owns bounded realization of that system; it
must not be asked to invent the missing motivational loop while implementing a
feature.

## Formal object and legal transition

Let `P` be the exact Product Thesis plus its causal links and Factory
constraints. Let `G` be a directed gameplay-system graph:

```text
G = (stages, state objects, transitions, cycle path, feedback states)
```

The legal transition before objective selection is:

```text
commissioned P
  -> author G
  -> product-fidelity review(G, P)
  -> cycle-closure review(G)
  -> STUDIO_GAMEPLAY_SYSTEM_READY
  -> select a minimum cycle-complete vertical slice
  -> bind the active project Card-authoring standard
  -> author its required project composition artifact(s)
  -> author/review the Player-Facing Interaction Contract
  -> author the exact pending Card v3
  -> fresh project-standard Card review
  -> final Card Factory-compliance review
  -> semantic-alignment review of the exact human surface
```

It is forbidden to jump from a Product Thesis directly to a convenient
feature, episode, or objective. A sequence that ends at result/settlement and
offers only “play again” is `BLOCKED_BY_LINEAR_GAMEPLAY`.

## Required causal cycle

The cycle path must contain all of these phases:

```text
PLAYER_DECISION -> COMMITMENT -> RESOLUTION -> REWARD
  -> REINVESTMENT -> RETURN -> PLAYER_DECISION
```

Names and presentation may differ, but the causal roles may not. At least one
player-visible feedback state must be written by `REWARD`, and every declared
feedback state must be written by reward/reinvestment and read by the next
player decision. Reinvestment cannot fabricate a missing reward edge.

The two-lap witness must show:

```text
lap 1 decision
  -> resolution
  -> visible feedback-state delta
  -> changed goal/opportunity/capacity
  -> materially changed lap 2 decision
```

A timer, replay button, new cosmetic, or repeated identical choice is not by
itself a feedback edge.

## Product fidelity and coupled systems

Every Product Thesis causal-link id and every applicable `all`/`gameplay`
Factory constraint must be realized by named transitions. Every compiled
product non-goal must have explicit `non_goal_coverage`, and the
product-fidelity reviewer must confirm that it bounds the system without
contradicting a declared causal link. Any systems whose
coupling carries a product promise—such as “options packaged as battle”—must be
listed in `coupled_systems` and marked `required_in_first_baseline: true`.

Studio may shrink:

- content count;
- visual/audio fidelity;
- number of opponents or scenarios;
- map breadth;
- production horizon.

Studio may not shrink away a load-bearing causal edge or defer one side of a
product-level coupled system. “Smallest” means the minimum vertical slice that
still completes the cycle twice, not the smallest isolated feature.

“Gamification,” positive response, repeat motivation, and reward language are
cycle requirements, not visual tone. A service/exhibition can lack conventional
combat or challenge mechanics while still requiring a real
decision/reward/reinvestment/return loop. A Product non-goal that turns the
former into “no gameplay cycle” is a blocking authority contradiction.

## Artifacts and validation

Write game-owned artifacts under:

```text
design/studio/gameplay_system/<system_id>/
  STUDIO_GAMEPLAY_SYSTEM.json
  STUDIO_GAMEPLAY_SYSTEM_REVIEW_PRODUCT.json
  STUDIO_GAMEPLAY_SYSTEM_REVIEW_CYCLE.json
  STUDIO_GAMEPLAY_SYSTEM_MANIFEST.json
```

The two reviews use different fresh contexts; neither may be the system author.
The product-fidelity reviewer covers every causal link and constraint. The
cycle-closure reviewer independently checks graph closure, reward feedback,
the two-lap difference, coupled-system preservation, and absence of a proxy
loop.

Validate before producing a Gameplay objective:

```bash
python3 <STUDIO_ROOT>/studio/cycle.py validate \
  --game-repo <GAME_REPO> \
  --manifest design/studio/gameplay_system/<system_id>/STUDIO_GAMEPLAY_SYSTEM_MANIFEST.json
```

Only `STUDIO_GAMEPLAY_SYSTEM_READY` may feed a Studio-routed Gameplay decision
card. Before the Card exists, the game must exact-bind its active, adopted
Project Gameplay Decision Card Authoring Standard and write every project-owned
composition artifact kind that standard requires. A Scene/Beat Map is one
possible project answer, not a Factory default. The composition freezes the
project's playable span, lap/loop boundaries, ordered scene/beat or equivalent
structure, transitions, interactions, branches, resolution/settlement,
failure/recovery, persistent return, and validation plan at the granularity the
project adopted. Follow the Gameplay Factory's
[`PROJECT_CARD_AUTHORING_STANDARD_WORKFLOW.md`](../../gameplay/docs/PROJECT_CARD_AUTHORING_STANDARD_WORKFLOW.md).

The game must also add an objective-local Player-Facing Interaction Contract
grounded in the current real scene composition and obtain a fresh
`PASS_PLAYER_FACING_INTERACTION_DESIGN` review. Abstract verbs, explanatory
prose, state ledgers, dialogue/popup advance, markers, straight traversal, and
static frames without input-response work cannot satisfy this gate. The card
binds the project standard, composition artifacts, a fresh independent
`PASS_PROJECT_CARD_AUTHORING_STANDARD` review, the contract/review, plus the
manifest's exact SHA and deterministically projects
the system promise, ordered cycle transitions, coupled-system roles, and
forbidden linearizations. Only additional `scope.*` commitments/red lines may
be authored for the bounded objective before human approval. Later objective
design therefore cannot silently replace the system.

At the human gate, render only this compact projection and its
`decision_payload_sha256`. Persist diagnostics and full system/spec artifacts;
do not make the human read them unless requested. The exact ruling token is
`USER_APPROVED <decision_payload_sha256>`.

Before semantic alignment, one additional fresh context—different from the
project-standard reviewer and the interaction-contract reviewer—must audit the exact
pending Card as a complete result using the
`studio-gameplay-decision-card-reviewer` skill. It reads the Card and all bound
Product/system/project/composition/review authority, inventories every Card
claim, and checks every Factory obligation already due at this boundary. The
project review owns the game's standard; this reviewer owns generic Factory
compliance, and neither substitutes for the other. In particular, passing
project or cycle reviews cannot excuse a Card whose playable substance is certain-outcome
clicks, dialogue/task/marker advancement, missing player work/response/
carry-forward, reskinned or unreachable alternatives, or an unearned claim
that later production/acceptance is complete, or an interaction contract whose
claims exist only outside the player surface. Only
`PASS_CARD_FACTORY_COMPLIANCE` proceeds. The reviewer neither edits the Card
nor owns the human verdict.

Before that surface is presented, follow
[`SEMANTIC_ALIGNMENT_WORKFLOW.md`](SEMANTIC_ALIGNMENT_WORKFLOW.md). A fresh
subagent/context must compare the raw user input, still-active authority,
pending-card state, and exact candidate surface. Product-fidelity and
cycle-closure reviews do not replace this gate: they validate `G` after the
operator has interpreted the user, while semantic alignment validates the
interpretation transition itself. Register the reviewed pending card so any
superseded pending payload becomes mechanically ineligible. The final-Card
reviewer and semantic-alignment reviewer must be different contexts; neither
replaces the other.
