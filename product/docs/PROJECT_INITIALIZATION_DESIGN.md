# Joint Idea / Product project initialization

Status: revised complete reusable-Factory design for two fresh independent
reviews, 2026-10-09. Implementation begins after both review this exact version.

## Request and boundaries

Initializing a game must establish both Idea and Product, so the intended
whole-offer value can guide development from the beginning. Product concerns the
coherent purchase for its intended player/price, including art, replay and
supporting functions where relevant. It is not feature count, hours, release QA,
or evidence that an unbuilt game already earns a price.

Idea retains exploration, post-frontier commission and canonical Thesis /
Constraints. Studio retains activation/archive and accepted-baseline lifecycle.
AI may propose a buyer, price scenario, value hypothesis and smallest useful test
within existing delegated scope. Unknowns are legal; initialization creates no
new USER gate, no commission, no migration and no commercial acceptance. Genuine
changes to commissioned price/audience/promise retain their existing authority.
Experimental staged-call files are not an adopted six-call runtime protocol.
Records contain inspectable claims, sources and decisions, never hidden reasoning.

## Entry and compatibility

Add `setup.py init --game-repo <GAME>` (also --project-root) as the canonical
initializer. Keep `setup.py link` routing-only, and install/sync unchanged. The
canonical and legacy initializer skills route new-game initialization to init;
explicit relink remains link. New whole-game entry documentation routes to init.
No global installation, consumer relinking, version change or main-branch update.

Init requires the exact existing Git root outside Factory (empty Git history is
allowed). Preflight confinement, selected workflow/checkout and pending migration
before writes. Hold the existing project lock, invoke the internal routing-link
writer (no nested lock), establish missing Idea work, and call Product's internal
idempotent seed writer. Public `product.py start` acquires the same lock itself.
`--dry-run` validates targets and reports intended writes without creating files.
All initialization-owned target paths are root-confined, reject symlink components
and invalid existing JSON; never overwrite author content or accepted history.

For Idea: if no exploration/probe/canonical material exists, use existing
`idea.start_idea_factory` to create its normal bounded repo probe. Existing Idea
work, including partial/commissioned/archive state, is preserved and linked.
Do not silently refresh its repo snapshot, reopen a direction, recompile or
recommission it on rerun. Report whether fresh work was created or existing work
was preserved and any partial-authority blocker. Existing-source presence is not
validation or acceptance. Continuing Idea follows its normal inspection/checks.

Idea must exclude the exact PRODUCT_VALUE_INTENT.json path from its generated-
planning snapshot/candidate set. Otherwise creating/authoring the Product seed
immediately makes Idea's repository-bound probe stale. This narrow exclusion does
not exclude arbitrary Product evidence or game implementation. Intent is never a
REPO_COMMITMENT merely because it is in the repository. Verify fresh exploration
can continue against the initial probe after intent creation and authoring; real
game-source edits must still stale the binding. Reject this exact artifact as
REPO_COMMITMENT evidence in Thesis provenance; other source meanings remain the
existing reviewer's semantic responsibility.

## Product intent artifact and lifecycle

Create only when absent `design/product_value/PRODUCT_VALUE_INTENT.json`, a
lightweight, game-owned `product_value_intent.v1` nonbinding planning source.
It contains:
- state OPEN or DRAFTED (drafting does not mean approval)
- exact source_refs for existing Idea probe/exploration/canonical files and
  authority register; they are context, not a new authority register
- offer and audience using Product's existing provenance/grounding shapes;
  seed UNKNOWN/null, never infer a price/market/commission from filesystem presence
- buying_reason and adequacy_case (nullable prose); value_hypotheses with IDs,
  statements and optional exact source refs; these remain hypotheses
- material_unknowns and next_move, with a useful default to read linked Idea
  sources and formulate the earliest whole-value test within current authority
- fixed current_build_assessment=NOT_ASSESSED, value_claim_eligible=false and
  authority_granted=false. These describe this planning artifact only, even if
  separate existing assessments later exist

