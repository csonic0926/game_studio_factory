"""Validate the human/fresh-review gate for one Objective Gameplay authority.

The compact objective workflow intentionally uses ``OBJECTIVE_GAMEPLAY.md`` as
its design authority.  This module prevents that authority from moving from an
AI draft directly into executable production plans.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DESIGN_VERDICT_NAME = "GAMEPLAY_DESIGN_VERDICT.json"
DESIGN_VERDICT_VERSION = "gameplay_design_verdict.v1"
FACTORY_REVISION_PATTERN = re.compile(r"^[0-9a-f]{7,64}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")

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

EXPECTED_EXPERIENCE_FIELDS = (
    "Target player",
    "Intended experience",
    "Required player work",
    "Earned satisfaction",
    "Failure / recovery",
    "Must not become",
)


@dataclass(frozen=True)
class DesignGateBinding:
    """Validated, exact design authority used by a production manifest."""

    factory_revision: str
    verdict_path: str
    verdict_sha256: str
    context_status: str
    human_verdict: str


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


def _validate_expected_experience(objective_text: str, errors: list[str]) -> None:
    if "## Expected player experience" not in objective_text:
        errors.append("OBJECTIVE_GAMEPLAY.md lacks '## Expected player experience'")
        return
    for field_name in EXPECTED_EXPERIENCE_FIELDS:
        pattern = re.compile(rf"^- {re.escape(field_name)}:\s*(.+)$", re.MULTILINE)
        match = pattern.search(objective_text)
        if match is None or not match.group(1).strip():
            errors.append(
                f"OBJECTIVE_GAMEPLAY.md lacks a filled '- {field_name}:' field"
            )
        elif "TBD" in match.group(1):
            errors.append(
                f"OBJECTIVE_GAMEPLAY.md expected experience {field_name} contains TBD"
            )


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
) -> DesignGateBinding:
    """Validate one exact objective, fresh design review, and human ruling."""

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
    if factory_revision and actual_factory_revision and factory_revision != actual_factory_revision:
        errors.append(
            "factory_revision does not match the Factory HEAD; refresh the design review and plans"
        )

    verdict_path_text, verdict_sha256, verdict_path = _validate_path_hash(
        game_repo, raw_verdict_ref, "design_verdict", errors
    )
    expected_verdict_path = objective_path.parent / DESIGN_VERDICT_NAME
    if verdict_path is not None and verdict_path != expected_verdict_path.resolve():
        errors.append(
            f"design_verdict must be the objective-local {DESIGN_VERDICT_NAME}"
        )

    context_match = _CONTEXT_STATUS_PATTERN.search(objective_text)
    context_status = context_match.group(1).strip() if context_match else ""
    if context_status not in CONTEXT_STATUSES:
        errors.append("OBJECTIVE_GAMEPLAY.md has no supported Context status")
    design_match = _DESIGN_STATUS_PATTERN.search(objective_text)
    design_status = design_match.group(1).strip() if design_match else ""
    if not design_status:
        errors.append("OBJECTIVE_GAMEPLAY.md has no Design status")
    _validate_expected_experience(objective_text, errors)

    human_verdict = ""
    if verdict_path is not None:
        try:
            verdict = json.loads(verdict_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            errors.append(f"cannot read design verdict JSON: {error}")
            verdict = {}
        required = {
            "schema_version",
            "verdict_id",
            "project_id",
            "objective_id",
            "factory_revision",
            "objective_gameplay",
            "context_status",
            "reviewer_context_id",
            "reviewer_freshness",
            "factory_verdict",
            "human_verdict",
            "human_verdict_source",
            "blocking_findings",
            "reviewed_at",
        }
        _require_exact_keys(verdict, "design verdict", required, errors)
        if verdict.get("schema_version") != DESIGN_VERDICT_VERSION:
            errors.append(f"design verdict schema_version must be {DESIGN_VERDICT_VERSION}")
        _require_text(verdict.get("verdict_id"), "design verdict.verdict_id", errors)
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
        if authority_path != objective_path_text or authority_sha != objective_sha256:
            errors.append("design verdict does not bind the exact objective gameplay authority")
        if verdict.get("context_status") != context_status:
            errors.append("design verdict context_status does not match OBJECTIVE_GAMEPLAY.md")
        _require_text(
            verdict.get("reviewer_context_id"),
            "design verdict.reviewer_context_id",
            errors,
        )
        if verdict.get("reviewer_freshness") != "FRESH":
            errors.append("design verdict reviewer_freshness must be FRESH")
        if verdict.get("factory_verdict") != "PASS_DESIGN_REVIEW":
            errors.append("design verdict factory_verdict must be PASS_DESIGN_REVIEW")
        human_verdict = verdict.get("human_verdict", "")
        if human_verdict not in HUMAN_VERDICTS:
            errors.append("design verdict human_verdict is unsupported")
        if (
            context_status == READY_FOR_NEW_GAMEPLAY_DESIGN
            and human_verdict != "USER_APPROVED"
        ):
            errors.append(
                "new gameplay design requires USER_APPROVED after the exact objective draft; delegation is insufficient"
            )
        source = _require_exact_keys(
            verdict.get("human_verdict_source"),
            "design verdict.human_verdict_source",
            {"kind", "text", "recorded_at"},
            errors,
        )
        expected_kind = (
            "POST_DRAFT_APPROVAL"
            if human_verdict == "USER_APPROVED"
            else "EXPLICIT_DELEGATION"
        )
        if source.get("kind") != expected_kind:
            errors.append(
                f"design verdict human_verdict_source.kind must be {expected_kind}"
            )
        _require_text(source.get("text"), "design verdict human_verdict_source.text", errors)
        _require_text(
            source.get("recorded_at"),
            "design verdict human_verdict_source.recorded_at",
            errors,
        )
        if verdict.get("blocking_findings") != []:
            errors.append("design verdict blocking_findings must be empty for PASS")
        _require_text(verdict.get("reviewed_at"), "design verdict.reviewed_at", errors)

    if human_verdict and design_status != human_verdict:
        errors.append(
            "OBJECTIVE_GAMEPLAY.md Design status must equal the recorded human verdict"
        )

    return DesignGateBinding(
        factory_revision=factory_revision,
        verdict_path=verdict_path_text,
        verdict_sha256=verdict_sha256,
        context_status=context_status,
        human_verdict=human_verdict,
    )
