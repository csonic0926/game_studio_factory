# Product Factory caller landing

Use `product-factory` from project initialization to form a provisional whole-offer
value target and choose the smallest useful experiment. Also use it when an
integrated game is called done/polished or worth its price, or when choosing the
next improvement requires judging the whole purchase experience.

For early intent, read [PROJECT_INITIALIZATION_WORKFLOW.md](PROJECT_INITIALIZATION_WORKFLOW.md).
For actual value judgment, read [VALUE_ASSESSMENT_WORKFLOW.md](VALUE_ASSESSMENT_WORKFLOW.md)
and encounter the exact value-bearing artifact. Source-code correctness,
screenshot presence and planning intent cannot substitute for experience.

Missing direction/contradictory product authority goes to Idea. A known bounded
implementation problem goes to its owner. Studio coordinates the result and owns
activation/archive and playable-baseline lifecycle. Unknown context and explicit
price scenarios are useful; do not demand a new USER choice merely to fill a
schema. Intent is nonbinding and cannot commission or accept a game.

## Initialize and author intent

```sh
python3 setup.py init --game-repo <GAME>
python3 product/product.py inspect --game-repo <GAME>
```

Canonical initialization establishes routing, missing Idea work and the additive
`design/product_value/PRODUCT_VALUE_INTENT.json` seed. Continue into bounded Idea
exploration and actual buying-reason, adequacy-case, hypothesis and next-test
authorship. On an existing Idea-only game, `product/product.py start --game-repo
<GAME>` adds only the intent. `setup.py link` remains routing-only. Neither entry
requires migration, a playable build, commercial PASS or a new commission.

Inspection reports the exact nonbinding intent, live Idea lifecycle, current
source-set comparison and blockers. Reconcile missing/changed/new sources by
reading them and deliberately revising the intent, not by silently refreshing
hashes. When a material design uses it, bind its exact artifact as an explicit
input. It is never canonical authority, Thesis REPO_COMMITMENT or actual-play
evidence. Initialization does not install an experimental staged-call protocol.

## Assess and check a claim

Standalone commands (game-owned paths are relative to the explicit game root):

```sh
python3 product/product.py prepare --game-repo <GAME> --input design/product_value/<ID>/PRODUCT_VALUE_ASSESSMENT.json
python3 product/product.py record --game-repo <GAME> --input design/product_value/<ID>/PRODUCT_VALUE_ASSESSMENT.json --review design/product_value/<ID>/reviews/intent.json --review design/product_value/<ID>/reviews/completeness.json
python3 product/product.py check --game-repo <GAME> --result design/product_value/<ID>/PRODUCT_VALUE_RESULT.json
python3 studio/product.py check-value --game-repo <GAME> --result design/product_value/<ID>/PRODUCT_VALUE_RESULT.json --build <EXACT_BUILD_OR_MANIFEST>
```

`prepare` is read-only and returns the exact review package. `record` publishes
one immutable result after two independent AGREE reviews; that may be a negative
assessment. `check` proves recorded-source consistency. Only `gate`/`check-value`
checks eligibility for the requested exact build and current/adopted offer.
Refresh material external offer facts before a new claim. Hashes prove unchanged
captures, not that a storefront still has that price. Preserve source dates.

Whole-product stopping/value-claim boundaries keep the applicable actual-experience
assessment/report/two-review flow and exact-build paid-value gate. A meaningful
build alone adds no commercial gate; learning and authorized production can
continue without a Product PASS. Product can honestly conclude VALUE_GAP,
EVIDENCE_INSUFFICIENT or CONTEXT_UNRESOLVED, and a scenario judgment retains its
conditionality. Legacy standalone assessments need no intent or migration.

Product commands do not migrate, commission, activate, archive, change game
content, relink skills, publish a price, grant production permission or accept a
game. The initializer changes routing and missing planning artifacts only.
