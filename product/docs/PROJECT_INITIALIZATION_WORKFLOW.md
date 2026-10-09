# Joint Idea / Product project initialization

## Purpose and ownership

Initialize both the question of what this game should become and why its intended
whole offer could be worthwhile. Product value concerns the coherent purchase for
its buyer and offer: gameplay, art, replay, closure and surrounding affordances
matter when they carry that experience. It is not a feature count, hours formula,
release checklist or a claim that an unbuilt game already earns a price.

Idea owns open exploration, explicit post-frontier commission and canonical
`PRODUCT_THESIS.md` / `FACTORY_CONSTRAINTS.json`. Studio's `studio/product.py` owns
activation/archive; its existing admission process owns playable baselines.
Product intent is a nonbinding planning source alongside those authorities.
Initialization neither changes them nor adds a USER gate. AI may propose a buyer,
price scenario, value hypothesis and bounded test within existing delegated scope.
Real changes to commissioned audience, price or promise keep their normal owners.

## Initialize or resume

Resolve the exact existing game Git root outside the selected Factory checkout.
Empty Git history is allowed. Read the root and department instructions, preserve
the selected checkout/version and recover a pending migration before writing.

```sh
python3 <STUDIO_ROOT>/setup.py init --game-repo <GAME>
python3 <STUDIO_ROOT>/product/product.py inspect --game-repo <GAME>
```

`--project-root` aliases `--game-repo`. `setup.py init --dry-run` validates targets
and describes intended writes without creating files. Init coordinates its writes
under the project lock:

- establish the normal local pointer and managed routing block, preserving other
  instructions and ignoring the machine-specific pointer
- create Idea's normal bounded repo probe only when no Idea work exists
- create `design/product_value/PRODUCT_VALUE_INTENT.json` only when absent

Existing probes, exploration, partial/commissioned canonical files and archive
state are preserved. Presence is not validation or acceptance: use the owning
Idea/lifecycle checks before treating existing material as active authority. Init
reports preserved work and partial-authority blockers; it does not refresh a repo
snapshot, reopen a direction, compile a Thesis or recommission on a rerun.
Malformed existing intent blocks initialization without overwriting it. Target
paths are confined to the game root and reject symlink components. Preserve
conflicting content and inspect the reported blocker; do not delete it to get a
fresh-looking initialization.

For an already linked Idea-only game, the additive standalone entry is:

```sh
python3 <STUDIO_ROOT>/product/product.py start --game-repo <GAME>
```

This creates only the missing intent and preserves an existing authored intent.
It does not link, migrate or require a new commission. `setup.py link` remains
routing-only for deliberate link/relink requests. Install/sync behavior is unchanged.
Standalone historical assessments remain usable without an intent artifact.

## Continue into useful authorship

An honest empty seed is a starting point, not completed product-value work. The
initializer continues through `idea-factory` and `product-factory` in the same
call, at the depth the user's request and actual sources support:

1. Read the available bounded Idea probe, actual user request, game materials and
   current authority register if present. Candidate paths are study hints. Do not
   infer commitment from filesystem presence or treat an archived direction as
   active. Preserve existing work and use Idea's normal checks to continue it.
