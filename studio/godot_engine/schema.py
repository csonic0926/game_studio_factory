"""Strict runtime validators for the public JSON contracts.

The checked-in JSON Schemas are the interchange specification.  These small
validators intentionally use only the Python standard library so CI and game
repositories do not need a schema package merely to reject unsafe input.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .common import GodotAutomationError, load_json, validate_repo_relative


def exact_object(
    value: Any,
    *,
    required: set[str],
    optional: set[str] = frozenset(),
    context: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise GodotAutomationError(f"{context} must be an object")
    missing = sorted(required - value.keys())
    unknown = sorted(value.keys() - required - optional)
    if missing:
        raise GodotAutomationError(f"{context} missing required fields: {', '.join(missing)}")
    if unknown:
        raise GodotAutomationError(f"{context} has unknown fields: {', '.join(unknown)}")
    return value


def string_list(value: Any, *, context: str, unique: bool = True) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise GodotAutomationError(f"{context} must be an array of non-empty strings")
    if unique and len(set(value)) != len(value):
        raise GodotAutomationError(f"{context} must contain unique values")
    return value


def load_strict_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise GodotAutomationError(f"{path} must contain one JSON object")
    return payload


PROFILE_KEYS = {
    "schema_version",
    "profile_id",
    "provider_autoload",
    "allowed_input_actions",
    "allowed_keycodes",
    "allowed_mouse_buttons",
    "project_commands",
    "observations",
    "checkpoints",
    "structural_nodes",
}


def validate_profile(payload: Any) -> dict[str, Any]:
    profile = exact_object(payload, required=PROFILE_KEYS, context="bridge profile")
    if profile["schema_version"] != "godot_bridge_profile.v1":
        raise GodotAutomationError("bridge profile schema_version must be godot_bridge_profile.v1")
    for field in ("profile_id", "provider_autoload"):
        if not isinstance(profile[field], str) or not profile[field]:
            raise GodotAutomationError(f"bridge profile {field} must be a non-empty string")
    string_list(profile["allowed_input_actions"], context="allowed_input_actions")
    for field in ("allowed_keycodes", "allowed_mouse_buttons"):
        values = profile[field]
        if not isinstance(values, list) or any(not isinstance(item, int) or isinstance(item, bool) or item < 0 for item in values):
            raise GodotAutomationError(f"bridge profile {field} must be an array of non-negative integers")
        if len(set(values)) != len(values):
            raise GodotAutomationError(f"bridge profile {field} must contain unique values")
    for field in ("project_commands", "observations", "checkpoints"):
        string_list(profile[field], context=field)
    nodes = profile["structural_nodes"]
    if not isinstance(nodes, list):
        raise GodotAutomationError("structural_nodes must be an array")
    seen: set[str] = set()
    for index, node in enumerate(nodes):
        item = exact_object(
            node,
            required={"id", "node_path", "facts"},
            context=f"structural_nodes[{index}]",
        )
        if not isinstance(item["id"], str) or not item["id"] or item["id"] in seen:
            raise GodotAutomationError("structural node ids must be non-empty and unique")
        seen.add(item["id"])
        if not isinstance(item["node_path"], str) or not item["node_path"].startswith("/"):
            raise GodotAutomationError("structural node_path must be an absolute SceneTree path")
        allowed_facts = {
            "class", "visible", "focus", "position", "size", "global_position",
            "theme", "styleboxes", "text", "disabled",
        }
        facts = set(string_list(item["facts"], context="structural node facts"))
        if not facts or not facts <= allowed_facts:
            raise GodotAutomationError(f"unsupported structural facts: {sorted(facts - allowed_facts)}")
    return profile


SCENARIO_KEYS = {
    "schema_version", "scenario_id", "seed", "initial_checkpoint",
    "required_capabilities", "fixed_fps", "max_frames", "steps", "expected_exit",
}


STEP_FIELDS: dict[str, tuple[set[str], set[str]]] = {
    "wait_frames": ({"type", "frames"}, set()),
    "wait_until": ({"type", "condition", "deadline_frames"}, set()),
    "input_action": ({"type", "action", "pressed"}, {"strength"}),
    "key_event": ({"type", "keycode", "pressed"}, {"echo", "unicode"}),
    "mouse_button": ({"type", "button_index", "pressed", "position"}, set()),
    "mouse_motion": ({"type", "position", "relative"}, {"button_mask"}),
    "project_command": ({"type", "command"}, {"arguments"}),
    "checkpoint": ({"type", "checkpoint"}, {"arguments"}),
    "snapshot": ({"type", "snapshot_id", "kind"}, {"observation"}),
    "assert": ({"type", "assertion_id", "actual", "operator", "expected"}, set()),
    "capture_structure": ({"type", "capture_id"}, set()),
    "capture_png": ({"type", "capture_id"}, set()),
    "movie_marker": ({"type", "marker"}, set()),
    "finish": ({"type"}, {"exit_code"}),
}


def _condition(value: Any, context: str) -> None:
    item = exact_object(value, required={"actual", "operator", "expected"}, context=context)
    if item["operator"] not in {"eq", "ne", "gt", "gte", "lt", "lte", "contains", "exists"}:
        raise GodotAutomationError(f"{context} has unsupported operator")
    if not isinstance(item["actual"], str) or not item["actual"]:
        raise GodotAutomationError(f"{context}.actual must be a non-empty observable name")


def _nonempty_string(value: Any, context: str) -> None:
    if not isinstance(value, str) or not value:
        raise GodotAutomationError(f"{context} must be a non-empty string")


def _integer(value: Any, context: str, *, minimum: int | None = None) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or (minimum is not None and value < minimum):
        suffix = " positive (at least 1)" if minimum == 1 else (f" at least {minimum}" if minimum is not None else "")
        raise GodotAutomationError(f"{context} must be an integer{suffix}")


def _number(value: Any, context: str, *, minimum: float | None = None, maximum: float | None = None) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise GodotAutomationError(f"{context} must be numeric")
    if minimum is not None and value < minimum or maximum is not None and value > maximum:
        raise GodotAutomationError(f"{context} is outside the allowed range")


def _vector(value: Any, context: str) -> None:
    if not isinstance(value, list) or len(value) != 2:
        raise GodotAutomationError(f"{context} must be a two-number array")
    for index, component in enumerate(value):
        _number(component, f"{context}[{index}]")


def validate_scenario(payload: Any) -> dict[str, Any]:
    scenario = exact_object(payload, required=SCENARIO_KEYS, context="scenario")
    if scenario["schema_version"] != "godot_scenario.v1":
        raise GodotAutomationError("scenario schema_version must be godot_scenario.v1")
    for field in ("scenario_id",):
        if not isinstance(scenario[field], str) or not scenario[field]:
            raise GodotAutomationError(f"scenario {field} must be a non-empty string")
    if not isinstance(scenario["seed"], int) or isinstance(scenario["seed"], bool):
        raise GodotAutomationError("scenario seed must be an integer")
    if scenario["initial_checkpoint"] is not None and (
        not isinstance(scenario["initial_checkpoint"], str) or not scenario["initial_checkpoint"]
    ):
        raise GodotAutomationError("initial_checkpoint must be null or a non-empty string")
    string_list(scenario["required_capabilities"], context="required_capabilities")
    for field in ("fixed_fps", "max_frames"):
        if not isinstance(scenario[field], int) or isinstance(scenario[field], bool) or scenario[field] < 1:
            raise GodotAutomationError(f"scenario {field} must be a positive integer")
    if scenario["expected_exit"] not in {"BRIDGE_FINISH", "PROJECT_EXIT", "EITHER"}:
        raise GodotAutomationError("scenario expected_exit is invalid")
    steps = scenario["steps"]
    if not isinstance(steps, list) or not steps:
        raise GodotAutomationError("scenario steps must be a non-empty array")
    finish_count = 0
    for index, raw in enumerate(steps):
        if not isinstance(raw, dict) or not isinstance(raw.get("type"), str):
            raise GodotAutomationError(f"steps[{index}] must be a typed object")
        step_type = raw["type"]
        if step_type not in STEP_FIELDS:
            raise GodotAutomationError(f"steps[{index}] has unsupported type {step_type!r}")
        required, optional = STEP_FIELDS[step_type]
        step = exact_object(raw, required=required, optional=optional, context=f"steps[{index}]")
        if step_type == "wait_frames":
            _integer(step["frames"], "wait_frames.frames", minimum=1)
        if step_type == "wait_until":
            _condition(step["condition"], f"steps[{index}].condition")
            _integer(step["deadline_frames"], "wait_until.deadline_frames", minimum=1)
        if step_type == "input_action":
            _nonempty_string(step["action"], f"steps[{index}].action")
            if not isinstance(step["pressed"], bool):
                raise GodotAutomationError(f"steps[{index}].pressed must be boolean")
            if "strength" in step:
                _number(step["strength"], f"steps[{index}].strength", minimum=0, maximum=1)
        if step_type == "key_event":
            _integer(step["keycode"], f"steps[{index}].keycode", minimum=0)
            if not isinstance(step["pressed"], bool):
                raise GodotAutomationError(f"steps[{index}].pressed must be boolean")
            if "echo" in step and not isinstance(step["echo"], bool):
                raise GodotAutomationError(f"steps[{index}].echo must be boolean")
            if "unicode" in step:
                _integer(step["unicode"], f"steps[{index}].unicode", minimum=0)
        if step_type == "assert":
            _condition({key: step[key] for key in ("actual", "operator", "expected")}, f"steps[{index}]")
            _nonempty_string(step["assertion_id"], f"steps[{index}].assertion_id")
        if step_type in {"mouse_button", "mouse_motion"}:
            for field in ("position", "relative") if step_type == "mouse_motion" else ("position",):
                _vector(step[field], f"steps[{index}].{field}")
        if step_type == "mouse_button":
            _integer(step["button_index"], f"steps[{index}].button_index", minimum=0)
            if not isinstance(step["pressed"], bool):
                raise GodotAutomationError(f"steps[{index}].pressed must be boolean")
        if step_type == "mouse_motion" and "button_mask" in step:
            _integer(step["button_mask"], f"steps[{index}].button_mask", minimum=0)
        if step_type in {"project_command", "checkpoint"}:
            field = "command" if step_type == "project_command" else "checkpoint"
            _nonempty_string(step[field], f"steps[{index}].{field}")
            if "arguments" in step and not isinstance(step["arguments"], dict):
                raise GodotAutomationError(f"steps[{index}].arguments must be an object")
        if step_type == "snapshot":
            _nonempty_string(step["snapshot_id"], f"steps[{index}].snapshot_id")
            if step["kind"] not in {"OBSERVABLE", "MECHANICAL"}:
                raise GodotAutomationError("snapshot.kind must be OBSERVABLE or MECHANICAL")
            if "observation" in step:
                _nonempty_string(step["observation"], f"steps[{index}].observation")
        if step_type in {"capture_structure", "capture_png"}:
            _nonempty_string(step["capture_id"], f"steps[{index}].capture_id")
        if step_type == "movie_marker":
            _nonempty_string(step["marker"], f"steps[{index}].marker")
        if step_type == "finish":
            finish_count += 1
            if index != len(steps) - 1:
                raise GodotAutomationError("finish must be the final scenario step")
            if "exit_code" in step:
                _integer(step["exit_code"], f"steps[{index}].exit_code")
    if finish_count != 1:
        raise GodotAutomationError("scenario requires exactly one final finish step")
    return scenario


def load_profile(path: Path) -> dict[str, Any]:
    return validate_profile(load_strict_object(path))


def load_scenario(path: Path) -> dict[str, Any]:
    return validate_scenario(load_strict_object(path))


def validate_evidence_ref(value: Any, *, context: str) -> dict[str, str]:
    item = exact_object(value, required={"path", "sha256"}, context=context)
    validate_repo_relative(item["path"], field=f"{context}.path")
    if not isinstance(item["sha256"], str) or len(item["sha256"]) != 64:
        raise GodotAutomationError(f"{context}.sha256 must be a SHA-256 digest")
    return item
