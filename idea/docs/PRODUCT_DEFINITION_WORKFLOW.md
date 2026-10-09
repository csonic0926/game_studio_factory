# Idea Factory: open discovery and product commission

## Why there are two phases

Idea-level work begins before the answer, its dimensions, or even the right
question are stable. Requiring a complete product brief at entry makes an AI
optimize document completion: an incompatibility becomes a feature-extraction
exercise, a reference becomes an imitation quota, and plausible prose is
mistaken for discovery.

Idea Factory therefore separates non-binding exploration from binding product
commission.

```text
idea.py start [--reopen]
  -> bounded repo probe
  -> open exploration (zero, one, or several directions)
  -> no-fit / open frontier / live directions / emerged direction
  -> human sees the frontier
  -> explicit commission gate (optional, later)
  -> PRODUCT_THESIS_INPUT.json v2
  -> deterministic compile/check
  -> PRODUCT_THESIS.md + FACTORY_CONSTRAINTS.json
```

No-fit and non-convergence are valid work, not incomplete Product Theses.

## Every idea receives substantive inquiry

Use the `idea-factory` skill for every proposed game-design idea before relying
on it as a premise, not only for the initial pitch or a change of whole direction.
This includes AI-generated mechanisms, later iterations, and existing implemented
ideas whose rationale has never been examined. Identify each idea being relied on
so none disappears inside an umbrella direction or a feature list. Reading these
instructions, calling `inspect`, or obtaining a technical PASS is not the inquiry.

For each idea, reason concretely about the player situation: why the player would
care or choose, how the proposed mechanism produces its consequence, and what
real cost, sacrificed possibility or tension it creates. Consider alternatives
or counterexamples that could change the choice. Distinguish evidence from
inference and unresolved assumptions; implementation is evidence of existence,
not evidence that the premise works. Preserve the resulting judgment and reasons,
including why an idea stays open or is rejected.

These are connected questions, not equally weighted checklist scores. Scale the
inquiry to its consequence and uncertainty; a brief answer can suffice, but
“small idea” is no exemption for an unexamined load-bearing premise. No fixed idea
count, mandatory A/B test, separate accepted Thesis for each mechanism or forced
convergence applies. Reuse reasoning that still holds; materially changed ideas
or contrary evidence reopen the affected assumptions, not every settled decision.
Operational technical repairs do not restart Idea unless they change player-facing
design. Other factories still own their detailed design, production and evidence.

Also reason about the coupled whole game: one idea's benefit may consume another's
attention, scarcity, reward or room for choice. Fifteen individually plausible
ideas do not establish a coherent experience. Product Factory separately asks
whether that complete offer earns its price; it cannot substitute for Idea's
premise/mechanism inquiry, and Idea cannot substitute for Product assessment.

### Run it and keep a small durable record

Follow the skill's target/version resolution, read actual relevant sources and
perform the inquiry, then preserve per-idea conclusions, reasons and open
questions in the game repo. Several related ideas may share one session/record;
each must remain identifiable, with their interactions considered together.

- During mutable, uncommissioned exploration, use the existing
  `idea/templates/IDEA_EXPLORATION.json` shape and the Phase A2 `explore` /
  `check-exploration` commands below. Name ideas and their reasoning in
  `frontier_summary` or the relevant direction's `proposition`, `why_live` and
  `tensions`; retain uncertainties in `open_questions` and the useful next move.
  Mechanisms need not be invented as separate product directions. Put AI-proposed
  or inferred premises in `anchors` with `authority: AI_HYPOTHESIS`; preserve actual
  USER/source anchors with their correct authority. Never label self-authored
  reasoning `USER`, and keep the schema's reserved `ai_assumptions` array empty.
- For later inquiries, preserve any exploration/input already bound by commission,
  reviews or accepted history. Keep an additive, clearly nonbinding game-owned
  inquiry note (for example `design/product/idea/inquiries/<topic>.md`) rather than
  overwriting that proof. Use the Idea skill to do the same substantive work in
  this note. On v2/v3, bind it to an Idea `DRAFT` through the existing
  `factory.py context --capability idea --task exploration` and `checkpoint`
  workflow; a DRAFT needs no complete design or new commission. On an unversioned
  project, retain the note as standalone Idea work; do not claim the canonical
  `explore` CLI validated this separate note or invent an alternate input path.

The record should make visible what was actually considered and what would change
the judgment, not just “Idea checked” or a list of proposed features. `OPEN`,
`REFERENCE_NO_FIT`, live alternatives and rejected ideas remain useful outcomes.
No formal commission and `MIGRATION_REQUIRED` are not reasons to skip this work.
An actual authority/provenance blocker must be reported precisely; it is not
permission to replace history, silently migrate or commission a hypothesis.
`--reopen` is for an explicitly reopened exploration, not a routine per-idea or
initialization shortcut. Material changes to adopted product promises retain the
existing commission and Studio lifecycle boundaries.

Allowed: question a proposed unit-copying reward by examining what choice it
creates, what scarcity it removes, and when keeping a damaged unit might be the
better alternative; record the uncertainty and its interaction with progression.
Not allowed: “copying already works in code, so it is a good reward,” followed by
a whole-game pitch or Product assessment with no inquiry into that premise.

