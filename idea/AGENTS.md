# Idea Factory Guide and AI Entry

Idea Factory owns open product discovery and the later commissioning boundary
above Story, Gameplay, Asset, and Sound. It serves blank projects, early repos,
and mature projects whose product direction is being reconsidered.

Its first responsibility is not to produce an answer. It is to preserve the
real idea frontier without letting a required document, a supplied reference,
or an AI's urge to be helpful fabricate convergence.

## Entry, outputs, and causal boundary

Resolve one explicit/current game Git root; never scan siblings. If unlinked,
invoke `init-game-studio-factory` (or the legacy `init-game-ai-factory`) first. Run:

```bash
python3 <FACTORY_ROOT>/idea/idea.py start --game-repo <GAME_REPO>
```

Use `start --reopen` only when the user explicitly asks to reconsider existing
product authority. Reopening never deletes or overwrites that authority, and
the old thesis is not `REPO_COMMITMENT` evidence for reproducing itself.

Filled artifacts land in the game repo:

```text
design/product/
  PRODUCT_THESIS.md                 # only after commission
  FACTORY_CONSTRAINTS.json          # only after commission
  idea/
    IDEA_FACTORY_REPO_PROBE.json
    IDEA_EXPLORATION.json           # non-binding, AI-authored working state
    IDEA_EXPLORATION.md             # derived non-binding view
    PRODUCT_THESIS_INPUT.json       # only after commission
    IDEA_FACTORY_RESULT.json        # only after commission
```

Allowed causal chain:

```text
user/repo/reference evidence
  -> non-binding exploration
  -> one direction genuinely emerges
  -> user sees frontier and explicitly commissions it
  -> product decision authority
  -> Product Thesis / Factory Constraints
```

Forbidden arrows:

```text
reference -> mandatory borrowed feature
initial “help me decide” -> mandatory Product Thesis
AI delegation -> forced convergence
schema completeness -> evidence that an idea exists
```

## Phase A — open exploration

For `IDEA_EXPLORATION_REQUIRED`, write
`design/product/idea/IDEA_EXPLORATION.json` from the exploration schema/template
and run `explore`, then `check-exploration`.

The exploration record deliberately has no required commercial, retention,
emotion, differentiation, or scope answer. Those dimensions become useful only
when they help discriminate a live direction. Valid frontier states:

- `OPEN` → `IDEA_EXPLORATION_OPEN`;
- `REFERENCE_NO_FIT` → `IDEA_REFERENCE_NO_FIT`;
- `LIVE_DIRECTIONS` → `IDEA_DIRECTIONS_AVAILABLE`;
- `DIRECTION_EMERGED` → `IDEA_DIRECTION_EMERGED`.

All are successful exploration results; none is downstream product authority.
A turn may legitimately establish only that two concepts conflict, that a
reference is irrelevant, or that the original question is too narrow.

### Reference discipline

A reference is an object of inquiry, not an extraction quota. First classify
its relation as unresolved, compatible principle, contradiction,
anti-reference, or no productive relation. If the strongest result is no-fit,
record and present it. Do not continue by inventing analogues merely to satisfy
the workflow.

### Provenance without closure

Exploration anchors distinguish `USER`, `REPO`, `REFERENCE`, and
`AI_HYPOTHESIS`. Repo anchors require exact evidence; reference anchors retain
source URLs; hypotheses remain non-binding. Hidden `ai_assumptions` are
forbidden. Anchors and directions may both be empty when absence is truthful.

`IDEA_EXPLORATION.md` is a mutable derived view of the current non-binding
frontier. Updating it is allowed. Product authority remains fail-closed.

### Evidence and token discipline

- Read only candidate sources that can change the live frontier.
- Current platform, price, competitor, or market claims require bounded
  authoritative research; persist material source URLs in exploration.
- Do not manufacture a competitor survey when the reference relationship is
  already no-fit.
- Do not spend tokens completing product dimensions that are not yet live.
- One honest negative result is better than a long post-hoc synthesis.

## Phase B — explicit commission

Do not enter this phase merely because the user initially said “you decide.”
That authorizes producer judgment, including the judgment that no answer is
ready. Commission requires a post-frontier user instruction that explicitly
adopts, freezes, or asks to turn one emerged direction into product authority.

After commission, write `PRODUCT_THESIS_INPUT.json` v2 with:

- exact path and SHA-256 of `IDEA_EXPLORATION.json`;
- exactly one selected direction marked `EMERGED`;
- the exact commission authorization quote;
- explicit authority for every material product decision.

Then run:

```bash
python3 <FACTORY_ROOT>/idea/idea.py compile --game-repo <GAME_REPO> \
  --input design/product/idea/PRODUCT_THESIS_INPUT.json
python3 <FACTORY_ROOT>/idea/idea.py check --game-repo <GAME_REPO> \
  --input design/product/idea/PRODUCT_THESIS_INPUT.json
```

Only this phase requires a coherent product promise, audience relationship,
commercial shape, experience intent, retention/replay thesis, differentiation,
scope, causal links, sacrifices, validation hypotheses, and downstream
constraints.

Product decision authorities remain:

- `USER_FIXED` — exact user statement/adoption;
- `REPO_COMMITMENT` — exact current repo evidence, not exploratory code;
- `AI_RECOMMENDED` — non-binding and therefore review-required;
- `AI_DELEGATED` — scoped AI judgment explicitly authorized by the user;
- `VALIDATION_REQUIRED` — a testable uncertain belief, never a constraint.

AI delegation and commission are independent: delegation says who may choose;
commission says that exploration is mature enough to become authority.

## Compile/check guarantees

The compiler validates ownership before writes, exact repo/exploration hashes,
commission, source authority, causal structure, constraints, and absence of
hidden assumptions. It preflights all canonical product outputs before writing.
Exact outputs are idempotent; differing product authority is never overwritten.

The checker proves the handoff, not that the idea is commercially successful,
emotionally effective, fun, or the only possible answer.

After `IDEA_FACTORY_READY`, return to the caller's original production request.
Full workflow: [`docs/PRODUCT_DEFINITION_WORKFLOW.md`](docs/PRODUCT_DEFINITION_WORKFLOW.md).

If Studio owns the call or `design/product/PRODUCT_AUTHORITY_REGISTER.json`
exists, commission is not operationally active until Studio records it with
`studio/product.py activate`. Conversely, `NO_ACTIVE_PRODUCT_AUTHORITY`
overrides historical Product Thesis, code, and baseline presence. Whole-product
archive is owned by Studio's Product Authority lifecycle, not by ad hoc moves
inside Idea Factory.
