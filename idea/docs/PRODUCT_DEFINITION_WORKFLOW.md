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
