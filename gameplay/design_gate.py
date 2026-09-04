"""Validate the compact human decision and full-spec conformance gate.

The human approves a deliberately small ``GAMEPLAY_DECISION_CARD.json``.  The
larger ``OBJECTIVE_GAMEPLAY.md`` is implementation authority only after two
fresh, independent reviews prove both directions of the refinement relation:

* every card claim is realized by the spec (card -> spec completeness); and
* every material spec item is authorized by the card (spec -> card
  non-expansion).

For Studio-routed work, the card must also bind a validated, cycle-complete
Idea-to-gameplay system.  A result/replay sequence is therefore unable to enter
production merely by being described in more detail.  Before human
presentation, a separate fresh final-Card reviewer must inventory the exact
Card and pass every Factory-compliance finding due at that boundary; semantic
alignment remains a different later gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:  # Package import in tests; direct script import for Gameplay CLI use.
    from studio.alignment import (
        AlignmentValidationError,
        HUMAN_RULING_GENUINELY_REQUIRED,
        record_card_verdict,
        register_pending_card,
        require_registered_card,
        validate_alignment_review,
    )
    from studio.cycle import (
        READY as STUDIO_GAMEPLAY_SYSTEM_READY,
        CycleValidationError,
        validate_gameplay_system,
    )
    from studio.player_surface import (
        INTERACTION_CONTRACT_NAME,
        INTERACTION_CONTRACT_REVIEW_NAME,
        validate_interaction_contract,
        validate_interaction_contract_review,
    )
except ModuleNotFoundError:  # pragma: no cover - direct CLI smoke path.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from studio.alignment import (  # type: ignore[no-redef]
        AlignmentValidationError,
        HUMAN_RULING_GENUINELY_REQUIRED,
        record_card_verdict,
        register_pending_card,
        require_registered_card,
        validate_alignment_review,
    )
    from studio.cycle import (  # type: ignore[no-redef]
        READY as STUDIO_GAMEPLAY_SYSTEM_READY,
        CycleValidationError,
        validate_gameplay_system,
    )
    from studio.player_surface import (  # type: ignore[no-redef]
        INTERACTION_CONTRACT_NAME,
        INTERACTION_CONTRACT_REVIEW_NAME,
        validate_interaction_contract,
        validate_interaction_contract_review,
    )


DESIGN_VERDICT_NAME = "GAMEPLAY_DESIGN_VERDICT.json"
DECISION_CARD_NAME = "GAMEPLAY_DECISION_CARD.json"
CARD_FACTORY_REVIEW_NAME = "GAMEPLAY_DECISION_CARD_FACTORY_REVIEW.json"
CARD_FACTORY_REVIEW_AUTHORITY_ID = "card.factory-compliance-review"
CARD_TO_SPEC_REVIEW_NAME = "GAMEPLAY_CONFORMANCE_CARD_TO_SPEC.json"
SPEC_TO_CARD_REVIEW_NAME = "GAMEPLAY_CONFORMANCE_SPEC_TO_CARD.json"

DESIGN_VERDICT_VERSION = "gameplay_design_verdict.v2"
LEGACY_DESIGN_VERDICT_VERSION = "gameplay_design_verdict.v1"
DECISION_CARD_VERSION = "gameplay_decision_card.v2"
LEGACY_DECISION_CARD_VERSION = "gameplay_decision_card.v1"
CARD_FACTORY_REVIEW_VERSION = "gameplay_decision_card_factory_review.v2"
CONFORMANCE_REVIEW_VERSION = "gameplay_design_conformance_review.v2"
LEGACY_CONFORMANCE_REVIEW_VERSION = "gameplay_design_conformance_review.v1"

PASS_CARD_FACTORY_REVIEW = "PASS_CARD_FACTORY_COMPLIANCE"
FINAL_CARD_REQUIREMENT_IDS = (
    "active_authority_and_scope_preserved",
    "minimum_cycle_complete_slice",
    "playable_span_sufficiency_not_inflated",
    "meaningful_choice_not_certain_click",
    "non_gameplay_activity_not_counted",
    "player_work_world_response_carry_forward",
    "reward_changes_next_decision",
    "two_lap_decision_materially_differs",
    "declared_alternatives_materially_distinct_and_reachable",
    "cost_obligation_failure_and_recovery_are_concrete",
    "red_lines_and_hypotheses_are_falsifiable",
    "applicable_factory_gates_complete",
    "player_facing_interaction_concretely_designed",
    "downstream_work_not_misrepresented_as_complete",
)
FINAL_CARD_REQUIREMENT_CLAIM_PREFIXES = {
    "active_authority_and_scope_preserved": ("promise.", "commitment."),
    "minimum_cycle_complete_slice": ("cycle.", "commitment."),
    "playable_span_sufficiency_not_inflated": ("cycle.",),
    "meaningful_choice_not_certain_click": ("cycle.",),
    "non_gameplay_activity_not_counted": ("redline.",),
    "player_work_world_response_carry_forward": ("cycle.",),
    "reward_changes_next_decision": ("cycle.",),
    "two_lap_decision_materially_differs": ("cycle.",),
    "declared_alternatives_materially_distinct_and_reachable": ("commitment.",),
    "cost_obligation_failure_and_recovery_are_concrete": ("commitment.",),
    "red_lines_and_hypotheses_are_falsifiable": ("redline.",),
    "applicable_factory_gates_complete": (
        "promise.", "cycle.", "commitment.", "redline."
    ),
    "player_facing_interaction_concretely_designed": ("cycle.",),
    "downstream_work_not_misrepresented_as_complete": ("redline.",),
}

DECISION_PAYLOAD_FIELDS = (
    "schema_version", "card_id", "project_id", "objective_id",
    "factory_revision", "routing", "product_authority",
    "studio_gameplay_system", "author_context_id", "player_promise",
    "player_facing_interaction_contract",
    "player_facing_interaction_contract_review",
    "core_cycle", "material_commitments", "red_lines",
    "validation_hypotheses",
)
LEGACY_DECISION_PAYLOAD_FIELDS = tuple(
    field
    for field in DECISION_PAYLOAD_FIELDS
    if field not in {
        "player_facing_interaction_contract",
        "player_facing_interaction_contract_review",
    }
)

FACTORY_REVISION_PATTERN = re.compile(r"^[0-9a-f]{7,64}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*$")

READY_FOR_HOW_DESIGN = "READY_FOR_HOW_DESIGN"
READY_FOR_NEW_GAMEPLAY_DESIGN = "READY_FOR_NEW_GAMEPLAY_DESIGN"
CONTEXT_STATUSES = {READY_FOR_HOW_DESIGN, READY_FOR_NEW_GAMEPLAY_DESIGN}
HUMAN_VERDICTS = {"USER_APPROVED", "USER_DELEGATED"}

_CONTEXT_STATUS_PATTERN = re.compile(
    r"^- Context status:\s*`([^`]+)`\s*$", re.MULTILINE
)
_DESIGN_STATUS_PATTERN = re.compile(
    r"^- Design status:\s*`([^`]+)`\s*$", re.MULTILINE
)
_AUTHOR_CONTEXT_PATTERN = re.compile(
    r"^- Author context id:\s*`([^`]+)`\s*$", re.MULTILINE
)
_OBJECTIVE_PATTERN = re.compile(r"^- Objective:\s*(.+)$", re.MULTILINE)

EXPECTED_EXPERIENCE_FIELDS = (
    ("target_player", "Target player"),
    ("intended_experience", "Intended experience"),
    ("required_player_work", "Required player work"),
    ("earned_satisfaction", "Earned satisfaction"),
    ("failure_recovery", "Failure / recovery"),
    ("must_not_become", "Must not become"),
)
ALLOWED_MATERIAL_HEADINGS = {
    "Expected player experience",
    "New gameplay additions",
    "Completion handoff",
}
CANONICAL_TABLE_HEADER = (
    "| # | Situation / objective progress | Player purpose or problem | "
    "Visible information | Available actions | Rewards / consequences | "
    "Meaningful decision or execution | Resulting next situation |"
)
CANONICAL_TABLE_SEPARATOR = (
    "| --- | --- | --- | --- | --- | --- | --- | --- |"
)


@dataclass(frozen=True)
class DesignGateBinding:
    """Validated, exact design authority used by a production manifest."""

    factory_revision: str
    verdict_path: str
    verdict_sha256: str
    context_status: str
    human_verdict: str
    decision_card_path: str = ""
    decision_card_sha256: str = ""
    studio_gameplay_system_path: str = ""
    studio_gameplay_system_sha256: str = ""
    cycle_id: str = ""


@dataclass(frozen=True)
class CardFactoryReviewResult:
    """Validation result for the final independent pre-human Card audit."""

    status: str
    errors: list[str]
    reviewer_context_id: str = ""
    review_path: str = ""


def current_factory_revision(factory_root: Path) -> str:
    """Return the exact Factory commit whose contracts are being executed."""

    result = subprocess.run(
        ["git", "-C", str(factory_root), "rev-parse", "HEAD"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    revision = result.stdout.strip()
    if result.returncode != 0 or FACTORY_REVISION_PATTERN.fullmatch(revision) is None:
        detail = result.stderr.strip() or "Factory checkout has no readable HEAD"
        raise ValueError(detail)
    return revision


def decision_payload_sha256(card: dict[str, Any]) -> str:
    """Hash exactly the compact material surface on which the human rules."""

    fields = (
        LEGACY_DECISION_PAYLOAD_FIELDS
        if card.get("schema_version") == LEGACY_DECISION_CARD_VERSION
        else DECISION_PAYLOAD_FIELDS
    )
    payload = {field: card.get(field) for field in fields}
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def render_decision_card(card: dict[str, Any]) -> str:
    """Render only the bounded material surface intended for human review."""

    digest = decision_payload_sha256(card)
    promise = card.get("player_promise")
    promise_text = promise.get("text", "") if isinstance(promise, dict) else ""
    lines = [
        f"# Gameplay Decision Card — {card.get('objective_id', '')}",
        "",
        f"**Promise:** {promise_text}",
        "",
        "## Core cycle",
    ]
    for index, item in enumerate(card.get("core_cycle", []), start=1):
        if isinstance(item, dict):
            lines.append(f"{index}. {item.get('text', '')}")
    lines.extend(["", "## Commitments"])
    for item in card.get("material_commitments", []):
        if isinstance(item, dict):
            lines.append(f"- {item.get('text', '')}")
    lines.extend(["", "## Red lines"])
    for item in card.get("red_lines", []):
        if isinstance(item, dict):
            lines.append(f"- {item.get('text', '')}")
    hypotheses = card.get("validation_hypotheses", [])
    if hypotheses:
        lines.extend(["", "## Validation hypotheses"])
        for item in hypotheses:
            if isinstance(item, dict):
                lines.append(
                    f"- {item.get('text', '')} — reject if: "
                    f"{item.get('falsification_signal', '')}"
                )
    lines.extend([
        "",
        f"**Decision payload:** `{digest}`",
        f"Reply: `USER_APPROVED {digest}`",
        "",
    ])
    return "\n".join(lines)


def _require_exact_keys(
    payload: Any,
    label: str,
    required: set[str],
    errors: list[str],
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        errors.append(f"{label} must be an object")
        return {}
    for key in sorted(required - set(payload)):
        errors.append(f"{label} is missing {key}")
    for key in sorted(set(payload) - required):
        errors.append(f"{label} contains unsupported field {key}")
    return payload


def _require_text(value: Any, label: str, errors: list[str]) -> str:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label} must be a non-empty string")
        return ""
    text = value.strip()
    if "TBD" in text:
        errors.append(f"{label} must not contain TBD")
    return text


def _require_id(value: Any, label: str, errors: list[str]) -> str:
    result = _require_text(value, label, errors)
    if result and ID_PATTERN.fullmatch(result) is None:
        errors.append(f"{label} must match {ID_PATTERN.pattern}")
    return result


def _load_json(path: Path, label: str, errors: list[str]) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        errors.append(f"cannot read {label} JSON: {error}")
        return {}
    if not isinstance(payload, dict):
        errors.append(f"{label} must be a JSON object")
        return {}
    return payload


def _validate_path_hash(
    game_repo: Path,
    raw_ref: Any,
    label: str,
    errors: list[str],
) -> tuple[str, str, Path | None]:
    ref = _require_exact_keys(raw_ref, label, {"path", "sha256"}, errors)
    path_text = _require_text(ref.get("path"), f"{label}.path", errors)
    digest = _require_text(ref.get("sha256"), f"{label}.sha256", errors)
    if not path_text or not digest:
        return path_text, digest, None
    candidate = Path(path_text)
    if candidate.is_absolute():
        errors.append(f"{label}.path must be game-repo-relative")
        return path_text, digest, None
    path = (game_repo / candidate).resolve()
    try:
        path.relative_to(game_repo)
    except ValueError:
        errors.append(f"{label}.path escapes the game repo")
        return path_text, digest, None
    if not path.is_file():
        errors.append(f"{label}.path does not identify a file: {path_text}")
        return path_text, digest, None
    if SHA256_PATTERN.fullmatch(digest) is None:
        errors.append(f"{label}.sha256 must be 64 lowercase hex characters")
    elif hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        errors.append(f"{label} hash does not match {path_text}")
    return path_text, digest, path


def _validate_optional_path_hash(
    game_repo: Path,
    raw_ref: Any,
    label: str,
    errors: list[str],
) -> tuple[str, str, Path | None]:
    ref = _require_exact_keys(raw_ref, label, {"path", "sha256"}, errors)
    path_value = ref.get("path")
    digest_value = ref.get("sha256")
    path_text = path_value.strip() if isinstance(path_value, str) else ""
    digest = digest_value.strip() if isinstance(digest_value, str) else ""
    if bool(path_text) != bool(digest):
        errors.append(f"{label}.path and .sha256 must both be empty or both be filled")
        return path_text, digest, None
    if not path_text:
        if path_value != "" or digest_value != "":
            errors.append(f"{label} empty values must be exact empty strings")
        return "", "", None
    return _validate_path_hash(game_repo, raw_ref, label, errors)


def _validate_ref_equals(
    actual_path: str,
    actual_sha: str,
    expected_path: str,
    expected_sha: str,
    label: str,
    errors: list[str],
) -> None:
    if actual_path != expected_path or actual_sha != expected_sha:
        errors.append(f"{label} does not bind the exact authority")


def _validate_claim(
    value: Any,
    label: str,
    *,
    max_length: int,
    errors: list[str],
    hypothesis: bool = False,
    require_hypothesis_status: bool = True,
) -> str:
    keys = {"claim_id", "text"}
    if hypothesis:
        keys.add("falsification_signal")
        if require_hypothesis_status:
            keys.add("status")
    payload = _require_exact_keys(value, label, keys, errors)
    claim_id = _require_id(payload.get("claim_id"), f"{label}.claim_id", errors)
    text = _require_text(payload.get("text"), f"{label}.text", errors)
    if len(text) > max_length:
        errors.append(f"{label}.text exceeds {max_length} characters")
    if hypothesis:
        if require_hypothesis_status and payload.get("status") != "TESTABLE_DESIGN":
            errors.append(
                f"{label}.status must be TESTABLE_DESIGN; design hypotheses "
                "cannot be labelled PASS or ACCEPTED"
            )
        signal = _require_text(
            payload.get("falsification_signal"),
            f"{label}.falsification_signal",
            errors,
        )
        if len(signal) > 160:
            errors.append(f"{label}.falsification_signal exceeds 160 characters")
    return claim_id


def _validate_claim_list(
    value: Any,
    label: str,
    *,
    minimum: int,
    maximum: int,
    text_limit: int,
    errors: list[str],
    hypothesis: bool = False,
    require_hypothesis_status: bool = True,
) -> list[str]:
    if not isinstance(value, list):
        errors.append(f"{label} must be an array")
        return []
    if not minimum <= len(value) <= maximum:
        errors.append(f"{label} must contain {minimum}-{maximum} items")
    return [
        _validate_claim(
            item,
            f"{label}[{index}]",
            max_length=text_limit,
            errors=errors,
            hypothesis=hypothesis,
            require_hypothesis_status=require_hypothesis_status,
        )
        for index, item in enumerate(value)
    ]


def _validate_studio_system_binding(
    *,
    game_repo: Path,
    project_id: str,
    factory_revision: str,
    product_ref: tuple[str, str, Path | None],
    system_ref: tuple[str, str, Path | None],
    errors: list[str],
) -> tuple[str, list[str], dict[str, Any], set[str]]:
    product_path_text, product_sha, _ = product_ref
    system_path_text, system_sha, system_manifest_path = system_ref
    if product_path_text != "design/product/PRODUCT_THESIS.md":
        errors.append(
            "Studio decision card product_authority.path must be "
            "design/product/PRODUCT_THESIS.md"
        )
    if system_manifest_path is None:
        errors.append("Studio decision card must bind a gameplay system manifest")
        return "", [], {}, set()
    try:
        result = validate_gameplay_system(
            str(game_repo),
            system_path_text,
            expected_factory_revision=factory_revision,
        )
    except CycleValidationError as error:
        errors.append(f"cannot validate Studio gameplay system: {error}")
        return "", [], {}, set()
    if result.status != STUDIO_GAMEPLAY_SYSTEM_READY:
        errors.extend(f"Studio gameplay system: {item}" for item in result.errors)
    if result.manifest_path != system_path_text or result.manifest_sha256 != system_sha:
        errors.append("decision card does not bind the exact validated Studio manifest")

    manifest = _load_json(system_manifest_path, "Studio gameplay system manifest", errors)
    if manifest.get("project_id") != project_id:
        errors.append("Studio gameplay system project_id does not match decision card")
    _, _, gameplay_system_path = _validate_path_hash(
        game_repo,
        manifest.get("gameplay_system"),
        "Studio manifest.gameplay_system",
        errors,
    )
    system: dict[str, Any] = {}
    prior_context_ids: set[str] = set()
    if gameplay_system_path is not None:
        system = _load_json(gameplay_system_path, "Studio gameplay system", errors)
        if isinstance(system.get("author_context_id"), str):
            prior_context_ids.add(system["author_context_id"])
        bound_product = system.get("product_authority")
        if not isinstance(bound_product, dict) or (
            bound_product.get("path") != product_path_text
            or bound_product.get("sha256") != product_sha
        ):
            errors.append(
                "decision card product authority differs from the validated Studio system"
            )
    reviews = manifest.get("reviews")
    if isinstance(reviews, dict):
        for key, raw_ref in reviews.items():
            _, _, review_path = _validate_path_hash(
                game_repo, raw_ref, f"Studio manifest.reviews.{key}", errors
            )
            if review_path is not None:
                review = _load_json(review_path, f"Studio system {key} review", errors)
                reviewer = review.get("reviewer_context_id")
                if isinstance(reviewer, str) and reviewer:
                    prior_context_ids.add(reviewer)
    return result.cycle_id, result.feedback_state_ids, system, prior_context_ids


def _validate_studio_card_projection(
    card: dict[str, Any], system: dict[str, Any], errors: list[str]
) -> None:
    """Require the human card's core to be a deterministic system projection."""

    if not system:
        return
    expected_promise = {
        "claim_id": "promise.system",
        "text": system.get("system_promise"),
    }
    if card.get("player_promise") != expected_promise:
        errors.append(
            "Studio decision card player_promise must be the exact gameplay-system promise"
        )

    transitions = {
        item.get("transition_id"): item
        for item in system.get("transitions", [])
        if isinstance(item, dict)
    }
    expected_cycle: list[dict[str, str]] = []
    for transition_id in system.get("cycle_path", []):
        transition = transitions.get(transition_id, {})
        text = " -> ".join(
            str(transition.get(field, ""))
            for field in ("player_action", "visible_consequence", "motivation_effect")
        )
        expected_cycle.append(
            {"claim_id": f"cycle.{transition_id}", "text": text}
        )
    if card.get("core_cycle") != expected_cycle:
        errors.append(
            "Studio decision card core_cycle must be the exact ordered gameplay-system projection"
        )

    commitments = card.get("material_commitments")
    if isinstance(commitments, list):
        expected_commitments = [
            {
                "claim_id": f"commitment.{item.get('component_id')}",
                "text": item.get("role"),
            }
            for item in system.get("coupled_systems", [])
            if isinstance(item, dict)
        ]
        for expected in expected_commitments:
            if expected not in commitments:
                errors.append(
                    "Studio decision card omits coupled-system commitment "
                    + str(expected.get("claim_id", ""))
                )
        expected_ids = {item["claim_id"] for item in expected_commitments}
        for item in commitments:
            if not isinstance(item, dict):
                continue
            claim_id = item.get("claim_id")
            if claim_id not in expected_ids and not str(claim_id).startswith("scope."):
                errors.append(
                    "Studio decision card additional commitments must use scope.* claim ids"
                )

    red_lines = card.get("red_lines")
    if isinstance(red_lines, list):
        expected_red_lines = [
            {"claim_id": f"redline.{index}", "text": text}
            for index, text in enumerate(
                system.get("forbidden_linearizations", []), start=1
            )
        ]
        for expected in expected_red_lines:
            if expected not in red_lines:
                errors.append(
                    "Studio decision card omits system red line "
                    + str(expected.get("claim_id", ""))
                )
        expected_ids = {item["claim_id"] for item in expected_red_lines}
        for item in red_lines:
            if not isinstance(item, dict):
                continue
            claim_id = item.get("claim_id")
            if claim_id not in expected_ids and not str(claim_id).startswith("scope."):
                errors.append(
                    "Studio decision card additional red lines must use scope.* claim ids"
                )


