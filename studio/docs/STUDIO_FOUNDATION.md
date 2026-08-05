# Game Studio Factory foundation v0

## Why this layer exists

The Game AI Factories can produce bounded gameplay realizations. Scale becomes
healthy only after Studio has defined the system they realize and that unit is
genuinely playable. The Studio layer therefore scales **accepted gameplay**,
not token count, agent count, feature count, or runnable software.

The missing ownership boundary is now explicit:

```text
Idea Factory: Product Thesis and causal product promises
Studio:       exact closed gameplay system and motivational cycle
Gameplay:     bounded cycle-complete objective/spec and implementation
```

See [`GAMEPLAY_SYSTEM_WORKFLOW.md`](GAMEPLAY_SYSTEM_WORKFLOW.md). A Product
Thesis cannot route directly to an isolated feature merely because that
feature is easy to build or verify.

## 1. Accepted Playable Baseline

`B_t` is a reproducible whole-game state, not a branch, screenshot, plan, or
build-success claim. It binds:

- exact game revision and product authority;
- runnable build/launch evidence;
- the playable scope and its complete loop;
- every accepted gameplay unit, its canonical experience authority, fresh
  acceptance decision, validated Studio cycle, observed two-lap feedback, and
  human playtest verdict;
- regression evidence for previously accepted gameplay;
- known gaps and delivery blockers.

The first baseline may be small. It may not be an interactive software demo.

Admission has two typed transitions:

```text
RECONSTRUCT: committed game + complete fresh acceptance -> B0
PROMOTE: Bt + completed workflow + fresh acceptance + regression(Bt) -> Bt+1
```

Both are implemented by `baseline.py`; neither transition authors its own
acceptance verdict.

## 2. Gameplay Ratchet

A candidate system is locally complete when its owned production tasks pass.
It is globally promotable only when:

```text
new unit acceptance == ACCEPTED
and human playtest == HUMAN_PLAYTEST_ACCEPTED
and two-lap cycle == ACCEPTED_TWO_LAP_CYCLE
and predecessor regression == PASS
and integration blockers == []
and interactive_demo_only == false
```

Sunk production cost is never acceptance evidence. Failed candidates remain
candidate history or are repaired; they do not alter the accepted baseline
record.

## 3. Design Token Research

Repeated closed-loop production converges on increasingly tidy recombinations
of the repo's existing actions, rewards, and product vocabulary. Web research
is the exogenous input that prevents that creative collapse.

A useful research artifact separates:

```text
source observation
-> abstract transferable mechanism
-> player decision/emotional effect
-> translation into this game's ontology
-> conflicts and non-copy boundary
-> smallest falsifiable prototype
```

Search distance is deliberate: adjacent games, cross-genre games, and non-game
systems. Search is not a requirement to fuse references; `NO_FIT` is healthy.

## 4. Autonomous Production Loop

The Studio diagnoses the current game's pressure rather than blindly consuming
a feature backlog. It first synthesizes or revalidates the causal gameplay
system, then selects the **minimum cycle-complete vertical slice** that can
materially improve the whole game, freezes its authority/interfaces, and only
then parallelizes safe specialist production.

The vertical slice may reduce content, opponents, scenarios, and fidelity. It
may not cut `decision -> commitment -> resolution -> reward -> reinvestment ->
return`, omit a product causal link, or defer one side of a product-level
coupling. A replay button with unchanged next-decision state is not a cycle.

Safe parallelism requires non-overlap in:

- authoritative state writes;
- player-attention/UI surfaces;
- reward and decision economy;
- progression ownership;
- planned files and integration order.

When overlap exists, the work is sequenced against a refreshed baseline.

## Scale out and scale up

- **Scale out** repeats baseline promotion and safely increases the number of
  accepted gameplay units/workstreams.
- **Scale up** increases the depth, cross-system coupling, 3D/asset fidelity,
  spatial scale, and causal horizon of those units.

Both obey the same ratchet. Scale up is not permission to weaken the minimum
accepted-gameplay floor.
