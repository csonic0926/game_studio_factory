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

try:  # Studio acceptance consumes the exact approved specialist Card surface.
    from gameplay.design_gate import (
        CARD_FACTORY_REVIEW_AUTHORITY_ID,
        decision_payload_sha256,
    )
except ModuleNotFoundError:  # pragma: no cover - direct CLI smoke path.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from gameplay.design_gate import (  # type: ignore[no-redef]
        CARD_FACTORY_REVIEW_AUTHORITY_ID,
        decision_payload_sha256,
    )

try:  # Package import in tests; direct script path below.
    from studio.cycle import (
        READY as STUDIO_GAMEPLAY_SYSTEM_READY,
        CycleValidationError,
        validate_gameplay_system,
    )
except ModuleNotFoundError:  # pragma: no cover - direct CLI smoke path.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from studio.cycle import (  # type: ignore[no-redef]
        READY as STUDIO_GAMEPLAY_SYSTEM_READY,
        CycleValidationError,
        validate_gameplay_system,
    )

try:
    from studio.product import require_active_product_authority
except ModuleNotFoundError:  # pragma: no cover - direct CLI smoke path.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from studio.product import require_active_product_authority  # type: ignore[no-redef]

try:
    from studio.player_surface import (
        validate_interaction_contract,
        validate_interaction_contract_review,
        validate_runtime_player_surface_chain,
    )
except ModuleNotFoundError:  # pragma: no cover - direct CLI smoke path.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from studio.player_surface import (  # type: ignore[no-redef]
        validate_interaction_contract,
        validate_interaction_contract_review,
        validate_runtime_player_surface_chain,
    )

try:
    from studio.alignment import require_registered_card
except ModuleNotFoundError:  # pragma: no cover - direct CLI smoke path.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from studio.alignment import require_registered_card  # type: ignore[no-redef]

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
PRODUCT_DIRECTION_REQUIRED = "PRODUCT_DIRECTION_REQUIRED"

ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
REVISION_PATTERN = re.compile(r"^[0-9a-f]{7,64}$")
SPECIALISTS = {"idea", "gameplay", "story", "asset", "sound", "repo_production"}

ACCEPTANCE_REVIEW_VERSION = "gameplay_acceptance_review.v4"
PREVIOUS_ACCEPTANCE_REVIEW_VERSION = "gameplay_acceptance_review.v3"
OLDER_ACCEPTANCE_REVIEW_VERSION = "gameplay_acceptance_review.v2"
ACCEPTANCE_INPUT_VERSION = "gameplay_acceptance_input.v3"
PREVIOUS_ACCEPTANCE_INPUT_VERSION = "gameplay_acceptance_input.v2"
OLDER_ACCEPTANCE_INPUT_VERSION = "gameplay_acceptance_input.v1"
WORKFLOW_COMPLETION_VERSION = "studio_workflow_completion.v2"
BASELINE_VERSION = "accepted_playable_baseline.v3"
RUN_STATE_VERSION = "studio_run_state.v3"
LEGACY_ACCEPTANCE_REVIEW_VERSION = "gameplay_acceptance_review.v1"
PREVIOUS_BASELINE_VERSION = "accepted_playable_baseline.v2"
PREVIOUS_RUN_STATE_VERSION = "studio_run_state.v2"
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


def human_playtest_payload_sha256(
    *,
    project_id: str,
    unit_id: str,
    game_revision: str,
    build_id: str,
    factory_revision: str,
    experience_authority: dict[str, str],
    acceptance_input: dict[str, str],
    studio_gameplay_system: dict[str, str],
    cycle_id: str,
) -> str:
    """Hash the exact build/authority/cycle tuple on which the user rules."""

    return _sha256_text(_json_text({
        "acceptance_input": acceptance_input,
        "build_id": build_id,
        "cycle_id": cycle_id,
        "experience_authority": experience_authority,
        "factory_revision": factory_revision,
        "game_revision": game_revision,
        "project_id": project_id,
        "studio_gameplay_system": studio_gameplay_system,
        "unit_id": unit_id,
    }))


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


def _load_bound_json(
    game_repo: Path,
    value: Any,
    label: str,
    errors: list[str],
) -> tuple[dict[str, str], dict[str, Any]]:
    ref = _validate_ref(game_repo, value, label, errors)
    if not ref["path"]:
        return ref, {}
    try:
        path = _resolve_persisted_path(game_repo, ref["path"], must_exist=True)
        return ref, _load_json(path, label)
    except BaselineAdmissionError as error:
        errors.append(str(error))
        return ref, {}