def _validate_decision_card(
    *,
    game_repo: Path,
    card_path: Path,
    project_id: str,
    objective_id: str,
    factory_revision: str,
    context_status: str,
    errors: list[str],
    pre_human_review: bool = False,
    allow_legacy_historical: bool = False,
) -> dict[str, Any]:
    game_repo = game_repo.resolve()
    card_path = card_path.resolve()
    card = _load_json(card_path, "gameplay decision card", errors)
    version = card.get("schema_version")
    legacy_card = (
        version == LEGACY_DECISION_CARD_VERSION and allow_legacy_historical
    )
    required = {
        "schema_version", "card_id", "project_id", "objective_id",
        "factory_revision", "routing", "product_authority",
        "studio_gameplay_system", "author_context_id", "player_promise",
        "core_cycle", "material_commitments", "red_lines",
        "validation_hypotheses", "decision_payload_sha256", "human_verdict",
    }
    if not legacy_card:
        required |= {
            "player_facing_interaction_contract",
            "player_facing_interaction_contract_review",
        }
    _require_exact_keys(card, "gameplay decision card", required, errors)
    if version != DECISION_CARD_VERSION and not legacy_card:
        errors.append(
            f"gameplay decision card schema_version must be {DECISION_CARD_VERSION}; "
            f"{LEGACY_DECISION_CARD_VERSION} is readable only in historical checks"
        )
    _require_id(card.get("card_id"), "gameplay decision card.card_id", errors)
    if card.get("project_id") != project_id:
        errors.append("gameplay decision card project_id does not match manifest")
    if card.get("objective_id") != objective_id:
        errors.append("gameplay decision card objective_id does not match manifest")
    if card.get("factory_revision") != factory_revision:
        errors.append("gameplay decision card factory_revision does not match manifest")
    declared_payload_sha = _require_text(
        card.get("decision_payload_sha256"),
        "gameplay decision card.decision_payload_sha256",
        errors,
    )
    actual_payload_sha = decision_payload_sha256(card)
    if SHA256_PATTERN.fullmatch(declared_payload_sha) is None:
        errors.append("gameplay decision card decision_payload_sha256 is invalid")
    elif declared_payload_sha != actual_payload_sha:
        errors.append(
            "gameplay decision card decision_payload_sha256 does not match its material surface"
        )
    author_context_id = _require_id(
        card.get("author_context_id"),
        "gameplay decision card.author_context_id",
        errors,
    )

    promise_id = _validate_claim(
        card.get("player_promise"),
        "gameplay decision card.player_promise",
        max_length=160,
        errors=errors,
    )
    cycle_ids = _validate_claim_list(
        card.get("core_cycle"),
        "gameplay decision card.core_cycle",
        minimum=3,
        maximum=10,
        text_limit=300,
        errors=errors,
    )
    commitment_ids = _validate_claim_list(
        card.get("material_commitments"),
        "gameplay decision card.material_commitments",
        minimum=1,
        maximum=8,
        text_limit=180,
        errors=errors,
    )
    red_line_ids = _validate_claim_list(
        card.get("red_lines"),
        "gameplay decision card.red_lines",
        minimum=1,
        maximum=6,
        text_limit=180,
        errors=errors,
    )
    hypothesis_ids = _validate_claim_list(
        card.get("validation_hypotheses"),
        "gameplay decision card.validation_hypotheses",
        minimum=0,
        maximum=3,
        text_limit=120,
        errors=errors,
        hypothesis=True,
        require_hypothesis_status=not legacy_card,
    )
    claim_ids = [promise_id, *cycle_ids, *commitment_ids, *red_line_ids, *hypothesis_ids]
    claim_ids = [item for item in claim_ids if item]
    if len(claim_ids) != len(set(claim_ids)):
        errors.append("gameplay decision card claim_id values must be globally unique")

    product_ref = _validate_optional_path_hash(
        game_repo, card.get("product_authority"), "decision card.product_authority", errors
    )
    system_ref = _validate_optional_path_hash(
        game_repo,
        card.get("studio_gameplay_system"),
        "decision card.studio_gameplay_system",
        errors,
    )
    routing = card.get("routing")
    cycle_id = ""
    feedback_state_ids: list[str] = []
    studio_system: dict[str, Any] = {}
    studio_context_ids: set[str] = set()
    if routing == "STUDIO_WHOLE_GAME":
        (
            cycle_id,
            feedback_state_ids,
            studio_system,
            studio_context_ids,
        ) = _validate_studio_system_binding(
            game_repo=game_repo,
            project_id=project_id,
            factory_revision=factory_revision,
            product_ref=product_ref,
            system_ref=system_ref,
            errors=errors,
        )
        _validate_studio_card_projection(card, studio_system, errors)
    elif routing == "DIRECT_SPECIALIST":
        if system_ref[0]:
            (
                cycle_id,
                feedback_state_ids,
                studio_system,
                studio_context_ids,
            ) = _validate_studio_system_binding(
                game_repo=game_repo,
                project_id=project_id,
                factory_revision=factory_revision,
                product_ref=product_ref,
                system_ref=system_ref,
                errors=errors,
            )
    else:
        errors.append("gameplay decision card routing is unsupported")

    expected_transition_ids = [
        str(item) for item in studio_system.get("cycle_path", [])
    ] if studio_system else [
        claim_id.removeprefix("cycle.") for claim_id in cycle_ids
        if claim_id.startswith("cycle.")
    ]
    contract_binding: dict[str, Any] = {}
    contract_review_binding: dict[str, Any] = {}
    if not legacy_card:
        contract_binding = validate_interaction_contract(
            game_repo,
            card.get("player_facing_interaction_contract"),
            project_id=project_id,
            objective_id=objective_id,
            factory_revision=factory_revision,
            product_authority={"path": product_ref[0], "sha256": product_ref[1]},
            studio_gameplay_system={"path": system_ref[0], "sha256": system_ref[1]},
            expected_transition_ids=expected_transition_ids,
            errors=errors,
        )
        contract_review_binding = validate_interaction_contract_review(
            game_repo,
            card.get("player_facing_interaction_contract_review"),
            contract=contract_binding,
            product_authority={"path": product_ref[0], "sha256": product_ref[1]},
            studio_gameplay_system={"path": system_ref[0], "sha256": system_ref[1]},
            forbidden_context_ids={author_context_id, *studio_context_ids} - {""},
            errors=errors,
        )

    human = _require_exact_keys(
        card.get("human_verdict"),
        "gameplay decision card.human_verdict",
        {"status", "source_text", "recorded_at"},
        errors,
    )
    human_status = human.get("status", "")
    if pre_human_review:
        if human_status != "PENDING":
            errors.append("pre-human decision-card review requires a PENDING card")
    else:
        if human_status not in HUMAN_VERDICTS:
            errors.append("gameplay decision card requires an approving human verdict")
        if routing == "STUDIO_WHOLE_GAME" and human_status != "USER_APPROVED":
            errors.append(
                "Studio whole-game decision cards require USER_APPROVED; delegation is insufficient"
            )
        if context_status == READY_FOR_NEW_GAMEPLAY_DESIGN and human_status != "USER_APPROVED":
            errors.append(
                "new gameplay design requires USER_APPROVED on the decision card; "
                "delegation is insufficient"
            )
    source_text = _require_text(
        human.get("source_text"), "human_verdict.source_text", errors
    )
    expected_source = "PENDING" if pre_human_review else f"{human_status} {actual_payload_sha}"
    if source_text and source_text != expected_source:
        errors.append(
            "human_verdict.source_text must be the exact verdict token plus decision payload SHA"
        )
    if isinstance(human.get("source_text"), str) and len(human["source_text"]) > 500:
        errors.append("human_verdict.source_text exceeds 500 characters")
    _require_text(human.get("recorded_at"), "human_verdict.recorded_at", errors)

    card_binding = {
        "claim_ids": set(claim_ids),
        "hypothesis_ids": set(hypothesis_ids),
        "author_context_id": author_context_id,
        "human_status": human_status,
        "routing": routing,
        "system_path": system_ref[0],
        "system_sha": system_ref[1],
        "cycle_id": cycle_id,
        "feedback_state_ids": feedback_state_ids,
        "studio_context_ids": studio_context_ids,
        "interaction_contract": contract_binding,
        "interaction_contract_review": contract_review_binding,
        "product_authority": card.get("product_authority", {}),
        "product_causal_link_ids": {
            str(item.get("link_id"))
            for item in studio_system.get("causal_link_coverage", [])
            if isinstance(item, dict) and item.get("link_id")
        },
        "factory_constraint_ids": {
            str(item.get("constraint_id"))
            for item in studio_system.get("constraint_coverage", [])
            if isinstance(item, dict) and item.get("constraint_id")
        },
        "product_non_goal_ids": {
            str(item.get("non_goal_id"))
            for item in studio_system.get("non_goal_coverage", [])
            if isinstance(item, dict) and item.get("non_goal_id")
        },
        "product_causal_link_coverage": {
            str(item.get("link_id")): {
                str(value) for value in item.get("transition_ids", [])
            }
            for item in studio_system.get("causal_link_coverage", [])
            if isinstance(item, dict) and item.get("link_id")
        },
        "factory_constraint_coverage": {
            str(item.get("constraint_id")): {
                str(value) for value in item.get("transition_ids", [])
            }
            for item in studio_system.get("constraint_coverage", [])
            if isinstance(item, dict) and item.get("constraint_id")
        },
        "product_non_goal_coverage": {
            str(item.get("non_goal_id")): {
                str(value) for value in item.get("transition_ids", [])
            }
            for item in studio_system.get("non_goal_coverage", [])
            if isinstance(item, dict) and item.get("non_goal_id")
        },
    }

    if routing == "STUDIO_WHOLE_GAME" and not pre_human_review and not legacy_card:
        entry = require_registered_card(
            game_repo,
            card_path,
            required_state="USER_APPROVED",
            errors=errors,
        )
        forbidden_context_ids: set[str] = set()
        if entry:
            _, _, alignment_input_path = _validate_path_hash(
                game_repo,
                entry.get("alignment_input"),
                "registered decision card alignment_input",
                errors,
            )
            _, _, alignment_review_path = _validate_path_hash(
                game_repo,
                entry.get("alignment_review"),
                "registered decision card alignment_review",
                errors,
            )
            if alignment_review_path is not None:
                alignment_review = _load_json(
                    alignment_review_path, "registered semantic alignment review", errors
                )
                alignment_reviewer = alignment_review.get("reviewer_context_id")
                if isinstance(alignment_reviewer, str) and alignment_reviewer:
                    forbidden_context_ids.add(alignment_reviewer)
            if alignment_input_path is not None and alignment_review_path is not None:
                try:
                    alignment_result = validate_alignment_review(
                        game_repo,
                        alignment_input_path,
                        alignment_review_path,
                        expected_output_text=render_decision_card(card),
                        expected_output_kind="DECISION_SURFACE",
                    )
                except AlignmentValidationError as error:
                    errors.append(str(error))
                else:
                    errors.extend(alignment_result.errors)
                    if alignment_result.status != HUMAN_RULING_GENUINELY_REQUIRED:
                        errors.append(
                            "registered Studio decision surface lacks a valid "
                            "HUMAN_RULING_GENUINELY_REQUIRED alignment verdict"
                        )
        _validate_card_factory_review_artifact(
            game_repo=game_repo,
            card_path=card_path,
            card=card,
            card_binding=card_binding,
            review_path=card_path.with_name(CARD_FACTORY_REVIEW_NAME),
            forbidden_context_ids=forbidden_context_ids,
            errors=errors,
        )

    return card_binding


