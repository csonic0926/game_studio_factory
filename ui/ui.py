#!/usr/bin/env python3
"""Compile a game-owned UI Production Adapter before UI-changing plans.

``start`` writes a bounded non-semantic inventory of likely UI construction
files.  One evidence-focused investigator then fills the canonical input.
``compile`` validates exact repository evidence and emits the reusable adapter;
``check`` proves that the adapter is current; explicit ``refresh`` replaces a
previously checked adapter after its cited convention sources change. The workflow reconstructs how
this repository owns layout, state, scene integration, input/layers,
responsive composition, localization fit, visual grammar, and separate
structural/visual UI validation.  It does not redesign the feature or infer
repository conventions from filenames alone.
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
from typing import Any, Iterable


PROBE_SCHEMA_VERSION = "ui_production_repo_probe.v1"
INPUT_SCHEMA_VERSION = "ui_production_adapter_input.v2"
ADAPTER_SCHEMA_VERSION = "ui_production_adapter.v2"
RESULT_SCHEMA_VERSION = "ui_production_adapter_result.v2"
PREVIOUS_RESULT_SCHEMA_VERSIONS = {"ui_production_adapter_result.v1"}

UI_PRODUCTION_ADAPTER_INPUT_REQUIRED = "UI_PRODUCTION_ADAPTER_INPUT_REQUIRED"
UI_PRODUCTION_ADAPTER_READY = "UI_PRODUCTION_ADAPTER_READY"
UI_PRODUCTION_ADAPTER_ALREADY_READY = "UI_PRODUCTION_ADAPTER_ALREADY_READY"
BLOCKED_BY_UI_MODEL = "BLOCKED_BY_UI_MODEL"
BLOCKED_BY_EXISTING_UI_STATE = "BLOCKED_BY_EXISTING_UI_STATE"

FACTORY_ROOT = Path(__file__).resolve().parent.parent
UI_ROOT_RELATIVE = Path("design/gameplay/ui")
PROBE_RELATIVE = UI_ROOT_RELATIVE / "PROJECT_UI_REPO_PROBE.json"
INPUT_RELATIVE = UI_ROOT_RELATIVE / "UI_PRODUCTION_ADAPTER_INPUT.json"
ADAPTER_JSON_RELATIVE = Path(
    "design/gameplay/adapter/UI_PRODUCTION_ADAPTER.json"
)
ADAPTER_MD_RELATIVE = Path("design/gameplay/adapter/UI_PRODUCTION_ADAPTER.md")
RESULT_RELATIVE = UI_ROOT_RELATIVE / "UI_PRODUCTION_ADAPTER_RESULT.json"
CANONICAL_OUTPUTS = (
    ADAPTER_JSON_RELATIVE,
    ADAPTER_MD_RELATIVE,
    RESULT_RELATIVE,
)

IGNORED_DIRECTORIES = {
    ".git",
    ".godot",
    ".cache",
    "node_modules",
    "vendor",
    "build",
    "dist",
    "coverage",
}
UI_EXTENSIONS = {
    ".gd",
    ".tscn",
    ".tres",
    ".cs",
    ".unity",
    ".prefab",
    ".uxml",
    ".uss",
    ".qml",
    ".ui",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".html",
    ".css",
    ".scss",
    ".json",
    ".csv",
    ".po",
    ".md",
}
UI_TERMS = (
    "ui",
    "hud",
    "menu",
    "screen",
    "dialog",
    "modal",
    "overlay",
    "panel",
    "widget",
    "control",
    "layout",
    "viewport",
    "locale",
    "localization",
    "i18n",
    "theme",
    "scene",
    "title",
    "shop",
    "battle",
)
PROJECT_MARKERS = (
    "project.godot",
    "ProjectSettings/ProjectVersion.txt",
    "package.json",
    "Cargo.toml",
    "CMakeLists.txt",
)
REQUIRED_RULE_CATEGORIES = {
    "LAYOUT_STRUCTURE",
    "STATE_OWNERSHIP",
    "SCENE_INTEGRATION",
    "INPUT_AND_LAYERING",
    "RESPONSIVE_COMPOSITION",
    "LOCALIZATION_FIT",
    "VISUAL_GRAMMAR",
    "VALIDATION",
}
PROJECT_BOUND_RULE_CATEGORIES = {
    "LAYOUT_STRUCTURE",
    "STATE_OWNERSHIP",
    "SCENE_INTEGRATION",
    "INPUT_AND_LAYERING",
    "VISUAL_GRAMMAR",
}
RULE_AUTHORITIES = {"REPO_EVIDENCE", "USER_RULING", "FACTORY_INVARIANT"}
EXEMPLAR_AUTHORITIES = {"ACCEPTED_BASELINE", "USER_RULING"}
VALIDATION_KINDS = {"STRUCTURAL_FIT", "VISUAL_CONSISTENCY"}
COMPARISON_METHODS = {
    "GEOMETRY_ASSERTION",
    "STATE_ASSERTION",
    "SCENE_ASSERTION",
    "INTERACTION_TRACE",
    "RESOURCE_IDENTITY",
    "RESOURCE_PROPERTY_EQUALITY",
    "COMPUTED_STYLE_EQUALITY",
    "SCREENSHOT_REVIEW",
}
STRUCTURAL_COMPARISON_METHODS = {
    "GEOMETRY_ASSERTION",
    "STATE_ASSERTION",
    "SCENE_ASSERTION",
    "INTERACTION_TRACE",
}
MECHANICAL_VISUAL_COMPARISON_METHODS = {
    "RESOURCE_IDENTITY",
    "RESOURCE_PROPERTY_EQUALITY",
    "COMPUTED_STYLE_EQUALITY",
}
GODOT_VISUAL_COMPARISON_METHODS = {
    "RESOURCE_IDENTITY",
    "RESOURCE_PROPERTY_EQUALITY",
}
VISUAL_GRAMMAR_POLICY = {
    "default_without_explicit_redesign": "PRESERVE_EXISTING_VISUAL_GRAMMAR",
    "redesign_requires": "USER_RULING",
}


class UiWorkflowError(ValueError):
    """Raised before an illegal path or repository can be written."""


@dataclass
class UiWorkflowResult:
    status: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    created_paths: list[str] = field(default_factory=list)
    updated_paths: list[str] = field(default_factory=list)
    verified_paths: list[str] = field(default_factory=list)


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _run_git(game_repo: Path, *args: str, binary: bool = False) -> str | bytes:
    result = subprocess.run(
        ["git", "-C", str(game_repo), *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=not binary,
        encoding=None if binary else "utf-8",
    )
    if result.returncode != 0:
        stderr = result.stderr
        detail = (
            stderr.decode("utf-8", errors="replace")
            if isinstance(stderr, bytes)
            else stderr
        ).strip()
        raise UiWorkflowError(f"git {' '.join(args)} failed: {detail}")
    return result.stdout


def _resolve_game_repo(raw_path: str) -> Path:
    game_repo = Path(raw_path).expanduser().resolve()
    if not game_repo.is_dir():
        raise UiWorkflowError(f"game repo does not exist: {game_repo}")
    if game_repo == FACTORY_ROOT or _is_within(game_repo, FACTORY_ROOT):
        raise UiWorkflowError("game repo must not be this factory repo or a child")
    try:
        git_root = str(_run_git(game_repo, "rev-parse", "--show-toplevel")).strip()
    except UiWorkflowError as error:
        raise UiWorkflowError("UI workflow requires an existing Git repository") from error
    if Path(git_root).resolve() != game_repo:
        raise UiWorkflowError(f"game repo must be the Git root, not a child: {game_repo}")
    return game_repo


def _resolve_cli_path(
    game_repo: Path, raw_path: str, *, must_exist: bool = False
) -> Path:
    candidate = Path(raw_path).expanduser()
    resolved = (candidate if candidate.is_absolute() else game_repo / candidate).resolve()
    if not _is_within(resolved, game_repo):
        raise UiWorkflowError(f"path escapes game repo: {raw_path}")
    if must_exist and not resolved.exists():
        raise UiWorkflowError(f"required path does not exist: {raw_path}")
    return resolved


def _resolve_persisted_path(
    game_repo: Path, raw_path: Any, *, must_exist: bool = False
) -> Path:
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise UiWorkflowError("persisted paths must be non-empty strings")
    if Path(raw_path).expanduser().is_absolute():
        raise UiWorkflowError(f"persisted path must be game-repo-relative: {raw_path}")
    return _resolve_cli_path(game_repo, raw_path, must_exist=must_exist)


def _json_text(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_text(value: str) -> str:
    return _sha256_bytes(value.encode("utf-8"))


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise UiWorkflowError(f"cannot read {label}: {error}") from error
    if not isinstance(value, dict):
        raise UiWorkflowError(f"{label} must contain a JSON object")
    return value


def _generated_path(relative: str) -> bool:
    path = Path(relative)
    return (
        path == ADAPTER_JSON_RELATIVE
        or path == ADAPTER_MD_RELATIVE
        or path == RESULT_RELATIVE
        or _is_within(path, UI_ROOT_RELATIVE)
    )


def _repo_files(game_repo: Path) -> list[str]:
    raw = str(
        _run_git(
            game_repo,
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "-z",
        )
    )
    result: list[str] = []
    for relative in raw.split("\0"):
        if not relative or _generated_path(relative):
            continue
        if any(part in IGNORED_DIRECTORIES for part in Path(relative).parts):
            continue
        path = (game_repo / relative).resolve()
        if _is_within(path, game_repo) and path.is_file():
            result.append(relative)
    return sorted(set(result))


def _changed_paths(game_repo: Path) -> list[str]:
    tracked = bytes(
        _run_git(game_repo, "diff", "--name-only", "-z", "HEAD", "--", binary=True)
    ).split(b"\0")
    untracked = bytes(
        _run_git(
            game_repo,
            "ls-files",
            "--others",
            "--exclude-standard",
            "-z",
            binary=True,
        )
    ).split(b"\0")
    values = {
        raw.decode("utf-8", errors="surrogateescape")
        for raw in (*tracked, *untracked)
        if raw
    }
    return sorted(path for path in values if not _generated_path(path))


def _working_tree_sha256(game_repo: Path, paths: Iterable[str]) -> str:
    digest = hashlib.sha256()
    for relative in sorted(paths):
        digest.update(relative.encode("utf-8", errors="surrogateescape"))
        digest.update(b"\0")
        path = game_repo / relative
        if path.is_symlink():
            digest.update(b"symlink\0")
            digest.update(path.readlink().as_posix().encode("utf-8"))
        elif path.is_file():
            digest.update(b"file\0")
            digest.update(hashlib.sha256(path.read_bytes()).digest())
        elif not path.exists():
            digest.update(b"missing\0")
        else:
            digest.update(b"other\0")
        digest.update(b"\0")
    return digest.hexdigest()


def _repository_binding(game_repo: Path) -> dict[str, Any]:
    dirty_paths = _changed_paths(game_repo)
    return {
        "revision": str(_run_git(game_repo, "rev-parse", "HEAD")).strip(),
        "dirty_paths": dirty_paths,
        "working_tree_sha256": _working_tree_sha256(game_repo, dirty_paths),
    }


def _candidate_score(relative: str) -> int:
    lower = relative.lower()
    score = sum(2 for term in UI_TERMS if term in lower)
    suffix = Path(relative).suffix.lower()
    if suffix in {".tscn", ".uxml", ".uss", ".ui", ".qml", ".prefab"}:
        score += 6
    elif suffix in {".gd", ".cs", ".ts", ".tsx", ".js", ".jsx"}:
        score += 2
    if any(part.lower() in {"ui", "scenes", "screens", "locales"} for part in Path(relative).parts):
        score += 3
    return score


def _write_exact_or_replace(path: Path, text: str) -> bool:
    if path.is_file() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def probe_repository(
    game_repo_text: str,
    output_text: str = PROBE_RELATIVE.as_posix(),
    *,
    max_candidates: int = 200,
) -> UiWorkflowResult:
    """Write a bounded file inventory without assigning UI semantics."""

    # Resolve all ownership and argument constraints before mkdir/write.
    game_repo = _resolve_game_repo(game_repo_text)
    output = _resolve_cli_path(game_repo, output_text)
    if output != (game_repo / PROBE_RELATIVE).resolve():
        raise UiWorkflowError(f"probe output must be {PROBE_RELATIVE.as_posix()}")
    if max_candidates < 1 or max_candidates > 1000:
        raise UiWorkflowError("max_candidates must be between 1 and 1000")

    files = _repo_files(game_repo)
    scored = [
        (_candidate_score(relative), relative)
        for relative in files
        if Path(relative).suffix.lower() in UI_EXTENSIONS
    ]
    scored = [item for item in scored if item[0] > 0]
    scored.sort(key=lambda item: (-item[0], item[1]))
    binding = _repository_binding(game_repo)
    payload = {
        "schema_version": PROBE_SCHEMA_VERSION,
        "repository_binding": binding,
        "project_markers": [
            marker for marker in PROJECT_MARKERS if (game_repo / marker).is_file()
        ],
        "candidate_files": [
            {"path": relative, "score": score}
            for score, relative in scored[:max_candidates]
        ],
        "candidate_count": min(len(scored), max_candidates),
        "truncated": len(scored) > max_candidates,
        "semantic_authority": "NONE",
        "next_input": INPUT_RELATIVE.as_posix(),
    }
    changed = _write_exact_or_replace(output, _json_text(payload))
    return UiWorkflowResult(
        UI_PRODUCTION_ADAPTER_INPUT_REQUIRED,
        created_paths=[PROBE_RELATIVE.as_posix()] if changed else [],
        verified_paths=[] if changed else [PROBE_RELATIVE.as_posix()],
        warnings=[
            "Candidate scores are navigation hints only. One bounded investigator "
            "must inspect successful existing surfaces, their state/refresh paths, "
            "and known UI failure evidence before compiling the adapter."
        ],
    )


def _adapter_complete(game_repo: Path) -> bool:
    return all((game_repo / relative).is_file() for relative in CANONICAL_OUTPUTS)


def _adapter_generation_is_current(game_repo: Path) -> bool:
    """Return whether an existing generation implements the current contract."""

    try:
        adapter = _load_json(
            game_repo / ADAPTER_JSON_RELATIVE, "UI Production Adapter"
        )
        result = _load_json(
            game_repo / RESULT_RELATIVE, "UI Production Adapter result"
        )
    except UiWorkflowError:
        return False
    return (
        adapter.get("schema_version") == ADAPTER_SCHEMA_VERSION
        and result.get("schema_version") == RESULT_SCHEMA_VERSION
    )


def start_ui_workflow(game_repo_text: str) -> UiWorkflowResult:
    game_repo = _resolve_game_repo(game_repo_text)
    if _adapter_complete(game_repo):
        if not _adapter_generation_is_current(game_repo):
            result = probe_repository(game_repo_text)
            result.warnings.append(
                "The existing UI adapter predates visual-grammar provenance, "
                "style-blast-radius planning, or split structural/visual validation. "
                "Reconstruct v2 input and use the explicit refresh command."
            )
            return result
        checked = check_ui_adapter(game_repo_text, INPUT_RELATIVE.as_posix())
        if checked.status == UI_PRODUCTION_ADAPTER_READY:
            checked.status = UI_PRODUCTION_ADAPTER_ALREADY_READY
        return checked
    return probe_repository(game_repo_text)


def _contains_placeholder(value: Any) -> bool:
    if isinstance(value, str):
        upper = value.upper()
        return "TBD" in upper or bool(re.search(r"<[^<>]+>", value))
    if isinstance(value, list):
        return any(_contains_placeholder(item) for item in value)
    if isinstance(value, dict):
        return any(_contains_placeholder(item) for item in value.values())
    return False


def _text(value: Any, label: str, errors: list[str], *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        errors.append(f"{label} must be {'a string' if allow_empty else 'a non-empty string'}")
        return ""
    if _contains_placeholder(value):
        errors.append(f"{label} must not contain placeholders")
    return value.strip()


def _list(value: Any, label: str, errors: list[str], *, allow_empty: bool = False) -> list[Any]:
    if not isinstance(value, list):
        errors.append(f"{label} must be an array")
        return []
    if not allow_empty and not value:
        errors.append(f"{label} must contain at least one item")
    return value


def _exact_fields(
    value: dict[str, Any], allowed: set[str], label: str, errors: list[str]
) -> None:
    missing = sorted(allowed - set(value))
    extra = sorted(set(value) - allowed)
    if missing:
        errors.append(f"{label} lacks required fields: " + ", ".join(missing))
    if extra:
        errors.append(f"{label} has unsupported fields: " + ", ".join(extra))


def _string_list(value: Any, label: str, errors: list[str], *, allow_empty: bool = False) -> list[str]:
    values = _list(value, label, errors, allow_empty=allow_empty)
    result = [_text(item, f"{label}[{index}]", errors) for index, item in enumerate(values)]
    result = [item for item in result if item]
    if len(result) != len(set(result)):
        errors.append(f"{label} must not contain duplicates")
    return result


def _portable_id(value: Any, label: str, errors: list[str]) -> str:
    result = _text(value, label, errors)
    if result and not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", result):
        errors.append(f"{label} must be a portable lowercase id")
    return result


def _validate_evidence_refs(
    game_repo: Path,
    value: Any,
    label: str,
    errors: list[str],
    *,
    allow_empty: bool = False,
) -> list[dict[str, Any]]:
    refs = _list(value, label, errors, allow_empty=allow_empty)
    normalized: list[dict[str, Any]] = []
    for index, ref in enumerate(refs):
        ref_label = f"{label}[{index}]"
        if not isinstance(ref, dict):
            errors.append(f"{ref_label} must be an object")
            continue
        if set(ref) != {"role", "path", "contains"}:
            errors.append(f"{ref_label} must contain only role, path, and contains")
        role = _text(ref.get("role"), f"{ref_label}.role", errors)
        path_text = _text(ref.get("path"), f"{ref_label}.path", errors)
        contains = _string_list(ref.get("contains"), f"{ref_label}.contains", errors)
        if not path_text:
            continue
        try:
            path = _resolve_persisted_path(game_repo, path_text, must_exist=True)
        except UiWorkflowError as error:
            errors.append(str(error))
            continue
        if not path.is_file():
            errors.append(f"{ref_label}.path is not a file: {path_text}")
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(f"{ref_label}.path is not UTF-8 text: {path_text}")
            continue
        for token in contains:
            if token not in source:
                errors.append(f"evidence token not found in {path_text}: {token}")
        normalized.append(
            {
                "role": role,
                "path": path_text,
                "contains": contains,
                "source_sha256": _sha256_bytes(path.read_bytes()),
            }
        )
    return normalized


def _git_file_at_revision(
    game_repo: Path,
    revision: str,
    path_text: str,
) -> bytes | None:
    result = subprocess.run(
        ["git", "-C", str(game_repo), "show", f"{revision}:{path_text}"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout if result.returncode == 0 else None


def _validate_exemplar_provenance(
    game_repo: Path,
    value: Any,
    evidence_refs: list[dict[str, Any]],
    project_id: str,
    label: str,
    errors: list[str],
) -> dict[str, str]:
    """Prove an exemplar predates the target work or was explicitly accepted.

    A Studio accepted baseline is executable provenance rather than a filename
    claim: the compiler verifies the baseline payload and proves that every
    cited exemplar byte already existed unchanged at its accepted game
    revision. A USER_RULING is the only way to authorize another source.
    """

    empty = {
        "authority": "",
        "accepted_baseline_path": "",
        "accepted_baseline_sha256": "",
        "accepted_game_revision": "",
        "user_quote": "",
    }
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object")
        return empty
    _exact_fields(
        value,
        {"authority", "accepted_baseline_path", "user_quote"},
        label,
        errors,
    )
    authority = _text(value.get("authority"), f"{label}.authority", errors)
    baseline_path_text = _text(
        value.get("accepted_baseline_path", ""),
        f"{label}.accepted_baseline_path",
        errors,
        allow_empty=True,
    )
    user_quote = _text(
        value.get("user_quote", ""),
        f"{label}.user_quote",
        errors,
        allow_empty=True,
    )
    if authority not in EXEMPLAR_AUTHORITIES:
        errors.append(f"{label}.authority has an unsupported value")
        return {**empty, "authority": authority}
    if authority == "USER_RULING":
        if baseline_path_text:
            errors.append(
                f"{label}.accepted_baseline_path must be empty for USER_RULING"
            )
        if not user_quote:
            errors.append(f"{label}.user_quote is required for USER_RULING")
        return {
            **empty,
            "authority": authority,
            "user_quote": user_quote,
        }

    if user_quote:
        errors.append(f"{label}.user_quote must be empty for ACCEPTED_BASELINE")
    if not baseline_path_text:
        errors.append(
            f"{label}.accepted_baseline_path is required for ACCEPTED_BASELINE"
        )
        return {**empty, "authority": authority}
    if not re.fullmatch(
        r"design/studio/baselines/[a-z0-9][a-z0-9._-]*/"
        r"ACCEPTED_PLAYABLE_BASELINE\.json",
        baseline_path_text,
    ):
        errors.append(
            f"{label}.accepted_baseline_path must name a canonical Studio "
            "ACCEPTED_PLAYABLE_BASELINE.json"
        )
    try:
        baseline_path = _resolve_persisted_path(
            game_repo, baseline_path_text, must_exist=True
        )
        baseline_bytes = baseline_path.read_bytes()
        baseline = json.loads(baseline_bytes.decode("utf-8"))
    except (UiWorkflowError, OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        errors.append(f"cannot validate {label} accepted baseline: {error}")
        return {
            **empty,
            "authority": authority,
            "accepted_baseline_path": baseline_path_text,
        }
    if not isinstance(baseline, dict):
        errors.append(f"{label} accepted baseline must contain an object")
        return {
            **empty,
            "authority": authority,
            "accepted_baseline_path": baseline_path_text,
            "accepted_baseline_sha256": _sha256_bytes(baseline_bytes),
        }
    if baseline.get("schema_version") not in {
        "accepted_playable_baseline.v1",
        "accepted_playable_baseline.v2",
        "accepted_playable_baseline.v3",
    }:
        errors.append(f"{label} accepted baseline has an unsupported schema")
    if baseline.get("status") != "ACCEPTED_PLAYABLE_BASELINE":
        errors.append(f"{label} source is not an ACCEPTED_PLAYABLE_BASELINE")
    if baseline.get("project_id") != project_id:
        errors.append(f"{label} accepted baseline belongs to another project")
    accepted_units = baseline.get("accepted_gameplay_units")
    if not isinstance(accepted_units, list) or not accepted_units:
        errors.append(f"{label} accepted baseline has no accepted gameplay units")
    promotion = baseline.get("promotion")
    if not isinstance(promotion, dict) or promotion.get("acceptance_owner") != "USER":
        errors.append(f"{label} accepted baseline has no user-owned promotion")
    eligibility = baseline.get("delivery_eligibility")
    if (
        not isinstance(eligibility, dict)
        or eligibility.get("interactive_demo_only") is not False
        or eligibility.get("minimum_gameplay_passed") is not True
        or eligibility.get("blocking_gap_ids") != []
    ):
        errors.append(f"{label} accepted baseline is not delivery eligible")
    revision = baseline.get("game_revision")
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{7,64}", revision):
        errors.append(f"{label} accepted baseline has no valid game_revision")
        revision = ""
    if revision:
        for ref in evidence_refs:
            path_text = ref.get("path", "")
            accepted_bytes = _git_file_at_revision(game_repo, revision, path_text)
            if accepted_bytes is None:
                errors.append(
                    f"{label} exemplar evidence did not exist in accepted baseline "
                    f"revision {revision}: {path_text}"
                )
                continue
            if _sha256_bytes(accepted_bytes) != ref.get("source_sha256"):
                errors.append(
                    f"{label} exemplar evidence changed after accepted baseline; "
                    f"it cannot certify current visual grammar: {path_text}"
                )
    return {
        "authority": authority,
        "accepted_baseline_path": baseline_path_text,
        "accepted_baseline_sha256": _sha256_bytes(baseline_bytes),
        "accepted_game_revision": revision,
        "user_quote": "",
    }


def _validate_repo_binding(
    game_repo: Path,
    probe: dict[str, Any],
    supplied: Any,
    errors: list[str],
    *,
    require_current: bool,
) -> dict[str, Any]:
    probe_binding = probe.get("repository_binding")
    if not isinstance(probe_binding, dict):
        errors.append("probe.repository_binding must be an object")
        return {}
    if not isinstance(supplied, dict):
        errors.append("repository_binding must be an object")
        return {}
    if supplied != probe_binding:
        errors.append("repository_binding does not exactly match the repo probe")
    if require_current:
        current = _repository_binding(game_repo)
        if current != probe_binding:
            errors.append("repository changed after the UI repo probe; rerun start")
    return probe_binding


def _normalize_input(
    game_repo: Path,
    payload: dict[str, Any],
    *,
    require_current_repo_binding: bool,
) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    _exact_fields(
        payload,
        {
            "schema_version",
            "project_id",
            "probe_path",
            "probe_sha256",
            "repository_binding",
            "surfaces",
            "canonical_exemplars",
            "rules",
            "viewport_profiles",
            "localization_profiles",
            "validation_scenarios",
            "anti_patterns",
            "unresolved_material_gaps",
            "ai_assumptions",
        },
        "UI adapter input",
        errors,
    )
    if payload.get("schema_version") != INPUT_SCHEMA_VERSION:
        errors.append(f"schema_version must be {INPUT_SCHEMA_VERSION}")
    project_id = _portable_id(payload.get("project_id"), "project_id", errors)
    probe_path_text = _text(payload.get("probe_path"), "probe_path", errors)
    probe_sha = _text(payload.get("probe_sha256"), "probe_sha256", errors)
    probe: dict[str, Any] = {}
    if probe_path_text:
        if probe_path_text != PROBE_RELATIVE.as_posix():
            errors.append(f"probe_path must be {PROBE_RELATIVE.as_posix()}")
        try:
            probe_path = _resolve_persisted_path(game_repo, probe_path_text, must_exist=True)
            probe_bytes = probe_path.read_bytes()
            if probe_sha != _sha256_bytes(probe_bytes):
                errors.append("probe_sha256 does not match the repo probe")
            probe = json.loads(probe_bytes.decode("utf-8"))
            if not isinstance(probe, dict) or probe.get("schema_version") != PROBE_SCHEMA_VERSION:
                errors.append("repo probe has an unsupported schema")
        except (UiWorkflowError, UnicodeDecodeError, json.JSONDecodeError) as error:
            errors.append(f"cannot validate repo probe: {error}")
    binding = _validate_repo_binding(
        game_repo,
        probe,
        payload.get("repository_binding"),
        errors,
        require_current=require_current_repo_binding,
    ) if probe else {}

    surfaces_raw = _list(payload.get("surfaces"), "surfaces", errors)
    surfaces: list[dict[str, Any]] = []
    surface_ids: list[str] = []
    for index, raw in enumerate(surfaces_raw):
        label = f"surfaces[{index}]"
        if not isinstance(raw, dict):
            errors.append(f"{label} must be an object")
            continue
        _exact_fields(
            raw,
            {
                "surface_id",
                "responsibility",
                "layout_structure",
                "state_ownership",
                "refresh_and_signal_flow",
                "scene_lifecycle",
                "input_and_layering",
                "evidence_refs",
            },
            label,
            errors,
        )
        surface_id = _portable_id(raw.get("surface_id"), f"{label}.surface_id", errors)
        surface_ids.append(surface_id)
        surfaces.append(
            {
                "surface_id": surface_id,
                "responsibility": _text(raw.get("responsibility"), f"{label}.responsibility", errors),
                "layout_structure": _text(raw.get("layout_structure"), f"{label}.layout_structure", errors),
                "state_ownership": _text(raw.get("state_ownership"), f"{label}.state_ownership", errors),
                "refresh_and_signal_flow": _text(raw.get("refresh_and_signal_flow"), f"{label}.refresh_and_signal_flow", errors),
                "scene_lifecycle": _text(raw.get("scene_lifecycle"), f"{label}.scene_lifecycle", errors),
                "input_and_layering": _text(raw.get("input_and_layering"), f"{label}.input_and_layering", errors),
                "evidence_refs": _validate_evidence_refs(game_repo, raw.get("evidence_refs"), f"{label}.evidence_refs", errors),
            }
        )
    if len(surface_ids) != len(set(surface_ids)):
        errors.append("surfaces must not contain duplicate surface_id values")

    exemplars_raw = _list(payload.get("canonical_exemplars"), "canonical_exemplars", errors)
    exemplars: list[dict[str, Any]] = []
    exemplar_ids: list[str] = []
    for index, raw in enumerate(exemplars_raw):
        label = f"canonical_exemplars[{index}]"
        if not isinstance(raw, dict):
            errors.append(f"{label} must be an object")
            continue
        _exact_fields(
            raw,
            {
                "exemplar_id",
                "why_canonical",
                "rules_illustrated",
                "acceptance_provenance",
                "evidence_refs",
            },
            label,
            errors,
        )
        exemplar_id = _portable_id(raw.get("exemplar_id"), f"{label}.exemplar_id", errors)
        exemplar_ids.append(exemplar_id)
        evidence_refs = _validate_evidence_refs(
            game_repo,
            raw.get("evidence_refs"),
            f"{label}.evidence_refs",
            errors,
        )
        exemplars.append(
            {
                "exemplar_id": exemplar_id,
                "why_canonical": _text(raw.get("why_canonical"), f"{label}.why_canonical", errors),
                "rules_illustrated": _string_list(raw.get("rules_illustrated"), f"{label}.rules_illustrated", errors),
                "acceptance_provenance": _validate_exemplar_provenance(
                    game_repo,
                    raw.get("acceptance_provenance"),
                    evidence_refs,
                    project_id,
                    f"{label}.acceptance_provenance",
                    errors,
                ),
                "evidence_refs": evidence_refs,
            }
        )
    if len(exemplar_ids) != len(set(exemplar_ids)):
        errors.append("canonical_exemplars must not contain duplicate exemplar_id values")

    rules_raw = _list(payload.get("rules"), "rules", errors)
    rules: list[dict[str, Any]] = []
    rule_ids: list[str] = []
    categories: set[str] = set()
    project_bound_categories: set[str] = set()
    for index, raw in enumerate(rules_raw):
        label = f"rules[{index}]"
        if not isinstance(raw, dict):
            errors.append(f"{label} must be an object")
            continue
        _exact_fields(
            raw,
            {
                "rule_id",
                "category",
                "authority",
                "requirement",
                "rationale",
                "evidence_refs",
                "user_quote",
            },
            label,
            errors,
        )
        rule_id = _portable_id(raw.get("rule_id"), f"{label}.rule_id", errors)
        category = _text(raw.get("category"), f"{label}.category", errors)
        authority = _text(raw.get("authority"), f"{label}.authority", errors)
        if category and category not in REQUIRED_RULE_CATEGORIES:
            errors.append(f"{label}.category has an unsupported value")
        if authority and authority not in RULE_AUTHORITIES:
            errors.append(f"{label}.authority has an unsupported value")
        evidence = _validate_evidence_refs(
            game_repo,
            raw.get("evidence_refs"),
            f"{label}.evidence_refs",
            errors,
            allow_empty=authority != "REPO_EVIDENCE",
        )
        user_quote = _text(raw.get("user_quote", ""), f"{label}.user_quote", errors, allow_empty=True)
        if authority == "USER_RULING" and not user_quote:
            errors.append(f"{label}.user_quote is required for USER_RULING")
        if authority == "REPO_EVIDENCE" and not evidence:
            errors.append(f"{label} REPO_EVIDENCE requires exact evidence refs")
        rule_ids.append(rule_id)
        categories.add(category)
        if authority in {"REPO_EVIDENCE", "USER_RULING"}:
            project_bound_categories.add(category)
        rules.append(
            {
                "rule_id": rule_id,
                "category": category,
                "authority": authority,
                "requirement": _text(raw.get("requirement"), f"{label}.requirement", errors),
                "rationale": _text(raw.get("rationale"), f"{label}.rationale", errors),
                "evidence_refs": evidence,
                "user_quote": user_quote,
            }
        )
    if len(rule_ids) != len(set(rule_ids)):
        errors.append("rules must not contain duplicate rule_id values")
    missing_categories = sorted(REQUIRED_RULE_CATEGORIES - categories)
    if missing_categories:
        errors.append("rules lack required UI categories: " + ", ".join(missing_categories))
    missing_project_bound = sorted(
        PROJECT_BOUND_RULE_CATEGORIES - project_bound_categories
    )
    if missing_project_bound:
        errors.append(
            "core UI construction categories require repo evidence or a user ruling: "
            + ", ".join(missing_project_bound)
        )

    rule_id_set = set(rule_ids)
    for exemplar in exemplars:
        unknown = sorted(set(exemplar["rules_illustrated"]) - rule_id_set)
        if unknown:
            errors.append(
                f"canonical exemplar {exemplar['exemplar_id']} references unknown rules: "
                + ", ".join(unknown)
            )
    visual_rule_ids = {
        rule["rule_id"] for rule in rules if rule["category"] == "VISUAL_GRAMMAR"
    }
    if visual_rule_ids and not any(
        set(exemplar["rules_illustrated"]) & visual_rule_ids
        for exemplar in exemplars
    ):
        errors.append(
            "at least one accepted canonical exemplar must illustrate a "
            "VISUAL_GRAMMAR rule"
        )

    viewports_raw = _list(payload.get("viewport_profiles"), "viewport_profiles", errors)
    viewports: list[dict[str, Any]] = []
    viewport_ids: list[str] = []
    for index, raw in enumerate(viewports_raw):
        label = f"viewport_profiles[{index}]"
        if not isinstance(raw, dict):
            errors.append(f"{label} must be an object")
            continue
        _exact_fields(
            raw,
            {"viewport_id", "width", "height", "input_modes", "composition_requirements"},
            label,
            errors,
        )
        viewport_id = _portable_id(raw.get("viewport_id"), f"{label}.viewport_id", errors)
        width = raw.get("width")
        height = raw.get("height")
        if not isinstance(width, int) or isinstance(width, bool) or width < 1:
            errors.append(f"{label}.width must be a positive integer")
        if not isinstance(height, int) or isinstance(height, bool) or height < 1:
            errors.append(f"{label}.height must be a positive integer")
        viewport_ids.append(viewport_id)
        viewports.append(
            {
                "viewport_id": viewport_id,
                "width": width,
                "height": height,
                "input_modes": _string_list(raw.get("input_modes"), f"{label}.input_modes", errors),
                "composition_requirements": _string_list(raw.get("composition_requirements"), f"{label}.composition_requirements", errors),
            }
        )
    if len(viewport_ids) != len(set(viewport_ids)):
        errors.append("viewport_profiles must not contain duplicate viewport_id values")

    locale_raw = _list(payload.get("localization_profiles"), "localization_profiles", errors)
    locales: list[dict[str, Any]] = []
    locale_profile_ids: list[str] = []
    for index, raw in enumerate(locale_raw):
        label = f"localization_profiles[{index}]"
        if not isinstance(raw, dict):
            errors.append(f"{label} must be an object")
            continue
        _exact_fields(
            raw,
            {"profile_id", "locale_ids", "fit_requirements"},
            label,
            errors,
        )
        profile_id = _portable_id(raw.get("profile_id"), f"{label}.profile_id", errors)
        locale_profile_ids.append(profile_id)
        locales.append(
            {
                "profile_id": profile_id,
                "locale_ids": _string_list(raw.get("locale_ids"), f"{label}.locale_ids", errors),
                "fit_requirements": _string_list(raw.get("fit_requirements"), f"{label}.fit_requirements", errors),
            }
        )
    if len(locale_profile_ids) != len(set(locale_profile_ids)):
        errors.append("localization_profiles must not contain duplicate profile_id values")

    scenarios_raw = _list(payload.get("validation_scenarios"), "validation_scenarios", errors)
    scenarios: list[dict[str, Any]] = []
    scenario_ids: list[str] = []
    covered_viewports: set[str] = set()
    covered_locales: set[str] = set()
    covered_combinations: set[tuple[str, str, str]] = set()
    validation_kinds: set[str] = set()
    is_godot_project = (game_repo / "project.godot").is_file()
    for index, raw in enumerate(scenarios_raw):
        label = f"validation_scenarios[{index}]"
        if not isinstance(raw, dict):
            errors.append(f"{label} must be an object")
            continue
        _exact_fields(
            raw,
            {
                "scenario_id",
                "validation_kind",
                "viewport_id",
                "localization_profile_id",
                "ui_states",
                "interaction_path",
                "assertions",
                "comparison_methods",
                "capture_requirements",
            },
            label,
            errors,
        )
        scenario_id = _portable_id(raw.get("scenario_id"), f"{label}.scenario_id", errors)
        validation_kind = _text(
            raw.get("validation_kind"), f"{label}.validation_kind", errors
        )
        if validation_kind and validation_kind not in VALIDATION_KINDS:
            errors.append(f"{label}.validation_kind has an unsupported value")
        viewport_id = _text(raw.get("viewport_id"), f"{label}.viewport_id", errors)
        locale_id = _text(raw.get("localization_profile_id"), f"{label}.localization_profile_id", errors)
        if viewport_id not in set(viewport_ids):
            errors.append(f"{label}.viewport_id references an unknown profile")
        if locale_id not in set(locale_profile_ids):
            errors.append(f"{label}.localization_profile_id references an unknown profile")
        covered_viewports.add(viewport_id)
        covered_locales.add(locale_id)
        covered_combinations.add((viewport_id, locale_id, validation_kind))
        validation_kinds.add(validation_kind)
        comparison_methods = _string_list(
            raw.get("comparison_methods"),
            f"{label}.comparison_methods",
            errors,
        )
        unknown_methods = sorted(set(comparison_methods) - COMPARISON_METHODS)
        if unknown_methods:
            errors.append(
                f"{label}.comparison_methods has unsupported values: "
                + ", ".join(unknown_methods)
            )
        if (
            validation_kind == "STRUCTURAL_FIT"
            and not set(comparison_methods) & STRUCTURAL_COMPARISON_METHODS
        ):
            errors.append(
                f"{label} STRUCTURAL_FIT requires a mechanical geometry, state, "
                "scene, or interaction comparison"
            )
        if (
            validation_kind == "VISUAL_CONSISTENCY"
            and not set(comparison_methods) & MECHANICAL_VISUAL_COMPARISON_METHODS
        ):
            errors.append(
                f"{label} VISUAL_CONSISTENCY requires mechanical style comparison; "
                "screenshots alone are supplemental"
            )
        if (
            is_godot_project
            and validation_kind == "VISUAL_CONSISTENCY"
            and not set(comparison_methods) & GODOT_VISUAL_COMPARISON_METHODS
        ):
            errors.append(
                f"{label} Godot VISUAL_CONSISTENCY must compare Theme/StyleBox "
                "resource identity or resource properties directly"
            )
        scenario_ids.append(scenario_id)
        scenarios.append(
            {
                "scenario_id": scenario_id,
                "validation_kind": validation_kind,
                "viewport_id": viewport_id,
                "localization_profile_id": locale_id,
                "ui_states": _string_list(raw.get("ui_states"), f"{label}.ui_states", errors),
                "interaction_path": _string_list(raw.get("interaction_path"), f"{label}.interaction_path", errors),
                "assertions": _string_list(raw.get("assertions"), f"{label}.assertions", errors),
                "comparison_methods": comparison_methods,
                "capture_requirements": _string_list(raw.get("capture_requirements"), f"{label}.capture_requirements", errors),
            }
        )
    if len(scenario_ids) != len(set(scenario_ids)):
        errors.append("validation_scenarios must not contain duplicate scenario_id values")
    missing_viewports = sorted(set(viewport_ids) - covered_viewports)
    missing_locales = sorted(set(locale_profile_ids) - covered_locales)
    if missing_viewports:
        errors.append("validation scenarios do not cover viewport profiles: " + ", ".join(missing_viewports))
    if missing_locales:
        errors.append("validation scenarios do not cover localization profiles: " + ", ".join(missing_locales))
    missing_validation_kinds = sorted(VALIDATION_KINDS - validation_kinds)
    if missing_validation_kinds:
        errors.append(
            "validation scenarios lack required validation kinds: "
            + ", ".join(missing_validation_kinds)
        )
    missing_combinations = sorted(
        set(
            (viewport, locale, validation_kind)
            for viewport in viewport_ids
            for locale in locale_profile_ids
            for validation_kind in VALIDATION_KINDS
        )
        - covered_combinations
    )
    if missing_combinations:
        errors.append(
            "validation scenarios do not cover viewport/localization/kind combinations: "
            + ", ".join(
                f"{viewport}+{locale}+{validation_kind}"
                for viewport, locale, validation_kind in missing_combinations
            )
        )

    anti_raw = _list(payload.get("anti_patterns"), "anti_patterns", errors, allow_empty=True)
    anti_patterns: list[dict[str, Any]] = []
    anti_ids: list[str] = []
    for index, raw in enumerate(anti_raw):
        label = f"anti_patterns[{index}]"
        if not isinstance(raw, dict):
            errors.append(f"{label} must be an object")
            continue
        _exact_fields(
            raw,
            {"anti_pattern_id", "description", "evidence_refs"},
            label,
            errors,
        )
        anti_id = _portable_id(raw.get("anti_pattern_id"), f"{label}.anti_pattern_id", errors)
        anti_ids.append(anti_id)
        anti_patterns.append(
            {
                "anti_pattern_id": anti_id,
                "description": _text(raw.get("description"), f"{label}.description", errors),
                "evidence_refs": _validate_evidence_refs(game_repo, raw.get("evidence_refs"), f"{label}.evidence_refs", errors, allow_empty=True),
            }
        )
    if len(anti_ids) != len(set(anti_ids)):
        errors.append("anti_patterns must not contain duplicate ids")

    unresolved = _string_list(payload.get("unresolved_material_gaps"), "unresolved_material_gaps", errors, allow_empty=True)
    assumptions = _string_list(payload.get("ai_assumptions"), "ai_assumptions", errors, allow_empty=True)
    if unresolved:
        errors.append("unresolved_material_gaps must be empty before compile")
    if assumptions:
        errors.append("ai_assumptions must be empty; use evidence, a user ruling, or block")
    if _contains_placeholder(payload):
        errors.append("UI adapter input contains unresolved placeholders")

    normalized = {
        "schema_version": ADAPTER_SCHEMA_VERSION,
        "status": UI_PRODUCTION_ADAPTER_READY,
        "project_id": project_id,
        "repository_binding": binding,
        "source_probe_path": probe_path_text,
        "source_probe_sha256": probe_sha,
        "visual_grammar_policy": VISUAL_GRAMMAR_POLICY,
        "surfaces": surfaces,
        "canonical_exemplars": exemplars,
        "rules": rules,
        "viewport_profiles": viewports,
        "localization_profiles": locales,
        "validation_scenarios": scenarios,
        "anti_patterns": anti_patterns,
    }
    return normalized, errors


def _render_markdown(adapter: dict[str, Any]) -> str:
    lines = [
        f"# UI Production Adapter — `{adapter['project_id']}`",
        "",
        f"- Status: `{adapter['status']}`",
        f"- Source probe: `{adapter['source_probe_path']}`",
        f"- Source probe SHA-256: `{adapter['source_probe_sha256']}`",
        f"- Repository revision: `{adapter['repository_binding'].get('revision', '')}`",
        "",
        "This game-owned adapter is the UI construction authority for Gameplay",
        "Factory plans. It does not define feature intent; it defines how this repo",
        "realizes that intent without breaking layout, state, scene integration, or",
        "the accepted visual identity.",
        "",
        "## Visual grammar policy",
        "",
        "- Without explicit redesign authority: "
        f"`{adapter['visual_grammar_policy']['default_without_explicit_redesign']}`",
        "- Redesign authority must be: "
        f"`{adapter['visual_grammar_policy']['redesign_requires']}`",
        "",
        "## Owned surfaces and flows",
        "",
    ]
    for surface in adapter["surfaces"]:
        lines.extend(
            [
                f"### `{surface['surface_id']}`",
                f"- Responsibility: {surface['responsibility']}",
                f"- Layout structure: {surface['layout_structure']}",
                f"- State ownership: {surface['state_ownership']}",
                f"- Refresh/signals: {surface['refresh_and_signal_flow']}",
                f"- Scene lifecycle: {surface['scene_lifecycle']}",
                f"- Input/layering: {surface['input_and_layering']}",
                "- Evidence: "
                + "; ".join(f"`{ref['path']}` ({ref['role']})" for ref in surface["evidence_refs"]),
                "",
            ]
        )
    lines.extend(["## Canonical exemplars", ""])
    for exemplar in adapter["canonical_exemplars"]:
        provenance = exemplar["acceptance_provenance"]
        provenance_source = (
            provenance["accepted_baseline_path"]
            if provenance["authority"] == "ACCEPTED_BASELINE"
            else provenance["user_quote"]
        )
        lines.append(
            f"- `{exemplar['exemplar_id']}` — {exemplar['why_canonical']} "
            f"Rules: {', '.join(exemplar['rules_illustrated'])}. Evidence: "
            + ", ".join(f"`{ref['path']}`" for ref in exemplar["evidence_refs"])
            + f". Acceptance: {provenance['authority']} ({provenance_source})"
        )
    lines.extend(["", "## Binding rules", ""])
    for rule in adapter["rules"]:
        authority = rule["authority"]
        source = rule["user_quote"] or ", ".join(ref["path"] for ref in rule["evidence_refs"]) or "factory invariant"
        lines.append(
            f"- `{rule['rule_id']}` [{rule['category']}; {authority}] "
            f"{rule['requirement']} Why: {rule['rationale']} Source: {source}."
        )
    lines.extend(["", "## Viewports and localization", ""])
    for viewport in adapter["viewport_profiles"]:
        lines.append(
            f"- `{viewport['viewport_id']}` — {viewport['width']}×{viewport['height']}; "
            + "; ".join(viewport["composition_requirements"])
        )
    for profile in adapter["localization_profiles"]:
        lines.append(
            f"- `{profile['profile_id']}` — locales {', '.join(profile['locale_ids'])}; "
            + "; ".join(profile["fit_requirements"])
        )
    lines.extend(["", "## Validation scenarios", ""])
    for scenario in adapter["validation_scenarios"]:
        lines.append(
            f"- `{scenario['scenario_id']}` [{scenario['validation_kind']}] — "
            f"viewport `{scenario['viewport_id']}`, "
            f"locale profile `{scenario['localization_profile_id']}`; states: "
            f"{', '.join(scenario['ui_states'])}; assert: "
            + "; ".join(scenario["assertions"])
            + "; compare: "
            + ", ".join(scenario["comparison_methods"])
        )
    lines.extend(["", "## Known anti-patterns", ""])
    if adapter["anti_patterns"]:
        for anti in adapter["anti_patterns"]:
            lines.append(f"- `{anti['anti_pattern_id']}` — {anti['description']}")
    else:
        lines.append("- None evidenced at adapter compilation time.")
    return "\n".join(lines) + "\n"


def _expected_outputs(adapter: dict[str, Any]) -> dict[Path, str]:
    adapter_json = _json_text(adapter)
    adapter_md = _render_markdown(adapter)
    result = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "status": UI_PRODUCTION_ADAPTER_READY,
        "project_id": adapter["project_id"],
        "source_input_path": INPUT_RELATIVE.as_posix(),
        "source_input_sha256": "",  # filled by caller
        "outputs": {
            ADAPTER_JSON_RELATIVE.as_posix(): _sha256_text(adapter_json),
            ADAPTER_MD_RELATIVE.as_posix(): _sha256_text(adapter_md),
        },
    }
    return {
        ADAPTER_JSON_RELATIVE: adapter_json,
        ADAPTER_MD_RELATIVE: adapter_md,
        RESULT_RELATIVE: _json_text(result),
    }


def _build_outputs(
    game_repo: Path,
    input_path: Path,
    *,
    require_current_repo_binding: bool,
) -> tuple[dict[Path, str], list[str]]:
    payload = _load_json(input_path, "UI Production Adapter input")
    adapter, errors = _normalize_input(
        game_repo,
        payload,
        require_current_repo_binding=require_current_repo_binding,
    )
    outputs = _expected_outputs(adapter)
    result = json.loads(outputs[RESULT_RELATIVE])
    result["source_input_sha256"] = _sha256_bytes(input_path.read_bytes())
    outputs[RESULT_RELATIVE] = _json_text(result)
    return outputs, errors


def compile_ui_adapter(game_repo_text: str, input_text: str) -> UiWorkflowResult:
    # Resolve all caller-controlled paths and validate exact canonical input first.
    game_repo = _resolve_game_repo(game_repo_text)
    input_path = _resolve_cli_path(game_repo, input_text, must_exist=True)
    if input_path != (game_repo / INPUT_RELATIVE).resolve():
        raise UiWorkflowError(f"input must be {INPUT_RELATIVE.as_posix()}")
    outputs, errors = _build_outputs(
        game_repo, input_path, require_current_repo_binding=True
    )
    if errors:
        return UiWorkflowResult(BLOCKED_BY_UI_MODEL, errors=errors)

    differing = [
        relative.as_posix()
        for relative, expected in outputs.items()
        if (game_repo / relative).exists()
        and (
            not (game_repo / relative).is_file()
            or (game_repo / relative).read_text(encoding="utf-8") != expected
        )
    ]
    if differing:
        return UiWorkflowResult(
            BLOCKED_BY_EXISTING_UI_STATE,
            errors=[
                "existing canonical UI adapter state differs; remediate explicitly: "
                + ", ".join(differing)
            ],
        )

    created: list[str] = []
    verified: list[str] = []
    # All-target preflight above means no partial canonical write on conflict.
    for relative, expected in outputs.items():
        path = game_repo / relative
        if path.is_file():
            verified.append(relative.as_posix())
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(expected, encoding="utf-8")
        created.append(relative.as_posix())
    return UiWorkflowResult(
        UI_PRODUCTION_ADAPTER_READY,
        created_paths=created,
        verified_paths=verified,
    )


def _existing_outputs_are_checked(game_repo: Path) -> list[str]:
    """Return integrity errors for the adapter generation being replaced."""

    errors: list[str] = []
    result_path = game_repo / RESULT_RELATIVE
    if not result_path.is_file():
        return ["cannot refresh without the previous checked result"]
    try:
        result = json.loads(result_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return ["cannot refresh an invalid previous checked result"]
    outputs = result.get("outputs") if isinstance(result, dict) else None
    if (
        not isinstance(result, dict)
        or result.get("schema_version")
        not in PREVIOUS_RESULT_SCHEMA_VERSIONS | {RESULT_SCHEMA_VERSION}
        or result.get("status") != UI_PRODUCTION_ADAPTER_READY
        or not isinstance(outputs, dict)
    ):
        return ["cannot refresh an unsupported previous checked result"]
    for relative in (ADAPTER_JSON_RELATIVE, ADAPTER_MD_RELATIVE):
        path = game_repo / relative
        declared = outputs.get(relative.as_posix())
        if (
            not path.is_file()
            or not isinstance(declared, str)
            or _sha256_bytes(path.read_bytes()) != declared
        ):
            errors.append(
                "previous UI adapter artifact was modified outside the compiler: "
                + relative.as_posix()
            )
    return errors


def refresh_ui_adapter(game_repo_text: str, input_text: str) -> UiWorkflowResult:
    """Explicitly replace one intact checked generation with a new one."""

    game_repo = _resolve_game_repo(game_repo_text)
    input_path = _resolve_cli_path(game_repo, input_text, must_exist=True)
    if input_path != (game_repo / INPUT_RELATIVE).resolve():
        raise UiWorkflowError(f"input must be {INPUT_RELATIVE.as_posix()}")
    integrity_errors = _existing_outputs_are_checked(game_repo)
    if integrity_errors:
        return UiWorkflowResult(
            BLOCKED_BY_EXISTING_UI_STATE, errors=integrity_errors
        )
    outputs, errors = _build_outputs(
        game_repo, input_path, require_current_repo_binding=True
    )
    if errors:
        return UiWorkflowResult(BLOCKED_BY_UI_MODEL, errors=errors)

    # The command name is the explicit replacement authorization. Every old
    # canonical byte was verified above and every new byte is built in memory
    # before the first write; no backup/safety artifact is created.
    for relative, expected in outputs.items():
        (game_repo / relative).write_text(expected, encoding="utf-8")
    return UiWorkflowResult(
        UI_PRODUCTION_ADAPTER_READY,
        updated_paths=[relative.as_posix() for relative in outputs],
    )


def check_ui_adapter(game_repo_text: str, input_text: str) -> UiWorkflowResult:
    game_repo = _resolve_game_repo(game_repo_text)
    input_path = _resolve_cli_path(game_repo, input_text, must_exist=True)
    if input_path != (game_repo / INPUT_RELATIVE).resolve():
        raise UiWorkflowError(f"input must be {INPUT_RELATIVE.as_posix()}")
    outputs, errors = _build_outputs(
        game_repo, input_path, require_current_repo_binding=False
    )
    if errors:
        return UiWorkflowResult(BLOCKED_BY_UI_MODEL, errors=errors)
    mismatches: list[str] = []
    verified: list[str] = []
    for relative, expected in outputs.items():
        path = game_repo / relative
        if not path.is_file() or path.read_text(encoding="utf-8") != expected:
            mismatches.append(relative.as_posix())
        else:
            verified.append(relative.as_posix())
    if mismatches:
        return UiWorkflowResult(
            BLOCKED_BY_EXISTING_UI_STATE,
            errors=[
                "missing or stale UI adapter artifacts: "
                + ", ".join(mismatches)
                + ". If cited UI evidence changed, rerun probe/investigation and "
                "use the explicit refresh command."
            ],
        )
    return UiWorkflowResult(UI_PRODUCTION_ADAPTER_READY, verified_paths=verified)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", choices=["start", "probe", "compile", "refresh", "check"]
    )
    parser.add_argument("--game-repo", required=True)
    parser.add_argument("--input", default=INPUT_RELATIVE.as_posix())
    parser.add_argument("--output", default=PROBE_RELATIVE.as_posix())
    parser.add_argument("--max-candidates", type=int, default=200)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "start":
            result = start_ui_workflow(args.game_repo)
        elif args.command == "probe":
            result = probe_repository(
                args.game_repo, args.output, max_candidates=args.max_candidates
            )
        elif args.command == "compile":
            result = compile_ui_adapter(args.game_repo, args.input)
        elif args.command == "refresh":
            result = refresh_ui_adapter(args.game_repo, args.input)
        else:
            result = check_ui_adapter(args.game_repo, args.input)
    except UiWorkflowError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(result.status)
    for path in result.created_paths:
        print(f"CREATED: {path}")
    for path in result.updated_paths:
        print(f"UPDATED: {path}")
    for path in result.verified_paths:
        print(f"VERIFIED: {path}")
    for warning in result.warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    for error in result.errors:
        print(f"ERROR: {error}", file=sys.stderr)
    return 0 if result.status in {
        UI_PRODUCTION_ADAPTER_READY,
        UI_PRODUCTION_ADAPTER_ALREADY_READY,
        UI_PRODUCTION_ADAPTER_INPUT_REQUIRED,
    } else 2


if __name__ == "__main__":
    raise SystemExit(main())
