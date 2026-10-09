---
name: init-game-studio-factory
description: Initialize the current game repository with Game Studio Factory routing, Idea exploration and nonbinding Product value intent. Also handles explicit routing-only relinks. Preserves existing game work, instructions, authority and workflow version.
---

# Initialize Game Studio Factory

1. Resolve the exact existing target Git root from the explicit path or current
   repository. An empty Git history is valid; never scan sibling games.
2. Resolve the selected Factory checkout from an explicit path, this skill's real
   path, the `.game_studio_factory_manifest.json` installed-skills locator, legacy
   `.game_ai_factory_manifest.json`, or existing
   `design/STUDIO_FACTORY.local.md` / `design/AI_FACTORY.local.md`. Respect an
   explicitly selected workflow/checkout; do not relink unrelated consumers.
3. Read `<STUDIO_ROOT>/AGENTS.md` and
   `<STUDIO_ROOT>/product/docs/PROJECT_INITIALIZATION_WORKFLOW.md`. For game
   initialization run:

```bash
python3 <STUDIO_ROOT>/setup.py init --game-repo <GAME_REPO>
```

`--project-root` is an alias; `--dry-run` validates and previews without writing.
An explicit request only to link/relink still uses `setup.py link`, which changes
routing only and does not initialize Idea or Product. Install/sync is unchanged.

4. Verify the returned writes and preserved state:
   - `design/STUDIO_FACTORY.local.md` points to the selected checkout and is
     git-ignored; `AGENTS.md` has one managed routing block
   - existing `CLAUDE.md` and instructions are preserved, or a pointer to
     `AGENTS.md` was added when absent
   - a normal Idea repo probe was created only if no Idea work existed; existing
     exploration, partial/canonical material and lifecycle history are preserved
   - `design/product_value/PRODUCT_VALUE_INTENT.json` exists and Product inspection
     exposes its nonbinding state, exact sources, lifecycle and any blockers
   - rerunning preserves authored files; no backup artifacts, migration,
     commission, activation, archive or acceptance was created
5. Continue beyond the empty seed in the same call. Read the available Idea probe and actual
   relevant sources, follow `idea-factory` into bounded exploration with
   substantive inquiry and recorded reasons/open questions for every proposed
   idea, including AI-generated mechanisms. Follow the per-idea workflow in
   `idea/docs/PRODUCT_DEFINITION_WORKFLOW.md`; one whole-direction pass is not
   coverage, and the obligation continues for later iterations. Then use
   `product-factory` to author a provisional whole-offer buying reason, adequacy
   case, value hypotheses, material unknowns and smallest useful next test in the
   intent. Reconcile the exact Idea sources after exploration changes them. An
   open frontier, unknown buyer/price, nullable prose or an explicitly conditional
   scenario is legal. Do not demand a new USER choice merely to fill fields, and
   do not require a playable game before doing this learning work.
6. Explain the useful direction/frontier, value hypothesis and next development
   experiment, then continue the user's original Studio/specialist request within
   its existing authority. Seed creation alone is not completed value analysis.
   If existing work is partial or stale, preserve it and report the precise
   reconciliation/authority blocker rather than reopening or rehashing it.

Use `product/product.py inspect --game-repo <GAME_REPO>` to check the intent.
On an unversioned project, `factory.py inspect` may return `MIGRATION_REQUIRED`;
continue nonbinding work through standalone Idea/Product commands without forcing
migration. Initialization does not grant production authority. Idea retains
post-frontier commission and canonical Thesis/Constraints; Studio retains its
activation/archive and playable-baseline lifecycle. An intent used by a material
design must be bound as an exact explicit input, never as authority or experience.

GPT-6 activation is not ordinary initialization or relinking. Preview
`factory.py migrate --workflow gpt6 --project-root <root> --project-id <id> --check`
from the explicitly selected checkout, then apply only the authorized exact
digest. Recover interrupted migrations first. Never install experimental skills
globally or use the stable checkout to relink a v3 project; existing versions and
historical proofs retain their meaning.
