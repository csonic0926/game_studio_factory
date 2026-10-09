---
name: idea-factory
description: Create or continue idea work with continuous primary-agent authorship, tool-owned checkpoints and independent boundary reviews. Resolve project state first; preserve existing CLI and historical formats.
---

# Idea Factory operation

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
3. For an explicitly versioned project run `factory.py context --game-repo $GAME_REPO --capability idea
   --task exploration` with the actual task kind and current task id when known.
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

## Pair exploration with nonbinding Product intent

New-game initialization uses `setup.py init`, which establishes missing Idea work
and `design/product_value/PRODUCT_VALUE_INTENT.json`. Read
`product/docs/PROJECT_INITIALIZATION_WORKFLOW.md` and run
`product/product.py inspect --game-repo <GAME_REPO>` before material planning.
If an existing Idea-only game is opting into early value work,
`product/product.py start` adds the intent without changing commission or requiring
migration.

Read the exact linked sources and intent as provisional context, separately from
canonical Thesis/Constraints and the live authority register. Explore the actual
question, then use `product-factory` to author a plausible whole-offer buying
reason, adequacy case, value hypotheses, material unknowns and smallest useful
test. An empty seed is not finished analysis. Unknown buyer/price and labeled
scenarios are legal; do not require a USER decision merely to complete fields.
When exploration adds/changes sources, deliberately reconcile the intent against
them rather than refreshing hashes without reconsidering its meaning.

Idea exploration may remain OPEN, no-fit or multiple live directions. A Product
Thesis requires explicit post-frontier commission; neither intent nor exploration
is downstream product authority. The intent is never `REPO_COMMITMENT` evidence.
When a material design actually uses it, bind its exact artifact as an explicit
input so later edits invalidate that dependency. Return material direction
conflicts to Idea/USER; do not use Product intent to narrow an adopted promise,
reopen an archived direction or manufacture experience/acceptance.

v1 reference (read only for historical interpretation or domain detail):
`$STUDIO_ROOT/idea/docs/ORCHESTRATION_V1.md`.

GPT-6 opt-in is explicit: `migrate --workflow gpt6 --check`, then authorized
`--apply --expected <digest>`. Keep global skills/stable consumers unchanged.
`context --method <id>` loads a specific optional technique; selected methods
belong in the sealed design. Read the selected checkout's skill, not a conflicting
installed copy. `--project-root` aliases `--game-repo`, including pure Story.
