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
Factory constraint must be realized by named transitions. Any systems whose
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
card. The card binds the manifest's exact SHA and deterministically projects
the system promise, ordered cycle transitions, coupled-system roles, and
forbidden linearizations. Only additional `scope.*` commitments/red lines may
be authored for the bounded objective before human approval. Later objective
design therefore cannot silently replace the system.

At the human gate, render only this compact projection and its
`decision_payload_sha256`. Persist diagnostics and full system/spec artifacts;
do not make the human read them unless requested. The exact ruling token is
`USER_APPROVED <decision_payload_sha256>`.
