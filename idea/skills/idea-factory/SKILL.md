---
name: idea-factory
description: Create or continue idea work with continuous primary-agent authorship, tool-owned checkpoints and independent boundary reviews. Resolve project state first; preserve existing CLI and historical formats.
---

# Idea Factory operation

Run substantive inquiry for every proposed game-design idea, including your own
mechanisms, unexamined implemented ideas and later iterations. Read and follow
`idea/docs/PRODUCT_DEFINITION_WORKFLOW.md#every-idea-receives-substantive-inquiry`:
actually question player reason/mechanism/consequence, costs, decision-changing
alternatives and known/inferred/unresolved premises; preserve each judgment and
open question in the supported exploration record or additive inquiry note.
Evaluate coupled whole-game consequences as well. A document read, whole-direction
review or Product assessment is not completion. This is nonbinding inquiry, not
a per-idea Thesis/commission gate or a restart for unchanged-design bug fixes.

Resolve GAME_REPO from explicit path or current Git root. Resolve STUDIO_ROOT
from `design/STUDIO_FACTORY.local.md`, legacy `design/AI_FACTORY.local.md`,
installed manifest or this skill's real source path. If unlinked, invoke
`init-game-studio-factory`. Never hardcode a developer path or scan sibling games.

Standalone thinking: when the caller needs only ideas/options for a bounded
task and product direction stays fixed (visual redesign, UI pass, naming,
mood), use skill `idea-thinking` (`idea/idea.py think`) instead of steps 1–5.
It needs no project state or migration and writes nothing. MIGRATION_REQUIRED
blocks product work, not this thinking; never drop the thinking because of it.

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

## You are the Director in autonomous modes

Check the authorship mode (`factory.py mode`). In AUTONOMOUS and CLOSED_BETA the USER
is not at every boundary, so you — this orchestrating session, not a subagent — hold
the seat the USER holds in COLLABORATIVE work: you judge whether the game is fun and
worth continuing, and you direct the Factory. You may be wrong; you may not be absent.
Follow `$STUDIO_ROOT/factory_core/docs/DIRECTOR_ROLE.md`:

- play before judging: drive the rules model, simulation or build yourself one decision
  at a time from the player's seat and record whether each choice mattered;
- write a Director note (`design/factory/director/<task_id>/`) at every major boundary
  and whenever measured evidence contradicts the design's intent; never answer "the USER
  will judge in the playtest";
- put direction above the pipeline: when the core is weak, stop polish, UI and evidence
  work on it and REDIRECT;
- in CLOSED_BETA you also hold the delegated design-approval seat (AI_DIRECTOR rulings),
  deliver a complete closed-beta build with your own verdict, the weaknesses you chose to
  ship and the questions only the USER can answer, or report a KILL instead;
- when the USER plays, record every difference from your notes as calibration.
