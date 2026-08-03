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
   `<STUDIO_ROOT>/studio/docs/AI_CALLER_LANDING.md`.
4. If the game repo is unlinked, use `init-game-studio-factory` and continue in
   the same call.

## Hard delivery rule

A build, scene, character controller, combat sandbox, or collection of working
features is not Studio delivery unless it belongs to an Accepted Playable
Baseline with genuine gameplay acceptance and prior-baseline regression.
Content, fidelity, map size, and production horizon may be narrowed; the
minimum gameplay floor may not.

## Route the current state

- Missing/open product direction: invoke `idea-factory`.
- Run `python3 <STUDIO_ROOT>/studio/baseline.py start --game-repo <GAME_REPO>`.
  `BASELINE_RECONSTRUCTION_INPUT_REQUIRED` means freshly reconstruct the whole
  currently playable baseline; `BASELINE_PROMOTION_INPUT_REQUIRED` means bind
  the just-completed workflow, fresh acceptance, and full predecessor
  regression. Follow `studio/docs/BASELINE_ADMISSION_WORKFLOW.md`.
- No accepted playable baseline and no complete loop: establish the smallest
  complete gameplay loop through `gameplay-factory`, then return to
  reconstruction; do not call an interactive demo a baseline.
- Accepted baseline exists: diagnose the next gameplay pressure, research new
  design tokens across same-type/cross-genre/non-game references, select one
  bounded unit, and use the specialist factories for production.
- Candidate implementation complete: require fresh new-gameplay acceptance and
  regression of predecessor gameplay before promotion.
- Requested horizon reached: deliver only the runnable build represented by the
  promoted baseline.

## Foundation limitation

The two-case baseline compiler/checker is operational, but the persistent
autonomous multi-cycle scheduler is not. Follow the contract for bounded
orchestration, but do not claim unattended multi-day Studio execution until
that scheduler and real pilots exist.
