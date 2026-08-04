#!/usr/bin/env python3
"""Deterministic Accepted Playable Baseline admission.

One public entry routes two causal transitions:

  RECONSTRUCT  repository + fresh acceptance -> B0 (or an explicit rebuild)
  PROMOTE      Bt + completed workflow + fresh acceptance + regression -> Bt+1

The compiler binds evidence and promotes state. It never authors an experience
verdict, accepts an implementation status as gameplay acceptance, or mutates a
predecessor baseline.
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


FACTORY_ROOT = Path(__file__).resolve().parents[1]
ADMISSIONS_ROOT = Path("design/studio/admissions")
BASELINES_ROOT = Path("design/studio/baselines")
RUN_STATE_PATH = Path("design/studio/STUDIO_RUN_STATE.json")
INPUT_NAME = "BASELINE_ADMISSION_INPUT.json"
RESULT_NAME = "BASELINE_ADMISSION_RESULT.json"

RECONSTRUCT = "RECONSTRUCT"
PROMOTE = "PROMOTE"

BASELINE_RECONSTRUCTION_INPUT_REQUIRED = "BASELINE_RECONSTRUCTION_INPUT_REQUIRED"
BASELINE_PROMOTION_INPUT_REQUIRED = "BASELINE_PROMOTION_INPUT_REQUIRED"
BASELINE_ADMITTED = "BASELINE_ADMITTED"
BASELINE_ADMISSION_VALID = "BASELINE_ADMISSION_VALID"
BLOCKED_BY_BASELINE_STATE = "BLOCKED_BY_BASELINE_STATE"
BLOCKED_BY_ADMISSION_MATERIAL = "BLOCKED_BY_ADMISSION_MATERIAL"
BLOCKED_BY_EXISTING_BASELINE = "BLOCKED_BY_EXISTING_BASELINE"

ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
REVISION_PATTERN = re.compile(r"^[0-9a-f]{7,64}$")
SPECIALISTS = {"idea", "gameplay", "story", "asset", "sound", "repo_production"}

ACCEPTANCE_REVIEW_VERSION = "gameplay_acceptance_review.v2"
ACCEPTANCE_INPUT_VERSION = "gameplay_acceptance_input.v1"
WORKFLOW_COMPLETION_VERSION = "studio_workflow_completion.v2"
BASELINE_VERSION = "accepted_playable_baseline.v2"
RUN_STATE_VERSION = "studio_run_state.v2"
LEGACY_ACCEPTANCE_REVIEW_VERSION = "gameplay_acceptance_review.v1"
LEGACY_WORKFLOW_COMPLETION_VERSION = "studio_workflow_completion.v1"


class BaselineAdmissionError(ValueError):
    """Raised before any command creates a directory or writes a file."""


@dataclass
class BaselineAdmissionResult:
    status: str
    mode: str = ""
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    created_paths: list[str] = field(default_factory=list)
    verified_paths: list[str] = field(default_factory=list)


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _run_git(game_repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-C", str(game_repo), *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise BaselineAdmissionError(f"git {' '.join(args)} failed: {detail}")
    return result


def _resolve_game_repo(raw_path: str) -> Path:
    game_repo = Path(raw_path).expanduser().resolve()
    if not game_repo.is_dir():
        raise BaselineAdmissionError(f"game repo does not exist: {game_repo}")
    if game_repo == FACTORY_ROOT or _is_within(game_repo, FACTORY_ROOT):
        raise BaselineAdmissionError("game repo must not be the Studio checkout or its child")
    root = _run_git(game_repo, "rev-parse", "--show-toplevel").stdout.strip()
    if Path(root).resolve() != game_repo:
        raise BaselineAdmissionError(f"game repo must be the Git root, not a child: {game_repo}")
    return game_repo


def _resolve_cli_path(game_repo: Path, raw_path: str, *, must_exist: bool = False) -> Path:
    candidate = Path(raw_path).expanduser()
    resolved = (candidate if candidate.is_absolute() else game_repo / candidate).resolve()
    if not _is_within(resolved, game_repo):
        raise BaselineAdmissionError(f"path escapes game repo: {raw_path}")
    if must_exist and not resolved.exists():
        raise BaselineAdmissionError(f"required path does not exist: {raw_path}")
    return resolved


def _resolve_persisted_path(
    game_repo: Path,
    raw_path: Any,
    *,
    must_exist: bool = False,
) -> Path:
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise BaselineAdmissionError("persisted paths must be non-empty strings")
    candidate = Path(raw_path)
    if candidate.is_absolute():
        raise BaselineAdmissionError(f"persisted path must be game-repo-relative: {raw_path}")
    return _resolve_cli_path(game_repo, raw_path, must_exist=must_exist)


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise BaselineAdmissionError(f"cannot read {label} JSON: {error}") from error
    if not isinstance(payload, dict):
        raise BaselineAdmissionError(f"{label} JSON must contain an object")
    return payload


def _json_text(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _sha256_text(value: str) -> str:
    return _sha256_bytes(value.encode("utf-8"))


def _relative(game_repo: Path, path: Path) -> str:
    return path.resolve().relative_to(game_repo).as_posix()


def _require_keys(
    payload: Any,
    label: str,
    required: set[str],
    errors: list[str],
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        errors.append(f"{label} must be an object")
        return {}
    missing = sorted(required - set(payload))
    extra = sorted(set(payload) - required)
    for key in missing:
        errors.append(f"{label} is missing {key}")
    for key in extra:
        errors.append(f"{label} contains unsupported field {key}")
    return payload


def _require_text(value: Any, label: str, errors: list[str], *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        errors.append(f"{label} must be a string")
        return ""
    text = value.strip()
    if not allow_empty and not text:
        errors.append(f"{label} must be a non-empty string")
    if "TBD" in text:
        errors.append(f"{label} must not contain TBD")
    return text


def _require_id(value: Any, label: str, errors: list[str]) -> str:
    text = _require_text(value, label, errors)
    if text and ID_PATTERN.fullmatch(text) is None:
        errors.append(f"{label} must match {ID_PATTERN.pattern}")
    return text


def _require_string_list(
    value: Any,
    label: str,
    errors: list[str],
    *,
    allow_empty: bool = False,
) -> list[str]:
    if not isinstance(value, list):
        errors.append(f"{label} must be an array")
        return []
    if not value and not allow_empty:
        errors.append(f"{label} must contain at least one value")
    result: list[str] = []
    for index, item in enumerate(value):
        text = _require_text(item, f"{label}[{index}]", errors)
        if text:
            result.append(text)
    if len(result) != len(set(result)):
        errors.append(f"{label} must not contain duplicates")
    return result


def _require_id_list(
    value: Any,
    label: str,
    errors: list[str],
    *,
    allow_empty: bool = False,
) -> list[str]:
    result = _require_string_list(value, label, errors, allow_empty=allow_empty)
    for index, item in enumerate(result):
        if ID_PATTERN.fullmatch(item) is None:
            errors.append(f"{label}[{index}] must match {ID_PATTERN.pattern}")
    return result


def _empty_ref() -> dict[str, str]:
    return {"path": "", "sha256": ""}


def _validate_ref(
    game_repo: Path,
    value: Any,
    label: str,
    errors: list[str],
    *,
    allow_empty: bool = False,
) -> dict[str, str]:
    payload = _require_keys(value, label, {"path", "sha256"}, errors)
    if not payload:
        return _empty_ref()
    path_text = _require_text(payload.get("path"), f"{label}.path", errors, allow_empty=allow_empty)
    digest = _require_text(payload.get("sha256"), f"{label}.sha256", errors, allow_empty=allow_empty)
    if not path_text and not digest and allow_empty:
        return _empty_ref()
    if not path_text or not digest:
        errors.append(f"{label} path and sha256 must both be set or both be empty")
        return {"path": path_text, "sha256": digest}
    if SHA256_PATTERN.fullmatch(digest) is None:
        errors.append(f"{label}.sha256 must be 64 lowercase hex characters")
    try:
        path = _resolve_persisted_path(game_repo, path_text, must_exist=True)
    except BaselineAdmissionError as error:
        errors.append(f"{label}: {error}")
        return {"path": path_text, "sha256": digest}
    if not path.is_file():
        errors.append(f"{label}.path must identify a file: {path_text}")
    elif SHA256_PATTERN.fullmatch(digest) and _sha256_file(path) != digest:
        errors.append(f"{label} hash does not match {path_text}")
    return {"path": path_text, "sha256": digest}


def _ref_for_file(game_repo: Path, path: Path) -> dict[str, str]:
    return {"path": _relative(game_repo, path), "sha256": _sha256_file(path)}


def _current_revision(game_repo: Path) -> str:
    return _run_git(game_repo, "rev-parse", "HEAD").stdout.strip()


def _current_factory_revision() -> str:
    result = subprocess.run(
        ["git", "-C", str(FACTORY_ROOT), "rev-parse", "HEAD"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    revision = result.stdout.strip()
    if result.returncode != 0 or REVISION_PATTERN.fullmatch(revision) is None:
        detail = result.stderr.strip() or "Factory checkout has no readable HEAD"
        raise BaselineAdmissionError(detail)
    return revision


def _revision_is_ancestor(game_repo: Path, revision: str) -> bool:
    return _run_git(game_repo, "merge-base", "--is-ancestor", revision, "HEAD", check=False).returncode == 0


def _runtime_dirty_paths(game_repo: Path) -> list[str]:
    output = _run_git(game_repo, "status", "--porcelain=v1", "--untracked-files=all").stdout
    paths: list[str] = []
    for line in output.splitlines():
        if len(line) < 4:
            continue
        raw = line[3:]
        if " -> " in raw:
            raw = raw.split(" -> ", 1)[1]
        normalized = raw.strip('"')
        if normalized == "design/studio" or normalized.startswith("design/studio/"):
            continue
        paths.append(normalized)
    return sorted(set(paths))


def _is_tracked_path(game_repo: Path, relative: Path) -> bool:
    return _run_git(
        game_repo,
        "ls-files",
        "--error-unmatch",
        "--",
        relative.as_posix(),
        check=False,
    ).returncode == 0


def _validate_current_baseline_payload(payload: dict[str, Any], label: str, errors: list[str]) -> None:
    schema_version = payload.get("schema_version")
    if schema_version not in {"accepted_playable_baseline.v1", BASELINE_VERSION}:
        errors.append(f"{label}.schema_version is unsupported")
    if payload.get("status") != "ACCEPTED_PLAYABLE_BASELINE":
        errors.append(f"{label}.status is not ACCEPTED_PLAYABLE_BASELINE")
    _require_id(payload.get("project_id"), f"{label}.project_id", errors)
    _require_id(payload.get("baseline_id"), f"{label}.baseline_id", errors)
    units = payload.get("accepted_gameplay_units")
    if not isinstance(units, list) or not units:
        errors.append(f"{label}.accepted_gameplay_units must be a non-empty array")
        units = []
    if schema_version == BASELINE_VERSION:
        factory_revision = payload.get("factory_revision")
        if not isinstance(factory_revision, str) or REVISION_PATTERN.fullmatch(factory_revision) is None:
            errors.append(f"{label}.factory_revision must be a Git revision")
        for index, unit in enumerate(units):
            if not isinstance(unit, dict):
                errors.append(f"{label}.accepted_gameplay_units[{index}] must be an object")
                continue
            review = unit.get("acceptance_review")
            if not isinstance(review, dict):
                errors.append(
                    f"{label}.accepted_gameplay_units[{index}].acceptance_review must be an object"
                )
                continue
            if review.get("experience_authority") != unit.get("authority"):
                errors.append(
                    f"{label}.accepted_gameplay_units[{index}] acceptance authority does not match"
                )
            if review.get("human_playtest_status") not in {
                "HUMAN_PLAYTEST_ACCEPTED", "LEGACY_ACCEPTANCE_GRANDFATHERED"
            }:
                errors.append(
                    f"{label}.accepted_gameplay_units[{index}] has no trusted human playtest status"
                )
    eligibility = payload.get("delivery_eligibility")
    if not isinstance(eligibility, dict):
        errors.append(f"{label}.delivery_eligibility must be an object")
    elif (
        eligibility.get("interactive_demo_only") is not False
        or eligibility.get("minimum_gameplay_passed") is not True
        or eligibility.get("blocking_gap_ids") != []
    ):
        errors.append(f"{label} is not delivery eligible")


def _load_current_baseline(
    game_repo: Path,
) -> tuple[dict[str, str] | None, dict[str, Any] | None]:
    state_path = game_repo / RUN_STATE_PATH
    if not state_path.exists():
        return None, None
    if not state_path.is_file():
        raise BaselineAdmissionError(f"Studio run state is not a file: {RUN_STATE_PATH}")
    state = _load_json(state_path, "Studio run state")
    current = state.get("current_baseline")
    if current == _empty_ref() or current is None:
        return None, None
    errors: list[str] = []
    ref = _validate_ref(game_repo, current, "current_baseline", errors)
    if errors:
        raise BaselineAdmissionError("; ".join(errors))
    baseline = _load_json(game_repo / ref["path"], "current accepted baseline")
    _validate_current_baseline_payload(baseline, "current_baseline", errors)
    if state.get("schema_version") not in {"studio_run_state.v1", RUN_STATE_VERSION}:
        errors.append("Studio run state has unsupported schema_version")
    if state.get("schema_version") == RUN_STATE_VERSION:
        if state.get("factory_revision") != baseline.get("factory_revision"):
            errors.append("Studio run state factory_revision does not match current baseline")
        acceptance = state.get("acceptance")
        if not isinstance(acceptance, dict) or acceptance.get("human_playtest_status") != "ACCEPTED":
            errors.append("Studio run state has no accepted human playtest status")
    if state.get("project_id") != baseline.get("project_id"):
        errors.append("Studio run state project_id does not match current baseline")
    if errors:
        raise BaselineAdmissionError("; ".join(errors))
    return ref, baseline


def start_baseline_admission(
    game_repo_text: str,
    *,
    reconstruct: bool = False,
) -> BaselineAdmissionResult:
    game_repo = _resolve_game_repo(game_repo_text)
    try:
        current_ref, _ = _load_current_baseline(game_repo)
    except BaselineAdmissionError as error:
        if not reconstruct:
            return BaselineAdmissionResult(BLOCKED_BY_BASELINE_STATE, errors=[str(error)])
        return BaselineAdmissionResult(
            BASELINE_RECONSTRUCTION_INPUT_REQUIRED,
            mode=RECONSTRUCT,
            warnings=[f"explicit reconstruction requested with untrusted state: {error}"],
        )
    if reconstruct or current_ref is None:
        warning = ""
        if reconstruct and current_ref is not None:
            warning = "explicit reconstruction will supersede the current baseline without mutating it"
        return BaselineAdmissionResult(
            BASELINE_RECONSTRUCTION_INPUT_REQUIRED,
            mode=RECONSTRUCT,
            warnings=[warning] if warning else [],
        )
    return BaselineAdmissionResult(BASELINE_PROMOTION_INPUT_REQUIRED, mode=PROMOTE)


def _validate_runnable_build(
    game_repo: Path,
    value: Any,
    errors: list[str],
) -> dict[str, Any]:
    payload = _require_keys(
        value,
        "runnable_build",
        {"build_id", "launch_command", "artifact_paths", "supported_platforms"},
        errors,
    )
    build_id = _require_id(payload.get("build_id"), "runnable_build.build_id", errors)
    launch = _require_text(payload.get("launch_command"), "runnable_build.launch_command", errors)
    platforms = _require_string_list(payload.get("supported_platforms"), "runnable_build.supported_platforms", errors)
    raw_refs = payload.get("artifact_paths")
    if not isinstance(raw_refs, list) or not raw_refs:
        errors.append("runnable_build.artifact_paths must contain at least one file reference")
        refs: list[dict[str, str]] = []
    else:
        refs = [
            _validate_ref(game_repo, item, f"runnable_build.artifact_paths[{index}]", errors)
            for index, item in enumerate(raw_refs)
        ]
    return {
        "build_id": build_id,
        "launch_command": launch,
        "artifact_paths": refs,
        "supported_platforms": platforms,
    }


def _validate_playable_scope(value: Any, errors: list[str]) -> dict[str, Any]:
    payload = _require_keys(
        value,
        "playable_scope",
        {"entry_condition", "completion_condition", "expected_minutes", "gameplay_loop"},
        errors,
    )
    minutes = payload.get("expected_minutes")
    if not isinstance(minutes, (int, float)) or isinstance(minutes, bool) or minutes <= 0:
        errors.append("playable_scope.expected_minutes must be a positive number")
        minutes = 0
    return {
        "entry_condition": _require_text(payload.get("entry_condition"), "playable_scope.entry_condition", errors),
        "completion_condition": _require_text(payload.get("completion_condition"), "playable_scope.completion_condition", errors),
        "expected_minutes": minutes,
        "gameplay_loop": _require_text(payload.get("gameplay_loop"), "playable_scope.gameplay_loop", errors),
    }


def _validate_acceptance_review(
    game_repo: Path,
    ref: dict[str, str],
    *,
    project_id: str,
    unit_id: str,
    game_revision: str,
    build_id: str,
    authority_ref: dict[str, str],
    factory_revision: str,
    production_context_ids: set[str],
    allow_legacy_historical: bool,
    errors: list[str],
) -> dict[str, Any]:
    if not ref["path"]:
        return {}
    review_path = game_repo / ref["path"]
    if not review_path.is_file():
        return {}
    review = _load_json(review_path, f"acceptance review for {unit_id}")
    schema_version = review.get("schema_version")
    if schema_version == LEGACY_ACCEPTANCE_REVIEW_VERSION:
        if not allow_legacy_historical:
            errors.append(
                f"acceptance review {unit_id} is legacy historical evidence; "
                f"new admission requires {ACCEPTANCE_REVIEW_VERSION} with canonical "
                "experience authority and a human playtest verdict"
            )
        required = {
            "schema_version", "review_id", "project_id", "unit_id", "game_revision",
            "build_id", "reviewer_context_id", "reviewer_freshness", "verdict",
            "acceptance_input", "evidence_paths", "observed_complete_loop",
            "blocking_findings", "reviewed_at",
        }
    else:
        required = {
            "schema_version", "review_id", "project_id", "unit_id", "game_revision",
            "build_id", "factory_revision", "experience_authority",
            "reviewer_context_id", "reviewer_freshness", "verdict",
            "acceptance_input", "human_playtest", "evidence_paths",
            "observed_complete_loop", "blocking_findings", "reviewed_at",
        }
    _require_keys(review, f"acceptance review {unit_id}", required, errors)
    if schema_version not in {LEGACY_ACCEPTANCE_REVIEW_VERSION, ACCEPTANCE_REVIEW_VERSION}:
        errors.append(f"acceptance review {unit_id} has unsupported schema_version")
    _require_id(review.get("review_id"), f"acceptance review {unit_id}.review_id", errors)
    if review.get("project_id") != project_id:
        errors.append(f"acceptance review {unit_id} project_id does not match admission")
    if review.get("unit_id") != unit_id:
        errors.append(f"acceptance review {unit_id} unit_id does not match")
    if review.get("game_revision") != game_revision:
        errors.append(f"acceptance review {unit_id} game_revision does not match")
    if review.get("build_id") != build_id:
        errors.append(f"acceptance review {unit_id} build_id does not match")
    reviewer = _require_id(review.get("reviewer_context_id"), f"acceptance review {unit_id}.reviewer_context_id", errors)
    if reviewer in production_context_ids:
        errors.append(f"acceptance review {unit_id} reuses a production context")
    if review.get("reviewer_freshness") != "FRESH":
        errors.append(f"acceptance review {unit_id} is not marked FRESH")
    if review.get("verdict") != "ACCEPTED":
        errors.append(f"acceptance review {unit_id} verdict must be ACCEPTED")
    acceptance_input_ref = _validate_ref(
        game_repo,
        review.get("acceptance_input"),
        f"acceptance review {unit_id}.acceptance_input",
        errors,
    )
    human_playtest_status = "LEGACY_ACCEPTANCE_GRANDFATHERED"
    if schema_version == ACCEPTANCE_REVIEW_VERSION:
        if review.get("factory_revision") != factory_revision:
            errors.append(
                f"acceptance review {unit_id} factory_revision does not match the active Factory"
            )
        experience_authority = _validate_ref(
            game_repo,
            review.get("experience_authority"),
            f"acceptance review {unit_id}.experience_authority",
            errors,
        )
        if experience_authority != authority_ref:
            errors.append(
                f"acceptance review {unit_id} must bind the exact admitted unit authority"
            )
        _validate_gameplay_acceptance_input(
            game_repo,
            review_path=review_path,
            ref=acceptance_input_ref,
            project_id=project_id,
            unit_id=unit_id,
            game_revision=game_revision,
            build_id=build_id,
            factory_revision=factory_revision,
            authority_ref=authority_ref,
            errors=errors,
        )
        human = _require_keys(
            review.get("human_playtest"),
            f"acceptance review {unit_id}.human_playtest",
            {"status", "verdict_owner", "verdict_source", "accepted_at"},
            errors,
        )
        if human.get("status") != "HUMAN_PLAYTEST_ACCEPTED":
            errors.append(
                f"acceptance review {unit_id}.human_playtest.status must be HUMAN_PLAYTEST_ACCEPTED"
            )
        if human.get("verdict_owner") != "USER":
            errors.append(
                f"acceptance review {unit_id}.human_playtest.verdict_owner must be USER"
            )
        _require_text(
            human.get("verdict_source"),
            f"acceptance review {unit_id}.human_playtest.verdict_source",
            errors,
        )
        _require_text(
            human.get("accepted_at"),
            f"acceptance review {unit_id}.human_playtest.accepted_at",
            errors,
        )
        human_playtest_status = str(human.get("status", ""))
    evidence = review.get("evidence_paths")
    if not isinstance(evidence, list) or not evidence:
        errors.append(f"acceptance review {unit_id}.evidence_paths must not be empty")
    else:
        for index, item in enumerate(evidence):
            _validate_ref(game_repo, item, f"acceptance review {unit_id}.evidence_paths[{index}]", errors)
    loop = _require_keys(
        review.get("observed_complete_loop"),
        f"acceptance review {unit_id}.observed_complete_loop",
        {"goal", "actions", "consequences", "completion"},
        errors,
    )
    _require_text(loop.get("goal"), f"acceptance review {unit_id}.observed_complete_loop.goal", errors)
    _require_string_list(loop.get("actions"), f"acceptance review {unit_id}.observed_complete_loop.actions", errors)
    _require_text(loop.get("consequences"), f"acceptance review {unit_id}.observed_complete_loop.consequences", errors)
    _require_text(loop.get("completion"), f"acceptance review {unit_id}.observed_complete_loop.completion", errors)
    if review.get("blocking_findings") != []:
        errors.append(f"acceptance review {unit_id}.blocking_findings must be empty for ACCEPTED")
    _require_text(review.get("reviewed_at"), f"acceptance review {unit_id}.reviewed_at", errors)
    return {
        **ref,
        "reviewer_freshness": "FRESH",
        "verdict": "ACCEPTED",
        "experience_authority": authority_ref,
        "human_playtest_status": human_playtest_status,
    }


def _validate_gameplay_acceptance_input(
    game_repo: Path,
    *,
    review_path: Path,
    ref: dict[str, str],
    project_id: str,
    unit_id: str,
    game_revision: str,
    build_id: str,
    factory_revision: str,
    authority_ref: dict[str, str],
    errors: list[str],
) -> None:
    if not ref["path"]:
        return
    path = game_repo / ref["path"]
    if not path.is_file():
        return
    expected_name = f"GAMEPLAY_ACCEPTANCE_INPUT_{unit_id}.json"
    if path.parent != review_path.parent or path.name != expected_name:
        errors.append(
            f"acceptance input for {unit_id} must be admission-local {expected_name}"
        )
    payload = _load_json(path, f"gameplay acceptance input for {unit_id}")
    required = {
        "schema_version", "acceptance_input_id", "project_id", "unit_id",
        "game_revision", "build_id", "factory_revision", "experience_authority",
        "expected_player_experience", "playtest_questions", "non_claims", "prepared_at",
    }
    _require_keys(payload, f"gameplay acceptance input {unit_id}", required, errors)
    if payload.get("schema_version") != ACCEPTANCE_INPUT_VERSION:
        errors.append(
            f"gameplay acceptance input {unit_id}.schema_version must be {ACCEPTANCE_INPUT_VERSION}"
        )
    _require_id(
        payload.get("acceptance_input_id"),
        f"gameplay acceptance input {unit_id}.acceptance_input_id",
        errors,
    )
    for field, expected in (
        ("project_id", project_id),
        ("unit_id", unit_id),
        ("game_revision", game_revision),
        ("build_id", build_id),
        ("factory_revision", factory_revision),
    ):
        if payload.get(field) != expected:
            errors.append(f"gameplay acceptance input {unit_id}.{field} does not match")
    bound_authority = _validate_ref(
        game_repo,
        payload.get("experience_authority"),
        f"gameplay acceptance input {unit_id}.experience_authority",
        errors,
    )
    if bound_authority != authority_ref:
        errors.append(
            f"gameplay acceptance input {unit_id} must bind the exact admitted unit authority"
        )
    expected = _require_keys(
        payload.get("expected_player_experience"),
        f"gameplay acceptance input {unit_id}.expected_player_experience",
        {
            "target_player", "intended_experience", "required_player_work",
            "earned_satisfaction", "failure_recovery", "must_not_become",
        },
        errors,
    )
    for field in (
        "target_player", "intended_experience", "required_player_work",
        "earned_satisfaction", "failure_recovery", "must_not_become",
    ):
        _require_text(
            expected.get(field),
            f"gameplay acceptance input {unit_id}.expected_player_experience.{field}",
            errors,
        )
    _require_string_list(
        payload.get("playtest_questions"),
        f"gameplay acceptance input {unit_id}.playtest_questions",
        errors,
    )
    _require_string_list(
        payload.get("non_claims"),
        f"gameplay acceptance input {unit_id}.non_claims",
        errors,
    )
    _require_text(
        payload.get("prepared_at"),
        f"gameplay acceptance input {unit_id}.prepared_at",
        errors,
    )


def _validate_unit(
    game_repo: Path,
    value: Any,
    index: int,
    *,
    project_id: str,
    game_revision: str,
    build_id: str,
    factory_revision: str,
    production_context_ids: set[str],
    allow_legacy_historical: bool,
    errors: list[str],
) -> dict[str, Any]:
    label = f"admitted_units[{index}]"
    payload = _require_keys(
        value,
        label,
        {"unit_id", "authority", "player_goal", "meaningful_actions", "consequence_or_reward", "acceptance_review"},
        errors,
    )
    unit_id = _require_id(payload.get("unit_id"), f"{label}.unit_id", errors)
    authority = _validate_ref(game_repo, payload.get("authority"), f"{label}.authority", errors)
    review_ref = _validate_ref(game_repo, payload.get("acceptance_review"), f"{label}.acceptance_review", errors)
    review_summary = _validate_acceptance_review(
        game_repo,
        review_ref,
        project_id=project_id,
        unit_id=unit_id,
        game_revision=game_revision,
        build_id=build_id,
        authority_ref=authority,
        factory_revision=factory_revision,
        production_context_ids=production_context_ids,
        allow_legacy_historical=allow_legacy_historical,
        errors=errors,
    )
    return {
        "unit_id": unit_id,
        "authority": authority,
        "player_goal": _require_text(payload.get("player_goal"), f"{label}.player_goal", errors),
        "meaningful_actions": _require_string_list(payload.get("meaningful_actions"), f"{label}.meaningful_actions", errors),
        "consequence_or_reward": _require_text(payload.get("consequence_or_reward"), f"{label}.consequence_or_reward", errors),
        "acceptance_review": review_summary,
    }


def _validate_workflow_completion(
    game_repo: Path,
    ref: dict[str, str],
    *,
    project_id: str,
    game_revision: str,
    factory_revision: str,
    admitted_unit_ids: set[str],
    allow_legacy_historical: bool,
    errors: list[str],
) -> set[str]:
    if not ref["path"]:
        return set()
    completion_path = game_repo / ref["path"]
    if not completion_path.is_file():
        return set()
    payload = _load_json(completion_path, "Studio workflow completion")
    schema_version = payload.get("schema_version")
    required = {
        "schema_version", "completion_id", "status", "project_id", "game_revision",
        "specialists", "workflow_kind", "unit_ids", "production_context_ids",
        "source_authorities", "implementation_results", "test_results", "completed_at",
    }
    if schema_version == WORKFLOW_COMPLETION_VERSION:
        required.add("factory_revision")
    _require_keys(payload, "workflow_completion", required, errors)
    if schema_version == LEGACY_WORKFLOW_COMPLETION_VERSION:
        if not allow_legacy_historical:
            errors.append(
                "workflow_completion is legacy historical evidence; new promotion "
                f"requires {WORKFLOW_COMPLETION_VERSION}"
            )
    elif schema_version != WORKFLOW_COMPLETION_VERSION:
        errors.append("workflow_completion has unsupported schema_version")
    if schema_version == WORKFLOW_COMPLETION_VERSION and payload.get("factory_revision") != factory_revision:
        errors.append("workflow_completion factory_revision does not match the active Factory")
    if payload.get("status") != "IMPLEMENTED_PENDING_ACCEPTANCE":
        errors.append("workflow_completion status must be IMPLEMENTED_PENDING_ACCEPTANCE")
    if payload.get("project_id") != project_id:
        errors.append("workflow_completion project_id does not match admission")
    if payload.get("game_revision") != game_revision:
        errors.append("workflow_completion game_revision does not match admission")
    _require_id(payload.get("completion_id"), "workflow_completion.completion_id", errors)
    specialists = _require_string_list(payload.get("specialists"), "workflow_completion.specialists", errors)
    for specialist in specialists:
        if specialist not in SPECIALISTS:
            errors.append(f"workflow_completion has unsupported specialist {specialist}")
    _require_text(payload.get("workflow_kind"), "workflow_completion.workflow_kind", errors)
    completion_unit_ids = set(_require_id_list(payload.get("unit_ids"), "workflow_completion.unit_ids", errors))
    if admitted_unit_ids != completion_unit_ids:
        errors.append("workflow_completion unit ids must exactly equal admitted unit ids")
    contexts = set(_require_id_list(payload.get("production_context_ids"), "workflow_completion.production_context_ids", errors))
    for field_name in ("source_authorities", "implementation_results", "test_results"):
        refs = payload.get(field_name)
        if not isinstance(refs, list) or not refs:
            errors.append(f"workflow_completion.{field_name} must contain at least one reference")
            continue
        for index, item in enumerate(refs):
            _validate_ref(game_repo, item, f"workflow_completion.{field_name}[{index}]", errors)
    _require_text(payload.get("completed_at"), "workflow_completion.completed_at", errors)
    return contexts


def _validate_reconstruction_inventory(
    game_repo: Path,
    ref: dict[str, str],
    *,
    project_id: str,
    game_revision: str,
    admitted_unit_ids: set[str],
    author_context_ids: set[str],
    errors: list[str],
) -> None:
    if not ref["path"]:
        errors.append("RECONSTRUCT requires a complete reconstruction inventory")
        return
    inventory_path = game_repo / ref["path"]
    if not inventory_path.is_file():
        return
    payload = _load_json(inventory_path, "baseline reconstruction inventory")
    required = {
        "schema_version", "inventory_id", "status", "project_id",
        "game_revision", "author_context_id", "source_paths",
        "discovered_unit_ids", "excluded_candidates", "completed_at",
    }
    _require_keys(payload, "reconstruction inventory", required, errors)
    if payload.get("schema_version") != "baseline_reconstruction_inventory.v1":
        errors.append("reconstruction inventory has unsupported schema_version")
    _require_id(payload.get("inventory_id"), "reconstruction inventory.inventory_id", errors)
    if payload.get("status") != "COMPLETE_CURRENT_PLAYABLE_SCOPE":
        errors.append("reconstruction inventory status must be COMPLETE_CURRENT_PLAYABLE_SCOPE")
    if payload.get("project_id") != project_id:
        errors.append("reconstruction inventory project_id does not match admission")
    if payload.get("game_revision") != game_revision:
        errors.append("reconstruction inventory game_revision does not match admission")
    author = _require_id(payload.get("author_context_id"), "reconstruction inventory.author_context_id", errors)
    if author not in author_context_ids:
        errors.append("reconstruction inventory author must be a reconstruction context")
    source_paths = payload.get("source_paths")
    if not isinstance(source_paths, list) or not source_paths:
        errors.append("reconstruction inventory.source_paths must not be empty")
    else:
        for index, item in enumerate(source_paths):
            _validate_ref(game_repo, item, f"reconstruction inventory.source_paths[{index}]", errors)
    discovered = set(_require_id_list(
        payload.get("discovered_unit_ids"),
        "reconstruction inventory.discovered_unit_ids",
        errors,
    ))
    if discovered != admitted_unit_ids:
        errors.append("reconstruction inventory unit ids must exactly equal admitted unit ids")
    excluded = payload.get("excluded_candidates")
    if not isinstance(excluded, list):
        errors.append("reconstruction inventory.excluded_candidates must be an array")
    else:
        for index, item in enumerate(excluded):
            candidate = _require_keys(
                item,
                f"reconstruction inventory.excluded_candidates[{index}]",
                {"candidate_id", "reason", "evidence"},
                errors,
            )
            _require_id(candidate.get("candidate_id"), f"reconstruction inventory.excluded_candidates[{index}].candidate_id", errors)
            _require_text(candidate.get("reason"), f"reconstruction inventory.excluded_candidates[{index}].reason", errors)
            _validate_ref(game_repo, candidate.get("evidence"), f"reconstruction inventory.excluded_candidates[{index}].evidence", errors)
    _require_text(payload.get("completed_at"), "reconstruction inventory.completed_at", errors)


def _validate_regression_review(
    game_repo: Path,
    ref: dict[str, str],
    *,
    project_id: str,
    game_revision: str,
    build_id: str,
    predecessor_ref: dict[str, str],
    predecessor_unit_ids: set[str],
    production_context_ids: set[str],
    verification_commands: set[str],
    verification_results: list[dict[str, str]],
    errors: list[str],
) -> None:
    if not ref["path"]:
        errors.append("promotion requires a regression review")
        return
    review_path = game_repo / ref["path"]
    if not review_path.is_file():
        return
    payload = _load_json(review_path, "baseline regression review")
    required = {
        "schema_version", "review_id", "project_id", "game_revision", "build_id",
        "reviewer_context_id", "reviewer_freshness", "predecessor_baseline",
        "covered_unit_ids", "commands", "result_paths", "status",
        "blocking_findings", "reviewed_at",
    }
    _require_keys(payload, "regression_review", required, errors)
    if payload.get("schema_version") != "baseline_regression_review.v1":
        errors.append("regression_review has unsupported schema_version")
    _require_id(payload.get("review_id"), "regression_review.review_id", errors)
    if payload.get("project_id") != project_id:
        errors.append("regression_review project_id does not match admission")
    if payload.get("game_revision") != game_revision:
        errors.append("regression_review game_revision does not match admission")
    if payload.get("build_id") != build_id:
        errors.append("regression_review build_id does not match admission")
    reviewer = _require_id(payload.get("reviewer_context_id"), "regression_review.reviewer_context_id", errors)
    if reviewer in production_context_ids:
        errors.append("regression_review reuses a production context")
    if payload.get("reviewer_freshness") != "FRESH":
        errors.append("regression_review is not marked FRESH")
    review_predecessor = _validate_ref(game_repo, payload.get("predecessor_baseline"), "regression_review.predecessor_baseline", errors)
    if review_predecessor != predecessor_ref:
        errors.append("regression_review predecessor does not match admission")
    covered = set(_require_id_list(payload.get("covered_unit_ids"), "regression_review.covered_unit_ids", errors, allow_empty=True))
    if covered != predecessor_unit_ids:
        errors.append("regression_review must cover exactly every predecessor gameplay unit")
    commands = set(_require_string_list(payload.get("commands"), "regression_review.commands", errors))
    if not commands.issubset(verification_commands):
        errors.append("regression_review commands are not all bound by verification")
    raw_results = payload.get("result_paths")
    review_results: list[dict[str, str]] = []
    if not isinstance(raw_results, list) or not raw_results:
        errors.append("regression_review.result_paths must not be empty")
    else:
        review_results = [
            _validate_ref(game_repo, item, f"regression_review.result_paths[{index}]", errors)
            for index, item in enumerate(raw_results)
        ]
    verification_pairs = {(item["path"], item["sha256"]) for item in verification_results}
    if not {(item["path"], item["sha256"]) for item in review_results}.issubset(verification_pairs):
        errors.append("regression_review results are not all bound by verification")
    if payload.get("status") != "PASS":
        errors.append("regression_review status must be PASS")
    if payload.get("blocking_findings") != []:
        errors.append("regression_review.blocking_findings must be empty for PASS")
    _require_text(payload.get("reviewed_at"), "regression_review.reviewed_at", errors)


def _merge_units(predecessor: dict[str, Any] | None, admitted: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if predecessor is None:
        return admitted
    replacements = {unit["unit_id"]: unit for unit in admitted}
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for old in predecessor["accepted_gameplay_units"]:
        unit_id = old["unit_id"]
        merged.append(replacements.get(unit_id, old))
        seen.add(unit_id)
    for unit in admitted:
        if unit["unit_id"] not in seen:
            merged.append(unit)
    return merged


def _legacy_unit_shape(unit: dict[str, Any]) -> dict[str, Any]:
    review = unit.get("acceptance_review", {})
    return {
        **unit,
        "acceptance_review": {
            key: review.get(key, "")
            for key in ("path", "sha256", "reviewer_freshness", "verdict")
        },
    }


def _v2_unit_shape(unit: dict[str, Any]) -> dict[str, Any]:
    review = dict(unit.get("acceptance_review", {}))
    review.setdefault("experience_authority", unit.get("authority", _empty_ref()))
    review.setdefault("human_playtest_status", "LEGACY_ACCEPTANCE_GRANDFATHERED")
    return {**unit, "acceptance_review": review}


def _merge_gaps(
    predecessor: dict[str, Any] | None,
    new_gaps: list[dict[str, str]],
    resolved_gap_ids: set[str],
) -> list[dict[str, str]]:
    if predecessor is None:
        return new_gaps
    updates = {gap["gap_id"]: gap for gap in new_gaps}
    merged: list[dict[str, str]] = []
    seen: set[str] = set()
    for old in predecessor.get("known_gaps", []):
        gap_id = old["gap_id"]
        if gap_id in resolved_gap_ids:
            continue
        merged.append(updates.get(gap_id, old))
        seen.add(gap_id)
    for gap in new_gaps:
        if gap["gap_id"] not in seen:
            merged.append(gap)
    return merged


def _validate_admission(
    game_repo: Path,
    input_path: Path,
    *,
    operation: str,
) -> tuple[dict[str, Any], dict[str, Any] | None, dict[Path, str], list[str], list[str]]:
    payload = _load_json(input_path, "baseline admission input")
    errors: list[str] = []
    warnings: list[str] = []
    try:
        factory_revision = _current_factory_revision()
    except BaselineAdmissionError as error:
        errors.append(f"cannot resolve Factory revision: {error}")
        factory_revision = ""
    required = {
        "schema_version", "admission_id", "admission_mode", "project_id",
        "baseline_id", "game_revision", "studio_goal", "requested_horizon",
        "product_authority", "runnable_build", "playable_scope", "admitted_units",
        "verification", "known_gaps", "resolved_gap_ids", "workflow_completion",
        "predecessor_baseline", "reconstruction", "acceptance_owner", "accepted_at",
    }
    _require_keys(payload, "baseline admission input", required, errors)
    if payload.get("schema_version") != "baseline_admission_input.v1":
        errors.append("schema_version must be baseline_admission_input.v1")
    admission_id = _require_id(payload.get("admission_id"), "admission_id", errors)
    baseline_id = _require_id(payload.get("baseline_id"), "baseline_id", errors)
    project_id = _require_id(payload.get("project_id"), "project_id", errors)
    mode = payload.get("admission_mode")
    if mode not in {RECONSTRUCT, PROMOTE}:
        errors.append("admission_mode must be RECONSTRUCT or PROMOTE")
        mode = ""
    game_revision = _require_text(payload.get("game_revision"), "game_revision", errors)
    if game_revision and REVISION_PATTERN.fullmatch(game_revision) is None:
        errors.append("game_revision must be 7-64 lowercase hex characters")
    if game_revision:
        if operation == "compile" and game_revision != _current_revision(game_repo):
            errors.append("game_revision must equal the current HEAD before admission")
        elif operation == "check" and not _revision_is_ancestor(game_repo, game_revision):
            errors.append("game_revision is not an ancestor of current HEAD")
    dirty = _runtime_dirty_paths(game_repo)
    if operation == "compile" and dirty:
        errors.append("runtime-affecting working tree paths must be committed before admission: " + ", ".join(dirty))

    expected_input = ADMISSIONS_ROOT / admission_id / INPUT_NAME if admission_id else Path()
    if admission_id and input_path != (game_repo / expected_input).resolve():
        errors.append(f"admission input must be {expected_input.as_posix()}")

    current_ref: dict[str, str] | None = None
    current_baseline: dict[str, Any] | None = None
    if operation == "compile":
        try:
            current_ref, current_baseline = _load_current_baseline(game_repo)
        except BaselineAdmissionError as error:
            errors.append(f"current baseline state is invalid: {error}")
    current_is_same_admission = bool(
        current_baseline
        and current_baseline.get("baseline_id") == baseline_id
        and isinstance(current_baseline.get("promotion"), dict)
        and current_baseline["promotion"].get("admission_input")
        == _ref_for_file(game_repo, input_path)
    )
    allow_legacy_historical = operation == "check" or current_is_same_admission

    predecessor_ref = _validate_ref(
        game_repo,
        payload.get("predecessor_baseline"),
        "predecessor_baseline",
        errors,
        allow_empty=True,
    )
    predecessor: dict[str, Any] | None = None
    if predecessor_ref["path"]:
        predecessor_path = game_repo / predecessor_ref["path"]
        if predecessor_path.is_file():
            predecessor = _load_json(predecessor_path, "predecessor baseline")
            _validate_current_baseline_payload(predecessor, "predecessor_baseline", errors)

    reconstruction = _require_keys(
        payload.get("reconstruction"),
        "reconstruction",
        {"trigger", "reason", "author_context_ids", "inventory", "superseded_baseline"},
        errors,
    )
    trigger = _require_text(reconstruction.get("trigger"), "reconstruction.trigger", errors, allow_empty=mode == PROMOTE)
    reason = _require_text(reconstruction.get("reason"), "reconstruction.reason", errors, allow_empty=mode == PROMOTE)
    author_context_ids = set(_require_id_list(
        reconstruction.get("author_context_ids"),
        "reconstruction.author_context_ids",
        errors,
        allow_empty=mode == PROMOTE,
    ))
    superseded_ref = _validate_ref(
        game_repo,
        reconstruction.get("superseded_baseline"),
        "reconstruction.superseded_baseline",
        errors,
        allow_empty=True,
    )
    inventory_ref = _validate_ref(
        game_repo,
        reconstruction.get("inventory"),
        "reconstruction.inventory",
        errors,
        allow_empty=True,
    )

    workflow_ref = _validate_ref(
        game_repo,
        payload.get("workflow_completion"),
        "workflow_completion",
        errors,
        allow_empty=True,
    )
    if mode == RECONSTRUCT:
        if trigger not in {"NO_ACCEPTED_BASELINE", "EXPLICIT_REBUILD"}:
            errors.append("RECONSTRUCT trigger must be NO_ACCEPTED_BASELINE or EXPLICIT_REBUILD")
        if predecessor_ref != _empty_ref():
            errors.append("RECONSTRUCT must not claim a predecessor baseline")
        if workflow_ref != _empty_ref():
            errors.append("RECONSTRUCT must not claim a completed workflow")
        if inventory_ref == _empty_ref():
            errors.append("RECONSTRUCT requires reconstruction.inventory")
        if operation == "compile":
            if current_is_same_admission:
                pass
            elif current_ref is None and trigger != "NO_ACCEPTED_BASELINE":
                errors.append("reconstruction without a current baseline must use NO_ACCEPTED_BASELINE")
            elif current_ref is not None:
                if trigger != "EXPLICIT_REBUILD":
                    errors.append("reconstruction with a current baseline requires EXPLICIT_REBUILD")
                if superseded_ref != current_ref:
                    errors.append("explicit reconstruction must bind the exact superseded current baseline")
        production_context_ids = author_context_ids
    else:
        if trigger or reason or author_context_ids or inventory_ref != _empty_ref() or superseded_ref != _empty_ref():
            errors.append("PROMOTE must leave reconstruction fields empty")
        if predecessor_ref == _empty_ref():
            errors.append("PROMOTE requires predecessor_baseline")
        if workflow_ref == _empty_ref():
            errors.append("PROMOTE requires workflow_completion")
        if operation == "compile" and not current_is_same_admission and current_ref is not None and predecessor_ref != current_ref:
            errors.append("PROMOTE predecessor must equal the current accepted baseline")
        if operation == "compile" and not current_is_same_admission and current_ref is None:
            errors.append("PROMOTE requires an existing current accepted baseline")
        production_context_ids = set()

    product_authority = _validate_ref(game_repo, payload.get("product_authority"), "product_authority", errors)
    if product_authority["path"] != "design/product/PRODUCT_THESIS.md":
        errors.append("product_authority.path must be design/product/PRODUCT_THESIS.md")
    runnable_build = _validate_runnable_build(game_repo, payload.get("runnable_build"), errors)
    playable_scope = _validate_playable_scope(payload.get("playable_scope"), errors)

    raw_units = payload.get("admitted_units")
    if not isinstance(raw_units, list) or not raw_units:
        errors.append("admitted_units must contain at least one accepted gameplay unit")
        raw_units = []
    preliminary_ids = {
        item.get("unit_id")
        for item in raw_units
        if isinstance(item, dict) and isinstance(item.get("unit_id"), str)
    }
    if mode == RECONSTRUCT:
        _validate_reconstruction_inventory(
            game_repo,
            inventory_ref,
            project_id=project_id,
            game_revision=game_revision,
            admitted_unit_ids=preliminary_ids,
            author_context_ids=author_context_ids,
            errors=errors,
        )
    elif mode == PROMOTE:
        production_context_ids = _validate_workflow_completion(
            game_repo,
            workflow_ref,
            project_id=project_id,
            game_revision=game_revision,
            factory_revision=factory_revision,
            admitted_unit_ids=preliminary_ids,
            allow_legacy_historical=allow_legacy_historical,
            errors=errors,
        )
    if not production_context_ids:
        errors.append("at least one production/reconstruction context id is required")

    admitted = [
        _validate_unit(
            game_repo,
            item,
            index,
            project_id=project_id,
            game_revision=game_revision,
            build_id=runnable_build["build_id"],
            factory_revision=factory_revision,
            production_context_ids=production_context_ids,
            allow_legacy_historical=allow_legacy_historical,
            errors=errors,
        )
        for index, item in enumerate(raw_units)
    ]
    admitted_ids = [unit["unit_id"] for unit in admitted]
    legacy_admission_material = any(
        unit.get("acceptance_review", {}).get("human_playtest_status")
        == "LEGACY_ACCEPTANCE_GRANDFATHERED"
        for unit in admitted
    )
    if len(admitted_ids) != len(set(admitted_ids)):
        errors.append("admitted_units must not contain duplicate unit_id values")

    if predecessor is not None and predecessor.get("project_id") != project_id:
        errors.append("predecessor project_id does not match admission")

    verification = _require_keys(
        payload.get("verification"),
        "verification",
        {"commands", "result_paths", "regression_review"},
        errors,
    )
    commands = _require_string_list(verification.get("commands"), "verification.commands", errors)
    raw_results = verification.get("result_paths")
    if not isinstance(raw_results, list) or not raw_results:
        errors.append("verification.result_paths must contain at least one reference")
        result_refs: list[dict[str, str]] = []
    else:
        result_refs = [
            _validate_ref(game_repo, item, f"verification.result_paths[{index}]", errors)
            for index, item in enumerate(raw_results)
        ]
    regression_ref = _validate_ref(
        game_repo,
        verification.get("regression_review"),
        "verification.regression_review",
        errors,
        allow_empty=True,
    )
    predecessor_unit_ids = {
        unit["unit_id"] for unit in predecessor.get("accepted_gameplay_units", [])
    } if predecessor else set()
    if mode == RECONSTRUCT:
        if regression_ref != _empty_ref():
            errors.append("RECONSTRUCT must not claim predecessor regression")
    else:
        _validate_regression_review(
            game_repo,
            regression_ref,
            project_id=project_id,
            game_revision=game_revision,
            build_id=runnable_build["build_id"],
            predecessor_ref=predecessor_ref,
            predecessor_unit_ids=predecessor_unit_ids,
            production_context_ids=production_context_ids,
            verification_commands=set(commands),
            verification_results=result_refs,
            errors=errors,
        )

    raw_gaps = payload.get("known_gaps")
    if not isinstance(raw_gaps, list):
        errors.append("known_gaps must be an array")
        raw_gaps = []
    gaps: list[dict[str, str]] = []
    for index, item in enumerate(raw_gaps):
        gap = _require_keys(item, f"known_gaps[{index}]", {"gap_id", "severity", "description"}, errors)
        gap_id = _require_id(gap.get("gap_id"), f"known_gaps[{index}].gap_id", errors)
        if gap.get("severity") != "NON_BLOCKING":
            errors.append(f"known_gaps[{index}].severity must be NON_BLOCKING")
        gaps.append({
            "gap_id": gap_id,
            "severity": "NON_BLOCKING",
            "description": _require_text(gap.get("description"), f"known_gaps[{index}].description", errors),
        })
    if len({gap["gap_id"] for gap in gaps}) != len(gaps):
        errors.append("known_gaps must not contain duplicate gap_id values")
    resolved_gap_ids = set(_require_id_list(payload.get("resolved_gap_ids"), "resolved_gap_ids", errors, allow_empty=True))
    if mode == RECONSTRUCT and resolved_gap_ids:
        errors.append("RECONSTRUCT cannot resolve gaps from a predecessor")
    predecessor_gap_ids = {gap["gap_id"] for gap in predecessor.get("known_gaps", [])} if predecessor else set()
    if not resolved_gap_ids.issubset(predecessor_gap_ids):
        errors.append("resolved_gap_ids must identify predecessor known gaps")

    studio_goal = _require_text(payload.get("studio_goal"), "studio_goal", errors)
    requested_horizon = _require_text(payload.get("requested_horizon"), "requested_horizon", errors)
    acceptance_owner = _require_text(payload.get("acceptance_owner"), "acceptance_owner", errors)
    if acceptance_owner != "USER" and not (
        allow_legacy_historical and legacy_admission_material
    ):
        errors.append("acceptance_owner must be USER")
    accepted_at = _require_text(payload.get("accepted_at"), "accepted_at", errors)

    if errors or not admission_id or not baseline_id:
        return payload, predecessor, {}, errors, warnings

    input_ref = _ref_for_file(game_repo, input_path)
    legacy_output = allow_legacy_historical and legacy_admission_material
    if legacy_output:
        accepted_units = [
            _legacy_unit_shape(unit) for unit in _merge_units(predecessor, admitted)
        ]
    else:
        accepted_units = [
            _v2_unit_shape(unit) for unit in _merge_units(predecessor, admitted)
        ]
    known_gaps = _merge_gaps(predecessor, gaps, resolved_gap_ids)
    baseline_relative = BASELINES_ROOT / baseline_id / "ACCEPTED_PLAYABLE_BASELINE.json"
    baseline_payload = {
        "schema_version": "accepted_playable_baseline.v1" if legacy_output else BASELINE_VERSION,
        "status": "ACCEPTED_PLAYABLE_BASELINE",
        "project_id": project_id,
        "baseline_id": baseline_id,
        "game_revision": game_revision,
        "product_authority": product_authority,
        "runnable_build": runnable_build,
        "playable_scope": playable_scope,
        "accepted_gameplay_units": accepted_units,
        "regression": {
            "commands": commands,
            "result_paths": result_refs,
            "predecessor_checks": [] if mode == RECONSTRUCT else [regression_ref],
        },
        "known_gaps": known_gaps,
        "promotion": {
            "admission_mode": mode,
            "admission_input": input_ref,
            "predecessor_baseline_path": predecessor_ref["path"],
            "predecessor_baseline_sha256": predecessor_ref["sha256"],
            "superseded_baseline": superseded_ref,
            "source_workflow_handoffs": [] if mode == RECONSTRUCT else [workflow_ref],
            "promoted_unit_ids": admitted_ids,
            "acceptance_owner": acceptance_owner,
            "accepted_at": accepted_at,
        },
        "delivery_eligibility": {
            "interactive_demo_only": False,
            "minimum_gameplay_passed": True,
            "blocking_gap_ids": [],
        },
    }
    if not legacy_output:
        baseline_payload["factory_revision"] = factory_revision
    baseline_text = _json_text(baseline_payload)
    baseline_ref = {"path": baseline_relative.as_posix(), "sha256": _sha256_text(baseline_text)}
    result_relative = ADMISSIONS_ROOT / admission_id / RESULT_NAME
    result_payload = {
        "schema_version": "baseline_admission_result.v1",
        "status": BASELINE_ADMITTED,
        "admission_id": admission_id,
        "admission_mode": mode,
        "project_id": project_id,
        "game_revision": game_revision,
        "input": input_ref,
        "predecessor_baseline": predecessor_ref,
        "accepted_baseline": baseline_ref,
        "promoted_unit_ids": admitted_ids,
        "handoff": "Diagnose the next gameplay pressure from the promoted baseline.",
    }
    result_text = _json_text(result_payload)
    state_payload = {
        "schema_version": "studio_run_state.v1" if legacy_output else RUN_STATE_VERSION,
        "project_id": project_id,
        "studio_goal": studio_goal,
        "status": "STUDIO_READY_TO_SCALE",
        "current_baseline": baseline_ref,
        "active_pressure": {"pressure_id": "", "diagnosis": "", "player_effect": ""},
        "research": {"required": False, "path": "", "sha256": ""},
        "candidate_unit": {"unit_id": "", "authority_path": "", "status": "NONE"},
        "workstreams": [],
        "acceptance": {
            "new_gameplay_status": "ACCEPTED",
            "predecessor_regression_status": "NOT_RUN" if mode == RECONSTRUCT else "PASS",
            "candidate_baseline_path": baseline_relative.as_posix(),
        },
        "delivery": {
            "requested_horizon": requested_horizon,
            "eligible": False,
            "baseline_path": baseline_relative.as_posix(),
            "build_paths": [item["path"] for item in runnable_build["artifact_paths"]],
        },
        "blockers": [],
    }
    if not legacy_output:
        state_payload["factory_revision"] = factory_revision
        state_payload["acceptance"]["human_playtest_status"] = "ACCEPTED"
    artifacts = {
        baseline_relative: baseline_text,
        result_relative: result_text,
        RUN_STATE_PATH: _json_text(state_payload),
    }
    return payload, predecessor, artifacts, errors, warnings


def compile_baseline_admission(game_repo_text: str, input_text: str) -> BaselineAdmissionResult:
    game_repo = _resolve_game_repo(game_repo_text)
    input_path = _resolve_cli_path(game_repo, input_text, must_exist=True)
    if not input_path.is_file():
        raise BaselineAdmissionError(f"admission input is not a file: {input_text}")
    payload, _, artifacts, errors, warnings = _validate_admission(
        game_repo, input_path, operation="compile"
    )
    mode = payload.get("admission_mode", "") if isinstance(payload, dict) else ""
    if errors:
        return BaselineAdmissionResult(
            BLOCKED_BY_ADMISSION_MATERIAL,
            mode=mode,
            errors=errors,
            warnings=warnings,
        )

    # Resolve and compare every target before creating any directory or file.
    resolved: dict[Path, tuple[Path, str]] = {}
    conflicts: list[str] = []
    for relative, content in artifacts.items():
        target = _resolve_persisted_path(game_repo, relative.as_posix())
        resolved[relative] = (target, content)
        if relative == RUN_STATE_PATH:
            if not target.exists() and _is_tracked_path(game_repo, relative):
                conflicts.append(
                    "Studio run state is tracked but missing; refusing to recreate an intentional deletion"
                )
            continue
        if target.exists():
            if not target.is_file():
                conflicts.append(f"canonical target is not a file: {relative.as_posix()}")
            elif target.read_text(encoding="utf-8") != content:
                conflicts.append(f"immutable Studio artifact differs and will not be overwritten: {relative.as_posix()}")
        elif _is_tracked_path(game_repo, relative):
            conflicts.append(
                "canonical Studio artifact is tracked but missing; refusing to recreate an intentional deletion: "
                + relative.as_posix()
            )
    if conflicts:
        return BaselineAdmissionResult(
            BLOCKED_BY_EXISTING_BASELINE,
            mode=mode,
            errors=conflicts,
            warnings=warnings,
        )

    created: list[str] = []
    verified: list[str] = []
    for relative, (target, content) in resolved.items():
        if target.exists() and target.is_file() and target.read_text(encoding="utf-8") == content:
            verified.append(relative.as_posix())
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        created.append(relative.as_posix())
    return BaselineAdmissionResult(
        BASELINE_ADMITTED,
        mode=mode,
        warnings=warnings,
        created_paths=sorted(created),
        verified_paths=sorted(verified),
    )


def check_baseline_admission(game_repo_text: str, input_text: str) -> BaselineAdmissionResult:
    game_repo = _resolve_game_repo(game_repo_text)
    input_path = _resolve_cli_path(game_repo, input_text, must_exist=True)
    if not input_path.is_file():
        raise BaselineAdmissionError(f"admission input is not a file: {input_text}")
    payload, _, artifacts, errors, warnings = _validate_admission(
        game_repo, input_path, operation="check"
    )
    mode = payload.get("admission_mode", "") if isinstance(payload, dict) else ""
    verified: list[str] = []
    baseline_paths = [path for path in artifacts if path != RUN_STATE_PATH]
    for relative in baseline_paths:
        expected = artifacts[relative]
        target = _resolve_persisted_path(game_repo, relative.as_posix())
        if not target.exists():
            errors.append(f"generated artifact is missing: {relative.as_posix()}")
        elif not target.is_file():
            errors.append(f"generated artifact is not a file: {relative.as_posix()}")
        elif target.read_text(encoding="utf-8") != expected:
            errors.append(f"generated artifact is stale or changed: {relative.as_posix()}")
        else:
            verified.append(relative.as_posix())

    if artifacts:
        expected_state = json.loads(artifacts[RUN_STATE_PATH])
        state_path = game_repo / RUN_STATE_PATH
        if state_path.is_file():
            state = _load_json(state_path, "Studio run state")
            if state.get("current_baseline") == expected_state["current_baseline"]:
                if state.get("project_id") != expected_state["project_id"]:
                    errors.append("current Studio run state project_id differs from the admission")
                else:
                    verified.append(RUN_STATE_PATH.as_posix())
            else:
                warnings.append("admission is valid historical state but is not the current baseline")
        else:
            errors.append(f"Studio run state is missing: {RUN_STATE_PATH.as_posix()}")

    if errors:
        return BaselineAdmissionResult(
            BLOCKED_BY_ADMISSION_MATERIAL,
            mode=mode,
            errors=errors,
            warnings=warnings,
            verified_paths=sorted(verified),
        )
    return BaselineAdmissionResult(
        BASELINE_ADMISSION_VALID,
        mode=mode,
        warnings=warnings,
        verified_paths=sorted(verified),
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    start = subparsers.add_parser("start")
    start.add_argument("--game-repo", required=True)
    start.add_argument("--reconstruct", action="store_true")
    for command in ("compile", "check"):
        item = subparsers.add_parser(command)
        item.add_argument("--game-repo", required=True)
        item.add_argument("--input", required=True)
    return parser


def _print_result(result: BaselineAdmissionResult) -> None:
    print(result.status)
    if result.mode:
        print(f"MODE: {result.mode}")
    for path in result.created_paths:
        print(f"CREATED: {path}")
    for path in result.verified_paths:
        print(f"VERIFIED: {path}")
    for warning in result.warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    for error in result.errors:
        print(f"ERROR: {error}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "start":
            result = start_baseline_admission(args.game_repo, reconstruct=args.reconstruct)
        elif args.command == "compile":
            result = compile_baseline_admission(args.game_repo, args.input)
        else:
            result = check_baseline_admission(args.game_repo, args.input)
    except BaselineAdmissionError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    _print_result(result)
    return 0 if result.status in {
        BASELINE_RECONSTRUCTION_INPUT_REQUIRED,
        BASELINE_PROMOTION_INPUT_REQUIRED,
        BASELINE_ADMITTED,
        BASELINE_ADMISSION_VALID,
    } else 2


if __name__ == "__main__":
    raise SystemExit(main())
