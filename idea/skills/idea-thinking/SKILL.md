---
name: idea-thinking
description: Standalone Idea Factory thinking for a bounded task (visual redesign, UI pass, naming, mood, feature variant) when product direction stays fixed. Read-only; skips project inspect and the migration gate, writes nothing, and returns options/tensions as non-binding AI hypotheses. Use instead of skipping idea work when idea-factory reports MIGRATION_REQUIRED or product direction must not change.
---

# Idea thinking (standalone)

Use this when a task needs idea thinking but must not change product direction
or project state, e.g. "Idea Factory says migrate first; we are not changing
direction or migrating, just doing this visual redesign." Do not skip the
thinking; run it here.

Resolve STUDIO_ROOT from `design/STUDIO_FACTORY.local.md`, legacy
`design/AI_FACTORY.local.md`, or this skill's real source path (two levels
above `idea/skills/`). GAME_REPO is optional: the explicit path or current Git
root. Never scan sibling games.

1. Run `python3 $STUDIO_ROOT/idea/idea.py think --focus "<task focus>"
   [--game-repo $GAME_REPO]`. Do not run `factory.py inspect` or `migrate`;
   migration status does not matter here.
2. Follow `$STUDIO_ROOT/idea/docs/IDEA_THINKING.md`: fixed frame (returned
   `product_boundaries` plus the user's own limits), tensions, 3–5 options at
   close / lateral / far distance, honest rejections, recommendation or open
   choice, escalation check.
3. Return the result to the user or calling workflow, then continue the
   original task under its own rules. Write nothing under `design/product/`
   and create no Exploration or Product Thesis files.
4. If every good option needs a product-direction change, say so and stop;
   that belongs to `idea-factory` and its USER rulings.

All output is AI_HYPOTHESIS, never USER, REPO or product authority.