def _validate_card_factory_review_artifact(
    *,
    game_repo: Path,
    card_path: Path,
    card: dict[str, Any],
    card_binding: dict[str, Any],
    review_path: Path,
    forbidden_context_ids: set[str],
    errors: list[str],
) -> str:
    expected_review_path = card_path.with_name(CARD_FACTORY_REVIEW_NAME).resolve()
    if review_path.resolve() != expected_review_path:
        errors.append(
            "final Card Factory review must be the objective-local "
            + CARD_FACTORY_REVIEW_NAME
        )
    review = _load_json(review_path, "final Card Factory review", errors)
    if not review:
        if not errors or "cannot read final Card Factory review JSON" not in errors[-1]:
            errors.append("final Card Factory review must not be empty")
        return ""
    required = {
        "schema_version", "review_id", "review_role", "project_id",
        "objective_id", "factory_revision", "decision_card",
        "product_authority", "studio_gameplay_system", "authority_inventory",
        "player_facing_interaction_contract",
        "player_facing_interaction_contract_review",
        "reviewer_context_id", "reviewer_freshness",
        "requirement_findings", "claim_inventory", "blocking_findings",
        "verdict", "reviewed_at",
    }
    _require_exact_keys(review, "final Card Factory review", required, errors)
    if review.get("schema_version") != CARD_FACTORY_REVIEW_VERSION:
        errors.append(
            "final Card Factory review schema_version must be "
            + CARD_FACTORY_REVIEW_VERSION
        )
    if review.get("review_role") != "FINAL_CARD_FACTORY_COMPLIANCE":
        errors.append(
            "final Card Factory review review_role must be "
            "FINAL_CARD_FACTORY_COMPLIANCE"
        )
    _require_id(review.get("review_id"), "final Card Factory review.review_id", errors)
    if review.get("project_id") != card.get("project_id"):
        errors.append("final Card Factory review project_id does not match the card")
    if review.get("objective_id") != card.get("objective_id"):
        errors.append("final Card Factory review objective_id does not match the card")
    if review.get("factory_revision") != card.get("factory_revision"):
        errors.append("final Card Factory review factory_revision does not match the card")

    card_ref = _require_exact_keys(
        review.get("decision_card"),
        "final Card Factory review.decision_card",
        {"path", "decision_payload_sha256", "rendered_surface_sha256"},
        errors,
    )
    expected_card_path = card_path.resolve().relative_to(game_repo).as_posix()
    if card_ref.get("path") != expected_card_path:
        errors.append("final Card Factory review binds a different decision-card path")
    if card_ref.get("decision_payload_sha256") != card.get("decision_payload_sha256"):
        errors.append("final Card Factory review binds a different decision payload")
    expected_surface_sha = hashlib.sha256(
        render_decision_card(card).encode("utf-8")
    ).hexdigest()
    if card_ref.get("rendered_surface_sha256") != expected_surface_sha:
        errors.append("final Card Factory review binds a different rendered Card surface")

    product_path, product_sha, _ = _validate_path_hash(
        game_repo,
        review.get("product_authority"),
        "final Card Factory review.product_authority",
        errors,
    )
    expected_product = card_binding.get("product_authority", {})
    if (
        product_path != expected_product.get("path")
        or product_sha != expected_product.get("sha256")
    ):
        errors.append("final Card Factory review binds different Product authority")

    system_path, system_sha, _ = _validate_path_hash(
        game_repo,
        review.get("studio_gameplay_system"),
        "final Card Factory review.studio_gameplay_system",
        errors,
    )
    if (
        system_path != card_binding.get("system_path")
        or system_sha != card_binding.get("system_sha")
    ):
        errors.append(
            "final Card Factory review does not bind the card's exact validated gameplay system"
        )

    contract_ref = card_binding.get("interaction_contract", {}).get("ref", {})
    contract_review_ref = card_binding.get("interaction_contract_review", {}).get("ref", {})
    for field, expected in (
        ("player_facing_interaction_contract", contract_ref),
        ("player_facing_interaction_contract_review", contract_review_ref),
    ):
        actual_path, actual_sha, _ = _validate_path_hash(
            game_repo, review.get(field), f"final Card Factory review.{field}", errors
        )
        if {"path": actual_path, "sha256": actual_sha} != expected:
            errors.append(
                f"final Card Factory review.{field} does not bind the exact "
                "validated player-facing design artifact"
            )

    authority_inventory = _require_exact_keys(
        review.get("authority_inventory"),
        "final Card Factory review.authority_inventory",
        {
            "product_causal_links",
            "factory_constraints",
            "product_non_goals",
        },
        errors,
    )
    authority_fields = {
        "product_causal_links": "product_causal_link_coverage",
        "factory_constraints": "factory_constraint_coverage",
        "product_non_goals": "product_non_goal_coverage",
    }
    claim_ids = set(card_binding.get("claim_ids", set()))
    for field, binding_field in authority_fields.items():
        values = authority_inventory.get(field)
        if not isinstance(values, list):
            errors.append(f"authority_inventory.{field} must be an array")
            values = []
        authority_ids: list[str] = []
        for index, raw in enumerate(values):
            item = _require_exact_keys(
                raw,
                f"authority_inventory.{field}[{index}]",
                {
                    "authority_id", "system_transition_ids", "requirement_ids",
                    "evidence_claim_ids", "verdict", "rationale",
                },
                errors,
            )
            authority_id = _require_id(
                item.get("authority_id"),
                f"authority_inventory.{field}[{index}].authority_id",
                errors,
            )
            authority_ids.append(authority_id)
            transition_ids = item.get("system_transition_ids")
            if not isinstance(transition_ids, list):
                errors.append(
                    f"authority_inventory.{field}[{index}].system_transition_ids "
                    "must be an array"
                )
                transition_ids = []
            if len(transition_ids) != len(set(transition_ids)):
                errors.append(
                    f"authority_inventory.{field}[{index}].system_transition_ids "
                    "must be unique"
                )
            requirement_ids = item.get("requirement_ids")
            if not isinstance(requirement_ids, list) or not requirement_ids:
                errors.append(
                    f"authority_inventory.{field}[{index}].requirement_ids "
                    "must be a non-empty array"
                )
                requirement_ids = []
            if len(requirement_ids) != len(set(requirement_ids)):
                errors.append(
                    f"authority_inventory.{field}[{index}].requirement_ids must be unique"
                )
            unknown_requirements = {
                str(value) for value in requirement_ids
            } - set(FINAL_CARD_REQUIREMENT_IDS)
            if unknown_requirements:
                errors.append(
                    f"authority_inventory.{field}[{index}] cites unknown Factory "
                    "requirements: " + ", ".join(sorted(unknown_requirements))
                )
            evidence_ids = item.get("evidence_claim_ids")
            if not isinstance(evidence_ids, list) or not evidence_ids:
                errors.append(
                    f"authority_inventory.{field}[{index}].evidence_claim_ids "
                    "must be a non-empty array"
                )
                evidence_ids = []
            if len(evidence_ids) != len(set(evidence_ids)):
                errors.append(
                    f"authority_inventory.{field}[{index}].evidence_claim_ids must be unique"
                )
            unknown_claims = {str(value) for value in evidence_ids} - claim_ids
            if unknown_claims:
                errors.append(
                    f"authority_inventory.{field}[{index}] cites unknown Card claims: "
                    + ", ".join(sorted(unknown_claims))
                )
            expected_coverage = dict(card_binding.get(binding_field, {})).get(
                authority_id, set()
            )
            if set(transition_ids) != set(expected_coverage):
                errors.append(
                    f"authority_inventory.{field}[{index}].system_transition_ids "
                    "must exactly match the bound system coverage"
                )
            required_cycle_claims = {
                f"cycle.{transition_id}" for transition_id in expected_coverage
            }
            if required_cycle_claims and not required_cycle_claims.issubset(
                {str(value) for value in evidence_ids}
            ):
                errors.append(
                    f"authority_inventory.{field}[{index}].evidence_claim_ids must "
                    "cover every mapped system transition claim"
                )
            if item.get("verdict") != "PASS":
                errors.append(
                    f"authority_inventory.{field}[{index}].verdict must be PASS"
                )
            _require_text(
                item.get("rationale"),
                f"authority_inventory.{field}[{index}].rationale",
                errors,
            )
        if len(authority_ids) != len(set(authority_ids)):
            errors.append(f"authority_inventory.{field} repeats an authority id")
        expected_values = set(dict(card_binding.get(binding_field, {})))
        if set(authority_ids) != expected_values:
            errors.append(
                f"authority_inventory.{field} must exactly cover the bound system: "
                + ", ".join(sorted(expected_values))
            )

    reviewer = _require_id(
        review.get("reviewer_context_id"),
        "final Card Factory review.reviewer_context_id",
        errors,
    )
    if review.get("reviewer_freshness") != "FRESH":
        errors.append("final Card Factory review reviewer_freshness must be FRESH")
    prior_context_ids = {
        str(card_binding.get("author_context_id", "")),
        *{str(value) for value in card_binding.get("studio_context_ids", set())},
        str(card_binding.get("interaction_contract", {}).get("author_context_id", "")),
        str(card_binding.get("interaction_contract_review", {}).get("reviewer_context_id", "")),
        *{str(value) for value in forbidden_context_ids},
    } - {""}
    if reviewer and reviewer in prior_context_ids:
        errors.append(
            "final Card Factory reviewer must be fresh from Card/system authors, "
            "system reviewers, and the semantic-alignment reviewer"
        )

    findings = _require_exact_keys(
        review.get("requirement_findings"),
        "final Card Factory review.requirement_findings",
        set(FINAL_CARD_REQUIREMENT_IDS),
        errors,
    )
    for requirement_id in FINAL_CARD_REQUIREMENT_IDS:
        finding = _require_exact_keys(
            findings.get(requirement_id),
            f"requirement_findings.{requirement_id}",
            {"verdict", "evidence_claim_ids", "rationale"},
            errors,
        )
        if finding.get("verdict") != "PASS":
            errors.append(f"requirement_findings.{requirement_id}.verdict must be PASS")
        evidence_ids = finding.get("evidence_claim_ids")
        if not isinstance(evidence_ids, list) or not evidence_ids:
            errors.append(
                f"requirement_findings.{requirement_id}.evidence_claim_ids "
                "must be a non-empty array"
            )
            evidence_ids = []
        if len(evidence_ids) != len(set(evidence_ids)):
            errors.append(
                f"requirement_findings.{requirement_id}.evidence_claim_ids "
                "must be unique"
            )
        unknown = {str(item) for item in evidence_ids} - claim_ids
        if unknown:
            errors.append(
                f"requirement_findings.{requirement_id} cites unknown Card claims: "
                + ", ".join(sorted(unknown))
            )
        evidence_texts = {str(item) for item in evidence_ids}
        for required_prefix in FINAL_CARD_REQUIREMENT_CLAIM_PREFIXES[requirement_id]:
            if not any(item.startswith(required_prefix) for item in evidence_texts):
                errors.append(
                    f"requirement_findings.{requirement_id}.evidence_claim_ids "
                    f"must include a {required_prefix} Card claim"
                )
        _require_text(
            finding.get("rationale"),
            f"requirement_findings.{requirement_id}.rationale",
            errors,
        )

    inventory = review.get("claim_inventory")
    if not isinstance(inventory, list):
        errors.append("final Card Factory review.claim_inventory must be an array")
        inventory = []
    inventoried_ids: list[str] = []
    for index, raw in enumerate(inventory):
        item = _require_exact_keys(
            raw,
            f"claim_inventory[{index}]",
            {"claim_id", "requirement_ids", "verdict", "rationale"},
            errors,
        )
        claim_id = _require_id(
            item.get("claim_id"), f"claim_inventory[{index}].claim_id", errors
        )
        inventoried_ids.append(claim_id)
        requirement_ids = item.get("requirement_ids")
        if not isinstance(requirement_ids, list) or not requirement_ids:
            errors.append(
                f"claim_inventory[{index}].requirement_ids must be a non-empty array"
            )
            requirement_ids = []
        if len(requirement_ids) != len(set(requirement_ids)):
            errors.append(f"claim_inventory[{index}].requirement_ids must be unique")
        unknown_requirements = {
            str(value) for value in requirement_ids
        } - set(FINAL_CARD_REQUIREMENT_IDS)
        if unknown_requirements:
            errors.append(
                f"claim_inventory[{index}] cites unknown Factory requirements: "
                + ", ".join(sorted(unknown_requirements))
            )
        expected_claim_verdict = (
            "TESTABLE_DESIGN"
            if claim_id in set(card_binding.get("hypothesis_ids", set()))
            else "PASS_DESIGN_CLAIM"
        )
        if item.get("verdict") != expected_claim_verdict:
            errors.append(
                f"claim_inventory[{index}].verdict must be {expected_claim_verdict}; "
                "a design hypothesis cannot be labelled PASS or ACCEPTED"
            )
        _require_text(
            item.get("rationale"), f"claim_inventory[{index}].rationale", errors
        )
    if len(inventoried_ids) != len(set(inventoried_ids)):
        errors.append("final Card Factory review.claim_inventory repeats a Card claim")
    if set(inventoried_ids) != claim_ids:
        missing = sorted(claim_ids - set(inventoried_ids))
        extra = sorted(set(inventoried_ids) - claim_ids)
        if missing:
            errors.append("final Card Factory review misses Card claims: " + ", ".join(missing))
        if extra:
            errors.append("final Card Factory review invents Card claims: " + ", ".join(extra))

    if review.get("blocking_findings") != []:
        errors.append("final Card Factory review.blocking_findings must be empty")
    if review.get("verdict") != PASS_CARD_FACTORY_REVIEW:
        errors.append(
            "final Card Factory review.verdict must be " + PASS_CARD_FACTORY_REVIEW
        )
    _require_text(review.get("reviewed_at"), "final Card Factory review.reviewed_at", errors)
    return reviewer


