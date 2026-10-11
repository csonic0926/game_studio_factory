#!/usr/bin/env python3
"""Compatibility entry: moved to ui/ui.py (UI Factory, 2026-10-11).

Existing callers (`python3 gameplay/ui.py ...` and `import gameplay.ui`)
keep working; both resolve to the single module in ui/. Game-owned artifacts
stay at their existing design/gameplay/ paths.
"""
import importlib.util
from pathlib import Path
import runpy
import sys

_SOURCE = Path(__file__).resolve().parents[1] / "ui" / "ui.py"

if __name__ == "__main__":
    sys.path.insert(0, str(_SOURCE.parent))
    runpy.run_path(str(_SOURCE), run_name="__main__")
else:
    _module = sys.modules.get("ui.ui")
    if _module is None:
        _spec = importlib.util.spec_from_file_location("ui.ui", _SOURCE)
        _module = importlib.util.module_from_spec(_spec)
        sys.modules["ui.ui"] = _module
        _spec.loader.exec_module(_module)
    sys.modules[__name__] = _module
