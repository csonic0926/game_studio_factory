# AI caller landing — Idea Factory

Read [`../AGENTS.md`](../AGENTS.md) first. The installed `idea-factory` skill
is the normal entry.

Use Idea Factory when product-level authority is missing or contradictory,
regardless of how much code exists. Typical triggers:

- only a genre or loose idea exists;
- an early repo implements mechanics but has no stable commercial/experiential
  direction;
- downstream factories cannot decide without inventing audience, monetization,
  retention, expression, emotion, differentiation, or scope priorities;
- the user asks the AI to help decide what the product should be.

Do not use it for one concrete objective, a known gameplay gap, chapter prose,
asset production, or sound generation after product direction is already
adequate. Route those to their owning factories.

Internal CLI:

```bash
python3 idea/idea.py start --game-repo <GAME_REPO>
python3 idea/idea.py compile --game-repo <GAME_REPO> \
  --input design/product/idea/PRODUCT_THESIS_INPUT.json
python3 idea/idea.py check --game-repo <GAME_REPO> \
  --input design/product/idea/PRODUCT_THESIS_INPUT.json
```

The AI caller continues intermediate states. Humans should not have to paste
the probe, fill the JSON, or issue a second production prompt.
