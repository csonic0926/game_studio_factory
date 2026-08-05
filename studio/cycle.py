#!/usr/bin/env python3
"""Validate the Studio's Idea-to-gameplay-system transition.

The Studio may reduce content or production breadth, but it may not turn a
product causal thesis into a one-way feature sequence.  This module validates
one game-owned system graph, an explicit two-lap witness, and two independent
reviews before a bounded Gameplay Factory unit may be selected.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    from studio.product import require_active_product_authority
except ModuleNotFoundError:  # pragma: no cover - direct script invocation.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from studio.product import require_active_product_authority  # type: ignore[no-redef]


FACTORY_ROOT = Path(__file__).resolve().parents[1]
SYSTEM_VERSION = "studio_gameplay_system.v1"
REVIEW_VERSION = "studio_gameplay_system_review.v1"
MANIFEST_VERSION = "studio_gameplay_system_manifest.v1"
READY = "STUDIO_GAMEPLAY_SYSTEM_READY"
BLOCKED = "BLOCKED_BY_LINEAR_GAMEPLAY"

ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
REVISION_PATTERN = re.compile(r"^[0-9a-f]{7,64}$")

REQUIRED_PHASES = {
    "PLAYER_DECISION",
    "COMMITMENT",
    "RESOLUTION",
    "REWARD",
    "REINVESTMENT",
    "RETURN",
}
REVIEW_ROLES = {"PRODUCT_FIDELITY", "CYCLE_CLOSURE"}
REQUIRED_CYCLE_FINDINGS = {
    "closed_graph",
    "reward_changes_next_decision",
    "second_lap_materially_differs",
    "coupled_systems_preserved",
    "no_proxy_loop",
}


class CycleValidationError(ValueError):
    """Raised for path/JSON failures that make validation impossible."""


@dataclass
class CycleValidationResult:
    status: str
    errors: list[str] = field(default_factory=list)
    system_id: str = ""
    cycle_id: str = ""
    feedback_state_ids: list[str] = field(default_factory=list)
    manifest_path: str = ""
    manifest_sha256: str = ""


def _json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise CycleValidationError(f"cannot read {label}: {error}") from error
    if not isinstance(payload, dict):
        raise CycleValidationError(f"{label} must be a JSON object")
    return payload


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def current_factory_revision(factory_root: Path = FACTORY_ROOT) -> str:
    result = subprocess.run(
        ["git", "-C", str(factory_root), "rev-parse", "HEAD"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    revision = result.stdout.strip()
    if result.returncode != 0 or REVISION_PATTERN.fullmatch(revision) is None:
        raise CycleValidationError(
            result.stderr.strip() or "Factory checkout has no readable HEAD"
        )
    return revision


def _keys(value: Any, label: str, required: set[str], errors: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object")
        return {}
    for key in sorted(required - set(value)):
        errors.append(f"{label} is missing {key}")
    for key in sorted(set(value) - required):
        errors.append(f"{label} contains unsupported field {key}")
    return value


def _text(value: Any, label: str, errors: list[str]) -> str:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label} must be a non-empty string")
        return ""
    result = value.strip()
    if "TBD" in result:
        errors.append(f"{label} must not contain TBD")
    return result


def _identifier(value: Any, label: str, errors: list[str]) -> str:
    result = _text(value, label, errors)
    if result and ID_PATTERN.fullmatch(result) is None:
        errors.append(f"{label} must match {ID_PATTERN.pattern}")
    return result


def _strings(value: Any, label: str, errors: list[str], *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list):
        errors.append(f"{label} must be an array")
        return []
    if not value and not allow_empty:
        errors.append(f"{label} must not be empty")
    result = [_text(item, f"{label}[{index}]", errors) for index, item in enumerate(value)]
    result = [item for item in result if item]
    if len(result) != len(set(result)):
        errors.append(f"{label} must not contain duplicates")
    return result


def _ids(value: Any, label: str, errors: list[str], *, allow_empty: bool = False) -> list[str]:
    result = _strings(value, label, errors, allow_empty=allow_empty)
    for index, item in enumerate(result):
        if ID_PATTERN.fullmatch(item) is None:
            errors.append(f"{label}[{index}] must match {ID_PATTERN.pattern}")
    return result


def _resolve_ref(
    game_repo: Path,
    value: Any,
    label: str,
    errors: list[str],
) -> tuple[dict[str, str], Path | None]:
    payload = _keys(value, label, {"path", "sha256"}, errors)
    path_text = _text(payload.get("path"), f"{label}.path", errors)
    digest = _text(payload.get("sha256"), f"{label}.sha256", errors)
    ref = {"path": path_text, "sha256": digest}
    if not path_text or not digest:
        return ref, None
    relative = Path(path_text)
    if relative.is_absolute():
        errors.append(f"{label}.path must be game-repo-relative")
        return ref, None
    path = (game_repo / relative).resolve()
    try:
        path.relative_to(game_repo)
    except ValueError:
        errors.append(f"{label}.path escapes the game repo")
        return ref, None
    if not path.is_file():
        errors.append(f"{label}.path does not identify a file: {path_text}")
        return ref, None
    if SHA256_PATTERN.fullmatch(digest) is None:
        errors.append(f"{label}.sha256 must be 64 lowercase hex characters")
    elif _sha256(path) != digest:
        errors.append(f"{label} hash does not match {path_text}")
    return ref, path


def _product_authority(
    game_repo: Path,
    product_ref: Any,
    input_ref: Any,
    constraints_ref: Any,
    errors: list[str],
) -> tuple[dict[str, str], dict[str, str], dict[str, str], set[str], set[str]]:
    product, product_path = _resolve_ref(game_repo, product_ref, "product_authority", errors)
    product_input, input_path = _resolve_ref(game_repo, input_ref, "product_input", errors)
    constraints, constraints_path = _resolve_ref(
        game_repo, constraints_ref, "factory_constraints", errors
    )
    if product.get("path") != "design/product/PRODUCT_THESIS.md":
        errors.append("product_authority.path must be design/product/PRODUCT_THESIS.md")
    if product_input.get("path") != "design/product/idea/PRODUCT_THESIS_INPUT.json":
        errors.append(
            "product_input.path must be design/product/idea/PRODUCT_THESIS_INPUT.json"
        )
    if constraints.get("path") != "design/product/FACTORY_CONSTRAINTS.json":
        errors.append(
            "factory_constraints.path must be design/product/FACTORY_CONSTRAINTS.json"
        )
    _, lifecycle_errors = require_active_product_authority(game_repo, product)
    errors.extend(lifecycle_errors)

    causal_ids: set[str] = set()
    if input_path is not None:
        payload = _json(input_path, "Product Thesis input")
        links = payload.get("causal_links")
        if not isinstance(links, list) or not links:
            errors.append("Product Thesis input must contain causal_links")
        else:
            for index, item in enumerate(links):
                if not isinstance(item, dict):
                    errors.append(f"product causal_links[{index}] must be an object")
                    continue
                link_id = _identifier(
                    item.get("link_id"), f"product causal_links[{index}].link_id", errors
                )
                if link_id:
                    causal_ids.add(link_id)

    constraint_ids: set[str] = set()
    if constraints_path is not None:
        payload = _json(constraints_path, "Factory constraints")
        if product_input and payload.get("source_input_sha256") != product_input.get("sha256"):
            errors.append("Factory constraints do not bind the exact Product Thesis input")
        constraints_list = payload.get("constraints")
        if not isinstance(constraints_list, list):
            errors.append("Factory constraints must contain constraints")
        else:
            for index, item in enumerate(constraints_list):
                if not isinstance(item, dict):
                    errors.append(f"factory constraints[{index}] must be an object")
                    continue
                factories = item.get("factories")
                if not isinstance(factories, list):
                    continue
                if "all" in factories or "gameplay" in factories:
                    constraint_id = _identifier(
                        item.get("constraint_id"),
                        f"factory constraints[{index}].constraint_id",
                        errors,
                    )
                    if constraint_id:
                        constraint_ids.add(constraint_id)

    if product_path is not None and product_input and input_path is not None:
        product_text = product_path.read_text(encoding="utf-8")
        for link_id in causal_ids:
            if f"`{link_id}`" not in product_text:
                errors.append(f"Product Thesis is missing causal link {link_id}")
    return product, product_input, constraints, causal_ids, constraint_ids


def _validate_system(
    game_repo: Path,
    path: Path,
    *,
    factory_revision: str,
    errors: list[str],
) -> dict[str, Any]:
    payload = _json(path, "Studio gameplay system")
    required = {
        "schema_version", "status", "system_id", "cycle_id", "project_id",
        "factory_revision", "product_authority", "product_input",
        "factory_constraints", "author_context_id", "system_promise",
        "core_player_verbs", "stages", "state_objects", "transitions",
        "cycle_path", "feedback_state_ids", "coupled_systems",
        "causal_link_coverage", "constraint_coverage", "two_lap_witness",
        "forbidden_linearizations", "authored_at",
    }
    _keys(payload, "Studio gameplay system", required, errors)
    if payload.get("schema_version") != SYSTEM_VERSION:
        errors.append(f"Studio gameplay system schema_version must be {SYSTEM_VERSION}")
    if payload.get("status") != READY:
        errors.append(f"Studio gameplay system status must be {READY}")
    if payload.get("factory_revision") != factory_revision:
        errors.append("Studio gameplay system factory_revision does not match manifest")
    system_id = _identifier(payload.get("system_id"), "system_id", errors)
    _identifier(payload.get("cycle_id"), "cycle_id", errors)
    _identifier(payload.get("project_id"), "project_id", errors)
    author_context_id = _identifier(
        payload.get("author_context_id"), "author_context_id", errors
    )
    system_promise = _text(payload.get("system_promise"), "system_promise", errors)
    if len(system_promise) > 160:
        errors.append("system_promise exceeds the compact decision-card limit of 160 characters")
    _ids(payload.get("core_player_verbs"), "core_player_verbs", errors)
    _text(payload.get("authored_at"), "authored_at", errors)

    product_ref, input_ref, constraints_ref, causal_ids, constraint_ids = _product_authority(
        game_repo,
        payload.get("product_authority"),
        payload.get("product_input"),
        payload.get("factory_constraints"),
        errors,
    )

    raw_stages = payload.get("stages")
    if not isinstance(raw_stages, list) or len(raw_stages) < 2:
        errors.append("stages must contain at least two stages")
        raw_stages = []
    stage_ids: set[str] = set()
    for index, item in enumerate(raw_stages):
        stage = _keys(item, f"stages[{index}]", {"stage_id", "player_goal"}, errors)
        stage_id = _identifier(stage.get("stage_id"), f"stages[{index}].stage_id", errors)
        _text(stage.get("player_goal"), f"stages[{index}].player_goal", errors)
        if stage_id in stage_ids:
            errors.append(f"duplicate stage_id: {stage_id}")
        stage_ids.add(stage_id)

    raw_states = payload.get("state_objects")
    if not isinstance(raw_states, list) or not raw_states:
        errors.append("state_objects must not be empty")
        raw_states = []
    state_ids: set[str] = set()
    visible_state_ids: set[str] = set()
    for index, item in enumerate(raw_states):
        state = _keys(
            item,
            f"state_objects[{index}]",
            {"state_id", "kind", "owner", "player_visible", "meaning"},
            errors,
        )
        state_id = _identifier(
            state.get("state_id"), f"state_objects[{index}].state_id", errors
        )
        if state_id in state_ids:
            errors.append(f"duplicate state_id: {state_id}")
        state_ids.add(state_id)
        if state.get("kind") not in {
            "RESOURCE", "PROGRESSION", "SOCIAL", "CONTENT", "COMMITMENT",
            "EXTERNAL", "RECORD", "CAPABILITY",
        }:
            errors.append(f"state_objects[{index}].kind is unsupported")
        _text(state.get("owner"), f"state_objects[{index}].owner", errors)
        if not isinstance(state.get("player_visible"), bool):
            errors.append(f"state_objects[{index}].player_visible must be boolean")
        elif state["player_visible"]:
            visible_state_ids.add(state_id)
        _text(state.get("meaning"), f"state_objects[{index}].meaning", errors)

    raw_transitions = payload.get("transitions")
    if not isinstance(raw_transitions, list) or not raw_transitions:
        errors.append("transitions must not be empty")
        raw_transitions = []
    transitions: dict[str, dict[str, Any]] = {}
    phases: set[str] = set()
    for index, item in enumerate(raw_transitions):
        transition = _keys(
            item,
            f"transitions[{index}]",
            {
                "transition_id", "from_stage_id", "to_stage_id", "phase",
                "player_action", "reads_state_ids", "writes_state_ids",
                "visible_consequence", "motivation_effect",
                "causal_link_ids", "constraint_ids",
            },
            errors,
        )
        transition_id = _identifier(
            transition.get("transition_id"),
            f"transitions[{index}].transition_id",
            errors,
        )
        if transition_id in transitions:
            errors.append(f"duplicate transition_id: {transition_id}")
        transitions[transition_id] = transition
        for field in ("from_stage_id", "to_stage_id"):
            stage_id = _identifier(
                transition.get(field), f"transitions[{index}].{field}", errors
            )
            if stage_id and stage_id not in stage_ids:
                errors.append(f"transitions[{index}].{field} is unknown: {stage_id}")
        phase = _text(transition.get("phase"), f"transitions[{index}].phase", errors)
        phases.add(phase)
        if phase not in REQUIRED_PHASES | {"READ", "PLAYER_GOAL", "PRESENTATION"}:
            errors.append(f"transitions[{index}].phase is unsupported")
        _text(transition.get("player_action"), f"transitions[{index}].player_action", errors)
        reads = set(_ids(
            transition.get("reads_state_ids"),
            f"transitions[{index}].reads_state_ids",
            errors,
            allow_empty=True,
        ))
        writes = set(_ids(
            transition.get("writes_state_ids"),
            f"transitions[{index}].writes_state_ids",
            errors,
            allow_empty=True,
        ))
        for state_id in reads | writes:
            if state_id not in state_ids:
                errors.append(f"transitions[{index}] references unknown state {state_id}")
        _text(
            transition.get("visible_consequence"),
            f"transitions[{index}].visible_consequence",
            errors,
        )
        _text(
            transition.get("motivation_effect"),
            f"transitions[{index}].motivation_effect",
            errors,
        )
        projection_text = " -> ".join(
            str(transition.get(field, ""))
            for field in ("player_action", "visible_consequence", "motivation_effect")
        )
        if len(projection_text) > 300:
            errors.append(
                f"transitions[{index}] exceeds the compact decision-card projection limit"
            )
        transition_causal = set(_ids(
            transition.get("causal_link_ids"),
            f"transitions[{index}].causal_link_ids",
            errors,
            allow_empty=True,
        ))
        transition_constraints = set(_ids(
            transition.get("constraint_ids"),
            f"transitions[{index}].constraint_ids",
            errors,
            allow_empty=True,
        ))
        if not transition_causal.issubset(causal_ids):
            errors.append(f"transitions[{index}] references unknown product causal link")
        if not transition_constraints.issubset(constraint_ids):
            errors.append(f"transitions[{index}] references unknown Factory constraint")

    missing_phases = sorted(REQUIRED_PHASES - phases)
    if missing_phases:
        errors.append("cycle is missing required phases: " + ", ".join(missing_phases))

    cycle_path = _ids(payload.get("cycle_path"), "cycle_path", errors)
    if len(cycle_path) > 10:
        errors.append("cycle_path exceeds the compact decision-card limit of 10 transitions")
    if len(cycle_path) != len(set(cycle_path)):
        errors.append("cycle_path must not repeat transitions inside one lap")
    for transition_id in cycle_path:
        if transition_id not in transitions:
            errors.append(f"cycle_path references unknown transition {transition_id}")
    if cycle_path and all(item in transitions for item in cycle_path):
        for left_id, right_id in zip(cycle_path, cycle_path[1:]):
            if transitions[left_id].get("to_stage_id") != transitions[right_id].get("from_stage_id"):
                errors.append(f"cycle_path is disconnected between {left_id} and {right_id}")
        first = transitions[cycle_path[0]]
        last = transitions[cycle_path[-1]]
        if last.get("to_stage_id") != first.get("from_stage_id"):
            errors.append("cycle_path does not close back to its starting stage")
        path_phases = {str(transitions[item].get("phase", "")) for item in cycle_path}
        missing_path_phases = sorted(REQUIRED_PHASES - path_phases)
        if missing_path_phases:
            errors.append(
                "cycle_path omits required phases: " + ", ".join(missing_path_phases)
            )

    feedback_state_ids = set(_ids(
        payload.get("feedback_state_ids"), "feedback_state_ids", errors
    ))
    if not feedback_state_ids.issubset(state_ids):
        errors.append("feedback_state_ids reference unknown state objects")
    if not feedback_state_ids.issubset(visible_state_ids):
        errors.append("every feedback state must be player-visible")
    reward_writes: set[str] = set()
    reinvest_writes: set[str] = set()
    decision_reads: set[str] = set()
    cycle_transitions = [
        transitions[item] for item in cycle_path if item in transitions
    ]
    for transition in cycle_transitions:
        phase = transition.get("phase")
        writes = set(transition.get("writes_state_ids", []))
        reads = set(transition.get("reads_state_ids", []))
        if phase == "REWARD":
            reward_writes |= writes
        elif phase == "REINVESTMENT":
            reinvest_writes |= writes
        elif phase == "PLAYER_DECISION":
            decision_reads |= reads
    if not feedback_state_ids.issubset(reward_writes | reinvest_writes):
        errors.append("feedback states must be written by reward or reinvestment")
    if feedback_state_ids and not (feedback_state_ids & reward_writes):
        errors.append(
            "at least one feedback state must be written by REWARD; "
            "reinvestment cannot fabricate the reward edge"
        )
    if not feedback_state_ids.issubset(decision_reads):
        errors.append("feedback states must be read by the next player decision")

    raw_coupled = payload.get("coupled_systems")
    if not isinstance(raw_coupled, list) or not raw_coupled:
        errors.append("coupled_systems must not be empty")
        raw_coupled = []
    if len(raw_coupled) > 8:
        errors.append("coupled_systems exceeds the compact decision-card limit of 8")
    coupled_ids: set[str] = set()
    for index, item in enumerate(raw_coupled):
        coupled = _keys(
            item,
            f"coupled_systems[{index}]",
            {"component_id", "role", "transition_ids", "required_in_first_baseline"},
            errors,
        )
        component_id = _identifier(
            coupled.get("component_id"), f"coupled_systems[{index}].component_id", errors
        )
        if component_id in coupled_ids:
            errors.append(f"duplicate coupled component_id: {component_id}")
        coupled_ids.add(component_id)
        role = _text(coupled.get("role"), f"coupled_systems[{index}].role", errors)
        if len(role) > 180:
            errors.append(f"coupled_systems[{index}].role exceeds 180 characters")
        ids = _ids(
            coupled.get("transition_ids"), f"coupled_systems[{index}].transition_ids", errors
        )
        if not set(ids).issubset(set(transitions)):
            errors.append(f"coupled_systems[{index}] references unknown transitions")
        if not set(ids).issubset(set(cycle_path)):
            errors.append(
                f"coupled_systems[{index}] is not fully realized inside cycle_path"
            )
        if coupled.get("required_in_first_baseline") is not True:
            errors.append(
                f"coupled_systems[{index}] must be required in the first baseline; "
                "bounded scope cannot defer a load-bearing system"
            )

    def coverage_ids(field: str, expected: set[str]) -> None:
        raw = payload.get(field)
        if not isinstance(raw, list):
            errors.append(f"{field} must be an array")
            return
        seen: set[str] = set()
        key = "link_id" if field == "causal_link_coverage" else "constraint_id"
        for index, item in enumerate(raw):
            coverage = _keys(
                item,
                f"{field}[{index}]",
                {key, "transition_ids", "status"},
                errors,
            )
            item_id = _identifier(coverage.get(key), f"{field}[{index}].{key}", errors)
            seen.add(item_id)
            ids = _ids(
                coverage.get("transition_ids"),
                f"{field}[{index}].transition_ids",
                errors,
            )
            if not set(ids).issubset(set(transitions)):
                errors.append(f"{field}[{index}] references unknown transitions")
            if not set(ids).issubset(set(cycle_path)):
                errors.append(f"{field}[{index}] is not realized inside cycle_path")
            if coverage.get("status") != "REALIZED_IN_CYCLE":
                errors.append(f"{field}[{index}].status must be REALIZED_IN_CYCLE")
        if seen != expected:
            missing = sorted(expected - seen)
            extra = sorted(seen - expected)
            if missing:
                errors.append(f"{field} is missing: " + ", ".join(missing))
            if extra:
                errors.append(f"{field} has unknown ids: " + ", ".join(extra))

    coverage_ids("causal_link_coverage", causal_ids)
    coverage_ids("constraint_coverage", constraint_ids)

    witness = _keys(
        payload.get("two_lap_witness"),
        "two_lap_witness",
        {"lap_one", "feedback_state_deltas", "lap_two", "why_second_lap_is_not_repetition"},
        errors,
    )
    for lap_name in ("lap_one", "lap_two"):
        lap = _keys(
            witness.get(lap_name),
            f"two_lap_witness.{lap_name}",
            {"player_goal", "decision", "resolution", "resulting_state"},
            errors,
        )
        for field in ("player_goal", "decision", "resolution", "resulting_state"):
            _text(lap.get(field), f"two_lap_witness.{lap_name}.{field}", errors)
    deltas = witness.get("feedback_state_deltas")
    if not isinstance(deltas, list) or not deltas:
        errors.append("two_lap_witness.feedback_state_deltas must not be empty")
        deltas = []
    delta_ids: set[str] = set()
    for index, item in enumerate(deltas):
        delta = _keys(
            item,
            f"two_lap_witness.feedback_state_deltas[{index}]",
            {"state_id", "before", "after", "effect_on_next_decision"},
            errors,
        )
        state_id = _identifier(
            delta.get("state_id"),
            f"two_lap_witness.feedback_state_deltas[{index}].state_id",
            errors,
        )
        delta_ids.add(state_id)
        for field in ("before", "after", "effect_on_next_decision"):
            _text(
                delta.get(field),
                f"two_lap_witness.feedback_state_deltas[{index}].{field}",
                errors,
            )
        if delta.get("before") == delta.get("after"):
            errors.append(
                f"two_lap_witness.feedback_state_deltas[{index}] has no state change"
            )
    if delta_ids != feedback_state_ids:
        errors.append("two-lap state deltas must exactly cover feedback_state_ids")
    _text(
        witness.get("why_second_lap_is_not_repetition"),
        "two_lap_witness.why_second_lap_is_not_repetition",
        errors,
    )
    forbidden = _strings(
        payload.get("forbidden_linearizations"),
        "forbidden_linearizations",
        errors,
    )
    if len(forbidden) > 6:
        errors.append("forbidden_linearizations exceeds the compact decision-card limit of 6")
    for index, text in enumerate(forbidden):
        if len(text) > 180:
            errors.append(f"forbidden_linearizations[{index}] exceeds 180 characters")

    payload["_validated"] = {
        "system_id": system_id,
        "author_context_id": author_context_id,
        "product_ref": product_ref,
        "input_ref": input_ref,
        "constraints_ref": constraints_ref,
        "causal_ids": causal_ids,
        "constraint_ids": constraint_ids,
        "transition_ids": set(transitions),
        "feedback_state_ids": feedback_state_ids,
    }
    return payload


def _validate_review(
    game_repo: Path,
    path: Path,
    *,
    expected_role: str,
    factory_revision: str,
    system_ref: dict[str, str],
    system: dict[str, Any],
    errors: list[str],
) -> str:
    payload = _json(path, f"{expected_role} gameplay system review")
    required = {
        "schema_version", "review_id", "review_role", "project_id", "system_id",
        "cycle_id", "factory_revision", "gameplay_system", "reviewer_context_id",
        "reviewer_freshness", "causal_link_ids_reviewed",
        "constraint_ids_reviewed", "transition_ids_reviewed", "cycle_findings",
        "blocking_findings", "verdict", "reviewed_at",
    }
    _keys(payload, f"{expected_role} review", required, errors)
    if payload.get("schema_version") != REVIEW_VERSION:
        errors.append(f"{expected_role} review schema_version must be {REVIEW_VERSION}")
    if payload.get("review_role") != expected_role:
        errors.append(f"review_role must be {expected_role}")
    if payload.get("factory_revision") != factory_revision:
        errors.append(f"{expected_role} review factory_revision does not match")
    if payload.get("project_id") != system.get("project_id"):
        errors.append(f"{expected_role} review project_id does not match")
    if payload.get("system_id") != system.get("system_id"):
        errors.append(f"{expected_role} review system_id does not match")
    if payload.get("cycle_id") != system.get("cycle_id"):
        errors.append(f"{expected_role} review cycle_id does not match")
    _identifier(payload.get("review_id"), f"{expected_role} review_id", errors)
    reviewer = _identifier(
        payload.get("reviewer_context_id"),
        f"{expected_role} reviewer_context_id",
        errors,
    )
    if payload.get("reviewer_freshness") != "FRESH":
        errors.append(f"{expected_role} reviewer_freshness must be FRESH")
    review_system_ref, _ = _resolve_ref(
        game_repo, payload.get("gameplay_system"), f"{expected_role}.gameplay_system", errors
    )
    if review_system_ref != system_ref:
        errors.append(f"{expected_role} review does not bind the exact gameplay system")
    validated = system.get("_validated", {})
    causal = set(_ids(
        payload.get("causal_link_ids_reviewed"),
        f"{expected_role}.causal_link_ids_reviewed",
        errors,
        allow_empty=expected_role == "CYCLE_CLOSURE",
    ))
    constraints = set(_ids(
        payload.get("constraint_ids_reviewed"),
        f"{expected_role}.constraint_ids_reviewed",
        errors,
        allow_empty=expected_role == "CYCLE_CLOSURE",
    ))
    transitions = set(_ids(
        payload.get("transition_ids_reviewed"),
        f"{expected_role}.transition_ids_reviewed",
        errors,
    ))
    if expected_role == "PRODUCT_FIDELITY":
        if causal != validated.get("causal_ids", set()):
            errors.append("PRODUCT_FIDELITY review must cover every product causal link")
        if constraints != validated.get("constraint_ids", set()):
            errors.append("PRODUCT_FIDELITY review must cover every applicable constraint")
    if transitions != validated.get("transition_ids", set()):
        errors.append(f"{expected_role} review must cover every system transition")
    findings = _keys(
        payload.get("cycle_findings"),
        f"{expected_role}.cycle_findings",
        REQUIRED_CYCLE_FINDINGS,
        errors,
    )
    for finding in REQUIRED_CYCLE_FINDINGS:
        if findings.get(finding) != "PASS":
            errors.append(f"{expected_role}.cycle_findings.{finding} must be PASS")
    if payload.get("blocking_findings") != []:
        errors.append(f"{expected_role}.blocking_findings must be empty")
    if payload.get("verdict") != "PASS_SYSTEM_REVIEW":
        errors.append(f"{expected_role}.verdict must be PASS_SYSTEM_REVIEW")
    _text(payload.get("reviewed_at"), f"{expected_role}.reviewed_at", errors)
    return reviewer


def validate_gameplay_system(
    game_repo_text: str,
    manifest_text: str,
    *,
    expected_factory_revision: str | None = None,
) -> CycleValidationResult:
    game_repo = Path(game_repo_text).expanduser().resolve()
    if not game_repo.is_dir():
        raise CycleValidationError(f"game repo does not exist: {game_repo}")
    manifest_candidate = Path(manifest_text).expanduser()
    manifest_path = (
        manifest_candidate
        if manifest_candidate.is_absolute()
        else game_repo / manifest_candidate
    ).resolve()
    try:
        manifest_path.relative_to(game_repo)
    except ValueError as error:
        raise CycleValidationError("manifest path escapes the game repo") from error
    if not manifest_path.is_file():
        raise CycleValidationError(f"manifest does not exist: {manifest_text}")

    errors: list[str] = []
    manifest = _json(manifest_path, "Studio gameplay system manifest")
    required = {
        "schema_version", "status", "project_id", "system_id", "cycle_id",
        "factory_revision", "gameplay_system", "reviews",
    }
    _keys(manifest, "Studio gameplay system manifest", required, errors)
    if manifest.get("schema_version") != MANIFEST_VERSION:
        errors.append(f"manifest schema_version must be {MANIFEST_VERSION}")
    if manifest.get("status") != READY:
        errors.append(f"manifest status must be {READY}")
    factory_revision = _text(
        manifest.get("factory_revision"), "manifest.factory_revision", errors
    )
    actual_revision = expected_factory_revision or current_factory_revision()
    if factory_revision != actual_revision:
        errors.append("manifest factory_revision does not match the active Factory")
    system_id = _identifier(manifest.get("system_id"), "manifest.system_id", errors)
    cycle_id = _identifier(manifest.get("cycle_id"), "manifest.cycle_id", errors)
    _identifier(manifest.get("project_id"), "manifest.project_id", errors)
    system_ref, system_path = _resolve_ref(
        game_repo, manifest.get("gameplay_system"), "manifest.gameplay_system", errors
    )
    system: dict[str, Any] = {}
    if system_path is not None:
        system = _validate_system(
            game_repo,
            system_path,
            factory_revision=factory_revision,
            errors=errors,
        )
        if system.get("system_id") != system_id:
            errors.append("manifest system_id does not match gameplay system")
        if system.get("cycle_id") != cycle_id:
            errors.append("manifest cycle_id does not match gameplay system")
        if system.get("project_id") != manifest.get("project_id"):
            errors.append("manifest project_id does not match gameplay system")

    reviews = _keys(
        manifest.get("reviews"),
        "manifest.reviews",
        {"product_fidelity", "cycle_closure"},
        errors,
    )
    reviewers: list[str] = []
    for key, role in (
        ("product_fidelity", "PRODUCT_FIDELITY"),
        ("cycle_closure", "CYCLE_CLOSURE"),
    ):
        _, review_path = _resolve_ref(
            game_repo, reviews.get(key), f"manifest.reviews.{key}", errors
        )
        if review_path is not None and system:
            reviewers.append(
                _validate_review(
                    game_repo,
                    review_path,
                    expected_role=role,
                    factory_revision=factory_revision,
                    system_ref=system_ref,
                    system=system,
                    errors=errors,
                )
            )
    author = system.get("_validated", {}).get("author_context_id") if system else ""
    if len(reviewers) == 2:
        if reviewers[0] == reviewers[1]:
            errors.append("product-fidelity and cycle-closure reviewers must be different")
        if author and author in reviewers:
            errors.append("gameplay system author cannot review the system")

    relative_manifest = manifest_path.relative_to(game_repo).as_posix()
    return CycleValidationResult(
        READY if not errors else BLOCKED,
        errors=errors,
        system_id=system_id,
        cycle_id=cycle_id,
        feedback_state_ids=sorted(
            system.get("_validated", {}).get("feedback_state_ids", set())
        ) if system else [],
        manifest_path=relative_manifest,
        manifest_sha256=_sha256(manifest_path),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["validate"])
    parser.add_argument("--game-repo", required=True)
    parser.add_argument("--manifest", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = validate_gameplay_system(args.game_repo, args.manifest)
    except CycleValidationError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(result.status)
    for error in result.errors:
        print(f"ERROR: {error}")
    return 0 if result.status == READY else 1


if __name__ == "__main__":
    raise SystemExit(main())
