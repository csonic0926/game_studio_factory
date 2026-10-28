# AGENTS — Game Studio Factory

## Branch and consumer-isolation policy

USER authorized a separate GPT-6 adaptation branch on 2026-09-06. This replaces
the former main-only policy; do not delete the adaptation branch under that old
rule. On 2026-10-11 the USER renamed it from `gpt-6-adaptation` to `frontier`;
older documents that say `gpt-6-adaptation` mean `frontier`.

- `main` is the stable shared line for existing partners and installed skills.
  It runs the guided v2 workflow (more scaffolding, for less capable models).
- `frontier` is the opt-in line for frontier-capability models (explicit v3 /
  `WORKFLOW_GPT6.md`) and its Factory research, planning, implementation, and
  validation. Its worktree is `game_ai_factory_frontier`. Commit and push its
  work there; do not merge it into `main` without explicit USER approval.
- Keep the existing shared checkout on `main`. Develop the adaptation in its
  own Git worktree, not by switching the checkout targeted by installed skill
  symlinks or existing project pointers.
- Do not globally reinstall skills or relink unrelated projects to the
  experimental worktree. Experimental consumers must opt in explicitly.
- These are the only authorized branches. Do not create backup/safety branches
  or duplicate repositories/files as backups; normal Git history preserves
  committed work. A development worktree is an active workspace, not a backup.

This repository contains the autonomous **Game Studio Factory** operator plus
its specialist **Game AI Factories**.

```text
Game Studio Factory   = autonomous whole-game operator
Game AI Factories     = idea / product / gameplay / story / asset / sound capabilities
```

1. Read [`STUDIO_CALLER_LANDING.md`](STUDIO_CALLER_LANDING.md).
2. Open-ended whole-game intent routes to skill `game-studio-factory`, then
   [`studio/AGENTS.md`](studio/AGENTS.md).
3. A deliberately bounded specialist request routes directly to the owning
   factory and obeys its local `AGENTS.md` / landing / calling contract.
   Every proposed game-design idea still requires substantive `idea-factory`
   inquiry, including AI-generated mechanisms and later iterations. Follow
   [the per-idea workflow](idea/docs/PRODUCT_DEFINITION_WORKFLOW.md#every-idea-receives-substantive-inquiry);
   reading docs or reviewing the whole direction once does not satisfy it.
4. Studio and specialist outputs land in the target game repo, never here.
5. Reusable workflow/provider/stage/schema changes land in the owning folder
   through normal commits; preserve compatibility surfaces for linked repos.
6. Reusable Factory changes must preserve the explicit state partitions and
   versioned compatibility rules: v2 in `factory_core/docs/WORKFLOW.md`, explicit
   GPT-6/v3 in `factory_core/docs/WORKFLOW_GPT6.md`.
7. On an explicitly migrated v2 or v3 project, complete designs receive two fresh
   independent reviews (intent/experience and completeness/project), each
   different from the author and without first-pass peer conclusions. Runtime
   blind observation and informed comparison remain separately isolated.
   Unmigrated/historical v1 contracts remain readable; never silently convert
   their approvals, rejections or baselines.

Specialist entry points:

- `idea/` → skill `idea-factory`, `idea/AGENTS.md`; standalone thinking → skill `idea-thinking`
- `product/` → skill `product-factory`, `product/AGENTS.md`
- `gameplay/` → skill `gameplay-factory`, `gameplay/AGENTS.md`
- `ui/` → `ui/AGENTS.md` (UI Production Adapter; invoked by Gameplay/Studio)
- `story/` → skill `game-story-factory`, `story/AGENTS.md`
- `asset/` → `asset/AGENTS.md`, `asset/docs/AI_CALLER_LANDING.md`, `asset/itf.py`
- `sound/` → `sound/docs/AI_CALLER_LANDING.md`, `sound/sfx.py`; video scoring → `sound/docs/SCORING_WORKFLOW.md`, `sound/score.py`

Studio hard boundary: a runnable interactive software demo is not whole-game
delivery. Only an Accepted Playable Baseline promoted through new-gameplay
acceptance plus predecessor regression may be presented as Studio delivery.
