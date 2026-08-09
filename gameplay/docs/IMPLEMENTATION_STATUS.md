# Gameplay Factory implementation status

This status is deliberately narrower than the umbrella proposal's completion
criteria. Contracts and synthetic tool tests are not a production pilot.

## Implemented in factory core

- installed `gameplay-factory` user entry that auto-links the current game
  repo, runs initialization before routing, and continues ordinary requests
  through production; machine install and per-repo linking are exposed by the
  Studio root's `setup.py install` and canonical
  `init-game-studio-factory` skill (legacy `init-game-ai-factory` retained);
- single `init.py start` entry that routes total-new, existing-project, and
  already-initialized repos without exposing numbered lifecycle cases;
- Gameplay Factory existing-project initialization: explicit non-blank
  Git-repo ownership gate,
  optional umbrella routing link, bounded non-semantic file/locale/test-source
  probe, and exact Git revision plus dirty-path/content binding;
- dependency-free `init.py start|probe-existing|compile|check` workflow driven by one
  structured evidence-focused investigation: it validates portable exact
  evidence, live progression authority, objective locale plus runtime
  selection/completion, implemented actions/rewards, production mappings, and
  honest observation capability before reusing the production material gate;
- initialization schemas/template and preflighted compiler for only-missing
  `PROJECT_GAMEPLAY_PROFILE.md`, Production/Observation Adapters,
  `GAMEPLAY_DESIGN_MODEL.json`, empty design-state ledgers, initial objective
  frontier, and SHA-bound init result; differing existing factory state,
  unresolved material gaps, AI assumptions, and stale repo/input/artifact state
  fail closed before mutation;
- objective-gameplay front end: explicit blank/foreign/factory-native
  case boundary, primary-progression-first object model, script-first Step 1,
  compact-card Step 2 plus exact-refinement Step 2.5 contract;
- dependency-free `prepare.py context` ownership guard and material compiler:
  stable project model + small objective frontier merge, exact repo evidence
  tokens, locale CSV lookup, runtime objective selection /
  completion proof, action/reward validation, compact context rendering, and
  the distinct `READY_FOR_HOW_DESIGN`, `READY_FOR_NEW_GAMEPLAY_DESIGN`, and
  `BLOCKED_BY_MATERIAL` states;
- blank `GAMEPLAY_DESIGN_MODEL.json`, `NEXT_GAMEPLAY_UNIT_INPUT.json`,
  compact decision-card, dual conformance-review, `OBJECTIVE_GAMEPLAY.md`, and
  exact `GAMEPLAY_DESIGN_VERDICT.json` v2 templates
  plus machine-readable schemas and
  adversarial preparation tests;
- model-independent objective production planning: the factory user may choose a
  Plan Mode or ordinary model, while both persist the same SHA-bound
  `PRODUCTION_PLAN_MANIFEST.json` plus `N` Markdown change-unit plans;
- dependency-free `plan.py validate` checks exact Factory revision, compact
  human card ruling, dual inverse conformance, objective-row coverage, source hash
  freshness, required plan sections/metadata, portable ownership,
  existing repo evidence, plan dependency cycles, ready/blocked consistency,
  and exclusive planned-path ownership;
- production-plan schemas/templates and adversarial tests, plus one real IMT
  sample compiling the nine-row objective into two non-overlapping plans;
- automatic Step 4 caller handoff: a normal high-level gameplay-production
  request treats `READY_FOR_EXECUTION` as intermediate, requires the original
  caller/orchestrator to execute the persisted plans without a second user
  prompt, and reserves plan-only stopping for explicit requests;
- canonical `gameplay/AGENTS.md` entry/router for the two production operations:
  progression production when no concrete unresolved gap is active, and
  anchored gameplay-gap repair when an existing objective contains an
  evidenced player-visible causal break;
- compact repair front end: exact base-objective id/path/SHA/row binding,
  exact gap evidence, affected stable action/reward selection, separated
  existing-design/user-ruling/omitted/conflicting authority states, and the
  distinct `READY_FOR_DIRECT_REPAIR_PLAN`, `READY_FOR_REPAIR_DESIGN`, and
  `BLOCKED_BY_REPAIR_MATERIAL` routes;
- dependency-free `repair.py context` ownership/material gate plus
  `GAMEPLAY_GAP_INPUT.json`, `GAMEPLAY_REPAIR.md`, and schemas/templates;
  explicit existing authority or a persisted user ruling skips creative
  repair authoring, while an omission gets one bounded amendment without
  rewriting `OBJECTIVE_GAMEPLAY.md`;
- model-independent repair planning through SHA-bound
  `REPAIR_PLAN_MANIFEST.json` and bounded Markdown repair plans;
  `repair_plan.py validate` checks exact base and repair-source freshness,
  every repair-row disposition, dependencies, portable repo paths,
  ready/blocked consistency, and exclusive planned-path ownership;
- repair Step 4 caller handoff: `READY_FOR_EXECUTION` triggers ordinary
  implementation automatically, while standard tests remain separate from
  user/fresh-reviewer experiential gap closure;
- just-in-time UI Production Adapter workflow: dependency-free `ui.py
  start|probe|compile|refresh|check` creates a bounded non-semantic candidate probe,
  binds exact Git revision plus dirty bytes, validates one investigator's
  exact repo/user/factory authority, and creates only missing game-owned
  JSON/Markdown UI construction authority after all-target preflight;