def _registered_card_design_context_ids(
    game_repo: Path,
    card_path: Path,
    register_entry: dict[str, Any],
    errors: list[str],
) -> set[str]:
    """Collect contexts that already saw answer-bearing Card/design authority."""

    contexts: set[str] = set()
    _, alignment_input = _load_bound_json(
        game_repo,
        register_entry.get("alignment_input"),
        "registered Card alignment_input",
        errors,
    )
    _, alignment_review = _load_bound_json(
        game_repo,
        register_entry.get("alignment_review"),
        "registered Card alignment_review",
        errors,
    )
    for payload, field in (
        (alignment_input, "author_context_id"),
        (alignment_review, "reviewer_context_id"),
    ):
        value = payload.get(field)
        if isinstance(value, str) and value:
            contexts.add(value)

    authorities = alignment_input.get("active_authorities")
    matching_reviews = [
        item
        for item in authorities
        if isinstance(authorities, list)
        and isinstance(item, dict)
        and item.get("authority_id") == CARD_FACTORY_REVIEW_AUTHORITY_ID
        and item.get("authority_kind") == "REPO_EVIDENCE"
    ] if isinstance(authorities, list) else []
    if len(matching_reviews) != 1:
        errors.append(
            "registered Card alignment input must bind exactly one final Card "
            f"Factory review authority {CARD_FACTORY_REVIEW_AUTHORITY_ID}"
        )
    else:
        review_ref, final_review = _load_bound_json(
            game_repo,
            matching_reviews[0].get("artifact"),
            "registered Card final Factory review",
            errors,
        )
        expected_review_path = card_path.with_name(
            "GAMEPLAY_DECISION_CARD_FACTORY_REVIEW.json"
        ).resolve()
        if review_ref.get("path"):
            try:
                actual_review_path = _resolve_persisted_path(
                    game_repo, review_ref["path"], must_exist=True
                )
            except BaselineAdmissionError:
                actual_review_path = None
            if actual_review_path != expected_review_path:
                errors.append(
                    "registered Card alignment input binds a non-canonical final "
                    "Card Factory review"
                )
        reviewer = final_review.get("reviewer_context_id")
        if isinstance(reviewer, str) and reviewer:
            contexts.add(reviewer)

    objective_path = card_path.with_name("OBJECTIVE_GAMEPLAY.md")
    if objective_path.is_file():
        match = re.search(
            r"^- Author context id:\s*`([^`]+)`\s*$",
            objective_path.read_text(encoding="utf-8"),
            re.MULTILINE,
        )
        if match:
            contexts.add(match.group(1))
    design_verdict_path = card_path.with_name("GAMEPLAY_DESIGN_VERDICT.json")
    if design_verdict_path.is_file():
        try:
            design_verdict = _load_json(design_verdict_path, "gameplay design verdict")
        except BaselineAdmissionError as error:
            errors.append(str(error))
            design_verdict = {}
        review_refs = design_verdict.get("conformance_reviews")
        if isinstance(review_refs, dict):
            for role in ("card_to_spec", "spec_to_card"):
                _, conformance = _load_bound_json(
                    game_repo,
                    review_refs.get(role),
                    f"gameplay design verdict {role} review",
                    errors,
                )
                reviewer = conformance.get("reviewer_context_id")
                if isinstance(reviewer, str) and reviewer:
                    contexts.add(reviewer)
    contexts.discard("")
    return contexts


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


