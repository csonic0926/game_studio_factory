"""Player-facing design and runtime evidence validators.

The objects in this module deliberately keep four different claims separate:

* a player-facing interaction has been concretely designed;
* an exact build produced visible interaction evidence;
* a blind observer understood only what the player surface exposed; and
* a fresh comparison found that observation conformant to design authority.

No validator promotes one claim into a later claim.  The design gate consumes
only the first object/review pair.  Baseline admission consumes the complete
runtime chain and still requires the user-owned playtest verdict.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


INTERACTION_CONTRACT_NAME = "PLAYER_FACING_INTERACTION_CONTRACT.json"
INTERACTION_CONTRACT_REVIEW_NAME = "PLAYER_FACING_INTERACTION_CONTRACT_REVIEW.json"
RUNTIME_EVIDENCE_NAME = "PLAYER_FACING_RUNTIME_INTERACTION_EVIDENCE.json"
BLIND_INPUT_NAME = "PLAYER_FACING_BLIND_OBSERVATION_INPUT.json"
BLIND_OBSERVATION_NAME = "PLAYER_FACING_BLIND_OBSERVATION.json"
COMPARISON_REVIEW_NAME = "PLAYER_FACING_COMPARISON_REVIEW.json"

INTERACTION_CONTRACT_VERSION = "player_facing_interaction_contract.v1"
INTERACTION_CONTRACT_REVIEW_VERSION = "player_facing_interaction_contract_review.v1"
RUNTIME_EVIDENCE_VERSION = "player_facing_runtime_interaction_evidence.v1"
BLIND_INPUT_VERSION = "player_facing_blind_observation_input.v1"
BLIND_OBSERVATION_VERSION = "player_facing_blind_observation.v1"
COMPARISON_REVIEW_VERSION = "player_facing_comparison_review.v1"

PASS_INTERACTION_DESIGN = "PASS_PLAYER_FACING_INTERACTION_DESIGN"
PASS_PLAYER_FACING_COMPARISON = "PASS_PLAYER_FACING_COMPARISON"

CONTRACT_REQUIREMENTS = (
    "visible_entry_cause_and_goal",
    "concrete_player_input_and_judgment",
    "ordered_interaction_not_abstract_verb",
    "visible_response_and_persistent_change",
    "discoverable_changed_next_affordance",
    "text_and_proxy_are_support_only",
    "current_scene_visual_sequence_present",
    "target_locale_readable",
    "runtime_capture_plan_is_falsifiable",
    "blind_prior_knowledge_is_deidentified",
)

WORK_INPUT_KINDS = {
    "MOVEMENT",
    "POSITIONING",
    "AIM",
    "TIMING",
    "SELECTION",
    "MANIPULATION",
    "RESOURCE_COMMITMENT",
    "COMBAT_COMMAND",
    "NAVIGATION",
    "CONTEXT_ACTION",
    "DIALOGUE_CHOICE",
}
PROXY_INPUT_KINDS = {
    "DIALOGUE_ADVANCE",
    "POPUP_DISMISS",
    "JOURNAL_OPEN",
    "MARKER_FOLLOW",
    "STRAIGHT_TRAVERSAL",
}
VISIBLE_RESPONSE_CHANNELS = {
    "WORLD_OBJECT",
    "CHARACTER",
    "CAMERA",
    "ANIMATION",
    "AUDIO",
    "WORLD_GEOMETRY",
    "CONTROL_STATE",
}
TEXT_PROXY_CHANNELS = {"DIALOGUE", "POPUP", "JOURNAL", "MARKER", "STATE_DUMP"}
REQUIRED_PROXY_NAMES = {
    "POPUP_ONLY",
    "JOURNAL_ONLY",
    "MARKER_ONLY",
    "HIDDEN_FLAG_ONLY",
    "STRAIGHT_TRAVERSAL_ONLY",
    "DIALOGUE_ADVANCE_ONLY",
}
REQUIRED_RUNTIME_FILE_TYPES = {
    "INPUT_TRACE",
    "FRAME_BEFORE",
    "FRAME_DURING",
    "FRAME_AFTER",
}
OBSERVATION_DIMENSIONS = (
    "cause",
    "goal",
    "affordance",
    "input_and_judgment",
    "visible_response",
    "persistent_change",
    "next_motive",
)
CURRENT_SCENE_MOMENTS = (
    "ENTRY",
    "AFFORDANCE",
    "EXPECTED_RESPONSE",
    "PERSISTENT_RETURN",
)

ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
SHA_PATTERN = re.compile(r"^[0-9a-f]{64}$")


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


def _id(value: Any, label: str, errors: list[str]) -> str:
    result = _text(value, label, errors)
    if result and ID_PATTERN.fullmatch(result) is None:
        errors.append(f"{label} must match {ID_PATTERN.pattern}")
    return result


def _contains_identifier(text: str, identifier: str) -> bool:
    if not identifier:
        return False
    return re.search(
        rf"(?<![a-z0-9_-]){re.escape(identifier.casefold())}(?![a-z0-9_-])",
        text.casefold(),
    ) is not None


def _strings(value: Any, label: str, errors: list[str], *, minimum: int = 1) -> list[str]:
    if not isinstance(value, list) or len(value) < minimum:
        errors.append(f"{label} must contain at least {minimum} item(s)")
        return []
    result = [_text(item, f"{label}[{index}]", errors) for index, item in enumerate(value)]
    if len(result) != len(set(result)):
        errors.append(f"{label} must be unique")
    return result


def _load_ref(repo: Path, raw: Any, label: str, errors: list[str]) -> tuple[dict[str, str], Path | None]:
    ref = _keys(raw, label, {"path", "sha256"}, errors)
    path_text = _text(ref.get("path"), f"{label}.path", errors)
    digest = _text(ref.get("sha256"), f"{label}.sha256", errors)
    result = {"path": path_text, "sha256": digest}
    if not path_text or not digest:
        return result, None
    candidate = Path(path_text)
    if candidate.is_absolute():
        errors.append(f"{label}.path must be game-repo-relative")
        return result, None
    path = (repo / candidate).resolve()
    try:
        path.relative_to(repo.resolve())
    except ValueError:
        errors.append(f"{label}.path escapes the game repo")
        return result, None
    if not path.is_file():
        errors.append(f"{label}.path does not identify a file: {path_text}")
        return result, None
    if SHA_PATTERN.fullmatch(digest) is None:
        errors.append(f"{label}.sha256 must be 64 lowercase hex characters")
    elif hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        errors.append(f"{label} hash does not match {path_text}")
    return result, path


def _load_optional_ref(repo: Path, raw: Any, label: str, errors: list[str]) -> tuple[dict[str, str], Path | None]:
    ref = _keys(raw, label, {"path", "sha256"}, errors)
    path_value = ref.get("path")
    sha_value = ref.get("sha256")
    if path_value == "" and sha_value == "":
        return {"path": "", "sha256": ""}, None
    return _load_ref(repo, raw, label, errors)


def _load_json(path: Path | None, label: str, errors: list[str]) -> dict[str, Any]:
    if path is None:
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        errors.append(f"cannot read {label} JSON: {error}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"{label} must contain a JSON object")
        return {}
    return value


def _same_ref(actual: dict[str, str], expected: dict[str, str], label: str, errors: list[str]) -> None:
    if actual != expected:
        errors.append(f"{label} does not bind the exact required artifact")


def _artifact_list(repo: Path, value: Any, label: str, errors: list[str], *, allowed_types: set[str] | None = None) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        errors.append(f"{label} must be a non-empty array")
        return []
    result: list[dict[str, Any]] = []
    for index, raw in enumerate(value):
        item = _keys(raw, f"{label}[{index}]", {"artifact_type", "artifact"}, errors)
        artifact_type = _text(item.get("artifact_type"), f"{label}[{index}].artifact_type", errors)
        if allowed_types is not None and artifact_type not in allowed_types:
            errors.append(f"{label}[{index}].artifact_type is unsupported")
        artifact, _ = _load_ref(repo, item.get("artifact"), f"{label}[{index}].artifact", errors)
        result.append({"artifact_type": artifact_type, "artifact": artifact})
    return result


def _current_scene_sequence(
    repo: Path,
    value: Any,
    label: str,
    errors: list[str],
) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        errors.append(f"{label} must be a non-empty ordered array")
        return []
    result: list[dict[str, Any]] = []
    for index, raw in enumerate(value):
        item = _keys(
            raw,
            f"{label}[{index}]",
            {"sequence", "beat_id", "surface_moment", "artifact_type", "artifact"},
            errors,
        )
        sequence = item.get("sequence")
        if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
            errors.append(f"{label}[{index}].sequence must be a positive integer")
        beat_id = _id(item.get("beat_id"), f"{label}[{index}].beat_id", errors)
        moment = _text(
            item.get("surface_moment"), f"{label}[{index}].surface_moment", errors
        )
        if moment not in CURRENT_SCENE_MOMENTS:
            errors.append(f"{label}[{index}].surface_moment is unsupported")
        artifact_type = _text(
            item.get("artifact_type"), f"{label}[{index}].artifact_type", errors
        )
        if artifact_type not in {
            "IN_ENGINE_SCREENSHOT",
            "ANNOTATED_CURRENT_SCENE_FRAME",
            "FAITHFUL_SCREEN_FLOW_PROTOTYPE",
        }:
            errors.append(f"{label}[{index}].artifact_type is unsupported")
        artifact, _ = _load_ref(
            repo, item.get("artifact"), f"{label}[{index}].artifact", errors
        )
        result.append(
            {
                "sequence": sequence,
                "beat_id": beat_id,
                "surface_moment": moment,
                "artifact_type": artifact_type,
                "artifact": artifact,
            }
        )
    return result


def validate_interaction_contract(
    repo: Path,
    raw_ref: Any,
    *,
    project_id: str,
    objective_id: str,
    factory_revision: str,
    product_authority: dict[str, str],
    studio_gameplay_system: dict[str, str],
    expected_transition_ids: list[str],
    errors: list[str],
) -> dict[str, Any]:
    """Validate one game-owned pre-production player-surface contract."""

    ref, path = _load_ref(repo, raw_ref, "player-facing interaction contract", errors)
    expected_path = (repo / Path(ref["path"])).resolve() if ref.get("path") else None
    if expected_path is not None and expected_path.name != INTERACTION_CONTRACT_NAME:
        errors.append(f"player-facing interaction contract must be named {INTERACTION_CONTRACT_NAME}")
    payload = _load_json(path, "player-facing interaction contract", errors)
    required = {
        "schema_version", "contract_id", "project_id", "objective_id",
        "factory_revision", "product_authority", "studio_gameplay_system",
        "author_context_id", "target_player", "target_locale",
        "player_entry_knowledge",
        "current_scene_composition", "localization_readability",
        "playable_beats", "design_status", "authored_at",
    }
    _keys(payload, "player-facing interaction contract", required, errors)
    if payload.get("schema_version") != INTERACTION_CONTRACT_VERSION:
        errors.append(f"player-facing interaction contract schema_version must be {INTERACTION_CONTRACT_VERSION}")
    _id(payload.get("contract_id"), "player-facing interaction contract.contract_id", errors)
    for field, expected in (
        ("project_id", project_id),
        ("objective_id", objective_id),
        ("factory_revision", factory_revision),
    ):
        if payload.get(field) != expected:
            errors.append(f"player-facing interaction contract.{field} does not match")
    product_ref, _ = _load_optional_ref(repo, payload.get("product_authority"), "interaction contract.product_authority", errors)
    system_ref, _ = _load_optional_ref(repo, payload.get("studio_gameplay_system"), "interaction contract.studio_gameplay_system", errors)
    _same_ref(product_ref, product_authority, "interaction contract Product authority", errors)
    _same_ref(system_ref, studio_gameplay_system, "interaction contract Studio gameplay system", errors)
    author = _id(payload.get("author_context_id"), "interaction contract.author_context_id", errors)
    _text(payload.get("target_player"), "interaction contract.target_player", errors)
    target_locale = _text(payload.get("target_locale"), "interaction contract.target_locale", errors)
    player_entry_knowledge = _strings(
        payload.get("player_entry_knowledge"),
        "interaction contract.player_entry_knowledge",
        errors,
    )
    scene_artifacts = _current_scene_sequence(
        repo,
        payload.get("current_scene_composition"),
        "interaction contract.current_scene_composition",
        errors,
    )
    locale = _keys(
        payload.get("localization_readability"),
        "interaction contract.localization_readability",
        {"locale", "readability_status", "fallback_used", "garbled_text_present", "evidence"},
        errors,
    )
    if locale.get("locale") != target_locale:
        errors.append("interaction contract localization locale must match target_locale")
    if locale.get("readability_status") != "VERIFIED_READABLE":
        errors.append("interaction contract target locale must be VERIFIED_READABLE")
    if locale.get("fallback_used") is not False or locale.get("garbled_text_present") is not False:
        errors.append("interaction contract target locale cannot use fallback or garbled text")
    _artifact_list(repo, locale.get("evidence"), "interaction contract.localization_readability.evidence", errors)

    raw_beats = payload.get("playable_beats")
    if not isinstance(raw_beats, list) or not raw_beats:
        errors.append("interaction contract.playable_beats must be a non-empty array")
        raw_beats = []
    beat_ids: list[str] = []
    covered_transitions: list[str] = []
    answer_bearing_design_ids: set[str] = set()
    for index, raw in enumerate(raw_beats):
        label = f"interaction contract.playable_beats[{index}]"
        beat = _keys(
            raw,
            label,
            {
                "beat_id", "system_transition_ids", "entry_screen_state",
                "player_prior_knowledge", "perceivable_cause", "visible_goal",
                "available_input", "required_judgment", "interaction_sequence",
                "immediate_visible_response", "persistent_visible_change",
                "next_affordance", "allowed_text_support", "forbidden_proxy_check",
                "player_surface_evidence_plan",
            },
            errors,
        )
        beat_id = _id(beat.get("beat_id"), f"{label}.beat_id", errors)
        beat_ids.append(beat_id)
        transition_ids = _strings(beat.get("system_transition_ids"), f"{label}.system_transition_ids", errors)
        covered_transitions.extend(transition_ids)
        answer_bearing_design_ids.update(transition_ids)
        for field in (
            "entry_screen_state", "perceivable_cause",
            "visible_goal", "required_judgment", "immediate_visible_response",
            "persistent_visible_change",
        ):
            _text(beat.get(field), f"{label}.{field}", errors)
        _text(
            beat.get("player_prior_knowledge"),
            f"{label}.player_prior_knowledge",
            errors,
        )
        available = _keys(beat.get("available_input"), f"{label}.available_input", {"input_kind", "control", "affordance_cue"}, errors)
        input_kind = _text(available.get("input_kind"), f"{label}.available_input.input_kind", errors)
        if input_kind not in WORK_INPUT_KINDS:
            errors.append(f"{label}.available_input must name concrete player work, not a proxy")
        _text(available.get("control"), f"{label}.available_input.control", errors)
        _text(available.get("affordance_cue"), f"{label}.available_input.affordance_cue", errors)

        sequence = beat.get("interaction_sequence")
        if not isinstance(sequence, list) or not sequence:
            errors.append(f"{label}.interaction_sequence must contain ordered input-to-response steps")
            sequence = []
        work_steps = 0
        for seq_index, raw_step in enumerate(sequence):
            step_label = f"{label}.interaction_sequence[{seq_index}]"
            step = _keys(raw_step, step_label, {"step_id", "input_kind", "control", "player_intent", "visible_response", "response_channels", "counts_as_player_work"}, errors)
            step_id = _id(step.get("step_id"), f"{step_label}.step_id", errors)
            answer_bearing_design_ids.add(step_id)
            kind = _text(step.get("input_kind"), f"{step_label}.input_kind", errors)
            if kind in PROXY_INPUT_KINDS or kind not in WORK_INPUT_KINDS:
                errors.append(f"{step_label}.input_kind cannot be a dialogue/popup/journal/marker/traversal proxy")
            if step.get("counts_as_player_work") is True:
                work_steps += 1
            else:
                errors.append(f"{step_label}.counts_as_player_work must be true")
            for field in ("control", "player_intent", "visible_response"):
                _text(step.get(field), f"{step_label}.{field}", errors)
            channels = set(_strings(step.get("response_channels"), f"{step_label}.response_channels", errors))
            if not channels & VISIBLE_RESPONSE_CHANNELS:
                errors.append(f"{step_label} must include a non-text visible world/person response channel")
        if work_steps == 0:
            errors.append(f"{label} has no concrete player-work step")

        next_affordance = _keys(beat.get("next_affordance"), f"{label}.next_affordance", {"description", "discovery_channels"}, errors)
        _text(next_affordance.get("description"), f"{label}.next_affordance.description", errors)
        discovery = set(_strings(next_affordance.get("discovery_channels"), f"{label}.next_affordance.discovery_channels", errors))
        if not discovery & VISIBLE_RESPONSE_CHANNELS:
            errors.append(f"{label}.next_affordance must be visible or interactively discoverable on the player surface")

        text_support = _keys(beat.get("allowed_text_support"), f"{label}.allowed_text_support", {"role", "text_can_complete_action", "description"}, errors)
        if text_support.get("role") != "SUPPORT_ONLY" or text_support.get("text_can_complete_action") is not False:
            errors.append(f"{label}.allowed_text_support cannot replace the player action")
        _text(text_support.get("description"), f"{label}.allowed_text_support.description", errors)
        proxy = _keys(beat.get("forbidden_proxy_check"), f"{label}.forbidden_proxy_check", {"proxy_only", "disallowed_proxies", "explanation"}, errors)
        if proxy.get("proxy_only") is not False:
            errors.append(f"{label}.forbidden_proxy_check.proxy_only must be false")
        proxies = set(_strings(proxy.get("disallowed_proxies"), f"{label}.forbidden_proxy_check.disallowed_proxies", errors))
        if proxies != REQUIRED_PROXY_NAMES:
            errors.append(f"{label}.forbidden_proxy_check must enumerate every mandatory proxy blocker")
        _text(proxy.get("explanation"), f"{label}.forbidden_proxy_check.explanation", errors)
        plan = _keys(beat.get("player_surface_evidence_plan"), f"{label}.player_surface_evidence_plan", {"scenario_id", "start_state", "ordered_capture_moments"}, errors)
        scenario_id = _id(plan.get("scenario_id"), f"{label}.player_surface_evidence_plan.scenario_id", errors)
        answer_bearing_design_ids.add(scenario_id)
        _text(plan.get("start_state"), f"{label}.player_surface_evidence_plan.start_state", errors)
        moments = _strings(
            plan.get("ordered_capture_moments"),
            f"{label}.player_surface_evidence_plan.ordered_capture_moments",
            errors,
        )
        if moments != [
            "BEFORE_INPUT",
            "DURING_INTERACTION",
            "AFTER_RESPONSE",
            "RETURNED_CHANGED_AFFORDANCE",
        ]:
            errors.append(
                f"{label}.player_surface_evidence_plan must capture before, "
                "during, after, and returned affordance in that exact order"
            )

    if len(beat_ids) != len(set(beat_ids)):
        errors.append("interaction contract beat_id values must be unique")
    answer_bearing_design_ids.update(beat_ids)
    for index, knowledge in enumerate(player_entry_knowledge):
        normalized = knowledge.casefold()
        exposed = sorted(
            identifier
            for identifier in answer_bearing_design_ids
            if _contains_identifier(normalized, identifier)
        )
        if exposed:
            errors.append(
                "interaction contract.player_entry_knowledge"
                f"[{index}] exposes answer-bearing design ids: "
                + ", ".join(exposed)
            )
    scene_sequences = [item.get("sequence") for item in scene_artifacts]
    if scene_sequences != list(range(1, len(scene_artifacts) + 1)):
        errors.append(
            "interaction contract.current_scene_composition sequence must be "
            "contiguous and stored in order"
        )
    scene_pairs = [
        (str(item.get("beat_id", "")), str(item.get("surface_moment", "")))
        for item in scene_artifacts
    ]
    expected_scene_pairs = [
        (beat_id, moment)
        for beat_id in beat_ids
        for moment in CURRENT_SCENE_MOMENTS
    ]
    if scene_pairs != expected_scene_pairs:
        errors.append(
            "interaction contract.current_scene_composition must exactly cover "
            "ENTRY, AFFORDANCE, EXPECTED_RESPONSE, and PERSISTENT_RETURN for "
            "every playable beat in contract-beat and temporal order"
        )
    scene_digests = [
        str(item.get("artifact", {}).get("sha256", ""))
        for item in scene_artifacts
    ]
    if len(scene_digests) != len(set(scene_digests)):
        errors.append(
            "interaction contract.current_scene_composition cannot copy, rename, "
            "relabel, or reuse one static visual as multiple temporal moments"
        )
    if covered_transitions != expected_transition_ids:
        errors.append(
            "interaction contract playable beats must exactly cover the "
            "Card/system transition ids in authoritative order"
        )
    if payload.get("design_status") != "TESTABLE_DESIGN":
        errors.append("interaction contract.design_status must be TESTABLE_DESIGN, never an observed/pass verdict")
    _text(payload.get("authored_at"), "interaction contract.authored_at", errors)
    return {
        "ref": ref,
        "payload": payload,
        "beat_ids": set(beat_ids),
        "player_entry_knowledge": player_entry_knowledge,
        "author_context_id": author,
        "answer_bearing_design_ids": answer_bearing_design_ids,
        "scene_artifacts": scene_artifacts,
        "target_locale": target_locale,
    }


def validate_interaction_contract_review(
    repo: Path,
    raw_ref: Any,
    *,
    contract: dict[str, Any],
    product_authority: dict[str, str],
    studio_gameplay_system: dict[str, str],
    forbidden_context_ids: set[str],
    errors: list[str],
) -> dict[str, Any]:
    ref, path = _load_ref(repo, raw_ref, "player-facing interaction contract review", errors)
    if path is not None and path.name != INTERACTION_CONTRACT_REVIEW_NAME:
        errors.append(f"player-facing interaction contract review must be named {INTERACTION_CONTRACT_REVIEW_NAME}")
    payload = _load_json(path, "player-facing interaction contract review", errors)
    required = {
        "schema_version", "review_id", "review_role", "project_id", "objective_id",
        "factory_revision", "interaction_contract", "product_authority",
        "studio_gameplay_system", "reviewer_context_id", "reviewer_freshness",
        "hypothesis_lifecycle", "requirement_findings", "beat_findings",
        "blocking_findings", "verdict", "reviewed_at",
    }
    _keys(payload, "player-facing interaction contract review", required, errors)
    if payload.get("schema_version") != INTERACTION_CONTRACT_REVIEW_VERSION:
        errors.append(f"player-facing interaction contract review schema_version must be {INTERACTION_CONTRACT_REVIEW_VERSION}")
    if payload.get("review_role") != "PLAYER_FACING_INTERACTION_DESIGN_REVIEW":
        errors.append("player-facing interaction review has the wrong review_role")
    contract_payload = contract.get("payload", {})
    for field in ("project_id", "objective_id", "factory_revision"):
        if payload.get(field) != contract_payload.get(field):
            errors.append(f"player-facing interaction review.{field} does not match the contract")
    contract_ref, _ = _load_ref(repo, payload.get("interaction_contract"), "interaction review.interaction_contract", errors)
    _same_ref(contract_ref, contract.get("ref", {}), "interaction review contract", errors)
    product_ref, _ = _load_optional_ref(repo, payload.get("product_authority"), "interaction review.product_authority", errors)
    system_ref, _ = _load_optional_ref(repo, payload.get("studio_gameplay_system"), "interaction review.studio_gameplay_system", errors)
    _same_ref(product_ref, product_authority, "interaction review Product authority", errors)
    _same_ref(system_ref, studio_gameplay_system, "interaction review Studio gameplay system", errors)
    reviewer = _id(payload.get("reviewer_context_id"), "interaction review.reviewer_context_id", errors)
    forbidden = {contract.get("author_context_id", ""), *forbidden_context_ids} - {""}
    if reviewer in forbidden:
        errors.append("player-facing interaction reviewer must be fresh from authors and other reviewers")
    if payload.get("reviewer_freshness") != "FRESH":
        errors.append("player-facing interaction reviewer_freshness must be FRESH")
    if payload.get("hypothesis_lifecycle") != "TESTABLE_DESIGN_ONLY":
        errors.append("design review may only label hypotheses TESTABLE_DESIGN_ONLY")
    findings = _keys(payload.get("requirement_findings"), "interaction review.requirement_findings", set(CONTRACT_REQUIREMENTS), errors)
    for requirement in CONTRACT_REQUIREMENTS:
        finding = _keys(findings.get(requirement), f"interaction review.requirement_findings.{requirement}", {"verdict", "beat_ids", "rationale"}, errors)
        if finding.get("verdict") != "PASS":
            errors.append(f"interaction review requirement {requirement} must PASS")
        cited = set(_strings(finding.get("beat_ids"), f"interaction review.requirement_findings.{requirement}.beat_ids", errors))
        if cited != contract.get("beat_ids", set()):
            errors.append(
                f"interaction review requirement {requirement} must exactly cover "
                "every contract beat"
            )
        _text(finding.get("rationale"), f"interaction review.requirement_findings.{requirement}.rationale", errors)
    beat_findings = payload.get("beat_findings")
    if not isinstance(beat_findings, list):
        errors.append("interaction review.beat_findings must be an array")
        beat_findings = []
    reviewed_beats: list[str] = []
    for index, raw in enumerate(beat_findings):
        finding = _keys(raw, f"interaction review.beat_findings[{index}]", {"beat_id", "verdict", "rationale"}, errors)
        reviewed_beats.append(_id(finding.get("beat_id"), f"interaction review.beat_findings[{index}].beat_id", errors))
        if finding.get("verdict") != "PASS_TESTABLE_DESIGN":
            errors.append("interaction review beat verdict must be PASS_TESTABLE_DESIGN")
        _text(finding.get("rationale"), f"interaction review.beat_findings[{index}].rationale", errors)
    if set(reviewed_beats) != contract.get("beat_ids", set()) or len(reviewed_beats) != len(set(reviewed_beats)):
        errors.append("interaction review.beat_findings must exactly cover every contract beat")
    if payload.get("blocking_findings") != []:
        errors.append("interaction review.blocking_findings must be empty")
    if payload.get("verdict") != PASS_INTERACTION_DESIGN:
        errors.append(f"interaction review.verdict must be {PASS_INTERACTION_DESIGN}")
    _text(payload.get("reviewed_at"), "interaction review.reviewed_at", errors)
    return {"ref": ref, "payload": payload, "reviewer_context_id": reviewer}


def validate_runtime_player_surface_chain(
    repo: Path,
    refs: dict[str, Any],
    *,
    project_id: str,
    unit_id: str,
    game_revision: str,
    build_id: str,
    factory_revision: str,
    expected_contract_ref: dict[str, str],
    expected_contract_review_ref: dict[str, str],
    expected_card_ref: dict[str, str],
    expected_system_ref: dict[str, str],
    expected_beat_ids: set[str],
    expected_answer_bearing_design_ids: set[str],
    expected_target_locale: str,
    expected_player_entry_knowledge: list[str],
    hypothesis_ids: set[str],
    design_context_ids: set[str],
    production_context_ids: set[str],
    acceptance_reviewer_context_id: str,
    errors: list[str],
) -> dict[str, Any]:
    """Validate exact runtime evidence, blind observation, and comparison."""

    required_refs = {"runtime_interaction_evidence", "blind_observation_input", "blind_observation", "comparison_review"}
    _keys(refs, "player-facing evidence chain", required_refs, errors)
    loaded: dict[str, tuple[dict[str, str], Path | None, dict[str, Any]]] = {}
    for key in sorted(required_refs):
        ref, path = _load_ref(repo, refs.get(key), f"player-facing evidence chain.{key}", errors)
        loaded[key] = (ref, path, _load_json(path, key.replace("_", " "), errors))

    runtime_ref, runtime_path, runtime = loaded["runtime_interaction_evidence"]
    runtime_required = {
        "schema_version", "evidence_id", "project_id", "unit_id", "game_revision",
        "build_id", "factory_revision", "interaction_contract", "producer_context_id",
        "clean_start", "scenario_entry_state", "capture_environment",
        "ordered_input_trace", "structural_evidence", "observable_changes",
        "returned_surface", "localization_observation", "evidence_files", "captured_at",
    }
    _keys(runtime, "runtime interaction evidence", runtime_required, errors)
    if runtime.get("schema_version") != RUNTIME_EVIDENCE_VERSION:
        errors.append(f"runtime interaction evidence schema_version must be {RUNTIME_EVIDENCE_VERSION}")
    if runtime_path is not None and runtime_path.name != RUNTIME_EVIDENCE_NAME:
        errors.append(f"runtime interaction evidence must be named {RUNTIME_EVIDENCE_NAME}")
    for field, expected in (("project_id", project_id), ("unit_id", unit_id), ("game_revision", game_revision), ("build_id", build_id), ("factory_revision", factory_revision)):
        if runtime.get(field) != expected:
            errors.append(f"runtime interaction evidence.{field} does not match acceptance")
    _id(runtime.get("evidence_id"), "runtime interaction evidence.evidence_id", errors)
    contract_ref, _ = _load_ref(repo, runtime.get("interaction_contract"), "runtime interaction evidence.interaction_contract", errors)
    _same_ref(contract_ref, expected_contract_ref, "runtime interaction evidence contract", errors)
    producer = _id(runtime.get("producer_context_id"), "runtime interaction evidence.producer_context_id", errors)
    clean_start = _keys(runtime.get("clean_start"), "runtime interaction evidence.clean_start", {"save_identity", "save_state", "start_state"}, errors)
    for field in ("save_identity", "start_state"):
        _text(clean_start.get(field), f"runtime interaction evidence.clean_start.{field}", errors)
    if clean_start.get("save_state") != "CLEAN_START":
        errors.append("runtime interaction evidence must use a CLEAN_START save state")
    _text(runtime.get("scenario_entry_state"), "runtime interaction evidence.scenario_entry_state", errors)
    capture = _keys(runtime.get("capture_environment"), "runtime interaction evidence.capture_environment", {"engine", "window_mode", "rendering_mode"}, errors)
    _text(capture.get("engine"), "runtime interaction evidence.capture_environment.engine", errors)
    if capture.get("window_mode") != "WINDOWED" or capture.get("rendering_mode") != "IN_ENGINE":
        errors.append("runtime interaction evidence must be windowed in-engine capture, not headless/dummy output")
    trace = runtime.get("ordered_input_trace")
    if not isinstance(trace, list) or not trace:
        errors.append("runtime interaction evidence.ordered_input_trace must not be empty")
        trace = []
    trace_sequences: set[int] = set()
    trace_sequence_order: list[int] = []
    trace_beat_ids: set[str] = set()
    runtime_surface_refs: set[tuple[str, str]] = set()
    trace_frame_refs: dict[str, set[tuple[str, str]]] = {
        "FRAME_BEFORE": set(),
        "FRAME_DURING": set(),
        "FRAME_AFTER": set(),
    }
    trace_surface_refs_by_sequence: dict[int, set[tuple[str, str]]] = {}
    for index, raw in enumerate(trace):
        item = _keys(raw, f"runtime interaction evidence.ordered_input_trace[{index}]", {"sequence", "beat_id", "input_kind", "control", "player_intent", "frame_before", "frame_during", "frame_after", "observed_response"}, errors)
        sequence = item.get("sequence")
        if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
            errors.append("runtime interaction trace sequence must be a positive integer")
        else:
            trace_sequences.add(sequence)
            trace_sequence_order.append(sequence)
        trace_beat_ids.add(_id(item.get("beat_id"), f"runtime interaction trace[{index}].beat_id", errors))
        kind = _text(item.get("input_kind"), f"runtime interaction trace[{index}].input_kind", errors)
        if kind in PROXY_INPUT_KINDS or kind not in WORK_INPUT_KINDS:
            errors.append("runtime interaction trace cannot use a proxy as the claimed gameplay action")
        for field in ("control", "player_intent", "observed_response"):
            _text(item.get(field), f"runtime interaction trace[{index}].{field}", errors)
        item_frame_refs: set[tuple[str, str]] = set()
        for field in ("frame_before", "frame_during", "frame_after"):
            frame_ref, _ = _load_ref(
                repo,
                item.get(field),
                f"runtime interaction trace[{index}].{field}",
                errors,
            )
            runtime_surface_refs.add((frame_ref["path"], frame_ref["sha256"]))
            item_frame_refs.add((frame_ref["path"], frame_ref["sha256"]))
            trace_frame_refs[field.upper()].add(
                (frame_ref["path"], frame_ref["sha256"])
            )
        frame_digests = {
            str(item.get(field, {}).get("sha256", ""))
            for field in ("frame_before", "frame_during", "frame_after")
            if isinstance(item.get(field), dict)
        }
        if len(frame_digests - {""}) != 3:
            errors.append(
                f"runtime interaction trace[{index}] requires byte-distinct "
                "before, during, and after frames; one static frame cannot prove interaction"
            )
        if isinstance(sequence, int) and not isinstance(sequence, bool):
            trace_surface_refs_by_sequence[sequence] = item_frame_refs
    if trace_sequence_order != list(range(1, len(trace) + 1)):
        errors.append("runtime interaction evidence trace sequence must be contiguous and ordered")
    seen_trace_digests: set[str] = set()
    for sequence in trace_sequence_order:
        current_refs = trace_surface_refs_by_sequence.get(sequence, set())
        current_digests = {digest for _path, digest in current_refs} - {""}
        if seen_trace_digests & current_digests:
            errors.append(
                "runtime interaction evidence cannot copy, rename, or reuse one "
                "trace frame visual across different interaction sequences"
            )
        seen_trace_digests.update(current_digests)
    if trace_beat_ids != expected_beat_ids:
        errors.append("runtime interaction evidence must exactly cover every interaction-contract beat")
    structural = _keys(runtime.get("structural_evidence"), "runtime interaction evidence.structural_evidence", {"status", "evidence", "rationale"}, errors)
    structural_refs = structural.get("evidence")
    if structural.get("status") == "CAPTURED":
        _artifact_list(repo, structural_refs, "runtime interaction evidence.structural_evidence.evidence", errors)
    elif structural.get("status") == "NOT_APPLICABLE":
        if structural_refs != []:
            errors.append("NOT_APPLICABLE structural evidence must have an empty evidence list")
    else:
        errors.append("runtime interaction evidence structural status is unsupported")
    _text(structural.get("rationale"), "runtime interaction evidence.structural_evidence.rationale", errors)
    changes = runtime.get("observable_changes")
    if not isinstance(changes, list) or not changes:
        errors.append("runtime interaction evidence.observable_changes must not be empty")
        changes = []
    changed_beats: set[str] = set()
    for index, raw in enumerate(changes):
        item = _keys(raw, f"runtime interaction evidence.observable_changes[{index}]", {"beat_id", "before", "after", "response_channels"}, errors)
        changed_beats.add(_id(item.get("beat_id"), f"runtime interaction evidence.observable_changes[{index}].beat_id", errors))
        before = _text(item.get("before"), f"runtime observable change[{index}].before", errors)
        after = _text(item.get("after"), f"runtime observable change[{index}].after", errors)
        if before and after and before == after:
            errors.append("runtime interaction evidence observable change did not change")
        channels = set(_strings(item.get("response_channels"), f"runtime observable change[{index}].response_channels", errors))
        if not channels & VISIBLE_RESPONSE_CHANNELS:
            errors.append("runtime observable change must use a visible world/person response channel")
    if changed_beats != trace_beat_ids:
        errors.append("runtime observable changes must exactly cover traced playable beats")
    returned = _keys(runtime.get("returned_surface"), "runtime interaction evidence.returned_surface", {"frame", "visible_next_affordance", "discovery_channels"}, errors)
    returned_ref, _ = _load_ref(
        repo,
        returned.get("frame"),
        "runtime interaction evidence.returned_surface.frame",
        errors,
    )
    runtime_surface_refs.add((returned_ref["path"], returned_ref["sha256"]))
    before_digests = {digest for _path, digest in trace_frame_refs["FRAME_BEFORE"]}
    if returned_ref.get("sha256") in before_digests:
        errors.append(
            "runtime returned player surface must be byte-distinct from the "
            "before-input surface so the changed affordance is visible"
        )
    _text(returned.get("visible_next_affordance"), "runtime interaction evidence.returned_surface.visible_next_affordance", errors)
    if not set(_strings(returned.get("discovery_channels"), "runtime interaction evidence.returned_surface.discovery_channels", errors)) & VISIBLE_RESPONSE_CHANNELS:
        errors.append("returned player surface must expose a visible/interactable changed next affordance")
    localization = _keys(runtime.get("localization_observation"), "runtime interaction evidence.localization_observation", {"locale", "status", "fallback_used", "garbled_text_present", "evidence"}, errors)
    if localization.get("locale") != expected_target_locale:
        errors.append(
            "runtime interaction evidence localization locale must match the "
            "interaction contract target locale"
        )
    if localization.get("status") != "OBSERVED_READABLE" or localization.get("fallback_used") is not False or localization.get("garbled_text_present") is not False:
        errors.append("runtime target localization must be observed readable without fallback or garbling")
    _text(localization.get("locale"), "runtime interaction evidence.localization_observation.locale", errors)
    localization_artifacts = _artifact_list(
        repo,
        localization.get("evidence"),
        "runtime interaction evidence.localization_observation.evidence",
        errors,
    )
    runtime_surface_refs.update(
        (item["artifact"]["path"], item["artifact"]["sha256"])
        for item in localization_artifacts
    )
    localization_surface_refs = {
        (item["artifact"]["path"], item["artifact"]["sha256"])
        for item in localization_artifacts
    }
    evidence_files = _artifact_list(repo, runtime.get("evidence_files"), "runtime interaction evidence.evidence_files", errors)
    file_types = {item["artifact_type"] for item in evidence_files}
    if not REQUIRED_RUNTIME_FILE_TYPES.issubset(file_types):
        errors.append("runtime interaction evidence must combine input trace with before/during/after frames")
    evidence_refs_by_type: dict[str, set[tuple[str, str]]] = {}
    for evidence_file in evidence_files:
        artifact = evidence_file["artifact"]
        evidence_refs_by_type.setdefault(evidence_file["artifact_type"], set()).add(
            (artifact["path"], artifact["sha256"])
        )
    for frame_type, expected_refs in trace_frame_refs.items():
        if evidence_refs_by_type.get(frame_type, set()) != expected_refs:
            errors.append(
                f"runtime interaction evidence.evidence_files {frame_type} must "
                "exactly bind the structured trace frame refs"
            )
    input_trace_refs = evidence_refs_by_type.get("INPUT_TRACE", set())
    if not input_trace_refs:
        errors.append("runtime interaction evidence must bind an INPUT_TRACE artifact")
    elif input_trace_refs & runtime_surface_refs:
        errors.append(
            "runtime INPUT_TRACE must be distinct from player-surface frame artifacts"
        )
    _text(runtime.get("captured_at"), "runtime interaction evidence.captured_at", errors)

    blind_input_ref, blind_input_path, blind_input = loaded["blind_observation_input"]
    blind_input_required = {"schema_version", "observation_input_id", "project_id", "unit_id", "game_revision", "build_id", "clean_start", "scenario_entry_state", "player_prior_knowledge", "normal_controls", "surface_artifacts", "context_policy", "preparation_attestation", "prepared_at"}
    _keys(blind_input, "blind observation input", blind_input_required, errors)
    if blind_input.get("schema_version") != BLIND_INPUT_VERSION:
        errors.append(f"blind observation input schema_version must be {BLIND_INPUT_VERSION}")
    if blind_input_path is not None and blind_input_path.name != BLIND_INPUT_NAME:
        errors.append(f"blind observation input must be named {BLIND_INPUT_NAME}")
    for field, expected in (("project_id", project_id), ("unit_id", unit_id), ("game_revision", game_revision), ("build_id", build_id)):
        if blind_input.get(field) != expected:
            errors.append(f"blind observation input.{field} does not match acceptance")
    _id(blind_input.get("observation_input_id"), "blind observation input.observation_input_id", errors)
    if blind_input.get("clean_start") != clean_start or blind_input.get("scenario_entry_state") != runtime.get("scenario_entry_state"):
        errors.append("blind observation input must use the runtime evidence's exact start state")
    bound_prior_knowledge = _strings(
        blind_input.get("player_prior_knowledge"),
        "blind observation input.player_prior_knowledge",
        errors,
    )
    if bound_prior_knowledge != expected_player_entry_knowledge:
        errors.append(
            "blind observation input player prior knowledge must exactly match the "
            "contract's de-identified entry knowledge and cannot expose beat ids or "
            "inject intended answers"
        )
    normal_controls = _strings(
        blind_input.get("normal_controls"),
        "blind observation input.normal_controls",
        errors,
    )
    blind_surface_artifacts = _artifact_list(
        repo,
        blind_input.get("surface_artifacts"),
        "blind observation input.surface_artifacts",
        errors,
        allowed_types={"SCREEN_FRAME", "AUDIO_CAPTURE", "VIDEO_CAPTURE"},
    )
    blind_surface_ref_set = {
        (item["artifact"]["path"], item["artifact"]["sha256"])
        for item in blind_surface_artifacts
    }
    if blind_surface_ref_set != runtime_surface_refs:
        errors.append(
            "blind observation input surface artifacts must exactly cover every "
            "runtime before/during/after, returned, and localization player-surface "
            "artifact"
        )
    phase_a_visible_strings = [
        str(clean_start.get("save_identity", "")),
        str(clean_start.get("start_state", "")),
        str(blind_input.get("scenario_entry_state", "")),
        *bound_prior_knowledge,
        *normal_controls,
        *[
            str(item.get("artifact", {}).get("path", ""))
            for item in blind_surface_artifacts
        ],
    ]
    exposed_design_ids = sorted(
        identifier
        for identifier in expected_answer_bearing_design_ids
        if any(
            _contains_identifier(value, identifier)
            for value in phase_a_visible_strings
        )
    )
    if exposed_design_ids:
        errors.append(
            "blind observation input Phase-A-visible text or artifact paths "
            "expose answer-bearing design ids: "
            + ", ".join(exposed_design_ids)
        )
    policy = _keys(blind_input.get("context_policy"), "blind observation input.context_policy", {"authority_access", "allowed_materials"}, errors)
    if policy != {"authority_access": "FORBIDDEN_BEFORE_OBSERVATION", "allowed_materials": "PLAYER_SURFACE_ONLY"}:
        errors.append("blind observation input must mechanically forbid answer-bearing design authority")
    preparation = _keys(
        blind_input.get("preparation_attestation"),
        "blind observation input.preparation_attestation",
        {
            "preparer_context_id", "answer_bearing_design_ids_removed",
            "intended_answers_removed", "future_beat_knowledge_removed",
            "only_phase_a_allowed_materials_present",
        },
        errors,
    )
    preparer = _id(
        preparation.get("preparer_context_id"),
        "blind observation input.preparation_attestation.preparer_context_id",
        errors,
    )
    expected_preparation = {
        "answer_bearing_design_ids_removed": True,
        "intended_answers_removed": True,
        "future_beat_knowledge_removed": True,
        "only_phase_a_allowed_materials_present": True,
    }
    if any(
        preparation.get(field) is not expected
        for field, expected in expected_preparation.items()
    ):
        errors.append(
            "blind observation input preparation must attest that all design "
            "ids, intended answers, future knowledge, and non-Phase-A material "
            "were removed before observation"
        )
    _text(blind_input.get("prepared_at"), "blind observation input.prepared_at", errors)

    blind_ref, blind_path, blind = loaded["blind_observation"]
    blind_required = {"schema_version", "observation_id", "project_id", "unit_id", "game_revision", "build_id", "observation_input", "reviewer_context_id", "reviewer_freshness", "context_attestation", "observation", "observed_at"}
    _keys(blind, "blind observation", blind_required, errors)
    if blind.get("schema_version") != BLIND_OBSERVATION_VERSION:
        errors.append(f"blind observation schema_version must be {BLIND_OBSERVATION_VERSION}")
    if blind_path is not None and blind_path.name != BLIND_OBSERVATION_NAME:
        errors.append(f"blind observation must be named {BLIND_OBSERVATION_NAME}")
    for field, expected in (("project_id", project_id), ("unit_id", unit_id), ("game_revision", game_revision), ("build_id", build_id)):
        if blind.get(field) != expected:
            errors.append(f"blind observation.{field} does not match acceptance")
    _id(blind.get("observation_id"), "blind observation.observation_id", errors)
    bound_blind_input, _ = _load_ref(repo, blind.get("observation_input"), "blind observation.observation_input", errors)
    _same_ref(bound_blind_input, blind_input_ref, "blind observation input binding", errors)
    blind_reviewer = _id(blind.get("reviewer_context_id"), "blind observation.reviewer_context_id", errors)
    if blind_reviewer == preparer:
        errors.append(
            "blind observer must be fresh from the context that prepared and "
            "de-identified the Phase-A input"
        )
    if blind_reviewer in (
        {producer, acceptance_reviewer_context_id}
        | design_context_ids
        | production_context_ids
    ) - {""}:
        errors.append(
            "blind observer must be fresh from design authority, production, "
            "evidence capture, and acceptance review"
        )
    if blind.get("reviewer_freshness") != "FRESH":
        errors.append("blind observation reviewer_freshness must be FRESH")
    attestation = _keys(blind.get("context_attestation"), "blind observation.context_attestation", {"design_authority_read_before_observation", "author_explanation_received", "only_player_surface_materials_used"}, errors)
    if attestation != {"design_authority_read_before_observation": False, "author_explanation_received": False, "only_player_surface_materials_used": True}:
        errors.append("blind observation was produced after answer-bearing authority or author explanation")
    observation = _keys(
        blind.get("observation"),
        "blind observation.observation",
        {"interaction_observations", "lost_or_passive_points"},
        errors,
    )
    raw_attempts = observation.get("interaction_observations")
    if not isinstance(raw_attempts, list) or not raw_attempts:
        errors.append(
            "blind observation.observation.interaction_observations must be a "
            "non-empty sequence"
        )
        raw_attempts = []
    attempt_ids: list[str] = []
    attempt_sequences: list[int] = []
    attempt_artifact_refs: dict[str, set[tuple[str, str]]] = {}
    for index, raw in enumerate(raw_attempts):
        attempt = _keys(
            raw,
            f"blind observation interaction_observations[{index}]",
            {
                "attempt_id", "sequence", "surface_artifacts", "cause", "goal",
                "affordance", "input_and_judgment", "visible_response",
                "persistent_change", "next_motive", "localization_readability",
            },
            errors,
        )
        sequence = attempt.get("sequence")
        if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
            errors.append("blind observation attempt sequence must be a positive integer")
        else:
            attempt_sequences.append(sequence)
        attempt_id = _id(
            attempt.get("attempt_id"),
            f"blind observation interaction_observations[{index}].attempt_id",
            errors,
        )
        if isinstance(sequence, int) and not isinstance(sequence, bool):
            expected_attempt_id = f"attempt.{sequence}"
            if attempt_id != expected_attempt_id:
                errors.append(
                    "blind observation attempt_id must be the neutral sequence id "
                    f"{expected_attempt_id}, not an answer-bearing design label"
                )
        attempt_ids.append(attempt_id)
        cited_artifacts = attempt.get("surface_artifacts")
        if not isinstance(cited_artifacts, list) or not cited_artifacts:
            errors.append("blind observation attempt must cite player-surface artifacts")
            cited_artifacts = []
        cited_ref_set: set[tuple[str, str]] = set()
        for citation_index, raw_ref in enumerate(cited_artifacts):
            cited_ref, _ = _load_ref(
                repo,
                raw_ref,
                f"blind observation attempt[{index}].surface_artifacts[{citation_index}]",
                errors,
            )
            if (cited_ref["path"], cited_ref["sha256"]) not in blind_surface_ref_set:
                errors.append(
                    "blind observation attempt may cite only the sealed blind-input "
                    "player-surface artifacts"
                )
            cited_ref_set.add((cited_ref["path"], cited_ref["sha256"]))
        if attempt_id:
            attempt_artifact_refs[attempt_id] = cited_ref_set
        for field in OBSERVATION_DIMENSIONS:
            _text(
                attempt.get(field),
                f"blind observation interaction_observations[{index}].{field}",
                errors,
            )
        _text(
            attempt.get("localization_readability"),
            f"blind observation interaction_observations[{index}].localization_readability",
            errors,
        )
    if attempt_sequences != list(range(1, len(raw_attempts) + 1)):
        errors.append("blind observation attempt sequence must be contiguous and ordered")
    if len(attempt_ids) != len(set(attempt_ids)):
        errors.append("blind observation attempt_id values must be unique")
    sealed_attempt_ids = set(attempt_ids)
    expected_attempt_ids = {
        f"attempt.{sequence}" for sequence in trace_sequence_order
    }
    if sealed_attempt_ids != expected_attempt_ids:
        errors.append(
            "blind observation must contain exactly one neutral attempt record per "
            "runtime trace sequence"
        )
    final_sequence = trace_sequence_order[-1] if trace_sequence_order else None
    for sequence in trace_sequence_order:
        expected_artifacts = set(trace_surface_refs_by_sequence.get(sequence, set()))
        if sequence == final_sequence:
            expected_artifacts.add((returned_ref["path"], returned_ref["sha256"]))
            expected_artifacts.update(localization_surface_refs)
        attempt_id = f"attempt.{sequence}"
        if attempt_artifact_refs.get(attempt_id, set()) != expected_artifacts:
            errors.append(
                f"blind observation {attempt_id} must bind every and only its "
                "runtime before/during/after capture"
                + (
                    " plus returned/localization surface"
                    if sequence == final_sequence
                    else ""
                )
            )
    if not isinstance(observation.get("lost_or_passive_points"), list):
        errors.append("blind observation.observation.lost_or_passive_points must be an array")
    else:
        for index, value in enumerate(observation["lost_or_passive_points"]):
            _text(value, f"blind observation lost_or_passive_points[{index}]", errors)
    _text(blind.get("observed_at"), "blind observation.observed_at", errors)

    comparison_ref, comparison_path, comparison = loaded["comparison_review"]
    comparison_required = {"schema_version", "review_id", "review_role", "project_id", "unit_id", "game_revision", "build_id", "factory_revision", "runtime_interaction_evidence", "blind_observation", "interaction_contract", "interaction_contract_review", "decision_card", "studio_gameplay_system", "reviewer_context_id", "reviewer_freshness", "context_independence", "beat_comparisons", "hypothesis_observations", "localization_readability", "blocking_findings", "verdict", "reviewed_at"}
    _keys(comparison, "player-facing comparison review", comparison_required, errors)
    if comparison.get("schema_version") != COMPARISON_REVIEW_VERSION:
        errors.append(f"player-facing comparison review schema_version must be {COMPARISON_REVIEW_VERSION}")
    if comparison_path is not None and comparison_path.name != COMPARISON_REVIEW_NAME:
        errors.append(f"player-facing comparison review must be named {COMPARISON_REVIEW_NAME}")
    if comparison.get("review_role") != "PLAYER_FACING_AUTHORITY_COMPARISON":
        errors.append("player-facing comparison review has the wrong review_role")
    for field, expected in (("project_id", project_id), ("unit_id", unit_id), ("game_revision", game_revision), ("build_id", build_id), ("factory_revision", factory_revision)):
        if comparison.get(field) != expected:
            errors.append(f"player-facing comparison review.{field} does not match acceptance")
    _id(comparison.get("review_id"), "player-facing comparison review.review_id", errors)
    for field, expected in (
        ("runtime_interaction_evidence", runtime_ref),
        ("blind_observation", blind_ref),
        ("interaction_contract", expected_contract_ref),
        ("interaction_contract_review", expected_contract_review_ref),
        ("decision_card", expected_card_ref),
        ("studio_gameplay_system", expected_system_ref),
    ):
        actual, _ = _load_ref(repo, comparison.get(field), f"comparison review.{field}", errors)
        _same_ref(actual, expected, f"comparison review {field}", errors)
    comparison_reviewer = _id(comparison.get("reviewer_context_id"), "comparison review.reviewer_context_id", errors)
    if comparison_reviewer in (
        {blind_reviewer, preparer, producer, acceptance_reviewer_context_id}
        | design_context_ids
        | production_context_ids
    ) - {""}:
        errors.append(
            "comparison reviewer must be fresh from design authority, blind-input "
            "preparation, blind observation, production, capture, and acceptance review"
        )
    if comparison.get("reviewer_freshness") != "FRESH":
        errors.append("comparison reviewer_freshness must be FRESH")
    independence = _keys(comparison.get("context_independence"), "comparison review.context_independence", {"blind_record_precedes_authority_access", "blind_observer_context_id", "comparison_reviewer_is_distinct"}, errors)
    if independence.get("blind_record_precedes_authority_access") is not True or independence.get("comparison_reviewer_is_distinct") is not True or independence.get("blind_observer_context_id") != blind_reviewer:
        errors.append("comparison review does not prove blind Phase A / authority Phase B separation")
    raw_comparisons = comparison.get("beat_comparisons")
    if not isinstance(raw_comparisons, list) or not raw_comparisons:
        errors.append("comparison review.beat_comparisons must not be empty")
        raw_comparisons = []
    comparison_beats: list[str] = []
    comparison_attempt_ids: list[str] = []
    for index, raw in enumerate(raw_comparisons):
        item = _keys(raw, f"comparison review.beat_comparisons[{index}]", {"beat_id", "observation_citations", "trace_sequences", *OBSERVATION_DIMENSIONS}, errors)
        comparison_beats.append(_id(item.get("beat_id"), f"comparison review.beat_comparisons[{index}].beat_id", errors))
        citations = _strings(
            item.get("observation_citations"),
            f"comparison review.beat_comparisons[{index}].observation_citations",
            errors,
        )
        comparison_attempt_ids.extend(citations)
        if not set(citations).issubset(sealed_attempt_ids):
            errors.append(
                "comparison review beat cites an observation that is absent from the "
                "sealed blind record"
            )
        sequences = item.get("trace_sequences")
        if not isinstance(sequences, list) or not sequences or any(not isinstance(value, int) for value in sequences):
            errors.append("comparison review beat trace_sequences must cite runtime trace integers")
        elif not set(sequences).issubset(trace_sequences):
            errors.append("comparison review cites unknown runtime trace sequences")
        else:
            beat_id = item.get("beat_id")
            expected_sequences = [
                int(trace_item.get("sequence"))
                for trace_item in trace
                if trace_item.get("beat_id") == beat_id
                and isinstance(trace_item.get("sequence"), int)
                and not isinstance(trace_item.get("sequence"), bool)
            ]
            if sequences != expected_sequences:
                errors.append(
                    f"comparison review beat {beat_id} must cite every and only its "
                    "runtime trace sequence in order"
                )
            expected_attempt_citations = [
                f"attempt.{sequence}" for sequence in expected_sequences
            ]
            if citations != expected_attempt_citations:
                errors.append(
                    f"comparison review beat {beat_id} must cite the neutral blind "
                    "attempts corresponding to its runtime trace sequences"
                )
            required_trace_artifacts = set().union(
                *(
                    trace_surface_refs_by_sequence.get(sequence, set())
                    for sequence in sequences
                )
            ) if sequences else set()
            cited_attempt_artifacts = set().union(
                *(attempt_artifact_refs.get(citation, set()) for citation in citations)
            ) if citations else set()
            if not required_trace_artifacts.issubset(cited_attempt_artifacts):
                errors.append(
                    f"comparison review beat {beat_id} cites blind attempts that do "
                    "not contain its complete before/during/after player-surface capture"
                )
        for dimension in OBSERVATION_DIMENSIONS:
            if item.get(dimension) != "OBSERVED":
                errors.append(f"comparison review beat {item.get('beat_id', '')}.{dimension} must be OBSERVED")
    if set(comparison_beats) != trace_beat_ids or len(comparison_beats) != len(set(comparison_beats)):
        errors.append("comparison review must exactly cover every runtime playable beat")
    if set(comparison_attempt_ids) != sealed_attempt_ids:
        errors.append(
            "comparison review must cite every sealed blind interaction observation"
        )
    if len(comparison_attempt_ids) != len(set(comparison_attempt_ids)):
        errors.append(
            "comparison review cannot reuse one blind interaction observation for "
            "multiple gameplay beats"
        )
    outcomes = comparison.get("hypothesis_observations")
    if not isinstance(outcomes, list):
        errors.append("comparison review.hypothesis_observations must be an array")
        outcomes = []
    observed_hypotheses: list[str] = []
    for index, raw in enumerate(outcomes):
        item = _keys(raw, f"comparison review.hypothesis_observations[{index}]", {"claim_id", "status", "observation_citations", "rationale"}, errors)
        observed_hypotheses.append(_id(item.get("claim_id"), f"comparison hypothesis[{index}].claim_id", errors))
        if item.get("status") != "OBSERVED_SUPPORT":
            errors.append("accepted player-facing comparison requires OBSERVED_SUPPORT, not design-stage PASS or rejected evidence")
        citations = _strings(item.get("observation_citations"), f"comparison hypothesis[{index}].observation_citations", errors)
        if not set(citations).issubset(sealed_attempt_ids):
            errors.append("comparison hypothesis cites evidence absent from the sealed blind record")
        _text(item.get("rationale"), f"comparison hypothesis[{index}].rationale", errors)
    if set(observed_hypotheses) != hypothesis_ids or len(observed_hypotheses) != len(set(observed_hypotheses)):
        errors.append("comparison review hypothesis observations must exactly cover Card hypotheses")
    comparison_locale = _keys(comparison.get("localization_readability"), "comparison review.localization_readability", {"status", "observation_citations"}, errors)
    if comparison_locale.get("status") != "OBSERVED_READABLE":
        errors.append("comparison review must observe readable target localization")
    locale_citations = _strings(comparison_locale.get("observation_citations"), "comparison review.localization_readability.observation_citations", errors)
    if not set(locale_citations).issubset(sealed_attempt_ids):
        errors.append("comparison localization cites evidence absent from the sealed blind record")
    if comparison.get("blocking_findings") != []:
        errors.append("comparison review.blocking_findings must be empty")
    if comparison.get("verdict") != PASS_PLAYER_FACING_COMPARISON:
        errors.append(f"comparison review.verdict must be {PASS_PLAYER_FACING_COMPARISON}")
    _text(comparison.get("reviewed_at"), "comparison review.reviewed_at", errors)

    return {
        "runtime_interaction_evidence": runtime_ref,
        "blind_observation_input": blind_input_ref,
        "blind_observation": blind_ref,
        "comparison_review": comparison_ref,
        "producer_context_id": producer,
        "blind_reviewer_context_id": blind_reviewer,
        "comparison_reviewer_context_id": comparison_reviewer,
    }
