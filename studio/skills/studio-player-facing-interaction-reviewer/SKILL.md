---
name: studio-player-facing-interaction-reviewer
description: Fresh pre-production player-perspective review of one exact Player-Facing Interaction Contract. Use before the final Studio Gameplay Decision Card review; it rejects prose-only, popup/dialogue-only, invisible, non-interactive, stale, or untestable gameplay designs without claiming that runtime evidence passed.
---

# Studio Player-Facing Interaction Reviewer

Use only as a fresh subagent/context after a game-owned
`PLAYER_FACING_INTERACTION_CONTRACT.json` exists and before final Card review,
semantic alignment, registration, or human presentation.

Read the exact current scene composition frames/prototype, target-player prior
knowledge, Product authority, Studio gameplay-system manifest, and contract.
Do not accept an author explanation in place of what the proposed player
surface exposes.

For every claimed beat, verify the visible entry state, perceivable cause,
visible goal, concrete control/input, player judgment, ordered input-response
sequence, immediate world/person response, persistent visible return state,
and discoverable changed next affordance. Dialogue, popup, journal, marker,
hidden flag, straight traversal, or state text may support the beat but cannot
perform the claimed player work. Block abstract verbs such as “investigate”,
“escort”, “track”, “protect”, or “report” unless decomposed into ordered inputs
and observable responses. Block missing/garbled/fallback localization that
prevents the target player from reading the interaction.
Require the `current_scene_composition` records to be contiguous and to cover,
for every beat in contract order, `ENTRY`, `AFFORDANCE`, `EXPECTED_RESPONSE`,
and `PERSISTENT_RETURN` in that order. One static screenshot or unbound prose
is not a player-surface sequence; copied or renamed files with the same visual
SHA cannot be relabelled as different temporal moments.
Also verify that `player_entry_knowledge` contains only de-identified knowledge
available at scenario entry: no beat ids, sequence labels, intended solution,
or information learned only in a future beat. Only that exact string list may
be copied into the blind Phase-A input.

Write only the objective-local
`PLAYER_FACING_INTERACTION_CONTRACT_REVIEW.json`. Bind the exact contract,
Product and Studio system SHA values. Inventory every beat and every required
finding. The only passing design-stage statuses are:

```text
hypothesis_lifecycle = TESTABLE_DESIGN_ONLY
beat verdict = PASS_TESTABLE_DESIGN
verdict = PASS_PLAYER_FACING_INTERACTION_DESIGN
```

Never write `PASS`, `ACCEPTED`, or an observed-result status for a validation
hypothesis. This review proves concrete testable design, not implementation,
observation, player understanding, fun, or human acceptance.
