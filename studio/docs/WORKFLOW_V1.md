> Version 1 compatibility contract. Relative paths below resolve from the owning department root.
> New v2 work uses `factory_core/docs/WORKFLOW.md`; this preserves v1 semantics/history and domain reference detail.

# AGENTS — Game Studio Factory

Game Studio Factory is the autonomous whole-game operator. The specialist Game
AI Factories (`idea/`, `gameplay/`, `story/`, `asset/`, `sound/`) are its
capability layer; they do not independently own whole-game delivery.

Read [`docs/AI_CALLER_LANDING.md`](docs/AI_CALLER_LANDING.md), then preserve
these invariants:

1. **A runnable demo is not a delivered game.** The Studio may reduce content,
   fidelity, breadth, or production horizon, but it may not reinterpret
   “game” as interactive software without accepted gameplay.
2. **Operate from an Accepted Playable Baseline.** Each production cycle starts
   from one reproducible accepted game revision and promotes exactly one next
   accepted baseline after new-gameplay acceptance plus prior-baseline
   regression.
3. **Gameplay Ratchet.** Completed code/assets/plans do not earn promotion. A
   candidate that weakens the existing game is repaired, rejected, or narrowed.
   Every acceptance review binds the unit's exact experience authority and
   Factory revision; AI review evidence cannot substitute for a recorded human
   playtest verdict on the exact build.
4. **Research before repetition.** After diagnosing the active gameplay
   pressure, use web research to acquire external design tokens from same-type,
   cross-genre, and non-game references. Extract transferable mechanisms; never
   force a reference into production merely because it was researched.
5. **Parallelize production, not conflicting authority.** Workstreams may run
   concurrently only when their state writes, player-attention surfaces,
   reward/decision systems, and file ownership do not conflict.
6. **Specialists retain their contracts.** Studio selects and composes work;
   each specialist factory still validates its own artifacts and writes outputs
   only into the target game repo.
7. **Delivery is a promotion decision.** Only a checked accepted baseline with
   a runnable build, accepted gameplay units, regression evidence, and no
   blocking gap can be presented as Studio delivery.
8. **Admission has two cases only.** `RECONSTRUCT` inventories and freshly
   accepts the complete current game. `PROMOTE` consumes one exact predecessor,
   a revision-pinned completed workflow handoff, authority-bound fresh
   acceptance plus human playtest verdict for changed gameplay, and regression
   of every predecessor unit. Never use reconstruction to erase a
   valid ratchet history or promotion to inherit unreviewed gameplay.
9. **Studio owns Idea -> gameplay system.** A commissioned Product Thesis must
   become a closed decision/commitment/resolution/reward/reinvestment/return
   graph before Studio selects an objective. The reward must change a visible
   state read by the next decision, and a two-lap witness must show a materially
   different second decision. A result plus replay prompt is linear, not a
   gameplay cycle.
10. **Bound the content, never the causal loop.** The first unit is the minimum
    cycle-complete vertical slice. Studio may reduce breadth, fidelity, content
    count, or opponent count; it may not defer a load-bearing product causal
    link or one side of a coupled system such as “options packaged as battle.”
11. **Human rules on a decision surface, not a generated full spec.** The
    human approves a compact gameplay decision card. A separate author may
    refine it into the full objective spec only when two fresh, independent
    conformance reviews prove both card-to-spec completeness and spec-to-card
    non-expansion. Never claim that the two artifacts are textually or
    semantically identical. Before the pending Card reaches semantic alignment
    or the human, an additional fresh final-Card reviewer—not the Card/system
    author or either system reviewer—must audit the exact Card and all bound
    authorities against every Factory requirement due at this boundary. It
    rejects certain-outcome clicks, dialogue/task/marker proxies, missing
    player-work -> response -> carry-forward chains, non-distinct or unreachable
    alternatives, scope/red-line breaches, and false gate/completion claims.
    Step-local reviews do not substitute for this whole-result audit.
    Before either review, the Card must bind the Project Gameplay Profile's
    active/adopted project Card-authoring standard, all project-required
    pre-Card composition artifacts, a fresh independent project-standard Card
    review, a game-owned player-facing interaction contract, and a fresh
    whole-sequence design review. The project review owns project-specific
    completeness; the final Card review owns generic Factory compliance, and
    neither substitutes for the other. The contract
    makes the current surface, input, response, persisted visible change, and
    next affordance concrete; prose, dialogue, popups, markers, or hidden state
    cannot substitute. Design hypotheses remain `TESTABLE_DESIGN`.
12. **Freshly review every material human transition.** Before presenting a
    material response, blocking question, or Studio decision card, bind the
    exact raw user input, active authority, pending decisions, candidate output,
    claim provenance, and proposed questions through
    [`docs/SEMANTIC_ALIGNMENT_WORKFLOW.md`](docs/SEMANTIC_ALIGNMENT_WORKFLOW.md).
    A fresh subagent/context—not the candidate author—must reject authority
    amnesia, semantic proxies, avoidable questions, and silent pending-card
    drift. This reviewer advises the transition; it never owns product taste or
    the human verdict.
    Short/elliptical replies bind to the exact prior reviewed question/option;
    they are never self-expanding user quotes. The same review binds every
    internal Product/system/card/plan authority changed by the interpretation,
    even when the human-facing surface stays compact.