def validate_card_factory_review(
    game_repo: str | Path,
    card_path: str | Path,
    review_path: str | Path,
    *,
    forbidden_context_ids: set[str] | None = None,
) -> CardFactoryReviewResult:
    """Validate the independent final Card audit before human presentation."""

    repo = Path(game_repo).expanduser().resolve()
    card_file = Path(card_path)
    if not card_file.is_absolute():
        card_file = repo / card_file
    review_file = Path(review_path)
    if not review_file.is_absolute():
        review_file = repo / review_file
    card_file = card_file.resolve()
    review_file = review_file.resolve()
    errors: list[str] = []
    try:
        card_file.relative_to(repo)
        review_file.relative_to(repo)
    except ValueError:
        errors.append("final Card Factory review paths must stay inside the game repo")
        return CardFactoryReviewResult("BLOCKED", errors)
    card = _load_json(card_file, "gameplay decision card", errors)
    if card.get("routing") != "STUDIO_WHOLE_GAME":
        errors.append("final Card Factory review is required only for STUDIO_WHOLE_GAME cards")
    card_binding = _validate_decision_card(
        game_repo=repo,
        card_path=card_file,
        project_id=str(card.get("project_id", "")),
        objective_id=str(card.get("objective_id", "")),
        factory_revision=current_factory_revision(Path(__file__).resolve().parents[1]),
        context_status=READY_FOR_NEW_GAMEPLAY_DESIGN,
        errors=errors,
        pre_human_review=True,
    )
    reviewer = _validate_card_factory_review_artifact(
        game_repo=repo,
        card_path=card_file,
        card=card,
        card_binding=card_binding,
        review_path=review_file,
        forbidden_context_ids=forbidden_context_ids or set(),
        errors=errors,
    )
    relative_review = ""
    try:
        relative_review = review_file.relative_to(repo).as_posix()
    except ValueError:
        pass
    return CardFactoryReviewResult(
        PASS_CARD_FACTORY_REVIEW if not errors else "BLOCKED",
        errors,
        reviewer_context_id=reviewer,
        review_path=relative_review,
    )


