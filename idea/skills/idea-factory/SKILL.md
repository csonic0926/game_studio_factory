---
name: idea-factory
description: Define or repair the high-level product direction for a game using AI producer support. Use for blank ideas, early repositories, or projects missing coherent commercial positioning, audience relationship, monetization/price shape, retention or replay thesis, intended thought/emotion, differentiation, scope, or cross-factory constraints. Produces one complete recommendation before asking a few high-leverage questions; supports explicit AI-delegated decisions and then hands ready authority to Gameplay, Story, Asset, and Sound.
---

# Idea Factory

Act as an AI producer, not a form filler. The user may supply only a genre,
feeling, commercial wish, partial intuition, or early repo. Complete the missing
product reasoning and make one coherent recommendation.

## Start

1. Resolve the explicit/current game Git root. Never scan sibling repos.
2. Resolve `<FACTORY_ROOT>` from `design/AI_FACTORY.local.md`, the installed
   skills manifest, or this skill's real source path. If unlinked, follow
   `init-game-ai-factory` and continue in the same call.
3. Read `<FACTORY_ROOT>/idea/AGENTS.md`; it is the full authority/routing
   contract.
4. Run:

```bash
python3 <FACTORY_ROOT>/idea/idea.py start --game-repo <GAME_REPO>
```

## Producer interaction

For `IDEA_FACTORY_DIALOGUE_REQUIRED`, read the bounded probe and only necessary
candidate sources. Write one complete `PRODUCT_THESIS_INPUT.json` recommendation
covering business outcome, accepted sacrifice, audience relationship, why the
player buys/returns/cares, intended experience/emotion, differentiation, scope,
causal mechanisms, downstream constraints, and validation hypotheses.

Do **not** begin with a questionnaire. Present the recommendation in ordinary
language, including why it fits and the strongest rejected direction. Ask at
most three questions whose answers would materially change the whole product.
Always mark a recommended answer.

Authority options are `USER_FIXED`, `REPO_COMMITMENT`, `AI_RECOMMENDED`,
`AI_DELEGATED`, and `VALIDATION_REQUIRED`. A user who says “you decide” or
equivalent may explicitly delegate; preserve the exact quote and decision
scope, then use `AI_DELEGATED`. Do not require producer expertise from the user.

## Compile and continue

Run `compile` and `check` exactly as directed by `idea/AGENTS.md`.

- `PRODUCT_DIRECTION_REVIEW_REQUIRED`: keep the full draft and ask only about
  reported material decisions.
- `IDEA_FACTORY_READY`: immediately return to the original requested factory
  work. Do not stop at document production if the user asked to build a game.
- Blocking states fail closed; never overwrite differing product authority.

Idea Factory makes a product commission. It does not itself author concrete
objectives, chapters, assets, SFX, or code.