- reusable UI evidence fingerprints: unrelated repo changes do not invalidate
  the adapter, while a changed cited scene/state/exemplar source blocks plan
  binding until an explicit `ui.py refresh`; refresh verifies the entire old
  checked generation before replacing it and creates no backup artifacts;
- explicit UI realization model covering layout structure, state ownership and
  refresh flow, scene/lifecycle integration, input/modal/layers, responsive
  composition, localization fit, accepted visual grammar, baseline/user-ruling
  exemplar provenance, and split structural/visual scenarios across every
  declared viewport/localization profile;
- UI adapter v2 proves accepted-baseline exemplar bytes at the baseline game
  revision, blocks self-canonicalizing current targets, defaults to preserving
  existing visual grammar, and requires mechanical visual comparisons (Godot
  Theme/StyleBox identity or properties) before supplemental screenshots;
- production manifest v4 / repair manifest v3 UI binding: every UI-changing
  plan inventories the full new/modified/reopened-batch style blast radius,
  maps targets to accepted exemplars and visual rules, selects separate
  structural/visual scenarios, and repeats the exact contract in Markdown;

- quant-first demand ordering: Span Quant Sheet template/module (span
  boundaries -> cadence contract -> implementation-blind playable-content
  inventory -> derived floors), fresh quant review gate, and
  Beat-Sheet-satisfies-quant design review checks;
- choice-cadence demand semantics: the meaningful-choice unit (information
  -> guess -> commitment -> consequence -> later-emotion influence) with
  three-question qualification, the factory canonical beat (3–5 s arrivals,
  5000 ms max gap, explicit-USER-override only), generator/one-shot
  inventory with a cadence sustainability walk, the chain rule
  (consequences deliver the next choice's hints), desire-line emotional
  signs, and the search-vs-commute traversal distinction — enforced at
  paper gates (quant review + design review);
- v1 Gameplay Experience Beat Sheet authority/authoring/review contract;
- exact version/checksum lineage into walkthroughs, packets, observation
  plans, runtime evidence, and acceptance;
- revised walkthrough and four-layer packet contracts/templates;
- separate Project Gameplay, Production, and Observation Adapter contracts;
- canonical raw evidence, observation-mapping, and kernel-selector schemas;
- dependency-free reference reader for validation, normalization, timeline
  reconstruction/latency, runtime blind projection, evidence viewing, and
  acceptance-comparison input;
- quantitative exact-span gate with runtime-owned run/session selection,
  non-gameplay-only chain rejection, non-inflating content counts, and
  presentation-adjusted effective control measurement;
- optional fail-closed `ordered_sequences` acceptance matching for distinct
  same-run intermediate events between positive phase boundaries;
- fail-closed integrity and contamination checks;
- manual fresh design/realization/packet/landing/runtime acceptance review
  templates;
- unit tests using synthetic evidence.

## Not yet proven or complete

- the compact objective Step 1/Step 2/Step 3 format now has one real-project
  design and planning sample, but its planning token cost and implementation
  usefulness are not proven until production executes the persisted plans;
- the repair workflow has synthetic adversarial contract tests but has
  not yet closed a real game-owned gap end to end; in particular, the IMT
  reusable-campfire break motivated the workflow but no IMT repair artifact or
  runtime fix is created by this factory-side implementation;
- open product discovery and explicit product commission are now implemented
  by the umbrella Idea Factory;
  new-project initial progression/action/reward bootstrap remains unimplemented
  and intentionally separate from both product definition and existing-runtime
  reconstruction;
- existing-project initialization has synthetic adversarial coverage but has
  not yet been piloted end to end on a real foreign game repo; its semantic
  reconstruction quality and token cost therefore remain unmeasured;
- the UI Production Adapter v2 hardening is derived from the auto-battler
  postmortem and has synthetic adversarial coverage; it has not yet been run as
  a complete adapter migration plus production-plan cycle inside that game repo;

- no real game-owned Beat Sheet -> implementation -> actual build evidence
  pilot has been supplied or run from this factory task;
- no real project Observation Adapter normalizer is validated;
- no `LIVE_BLIND_RUN` plus `CONTROLLED_BRANCH_PROBE` evidence set exists here;
- no deliberate implementation/reception mismatch has yet demonstrated correct
  failure routing;
- no second project/gameplay shape has demonstrated portability;
- no human playtest has accepted enjoyment/commercial value;
- no real span has driven the quant-first tower (quant sheet -> Beat Sheet ->
  implementation) end to end, so sufficiency-assessment quality is untuned;
  calibration levers (instruction tuning; an optional independent code-view
  subagent producing a supply-side gameplay report) are deferred to the tune
  phase;
- runtime cadence measurement does not exist: `reader.py` and the budget
  schema still measure the duration/control/gap ontology, and choice-arrival
  events are not yet an Observation Adapter concept. The quant cadence is
  enforced on paper only; the budget JSON's gap caps act as crude
  arrival-gap proxies until the tune phase defines arrival measurement;
- the creative step machine/`.5` worker automation remains intentionally
  deferred until pilot formats stabilize.

Therefore the factory request remains **in progress**. The reference reader is
an MVP implementation candidate, not evidence that Phase 1 or cross-project
closure has passed.