13. **Product authority has an explicit lifecycle.** Read
    `design/product/PRODUCT_AUTHORITY_REGISTER.json` when present. Whole-direction
    revocation uses [`docs/PRODUCT_AUTHORITY_LIFECYCLE.md`](docs/PRODUCT_AUTHORITY_LIFECYCLE.md):
    snapshot the bounded authority package, align the exact user revocation
    before mutation, withdraw pending cards as `PRODUCT_ARCHIVED` without
    inventing human verdict tokens, and return to Idea exploration. A new
    commissioned thesis must be activated before downstream work.
14. **Gamification is a causal-loop obligation.** A service, exhibition, or
    utility may not need conventional combat/challenge mechanics, but a request
    for gamification, positive feedback, or repeated motivation still requires
    an actual decision/reward/reinvestment/return loop. “Not conventional
    gameplay” must not become “not a gameplay cycle.” Product non-goals are
    compiled downstream and product-fidelity review must prove they bound the
    loop without silently deleting it.
15. **Engine adapters provide evidence, not authority.** A passing import,
    bounded run, export, log assertion, screenshot, or future runtime trace may
    support technical verification and regression. It cannot issue the fresh
    gameplay verdict, replace the exact-build human playtest, or promote a
    baseline. For Godot projects use
    [`docs/GODOT_ENGINE_ADAPTER.md`](docs/GODOT_ENGINE_ADAPTER.md); respect its
    explicit capability gaps instead of inventing ad-hoc proof.
16. **Observe the player surface before reading the answer.** Every new
    gameplay acceptance binds a windowed exact-build input-to-visible-response
    evidence bundle. A fresh blind observer first receives only legitimate
    de-identified entry knowledge (never beat ids/sequence), controls, and
    player-facing output. A different preparer must attest that every
    Phase-A-visible field/path is free of answer-bearing ids, intended answers,
    future knowledge, and non-Phase-A material; a different fresh
    reviewer then compares that sealed observation with the interaction
    contract, Card, and system. Screenshots, input traces, tests, logs, state
    JSON, or task/dialogue text alone do not prove interaction. See
    [`docs/PLAYER_FACING_GAMEPLAY_EVIDENCE_GATE.md`](docs/PLAYER_FACING_GAMEPLAY_EVIDENCE_GATE.md).

## Formal production transition

Let `B_t` be the current Accepted Playable Baseline, `P_t` the diagnosed
pressure, `R_t` the external reference-token set, `G_t` the validated gameplay
system/cycle, and `U_t` one minimum cycle-complete gameplay unit. The only legal
promotion is:

```text
B_t + P_t + R_t -> synthesize/validate(G_t) -> decision_card(G_t)
    -> player-surface design contract/review -> design(U_t)
    -> production(U_t) -> integration
    -> exact-build interaction evidence -> blind observation/comparison
    -> fresh gameplay acceptance + regression(B_t)
    -> B_(t+1)
```

Every material human-facing arrow is additionally gated as:

```text
active authority + pending decisions + raw user input
  -> project-standard Card review when applicable
  -> final Card Factory compliance review when applicable
  -> candidate output -> separate fresh semantic alignment review -> user surface
```

Forbidden transitions:

- brief -> code/assets -> delivery;
- several locally complete systems -> assumed whole-game quality;
- failed/inconclusive gameplay acceptance -> accepted baseline;
- reference surface/theme -> copied feature without mechanism translation;
- candidate implementation state -> mutation of the prior accepted baseline
  record.
- Product Thesis -> convenient linear objective without a validated `G_t`;
- result/settlement -> replay prompt presented as a retention cycle;
- smallest isolated feature -> first baseline when it cuts a load-bearing
  causal edge;
- human approval of a short card -> assumed correctness of an unreviewed full
  spec.
- natural-language direction revocation -> fabricated per-card verdict token;
- external reference feature -> claimed proof of demand;
- one reusable scene-root fact -> claimed absence of system engineering risk;
- author-selected claim subset -> supposedly complete semantic review.

## Current foundation boundary

The baseline admission compiler/checker is operational and owns only evidence
binding plus state promotion; it does not issue gameplay verdicts. A persistent
autonomous multi-cycle scheduler is not implemented yet. The desktop Godot
adapter provides versioned opt-in debug instrumentation, frame-bound scenarios,
live sessions, structured/PNG/movie/performance capture, visual regression, and
debug/release runtime evidence. It remains `EVIDENCE_ONLY`, cannot author game
content, cannot approve a visual baseline, and cannot replace project semantic
observation or human gameplay acceptance. Never describe these bounded layers
as proof that unattended multi-day production is already operational.
