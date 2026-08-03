---
name: init-game-ai-factory
description: Compatibility alias for initializing a game repo with the renamed Game Studio Factory. Use for existing prompts or repos that still say Game AI Factory or design/AI_FACTORY.local.md; new calls should prefer init-game-studio-factory.
---

# Initialize Game Studio Factory — legacy entry name

`init-game-ai-factory` is retained so existing game repos and user prompts do
not break. The product is now **Game Studio Factory**; the specialist Idea,
Gameplay, Story, Asset, and Sound components are its **Game AI Factories**.

Resolve `<STUDIO_ROOT>` from an explicit path, either local pointer, either
installed-skills manifest, or this skill's real source path. Then read and
follow `<STUDIO_ROOT>/skills/init-game-studio-factory/SKILL.md` (also installed
under the canonical `init-game-studio-factory` name).

Accept both pointer surfaces:

1. `design/STUDIO_FACTORY.local.md` (canonical), then
2. `design/AI_FACTORY.local.md` (legacy fallback).

Run:

```bash
python3 <STUDIO_ROOT>/setup.py link --game-repo <GAME_REPO>
```

Verify the new Studio pointer, one managed Studio routing block, preserved
existing instructions, idempotence, and no backup artifacts. Continue the
user's original request; linking is routing only, not product/gameplay
acceptance authority.
