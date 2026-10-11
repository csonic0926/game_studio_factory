# UI Factory

Split from Gameplay on 2026-10-11. Today it holds the UI Production Adapter:
a just-in-time preflight that reconstructs how a game repository actually builds
and validates UI (layout structure, state ownership, scene integration, visual
grammar) before a UI-changing production plan. See
[`docs/UI_PRODUCTION_WORKFLOW.md`](docs/UI_PRODUCTION_WORKFLOW.md).

```text
python3 ui/ui.py start --game-repo <GAME_REPO>     # bounded UI file probe
python3 ui/ui.py compile|check|refresh ...          # adapter lifecycle
```

`gameplay/ui.py` stays as a compatibility entry. Player-readability ownership is
a planned extension awaiting a USER-approved design.
