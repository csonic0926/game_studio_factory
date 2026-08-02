---
name: init-game-ai-factory
description: Initialize, connect, or relink the current game repository to a cloned Game AI Factory checkout. Use when the user says to init/setup/install the factory for a game repo, when design/AI_FACTORY.local.md is missing, or before the first factory-backed production call. This is the per-game-repo initializer; machine-level skill installation is handled by setup.py install.
---

# Initialize a game repo for Game AI Factory

Connect one explicit/current game repo to the factory umbrella. The human does
not need to know `setup.py link` or provide internal department commands.

## Resolve

1. Resolve `<GAME_REPO>` from an explicit path, otherwise the current Git root.
   Never scan sibling repos. Reject the factory checkout itself or its child.
2. Resolve `<FACTORY_ROOT>` in this order:
   - an explicit factory path;
   - `<GAME_REPO>/design/AI_FACTORY.local.md` when already linked;
   - `.game_ai_factory_manifest.json` beside the installed skills directory;
   - the real path of this skill, walking upward to the directory containing
     both `setup.py` and `AI_CALLER_LANDING.md`.
3. If no valid checkout resolves, ask only for its path. Do not guess among
   neighboring repositories.

## Initialize

Run:

```bash
python3 <FACTORY_ROOT>/setup.py link --game-repo <GAME_REPO>
```

Then verify all four surfaces, not only command exit status:

- `design/AI_FACTORY.local.md` points to the resolved checkout;
- `.gitignore` contains `design/AI_FACTORY.local.md`;
- `AGENTS.md` contains exactly one managed Game AI Factory routing block;
- an existing `CLAUDE.md` was preserved, or an absent one received the
  `AGENTS.md` pointer.

The operation is idempotent. It installs routing, not design claims, gameplay
state, story state, code, or assets.

## Same-call handoff

If the user also requested product definition or a factory production task,
immediately invoke the owning `idea-factory`, `gameplay-factory`,
`game-story-factory`, Asset, or Sound workflow after the link. Do not make the
user issue a second prompt. Otherwise finish after verified umbrella linkage.
