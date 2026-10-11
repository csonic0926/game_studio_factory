"""Shared validation for UI-changing Gameplay Factory production plans.

The feature/design artifact says what the player should experience.  This
module prevents a planner from silently inventing how an established game
repository constructs UI: every UI-changing plan must bind the exact
game-owned UI Production Adapter, enumerate the complete style blast radius,
map every target to accepted exemplars, and select separate structural-fit and
visual-consistency validation scenarios from it.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


UI_ADAPTER_SCHEMA_VERSION = "ui_production_adapter.v2"
UI_ADAPTER_STATUS = "UI_PRODUCTION_ADAPTER_READY"
UI_RESULT_SCHEMA_VERSION = "ui_production_adapter_result.v2"
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
    "panel",
    "panels",
    "button",
    "buttons",
    "theme",
    "themes",
    "stylebox",
    "widget",
    "widgets",
}
STYLE_BLAST_RADIUS_SCOPE = (
    "ALL_UI_CONTROLS_IN_CHANGE_AND_REOPENED_STYLE_BATCH"
)
STYLE_CHANGE_KINDS = {
    "NEW_CONTROL",
    "MODIFIED_CONTROL",
    "REOPENED_BATCH_CONTROL",
}
STYLE_DISPOSITIONS = {"IMPLEMENT_STYLE_CHANGE", "VERIFIED_CONSISTENT"}
MECHANICAL_VISUAL_METHODS = {
    "RESOURCE_IDENTITY",
    "RESOURCE_PROPERTY_EQUALITY",
    "COMPUTED_STYLE_EQUALITY",
}
GODOT_VISUAL_METHODS = {"RESOURCE_IDENTITY", "RESOURCE_PROPERTY_EQUALITY"}


@dataclass(frozen=True)
class UiStyleTarget:
    target_id: str
    target_path: str
    control_ids: tuple[str, ...]
    change_kind: str
    disposition: str
    reference_exemplar_ids: tuple[str, ...]
    visual_rule_ids: tuple[str, ...]
    structural_validation_scenario_ids: tuple[str, ...]
    visual_validation_scenario_ids: tuple[str, ...]


@dataclass(frozen=True)
class UiImpactBinding:
    touches_ui: bool = False
    adapter_path: str = ""
    adapter_sha256: str = ""
    rule_ids: tuple[str, ...] = ()
    exemplar_ids: tuple[str, ...] = ()
    validation_scenario_ids: tuple[str, ...] = ()
    style_blast_radius_scope: str = ""
    style_blast_radius: tuple[UiStyleTarget, ...] = ()


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


def _by_id(
    payload: dict[str, Any], field: str, id_field: str
) -> dict[str, dict[str, Any]]:
    values = payload.get(field)
    if not isinstance(values, list):
        return {}
    return {
        item[id_field]: item
        for item in values
        if isinstance(item, dict)
        and isinstance(item.get(id_field), str)
        and item[id_field]
    }


def _portable_target_path(
    game_repo: Path,
    value: Any,
    label: str,
    errors: list[str],
) -> str:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label} must be a non-empty string")
        return ""
    path_text = value.strip()
    path = Path(path_text)
    if path.is_absolute():
        errors.append(f"{label} must be game-repo-relative")
        return path_text
    resolved = (game_repo / path).resolve()
    try:
        resolved.relative_to(game_repo.resolve())
    except ValueError:
        errors.append(f"{label} escapes the game repo")
    return path_text


def _normalize_style_blast_radius(
    *,
    game_repo: Path,
    value: Any,
    planned_path_texts: list[str],
    label: str,
    errors: list[str],
) -> list[UiStyleTarget]:
    if not isinstance(value, list) or not value:
        errors.append(
            f"{label} must inventory every new, modified, and reopened-batch UI control"
        )
        return []
    result: list[UiStyleTarget] = []
    target_ids: set[str] = set()
    control_keys: set[tuple[str, str]] = set()
    planned = set(planned_path_texts)
    allowed_fields = {
        "target_id",
        "target_path",
        "control_ids",
        "change_kind",
        "disposition",
        "reference_exemplar_ids",
        "visual_rule_ids",
        "structural_validation_scenario_ids",
        "visual_validation_scenario_ids",
    }
    for index, raw in enumerate(value):
        item_label = f"{label}[{index}]"
        if not isinstance(raw, dict):
            errors.append(f"{item_label} must be an object")
            continue
        missing = sorted(allowed_fields - set(raw))
        extra = sorted(set(raw) - allowed_fields)
        if missing:
            errors.append(f"{item_label} lacks required fields: " + ", ".join(missing))
        if extra:
            errors.append(f"{item_label} has unsupported fields: " + ", ".join(extra))
        target_id = raw.get("target_id")
        if not isinstance(target_id, str) or not target_id.strip():
            errors.append(f"{item_label}.target_id must be a non-empty string")
            target_id = ""
        else:
            target_id = target_id.strip()
            if not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", target_id):
                errors.append(f"{item_label}.target_id must be a portable lowercase id")
        if target_id in target_ids:
            errors.append(f"{label} has duplicate target_id: {target_id}")
        target_ids.add(target_id)
        target_path = _portable_target_path(
            game_repo, raw.get("target_path"), f"{item_label}.target_path", errors
        )
        control_ids = _text_list(
            raw.get("control_ids"), f"{item_label}.control_ids", errors
        )
        if not control_ids:
            errors.append(f"{item_label}.control_ids must name affected controls")
        for control_id in control_ids:
            key = (target_path, control_id)
            if key in control_keys:
                errors.append(
                    f"{label} repeats control {control_id} in {target_path}"
                )
            control_keys.add(key)
        change_kind = raw.get("change_kind")
        if change_kind not in STYLE_CHANGE_KINDS:
            errors.append(f"{item_label}.change_kind has an unsupported value")
            change_kind = str(change_kind or "")
        disposition = raw.get("disposition")
        if disposition not in STYLE_DISPOSITIONS:
            errors.append(f"{item_label}.disposition has an unsupported value")
            disposition = str(disposition or "")
        if disposition == "IMPLEMENT_STYLE_CHANGE" and target_path not in planned:
            errors.append(
                f"{item_label} implements style changes but target_path is not planned"
            )
        if (
            disposition == "VERIFIED_CONSISTENT"
            and target_path
            and not (game_repo / target_path).is_file()
        ):
            errors.append(
                f"{item_label} cannot verify a target that does not yet exist"
            )
        result.append(
            UiStyleTarget(
                target_id=target_id,
                target_path=target_path,
                control_ids=tuple(control_ids),
                change_kind=change_kind,
                disposition=disposition,
                reference_exemplar_ids=tuple(
                    _text_list(
                        raw.get("reference_exemplar_ids"),
                        f"{item_label}.reference_exemplar_ids",
                        errors,
                    )
                ),
                visual_rule_ids=tuple(
                    _text_list(
                        raw.get("visual_rule_ids"),
                        f"{item_label}.visual_rule_ids",
                        errors,
                    )
                ),
                structural_validation_scenario_ids=tuple(
                    _text_list(
                        raw.get("structural_validation_scenario_ids"),
                        f"{item_label}.structural_validation_scenario_ids",
                        errors,
                    )
                ),
                visual_validation_scenario_ids=tuple(
                    _text_list(
                        raw.get("visual_validation_scenario_ids"),
                        f"{item_label}.visual_validation_scenario_ids",
                        errors,
                    )
                ),
            )
        )
    covered_paths = {target.target_path for target in result}
    missing_ui_paths = sorted(
        path for path in planned_path_texts if looks_like_ui_path(path) and path not in covered_paths
    )
    if missing_ui_paths:
        errors.append(
            f"{label} does not cover planned UI paths: " + ", ".join(missing_ui_paths)
        )
    return result


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

    exemplars = adapter.get("canonical_exemplars")
    if not isinstance(exemplars, list):
        return
    for exemplar in exemplars:
        provenance = (
            exemplar.get("acceptance_provenance")
            if isinstance(exemplar, dict)
            else None
        )
        if not isinstance(provenance, dict):
            errors.append(f"{label} UI exemplar lacks acceptance provenance")
            continue
        authority = provenance.get("authority")
        if authority == "USER_RULING":
            if not provenance.get("user_quote"):
                errors.append(f"{label} UI exemplar USER_RULING lacks its quote")
            continue
        if authority != "ACCEPTED_BASELINE":
            errors.append(f"{label} UI exemplar has unsupported provenance")
            continue
        path_text = provenance.get("accepted_baseline_path")
        declared = provenance.get("accepted_baseline_sha256")
        if not isinstance(path_text, str) or not path_text or not isinstance(declared, str):
            errors.append(f"{label} UI exemplar accepted-baseline provenance is incomplete")
            continue
        path = (game_repo / path_text).resolve()
        try:
            path.relative_to(game_repo.resolve())
        except ValueError:
            errors.append(f"{label} UI exemplar baseline path escapes the game repo")
            continue
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != declared:
            errors.append(
                f"{label} UI exemplar accepted baseline changed; refresh before planning: "
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
        "style_blast_radius_scope",
        "style_blast_radius",
    }
    extra_fields = sorted(set(raw_impact) - allowed_fields)
    missing_fields = sorted(allowed_fields - set(raw_impact))
    if missing_fields:
        errors.append(
            f"{label}.ui_impact lacks required fields: " + ", ".join(missing_fields)
        )
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
    style_scope = raw_impact.get("style_blast_radius_scope")
    if not isinstance(style_scope, str):
        errors.append(f"{label}.ui_impact.style_blast_radius_scope must be a string")
        style_scope = ""
    raw_style_blast_radius = raw_impact.get("style_blast_radius")

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
        style_blast_radius_scope=style_scope,
    )
    if not touches_ui:
        if (
            adapter_path
            or adapter_sha256
            or rule_ids
            or exemplar_ids
            or scenario_ids
            or style_scope
            or raw_style_blast_radius not in ([], None)
        ):
            errors.append(
                f"{label}.ui_impact must leave adapter, ids, and style blast radius empty when "
                "touches_ui=false"
            )
        return binding

    if style_scope != STYLE_BLAST_RADIUS_SCOPE:
        errors.append(
            f"{label}.ui_impact.style_blast_radius_scope must be "
            f"{STYLE_BLAST_RADIUS_SCOPE}"
        )
    style_targets = _normalize_style_blast_radius(
        game_repo=game_repo,
        value=raw_style_blast_radius,
        planned_path_texts=planned_path_texts,
        label=f"{label}.ui_impact.style_blast_radius",
        errors=errors,
    )
    binding = UiImpactBinding(
        touches_ui=True,
        adapter_path=adapter_path,
        adapter_sha256=adapter_sha256,
        rule_ids=tuple(rule_ids),
        exemplar_ids=tuple(exemplar_ids),
        validation_scenario_ids=tuple(scenario_ids),
        style_blast_radius_scope=style_scope,
        style_blast_radius=tuple(style_targets),
    )

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
    if adapter.get("visual_grammar_policy") != {
        "default_without_explicit_redesign": "PRESERVE_EXISTING_VISUAL_GRAMMAR",
        "redesign_requires": "USER_RULING",
    }:
        errors.append(
            f"{label} UI Production Adapter lacks the preserve-existing-visual-grammar default"
        )
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
                or result.get("schema_version") != UI_RESULT_SCHEMA_VERSION
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

    rules_by_id = _by_id(adapter, "rules", "rule_id")
    exemplars_by_id = _by_id(
        adapter, "canonical_exemplars", "exemplar_id"
    )
    scenarios_by_id = _by_id(
        adapter, "validation_scenarios", "scenario_id"
    )
    is_godot_project = (game_repo / "project.godot").is_file()
    for target in style_targets:
        target_label = (
            f"{label}.ui_impact.style_blast_radius target {target.target_id}"
        )
        if not target.reference_exemplar_ids:
            errors.append(f"{target_label} must map to an accepted exemplar")
        if not target.visual_rule_ids:
            errors.append(f"{target_label} must select VISUAL_GRAMMAR rules")
        if not target.structural_validation_scenario_ids:
            errors.append(f"{target_label} must select STRUCTURAL_FIT validation")
        if not target.visual_validation_scenario_ids:
            errors.append(f"{target_label} must select VISUAL_CONSISTENCY validation")
        for exemplar_id in target.reference_exemplar_ids:
            if exemplar_id not in exemplar_ids:
                errors.append(f"{target_label} references unknown exemplar: {exemplar_id}")
            if exemplar_id not in exemplar_ids:
                continue
            exemplar = exemplars_by_id.get(exemplar_id, {})
            provenance = exemplar.get("acceptance_provenance")
            if not isinstance(provenance, dict) or provenance.get("authority") not in {
                "ACCEPTED_BASELINE",
                "USER_RULING",
            }:
                errors.append(
                    f"{target_label} exemplar is not backed by accepted provenance: "
                    f"{exemplar_id}"
                )
            illustrated = exemplar.get("rules_illustrated")
            if not isinstance(illustrated, list) or not (
                set(illustrated) & set(target.visual_rule_ids)
            ):
                errors.append(
                    f"{target_label} exemplar does not illustrate its selected "
                    f"VISUAL_GRAMMAR rule: {exemplar_id}"
                )
        for rule_id in target.visual_rule_ids:
            rule = rules_by_id.get(rule_id)
            if rule is None:
                errors.append(f"{target_label} references unknown rule: {rule_id}")
            elif rule.get("category") != "VISUAL_GRAMMAR":
                errors.append(f"{target_label} rule is not VISUAL_GRAMMAR: {rule_id}")
        for scenario_id in target.structural_validation_scenario_ids:
            scenario = scenarios_by_id.get(scenario_id)
            if scenario is None:
                errors.append(
                    f"{target_label} references unknown validation scenario: {scenario_id}"
                )
            elif scenario.get("validation_kind") != "STRUCTURAL_FIT":
                errors.append(
                    f"{target_label} structural validation is not STRUCTURAL_FIT: "
                    f"{scenario_id}"
                )
        for scenario_id in target.visual_validation_scenario_ids:
            scenario = scenarios_by_id.get(scenario_id)
            if scenario is None:
                errors.append(
                    f"{target_label} references unknown validation scenario: {scenario_id}"
                )
                continue
            if scenario.get("validation_kind") != "VISUAL_CONSISTENCY":
                errors.append(
                    f"{target_label} visual validation is not VISUAL_CONSISTENCY: "
                    f"{scenario_id}"
                )
            methods = scenario.get("comparison_methods")
            method_set = set(methods) if isinstance(methods, list) else set()
            if not method_set & MECHANICAL_VISUAL_METHODS:
                errors.append(
                    f"{target_label} visual validation relies on screenshots without "
                    f"mechanical style comparison: {scenario_id}"
                )
            if is_godot_project and not method_set & GODOT_VISUAL_METHODS:
                errors.append(
                    f"{target_label} Godot visual validation must directly compare "
                    f"Theme/StyleBox resources or properties: {scenario_id}"
                )
        for selected, aggregate, selection_label in (
            (target.reference_exemplar_ids, set(exemplar_ids), "exemplar_ids"),
            (target.visual_rule_ids, set(rule_ids), "rule_ids"),
            (
                target.structural_validation_scenario_ids,
                set(scenario_ids),
                "validation_scenario_ids",
            ),
            (
                target.visual_validation_scenario_ids,
                set(scenario_ids),
                "validation_scenario_ids",
            ),
        ):
            missing = sorted(set(selected) - aggregate)
            if missing:
                errors.append(
                    f"{target_label} selections must also appear in top-level "
                    f"{selection_label}: " + ", ".join(missing)
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
    lines = [
        "## UI realization contract",
        f"- UI adapter: `{binding.adapter_path}`",
        f"- UI adapter SHA-256: `{binding.adapter_sha256}`",
        f"- UI rules: `{', '.join(binding.rule_ids)}`",
        f"- UI exemplars: `{', '.join(binding.exemplar_ids)}`",
        "- UI validation scenarios: "
        f"`{', '.join(binding.validation_scenario_ids)}`",
        "## UI style blast radius",
        f"- Scope: `{binding.style_blast_radius_scope}`",
    ]
    for target in binding.style_blast_radius:
        lines.append(
            f"- `{target.target_id}` — `{target.target_path}`; controls: "
            f"`{', '.join(target.control_ids)}`; change: `{target.change_kind}`; "
            f"disposition: `{target.disposition}`; references: "
            f"`{', '.join(target.reference_exemplar_ids)}`; visual rules: "
            f"`{', '.join(target.visual_rule_ids)}`; structural validation: "
            f"`{', '.join(target.structural_validation_scenario_ids)}`; "
            f"visual validation: "
            f"`{', '.join(target.visual_validation_scenario_ids)}`"
        )
    return tuple(lines)