The schema and runtime validator agree. Source refs are game-owned and confined;
all refs must resolve exactly. Existing files are validated/preserved, never
reset to the seed on resume. The initial empty draft is honest but not a completed
product-value analysis. The initializer skill must continue into Idea exploration
and Product intent authoring, preserve unknowns, and explain the next development
experiment/value target. Do not require completed gameplay or actual-play evidence
before initializing or conducting learning work.

Product inspect returns the intent's exact ref, nonbinding payload, live Idea
lifecycle status, current source-set comparison, blockers and next action. Missing,
changed or newly introduced Idea sources yield RECONCILIATION_REQUIRED; preserve
the old intent rather than silently rehashing it into current authority. A caller
reads changed sources, revises the hypotheses/unknowns and deliberately updates
the exact refs. A malformed existing intent blocks init without overwriting it.
No automatic qualitative claim is generated by the initializer. `product start`
allows an existing Idea-only game to opt into the additive artifact without a
workflow migration or requiring a new commission. Standalone legacy assessments
remain usable without an intent artifact.

## Downstream consumption and dependency validity

`product inspect`, generic `factory inspect`, and author context for Idea,
Studio, Gameplay and Product expose the nonbinding intent separately from the
canonical authority/constraints. Do not put it in authority_paths. Studio and
Idea entry guidance read it before material planning, use it to compare bounded
production options, and return real direction conflicts to Idea. Product entry
supports early intent as well as later experience-based assessment.

When a material design uses intent, bind its exact artifact as an explicit input;
subsequent edits then stale that design via existing dependency checks. The new
factory code/schema/workflow changes also participate in ordinary Factory
compatibility fingerprints. Explicitly include Product intent code/schema/workflow
in the affected Idea/Studio/Gameplay/Product dependency sets; their current
department discovery would otherwise omit Product for the first three. Also
wire both v2/v3 route renderers. Unversioned nonbinding exploration/intent may
use standalone Idea/Product commands; MIGRATION_REQUIRED does not authorize or
require migration merely to initialize. Never refresh old reviews/USER rulings or claim they
are newly valid. Historical v1/v2/v3 proof and project versions remain unchanged.

At development boundaries, update intent and observations proportionately; a
meaningful build alone introduces no whole-product review or commercial gate.
At the existing whole-product stopping/value-claim boundaries, perform the
applicable Product assessment/report/two-independent-review flow. Use the
exact-build current-offer gate before the existing paid-value claims. A failed
or inapplicable claim gate does not block authorized learning or production.
Intent can supply clearly labeled scenario hypotheses, not actual experience.
Existing gate rejects intent as result, no-build SUPPORTED, proposed/scenario
current-offer claims and absent experience. Preserve existing assessment/results;
no initialized/ready flag substitutes for commercial or USER acceptance.

## Verification and publication

Focused tests: fresh empty Git init creates routing+Idea probe+Product intent;
byte-identical rerun including authored intent; interrupt after one artifact then
resume; existing Idea-only and commissioned/partial/archive source preservation;
unknown unbuilt intent has no value PASS; source refs resolve and newly added /
changed sources are visibly stale; author context separates intent from authority;
malformed intent and symlinks fail without overwrite; dry-run writes nothing;
legacy link remains routing-only; no workflow migration; init artifact cannot
pass existing current-offer gate. Cover empty Git history and selected v3 routing.
Walk through an early scenario-priced experiment: intent may evolve and authorized
work continue without a commercial PASS or premature price-adoption request.

Run setup/Idea/Product/shared-core and relevant Studio regressions, whitespace
checks and any new tests. Record actual counts and blockers, not unrun CI or
semantic efficacy. Publish a meaningful adaptation commit over the verified
remote head using optimistic expected-head checking and exact tree verification.
Parent coordinates Mac pull and E&U adoption at its safe boundary; do not mutate
those consumers here. Preserve failed design review findings and independent
implementation verification; no unrelated workflow rewrite.
