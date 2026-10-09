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
2. MIGRATION_REQUIRED: preview `migrate --check --project-id <id>`; apply only
   an explicitly authorized migration with its exact source digest. No automatic
   approval/history conversion. Legacy CLI calls/parameters remain supported.
3. For an explicitly versioned project run `factory.py context --game-repo $GAME_REPO --capability studio
   --task objective` with the actual task kind and current task id when known.
4. Use the inspected version: v2 follows `$STUDIO_ROOT/factory_core/docs/WORKFLOW.md`;
   v3 follows `$STUDIO_ROOT/factory_core/docs/WORKFLOW_GPT6.md` and the returned
   capability rules. Never infer upgrade from the model name. Continue in this primary agent; load task methods only as needed.
   Freeze one full design, run the two independent reviews on its exact hash,
   repair FAILs continuously within authority, obtain required USER rulings,
   produce within scope, then exact-output
   evidence and specialist acceptance. Ordinary replies do not create reviews.
5. Checkpoint validated references, progress and unresolved questions. A resumed
   session rechecks the ledger; context views and technical success are not
   authority or whole-game delivery.

Whole-game delivery still requires new gameplay acceptance, exact-build USER playtest, predecessor regression and no blocking gap.

v1 reference (read only for historical interpretation or domain detail):
`$STUDIO_ROOT/studio/docs/ORCHESTRATION_V1.md`.

GPT-6 opt-in is explicit: `migrate --workflow gpt6 --check`, then authorized
`--apply --expected <digest>`. Keep global skills/stable consumers unchanged.
`context --method <id>` loads a specific optional technique; selected methods
belong in the sealed design. Read the selected checkout's skill, not a conflicting
installed copy. `--project-root` aliases `--game-repo`, including pure Story.

## Whole-product value supervision

Before claiming the integrated game justifies its price, invoke the peer
`product-factory` and read `product/docs/VALUE_ASSESSMENT_WORKFLOW.md`. Reconstruct
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
