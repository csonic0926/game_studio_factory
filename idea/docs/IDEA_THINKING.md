# Idea Factory: standalone idea thinking

## Why it exists

The full Idea Factory flow owns product direction. It resolves project state,
and an unmigrated v2 project returns `MIGRATION_REQUIRED` before any work. That
gate is correct for product authority, but it also blocked a smaller need:

```text
"The Idea Factory entry check says the project must migrate first; this time
we are not changing product direction or migrating without authorization, so
we will just do this pure visual redesign."
```

The caller then did the visual redesign with no idea thinking at all. The
redesign still needed divergent options, tensions and a reasoned choice; it did
not need product authority or migration.

Standalone thinking gives the caller that thinking without touching project
state. The skill `idea-thinking` is its entry point.

## Contract

```bash
python3 idea/idea.py think --focus "<what the thinking is for>" \
  [--game-repo <GAME_REPO>] [--max-candidates 40]
```

- Read-only. It never calls `factory.py inspect`, never migrates, never writes
  into the game repo (`written_paths` is always empty).
- Works on unmigrated, v1, v2 and unlinked repos, or with no repo at all.
- Returns `IDEA_THINKING_READY` with a JSON brief: focus, repository revision,
  existing product boundaries (`PRODUCT_THESIS.md`, `FACTORY_CONSTRAINTS.json`
  when present) and bounded candidate reading materials.
- Everything the thinking produces is `AI_HYPOTHESIS`. It is not USER, REPO
  or product authority, it is not an `IDEA_EXPLORATION` record and it cannot
  feed a Product Thesis commission.

## Method

The primary agent thinks; the CLI only bounds what to read.

1. **Pin the focus and the fixed frame.** Restate the focus in one line. List
   what must not move: existing product boundaries, the user's own limits in
   this request ("no product direction change", "visual only", scope, platform)
   and any repo commitments that are actually read. Read only the materials
   needed for the focus.
2. **Name the tensions.** State the 2–4 forces this focus has to balance (e.g.
   readability vs. atmosphere, familiarity vs. identity). A tension is a pair
   that pulls in opposite directions, not a feature list.
3. **Diverge on distance.** Produce 3–5 options that sit at different
   distances from the current state: at least one close variant, one clear
   lateral move, and one far option that still respects the fixed frame. Each
   option gets: the core idea in one line, what it preserves, what it risks,
   and which tension it resolves in which direction.
4. **Reject honestly.** Drop options that break the fixed frame and say why. A
   no-fit finding ("no option improves this without changing direction") is a
   valid result.
5. **Recommend or leave open.** Give one recommendation with the reason, or
   say that the choice belongs to the user and which observation would decide
   it. Do not force convergence.
6. **Escalation check.** If good options all require changing product
   direction, report that plainly and stop. Product change goes through the
   full `idea-factory` flow, including its migration gate and USER rulings.

## Output to the caller

Return the result in the conversation (or to the calling skill), not as a
game-repo artifact:

```text
Focus / fixed frame
Tensions
Options (close / lateral / far) — idea, preserves, risks, tension resolved
Rejected (and why)
Recommendation or open choice
Escalation: none | product direction would need to change because …
```

The caller then continues its own task (visual redesign, UI pass, naming, a
scene mood, …) under its own factory or workflow. Adopting an option inside
that task is the caller's decision under that task's rules; it does not
become product authority.

## Boundary with the full flow

| Need | Use |
| --- | --- |
| Ideas, options or tensions for a bounded task; product direction fixed | `idea-thinking` → `idea.py think` |
| Explore or change what the product is | `idea-factory` (inspect, migration gate, exploration, commission) |
| Persist a non-binding exploration record in the game repo | `idea-factory` → `idea.py start` / `explore` |
