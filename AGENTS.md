# AGENTS — Game Studio Factory

This repository contains the autonomous **Game Studio Factory** operator plus
its specialist **Game AI Factories**.

```text
Game Studio Factory   = autonomous whole-game operator
Game AI Factories     = idea / gameplay / story / asset / sound capabilities
```

1. Read [`STUDIO_CALLER_LANDING.md`](STUDIO_CALLER_LANDING.md).
2. Open-ended whole-game intent routes to skill `game-studio-factory`, then
   [`studio/AGENTS.md`](studio/AGENTS.md).
3. A deliberately bounded specialist request routes directly to the owning
   factory and obeys its local `AGENTS.md` / landing / calling contract.
4. Studio and specialist outputs land in the target game repo, never here.
5. Reusable workflow/provider/stage/schema changes land in the owning folder
   through normal commits; preserve compatibility surfaces for linked repos.
6. Material Studio input/output transitions use the fresh-subagent semantic
   alignment gate in `studio/docs/SEMANTIC_ALIGNMENT_WORKFLOW.md`; ordinary
   user language must not require Factory-specific prompt boilerplate.

Specialist entry points:

- `idea/` → skill `idea-factory`, `idea/AGENTS.md`
- `gameplay/` → skill `gameplay-factory`, `gameplay/AGENTS.md`
- `story/` → skill `game-story-factory`, `story/AGENTS.md`
- `asset/` → `asset/AGENTS.md`, `asset/docs/AI_CALLER_LANDING.md`, `asset/itf.py`
- `sound/` → `sound/docs/AI_CALLER_LANDING.md`, `sound/sfx.py`

Studio hard boundary: a runnable interactive software demo is not whole-game
delivery. Only an Accepted Playable Baseline promoted through new-gameplay
acceptance plus predecessor regression may be presented as Studio delivery.
