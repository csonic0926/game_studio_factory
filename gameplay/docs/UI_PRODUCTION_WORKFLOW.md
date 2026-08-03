# UI Production Adapter workflow

This is a **just-in-time production preflight**, not a fourth gameplay-design
workflow. It runs before the first objective or repair production plan that
will change UI. Its output records how the current game repo actually builds
and validates UI, so a later coding model does not reinterpret the feature
through a generic UI architecture.

The adapter addresses three different failure classes that must not be folded
into one vague “UI bug”:

1. **layout structure** — containers, anchors, offsets, sizing, responsive
   composition, occlusion, and localization expansion;
2. **state ownership** — authoritative state, refresh timing, signals, and
   forbidden duplicate view logic/state;
3. **scene integration** — node paths, instantiation/lifecycle, input/focus,
   modals, canvas/layers, z-order, and teardown.

It does not decide what feature to make, restyle the game, or award gameplay
acceptance.

## Trigger

After objective/repair design is stable and before production planning:

- if the intended change touches a visible gameplay surface, scene UI, HUD,
  menu, modal, overlay, responsive composition, or localization fit, run this
  workflow;
- if the change is genuinely non-UI, do not run it merely for completeness;
- if a checked adapter already exists, reuse it and select only the relevant
  rules/exemplars/scenarios in the production plan;
- exact hashes of every cited UI evidence file determine reuse. Unrelated repo
  changes do not burn another investigation; if a cited source changes, rerun
  the workflow rather than letting a planner guess.

An obvious UI path or `work_types: [UI]` cannot be hidden behind
`touches_ui: false`. Historical v1 manifests remain valid for non-UI work, but
historical UI plans must be regenerated with the v2 binding.

## Step UI-1 — bounded mechanical probe

```bash
python3 <FACTORY_ROOT>/gameplay/ui.py start --game-repo <GAME_REPO>
```

When no checked adapter exists, this writes:

```text
design/gameplay/ui/PROJECT_UI_REPO_PROBE.json
```

and returns `UI_PRODUCTION_ADAPTER_INPUT_REQUIRED`.

The probe contains only repo revision/dirty-state binding, project markers,
and a bounded list of likely UI files with mechanical filename scores. Scores
are navigation hints with `semantic_authority: NONE`; a filename does not
prove ownership, lifecycle, or a valid convention.

## Step UI-2 — one evidence-focused investigator

Use one bounded investigator, not independent layout/state/scene authors.
Start from the feature's affected surface, then inspect:

- at least one **successful existing surface** the new work should resemble;
- its scene/layout hierarchy and actual sizing rules;
- the authoritative runtime state and state-to-view refresh/signal path;
- scene ownership, node paths, lifecycle, input/focus, modals, and layers;
- supported viewports/input modes and the distinct composition of each;
- active locales and stress cases for text expansion/glyph fit;
- existing screenshot/interaction harnesses and known bug evidence.

Write the exact canonical input:

```text
design/gameplay/ui/UI_PRODUCTION_ADAPTER_INPUT.json
```

using `templates/UI_PRODUCTION_ADAPTER_INPUT.json`.

### Evidence and authority rules

- `REPO_EVIDENCE` rules require exact game-repo-relative UTF-8 files and exact
  contained tokens. Repo convention comes from working implementation, not a
  path name or an AI preference.
- `USER_RULING` rules preserve an exact user quote. Use this when the user's
  production habit is intentional but not yet encoded consistently.
- `FACTORY_INVARIANT` is limited to portable safety constraints; it may not
  invent the game's visual grammar.
- Keep `ai_assumptions` and `unresolved_material_gaps` empty. Conflicting or
  absent material blocks compilation instead of being silently completed.

Every adapter must cover all seven rule categories:

```text
LAYOUT_STRUCTURE
STATE_OWNERSHIP
SCENE_INTEGRATION
INPUT_AND_LAYERING
RESPONSIVE_COMPOSITION
LOCALIZATION_FIT
VALIDATION
```

It must name at least one canonical exemplar. Validation scenarios must cover
every declared viewport and localization profile and must specify UI states,
an interaction path, assertions, and captures. A single happy-state screenshot
is not structural validation.

## Step UI-3 — compile and check

```bash
python3 <FACTORY_ROOT>/gameplay/ui.py compile \
  --game-repo <GAME_REPO> \
  --input design/gameplay/ui/UI_PRODUCTION_ADAPTER_INPUT.json

python3 <FACTORY_ROOT>/gameplay/ui.py check \
  --game-repo <GAME_REPO> \
  --input design/gameplay/ui/UI_PRODUCTION_ADAPTER_INPUT.json
```

Successful compilation creates only missing canonical files:

```text
design/gameplay/adapter/UI_PRODUCTION_ADAPTER.json
design/gameplay/adapter/UI_PRODUCTION_ADAPTER.md
design/gameplay/ui/UI_PRODUCTION_ADAPTER_RESULT.json
```

The compiler validates ownership before any mkdir/write, binds the exact repo
revision plus dirty bytes for the investigation window, fingerprints every
cited convention source for later reuse, and preflights all outputs.
Differing existing canonical state returns `BLOCKED_BY_EXISTING_UI_STATE`
without partial writes. Invalid/stale/assumed material returns
`BLOCKED_BY_UI_MODEL`.

If a cited convention source later changes, run `ui.py probe`, update the
bounded input from the changed evidence, and use the explicit replacement
command:

```bash
python3 <FACTORY_ROOT>/gameplay/ui.py refresh \
  --game-repo <GAME_REPO> \
  --input design/gameplay/ui/UI_PRODUCTION_ADAPTER_INPUT.json
```

`refresh` first verifies that the prior JSON/Markdown generation still matches
its checked result, builds and validates every replacement byte in memory, and
then replaces the canonical generation without creating a backup artifact.
Tampered or partial prior state blocks. Ordinary `compile` remains create-only
and never silently overwrites a differing adapter.

## Step UI-4 — bind production plans

Every v2 plan has `ui_impact`. A non-UI plan writes an explicit false/empty
declaration. A UI plan writes:

```json
{
  "touches_ui": true,
  "adapter_path": "design/gameplay/adapter/UI_PRODUCTION_ADAPTER.json",
  "adapter_sha256": "<EXACT_SHA256>",
  "rule_ids": ["<RELEVANT_RULE_ID>"],
  "exemplar_ids": ["<RELEVANT_EXEMPLAR_ID>"],
  "validation_scenario_ids": ["<RELEVANT_SCENARIO_ID>"]
}
```

The Markdown plan repeats that selection under `## UI realization contract`.
`plan.py` and `repair_plan.py` reject a stale adapter hash, unknown ids, missing
selection, false UI declaration, missing Markdown contract, or any attempt to
mutate the adapter as part of feature production.

During implementation, the selected scenarios are requirements, not advice.
The coding caller validates the affected empty/loading/populated/disabled/
modal/error states as applicable, exact interaction/refresh path, all selected
viewport/localization combinations, and scene/layer behavior before reporting
implementation complete.