def validate_studio_card_presentation(
    game_repo: str | Path,
    card_path: str | Path,
    card: dict[str, Any] | None = None,
) -> list[str]:
    """Validate both final reviewers for an exact registered pending Card."""

    repo = Path(game_repo).expanduser().resolve()
    path = Path(card_path)
    if not path.is_absolute():
        path = repo / path
    path = path.resolve()
    errors: list[str] = []
    payload = card or _load_json(path, "gameplay decision card", errors)
    if payload.get("routing") != "STUDIO_WHOLE_GAME":
        return errors
    rendered = render_decision_card(payload)
    alignment_reviewer = ""
    entry = require_registered_card(
        repo,
        path,
        required_state="PENDING",
        errors=errors,
    )
    if entry:
        try:
            result = validate_alignment_review(
                repo,
                entry.get("alignment_input", {}).get("path", ""),
                entry.get("alignment_review", {}).get("path", ""),
                expected_output_text=rendered,
                expected_output_kind="DECISION_SURFACE",
            )
        except AlignmentValidationError as error:
            errors.append(str(error))
        else:
            errors.extend(result.errors)
            review_path = repo / entry.get("alignment_review", {}).get("path", "")
            alignment_review = _load_json(
                review_path, "registered semantic alignment review", errors
            )
            if isinstance(alignment_review.get("reviewer_context_id"), str):
                alignment_reviewer = alignment_review["reviewer_context_id"]
            if result.status != HUMAN_RULING_GENUINELY_REQUIRED:
                errors.append(
                    "Studio decision surface requires "
                    "HUMAN_RULING_GENUINELY_REQUIRED alignment verdict"
                )
    compliance = validate_card_factory_review(
        repo,
        path,
        path.with_name(CARD_FACTORY_REVIEW_NAME),
        forbidden_context_ids={alignment_reviewer} - {""},
    )
    errors.extend(compliance.errors)
    return errors


def _section(objective_text: str, heading: str) -> str:
    match = re.search(
        rf"^## {re.escape(heading)}\s*$\n(.*?)(?=^## |\Z)",
        objective_text,
        re.MULTILINE | re.DOTALL,
    )
    return match.group(1) if match else ""


