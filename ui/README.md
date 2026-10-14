# UI Factory

UI Factory makes UI **correct**, not pretty: the player sees what the gameplay needs
them to know, when they need it, and never what it hides. It has two parts:

1. **UI design capability** (`ui`, USER-approved 2026-10-14): starts from authorized
   gameplay and authors the Player Information Model, Attention and Motion Plan,
   Screen Contracts and Verification Plan, through the normal two-review, USER-approved
   lifecycle. See [`docs/UI_DESIGN_CAPABILITY.md`](docs/UI_DESIGN_CAPABILITY.md) and
   `ui_design.py`.
2. **UI Production Adapter** (construction): how this repo builds UI.

Split from Gameplay on 2026-10-11. The UI Production Adapter is
a just-in-time preflight that reconstructs how a game repository actually builds
and validates UI (layout structure, state ownership, scene integration, visual
grammar) before a UI-changing production plan. See
[`docs/UI_PRODUCTION_WORKFLOW.md`](docs/UI_PRODUCTION_WORKFLOW.md).

```text
python3 ui/ui.py start --game-repo <GAME_REPO>     # bounded UI file probe
python3 ui/ui.py compile|check|refresh ...          # adapter lifecycle
```

`gameplay/ui.py` stays as a compatibility entry.
