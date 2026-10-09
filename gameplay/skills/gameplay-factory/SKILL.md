---
name: gameplay-factory
description: Create or continue gameplay work with continuous primary-agent authorship, tool-owned checkpoints and independent boundary reviews. Resolve project state first; preserve existing CLI and historical formats.
---

# Gameplay Factory operation

Resolve GAME_REPO from explicit path or current Git root. Resolve STUDIO_ROOT
from `design/STUDIO_FACTORY.local.md`, legacy `design/AI_FACTORY.local.md`,
installed manifest or this skill's real source path. If unlinked, invoke
`init-game-studio-factory`. Never hardcode a developer path or scan sibling games.

1. Run `python3 $STUDIO_ROOT/factory.py inspect --game-repo $GAME_REPO`.
2. MIGRATION_REQUIRED does not block standalone nonbinding Idea inquiry. For
   shared versioned work, preview `migrate --check --project-id <id>`; apply only
   an explicitly authorized migration with its exact source digest. No automatic
   approval/history conversion. Legacy CLI calls/parameters remain supported.
3. For an explicitly versioned project run `factory.py context --game-repo $GAME_REPO --capability gameplay
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

Initialize missing adapters before production; repair an evidenced known gap before advancing unless USER defers it. Preserve adopted project gameplay standards, UI grammar and full causal cycles.

Before relying on each proposed game-design idea, invoke `idea-factory` under
`idea/docs/PRODUCT_DEFINITION_WORKFLOW.md#every-idea-receives-substantive-inquiry`.
AI-generated mechanisms and later iterations need identifiable inquiry, reasons,
judgments and open questions, including coupled whole-game consequences. Settled
direction, implemented code or a whole-direction review is not per-idea coverage.
Gameplay retains detailed design/production ownership; unchanged-design technical
repairs do not restart Idea, and nonbinding inquiry needs no new commission.

v1 reference (read only for historical interpretation or domain detail):
`$STUDIO_ROOT/gameplay/docs/ORCHESTRATION_V1.md`.

GPT-6 opt-in is explicit: `migrate --workflow gpt6 --check`, then authorized
`--apply --expected <digest>`. Keep global skills/stable consumers unchanged.
`context --method <id>` loads a specific optional technique; selected methods
belong in the sealed design. Read the selected checkout's skill, not a conflicting
installed copy. `--project-root` aliases `--game-repo`, including pure Story.