def _validate_current_baseline_payload(
    payload: dict[str, Any],
    label: str,
    errors: list[str],
    *,
    game_repo: Path | None = None,
) -> None:
    schema_version = payload.get("schema_version")
    if schema_version not in {
        "accepted_playable_baseline.v1", PREVIOUS_BASELINE_VERSION, BASELINE_VERSION
    }:
        errors.append(f"{label}.schema_version is unsupported")
    if payload.get("status") != "ACCEPTED_PLAYABLE_BASELINE":
        errors.append(f"{label}.status is not ACCEPTED_PLAYABLE_BASELINE")
    _require_id(payload.get("project_id"), f"{label}.project_id", errors)
    _require_id(payload.get("baseline_id"), f"{label}.baseline_id", errors)
    units = payload.get("accepted_gameplay_units")
    if not isinstance(units, list) or not units:
        errors.append(f"{label}.accepted_gameplay_units must be a non-empty array")
        units = []
    if schema_version in {PREVIOUS_BASELINE_VERSION, BASELINE_VERSION}:
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
            if game_repo is not None:
                _validate_ref(
                    game_repo,
                    unit.get("authority"),
                    f"{label}.accepted_gameplay_units[{index}].authority",
                    errors,
                )
                _validate_ref(
                    game_repo,
                    {"path": review.get("path"), "sha256": review.get("sha256")},
                    f"{label}.accepted_gameplay_units[{index}].acceptance_review",
                    errors,
                )
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
            if schema_version == BASELINE_VERSION:
                cycle_status = review.get("cycle_status")
                if cycle_status not in {
                    "ACCEPTED_TWO_LAP_CYCLE", "PREDECESSOR_CYCLE_UNPROVEN"
                }:
                    errors.append(
                        f"{label}.accepted_gameplay_units[{index}] has no cycle status"
                    )
                if cycle_status == "ACCEPTED_TWO_LAP_CYCLE":
                    cycle_ref = review.get("studio_gameplay_system")
                    if not isinstance(cycle_ref, dict) or not cycle_ref.get("path"):
                        errors.append(
                            f"{label}.accepted_gameplay_units[{index}] lacks its Studio gameplay system"
                        )
                    elif game_repo is not None:
                        _validate_ref(
                            game_repo,
                            cycle_ref,
                            f"{label}.accepted_gameplay_units[{index}].studio_gameplay_system",
                            errors,
                        )
                    if not isinstance(review.get("cycle_id"), str) or not review.get("cycle_id"):
                        errors.append(
                            f"{label}.accepted_gameplay_units[{index}] lacks its cycle_id"
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
    _validate_current_baseline_payload(
        baseline, "current_baseline", errors, game_repo=game_repo
    )
    if state.get("schema_version") not in {
        "studio_run_state.v1", PREVIOUS_RUN_STATE_VERSION, RUN_STATE_VERSION
    }:
        errors.append("Studio run state has unsupported schema_version")
    if state.get("schema_version") in {PREVIOUS_RUN_STATE_VERSION, RUN_STATE_VERSION}:
        if state.get("factory_revision") != baseline.get("factory_revision"):
            errors.append("Studio run state factory_revision does not match current baseline")
        acceptance = state.get("acceptance")
        if not isinstance(acceptance, dict) or acceptance.get("human_playtest_status") != "ACCEPTED":
            errors.append("Studio run state has no accepted human playtest status")
        if (
            state.get("schema_version") == RUN_STATE_VERSION
            and acceptance.get("cycle_status") != "ACCEPTED_TWO_LAP_CYCLE"
        ):
            errors.append("Studio run state has no accepted two-lap cycle status")
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
    product_state, product_errors = require_active_product_authority(game_repo)
    if product_errors:
        return BaselineAdmissionResult(
            PRODUCT_DIRECTION_REQUIRED,
            errors=product_errors,
        )
    try:
        current_ref, current_baseline = _load_current_baseline(game_repo)
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
    active_product = product_state.get("active_authority", {}).get("product_thesis")
    baseline_product = current_baseline.get("product_authority") if current_baseline else None
    if active_product and baseline_product != active_product:
        return BaselineAdmissionResult(
            BASELINE_RECONSTRUCTION_INPUT_REQUIRED,
            mode=RECONSTRUCT,
            warnings=[
                "the current accepted baseline belongs to a different or archived Product "
                "Thesis; it is historical evidence, not the predecessor for this direction"
            ],
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
    product_authority_ref: dict[str, str],
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
    elif schema_version == OLDER_ACCEPTANCE_REVIEW_VERSION:
        if not allow_legacy_historical:
            errors.append(
                f"acceptance review {unit_id} is historical-only; new admission requires "
                f"{ACCEPTANCE_REVIEW_VERSION} with player-facing interaction evidence"
            )
        required = {
            "schema_version", "review_id", "project_id", "unit_id", "game_revision",
            "build_id", "factory_revision", "experience_authority",
            "reviewer_context_id", "reviewer_freshness", "verdict",
            "acceptance_input", "human_playtest", "evidence_paths",
            "observed_complete_loop", "blocking_findings", "reviewed_at",
        }
    elif schema_version == PREVIOUS_ACCEPTANCE_REVIEW_VERSION:
        if not allow_legacy_historical:
            errors.append(
                f"acceptance review {unit_id} is historical-only; new admission requires "
                f"{ACCEPTANCE_REVIEW_VERSION} with player-facing interaction evidence"
            )
        required = {
            "schema_version", "review_id", "project_id", "unit_id", "game_revision",
            "build_id", "factory_revision", "experience_authority",
            "reviewer_context_id", "reviewer_freshness", "verdict",
            "acceptance_input", "human_playtest", "evidence_paths",
            "observed_complete_loop", "observed_two_lap_cycle",
            "blocking_findings", "reviewed_at",
        }
    else:
        required = {
            "schema_version", "review_id", "project_id", "unit_id", "game_revision",
            "build_id", "factory_revision", "experience_authority",
            "reviewer_context_id", "reviewer_freshness", "verdict",
            "acceptance_input", "player_facing_evidence", "human_playtest",
            "evidence_paths", "observed_complete_loop", "observed_two_lap_cycle",
            "blocking_findings", "reviewed_at",
        }
    _require_keys(review, f"acceptance review {unit_id}", required, errors)
    if schema_version not in {
        LEGACY_ACCEPTANCE_REVIEW_VERSION,
        OLDER_ACCEPTANCE_REVIEW_VERSION,
        PREVIOUS_ACCEPTANCE_REVIEW_VERSION,
        ACCEPTANCE_REVIEW_VERSION,
    }:
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
    input_binding: dict[str, Any] = {
        "schema_version": "",
        "studio_gameplay_system": _empty_ref(),
        "cycle_id": "",
        "feedback_state_ids": [],
    }
    bound_factory_revision = factory_revision
    if schema_version in {
        OLDER_ACCEPTANCE_REVIEW_VERSION,
        PREVIOUS_ACCEPTANCE_REVIEW_VERSION,
        ACCEPTANCE_REVIEW_VERSION,
    }:
        recorded_factory_revision = _require_text(
            review.get("factory_revision"),
            f"acceptance review {unit_id}.factory_revision",
            errors,
        )
        if (
            recorded_factory_revision
            and REVISION_PATTERN.fullmatch(recorded_factory_revision) is None
        ):
            errors.append(
                f"acceptance review {unit_id}.factory_revision must be a Git revision"
            )
        historical_version = schema_version in {
            OLDER_ACCEPTANCE_REVIEW_VERSION,
            PREVIOUS_ACCEPTANCE_REVIEW_VERSION,
        }
        if historical_version and allow_legacy_historical:
            bound_factory_revision = recorded_factory_revision
        elif recorded_factory_revision != factory_revision:
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
        input_binding = _validate_gameplay_acceptance_input(
            game_repo,
            review_path=review_path,
            ref=acceptance_input_ref,
            project_id=project_id,
            unit_id=unit_id,
            game_revision=game_revision,
            build_id=build_id,
            factory_revision=bound_factory_revision,
            authority_ref=authority_ref,
            product_authority_ref=product_authority_ref,
            production_context_ids=production_context_ids,
            acceptance_reviewer_context_id=reviewer,
            allow_legacy_historical=allow_legacy_historical,
            errors=errors,
        )
        if (
            schema_version == ACCEPTANCE_REVIEW_VERSION
            and input_binding.get("schema_version") != ACCEPTANCE_INPUT_VERSION
        ):
            errors.append(
                f"acceptance review {unit_id} requires {ACCEPTANCE_INPUT_VERSION}"
            )
        human_required = {"status", "verdict_owner", "verdict_source", "accepted_at"}
        if schema_version in {PREVIOUS_ACCEPTANCE_REVIEW_VERSION, ACCEPTANCE_REVIEW_VERSION}:
            human_required.add("verdict_payload_sha256")
        human = _require_keys(
            review.get("human_playtest"),
            f"acceptance review {unit_id}.human_playtest",
            human_required,
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
        verdict_source = _require_text(
            human.get("verdict_source"),
            f"acceptance review {unit_id}.human_playtest.verdict_source",
            errors,
        )
        if schema_version in {PREVIOUS_ACCEPTANCE_REVIEW_VERSION, ACCEPTANCE_REVIEW_VERSION}:
            expected_payload_sha = human_playtest_payload_sha256(
                project_id=project_id,
                unit_id=unit_id,
                game_revision=game_revision,
                build_id=build_id,
                factory_revision=bound_factory_revision,
                experience_authority=authority_ref,
                acceptance_input=acceptance_input_ref,
                studio_gameplay_system=input_binding.get(
                    "studio_gameplay_system", _empty_ref()
                ),
                cycle_id=str(input_binding.get("cycle_id", "")),
            )
            declared_payload_sha = _require_text(
                human.get("verdict_payload_sha256"),
                f"acceptance review {unit_id}.human_playtest.verdict_payload_sha256",
                errors,
            )
            if declared_payload_sha != expected_payload_sha:
                errors.append(
                    f"acceptance review {unit_id} human verdict payload SHA does not match exact build/authority/cycle"
                )
            if verdict_source != f"HUMAN_PLAYTEST_ACCEPTED {expected_payload_sha}":
                errors.append(
                    f"acceptance review {unit_id} human verdict source must be the exact accepted payload token"
                )
        _require_text(
            human.get("accepted_at"),
            f"acceptance review {unit_id}.human_playtest.accepted_at",
            errors,
        )
        human_playtest_status = str(human.get("status", ""))
        if schema_version == ACCEPTANCE_REVIEW_VERSION:
            review_chain = _require_keys(
                review.get("player_facing_evidence"),
                f"acceptance review {unit_id}.player_facing_evidence",
                {
                    "runtime_interaction_evidence", "blind_observation_input",
                    "blind_observation", "comparison_review",
                },
                errors,
            )
            for key in (
                "runtime_interaction_evidence", "blind_observation_input",
                "blind_observation", "comparison_review",
            ):
                actual = _validate_ref(
                    game_repo,
                    review_chain.get(key),
                    f"acceptance review {unit_id}.player_facing_evidence.{key}",
                    errors,
                )
                if actual != input_binding.get("player_facing_evidence", {}).get(key):
                    errors.append(
                        f"acceptance review {unit_id} player-facing {key} does not "
                        "bind the exact acceptance-input evidence"
                    )
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
    if schema_version in {PREVIOUS_ACCEPTANCE_REVIEW_VERSION, ACCEPTANCE_REVIEW_VERSION}:
        _validate_two_lap_cycle_observation(
            review.get("observed_two_lap_cycle"),
            f"acceptance review {unit_id}.observed_two_lap_cycle",
            set(input_binding.get("feedback_state_ids", [])),
            errors,
        )
    if review.get("blocking_findings") != []:
        errors.append(f"acceptance review {unit_id}.blocking_findings must be empty for ACCEPTED")
    _require_text(review.get("reviewed_at"), f"acceptance review {unit_id}.reviewed_at", errors)
    return {
        **ref,
        "reviewer_freshness": "FRESH",
        "verdict": "ACCEPTED",
        "experience_authority": authority_ref,
        "human_playtest_status": human_playtest_status,
        "studio_gameplay_system": input_binding.get(
            "studio_gameplay_system", _empty_ref()
        ),
        "cycle_id": input_binding.get("cycle_id", ""),
        "cycle_status": (
            "ACCEPTED_TWO_LAP_CYCLE"
            if schema_version in {PREVIOUS_ACCEPTANCE_REVIEW_VERSION, ACCEPTANCE_REVIEW_VERSION}
            else "PREDECESSOR_CYCLE_UNPROVEN"
        ),
        "_review_schema_version": schema_version,
    }


def _validate_two_lap_cycle_observation(
    value: Any,
    label: str,
    expected_feedback_state_ids: set[str],
    errors: list[str],
) -> None:
    payload = _require_keys(
        value,
        label,
        {
            "first_lap", "feedback_state_changes", "second_lap",
            "why_player_has_new_motive",
        },
        errors,
    )
    first = _require_keys(
        payload.get("first_lap"),
        f"{label}.first_lap",
        {"decision", "resolution", "reward"},
        errors,
    )
    for field in ("decision", "resolution", "reward"):
        _require_text(first.get(field), f"{label}.first_lap.{field}", errors)

    raw_changes = payload.get("feedback_state_changes")
    if not isinstance(raw_changes, list) or not raw_changes:
        errors.append(f"{label}.feedback_state_changes must not be empty")
        raw_changes = []
    seen: set[str] = set()
    for index, value in enumerate(raw_changes):
        change = _require_keys(
            value,
            f"{label}.feedback_state_changes[{index}]",
            {"state_id", "before", "after", "effect_on_next_decision"},
            errors,
        )
        state_id = _require_id(
            change.get("state_id"),
            f"{label}.feedback_state_changes[{index}].state_id",
            errors,
        )
        if state_id in seen:
            errors.append(f"{label} repeats feedback state {state_id}")
        seen.add(state_id)
        before = _require_text(
            change.get("before"),
            f"{label}.feedback_state_changes[{index}].before",
            errors,
        )
        after = _require_text(
            change.get("after"),
            f"{label}.feedback_state_changes[{index}].after",
            errors,
        )
        if before and after and before == after:
            errors.append(f"{label} feedback state {state_id} did not change")
        _require_text(
            change.get("effect_on_next_decision"),
            f"{label}.feedback_state_changes[{index}].effect_on_next_decision",
            errors,
        )
    if seen != expected_feedback_state_ids:
        missing = sorted(expected_feedback_state_ids - seen)
        extra = sorted(seen - expected_feedback_state_ids)
        if missing:
            errors.append(f"{label} misses feedback states: " + ", ".join(missing))
        if extra:
            errors.append(f"{label} invents feedback states: " + ", ".join(extra))

    second = _require_keys(
        payload.get("second_lap"),
        f"{label}.second_lap",
        {"changed_goal", "changed_decision", "reentry_action"},
        errors,
    )
    for field in ("changed_goal", "changed_decision", "reentry_action"):
        _require_text(second.get(field), f"{label}.second_lap.{field}", errors)
    _require_text(
        payload.get("why_player_has_new_motive"),
        f"{label}.why_player_has_new_motive",
        errors,
    )


def _validate_acceptance_cycle_manifest(
    game_repo: Path,
    value: Any,
    *,
    project_id: str,
    factory_revision: str,
    product_authority_ref: dict[str, str],
    errors: list[str],
) -> tuple[dict[str, str], str, list[str], set[str]]:
    manifest_ref = _validate_ref(
        game_repo, value, "gameplay acceptance Studio gameplay system", errors
    )
    if not manifest_ref["path"]:
        return manifest_ref, "", [], set()
    try:
        result = validate_gameplay_system(
            str(game_repo),
            manifest_ref["path"],
            expected_factory_revision=factory_revision,
        )
    except CycleValidationError as error:
        errors.append(f"cannot validate acceptance Studio gameplay system: {error}")
        return manifest_ref, "", [], set()
    if result.status != STUDIO_GAMEPLAY_SYSTEM_READY:
        errors.extend(f"acceptance Studio gameplay system: {item}" for item in result.errors)
    if (
        result.manifest_path != manifest_ref["path"]
        or result.manifest_sha256 != manifest_ref["sha256"]
    ):
        errors.append("acceptance does not bind the exact validated Studio gameplay system")

    manifest_path = game_repo / manifest_ref["path"]
    manifest = _load_json(manifest_path, "acceptance Studio gameplay system manifest")
    if manifest.get("project_id") != project_id:
        errors.append("acceptance Studio gameplay system project_id does not match")
    system_ref = _validate_ref(
        game_repo,
        manifest.get("gameplay_system"),
        "acceptance Studio manifest.gameplay_system",
        errors,
    )
    design_context_ids: set[str] = set()
    if system_ref["path"]:
        system = _load_json(
            game_repo / system_ref["path"], "acceptance Studio gameplay system"
        )
        if isinstance(system.get("author_context_id"), str):
            design_context_ids.add(system["author_context_id"])
        if system.get("product_authority") != product_authority_ref:
            errors.append(
                "acceptance Studio gameplay system product authority differs from admission"
            )
    reviews = manifest.get("reviews")
    if isinstance(reviews, dict):
        for key, value in reviews.items():
            review_ref = _validate_ref(
                game_repo,
                value,
                f"acceptance Studio manifest.reviews.{key}",
                errors,
            )
            if review_ref["path"]:
                review = _load_json(
                    game_repo / review_ref["path"],
                    f"acceptance Studio gameplay system {key} review",
                )
                if isinstance(review.get("reviewer_context_id"), str):
                    design_context_ids.add(review["reviewer_context_id"])
    design_context_ids.discard("")
    return (
        manifest_ref,
        result.cycle_id,
        result.feedback_state_ids,
        design_context_ids,
    )


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
    product_authority_ref: dict[str, str],
    production_context_ids: set[str],
    acceptance_reviewer_context_id: str,
    allow_legacy_historical: bool,
    errors: list[str],
) -> dict[str, Any]:
    empty = {
        "schema_version": "",
        "studio_gameplay_system": _empty_ref(),
        "cycle_id": "",
        "feedback_state_ids": [],
        "player_facing_evidence": {},
    }
    if not ref["path"]:
        return empty
    path = game_repo / ref["path"]
    if not path.is_file():
        return empty
    expected_name = f"GAMEPLAY_ACCEPTANCE_INPUT_{unit_id}.json"
    if path.parent != review_path.parent or path.name != expected_name:
        errors.append(
            f"acceptance input for {unit_id} must be admission-local {expected_name}"
        )
    payload = _load_json(path, f"gameplay acceptance input for {unit_id}")
    schema_version = payload.get("schema_version")
    required = {
        "schema_version", "acceptance_input_id", "project_id", "unit_id",
        "game_revision", "build_id", "factory_revision", "experience_authority",
        "expected_player_experience", "playtest_questions", "non_claims", "prepared_at",
    }
    if schema_version in {PREVIOUS_ACCEPTANCE_INPUT_VERSION, ACCEPTANCE_INPUT_VERSION}:
        required |= {"studio_gameplay_system", "cycle_id", "cycle_acceptance"}
    if schema_version == ACCEPTANCE_INPUT_VERSION:
        required |= {
            "decision_card", "player_facing_interaction_contract",
            "player_facing_interaction_contract_review", "player_facing_evidence",
        }
    _require_keys(payload, f"gameplay acceptance input {unit_id}", required, errors)
    if schema_version in {OLDER_ACCEPTANCE_INPUT_VERSION, PREVIOUS_ACCEPTANCE_INPUT_VERSION}:
        if not allow_legacy_historical:
            errors.append(
                f"gameplay acceptance input {unit_id} is historical-only; new admission "
                f"requires {ACCEPTANCE_INPUT_VERSION} with cycle authority"
            )
    elif schema_version != ACCEPTANCE_INPUT_VERSION:
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
    if schema_version not in {PREVIOUS_ACCEPTANCE_INPUT_VERSION, ACCEPTANCE_INPUT_VERSION}:
        return {**empty, "schema_version": str(schema_version or "")}

    manifest_ref, actual_cycle_id, feedback_state_ids, system_context_ids = (
        _validate_acceptance_cycle_manifest(
            game_repo,
            payload.get("studio_gameplay_system"),
            project_id=project_id,
            factory_revision=factory_revision,
            product_authority_ref=product_authority_ref,
            errors=errors,
        )
    )
    cycle_id = _require_id(
        payload.get("cycle_id"),
        f"gameplay acceptance input {unit_id}.cycle_id",
        errors,
    )
    if actual_cycle_id and cycle_id != actual_cycle_id:
        errors.append(
            f"gameplay acceptance input {unit_id}.cycle_id does not match Studio system"
        )
    _validate_two_lap_cycle_observation(
        payload.get("cycle_acceptance"),
        f"gameplay acceptance input {unit_id}.cycle_acceptance",
        set(feedback_state_ids),
        errors,
    )
    player_facing_evidence: dict[str, Any] = {}
    if schema_version == ACCEPTANCE_INPUT_VERSION:
        card_ref = _validate_ref(
            game_repo,
            payload.get("decision_card"),
            f"gameplay acceptance input {unit_id}.decision_card",
            errors,
        )
        contract_ref = _validate_ref(
            game_repo,
            payload.get("player_facing_interaction_contract"),
            f"gameplay acceptance input {unit_id}.player_facing_interaction_contract",
            errors,
        )
        contract_review_ref = _validate_ref(
            game_repo,
            payload.get("player_facing_interaction_contract_review"),
            f"gameplay acceptance input {unit_id}.player_facing_interaction_contract_review",
            errors,
        )
        card_payload = _load_json(game_repo / card_ref["path"], "gameplay decision card") if card_ref["path"] else {}
        if card_payload.get("schema_version") != "gameplay_decision_card.v2":
            errors.append(
                f"gameplay acceptance input {unit_id} requires gameplay_decision_card.v2"
            )
        if card_payload.get("project_id") != project_id or card_payload.get("factory_revision") != factory_revision:
            errors.append(f"gameplay acceptance input {unit_id} decision card identity does not match")
        if card_payload.get("objective_id") != unit_id:
            errors.append(
                f"gameplay acceptance input {unit_id} decision card objective_id "
                "does not match the admitted unit"
            )
        registered_design_context_ids: set[str] = set()
        if card_payload.get("routing") != "STUDIO_WHOLE_GAME":
            errors.append(
                f"gameplay acceptance input {unit_id} requires a Studio whole-game Card"
            )
        else:
            register_entry = require_registered_card(
                game_repo,
                game_repo / card_ref["path"],
                required_state="USER_APPROVED",
                errors=errors,
            )
            if register_entry:
                registered_design_context_ids = _registered_card_design_context_ids(
                    game_repo,
                    game_repo / card_ref["path"],
                    register_entry,
                    errors,
                )
        card_payload_sha = decision_payload_sha256(card_payload)
        if card_payload.get("decision_payload_sha256") != card_payload_sha:
            errors.append(
                f"gameplay acceptance input {unit_id} decision Card payload SHA "
                "does not match its material surface"
            )
        if card_payload.get("human_verdict", {}).get("status") != "USER_APPROVED":
            errors.append(f"gameplay acceptance input {unit_id} decision card must be USER_APPROVED")
        elif card_payload.get("human_verdict", {}).get("source_text") != (
            f"USER_APPROVED {card_payload_sha}"
        ):
            errors.append(
                f"gameplay acceptance input {unit_id} decision Card human verdict "
                "does not bind the exact payload"
            )
        if card_payload.get("player_facing_interaction_contract") != contract_ref:
            errors.append(f"gameplay acceptance input {unit_id} contract differs from the approved Card")
        if card_payload.get("player_facing_interaction_contract_review") != contract_review_ref:
            errors.append(f"gameplay acceptance input {unit_id} contract review differs from the approved Card")
        if card_payload.get("studio_gameplay_system") != manifest_ref:
            errors.append(f"gameplay acceptance input {unit_id} Card binds a different Studio system")
        hypotheses = card_payload.get("validation_hypotheses", [])
        hypothesis_ids: set[str] = set()
        if not isinstance(hypotheses, list):
            errors.append(f"gameplay acceptance input {unit_id} Card hypotheses must be an array")
            hypotheses = []
        for index, item in enumerate(hypotheses):
            if not isinstance(item, dict) or item.get("status") != "TESTABLE_DESIGN":
                errors.append(
                    f"gameplay acceptance input {unit_id} Card hypothesis[{index}] "
                    "must remain TESTABLE_DESIGN until observed"
                )
            elif isinstance(item.get("claim_id"), str):
                hypothesis_ids.add(item["claim_id"])
        transition_ids = [
            str(item).removeprefix("cycle.")
            for item in (
                entry.get("claim_id", "")
                for entry in card_payload.get("core_cycle", [])
                if isinstance(entry, dict)
            )
        ]
        contract_binding = validate_interaction_contract(
            game_repo,
            contract_ref,
            project_id=project_id,
            objective_id=str(card_payload.get("objective_id", "")),
            factory_revision=factory_revision,
            product_authority=product_authority_ref,
            studio_gameplay_system=manifest_ref,
            expected_transition_ids=transition_ids,
            errors=errors,
        )
        if contract_binding.get("payload", {}).get("target_player") != expected.get(
            "target_player"
        ):
            errors.append(
                f"gameplay acceptance input {unit_id} target player differs from "
                "the interaction contract"
            )
        contract_review_binding = validate_interaction_contract_review(
            game_repo,
            contract_review_ref,
            contract=contract_binding,
            product_authority=product_authority_ref,
            studio_gameplay_system=manifest_ref,
            forbidden_context_ids={str(card_payload.get("author_context_id", ""))},
            errors=errors,
        )
        raw_chain = _require_keys(
            payload.get("player_facing_evidence"),
            f"gameplay acceptance input {unit_id}.player_facing_evidence",
            {
                "runtime_interaction_evidence", "blind_observation_input",
                "blind_observation", "comparison_review",
            },
            errors,
        )
        player_facing_evidence = validate_runtime_player_surface_chain(
            game_repo,
            raw_chain,
            project_id=project_id,
            unit_id=unit_id,
            game_revision=game_revision,
            build_id=build_id,
            factory_revision=factory_revision,
            expected_contract_ref=contract_ref,
            expected_contract_review_ref=contract_review_ref,
            expected_card_ref=card_ref,
            expected_system_ref=manifest_ref,
            expected_beat_ids=set(contract_binding.get("beat_ids", set())),
            expected_answer_bearing_design_ids=set(
                contract_binding.get("answer_bearing_design_ids", set())
            ),
            expected_target_locale=str(contract_binding.get("target_locale", "")),
            expected_player_entry_knowledge=list(
                contract_binding.get("player_entry_knowledge", [])
            ),
            hypothesis_ids=hypothesis_ids,
            design_context_ids={
                str(card_payload.get("author_context_id", "")),
                str(contract_binding.get("author_context_id", "")),
                str(contract_review_binding.get("reviewer_context_id", "")),
                *system_context_ids,
                *registered_design_context_ids,
            } - {""},
            production_context_ids=production_context_ids,
            acceptance_reviewer_context_id=acceptance_reviewer_context_id,
            errors=errors,
        )
    return {
        "schema_version": schema_version,
        "studio_gameplay_system": manifest_ref,
        "cycle_id": cycle_id,
        "feedback_state_ids": feedback_state_ids,
        "player_facing_evidence": {
            key: player_facing_evidence.get(key, {})
            for key in (
                "runtime_interaction_evidence", "blind_observation_input",
                "blind_observation", "comparison_review",
            )
        },
    }


def _validate_unit(
    game_repo: Path,
    value: Any,
    index: int,
    *,
    project_id: str,
    game_revision: str,
    build_id: str,
    product_authority_ref: dict[str, str],
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
        product_authority_ref=product_authority_ref,
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
    review = unit.get("acceptance_review", {})
    clean_review = {
        key: review.get(key, "")
        for key in (
            "path", "sha256", "reviewer_freshness", "verdict",
            "experience_authority", "human_playtest_status",
        )
    }
    clean_review["experience_authority"] = review.get(
        "experience_authority", unit.get("authority", _empty_ref())
    )
    clean_review["human_playtest_status"] = review.get(
        "human_playtest_status", "LEGACY_ACCEPTANCE_GRANDFATHERED"
    )
    return {**unit, "acceptance_review": clean_review}


def _v3_unit_shape(unit: dict[str, Any]) -> dict[str, Any]:
    review = unit.get("acceptance_review", {})
    cycle_status = review.get("cycle_status", "PREDECESSOR_CYCLE_UNPROVEN")
    clean_review = {
        key: review.get(key, "")
        for key in (
            "path", "sha256", "reviewer_freshness", "verdict",
            "experience_authority", "human_playtest_status",
        )
    }
    clean_review["experience_authority"] = review.get(
        "experience_authority", unit.get("authority", _empty_ref())
    )
    clean_review["human_playtest_status"] = review.get(
        "human_playtest_status", "LEGACY_ACCEPTANCE_GRANDFATHERED"
    )
    clean_review["studio_gameplay_system"] = review.get(
        "studio_gameplay_system", _empty_ref()
    )
    clean_review["cycle_id"] = review.get("cycle_id", "")
    clean_review["cycle_status"] = cycle_status
    return {**unit, "acceptance_review": clean_review}


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
            _validate_current_baseline_payload(
                predecessor, "predecessor_baseline", errors, game_repo=game_repo
            )

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
            product_authority_ref=product_authority,
            factory_revision=factory_revision,
            production_context_ids=production_context_ids,
            allow_legacy_historical=allow_legacy_historical,
            errors=errors,
        )
        for index, item in enumerate(raw_units)
    ]
    admitted_ids = [unit["unit_id"] for unit in admitted]
    admitted_review_versions = {
        unit.get("acceptance_review", {}).get("_review_schema_version", "")
        for unit in admitted
    }
    legacy_admission_material = LEGACY_ACCEPTANCE_REVIEW_VERSION in admitted_review_versions
    previous_admission_material = (
        OLDER_ACCEPTANCE_REVIEW_VERSION in admitted_review_versions
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
    previous_output = (
        allow_legacy_historical
        and not legacy_output
        and previous_admission_material
    )
    if legacy_output:
        accepted_units = [
            _legacy_unit_shape(unit) for unit in _merge_units(predecessor, admitted)
        ]
        output_baseline_version = "accepted_playable_baseline.v1"
        output_state_version = "studio_run_state.v1"
    elif previous_output:
        accepted_units = [
            _v2_unit_shape(unit) for unit in _merge_units(predecessor, admitted)
        ]
        output_baseline_version = PREVIOUS_BASELINE_VERSION
        output_state_version = PREVIOUS_RUN_STATE_VERSION
    else:
        accepted_units = [
            _v3_unit_shape(unit) for unit in _merge_units(predecessor, admitted)
        ]
        output_baseline_version = BASELINE_VERSION
        output_state_version = RUN_STATE_VERSION
    known_gaps = _merge_gaps(predecessor, gaps, resolved_gap_ids)
    baseline_relative = BASELINES_ROOT / baseline_id / "ACCEPTED_PLAYABLE_BASELINE.json"
    baseline_payload = {
        "schema_version": output_baseline_version,
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
    if output_baseline_version != "accepted_playable_baseline.v1":
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
        "schema_version": output_state_version,
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
    if output_state_version != "studio_run_state.v1":
        state_payload["factory_revision"] = factory_revision
        state_payload["acceptance"]["human_playtest_status"] = "ACCEPTED"
    if output_state_version == RUN_STATE_VERSION:
        state_payload["acceptance"]["cycle_status"] = "ACCEPTED_TWO_LAP_CYCLE"
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


def compute_playtest_token(game_repo_text: str, review_text: str) -> str:
    """Compute the exact non-circular human playtest verdict token."""

    game_repo = _resolve_game_repo(game_repo_text)
    review_path = _resolve_cli_path(game_repo, review_text, must_exist=True)
    if not review_path.is_file():
        raise BaselineAdmissionError(f"acceptance review is not a file: {review_text}")
    review = _load_json(review_path, "gameplay acceptance review")
    errors: list[str] = []
    authority = _validate_ref(
        game_repo, review.get("experience_authority"), "experience_authority", errors
    )
    acceptance_input_ref = _validate_ref(
        game_repo, review.get("acceptance_input"), "acceptance_input", errors
    )
    acceptance_input: dict[str, Any] = {}
    if acceptance_input_ref["path"]:
        acceptance_input = _load_json(
            game_repo / acceptance_input_ref["path"], "gameplay acceptance input"
        )
    system_ref = _validate_ref(
        game_repo,
        acceptance_input.get("studio_gameplay_system"),
        "studio_gameplay_system",
        errors,
    )
    values = {
        field: _require_text(review.get(field), field, errors)
        for field in (
            "project_id", "unit_id", "game_revision", "build_id", "factory_revision"
        )
    }
    cycle_id = _require_text(acceptance_input.get("cycle_id"), "cycle_id", errors)
    if errors:
        raise BaselineAdmissionError("; ".join(errors))
    digest = human_playtest_payload_sha256(
        project_id=values["project_id"],
        unit_id=values["unit_id"],
        game_revision=values["game_revision"],
        build_id=values["build_id"],
        factory_revision=values["factory_revision"],
        experience_authority=authority,
        acceptance_input=acceptance_input_ref,
        studio_gameplay_system=system_ref,
        cycle_id=cycle_id,
    )
    return f"HUMAN_PLAYTEST_ACCEPTED {digest}"


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
    token = subparsers.add_parser("playtest-token")
    token.add_argument("--game-repo", required=True)
    token.add_argument("--review", required=True)
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
        elif args.command == "playtest-token":
            print(compute_playtest_token(args.game_repo, args.review))
            return 0
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
