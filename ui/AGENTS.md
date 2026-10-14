# UI Factory ownership

This department owns reusable UI production methods, validators, schemas and
CLI compatibility. Filled game artifacts belong only in the target game
repository (existing games keep them under `design/gameplay/ui/` and
`design/gameplay/adapter/`). It was split out of Gameplay on 2026-10-11 so that
Gameplay stays focused on rules and system integrity.

- Current scope: the just-in-time UI Production Adapter
  (`docs/UI_PRODUCTION_WORKFLOW.md`, `ui.py`, `ui_binding.py`): how this repo
  builds layout, owns state, integrates scenes/input/layers and keeps its
  visual grammar. Gameplay and Studio designs still invoke it before a
  UI-changing plan, and its rules stay in their review closure.
- `gameplay/ui.py` and `gameplay/ui_binding.py` remain compatibility entries.
- The UI design capability (`ui`, `docs/UI_DESIGN_CAPABILITY.md`, `ui_design.py`)
  owns player readability: what the player must, may and must not know, when,
  through which channel, what draws attention and for how long, and how every
  input answers. It starts only from an AUTHORIZED gameplay or studio design and
  never changes rules, balance, art direction or the repo's build conventions.
  Correct beats pretty: refuse a pretty UI that hides gameplay, never a plain UI
  that plays correctly.
- Mechanical checks (`ui_design.py`) prove coverage and bounds only; whether the
  facts and the attention plan are right stays with the two reviewers, blind
  observation and the USER playtest. Never merge those layers.
- Never write game output here; execution success never constitutes USER
  acceptance.
