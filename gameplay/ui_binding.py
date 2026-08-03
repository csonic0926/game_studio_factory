"""Shared validation for UI-changing Gameplay Factory production plans.

The feature/design artifact says what the player should experience.  This
module prevents a planner from silently inventing how an established game
repository constructs UI: every UI-changing plan must bind the exact
game-owned UI Production Adapter and select concrete rules, exemplars, and
validation scenarios from it.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


UI_ADAPTER_SCHEMA_VERSION = "ui_production_adapter.v1"
UI_ADAPTER_STATUS = "UI_PRODUCTION_ADAPTER_READY"
UI_ADAPTER_RELATIVE = Path(
    "design/gameplay/adapter/UI_PRODUCTION_ADAPTER.json"
)
UI_RESULT_RELATIVE = Path(
    "design/gameplay/ui/UI_PRODUCTION_ADAPTER_RESULT.json"
)

_UI_PATH_SUFFIXES = {
    ".uxml",
    ".uss",
    ".ui",
    ".qml",
    ".css",
    ".scss",
}
_UI_PATH_PARTS = {
    "ui",
    "hud",
    "menu",
    "menus",
    "screen",
    "screens",
    "dialog",
    "dialogs",
    "modal",
    "overlay",
    "overlays",
    "widget",
    "widgets",
}


@dataclass(frozen=True)
class UiImpactBinding:
    touches_ui: bool = False
    adapter_path: str = ""
    adapter_sha256: str = ""
    rule_ids: tuple[str, ...] = ()
    exemplar_ids: tuple[str, ...] = ()
    validation_scenario_ids: tuple[str, ...] = ()


def _text_list(value: Any, label: str, errors: list[str]) -> list[str]:
    if not isinstance(value, list):
        errors.append(f"{label} must be an array")
        return []
    result: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{label}[{index}] must be a non-empty string")
            continue
        result.append(item.strip())
    if len(result) != len(set(result)):
        errors.append(f"{label} must not contain duplicates")
    return result


def looks_like_ui_path(path_text: str) -> bool:
    """Return true only for paths with explicit UI construction signals."""

    path = Path(path_text)
    if path.suffix.lower() in _UI_PATH_SUFFIXES:
        return True
    lowered_parts = {part.lower() for part in path.parts}
    stem_tokens = set(path.stem.lower().replace("-", "_").split("_"))
    return bool((lowered_parts | stem_tokens) & _UI_PATH_PARTS)


def _ids(payload: dict[str, Any], field: str, id_field: str) -> set[str]:
    values = payload.get(field)
    if not isinstance(values, list):
        return set()
    return {
        item[id_field]
        for item in values
        if isinstance(item, dict)
        and isinstance(item.get(id_field), str)
        and item[id_field]
    }


def _validate_adapter_evidence_fingerprints(
    game_repo: Path,
    adapter: dict[str, Any],
    label: str,
    errors: list[str],
) -> None:
    """Fail when a UI convention source changed after adapter compilation."""

    refs: list[dict[str, Any]] = []
    for field in ("surfaces", "canonical_exemplars", "rules", "anti_patterns"):
        values = adapter.get(field)
        if not isinstance(values, list):
            continue
        for value in values:
            if isinstance(value, dict) and isinstance(value.get("evidence_refs"), list):
                refs.extend(
                    ref for ref in value["evidence_refs"] if isinstance(ref, dict)
                )
    seen: set[tuple[str, str]] = set()
    for ref in refs:
        path_text = ref.get("path")
        declared = ref.get("source_sha256")
        if not isinstance(path_text, str) or not path_text or Path(path_text).is_absolute():
            errors.append(f"{label} UI adapter has a non-portable evidence path")
            continue
        path = (game_repo / path_text).resolve()
        try:
            path.relative_to(game_repo.resolve())
        except ValueError:
            errors.append(f"{label} UI adapter evidence escapes the game repo")
            continue
        key = (path_text, str(declared))
        if key in seen:
            continue
        seen.add(key)
        if not path.is_file() or not isinstance(declared, str):
            errors.append(f"{label} UI adapter evidence is missing: {path_text}")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != declared:
            errors.append(
                f"{label} UI adapter evidence changed; refresh before planning: "
                f"{path_text}"
            )


def validate_ui_impact(
    *,
    game_repo: Path,
    raw_impact: Any,
    manifest_schema_version: str,
    work_types: list[str],
    planned_path_texts: list[str],
    label: str,
    errors: list[str],
) -> UiImpactBinding:
    """Validate one plan's UI declaration and return normalized metadata.

    Manifest v1 remains accepted for genuinely non-UI historical plans.  It
    cannot authorize UI work because it predates the adapter binding.
    """

    inferred_ui = "UI" in work_types or any(
        looks_like_ui_path(path) for path in planned_path_texts
    )
    if manifest_schema_version.endswith(".v1"):
        if inferred_ui:
            errors.append(
                f"{label} is a legacy v1 UI plan; regenerate it with a "
                "ui_impact binding before execution"
            )
        return UiImpactBinding()

    if not isinstance(raw_impact, dict):
        errors.append(f"{label}.ui_impact must be an object")
        return UiImpactBinding()

    allowed_fields = {
        "touches_ui",
        "adapter_path",
        "adapter_sha256",
        "rule_ids",
        "exemplar_ids",
        "validation_scenario_ids",
    }
    extra_fields = sorted(set(raw_impact) - allowed_fields)
    if extra_fields:
        errors.append(
            f"{label}.ui_impact has unsupported fields: " + ", ".join(extra_fields)
        )

    touches_ui = raw_impact.get("touches_ui")
    if not isinstance(touches_ui, bool):
        errors.append(f"{label}.ui_impact.touches_ui must be a boolean")
        touches_ui = False
    adapter_path = raw_impact.get("adapter_path")
    adapter_sha256 = raw_impact.get("adapter_sha256")
    if not isinstance(adapter_path, str):
        errors.append(f"{label}.ui_impact.adapter_path must be a string")
        adapter_path = ""
    if not isinstance(adapter_sha256, str):
        errors.append(f"{label}.ui_impact.adapter_sha256 must be a string")
        adapter_sha256 = ""
    rule_ids = _text_list(
        raw_impact.get("rule_ids"), f"{label}.ui_impact.rule_ids", errors
    )
    exemplar_ids = _text_list(
        raw_impact.get("exemplar_ids"),
        f"{label}.ui_impact.exemplar_ids",
        errors,
    )
    scenario_ids = _text_list(
        raw_impact.get("validation_scenario_ids"),
        f"{label}.ui_impact.validation_scenario_ids",
        errors,
    )

    if inferred_ui and not touches_ui:
        errors.append(
            f"{label} has UI work or an explicit UI path but declares touches_ui=false"
        )
    if touches_ui and "UI" not in work_types:
        errors.append(f"{label} declares touches_ui=true but work_types lacks UI")

    binding = UiImpactBinding(
        touches_ui=bool(touches_ui),
        adapter_path=adapter_path,
        adapter_sha256=adapter_sha256,
        rule_ids=tuple(rule_ids),
        exemplar_ids=tuple(exemplar_ids),
        validation_scenario_ids=tuple(scenario_ids),
    )
    if not touches_ui:
        if adapter_path or adapter_sha256 or rule_ids or exemplar_ids or scenario_ids:
            errors.append(
                f"{label}.ui_impact must leave adapter and id fields empty when "
                "touches_ui=false"
            )
        return binding

    expected_path = UI_ADAPTER_RELATIVE.as_posix()
    if adapter_path != expected_path:
        errors.append(
            f"{label}.ui_impact.adapter_path must be {expected_path}"
        )
        return binding
    adapter_file = (game_repo / UI_ADAPTER_RELATIVE).resolve()
    try:
        adapter_file.relative_to(game_repo.resolve())
    except ValueError:
        errors.append(f"{label}.ui_impact.adapter_path escapes the game repo")
        return binding
    if not adapter_file.is_file():
        errors.append(
            f"{label} touches UI but the UI Production Adapter is not ready"
        )
        return binding
    adapter_bytes = adapter_file.read_bytes()
    actual_sha256 = hashlib.sha256(adapter_bytes).hexdigest()
    if adapter_sha256 != actual_sha256:
        errors.append(f"{label}.ui_impact.adapter_sha256 is stale or incorrect")
    try:
        adapter = json.loads(adapter_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        errors.append(f"{label} UI Production Adapter is not valid UTF-8 JSON")
        return binding
    if not isinstance(adapter, dict):
        errors.append(f"{label} UI Production Adapter must contain an object")
        return binding
    if adapter.get("schema_version") != UI_ADAPTER_SCHEMA_VERSION:
        errors.append(f"{label} UI Production Adapter has an unsupported schema")
    if adapter.get("status") != UI_ADAPTER_STATUS:
        errors.append(f"{label} UI Production Adapter is not ready")
    for required_field in (
        "surfaces",
        "canonical_exemplars",
        "rules",
        "viewport_profiles",
        "localization_profiles",
        "validation_scenarios",
    ):
        if not isinstance(adapter.get(required_field), list) or not adapter[required_field]:
            errors.append(
                f"{label} UI Production Adapter lacks compiled {required_field}"
            )
    _validate_adapter_evidence_fingerprints(game_repo, adapter, label, errors)

    result_file = game_repo / UI_RESULT_RELATIVE
    if not result_file.is_file():
        errors.append(f"{label} UI Production Adapter has no checked result")
    else:
        try:
            result = json.loads(result_file.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            errors.append(f"{label} UI Production Adapter result is invalid")
        else:
            outputs = result.get("outputs") if isinstance(result, dict) else None
            if (
                not isinstance(result, dict)
                or result.get("schema_version") != "ui_production_adapter_result.v1"
                or result.get("status") != UI_ADAPTER_STATUS
                or not isinstance(outputs, dict)
                or outputs.get(UI_ADAPTER_RELATIVE.as_posix()) != actual_sha256
            ):
                errors.append(
                    f"{label} UI Production Adapter is not backed by its checked result"
                )

    available_rules = _ids(adapter, "rules", "rule_id")
    available_exemplars = _ids(adapter, "canonical_exemplars", "exemplar_id")
    available_scenarios = _ids(
        adapter, "validation_scenarios", "scenario_id"
    )
    if not rule_ids:
        errors.append(f"{label}.ui_impact.rule_ids must select adapter rules")
    if not exemplar_ids:
        errors.append(f"{label}.ui_impact.exemplar_ids must select an exemplar")
    if not scenario_ids:
        errors.append(
            f"{label}.ui_impact.validation_scenario_ids must select validation"
        )
    for selected, available, item_label in (
        (rule_ids, available_rules, "rule"),
        (exemplar_ids, available_exemplars, "exemplar"),
        (scenario_ids, available_scenarios, "validation scenario"),
    ):
        unknown = sorted(set(selected) - available)
        if unknown:
            errors.append(
                f"{label}.ui_impact selects unknown {item_label} ids: "
                + ", ".join(unknown)
            )

    if UI_ADAPTER_RELATIVE in {
        Path(path) for path in planned_path_texts if isinstance(path, str)
    }:
        errors.append(f"{label} may not mutate its UI Production Adapter authority")
    return binding


def markdown_ui_contract(binding: UiImpactBinding) -> tuple[str, ...]:
    """Return exact Markdown lines required for a UI-changing plan."""

    if not binding.touches_ui:
        return ()
    return (
        "## UI realization contract",
        f"- UI adapter: `{binding.adapter_path}`",
        f"- UI adapter SHA-256: `{binding.adapter_sha256}`",
        f"- UI rules: `{', '.join(binding.rule_ids)}`",
        f"- UI exemplars: `{', '.join(binding.exemplar_ids)}`",
        "- UI validation scenarios: "
        f"`{', '.join(binding.validation_scenario_ids)}`",
    )
