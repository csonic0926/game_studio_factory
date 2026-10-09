---
name: init-game-ai-factory
description: Compatibility alias for joint Idea/Product initialization with the renamed Game Studio Factory. Use for existing prompts or repos that still say Game AI Factory or design/AI_FACTORY.local.md; new calls should prefer init-game-studio-factory.
---

# Initialize Game Studio Factory — legacy entry name

`init-game-ai-factory` is retained so existing game repos and user prompts do
not break. The product is now **Game Studio Factory**; Idea, Product, Gameplay,
Story, Asset and Sound are its specialist **Game AI Factories**.

Resolve `<STUDIO_ROOT>` from an explicit path, either local pointer, either
installed-skills manifest, or this skill's real source path. Read and follow
`<STUDIO_ROOT>/skills/init-game-studio-factory/SKILL.md` in full. This alias has the
same initialization, continuation and authority boundaries as the canonical skill.

Accept `design/STUDIO_FACTORY.local.md` first, then the legacy
`design/AI_FACTORY.local.md` fallback. For initialization run:

```bash
python3 <STUDIO_ROOT>/setup.py init --game-repo <GAME_REPO>
```

This establishes routing, missing Idea work and nonbinding Product value intent.
Continue into bounded Idea exploration and real intent/hypothesis authoring;
creating the empty seed is not the completed work. Preserve unknowns and explicit
scenarios, existing commission/lifecycle and workflow version. Unversioned
standalone Idea/Product work requires no migration or extra USER approval gate.

Only an explicit routing-only link/relink request uses `setup.py link --game-repo
<GAME_REPO>`. Neither command supplies product/gameplay acceptance or authorizes
new production. Verify preserved instructions, exact selected pointer, one managed
routing block, idempotence and no backup artifacts as the canonical skill directs.
