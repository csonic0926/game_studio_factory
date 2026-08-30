---
name: game-studio-factory
description: Operate the whole game across Idea, Gameplay, Story, Asset, and Sound factories from an Accepted Playable Baseline. Use for open-ended requests to make, continue, or autonomously scale a game rather than one bounded specialist artifact. Never treats a runnable interactive demo as delivered gameplay.
---

# Game Studio Factory

This is the whole-game entry. Specialist Game AI Factories are capabilities
called by the Studio, not substitutes for whole-game delivery.

## Resolve the operator contract

1. Resolve `<GAME_REPO>` from an explicit path or the current Git root. Never
   scan siblings.
2. Resolve `<STUDIO_ROOT>` from `design/STUDIO_FACTORY.local.md`, legacy
   `design/AI_FACTORY.local.md`, the installed-skills manifest, or this skill's
   real source path.
3. Read `<STUDIO_ROOT>/studio/AGENTS.md` and
   `<STUDIO_ROOT>/studio/docs/AI_CALLER_LANDING.md`, including
   `studio/docs/SEMANTIC_ALIGNMENT_WORKFLOW.md` and
   `studio/docs/PRODUCT_AUTHORITY_LIFECYCLE.md`.
4. If the game repo is unlinked, use `init-game-studio-factory` and continue in
   the same call.

## Hard delivery rule

A build, scene, character controller, combat sandbox, or collection of working
features is not Studio delivery unless it belongs to an Accepted Playable
Baseline with genuine gameplay acceptance and prior-baseline regression.
Acceptance must bind the exact expected-experience authority and include a
validated Studio gameplay-system cycle, observed two-lap feedback, and a
recorded human playtest verdict; AI reviewers and implementation tests do not
own taste.
Content, fidelity, map size, and production horizon may be narrowed; the
minimum gameplay floor may not.

## Route the current state

Before routing material new user input or presenting a material Studio answer,
run the semantic-alignment workflow. The candidate author records the exact raw
input, active authority, pending decision dispositions, candidate output,
claim provenance, and any question. Spawn one fresh subagent/context using the
`studio-semantic-alignment-reviewer` skill to review it.
`REVISE_BEFORE_USER` returns privately to the author; only
`PASS_ALIGNMENT` or `HUMAN_RULING_GENUINELY_REQUIRED` may reach the user. Do
not ask the user to name this workflow or rewrite ordinary language as a
Factory brief.
When a reply is elliptical (`b`, `yes`, `that one`), bind it to the exact
reviewed prior question/option before treating the selected meaning as user
authority. Include every internal Product/system/card/plan artifact changed by
the interpretation in the same review; a compact human surface is not a waiver
for hidden authority drift.

Run `studio/product.py status` before trusting a canonical Product Thesis or an
old accepted baseline. `NO_ACTIVE_PRODUCT_AUTHORITY` routes to Idea exploration
even when historical code or artifacts remain. A whole-direction revocation
uses the native two-phase Product Authority archive workflow: snapshot first,
semantic review before mutation, then `product.py archive`. Never move a whole
design tree ad hoc or synthesize `USER_REJECTED` card tokens from natural
language. After a new Idea commission compiles and checks, run
`product.py activate` before downstream design.

- Missing/open product direction: invoke `idea-factory`. After the Product
  Thesis is commissioned, follow `studio/docs/GAMEPLAY_SYSTEM_WORKFLOW.md`;
  Studio—not Gameplay Factory—must synthesize the exact closed gameplay system.
  A gamification or positive-feedback intent is a reward-loop obligation even
  when the underlying service is not conventional gameplay. Preserve that
  distinction through Product non-goals and product-fidelity review.
- Run `python3 <STUDIO_ROOT>/studio/baseline.py start --game-repo <GAME_REPO>`.
  `BASELINE_RECONSTRUCTION_INPUT_REQUIRED` means freshly reconstruct the whole
  currently playable baseline; `BASELINE_PROMOTION_INPUT_REQUIRED` means bind
  the just-completed workflow, fresh acceptance, and full predecessor
  regression. Follow `studio/docs/BASELINE_ADMISSION_WORKFLOW.md`.
- No accepted playable baseline: validate a gameplay system with
  `studio/cycle.py`, obtain human approval on its compact decision card, then
  use `gameplay-factory` for the minimum cycle-complete vertical slice. It must
  demonstrate two laps in which lap-one reward/state materially changes the
  lap-two decision. Do not call a result/replay sequence a loop or baseline.
- At the approval boundary, use `gameplay/design_gate.py render-card` and show
  only an alignment-reviewed, registered pending decision surface. Persist
  reconstruction, research, full specs, and review reports without dumping
  them into the user's verdict request. A revised pending card must
  machine-supersede the old payload before rendering.
- Accepted baseline exists: diagnose the next gameplay pressure or broken
  cycle edge, research new design tokens across same-type/cross-genre/non-game
  references, select one minimum cycle-complete unit, and use the specialist
  factories for production.
- Candidate implementation complete: require revision-pinned, authority-bound
  fresh new-gameplay acceptance with an observed two-lap cycle, an explicit
  user playtest verdict, and regression of predecessor gameplay before
  promotion.
- For a Godot target, use `studio/godot_adapter.py` after implementation or
  integration to bind project discovery, import/run/export results, and hashed
  logs before making technical runtime claims. Read
  `studio/docs/GODOT_ENGINE_ADAPTER.md`. Adapter evidence is evidence-only: a
  passing process run cannot replace gameplay acceptance, the human playtest,
  or baseline regression. Preserve v1's explicit gaps for input injection,
  structured runtime state, and validated visual capture rather than claiming
  those capabilities exist.
- Requested horizon reached: deliver only the runnable build represented by the
  promoted baseline.

## Foundation limitation

The two-case baseline compiler/checker is operational, but the persistent
autonomous multi-cycle scheduler is not. Follow the contract for bounded
orchestration, but do not claim unattended multi-day Studio execution until
that scheduler and real pilots exist.