def _extract_material_spec(
    objective_text: str, errors: list[str]
) -> tuple[dict[str, str], str]:
    """Return the finite set of material design statements in the full spec."""

    material: dict[str, str] = {}
    headings = re.findall(r"^## (.+?)\s*$", objective_text, re.MULTILINE)
    if len(headings) != len(set(headings)):
        errors.append("OBJECTIVE_GAMEPLAY.md contains duplicate material headings")
    unsupported = sorted(set(headings) - ALLOWED_MATERIAL_HEADINGS)
    if unsupported:
        errors.append(
            "OBJECTIVE_GAMEPLAY.md contains unsupported material headings: "
            + ", ".join(unsupported)
        )
    for heading in sorted(ALLOWED_MATERIAL_HEADINGS - set(headings)):
        errors.append(f"OBJECTIVE_GAMEPLAY.md lacks '## {heading}'")

    preamble = objective_text.split("## Expected player experience", 1)[0]
    required_preamble_patterns = {
        "title": re.compile(r"^# Objective Gameplay — `[^`]+`$"),
        "Step 1 context": re.compile(r"^- Step 1 context: `[^`]+`$"),
        "Context status": re.compile(r"^- Context status: `[^`]+`$"),
        "Author context id": re.compile(r"^- Author context id: `[^`]+`$"),
        "Objective": re.compile(r"^- Objective: .+$"),
        "Frontier decision": re.compile(r"^- Frontier decision: `[^`]+`$"),
        "Design status": re.compile(r"^- Design status: `[^`]+`$"),
    }
    seen_preamble: set[str] = set()
    for line in (item.strip() for item in preamble.splitlines() if item.strip()):
        matches = [
            label for label, pattern in required_preamble_patterns.items()
            if pattern.fullmatch(line)
        ]
        if len(matches) != 1:
            errors.append(
                "OBJECTIVE_GAMEPLAY.md contains non-canonical preamble content: " + line
            )
        else:
            if matches[0] in seen_preamble:
                errors.append(
                    "OBJECTIVE_GAMEPLAY.md duplicates canonical " + matches[0] + " metadata"
                )
            seen_preamble.add(matches[0])
    for missing in sorted(set(required_preamble_patterns) - seen_preamble):
        errors.append(f"OBJECTIVE_GAMEPLAY.md lacks canonical {missing} metadata")

    author_match = _AUTHOR_CONTEXT_PATTERN.search(objective_text)
    author_context_id = (
        _require_id(
            author_match.group(1).strip(),
            "OBJECTIVE_GAMEPLAY.md Author context id",
            errors,
        )
        if author_match
        else ""
    )
    if not author_match:
        errors.append("OBJECTIVE_GAMEPLAY.md lacks '- Author context id:'")

    objective_match = _OBJECTIVE_PATTERN.search(objective_text)
    if objective_match:
        material["objective.promise"] = _require_text(
            objective_match.group(1), "OBJECTIVE_GAMEPLAY.md Objective", errors
        )
    else:
        errors.append("OBJECTIVE_GAMEPLAY.md lacks '- Objective:'")

    for ref_name, field_name in EXPECTED_EXPERIENCE_FIELDS:
        pattern = re.compile(rf"^- {re.escape(field_name)}:\s*(.+)$", re.MULTILINE)
        matches = list(pattern.finditer(objective_text))
        if not matches:
            errors.append(
                f"OBJECTIVE_GAMEPLAY.md lacks a filled '- {field_name}:' field"
            )
        else:
            if len(matches) > 1:
                errors.append(f"OBJECTIVE_GAMEPLAY.md duplicates '- {field_name}:'")
            match = matches[0]
            material[f"expected.{ref_name}"] = _require_text(
                match.group(1),
                f"OBJECTIVE_GAMEPLAY.md expected experience {field_name}",
                errors,
            )

    expected_body = _section(objective_text, "Expected player experience")
    expected_bullet_prefixes = {
        f"- {field_name}:" for _, field_name in EXPECTED_EXPERIENCE_FIELDS
    }
    for line in (item.strip() for item in expected_body.splitlines() if item.strip()):
        if line == CANONICAL_TABLE_HEADER or line == CANONICAL_TABLE_SEPARATOR:
            continue
        if re.match(r"^\|\s*\d+\s*\|", line):
            continue
        if any(line.startswith(prefix) for prefix in expected_bullet_prefixes):
            continue
        errors.append(
            "OBJECTIVE_GAMEPLAY.md contains non-canonical expected/table content: "
            + line
        )
    if CANONICAL_TABLE_HEADER not in expected_body:
        errors.append("OBJECTIVE_GAMEPLAY.md lacks the canonical gameplay table header")
    if CANONICAL_TABLE_SEPARATOR not in expected_body:
        errors.append("OBJECTIVE_GAMEPLAY.md lacks the canonical gameplay table separator")

    row_refs: set[str] = set()
    for line in objective_text.splitlines():
        match = re.match(r"^\|\s*(\d+)\s*\|", line)
        if not match:
            continue
        ref = f"row.{int(match.group(1))}"
        if ref in row_refs:
            errors.append(f"OBJECTIVE_GAMEPLAY.md duplicates {ref}")
        row_refs.add(ref)
        material[ref] = _require_text(line, f"OBJECTIVE_GAMEPLAY.md {ref}", errors)
    if not row_refs:
        errors.append("OBJECTIVE_GAMEPLAY.md has no numbered gameplay rows")

    additions = [
        line[2:].strip()
        for line in _section(objective_text, "New gameplay additions").splitlines()
        if line.startswith("- ")
    ]
    for line in (
        item.strip()
        for item in _section(objective_text, "New gameplay additions").splitlines()
        if item.strip()
    ):
        if not line.startswith("- "):
            errors.append(
                "OBJECTIVE_GAMEPLAY.md additions must be canonical bullet items: " + line
            )
    if not additions:
        errors.append("OBJECTIVE_GAMEPLAY.md must state its New gameplay additions")
    for index, addition in enumerate(additions, start=1):
        material[f"addition.{index}"] = _require_text(
            addition, f"OBJECTIVE_GAMEPLAY.md addition.{index}", errors
        )

    completion_fields = (
        ("completion.objective", "Objective completion condition"),
        ("completion.response", "Player-visible completion response"),
        ("completion.successor", "Successor objective/handoff"),
    )
    for spec_ref, field_name in completion_fields:
        pattern = re.compile(rf"^- {re.escape(field_name)}:\s*(.+)$", re.MULTILINE)
        matches = list(pattern.finditer(objective_text))
        if not matches:
            errors.append(f"OBJECTIVE_GAMEPLAY.md lacks '- {field_name}:'")
        else:
            if len(matches) > 1:
                errors.append(f"OBJECTIVE_GAMEPLAY.md duplicates '- {field_name}:'")
            match = matches[0]
            material[spec_ref] = _require_text(
                match.group(1), f"OBJECTIVE_GAMEPLAY.md {field_name}", errors
            )
    completion_prefixes = {f"- {field_name}:" for _, field_name in completion_fields}
    for line in (
        item.strip()
        for item in _section(objective_text, "Completion handoff").splitlines()
        if item.strip()
    ):
        if not any(line.startswith(prefix) for prefix in completion_prefixes):
            errors.append(
                "OBJECTIVE_GAMEPLAY.md contains non-canonical completion content: " + line
            )
    return material, author_context_id


def _require_empty_list(value: Any, label: str, errors: list[str]) -> None:
    if value != []:
        errors.append(f"{label} must be empty for PASS_CONFORMANCE")


def _validate_conformance_review(
    *,
    game_repo: Path,
    review_path: Path,
    expected_role: str,
    project_id: str,
    objective_id: str,
    factory_revision: str,
    card_path_text: str,
    card_sha: str,
    objective_path_text: str,
    objective_sha: str,
    claim_ids: set[str],
    hypothesis_ids: set[str],
    spec_refs: set[str],
    allow_legacy_historical: bool,
    errors: list[str],
) -> dict[str, Any]:
    review = _load_json(review_path, f"{expected_role} conformance review", errors)
    required = {
        "schema_version", "review_id", "review_role", "project_id",
        "objective_id", "factory_revision", "decision_card",
        "objective_gameplay", "reviewer_context_id", "reviewer_freshness",
        "claim_coverage", "spec_material_inventory", "contradictions",
        "ambiguities", "unsupported_material_decisions", "blocking_findings",
        "verdict", "reviewed_at",
    }
    _require_exact_keys(review, f"{expected_role} conformance review", required, errors)
    review_version = review.get("schema_version")
    legacy_review = (
        review_version == LEGACY_CONFORMANCE_REVIEW_VERSION
        and allow_legacy_historical
    )
    if review_version != CONFORMANCE_REVIEW_VERSION and not legacy_review:
        errors.append(
            f"{expected_role} review schema_version must be {CONFORMANCE_REVIEW_VERSION}; "
            f"{LEGACY_CONFORMANCE_REVIEW_VERSION} is readable only in historical checks"
        )
    _require_id(review.get("review_id"), f"{expected_role} review.review_id", errors)
    if review.get("review_role") != expected_role:
        errors.append(f"conformance review role must be {expected_role}")
    if review.get("project_id") != project_id:
        errors.append(f"{expected_role} review project_id does not match")
    if review.get("objective_id") != objective_id:
        errors.append(f"{expected_role} review objective_id does not match")
    if review.get("factory_revision") != factory_revision:
        errors.append(f"{expected_role} review factory_revision does not match")
    review_card_path, review_card_sha, _ = _validate_path_hash(
        game_repo, review.get("decision_card"), f"{expected_role} review.decision_card", errors
    )
    _validate_ref_equals(
        review_card_path, review_card_sha, card_path_text, card_sha,
        f"{expected_role} review decision card", errors,
    )
    review_spec_path, review_spec_sha, _ = _validate_path_hash(
        game_repo,
        review.get("objective_gameplay"),
        f"{expected_role} review.objective_gameplay",
        errors,
    )
    _validate_ref_equals(
        review_spec_path, review_spec_sha, objective_path_text, objective_sha,
        f"{expected_role} review objective gameplay", errors,
    )
    reviewer = _require_id(
        review.get("reviewer_context_id"),
        f"{expected_role} review.reviewer_context_id",
        errors,
    )
    if review.get("reviewer_freshness") != "FRESH":
        errors.append(f"{expected_role} review reviewer_freshness must be FRESH")

    pairs: set[tuple[str, str]] = set()
    coverage = review.get("claim_coverage")
    inventory = review.get("spec_material_inventory")
    if expected_role == "CARD_TO_SPEC":
        if not isinstance(coverage, list):
            errors.append("CARD_TO_SPEC claim_coverage must be an array")
            coverage = []
        seen_claims: set[str] = set()
        for index, raw_item in enumerate(coverage):
            item = _require_exact_keys(
                raw_item,
                f"CARD_TO_SPEC claim_coverage[{index}]",
                {"claim_id", "spec_refs", "verdict"},
                errors,
            )
            claim_id = _require_id(
                item.get("claim_id"),
                f"CARD_TO_SPEC claim_coverage[{index}].claim_id",
                errors,
            )
            if claim_id in seen_claims:
                errors.append(f"CARD_TO_SPEC duplicates claim {claim_id}")
            seen_claims.add(claim_id)
            raw_refs = item.get("spec_refs")
            if not isinstance(raw_refs, list) or not raw_refs:
                errors.append(f"CARD_TO_SPEC claim {claim_id} must have spec_refs")
                raw_refs = []
            refs = [
                _require_id(value, f"CARD_TO_SPEC claim {claim_id}.spec_refs", errors)
                for value in raw_refs
            ]
            if len(refs) != len(set(refs)):
                errors.append(f"CARD_TO_SPEC claim {claim_id} repeats a spec_ref")
            for spec_ref in refs:
                if spec_ref not in spec_refs:
                    errors.append(f"CARD_TO_SPEC references unknown spec_ref {spec_ref}")
                pairs.add((claim_id, spec_ref))
            expected_verdict = (
                "PASS"
                if legacy_review
                else (
                    "TESTABLE_DESIGN"
                    if claim_id in hypothesis_ids
                    else "PASS_DESIGN_CLAIM"
                )
            )
            if item.get("verdict") != expected_verdict:
                errors.append(
                    f"CARD_TO_SPEC claim {claim_id} verdict must be {expected_verdict}; "
                    "a design-stage hypothesis cannot be labelled PASS or ACCEPTED"
                )
        if seen_claims != claim_ids:
            missing = sorted(claim_ids - seen_claims)
            extra = sorted(seen_claims - claim_ids)
            if missing:
                errors.append("CARD_TO_SPEC misses card claims: " + ", ".join(missing))
            if extra:
                errors.append("CARD_TO_SPEC invents card claims: " + ", ".join(extra))
        if inventory != []:
            errors.append("CARD_TO_SPEC spec_material_inventory must be empty")
    else:
        if coverage != []:
            errors.append("SPEC_TO_CARD claim_coverage must be empty")
        if not isinstance(inventory, list):
            errors.append("SPEC_TO_CARD spec_material_inventory must be an array")
            inventory = []
        seen_specs: set[str] = set()
        for index, raw_item in enumerate(inventory):
            item = _require_exact_keys(
                raw_item,
                f"SPEC_TO_CARD spec_material_inventory[{index}]",
                {"spec_ref", "claim_ids", "classification", "rationale"},
                errors,
            )
            spec_ref = _require_id(
                item.get("spec_ref"),
                f"SPEC_TO_CARD spec_material_inventory[{index}].spec_ref",
                errors,
            )
            if spec_ref in seen_specs:
                errors.append(f"SPEC_TO_CARD duplicates spec_ref {spec_ref}")
            seen_specs.add(spec_ref)
            raw_claims = item.get("claim_ids")
            if not isinstance(raw_claims, list) or not raw_claims:
                errors.append(f"SPEC_TO_CARD {spec_ref} must have claim_ids")
                raw_claims = []
            mapped_claims = [
                _require_id(value, f"SPEC_TO_CARD {spec_ref}.claim_ids", errors)
                for value in raw_claims
            ]
            if len(mapped_claims) != len(set(mapped_claims)):
                errors.append(f"SPEC_TO_CARD {spec_ref} repeats a claim_id")
            for claim_id in mapped_claims:
                if claim_id not in claim_ids:
                    errors.append(f"SPEC_TO_CARD references unknown claim {claim_id}")
                pairs.add((claim_id, spec_ref))
            classification = item.get("classification")
            if classification not in {
                "AUTHORIZED_BY_CARD", "VALIDATION_HYPOTHESIS"
            }:
                errors.append(f"SPEC_TO_CARD {spec_ref} classification is unsupported")
            elif classification == "VALIDATION_HYPOTHESIS":
                if not set(mapped_claims).issubset(hypothesis_ids):
                    errors.append(
                        f"SPEC_TO_CARD {spec_ref} hypothesis classification uses a binding claim"
                    )
                if not spec_ref.startswith("expected."):
                    errors.append(
                        f"SPEC_TO_CARD {spec_ref} cannot turn a validation hypothesis into production authority"
                    )
            elif mapped_claims and set(mapped_claims).issubset(hypothesis_ids):
                errors.append(
                    f"SPEC_TO_CARD {spec_ref} is authorized only by validation hypotheses"
                )
            _require_text(
                item.get("rationale"), f"SPEC_TO_CARD {spec_ref}.rationale", errors
            )
        if seen_specs != spec_refs:
            missing = sorted(spec_refs - seen_specs)
            extra = sorted(seen_specs - spec_refs)
            if missing:
                errors.append("SPEC_TO_CARD misses material spec refs: " + ", ".join(missing))
            if extra:
                errors.append("SPEC_TO_CARD invents material spec refs: " + ", ".join(extra))

    for key in (
        "contradictions", "ambiguities", "unsupported_material_decisions",
        "blocking_findings",
    ):
        _require_empty_list(review.get(key), f"{expected_role} review.{key}", errors)
    if review.get("verdict") != "PASS_CONFORMANCE":
        errors.append(f"{expected_role} review verdict must be PASS_CONFORMANCE")
    _require_text(review.get("reviewed_at"), f"{expected_role} review.reviewed_at", errors)
    return {"reviewer": reviewer, "pairs": pairs}


