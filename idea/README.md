# Idea Factory

Idea Factory supplies AI-producer support above Story, Gameplay, Asset, and
Sound. It is appropriate for a one-line game idea, an early repository with
unsettled positioning, or a later project whose product constraints conflict.

Normal use from a linked game repo:

```text
/idea-factory Help decide what product this project should become.
```

The AI first provides one complete recommended commercial/experiential
direction. It asks at most a few high-leverage questions in ordinary language;
the user may edit, accept, or explicitly delegate decisions to the AI.

```text
bounded repo probe
  -> one AI producer synthesis
  -> adoption or scoped delegation
  -> PRODUCT_THESIS_INPUT.json
  -> deterministic compile/check
  -> PRODUCT_THESIS.md + FACTORY_CONSTRAINTS.json
  -> downstream factory handoff
```

Authority remains explicit:

- `USER_FIXED`
- `REPO_COMMITMENT`
- `AI_RECOMMENDED`
- `AI_DELEGATED`
- `VALIDATION_REQUIRED`

The checker proves provenance, ownership, causal structure, and exact handoff.
It does not prove market success, retention, emotion, or fun.

See [`AGENTS.md`](AGENTS.md) and
[`docs/PRODUCT_DEFINITION_WORKFLOW.md`](docs/PRODUCT_DEFINITION_WORKFLOW.md).
