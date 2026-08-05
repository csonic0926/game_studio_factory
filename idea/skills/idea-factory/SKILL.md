---
name: idea-factory
description: Openly explore or later commission the high-level product direction for a game with AI producer support. Use for blank ideas, early repositories, unresolved positioning, or user-supplied game references. Exploration may validly end with incompatibility, no useful synthesis, or several live directions; it must not force a Product Thesis. Only an explicitly commissioned emerged direction becomes downstream authority.
---

# Idea Factory

Act as an exploratory producer before acting as a commissioning producer. The
user may lack producer vocabulary, but that does not imply that a product
answer already exists.

## Start or reopen

1. Resolve the explicit/current game Git root. Never scan sibling repos.
2. Resolve `<FACTORY_ROOT>` from `design/STUDIO_FACTORY.local.md`, legacy
   `design/AI_FACTORY.local.md`, the installed skills manifest, or this skill's
   real source path. If unlinked, follow
   `init-game-studio-factory` (or legacy `init-game-ai-factory`) and continue
   in the same call.
3. Read `<FACTORY_ROOT>/idea/AGENTS.md`.
4. Run:

```bash
python3 <FACTORY_ROOT>/idea/idea.py start --game-repo <GAME_REPO>
```

When the user explicitly asks to reconsider or rerun an already-commissioned
direction, add `--reopen`. This starts non-binding exploration beside the old
authority; it does not overwrite it. Treat the old thesis as the direction
under reconsideration, not as repo evidence that the same answer must return.

## Open exploration

For `IDEA_EXPLORATION_REQUIRED`, use
`templates/IDEA_EXPLORATION.json`. Study the bounded probe and only material
sources. Record what has actually been learned, then run:

```bash
python3 <FACTORY_ROOT>/idea/idea.py explore --game-repo <GAME_REPO> \
  --input design/product/idea/IDEA_EXPLORATION.json
python3 <FACTORY_ROOT>/idea/idea.py check-exploration --game-repo <GAME_REPO> \
  --input design/product/idea/IDEA_EXPLORATION.json
```

Exploration has no mandatory product dimensions and no obligation to recommend
one direction. Valid states are:

- `IDEA_EXPLORATION_OPEN` — the question or ontology is still moving;
- `IDEA_REFERENCE_NO_FIT` — a supplied reference is contradictory or has no
  productive relationship; do not extract substitute features from it;
- `IDEA_DIRECTIONS_AVAILABLE` — one or more possibilities remain live;
- `IDEA_DIRECTION_EMERGED` — one coherent direction has emerged, but is still
  non-binding.

For every supplied reference, first determine whether any useful relationship
exists. Compatibility, anti-reference, contradiction, and no-fit are equally
legal. Never assume “use this reference” means “merge these games” or “find
something to copy.”

Surface only the current frontier in ordinary language. A negative finding can
be the whole useful result of a turn. Ask a question only when the user's
judgment can materially change the live space; do not ask to fill a schema.

## Explicit commission gate

“Help me decide,” “you decide,” and similar language may delegate exploratory
judgment. They do **not** require a product answer and do not by themselves
authorize compilation.

Only after the exploration frontier has been presented may an explicit user
adoption/freeze/commission authorize a Product Thesis. Then:

1. mark exactly one exploration direction `EMERGED`;
2. preserve the post-exploration authorization quote, selected direction id,
   exploration path, and exact SHA-256 in `PRODUCT_THESIS_INPUT.json` v2;
3. use normal decision authority (`USER_FIXED`, `REPO_COMMITMENT`,
   `AI_RECOMMENDED`, `AI_DELEGATED`, `VALIDATION_REQUIRED`);
4. run `compile` and `check` as directed by `idea/AGENTS.md`.

The compiler rejects no-fit/open/multi-direction exploration and rejects AI
delegation without a separate commission gate.

After `IDEA_FACTORY_READY`, return to the original requested production work.
Idea Factory itself does not author objectives, chapters, assets, SFX, or code.
When `design/product/PRODUCT_AUTHORITY_REGISTER.json` exists—or when Studio is
the caller—record the newly compiled authority before returning:

```bash
python3 <STUDIO_ROOT>/studio/product.py activate \
  --game-repo <GAME_REPO> \
  --authority-id <SELECTED_DIRECTION_ID> \
  --recorded-at <ISO_8601>
```

Never treat canonical Product Thesis file presence as active when the register
says `NO_ACTIVE_PRODUCT_AUTHORITY`.
