#!/usr/bin/env python3
"""Compatibility entry point for the Studio Godot automation platform.

The v1 CLI and Python functions remain import-compatible. New automation
commands are implemented under :mod:`studio.godot_engine`.
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:  # Direct ``python studio/godot_adapter.py`` use.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from studio.godot_engine.api import GodotSession  # noqa: E402
from studio.godot_engine.cli import main  # noqa: E402
from studio.godot_engine.v1 import (  # noqa: E402,F401
    ADAPTER_ROOT_RELATIVE,
    ADAPTER_VERSION,
    EVIDENCE_ROOT_RELATIVE,
    EVIDENCE_VERSION,
    FAIL,
    MANIFEST_RELATIVE,
    MANIFEST_VERSION,
    PASS,
    READY,
    TIMEOUT,
    EngineProbe,
    GodotAdapterError,
    GodotAdapterResult,
    ProcessResult,
    export_godot,
    import_check_godot,
    probe_godot,
    run_godot,
)

__all__ = [
    "ADAPTER_ROOT_RELATIVE", "ADAPTER_VERSION", "EVIDENCE_ROOT_RELATIVE",
    "EVIDENCE_VERSION", "FAIL", "MANIFEST_RELATIVE", "MANIFEST_VERSION",
    "PASS", "READY", "TIMEOUT", "EngineProbe", "GodotAdapterError",
    "GodotAdapterResult", "GodotSession", "ProcessResult", "export_godot",
    "import_check_godot", "probe_godot", "run_godot",
]


if __name__ == "__main__":
    raise SystemExit(main())
