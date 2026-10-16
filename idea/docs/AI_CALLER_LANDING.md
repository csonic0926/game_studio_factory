# AI caller landing — Idea Factory

Read [`../AGENTS.md`](../AGENTS.md) first. The installed `idea-factory` skill
is the normal entry.

Use Idea Factory to question every proposed game-design idea, including
AI-generated mechanisms and later iterations, even when direction is settled or
the idea already exists in code. Follow
[the per-idea workflow](PRODUCT_DEFINITION_WORKFLOW.md#every-idea-receives-substantive-inquiry)
and preserve substantive reasoning, judgment and open questions.

Also use it when the product question is open or product-level authority is
missing/contradictory, regardless of how much code exists. Typical triggers:

- only a genre or loose idea exists;
- an early repo implements mechanics but has no stable commercial/experiential
  direction;
- downstream factories cannot decide without inventing audience, monetization,
  retention, expression, emotion, differentiation, or scope priorities;
- the user asks the AI to help decide what the product should be;
- the user supplies another game as a possible reference whose relationship to
  this project has not yet been established.

Concrete objective execution, chapter prose, asset and sound production stay with
their owning factories. Any new or materially changed game-design premise within
that work still needs the bounded Idea inquiry above; an unchanged-design
technical repair does not require a full Idea restart.

For idea thinking inside a bounded task whose product direction stays fixed
(visual redesign, UI pass, naming, mood), use skill `idea-thinking`:
`idea.py think` is read-only, needs no project state or migration, and returns
non-binding options. See [`IDEA_THINKING.md`](IDEA_THINKING.md).

Internal CLI:

```bash
python3 idea/idea.py think --focus "<task focus>" [--game-repo <GAME_REPO>]
python3 idea/idea.py start --game-repo <GAME_REPO>
# --reopen only for explicit exploration/direction reconsideration, not routine idea iterations
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
