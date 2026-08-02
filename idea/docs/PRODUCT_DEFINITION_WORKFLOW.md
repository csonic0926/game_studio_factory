# Idea Factory product-definition workflow

## Purpose

Turn a sparse user wish and/or early repository into explicit product authority
that can constrain Story, Gameplay, Asset, Sound, and ordinary production.
The workflow supplies producer-level reasoning without pretending AI-generated
judgment came from the user.

```text
idea.py start
  -> bounded repo probe
  -> one complete AI producer recommendation
  -> at most three high-leverage user choices, or explicit delegation
  -> PRODUCT_THESIS_INPUT.json
  -> idea.py compile
  -> PRODUCT_THESIS.md + FACTORY_CONSTRAINTS.json
  -> idea.py check
  -> IDEA_FACTORY_READY
```

## Step 1 — mechanical study boundary

`start` binds the Git revision, dirty paths, and dirty-content fingerprint. It
writes a bounded candidate list; candidate paths are not semantic authority.
The probe works for blank, early, and mature repositories.

Study only enough material to answer:

- what the user explicitly wants;
- which existing behaviors are true product commitments versus experiments;
- which high-level decisions are absent;
- which current market/platform facts would materially alter the direction.

## Step 2 — AI producer synthesis

One producer creates a whole recommendation. Do not split commercial strategy,
experience intent, retention, theme, and downstream consequences among several
workers: they form one causal thesis and must be reconciled together.

Required dimensions:

1. product promise;
2. audience relationship;
3. commercial shape;
4. intended thought/emotion/experience;
5. retention or replay reason;
6. differentiation;
7. scope shape and accepted sacrifices;
8. product-outcome → player-reason → experience-mechanism causal links;
9. cross-factory constraints;
10. cheap falsification tests for uncertain player/market beliefs.

The producer must provide a best recommendation, reasons, and concise rejected
alternatives before requesting user input. Questions are reserved for value
forks that materially reshape the product.

## Step 3 — adoption or delegation

Use the authority model in [`../AGENTS.md`](../AGENTS.md).

- A user accepting an AI recommendation converts it to `USER_FIXED`; preserve
  the acceptance quote and keep the AI rationale/alternatives.
- A user saying the AI should decide converts only the authorized scope to
  `AI_DELEGATED`; persist the exact authorization text and scoped decision ids.
- Without adoption/delegation, a material `AI_RECOMMENDED` decision produces
  `PRODUCT_DIRECTION_REVIEW_REQUIRED`, not a fake ready state.
- Uncertain response beliefs become validation hypotheses with a falsification
  signal and cheapest test. They do not need to block unrelated decisions.

## Step 4 — deterministic compile

`compile` verifies:

- game-repo ownership before any mkdir/write;
- exact repository snapshot and portable paths;
- exact repo evidence for `REPO_COMMITMENT`;
- exact user/delegation quotes where required;
- known, unique decision/source ids;
- binding authority for every thesis statement, causal link, non-goal, and
  factory constraint;
- at least one explicit sacrifice, one causal link, and one downstream
  constraint;
- no unresolved placeholders or hidden AI assumptions.

It renders every artifact in memory and preflights all existing canonical
outputs before the first write. Exact outputs are idempotent; differing outputs
block without overwrite.

The explicit `check` command enforces the creation-time repository snapshot.
After a successful checked handoff, later normal production commits do not make
the product thesis stale: `start` revalidates exact compiled artifacts,
authority, and current `REPO_COMMITMENT` evidence without requiring the whole
repo to remain at its old revision.

## Step 5 — downstream consumption

`PRODUCT_THESIS.md` is the human-readable product authority.
`FACTORY_CONSTRAINTS.json` is its machine-readable projection.

Downstream factories:

- obey constraints addressed to them or `all`;
- treat validation hypotheses as tests, not facts;
- return contradictions to Idea Factory instead of silently selecting another
  product direction;
- retain their own domain authority for concrete story/gameplay/asset/sound
  creation.

Idea Factory completion is not proof of market success, player retention,
artistic effect, or fun. It is a coherent, provenance-safe commission for
production and validation.
