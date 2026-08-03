---
name: init-game-studio-factory
description: Connect or relink the current game repository to a cloned Game Studio Factory checkout. Use before the first Studio or specialist Game AI Factory call, or when design/STUDIO_FACTORY.local.md is missing. Preserves existing repo instructions and supports legacy Game AI Factory links.
---

# Initialize Game Studio Factory

1. Resolve the target game repo from the explicit path or current Git root.
2. Resolve the cloned Studio checkout from this skill's real path, the
   `.game_studio_factory_manifest.json` installed-skills locator, legacy
   `.game_ai_factory_manifest.json`, or existing
   `design/STUDIO_FACTORY.local.md` / `design/AI_FACTORY.local.md`.
3. Read `<STUDIO_ROOT>/AGENTS.md` and run:

```bash
python3 <STUDIO_ROOT>/setup.py link --game-repo <GAME_REPO>
```

4. Verify:

- `design/STUDIO_FACTORY.local.md` points to the checkout and is git-ignored;
- `AGENTS.md` contains exactly one managed Game Studio Factory routing block;
- an existing `CLAUDE.md` was preserved, or a pointer to `AGENTS.md` was added;
- re-running the command is idempotent;
- no backup branch/file/directory was created.

Continue the user's original Studio/specialist request in the same call. Linkage
supplies routing only; it is not product, gameplay, or acceptance authority.
