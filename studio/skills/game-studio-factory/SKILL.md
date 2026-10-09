---
name: game-studio-factory
description: Operate the whole game from an Accepted Playable Baseline with explicit acceptance and regression. Resolve project state first; preserve existing CLI and historical formats.
---

# Studio Factory operation

Resolve GAME_REPO from explicit path or current Git root. Resolve STUDIO_ROOT
from `design/STUDIO_FACTORY.local.md`, legacy `design/AI_FACTORY.local.md`,
installed manifest or this skill's real source path. If unlinked, invoke
`init-game-studio-factory`. Never hardcode a developer path or scan sibling games.

1. Run `python3 $STUDIO_ROOT/factory.py inspect --game-repo $GAME_REPO`.
2. MIGRATION_REQUIRED does not require migration for nonbinding initialization,
   Idea exploration or Product intent. Continue that work with standalone
   Idea/Product commands. If shared versioned work is requested, preview
   `migrate --check --project-id <id>` and apply only an explicitly authorized
   exact source digest. No automatic approval/history conversion; historical
   CLI calls/parameters retain their meaning.
3. For an explicitly versioned project run `factory.py context --game-repo $GAME_REPO --capability studio
   --task objective` with the actual task kind and current task id when known.
4. Use the inspected version: v2 follows `$STUDIO_ROOT/factory_core/docs/WORKFLOW.md`;
   v3 follows `$STUDIO_ROOT/factory_core/docs/WORKFLOW_GPT6.md` and the returned
   capability rules. Never infer upgrade from the model name. Continue in this primary agent; load task methods only as needed.
   For material designs, freeze one full design and run the two independent
   reviews on its exact hash,
   repair FAILs continuously within authority, obtain required USER rulings,
   produce within scope, then exact-output
   evidence and specialist acceptance. Ordinary replies do not create reviews.
5. Checkpoint validated references, progress and unresolved questions. A resumed
   session rechecks the ledger; context views and technical success are not
   authority or whole-game delivery.

Whole-game delivery still requires new gameplay acceptance, exact-build USER playtest, predecessor regression and no blocking gap.

Before relying on each proposed game-design idea, invoke `idea-factory` for
substantive inquiry, including AI-generated mechanisms and later iterations.
Follow `idea/docs/PRODUCT_DEFINITION_WORKFLOW.md#every-idea-receives-substantive-inquiry`:
retain per-idea reasons/judgments/unknowns and examine their coupled whole-game
consequences. One whole-direction review, existing code or Product assessment
cannot replace it. Missing commission or `MIGRATION_REQUIRED` does not excuse
skipping nonbinding inquiry; unchanged-design technical repairs do not restart it.

v1 reference (read only for historical interpretation or domain detail):
`$STUDIO_ROOT/studio/docs/ORCHESTRATION_V1.md`.

GPT-6 opt-in is explicit: `migrate --workflow gpt6 --check`, then authorized
`--apply --expected <digest>`. Keep global skills/stable consumers unchanged.
`context --method <id>` loads a specific optional technique; selected methods
belong in the sealed design. Read the selected checkout's skill, not a conflicting
installed copy. `--project-root` aliases `--game-repo`, including pure Story.

## Use early whole-value intent

New-game initialization uses `setup.py init` to establish routing, missing Idea
work and `design/product_value/PRODUCT_VALUE_INTENT.json`. Read
`product/docs/PROJECT_INITIALIZATION_WORKFLOW.md` and inspect Product intent before
material planning. The empty seed needs bounded Idea exploration and real
`product-factory` authorship of buying reason, adequacy case, value hypotheses,
material unknowns and next experiment; do not stop at file creation.

Compare already authorized production options against this provisional whole-offer
target, keeping hypotheses separate from current commission, constraints and live
activation/archive state. Unknowns and explicit price/buyer scenarios need no new
USER gate merely to investigate them. `RECONCILIATION_REQUIRED` means read the
changed/new/missing Idea sources and deliberately revise the intent, not silently
rehash it or revive old authority. Material direction conflicts return to Idea.
A material design that uses intent binds its exact artifact as an explicit input,
never an authority path; later intent edits stale that design's dependency.

Update intent and observations proportionately at development boundaries. A
meaningful build alone adds no whole-product assessment/review or paid-value gate.
A scenario experiment may guide the next authorized step without commercial PASS,
price adoption or completed gameplay. Actual-play acceptance and whole-product
stopping/value claims still follow their existing boundaries below.

## Whole-product value supervision

At a whole-product stopping boundary ("done", "polished", final product handoff,
or completion of the original whole-game request), invoke the peer
`product-factory` even if the statement does not explicitly mention price.
Also invoke it before claiming the integrated game justifies its price. Read `product/docs/VALUE_ASSESSMENT_WORKFLOW.md`. Reconstruct
the current/adopted offer and buyer; encounter the value-bearing experience,
seek decisive contrary evidence, and use the weakest causal value link to choose
the next authorized repair or justified stopping point. Art, replay, closure and
surrounding affordances contribute to one purchase; no additive score or default
content expansion applies. Refresh external price sources before a new claim.

Consume the reviewed exact-build result with `studio/product.py check-value
--game-repo <GAME> --result <PRODUCT_RESULT> --build <BUILD_OR_MANIFEST>`. Preserve
its exact offer/audience/provenance and conditionality in the user-facing answer.
A proposed/scenario price is not the current/adopted offer. Negative/unknown
assessment is useful work, not authority to change product direction. Return
material promise/price/audience changes to Idea/USER and bounded execution to its
owner. Product does not alter Studio activation/archive, gameplay/human verdicts
or baseline admission. A playable baseline alone never proves whole-product value.
Routine prototype, accepted-slice and checkpoint claims keep their explicitly
bounded scope and do not require a whole-product review. Do not review every edit
or block learning work; the Product gate guards the whole-product stopping claim.
