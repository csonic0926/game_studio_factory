# Idea Factory

Idea Factory supports open game-product discovery and, separately, the later
commissioning of a stable direction.

Normal use from a linked game repo:

```text
/idea-factory Explore what this project could become.
```

The first phase does not owe the user a pitch. It may record:

- an open question;
- an incompatible or unhelpful reference;
- several live directions;
- one direction that has genuinely emerged.

```text
bounded repo probe
  -> IDEA_EXPLORATION.json / .md (non-binding)
  -> optional further human/AI exploration
  -> explicit commission of one emerged direction
  -> PRODUCT_THESIS_INPUT.json v2
  -> deterministic compile/check
  -> PRODUCT_THESIS.md + FACTORY_CONSTRAINTS.json
```

“You decide” authorizes AI judgment, including a no-fit judgment. It does not
force convergence or automatically commission downstream authority.

Only commissioned Product Thesis decisions use the binding authority model:
`USER_FIXED`, `REPO_COMMITMENT`, `AI_RECOMMENDED`, `AI_DELEGATED`, and
`VALIDATION_REQUIRED`.

See [`AGENTS.md`](AGENTS.md) and
[`docs/PRODUCT_DEFINITION_WORKFLOW.md`](docs/PRODUCT_DEFINITION_WORKFLOW.md).
