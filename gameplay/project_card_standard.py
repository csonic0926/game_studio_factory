"""Validate game-owned Gameplay Decision Card authoring authority.

The Factory owns this portable envelope, never a game's answers.  A current
Card is eligible only when the game repository owns an active, adopted
standard; the Project Gameplay Profile binds its exact version and bytes; the
Card binds the same standard plus every required composition artifact; and a
fresh project reviewer inventories the complete project rubric.

The project review binds the Card's material payload and rendered surface
rather than the complete Card file.  This deliberately avoids a hash cycle:
the Card contains the project-review path/hash, while the review proves the
unchanging human decision payload.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


STANDARD_SCHEMA_VERSION = "project_gameplay_decision_card_standard.v1"
PROJECT_REVIEW_SCHEMA_VERSION = "gameplay_decision_card_project_review.v1"
PROJECT_REVIEW_NAME = "GAMEPLAY_DECISION_CARD_PROJECT_REVIEW.json"
PROFILE_RELATIVE = Path("design/gameplay/adapter/PROJECT_GAMEPLAY_PROFILE.md")
STANDARD_DIRECTORY = Path("design/gameplay/adapter")
ACTIVE_STANDARD_STATUS = "ACTIVE"
ADOPTED_STATUS = "HUMAN_OR_PROJECT_AUTHORITY_ADOPTED"
PASS_PROJECT_REVIEW = "PASS_PROJECT_CARD_AUTHORING_STANDARD"

ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
PLACEHOLDER_PATTERN = re.compile(r"(?:\bTBD\b|<[^>]+>)", re.IGNORECASE)

_PROFILE_PATTERNS = {
    "path": re.compile(
        r"^- Project Card authoring standard path:\s*`([^`]+)`\s*$",
        re.MULTILINE,
    ),
    "version": re.compile(
        r"^- Project Card authoring standard version:\s*`([^`]+)`\s*$",
        re.MULTILINE,
    ),
    "sha256": re.compile(
        r"^- Project Card authoring standard SHA-256:\s*`([^`]+)`\s*$",
        re.MULTILINE,
    ),
    "status": re.compile(
        r"^- Project Card authoring standard status:\s*`([^`]+)`\s*$",
        re.MULTILINE,
    ),
}


def _exact_object(
    value: Any, label: str, keys: set[str], errors: list[str]
) -> dict[str, Any]:
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object")
        return {}
    for key in sorted(keys - set(value)):
        errors.append(f"{label} is missing {key}")
    for key in sorted(set(value) - keys):
        errors.append(f"{label} contains unsupported field {key}")
    return value


def _text(value: Any, label: str, errors: list[str]) -> str:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label} must be a non-empty string")
        return ""
    result = value.strip()
    if PLACEHOLDER_PATTERN.search(result):
        errors.append(f"{label} contains a placeholder")
    return result


def _identifier(value: Any, label: str, errors: list[str]) -> str:
    result = _text(value, label, errors)
    if result and ID_PATTERN.fullmatch(result) is None:
        errors.append(f"{label} must match {ID_PATTERN.pattern}")
    return result


def _strings(
    value: Any,
    label: str,
    errors: list[str],
    *,
    nonempty: bool = True,
) -> list[str]:
    if not isinstance(value, list) or (nonempty and not value):
        qualifier = "a non-empty array" if nonempty else "an array"
        errors.append(f"{label} must be {qualifier}")
        return []
    result = [_text(item, f"{label}[{index}]", errors) for index, item in enumerate(value)]
    if len(result) != len(set(result)):
        errors.append(f"{label} must contain unique values")
    return result


def _load_json(path: Path, label: str, errors: list[str]) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        errors.append(f"cannot read {label} JSON: {error}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"{label} must be a JSON object")
        return {}
    return value


def _path_hash(
    repo: Path,
    raw: Any,
    label: str,
    errors: list[str],
) -> tuple[dict[str, str], Path | None]:
    ref = _exact_object(raw, label, {"path", "sha256"}, errors)
    path_text = _text(ref.get("path"), f"{label}.path", errors)
    digest = _text(ref.get("sha256"), f"{label}.sha256", errors)
    normalized = {"path": path_text, "sha256": digest}
    if not path_text or not digest:
        return normalized, None
    candidate = Path(path_text)
    if candidate.is_absolute():
        errors.append(f"{label}.path must be game-repo-relative")
        return normalized, None
    path = (repo / candidate).resolve()
    try:
        path.relative_to(repo)
    except ValueError:
        errors.append(f"{label}.path escapes the game repo")
        return normalized, None
    if not path.is_file():
        errors.append(f"{label}.path does not identify a file: {path_text}")
        return normalized, None
    if SHA256_PATTERN.fullmatch(digest) is None:
        errors.append(f"{label}.sha256 must be 64 lowercase hex characters")
    elif hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        errors.append(f"{label} hash does not match {path_text}")
    return normalized, path


def _versioned_path_hash(
    repo: Path,
    raw: Any,
    label: str,
    errors: list[str],
) -> tuple[dict[str, str], Path | None]:
    ref = _exact_object(raw, label, {"path", "version", "sha256"}, errors)
    path_hash, path = _path_hash(
        repo,
        {"path": ref.get("path"), "sha256": ref.get("sha256")},
        label,
        errors,
    )
    version = _text(ref.get("version"), f"{label}.version", errors)
    return {
        "path": path_hash["path"],
        "version": version,
        "sha256": path_hash["sha256"],
    }, path


def _profile_binding(repo: Path, errors: list[str]) -> dict[str, str]:
    profile_path = repo / PROFILE_RELATIVE
    if not profile_path.is_file():
        errors.append(
            "Project Gameplay Profile is missing; project Card authoring authority "
            f"must be declared in {PROFILE_RELATIVE.as_posix()}"
        )
        return {}
    try:
        text = profile_path.read_text(encoding="utf-8")
    except OSError as error:
        errors.append(f"cannot read Project Gameplay Profile: {error}")
        return {}
    result: dict[str, str] = {}
    for field, pattern in _PROFILE_PATTERNS.items():
        match = pattern.search(text)
        if not match:
            errors.append(
                "Project Gameplay Profile is missing exact project Card standard "
                f"binding field: {field}"
            )
            continue
        result[field] = _text(
            match.group(1), f"Project Gameplay Profile standard {field}", errors
        )
    return result


def validate_project_standard(
    game_repo: str | Path,
    raw_ref: Any,
    *,
    project_id: str,
    routing: str,
    errors: list[str],
) -> dict[str, Any]:
    """Validate the active repo-owned standard and its Profile binding."""

    repo = Path(game_repo).expanduser().resolve()
    ref, standard_path = _versioned_path_hash(
        repo, raw_ref, "project Card authoring standard", errors
    )
    profile = _profile_binding(repo, errors)
    if profile:
        if profile.get("path") != ref["path"]:
            errors.append(
                "decision card standard path differs from the active Project Gameplay Profile"
            )
        if profile.get("sha256") != ref["sha256"]:
            errors.append(
                "decision card standard SHA differs from the active Project Gameplay Profile"
            )
        if profile.get("version") != ref["version"]:
            errors.append(
                "decision card standard version differs from the active Project Gameplay Profile"
            )
        if profile.get("status") != ACTIVE_STANDARD_STATUS:
            errors.append(
                "Project Gameplay Profile Card standard status must be ACTIVE"
            )

    expected_parent = (repo / STANDARD_DIRECTORY).resolve()
    if standard_path is not None and standard_path.parent != expected_parent:
        errors.append(
            "project Card authoring standard must be owned under "
            f"{STANDARD_DIRECTORY.as_posix()}/ in the game repository"
        )
    standard = (
        _load_json(standard_path, "project Card authoring standard", errors)
        if standard_path is not None
        else {}
    )
    keys = {
        "schema_version",
        "standard_id",
        "project_id",
        "version",
        "status",
        "applicable_routings",
        "adoption",
        "collaboration_contract",
        "vocabulary",
        "repeatable_lap",
        "player_work_boundary",
        "granularity_rules",
        "interaction_requirements",
        "resolution_boundaries",
        "failure_recovery_replay",
        "validation_methods",
        "independence_rules",
        "synchronization_rules",
        "composition_artifact_kinds",
        "requirements",
        "render_only_requirement_ids",
    }
    _exact_object(standard, "project Card authoring standard", keys, errors)
    if standard.get("schema_version") != STANDARD_SCHEMA_VERSION:
        errors.append(
            "project Card authoring standard schema_version must be "
            + STANDARD_SCHEMA_VERSION
        )
    _identifier(standard.get("standard_id"), "project standard.standard_id", errors)
    if standard.get("project_id") != project_id:
        errors.append("project Card authoring standard project_id does not match the Card")
    version = _text(standard.get("version"), "project standard.version", errors)
    if ref.get("version") != version:
        errors.append("decision card standard bound version differs from the standard")
    if profile and profile.get("version") != version:
        errors.append(
            "Project Gameplay Profile standard version differs from the active standard"
        )
    if standard.get("status") != ACTIVE_STANDARD_STATUS:
        errors.append("project Card authoring standard status must be ACTIVE")
    routings = _strings(
        standard.get("applicable_routings"),
        "project standard.applicable_routings",
        errors,
    )
    allowed_routings = {"STUDIO_WHOLE_GAME", "DIRECT_SPECIALIST"}
    unknown_routings = set(routings) - allowed_routings
    if unknown_routings:
        errors.append(
            "project standard has unsupported routings: "
            + ", ".join(sorted(unknown_routings))
        )
    if routing not in routings:
        errors.append(f"project Card authoring standard does not apply to {routing}")
    if set(routings) != allowed_routings:
        errors.append(
            "active project Card authoring standard must cover both "
            "STUDIO_WHOLE_GAME and DIRECT_SPECIALIST routing"
        )

    adoption = _exact_object(
        standard.get("adoption"),
        "project standard.adoption",
        {"status", "owner", "authority_ref", "adopted_at"},
        errors,
    )
    if adoption.get("status") != ADOPTED_STATUS:
        errors.append(
            "project Card authoring standard must be explicitly adopted by human/project authority"
        )
    for field in ("owner", "authority_ref", "adopted_at"):
        _text(adoption.get(field), f"project standard.adoption.{field}", errors)

    collaboration_ref, collaboration_path = _path_hash(
        repo,
        standard.get("collaboration_contract"),
        "project standard.collaboration_contract",
        errors,
    )
    if collaboration_path is not None:
        if collaboration_path.parent != repo:
            errors.append(
                "project collaboration contract must be a committed root-level "
                "game-repo contract, not a nested or local pointer"
            )
        if ".local." in collaboration_path.name.lower():
            errors.append(
                "project collaboration contract must not be a machine-local pointer"
            )
        try:
            collaboration_text = collaboration_path.read_text(encoding="utf-8")
        except OSError as error:
            errors.append(f"cannot read project collaboration contract: {error}")
        else:
            if ref["path"] not in collaboration_text:
                errors.append(
                    "project collaboration contract must point to the canonical Card standard path"
                )

    vocabulary = standard.get("vocabulary")
    vocabulary_ids: list[str] = []
    if not isinstance(vocabulary, list) or not vocabulary:
        errors.append("project standard.vocabulary must be a non-empty array")
        vocabulary = []
    for index, raw in enumerate(vocabulary):
        item = _exact_object(
            raw,
            f"project standard.vocabulary[{index}]",
            {"term_id", "term", "definition"},
            errors,
        )
        vocabulary_ids.append(
            _identifier(
                item.get("term_id"),
                f"project standard.vocabulary[{index}].term_id",
                errors,
            )
        )
        _text(item.get("term"), f"project standard.vocabulary[{index}].term", errors)
        _text(
            item.get("definition"),
            f"project standard.vocabulary[{index}].definition",
            errors,
        )
    if len(vocabulary_ids) != len(set(vocabulary_ids)):
        errors.append("project standard vocabulary term_id values must be unique")

    for field in (
        "repeatable_lap",
        "player_work_boundary",
        "granularity_rules",
        "interaction_requirements",
        "resolution_boundaries",
        "failure_recovery_replay",
        "independence_rules",
        "synchronization_rules",
    ):
        _strings(standard.get(field), f"project standard.{field}", errors)

    methods = standard.get("validation_methods")
    method_ids: list[str] = []
    if not isinstance(methods, list) or not methods:
        errors.append("project standard.validation_methods must be a non-empty array")
        methods = []
    for index, raw in enumerate(methods):
        item = _exact_object(
            raw,
            f"project standard.validation_methods[{index}]",
            {"method_id", "use", "observable_evidence", "falsification_rule"},
            errors,
        )
        method_ids.append(
            _identifier(
                item.get("method_id"),
                f"project standard.validation_methods[{index}].method_id",
                errors,
            )
        )
        for field in ("use", "observable_evidence", "falsification_rule"):
            _text(
                item.get(field),
                f"project standard.validation_methods[{index}].{field}",
                errors,
            )
    if len(method_ids) != len(set(method_ids)):
        errors.append("project standard validation method ids must be unique")

    kinds = standard.get("composition_artifact_kinds")
    kind_ids: list[str] = []
    required_kind_ids: set[str] = set()
    if not isinstance(kinds, list) or not kinds:
        errors.append(
            "project standard.composition_artifact_kinds must be a non-empty array"
        )
        kinds = []
    for index, raw in enumerate(kinds):
        item = _exact_object(
            raw,
            f"project standard.composition_artifact_kinds[{index}]",
            {"kind_id", "name", "purpose", "required"},
            errors,
        )
        kind_id = _identifier(
            item.get("kind_id"),
            f"project standard.composition_artifact_kinds[{index}].kind_id",
            errors,
        )
        kind_ids.append(kind_id)
        _text(item.get("name"), f"project standard.composition_artifact_kinds[{index}].name", errors)
        _text(
            item.get("purpose"),
            f"project standard.composition_artifact_kinds[{index}].purpose",
            errors,
        )
        if not isinstance(item.get("required"), bool):
            errors.append(
                f"project standard.composition_artifact_kinds[{index}].required must be boolean"
            )
        elif item["required"] and kind_id:
            required_kind_ids.add(kind_id)
    if len(kind_ids) != len(set(kind_ids)):
        errors.append("project standard composition artifact kind ids must be unique")
    if not required_kind_ids:
        errors.append("project standard must require at least one composition artifact kind")

    requirements = standard.get("requirements")
    requirement_ids: list[str] = []
    requirement_surfaces: dict[str, str] = {}
    if not isinstance(requirements, list) or not requirements:
        errors.append("project standard.requirements must be a non-empty array")
        requirements = []
    for index, raw in enumerate(requirements):
        item = _exact_object(
            raw,
            f"project standard.requirements[{index}]",
            {"requirement_id", "rule", "applicability", "evidence_surface"},
            errors,
        )
        requirement_id = _identifier(
            item.get("requirement_id"),
            f"project standard.requirements[{index}].requirement_id",
            errors,
        )
        requirement_ids.append(requirement_id)
        _text(item.get("rule"), f"project standard.requirements[{index}].rule", errors)
        _text(
            item.get("applicability"),
            f"project standard.requirements[{index}].applicability",
            errors,
        )
        if item.get("evidence_surface") not in {
            "CARD",
            "COMPOSITION",
            "INTERACTION_CONTRACT",
            "MULTIPLE",
        }:
            errors.append(
                f"project standard.requirements[{index}].evidence_surface is unsupported"
            )
        elif requirement_id:
            requirement_surfaces[requirement_id] = str(item["evidence_surface"])
    requirement_ids = [item for item in requirement_ids if item]
    if len(requirement_ids) != len(set(requirement_ids)):
        errors.append("project standard requirement ids must be unique")
    render_ids = _strings(
        standard.get("render_only_requirement_ids"),
        "project standard.render_only_requirement_ids",
        errors,
    )
    unknown_render_ids = set(render_ids) - set(requirement_ids)
    if unknown_render_ids:
        errors.append(
            "project standard render-only requirements are not declared: "
            + ", ".join(sorted(unknown_render_ids))
        )
    non_card_render_ids = {
        requirement_id
        for requirement_id in render_ids
        if requirement_surfaces.get(requirement_id) not in {"CARD", "MULTIPLE"}
    }
    if non_card_render_ids:
        errors.append(
            "project standard render-only requirements must include the Card as an "
            "evidence surface: " + ", ".join(sorted(non_card_render_ids))
        )

    return {
        "ref": ref,
        "path": standard_path,
        "standard": standard,
        "version": version,
        "requirement_ids": set(requirement_ids),
        "requirement_surfaces": requirement_surfaces,
        "render_requirement_ids": set(render_ids),
        "composition_kind_ids": set(kind_ids),
        "required_composition_kind_ids": required_kind_ids,
        "validation_method_ids": set(method_ids),
        "collaboration_contract": collaboration_ref,
    }


def validate_composition_artifacts(
    game_repo: str | Path,
    raw_artifacts: Any,
    *,
    standard_binding: dict[str, Any],
    errors: list[str],
) -> list[dict[str, Any]]:
    """Validate exact game-owned pre-Card composition artifacts."""

    repo = Path(game_repo).expanduser().resolve()
    if not isinstance(raw_artifacts, list) or not raw_artifacts:
        errors.append("project_composition_artifacts must be a non-empty array")
        return []
    results: list[dict[str, Any]] = []
    artifact_ids: list[str] = []
    kind_ids: list[str] = []
    allowed_kinds = set(standard_binding.get("composition_kind_ids", set()))
    for index, raw in enumerate(raw_artifacts):
        item = _exact_object(
            raw,
            f"project_composition_artifacts[{index}]",
            {"artifact_id", "kind_id", "path", "sha256", "author_context_id"},
            errors,
        )
        artifact_id = _identifier(
            item.get("artifact_id"),
            f"project_composition_artifacts[{index}].artifact_id",
            errors,
        )
        kind_id = _identifier(
            item.get("kind_id"),
            f"project_composition_artifacts[{index}].kind_id",
            errors,
        )
        author = _identifier(
            item.get("author_context_id"),
            f"project_composition_artifacts[{index}].author_context_id",
            errors,
        )
        ref, path = _path_hash(
            repo,
            {"path": item.get("path"), "sha256": item.get("sha256")},
            f"project_composition_artifacts[{index}]",
            errors,
        )
        if kind_id and kind_id not in allowed_kinds:
            errors.append(
                f"project_composition_artifacts[{index}].kind_id is not declared by the active standard"
            )
        if path is not None:
            standard_path = standard_binding.get("path")
            if standard_path is not None and path == standard_path:
                errors.append("the project Card standard cannot substitute for a composition artifact")
        artifact_ids.append(artifact_id)
        kind_ids.append(kind_id)
        results.append(
            {
                "artifact_id": artifact_id,
                "kind_id": kind_id,
                "path": ref["path"],
                "sha256": ref["sha256"],
                "author_context_id": author,
            }
        )
    if len(artifact_ids) != len(set(artifact_ids)):
        errors.append("project composition artifact ids must be unique")
    required = set(standard_binding.get("required_composition_kind_ids", set()))
    missing = required - set(kind_ids)
    if missing:
        errors.append(
            "project composition artifacts do not cover required kinds: "
            + ", ".join(sorted(missing))
        )
    return results


def validate_project_review(
    game_repo: str | Path,
    raw_review_ref: Any,
    *,
    card_path: Path,
    card: dict[str, Any],
    standard_binding: dict[str, Any],
    composition_artifacts: list[dict[str, Any]],
    interaction_contract_ref: dict[str, str],
    interaction_contract_review_ref: dict[str, str],
    interaction_contract_author: str,
    card_claim_ids: set[str],
    decision_payload_sha256: str,
    rendered_surface_sha256: str,
    errors: list[str],
) -> dict[str, Any]:
    """Validate the fresh project-specific Card review."""

    repo = Path(game_repo).expanduser().resolve()
    ref, review_path = _path_hash(repo, raw_review_ref, "project Card review", errors)
    expected_review_path = card_path.with_name(PROJECT_REVIEW_NAME).resolve()
    if review_path is not None and review_path != expected_review_path:
        errors.append(f"project Card review must be the objective-local {PROJECT_REVIEW_NAME}")
    review = (
        _load_json(review_path, "project Card review", errors)
        if review_path is not None
        else {}
    )
    keys = {
        "schema_version",
        "review_id",
        "review_role",
        "project_id",
        "objective_id",
        "factory_revision",
        "project_card_authoring_standard",
        "project_composition_artifacts",
        "player_facing_interaction_contract",
        "player_facing_interaction_contract_review",
        "decision_card",
        "author_context_ids",
        "reviewer_context_id",
        "reviewer_freshness",
        "requirement_findings",
        "render_only_findings",
        "blocking_findings",
        "verdict",
        "reviewed_at",
    }
    _exact_object(review, "project Card review", keys, errors)
    if review.get("schema_version") != PROJECT_REVIEW_SCHEMA_VERSION:
        errors.append(
            "project Card review schema_version must be " + PROJECT_REVIEW_SCHEMA_VERSION
        )
    if review.get("review_role") != "PROJECT_CARD_AUTHORING_STANDARD_REVIEW":
        errors.append(
            "project Card review review_role must be PROJECT_CARD_AUTHORING_STANDARD_REVIEW"
        )
    _identifier(review.get("review_id"), "project Card review.review_id", errors)
    for field in ("project_id", "objective_id", "factory_revision"):
        if review.get(field) != card.get(field):
            errors.append(f"project Card review {field} does not match the Card")

    for field, expected in (
        ("project_card_authoring_standard", standard_binding.get("ref", {})),
        ("player_facing_interaction_contract", interaction_contract_ref),
        ("player_facing_interaction_contract_review", interaction_contract_review_ref),
    ):
        if field == "project_card_authoring_standard":
            actual, _ = _versioned_path_hash(
                repo,
                review.get(field),
                f"project Card review.{field}",
                errors,
            )
        else:
            actual, _ = _path_hash(
                repo,
                review.get(field),
                f"project Card review.{field}",
                errors,
            )
        if actual != expected:
            errors.append(f"project Card review.{field} does not bind the exact Card authority")

    reviewed_compositions = review.get("project_composition_artifacts")
    if not isinstance(reviewed_compositions, list):
        errors.append("project Card review.project_composition_artifacts must be an array")
        reviewed_compositions = []
    normalized_reviewed: list[dict[str, Any]] = []
    for index, raw in enumerate(reviewed_compositions):
        item = _exact_object(
            raw,
            f"project Card review.project_composition_artifacts[{index}]",
            {"artifact_id", "kind_id", "path", "sha256", "author_context_id"},
            errors,
        )
        normalized_reviewed.append(
            {
                "artifact_id": item.get("artifact_id"),
                "kind_id": item.get("kind_id"),
                "path": item.get("path"),
                "sha256": item.get("sha256"),
                "author_context_id": item.get("author_context_id"),
            }
        )
    if normalized_reviewed != composition_artifacts:
        errors.append("project Card review does not bind the exact ordered composition artifacts")

    decision = _exact_object(
        review.get("decision_card"),
        "project Card review.decision_card",
        {"path", "decision_payload_sha256", "rendered_surface_sha256"},
        errors,
    )
    expected_card_path = card_path.resolve().relative_to(repo).as_posix()
    if decision.get("path") != expected_card_path:
        errors.append("project Card review binds a different decision-card path")
    if decision.get("decision_payload_sha256") != decision_payload_sha256:
        errors.append("project Card review binds a different decision payload")
    if decision.get("rendered_surface_sha256") != rendered_surface_sha256:
        errors.append("project Card review binds a different rendered Card surface")

    authors = _exact_object(
        review.get("author_context_ids"),
        "project Card review.author_context_ids",
        {
            "composition_artifact_authors",
            "interaction_contract_author",
            "decision_card_author",
        },
        errors,
    )
    declared_composition_authors = _strings(
        authors.get("composition_artifact_authors"),
        "project Card review.author_context_ids.composition_artifact_authors",
        errors,
    )
    expected_composition_authors = [
        str(item.get("author_context_id", "")) for item in composition_artifacts
    ]
    if declared_composition_authors != expected_composition_authors:
        errors.append("project Card review composition author ids do not match the Card bindings")
    if authors.get("interaction_contract_author") != interaction_contract_author:
        errors.append("project Card review interaction Contract author id does not match")
    if authors.get("decision_card_author") != card.get("author_context_id"):
        errors.append("project Card review decision Card author id does not match")
    reviewer = _identifier(
        review.get("reviewer_context_id"),
        "project Card review.reviewer_context_id",
        errors,
    )
    if review.get("reviewer_freshness") != "FRESH":
        errors.append("project Card review reviewer_freshness must be FRESH")
    forbidden = {
        *expected_composition_authors,
        interaction_contract_author,
        str(card.get("author_context_id", "")),
    } - {""}
    if reviewer in forbidden:
        errors.append(
            "project Card reviewer must differ from every composition, Contract, and Card author"
        )

    expected_requirements = set(standard_binding.get("requirement_ids", set()))
    requirement_surfaces = dict(
        standard_binding.get("requirement_surfaces", {})
    )
    findings = review.get("requirement_findings")
    if not isinstance(findings, list):
        errors.append("project Card review.requirement_findings must be an array")
        findings = []
    found_ids: list[str] = []
    for index, raw in enumerate(findings):
        item = _exact_object(
            raw,
            f"project Card review.requirement_findings[{index}]",
            {"requirement_id", "applicability", "verdict", "evidence_refs", "rationale"},
            errors,
        )
        requirement_id = _identifier(
            item.get("requirement_id"),
            f"project Card review.requirement_findings[{index}].requirement_id",
            errors,
        )
        found_ids.append(requirement_id)
        applicability = item.get("applicability")
        verdict = item.get("verdict")
        if applicability not in {"APPLICABLE", "NOT_APPLICABLE"}:
            errors.append(
                f"project Card review.requirement_findings[{index}].applicability is unsupported"
            )
        expected_verdict = "PASS" if applicability == "APPLICABLE" else "NOT_APPLICABLE"
        if verdict != expected_verdict:
            errors.append(
                f"project Card review.requirement_findings[{index}].verdict must be {expected_verdict}"
            )
        evidence = item.get("evidence_refs")
        if not isinstance(evidence, list) or (applicability == "APPLICABLE" and not evidence):
            errors.append(
                f"project Card review.requirement_findings[{index}].evidence_refs must be a non-empty array for applicable requirements"
            )
            evidence = []
        cited_surfaces: set[str] = set()
        for evidence_index, raw_evidence in enumerate(evidence):
            evidence_item = _exact_object(
                raw_evidence,
                f"project Card review.requirement_findings[{index}].evidence_refs[{evidence_index}]",
                {"surface", "ref"},
                errors,
            )
            surface = evidence_item.get("surface")
            if isinstance(surface, str):
                cited_surfaces.add(surface)
            ref_id = _text(
                evidence_item.get("ref"),
                f"project Card review.requirement_findings[{index}].evidence_refs[{evidence_index}].ref",
                errors,
            )
            if surface == "CARD_CLAIM" and ref_id not in card_claim_ids:
                errors.append(
                    f"project Card review requirement finding cites unknown Card claim: {ref_id}"
                )
            elif surface == "COMPOSITION_ARTIFACT" and ref_id not in {
                str(value.get("artifact_id")) for value in composition_artifacts
            }:
                errors.append(
                    f"project Card review requirement finding cites unknown composition artifact: {ref_id}"
                )
            elif surface not in {"CARD_CLAIM", "COMPOSITION_ARTIFACT", "INTERACTION_CONTRACT"}:
                errors.append(
                    f"project Card review.requirement_findings[{index}] evidence surface is unsupported"
                )
        if applicability == "APPLICABLE":
            declared_surface = requirement_surfaces.get(requirement_id)
            required_review_surfaces = {
                "CARD": {"CARD_CLAIM"},
                "COMPOSITION": {"COMPOSITION_ARTIFACT"},
                "INTERACTION_CONTRACT": {"INTERACTION_CONTRACT"},
            }
            if declared_surface in required_review_surfaces and not (
                required_review_surfaces[declared_surface] & cited_surfaces
            ):
                errors.append(
                    f"project Card review requirement {requirement_id} must cite its "
                    f"declared {declared_surface} evidence surface"
                )
            if declared_surface == "MULTIPLE" and len(cited_surfaces) < 2:
                errors.append(
                    f"project Card review requirement {requirement_id} declares MULTIPLE "
                    "evidence surfaces and must cite at least two distinct surfaces"
                )
        _text(
            item.get("rationale"),
            f"project Card review.requirement_findings[{index}].rationale",
            errors,
        )
    found_ids = [item for item in found_ids if item]
    if len(found_ids) != len(set(found_ids)):
        errors.append("project Card review repeats a standard requirement id")
    if set(found_ids) != expected_requirements:
        missing = expected_requirements - set(found_ids)
        extra = set(found_ids) - expected_requirements
        if missing:
            errors.append(
                "project Card review misses declared standard requirements: "
                + ", ".join(sorted(missing))
            )
        if extra:
            errors.append(
                "project Card review invents standard requirements: "
                + ", ".join(sorted(extra))
            )

    expected_render = set(standard_binding.get("render_requirement_ids", set()))
    render_findings = review.get("render_only_findings")
    if not isinstance(render_findings, list):
        errors.append("project Card review.render_only_findings must be an array")
        render_findings = []
    render_ids: list[str] = []
    for index, raw in enumerate(render_findings):
        item = _exact_object(
            raw,
            f"project Card review.render_only_findings[{index}]",
            {"requirement_id", "evidence_claim_ids", "verdict", "rationale"},
            errors,
        )
        requirement_id = _identifier(
            item.get("requirement_id"),
            f"project Card review.render_only_findings[{index}].requirement_id",
            errors,
        )
        render_ids.append(requirement_id)
        evidence_ids = _strings(
            item.get("evidence_claim_ids"),
            f"project Card review.render_only_findings[{index}].evidence_claim_ids",
            errors,
        )
        unknown = set(evidence_ids) - card_claim_ids
        if unknown:
            errors.append(
                "project Card review render-only finding cites unknown Card claims: "
                + ", ".join(sorted(unknown))
            )
        if item.get("verdict") != "PASS":
            errors.append(
                f"project Card review.render_only_findings[{index}].verdict must be PASS"
            )
        _text(
            item.get("rationale"),
            f"project Card review.render_only_findings[{index}].rationale",
            errors,
        )
    if len(render_ids) != len(set(render_ids)):
        errors.append("project Card review repeats a render-only requirement id")
    if set(render_ids) != expected_render:
        errors.append(
            "project Card review render-only findings must exactly inventory the active standard checklist"
        )

    if review.get("blocking_findings") != []:
        errors.append("project Card review.blocking_findings must be empty")
    if review.get("verdict") != PASS_PROJECT_REVIEW:
        errors.append("project Card review.verdict must be " + PASS_PROJECT_REVIEW)
    _text(review.get("reviewed_at"), "project Card review.reviewed_at", errors)
    return {"ref": ref, "review": review, "reviewer_context_id": reviewer}


def inspect_active_project_standard(game_repo: str | Path) -> tuple[bool, list[str]]:
    """Lightweight initialization probe for a Profile-declared active standard."""

    repo = Path(game_repo).expanduser().resolve()
    errors: list[str] = []
    profile = _profile_binding(repo, errors)
    if not profile:
        return False, errors
    validate_project_standard(
        repo,
        {
            "path": profile.get("path", ""),
            "version": profile.get("version", ""),
            "sha256": profile.get("sha256", ""),
        },
        project_id=_profile_project_id(repo, errors),
        routing="STUDIO_WHOLE_GAME",
        errors=errors,
    )
    return not errors, errors


def _profile_project_id(repo: Path, errors: list[str]) -> str:
    profile_path = repo / PROFILE_RELATIVE
    try:
        text = profile_path.read_text(encoding="utf-8")
    except OSError:
        return ""
    match = re.search(r"^# Project Gameplay Profile — `([^`]+)`\s*$", text, re.MULTILINE)
    if not match:
        errors.append("Project Gameplay Profile has no canonical project id heading")
        return ""
    return _identifier(match.group(1), "Project Gameplay Profile project id", errors)
