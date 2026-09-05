---
name: game-story-factory
description: Create or continue story work with continuous primary-agent authorship, tool-owned checkpoints and independent boundary reviews. Resolve project state first; preserve existing CLI and historical formats.
---

# Story Factory operation

Resolve GAME_REPO from explicit path or current Git root. Resolve STUDIO_ROOT
from `design/STUDIO_FACTORY.local.md`, legacy `design/AI_FACTORY.local.md`,
installed manifest or this skill's real source path. If unlinked, invoke
`init-game-studio-factory`. Never hardcode a developer path or scan sibling games.

1. Run `python3 $STUDIO_ROOT/factory.py inspect --game-repo $GAME_REPO`.
2. MIGRATION_REQUIRED: preview `migrate --check --project-id <id>`; apply only
   an explicitly authorized migration with its exact source digest. No automatic
   approval/history conversion. Legacy CLI calls/parameters remain supported.
3. For v2 run `factory.py context --game-repo $GAME_REPO --capability story
   --task chapter` with the actual task kind and current task id when known.
4. Follow `$STUDIO_ROOT/factory_core/docs/WORKFLOW.md` and the returned capability
   rules. Continue in this primary agent; load task methods only as needed.
   Freeze one full design, run the two independent reviews on its exact hash,
   obtain required USER rulings, produce within scope, then exact-output
   evidence and specialist acceptance. Ordinary replies do not create reviews.
5. Checkpoint validated references, progress and unresolved questions. A resumed
   session rechecks the ledger; context views and technical success are not
   authority or whole-game delivery.

Story tasks: world, character, cast, chapter, branch, craft, beat-sheet (legacy beatsheet alias), delivery, twin, rules. Resolve PROJECT_PROFILE_CONTRACT and project adapter before writing. Keep full prose, voices, knowledge, branch memory, all shipped locales, sovereign rules and clean-room spoken-fluency/canon back-check. Latest landed output requires independent semantic QA.

v1 reference (read only for historical interpretation or domain detail):
`$STUDIO_ROOT/story/docs/ORCHESTRATION_V1.md`.
