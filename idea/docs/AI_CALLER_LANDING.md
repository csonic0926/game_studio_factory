# AI caller landing — Idea Factory

Read [`../AGENTS.md`](../AGENTS.md) first. The installed `idea-factory` skill
is the normal entry.

Use Idea Factory when the product question is open or product-level authority
is missing/contradictory, regardless of how much code exists. Typical triggers:

- only a genre or loose idea exists;
- an early repo implements mechanics but has no stable commercial/experiential
  direction;
- downstream factories cannot decide without inventing audience, monetization,
  retention, expression, emotion, differentiation, or scope priorities;
- the user asks the AI to help decide what the product should be;
- the user supplies another game as a possible reference whose relationship to
  this project has not yet been established.

Do not use it for one concrete objective, a known gameplay gap, chapter prose,
asset production, or sound generation after product direction is already
adequate. Route those to their owning factories.

Internal CLI:

```bash
python3 idea/idea.py start --game-repo <GAME_REPO>
# add --reopen only for an explicit reconsider/rerun request
python3 idea/idea.py explore --game-repo <GAME_REPO> \
  --input design/product/idea/IDEA_EXPLORATION.json
python3 idea/idea.py check-exploration --game-repo <GAME_REPO> \
  --input design/product/idea/IDEA_EXPLORATION.json
python3 idea/idea.py compile --game-repo <GAME_REPO> \
  --input design/product/idea/PRODUCT_THESIS_INPUT.json
python3 idea/idea.py check --game-repo <GAME_REPO> \
  --input design/product/idea/PRODUCT_THESIS_INPUT.json
```

Exploration may validly return no-fit, no current answer, or several live
directions. The caller must not create a Product Thesis until the user sees the
frontier and explicitly commissions one emerged direction. Humans never fill
the internal JSON themselves.