2. Explore the actual question through `idea-factory`, substantively questioning
   every proposed idea, including AI-generated mechanisms. Keep identifiable
   per-idea reasons, judgments and open questions, plus their coupled whole-game
   consequences; one whole-direction review is not coverage. Follow
   [the per-idea workflow](../../idea/docs/PRODUCT_DEFINITION_WORKFLOW.md#every-idea-receives-substantive-inquiry)
   for the supported record and later iterations. Record sourced anchors separately from AI
   hypotheses, the reference relationships, open/live/no-fit frontier and useful
   next move under `idea/docs/PRODUCT_DEFINITION_WORKFLOW.md`. No forced direction
   or complete commercial brief is needed. Idea's post-frontier commission remains
   separate; do not compile a Thesis merely to initialize.
3. Author the Product intent against those sources. Explain a plausible buying
   reason, what coherent benefit would make the whole offer sufficient despite
   its deliberate limits, and what experience would defeat that hypothesis. Label
   a proposed buyer or price scenario honestly; keep unknown fields and nullable
   prose when the sources cannot yet support more. Material unknowns name what
   could change the direction or next experiment, not every unmeasured fact.
4. Choose the smallest useful test of the weakest value hypothesis. Explain the
   concrete observation that would support or undermine it and the resulting next
   decision. This may guide an already authorized prototype, research or source
   inspection. It is not permission to change the game or adopt a price.
5. Inspect the resulting intent and reconcile changed/new Idea sources as below.
   Tell the user the useful frontier, conditional value target, material unknowns
   and next experiment, then continue authorized work. Do not report only file
   creation, a ready flag or a validator PASS.

An unversioned game's generic `factory.py inspect` may say `MIGRATION_REQUIRED`.
That means the shared versioned process is not active; it neither authorizes nor
requires migration for this nonbinding work. Continue with standalone Idea
`start` / `explore` / `check-exploration` and Product `start` / `inspect` as
appropriate. Do not use `--reopen` just to make an initialization rerun pass.
Versioned material designs still follow the selected v2/v3 process, its independent
complete-design reviews and existing USER boundary.

No completed gameplay, actual-play evidence, commercial PASS or new USER
price-adoption decision is required to initialize or investigate a scenario.
There is no fixed staged-call/six-call runtime protocol and no feature, hour,
reference or observation quota.

## Intent contract

The game-owned file uses `schema_version: product_value_intent.v1`:

- `state`: `OPEN` or `DRAFTED`; drafting does not mean approval or convergence
- `source_refs`: exact game-owned references to the current available Idea
  probe/exploration/canonical sources and authority register; these are context,
  not a second authority register
- `offer` and `audience`: Product's existing assessment provenance/grounding
  shapes; the initial seed is `UNKNOWN` with unknown price fields `null`
- `buying_reason` and `adequacy_case`: nullable prose for the intended whole value
- `value_hypotheses`: statements with unique `id`, `statement` and `source_refs`
  array (empty when no source is available); every entry remains a hypothesis
- `material_unknowns`: a list of decision-changing unknowns
- `next_move`: a prose string naming the useful next step, initially inviting the
  author to read linked Idea sources and formulate the earliest whole-value test
- `current_build_assessment: NOT_ASSESSED`, `value_claim_eligible: false` and
  `authority_granted: false`: fixed properties of this planning artifact, even if
  a separate later assessment exists

Source references resolve exact content in the game repository, with confined
paths and SHA-256 bindings. Offer/audience provenance must preserve fact,
adoption, proposal, hypothesis and unknown distinctions. An attractive scenario
never becomes `CURRENT_OFFER` or `ADOPTED_OFFER` by being written into this file.
Consult [the intent schema](../schemas/intent.schema.json) and Product inspection
when authoring; prose examples
are not permission to add unsupported keys or fabricate sources.

## Reconcile, do not silently refresh

`product.py inspect` exposes the exact intent reference and nonbinding payload,
live Idea lifecycle, current Idea source-set comparison, blockers and next action.
Missing, changed or newly introduced Idea sources produce
`RECONCILIATION_REQUIRED`, even when the old intent still looks plausible.

Read the changed sources and current lifecycle first. Deliberately revise the
hypotheses, unknowns and next move, then update the exact source references to
what was actually read and re-inspect. A reviewed hypothesis may remain unchanged,
but replacing hashes without reconsidering its meaning is not reconciliation.
Preserve the old content until the revision is deliberate; rerunning init/start
must not rehash it into fresh authority. Invalid JSON/shape needs repair without
resetting the author's intent. Broken or archived product authority stays with
Idea/Studio; an updated intent cannot repair or reactivate it.

Only the exact intent path is excluded from Idea's generated-planning repository
snapshot and candidate set, so seed creation and normal intent authoring do not
stale the initial probe. Actual game/source changes and other Product evidence
still participate in their normal bindings. The intent is never Thesis
`REPO_COMMITMENT` evidence, even if committed to Git.

## Use downstream and retain existing claim boundaries

Read intent before material Idea/Studio planning and compare bounded production
options against its provisional whole-value target. Generic inspection and
relevant author context expose it separately from canonical authority; never add
it to `authority_paths`. Return genuine direction conflicts to Idea and preserve
Studio's lifecycle. A material design that uses intent must bind its exact
artifact as an explicit input. Later intent edits then stale the dependent design
through normal checks; do not refresh old reviews, USER rulings or baselines.
Relevant Factory code/schema/workflow changes also retain their normal dependency
and compatibility effects across Idea, Studio, Gameplay and Product.

At development boundaries, update intent and observations proportionately. A
meaningful build alone does not require a whole-product report, independent
assessment reviews or a commercial claim gate. For example, a scenario-priced
prototype can reveal whether a central choice creates a worthwhile second lap;
record what that bounded experiment shows, revise the hypothesis and continue
already authorized work. The price remains a scenario and the whole-build value
remains unassessed unless separately assessed. Do not demand price adoption merely
because the current-offer gate cannot support a scenario.

At existing whole-product stopping claims (done, polished, final whole-game
handoff) and price-value judgments, follow
[VALUE_ASSESSMENT_WORKFLOW.md](VALUE_ASSESSMENT_WORKFLOW.md): encounter the actual
value-bearing experience, write the report/evidence index and obtain the two
fresh independent whole-assessment reviews. Before the existing paid-value claim,
use the exact-build current/adopted-offer gate. Intent supplies hypotheses, never
actual experience, an assessment result or a no-build `SUPPORTED` conclusion.
Negative/unknown or conditional assessments remain useful. A failed or inapplicable
claim gate does not block authorized learning/production. Actual-play, human
verdicts, gameplay acceptance and baseline admission retain their existing gates;
initialization never substitutes for any of them.