def _validate_legacy_verdict(
    *,
    game_repo: Path,
    verdict: dict[str, Any],
    project_id: str,
    objective_id: str,
    factory_revision: str,
    objective_path_text: str,
    objective_sha256: str,
    context_status: str,
    design_status: str,
    errors: list[str],
) -> str:
    required = {
        "schema_version", "verdict_id", "project_id", "objective_id",
        "factory_revision", "objective_gameplay", "context_status",
        "reviewer_context_id", "reviewer_freshness", "factory_verdict",
        "human_verdict", "human_verdict_source", "blocking_findings", "reviewed_at",
    }
    _require_exact_keys(verdict, "legacy design verdict", required, errors)
    _require_text(verdict.get("verdict_id"), "legacy design verdict.verdict_id", errors)
    if verdict.get("project_id") != project_id:
        errors.append("legacy design verdict project_id does not match")
    if verdict.get("objective_id") != objective_id:
        errors.append("legacy design verdict objective_id does not match")
    if verdict.get("factory_revision") != factory_revision:
        errors.append("legacy design verdict factory_revision does not match")
    authority_path, authority_sha, _ = _validate_path_hash(
        game_repo,
        verdict.get("objective_gameplay"),
        "legacy design verdict.objective_gameplay",
        errors,
    )
    _validate_ref_equals(
        authority_path, authority_sha, objective_path_text, objective_sha256,
        "legacy design verdict objective gameplay", errors,
    )
    if verdict.get("context_status") != context_status:
        errors.append("legacy design verdict context_status does not match")
    _require_text(
        verdict.get("reviewer_context_id"), "legacy verdict.reviewer_context_id", errors
    )
    if verdict.get("reviewer_freshness") != "FRESH":
        errors.append("legacy verdict reviewer_freshness must be FRESH")
    if verdict.get("factory_verdict") != "PASS_DESIGN_REVIEW":
        errors.append("legacy verdict factory_verdict must be PASS_DESIGN_REVIEW")
    human_verdict = verdict.get("human_verdict", "")
    if human_verdict not in HUMAN_VERDICTS:
        errors.append("legacy verdict human_verdict is unsupported")
    if context_status == READY_FOR_NEW_GAMEPLAY_DESIGN and human_verdict != "USER_APPROVED":
        errors.append("legacy new gameplay design requires USER_APPROVED")
    source = _require_exact_keys(
        verdict.get("human_verdict_source"),
        "legacy verdict.human_verdict_source",
        {"kind", "text", "recorded_at"},
        errors,
    )
    expected_kind = (
        "POST_DRAFT_APPROVAL" if human_verdict == "USER_APPROVED" else "EXPLICIT_DELEGATION"
    )
    if source.get("kind") != expected_kind:
        errors.append(f"legacy verdict human_verdict_source.kind must be {expected_kind}")
    _require_text(source.get("text"), "legacy verdict human source.text", errors)
    _require_text(source.get("recorded_at"), "legacy verdict human source.recorded_at", errors)
    _require_empty_list(verdict.get("blocking_findings"), "legacy verdict.blocking_findings", errors)
    _require_text(verdict.get("reviewed_at"), "legacy verdict.reviewed_at", errors)
    if human_verdict and design_status != human_verdict:
        errors.append("OBJECTIVE_GAMEPLAY.md Design status must equal the legacy verdict")
    return human_verdict


