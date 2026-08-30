"""Explicit runtime capability negotiation."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


BRIDGE_CAPABILITIES = frozenset(
    {
        "FRAME_BOUND_EXECUTION", "ACTION_INPUT", "KEY_INPUT", "MOUSE_INPUT",
        "STRUCTURAL_CAPTURE", "PNG_CAPTURE", "OBSERVATION", "CHECKPOINT",
        "PROJECT_COMMAND", "LIVE_SESSION",
    }
)


def negotiate(required: Iterable[str], available: Iterable[str]) -> dict[str, Any]:
    required_set = set(required)
    available_set = set(available)
    missing = sorted(required_set - available_set)
    return {
        "status": "PASS" if not missing else "BLOCKED",
        "required": sorted(required_set),
        "available": sorted(available_set),
        "missing": missing,
    }


__all__ = ["BRIDGE_CAPABILITIES", "negotiate"]