## Joint initialization and early value intent

`setup.py init` creates the routing, this department's missing repo probe, and
`design/product_value/PRODUCT_VALUE_INTENT.json`. Then continue the exploration
and author Product's provisional whole-offer value target together; see
`product/docs/PROJECT_INITIALIZATION_WORKFLOW.md`. The intent is nonbinding,
separate from the commission and not a REPO_COMMITMENT. Its exact path is
excluded from the generated-planning snapshot so authoring it does not invalidate
Idea's probe; actual game-source changes still do. Existing Idea work is preserved,
not silently reopened. Standalone exploration/intent needs no workflow migration.

Read Product intent as planning context, reconcile changed Idea source refs,
and bind it as an explicit input when a material design uses it. Product's
questions about whole-offer value can inform exploration without forcing a
direction, adopting a price, or treating an unbuilt game as assessed.

## Phase A1 — mechanical boundary

`start` binds Git revision, dirty paths, and dirty-content fingerprint and
writes a bounded list of candidate sources. Candidate paths are study hints,
not authority. `--reopen` refreshes the mechanical probe for an explicitly
reopened exploration without changing an existing Product Thesis.

## Phase A2 — open exploration record

The AI writes `IDEA_EXPLORATION.json` and uses:

```bash
python3 idea/idea.py explore --game-repo <GAME_REPO> \
  --input design/product/idea/IDEA_EXPLORATION.json
python3 idea/idea.py check-exploration --game-repo <GAME_REPO> \
  --input design/product/idea/IDEA_EXPLORATION.json
```

The record contains only:

- the actual user request and supplied references;
- sourced anchors or explicitly marked AI hypotheses;
- the relationship, if any, between each reference and the project;
- zero or more live/rejected/emerged directions;
- the current frontier, open questions, and highest-information next move.

It does **not** demand answers for business model, retention, emotion,
differentiation, scope, or downstream constraints. Those are probes the AI may
use when relevant, not slots it must fill.

### Frontier states

| State | Meaning | Product authority? |
| --- | --- | --- |
| `OPEN` | The question, ontology, or causal frame is still moving | No |
| `REFERENCE_NO_FIT` | A reference conflicts or has no productive relationship | No |
| `LIVE_DIRECTIONS` | Possibilities exist but premature selection would discard information | No |
| `DIRECTION_EMERGED` | One coherent direction now survives the exploration | Still no |

The user-facing turn presents this frontier rather than a compulsory pitch.

## Reference relation before reference extraction

For each user-supplied reference, ask first:

```text
Does a productive relationship exist?
```

Legal answers include compatible principle, anti-reference, contradiction,
no productive relationship, and unresolved. “These games should not be
combined” may be the complete useful finding. Once that finding is reached, the
workflow must not mine the reference for substitute features to justify its
continued existence.

## Phase B — commission gate

An initial instruction such as “help me decide” or “you decide” delegates
judgment but does not demand convergence. After seeing the exploration, the
user must explicitly adopt/freeze/commission one `EMERGED` direction before a
Product Thesis can be compiled.

`PRODUCT_THESIS_INPUT.json` v2 binds:

- exact exploration path and SHA-256;
- selected emerged direction id;
- exact post-exploration commission quote;
- repository snapshot and all product decision provenance.

The compiler rejects:

- open, no-fit, or multi-direction frontiers;
- a complete-looking Product Thesis with no exploration;
- AI delegation used as a substitute for commission;
- a stale or different exploration hash;
- non-binding hypotheses used as downstream authority.

Only after this gate does the familiar complete product commission become
appropriate: promise, audience relationship, commercial shape, experience,
retention/replay, differentiation, scope, causal links, sacrifices, validation
hypotheses, and factory constraints.

For Studio-managed repositories, successful compile/check is followed by
`studio/product.py activate`. Canonical file presence alone cannot override a
`NO_ACTIVE_PRODUCT_AUTHORITY` register left by an earlier direction archive.

## Downstream ownership

`PRODUCT_THESIS.md` and `FACTORY_CONSTRAINTS.json` remain canonical downstream
authority. Compiled Factory Constraints include every product non-goal so a
downstream product-fidelity review cannot silently ignore a boundary. A
non-goal may narrow mechanics or scope, but cannot erase a declared causal or
reward loop. In particular, gamification/positive-feedback intent remains a
cycle obligation even when the underlying service is not conventional
gameplay. `IDEA_EXPLORATION.md` never constrains Story, Gameplay, Asset, Sound,
or production. Downstream factories must ignore uncommissioned exploration and
return product-level contradictions to Idea Factory.

When `PRODUCT_AUTHORITY_REGISTER.json` exists, it owns whether those canonical
files are active. Whole-direction archiving is a Studio transition; it must not
be simulated by manually moving arbitrary design trees or rewriting decision
cards inside Idea Factory.

Compile/check proves ownership, provenance, commission, and exact handoff. It
does not prove that exploration was profound or the commissioned product will
succeed.