def validate_objective_design_gate(
    *,
    factory_root: Path,
    game_repo: Path,
    project_id: str,
    objective_id: str,
    objective_path_text: str,
    objective_path: Path,
    objective_sha256: str,
    objective_text: str,
    manifest_factory_revision: Any,
    raw_verdict_ref: Any,
    errors: list[str],
    allow_legacy_historical: bool = False,
) -> DesignGateBinding:
    """Validate the exact card, full spec, two-way conformance, and verdict."""

    factory_revision = _require_text(
        manifest_factory_revision, "factory_revision", errors
    )
    if factory_revision and FACTORY_REVISION_PATTERN.fullmatch(factory_revision) is None:
        errors.append("factory_revision must be a 7-64 lowercase Git revision")
    try:
        actual_factory_revision = current_factory_revision(factory_root)
    except ValueError as error:
        errors.append(f"cannot resolve Factory revision: {error}")
        actual_factory_revision = ""
    if (
        not allow_legacy_historical
        and factory_revision
        and actual_factory_revision
        and factory_revision != actual_factory_revision
    ):
        errors.append(
            "factory_revision does not match the Factory HEAD; refresh the decision card, "
            "conformance reviews, and plans"
        )

    verdict_path_text, verdict_sha256, verdict_path = _validate_path_hash(
        game_repo, raw_verdict_ref, "design_verdict", errors
    )
    expected_verdict_path = objective_path.parent / DESIGN_VERDICT_NAME
    if verdict_path is not None and verdict_path != expected_verdict_path.resolve():
        errors.append(f"design_verdict must be the objective-local {DESIGN_VERDICT_NAME}")

    context_match = _CONTEXT_STATUS_PATTERN.search(objective_text)
    context_status = context_match.group(1).strip() if context_match else ""
    if context_status not in CONTEXT_STATUSES:
        errors.append("OBJECTIVE_GAMEPLAY.md has no supported Context status")
    design_match = _DESIGN_STATUS_PATTERN.search(objective_text)
    design_status = design_match.group(1).strip() if design_match else ""
    if not design_status:
        errors.append("OBJECTIVE_GAMEPLAY.md has no Design status")

    if verdict_path is None:
        return DesignGateBinding(
            factory_revision, verdict_path_text, verdict_sha256, context_status, ""
        )
    verdict = _load_json(verdict_path, "design verdict", errors)
    version = verdict.get("schema_version")
    if version == LEGACY_DESIGN_VERDICT_VERSION:
        if not allow_legacy_historical:
            errors.append(
                "legacy gameplay design verdicts are historical-only; create a compact "
                "decision card and dual conformance reviews before production"
            )
            return DesignGateBinding(
                factory_revision, verdict_path_text, verdict_sha256, context_status, ""
            )
        human = _validate_legacy_verdict(
            game_repo=game_repo,
            verdict=verdict,
            project_id=project_id,
            objective_id=objective_id,
            factory_revision=factory_revision,
            objective_path_text=objective_path_text,
            objective_sha256=objective_sha256,
            context_status=context_status,
            design_status=design_status,
            errors=errors,
        )
        return DesignGateBinding(
            factory_revision, verdict_path_text, verdict_sha256, context_status, human
        )

    required = {
        "schema_version", "verdict_id", "project_id", "objective_id",
        "factory_revision", "objective_gameplay", "context_status",
        "decision_card", "conformance_reviews", "factory_verdict",
        "blocking_findings", "reviewed_at",
    }
    _require_exact_keys(verdict, "design verdict", required, errors)
    if version != DESIGN_VERDICT_VERSION:
        errors.append(f"design verdict schema_version must be {DESIGN_VERDICT_VERSION}")
    _require_id(verdict.get("verdict_id"), "design verdict.verdict_id", errors)
    if verdict.get("project_id") != project_id:
        errors.append("design verdict project_id does not match the manifest")
    if verdict.get("objective_id") != objective_id:
        errors.append("design verdict objective_id does not match the manifest")
    if verdict.get("factory_revision") != factory_revision:
        errors.append("design verdict factory_revision does not match the manifest")
    authority_path, authority_sha, _ = _validate_path_hash(
        game_repo,
        verdict.get("objective_gameplay"),
        "design verdict.objective_gameplay",
        errors,
    )
    _validate_ref_equals(
        authority_path, authority_sha, objective_path_text, objective_sha256,
        "design verdict objective gameplay", errors,
    )
    if verdict.get("context_status") != context_status:
        errors.append("design verdict context_status does not match OBJECTIVE_GAMEPLAY.md")
    if verdict.get("factory_verdict") != "PASS_DESIGN_CONFORMANCE":
        errors.append("design verdict factory_verdict must be PASS_DESIGN_CONFORMANCE")
    _require_empty_list(verdict.get("blocking_findings"), "design verdict.blocking_findings", errors)
    _require_text(verdict.get("reviewed_at"), "design verdict.reviewed_at", errors)

    card_path_text, card_sha, card_path = _validate_path_hash(
        game_repo, verdict.get("decision_card"), "design verdict.decision_card", errors
    )
    if card_path is not None and card_path != (objective_path.parent / DECISION_CARD_NAME).resolve():
        errors.append(f"decision_card must be the objective-local {DECISION_CARD_NAME}")
    card_binding: dict[str, Any] = {
        "claim_ids": set(), "hypothesis_ids": set(),
        "author_context_id": "", "human_status": "",
        "system_path": "", "system_sha": "", "cycle_id": "",
        "studio_context_ids": set(),
    }
    if card_path is not None:
        card_binding = _validate_decision_card(
            game_repo=game_repo,
            card_path=card_path,
            project_id=project_id,
            objective_id=objective_id,
            factory_revision=factory_revision,
            context_status=context_status,
            errors=errors,
            allow_legacy_historical=allow_legacy_historical,
        )

    material_spec, objective_author = _extract_material_spec(objective_text, errors)
    if (
        objective_author
        and card_binding.get("author_context_id")
        and objective_author == card_binding["author_context_id"]
    ):
        errors.append("decision-card author and full-spec author must be different contexts")

    reviews = _require_exact_keys(
        verdict.get("conformance_reviews"),
        "design verdict.conformance_reviews",
        {"card_to_spec", "spec_to_card"},
        errors,
    )
    review_results: list[dict[str, Any]] = []
    for key, role, filename in (
        ("card_to_spec", "CARD_TO_SPEC", CARD_TO_SPEC_REVIEW_NAME),
        ("spec_to_card", "SPEC_TO_CARD", SPEC_TO_CARD_REVIEW_NAME),
    ):
        _, _, review_path = _validate_path_hash(
            game_repo, reviews.get(key), f"design verdict.conformance_reviews.{key}", errors
        )
        if review_path is not None:
            if review_path != (objective_path.parent / filename).resolve():
                errors.append(f"{role} review must be the objective-local {filename}")
            review_results.append(
                _validate_conformance_review(
                    game_repo=game_repo,
                    review_path=review_path,
                    expected_role=role,
                    project_id=project_id,
                    objective_id=objective_id,
                    factory_revision=factory_revision,
                    card_path_text=card_path_text,
                    card_sha=card_sha,
                    objective_path_text=objective_path_text,
                    objective_sha=objective_sha256,
                    claim_ids=set(card_binding.get("claim_ids", set())),
                    hypothesis_ids=set(card_binding.get("hypothesis_ids", set())),
                    spec_refs=set(material_spec),
                    allow_legacy_historical=allow_legacy_historical,
                    errors=errors,
                )
            )
    if len(review_results) == 2:
        reviewers = [item["reviewer"] for item in review_results]
        if reviewers[0] == reviewers[1]:
            errors.append("CARD_TO_SPEC and SPEC_TO_CARD reviewers must be different")
        forbidden_reviewers = {
            objective_author, str(card_binding.get("author_context_id", ""))
        } | set(card_binding.get("studio_context_ids", set()))
        forbidden_reviewers -= {""}
        for reviewer in reviewers:
            if reviewer in forbidden_reviewers:
                errors.append(
                    "conformance reviewers must be fresh from system/card/spec authoring and review"
                )
        if review_results[0]["pairs"] != review_results[1]["pairs"]:
            errors.append(
                "CARD_TO_SPEC and SPEC_TO_CARD mappings are not exact inverses"
            )

    human_verdict = str(card_binding.get("human_status", ""))
    if human_verdict and design_status != human_verdict:
        errors.append(
            "OBJECTIVE_GAMEPLAY.md Design status must equal the decision-card human verdict"
        )
    return DesignGateBinding(
        factory_revision=factory_revision,
        verdict_path=verdict_path_text,
        verdict_sha256=verdict_sha256,
        context_status=context_status,
        human_verdict=human_verdict,
        decision_card_path=card_path_text,
        decision_card_sha256=card_sha,
        studio_gameplay_system_path=str(card_binding.get("system_path", "")),
        studio_gameplay_system_sha256=str(card_binding.get("system_sha", "")),
        cycle_id=str(card_binding.get("cycle_id", "")),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    card_hash = subparsers.add_parser(
        "card-hash", help="compute the compact material decision payload SHA"
    )
    card_hash.add_argument("--card", required=True)
    draft_card = subparsers.add_parser(
        "draft-card-surface",
        help="render an unpresented candidate surface for semantic alignment review",
    )
    draft_card.add_argument("--card", required=True)
    render_card = subparsers.add_parser(
        "render-card", help="render the bounded human decision surface"
    )
    render_card.add_argument("--card", required=True)
    render_card.add_argument("--game-repo")
    validate_card_review = subparsers.add_parser(
        "validate-card-review",
        help="validate the independent final Factory-compliance review for a Studio Card",
    )
    validate_card_review.add_argument("--game-repo", required=True)
    validate_card_review.add_argument("--card", required=True)
    validate_card_review.add_argument("--review", required=True)
    register_card = subparsers.add_parser(
        "register-card",
        help="register one compliance- and alignment-reviewed pending Studio decision card",
    )
    register_card.add_argument("--game-repo", required=True)
    register_card.add_argument("--card", required=True)
    register_card.add_argument("--alignment-input", required=True)
    register_card.add_argument("--alignment-review", required=True)
    register_card.add_argument("--factory-compliance-review", required=True)
    register_card.add_argument("--supersede-payload", action="append", default=[])
    register_card.add_argument("--recorded-at", required=True)
    record_verdict = subparsers.add_parser(
        "record-card-verdict",
        help="record an exact user verdict on a registered pending Studio card",
    )
    record_verdict.add_argument("--game-repo", required=True)
    record_verdict.add_argument("--card", required=True)
    record_verdict.add_argument("--verdict-token", required=True)
    record_verdict.add_argument("--recorded-at", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command in {"card-hash", "draft-card-surface", "render-card"}:
        path = Path(args.card).expanduser().resolve()
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            print(f"ERROR: cannot read decision card: {error}", file=sys.stderr)
            return 2
        if not isinstance(payload, dict):
            print("ERROR: decision card must be a JSON object", file=sys.stderr)
            return 2
        if args.command == "card-hash":
            print(decision_payload_sha256(payload))
        elif args.command == "draft-card-surface":
            print(render_decision_card(payload), end="")
        else:
            rendered = render_decision_card(payload)
            if payload.get("routing") == "STUDIO_WHOLE_GAME":
                if not args.game_repo:
                    print(
                        "ERROR: Studio render-card requires --game-repo so alignment "
                        "and supersession can be checked",
                        file=sys.stderr,
                    )
                    return 2
                errors = validate_studio_card_presentation(
                    args.game_repo, path, payload
                )
                if errors:
                    for error in errors:
                        print(f"ERROR: {error}", file=sys.stderr)
                    return 2
            print(rendered, end="")
        return 0
    if args.command == "validate-card-review":
        result = validate_card_factory_review(args.game_repo, args.card, args.review)
        print(result.status)
        for error in result.errors:
            print(f"ERROR: {error}")
        return 0 if result.status == PASS_CARD_FACTORY_REVIEW else 1
    if args.command == "register-card":
        repo = Path(args.game_repo).expanduser().resolve()
        card_path = Path(args.card)
        if not card_path.is_absolute():
            card_path = repo / card_path
        try:
            payload = json.loads(card_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise AlignmentValidationError("decision card must be a JSON object")
            expected_digest = decision_payload_sha256(payload)
            if payload.get("decision_payload_sha256") != expected_digest:
                raise AlignmentValidationError(
                    "decision card payload SHA does not match its material surface"
                )
            alignment_review_path = Path(args.alignment_review)
            if not alignment_review_path.is_absolute():
                alignment_review_path = repo / alignment_review_path
            alignment_review = _load_json(
                alignment_review_path.resolve(), "semantic alignment review", []
            )
            alignment_reviewer = alignment_review.get("reviewer_context_id", "")
            compliance = validate_card_factory_review(
                repo,
                card_path,
                args.factory_compliance_review,
                forbidden_context_ids={str(alignment_reviewer)} - {""},
            )
            if compliance.errors or compliance.status != PASS_CARD_FACTORY_REVIEW:
                raise AlignmentValidationError(
                    "; ".join(compliance.errors)
                    or "final Card Factory compliance review did not pass"
                )
            alignment_input_path = Path(args.alignment_input)
            if not alignment_input_path.is_absolute():
                alignment_input_path = repo / alignment_input_path
            alignment_input = _load_json(
                alignment_input_path.resolve(), "semantic alignment input", []
            )
            compliance_review_path = Path(args.factory_compliance_review)
            if not compliance_review_path.is_absolute():
                compliance_review_path = repo / compliance_review_path
            compliance_review_path = compliance_review_path.resolve()
            expected_review_ref = {
                "path": compliance_review_path.relative_to(repo).as_posix(),
                "sha256": hashlib.sha256(compliance_review_path.read_bytes()).hexdigest(),
            }
            bound_reviews = [
                item
                for item in alignment_input.get("active_authorities", [])
                if isinstance(item, dict)
                and item.get("authority_id") == CARD_FACTORY_REVIEW_AUTHORITY_ID
                and item.get("authority_kind") == "REPO_EVIDENCE"
                and item.get("artifact") == expected_review_ref
            ]
            if len(bound_reviews) != 1:
                raise AlignmentValidationError(
                    "semantic alignment input must bind the exact final Card Factory "
                    f"review as active authority {CARD_FACTORY_REVIEW_AUTHORITY_ID}"
                )
            register_path = register_pending_card(
                repo,
                card_path,
                args.alignment_input,
                args.alignment_review,
                expected_output_text=render_decision_card(payload),
                supersede_payloads=list(args.supersede_payload),
                recorded_at=args.recorded_at,
            )
        except (OSError, json.JSONDecodeError, AlignmentValidationError) as error:
            print(f"ERROR: {error}", file=sys.stderr)
            return 2
        print(register_path.relative_to(repo).as_posix())
        return 0
    if args.command == "record-card-verdict":
        presentation_errors = validate_studio_card_presentation(
            args.game_repo, args.card
        )
        if presentation_errors:
            for error in presentation_errors:
                print(f"ERROR: {error}", file=sys.stderr)
            return 2
        try:
            card_path = record_card_verdict(
                args.game_repo,
                args.card,
                verdict_token=args.verdict_token,
                recorded_at=args.recorded_at,
            )
        except AlignmentValidationError as error:
            print(f"ERROR: {error}", file=sys.stderr)
            return 2
        print(card_path)
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
