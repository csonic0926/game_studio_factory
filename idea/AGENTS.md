# Idea Factory Guide and AI Entry

Idea Factory is the product-definition layer above Story, Gameplay, Asset, and
Sound. It is for blank projects, early repositories, and later projects whose
commercial/experiential direction is too weak or contradictory to constrain
production.

The user need not be a producer. The AI producer must complete missing product
reasoning, recommend one coherent direction, expose decisive tradeoffs in
ordinary language, and preserve the source and risk of every material choice.

## Entry and ownership

The installed `idea-factory` skill is the normal entry. Resolve one explicit
game repo or the current Git root; never scan siblings. If the repo is not
linked to the umbrella, invoke `init-game-ai-factory` first.

Run:

```bash
python3 <FACTORY_ROOT>/idea/idea.py start --game-repo <GAME_REPO>
```

All filled artifacts land in the game repo:

```text
design/product/
  PRODUCT_THESIS.md
  FACTORY_CONSTRAINTS.json
  idea/
    IDEA_FACTORY_REPO_PROBE.json
    PRODUCT_THESIS_INPUT.json
    IDEA_FACTORY_RESULT.json
```

The factory checkout owns only tools, schemas, templates, workflow contracts,
and tests.

## One AI producer, not a questionnaire tower

After `IDEA_FACTORY_DIALOGUE_REQUIRED`, read the bounded probe and only the
candidate sources needed to distinguish existing commitments from experiments.
Then one AI producer writes a **complete recommended product direction** before
asking the user anything.

The recommendation must connect:

```text
desired product/business outcome
  -> acceptable sacrifice
  -> intended player relationship
  -> why the player buys/returns/cares
  -> experience/emotion mechanism
  -> downstream factory constraints
  -> cheapest tests for uncertain beliefs
```

Ask no more than three high-leverage, plain-language questions in one round.
Do not ask the user to supply producer vocabulary, metrics, a GDD, or every
schema field. Offer one recommended answer with its consequence. A user may
edit, accept, or delegate the decision.

## Authority is provenance, not an AI prohibition

Every decision uses exactly one authority:

- `USER_FIXED` — the user stated or adopted it; preserve the exact quote.
- `REPO_COMMITMENT` — existing shipped/current product behavior genuinely
  commits the product; exact repo evidence is mandatory. Exploratory code is
  not automatically a commitment.
- `AI_RECOMMENDED` — a complete AI producer recommendation awaiting adoption
  or delegation. It may appear in the draft but cannot compile binding output.
- `AI_DELEGATED` — the user explicitly authorized AI judgment for this
  decision/scope. Preserve the authorization quote; this is valid authority.
- `VALIDATION_REQUIRED` — an uncertain player/market belief. It may define an
  experiment, never a binding downstream constraint.

Never hide AI completion as `USER_FIXED`, and never turn uncertainty into an
unlabeled product promise. Conversely, do not block merely because the user did
not possess producer expertise: recommend and explain the missing decisions.

## Compile and handoff

Write the structured handoff using:

- `schemas/product_thesis_input.schema.json`
- `templates/PRODUCT_THESIS_INPUT.json`

Then run:

```bash
python3 <FACTORY_ROOT>/idea/idea.py compile \
  --game-repo <GAME_REPO> \
  --input design/product/idea/PRODUCT_THESIS_INPUT.json

python3 <FACTORY_ROOT>/idea/idea.py check \
  --game-repo <GAME_REPO> \
  --input design/product/idea/PRODUCT_THESIS_INPUT.json
```

Routes:

- `PRODUCT_DIRECTION_REVIEW_REQUIRED` — present the whole recommendation, then
  ask only about listed material decisions. Do not discard the draft.
- `BLOCKED_BY_IDEA_MATERIAL` — provenance, causal reasoning, evidence, or
  structure is invalid; repair the exact gap.
- `BLOCKED_BY_EXISTING_PRODUCT_STATE` — canonical product files differ;
  preserve them and obtain an explicit revision path instead of overwriting.
- `IDEA_FACTORY_READY` — the product thesis and constraints are exact and
  ready for downstream factories.

After ready, return to the original request in the same call. If the user asked
to make Gameplay, invoke Gameplay Factory; do not stop merely to announce that
Idea Factory produced documents.

## Research and token discipline

- Probe mechanically before semantic study.
- Use one producer synthesis, not separate business/creative/reviewer agents.
- Current price/platform/market claims require bounded authoritative research;
  persist only the evidence that materially changes the recommendation.
- Do not perform a broad competitor report by default.
- Keep rejected alternatives concise but real enough to show the tradeoff.
- A checker proves ownership, provenance, binding, and exact handoff—not
  commercial success or artistic quality.

Full workflow: [`docs/PRODUCT_DEFINITION_WORKFLOW.md`](docs/PRODUCT_DEFINITION_WORKFLOW.md).
