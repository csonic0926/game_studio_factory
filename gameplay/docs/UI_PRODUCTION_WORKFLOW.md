# UI Production Adapter workflow

This is a **just-in-time production preflight**, not a fourth gameplay-design
workflow. It runs before the first objective or repair production plan that
will change UI. Its output records how the current game repo actually builds
and validates UI, so a later coding model does not reinterpret the feature
through a generic UI architecture.

The adapter addresses four different failure classes that must not be folded
into one vague “UI bug”:

1. **layout structure** — containers, anchors, offsets, sizing, responsive
   composition, occlusion, and localization expansion;
2. **state ownership** — authoritative state, refresh timing, signals, and
   forbidden duplicate view logic/state;
3. **scene integration** — node paths, instantiation/lifecycle, input/focus,
   modals, canvas/layers, z-order, and teardown.
4. **visual grammar** — accepted Theme/style resources, state StyleBoxes,
   typography/color roles, target-to-reference mappings, and the default that
   an additive change preserves the existing visual identity.

It does not decide what feature to make, authorize a redesign, or award
gameplay acceptance. Without an exact user redesign ruling, the compiled
policy is always `PRESERVE_EXISTING_VISUAL_GRAMMAR`.

## Trigger

After objective/repair design is stable and before production planning:

- if the intended change touches a visible gameplay surface, scene UI, HUD,
  menu, modal, overlay, responsive composition, or localization fit, run this
  workflow;
- if the change is genuinely non-UI, do not run it merely for completeness;
- if a checked adapter already exists, reuse it and select only the relevant
  rules/exemplars/scenarios in the production plan;
- v1 adapters are migration inputs, not production authority: `ui.py start`
  emits a fresh probe and requires v2 reconstruction plus explicit `refresh`;
- exact hashes of every cited UI evidence file determine reuse. Unrelated repo
  changes do not burn another investigation; if a cited source changes, rerun
  the workflow rather than letting a planner guess.

An obvious UI path or `work_types: [UI]` cannot be hidden behind
`touches_ui: false`. Historical non-current manifests remain readable only at
their documented non-UI/historical boundary; UI plans must be regenerated with
the v2 adapter and current plan schemas.

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
- the exact accepted baseline or explicit user ruling that makes each visual
  reference canonical; a current target is never evidence for itself;
- Theme/style/font/color resources and state-specific visual bindings, not
  only node containment and sizing;
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

Every adapter must cover all eight rule categories:

```text
LAYOUT_STRUCTURE
STATE_OWNERSHIP
SCENE_INTEGRATION
INPUT_AND_LAYERING
RESPONSIVE_COMPOSITION
LOCALIZATION_FIT
VISUAL_GRAMMAR
VALIDATION
```

`VISUAL_GRAMMAR`, like the four core construction categories, must be backed by
repo evidence or a user ruling.

Every canonical exemplar must carry one of two machine-checked provenance
forms:

- `ACCEPTED_BASELINE`: a canonical Studio
  `ACCEPTED_PLAYABLE_BASELINE.json`; the compiler verifies its project/status/
  game revision and proves every exemplar evidence file existed **unchanged**
  at that revision;
- `USER_RULING`: the exact quote explicitly accepting that reference.

This forbids circular certification such as treating a just-created target as
its own canonical exemplar.

Validation is deliberately split into `STRUCTURAL_FIT` and
`VISUAL_CONSISTENCY`. Every viewport/localization combination needs both.
Structural scenarios use geometry/state/scene/interaction comparisons. Visual
scenarios require a mechanical style comparison; screenshots are supplemental,
not sufficient. In Godot, visual scenarios must directly compare Theme/
StyleBox resource identity or resource properties (including font/color
properties where identity is not the right invariant).

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

Every objective manifest v4 / repair manifest v3 plan has `ui_impact`. A non-UI
plan writes an explicit false/empty declaration. A UI plan writes:

```json
{
  "touches_ui": true,
  "adapter_path": "design/gameplay/adapter/UI_PRODUCTION_ADAPTER.json",
  "adapter_sha256": "<EXACT_SHA256>",
  "rule_ids": ["<RELEVANT_RULE_ID>"],
  "exemplar_ids": ["<RELEVANT_EXEMPLAR_ID>"],
  "validation_scenario_ids": ["<STRUCTURAL_ID>", "<VISUAL_ID>"],
  "style_blast_radius_scope": "ALL_UI_CONTROLS_IN_CHANGE_AND_REOPENED_STYLE_BATCH",
  "style_blast_radius": [
    {
      "target_id": "<TARGET_ID>",
      "target_path": "<REPO_RELATIVE_PATH>",
      "control_ids": ["<CONTROL_OR_NODE_ID>"],
      "change_kind": "NEW_CONTROL | MODIFIED_CONTROL | REOPENED_BATCH_CONTROL",
      "disposition": "IMPLEMENT_STYLE_CHANGE | VERIFIED_CONSISTENT",
      "reference_exemplar_ids": ["<ACCEPTED_EXEMPLAR_ID>"],
      "visual_rule_ids": ["<VISUAL_GRAMMAR_RULE_ID>"],
      "structural_validation_scenario_ids": ["<STRUCTURAL_FIT_ID>"],
      "visual_validation_scenario_ids": ["<VISUAL_CONSISTENCY_ID>"]
    }
  ]
}
```

The blast radius inventories every control introduced or modified by the
change. When a style complaint reopens an earlier batch, it also inventories
the whole batch—not just the controls named in the complaint—and records
`VERIFIED_CONSISTENT` for reviewed siblings that need no write. Every target
maps to an accepted exemplar, a `VISUAL_GRAMMAR` rule, and separate structural
and visual scenarios. Every planned UI path must appear in this inventory.

The Markdown plan repeats that selection under `## UI realization contract`
and `## UI style blast radius`. `plan.py` and `repair_plan.py` reject a stale
adapter hash, unknown ids, incomplete blast radius, non-visual rules, swapped
validation kinds, screenshot-only visual checks, false UI declarations,
missing Markdown contracts, or any attempt to mutate the adapter as part of
feature production.

During implementation, the selected scenarios are requirements, not advice.
The coding caller validates the affected empty/loading/populated/disabled/
modal/error states as applicable, exact interaction/refresh path, all selected
viewport/localization combinations, and scene/layer behavior before reporting
implementation complete. Visual validation compares target/reference resources
or computed properties mechanically first; capture review then checks the
remaining rendered gestalt.
