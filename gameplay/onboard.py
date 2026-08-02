#!/usr/bin/env python3
"""Case 2 foreign-repo onboarding compiler for Gameplay Factory.

The workflow is intentionally engineering-oriented. ``probe`` inventories a
bounded repository surface without assigning gameplay meaning. A single
investigator then supplies exact evidence in CASE2_ONBOARDING_INPUT.json.
``compile`` validates that evidence and preflights the minimum canonical Case
3 adapter/model/state/frontier artifacts before writing. ``check`` proves that
the generated handoff is still exact and accepted by the Case 3 material gate.

No command invents gameplay, silently chooses between conflicting runtime
systems, or overwrites existing factory state.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

try:  # Package import in tests; script import for ``python gameplay/onboard.py``.
    from gameplay.prepare import (
        READY_FOR_HOW_DESIGN,
        READY_FOR_NEW_GAMEPLAY_DESIGN,
        validate_materials,
    )
except ModuleNotFoundError:  # pragma: no cover - exercised by CLI smoke tests.
    from prepare import (  # type: ignore[no-redef]
        READY_FOR_HOW_DESIGN,
        READY_FOR_NEW_GAMEPLAY_DESIGN,
        validate_materials,
    )


INPUT_SCHEMA_VERSION = "case2_onboarding_input.v1"
PROBE_SCHEMA_VERSION = "case2_repo_probe.v1"
RESULT_SCHEMA_VERSION = "case2_onboarding_result.v1"
MODEL_SCHEMA_VERSION = "gameplay_design_model.v1"
UNIT_SCHEMA_VERSION = "next_gameplay_unit_input.v1"

CASE2_PROBE_READY = "CASE2_PROBE_READY"
ALREADY_CASE3 = "ALREADY_CASE3"
CASE3_READY = "CASE3_READY"
BLOCKED_BY_ONBOARDING_MATERIAL = "BLOCKED_BY_ONBOARDING_MATERIAL"
BLOCKED_BY_EXISTING_FACTORY_STATE = "BLOCKED_BY_EXISTING_FACTORY_STATE"

FACTORY_ROOT = Path(__file__).resolve().parent.parent

ONBOARDING_ROOT_RELATIVE = Path("design/gameplay/onboarding")
PROBE_RELATIVE = ONBOARDING_ROOT_RELATIVE / "CASE2_REPO_PROBE.json"
INPUT_RELATIVE = ONBOARDING_ROOT_RELATIVE / "CASE2_ONBOARDING_INPUT.json"
RESULT_RELATIVE = ONBOARDING_ROOT_RELATIVE / "CASE2_ONBOARDING_RESULT.json"

PROFILE_RELATIVE = Path("design/gameplay/adapter/PROJECT_GAMEPLAY_PROFILE.md")
PRODUCTION_RELATIVE = Path("design/gameplay/adapter/PRODUCTION_ADAPTER.md")
OBSERVATION_RELATIVE = Path("design/gameplay/adapter/OBSERVATION_ADAPTER.md")
MODEL_RELATIVE = Path("design/gameplay/adapter/GAMEPLAY_DESIGN_MODEL.json")
GRAMMAR_RELATIVE = Path("design/gameplay/state/GAMEPLAY_GRAMMAR_STATE.md")
LESSONS_RELATIVE = Path("design/gameplay/state/EXPERIENCE_LESSONS.md")

STATIC_CANONICAL_OUTPUTS = (
    PROFILE_RELATIVE,
    PRODUCTION_RELATIVE,
    OBSERVATION_RELATIVE,
    MODEL_RELATIVE,
    GRAMMAR_RELATIVE,
    LESSONS_RELATIVE,
    RESULT_RELATIVE,
)

PROJECT_MARKERS = (
    "project.godot",
    "package.json",
    "Cargo.toml",
    "pyproject.toml",
    "requirements.txt",
    "CMakeLists.txt",
    "Makefile",
    "ProjectSettings/ProjectVersion.txt",
)
IGNORED_DIRECTORY_NAMES = {
    ".git",
    ".godot",
    ".cache",
    "node_modules",
    "vendor",
    "build",
    "dist",
    "coverage",
    "debug_output",
}
CANDIDATE_EXTENSIONS = {
    ".gd",
    ".tscn",
    ".tres",
    ".csv",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".md",
    ".cs",
    ".ts",
    ".js",
    ".py",
    ".lua",
}
CANDIDATE_TERMS = (
    "progress",
    "objective",
    "mission",
    "quest",
    "stage",
    "level",
    "round",
    "turn",
    "game_system",
    "gamestate",
    "game_state",
    "save",
    "locale",
    "localization",
    "i18n",
    "action",
    "reward",
    "battle",
    "combat",
    "player",
    "input",
    "hud",
    "main",
    "test",
)
TEST_COMMAND_TERMS = (
    "test",
    "ci",
    "workflow",
    "makefile",
    "project.godot",
    "package.json",
    "pyproject",
)
EVIDENCE_REF_REQUIRED_FIELDS = ("role", "path", "contains")
REQUIRED_PRODUCTION_CONCERNS = {
    "objective_selection",
    "objective_completion",
    "player_actions",
    "rewards_and_state",
}


class OnboardingError(ValueError):
    """Raised before any command creates or overwrites an artifact."""


@dataclass
class OnboardingResult:
    status: str
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


def _resolve_game_repo(raw_path: str) -> Path:
    game_repo = Path(raw_path).expanduser().resolve()
    if not game_repo.is_dir():
        raise OnboardingError(f"game repo does not exist: {game_repo}")
    if game_repo == FACTORY_ROOT or _is_within(game_repo, FACTORY_ROOT):
        raise OnboardingError(
            "game repo must not be this factory repo or a child of it"
        )
    try:
        git_root = _run_git(game_repo, "rev-parse", "--show-toplevel").strip()
    except OnboardingError as error:
        raise OnboardingError("Case 2 requires an existing Git repository") from error
    if Path(git_root).resolve() != game_repo:
        raise OnboardingError(
            f"game repo must be the Git root, not a child: {game_repo}"
        )
    return game_repo


def _resolve_cli_owned_path(
    game_repo: Path,
    raw_path: str,
    *,
    must_exist: bool = False,
) -> Path:
    candidate = Path(raw_path).expanduser()
    resolved = (candidate if candidate.is_absolute() else game_repo / candidate).resolve()
    if not _is_within(resolved, game_repo):
        raise OnboardingError(f"path escapes game repo: {raw_path}")
    if must_exist and not resolved.exists():
        raise OnboardingError(f"required path does not exist: {raw_path}")
    return resolved


def _resolve_persisted_owned_path(
    game_repo: Path,
    raw_path: Any,
    *,
    must_exist: bool = False,
) -> Path:
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise OnboardingError("persisted paths must be non-empty strings")
    candidate = Path(raw_path).expanduser()
    if candidate.is_absolute():
        raise OnboardingError(
            f"persisted path must be game-repo-relative: {raw_path}"
        )
    return _resolve_cli_owned_path(game_repo, raw_path, must_exist=must_exist)


def _run_git(game_repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(game_repo), *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise OnboardingError(f"git {' '.join(args)} failed: {detail}")
    return result.stdout


def _run_git_bytes(game_repo: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(game_repo), *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise OnboardingError(f"git {' '.join(args)} failed: {detail}")
    return result.stdout


def _is_tracked_path(game_repo: Path, relative: Path) -> bool:
    result = subprocess.run(
        [
            "git",
            "-C",
            str(game_repo),
            "ls-files",
            "--error-unmatch",
            "--",
            relative.as_posix(),
        ],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def _load_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise OnboardingError(f"cannot read {label} JSON: {error}") from error
    if not isinstance(payload, dict):
        raise OnboardingError(f"{label} JSON must contain an object")
    return payload


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _require_text(value: Any, label: str, errors: list[str]) -> str:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label} must be a non-empty string")
        return ""
    if "TBD" in value:
        errors.append(f"{label} must not contain TBD")
    return value.strip()


def _require_string_list(
    value: Any,
    label: str,
    errors: list[str],
    *,
    allow_empty: bool = True,
) -> list[str]:
    if not isinstance(value, list):
        errors.append(f"{label} must be an array")
        return []
    if not allow_empty and not value:
        errors.append(f"{label} must contain at least one value")
    result: list[str] = []
    for index, item in enumerate(value):
        text = _require_text(item, f"{label}[{index}]", errors)
        if text:
            result.append(text)
    if len(result) != len(set(result)):
        errors.append(f"{label} must not contain duplicates")
    return result


def _portable_component(value: str, label: str, errors: list[str]) -> str:
    text = _require_text(value, label, errors)
    if text and not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", text):
        errors.append(
            f"{label} must be a portable lowercase path component ([a-z0-9._-])"
        )
    return text


def _evidence_ref_summary(refs: Iterable[dict[str, Any]]) -> str:
    parts: list[str] = []
    for ref in refs:
        path = str(ref.get("path", ""))
        tokens = ref.get("contains", [])
        token_summary = "; ".join(str(token) for token in tokens)
        parts.append(f"`{path}` — {token_summary}")
    return "<br>".join(parts) or "—"


def _validate_evidence_refs(
    game_repo: Path,
    refs: Any,
    label: str,
    errors: list[str],
    *,
    allow_empty: bool = False,
) -> set[str]:
    roles: set[str] = set()
    if not isinstance(refs, list) or (not refs and not allow_empty):
        errors.append(f"{label} must contain at least one evidence ref")
        return roles
    for index, ref in enumerate(refs):
        ref_label = f"{label}[{index}]"
        if not isinstance(ref, dict):
            errors.append(f"{ref_label} must be an object")
            continue
        for field_name in EVIDENCE_REF_REQUIRED_FIELDS:
            if field_name not in ref:
                errors.append(f"{ref_label} lacks {field_name}")
        role = _require_text(ref.get("role"), f"{ref_label}.role", errors)
        path_text = _require_text(ref.get("path"), f"{ref_label}.path", errors)
        contains = ref.get("contains")
        if not isinstance(contains, list) or not contains:
            errors.append(f"{ref_label}.contains must be a non-empty array")
            contains = []
        if role:
            roles.add(role)
        if not path_text:
            continue
        try:
            evidence_path = _resolve_persisted_owned_path(
                game_repo, path_text, must_exist=True
            )
        except OnboardingError as error:
            errors.append(str(error))
            continue
        if not evidence_path.is_file():
            errors.append(f"evidence ref is not a file: {path_text}")
            continue
        try:
            evidence_text = evidence_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(f"evidence ref is not UTF-8 text: {path_text}")
            continue
        for token_index, token in enumerate(contains):
            if not isinstance(token, str) or not token:
                errors.append(f"{ref_label}.contains[{token_index}] must be text")
            elif token not in evidence_text:
                errors.append(f"evidence token not found in {path_text}: {token}")
    return roles


def _canonical_outputs_for_input(payload: dict[str, Any]) -> tuple[Path, ...]:
    frontier = payload.get("initial_frontier", {})
    objective_dir = frontier.get("objective_dir", "") if isinstance(frontier, dict) else ""
    if not isinstance(objective_dir, str) or not re.fullmatch(
        r"[a-z0-9][a-z0-9._-]*", objective_dir
    ):
        return STATIC_CANONICAL_OUTPUTS
    unit_relative = Path(
        f"design/gameplay/objective_gameplay/{objective_dir}/"
        "NEXT_GAMEPLAY_UNIT_INPUT.json"
    )
    return (*STATIC_CANONICAL_OUTPUTS, unit_relative)


def _dirty_paths(
    game_repo: Path,
    *,
    ignored_exact: Iterable[Path] = (),
) -> list[str]:
    ignored = {path.as_posix() for path in ignored_exact}
    lines = _run_git(
        game_repo, "status", "--porcelain=v1", "--untracked-files=all"
    ).splitlines()
    paths: list[str] = []
    for line in lines:
        if len(line) < 4:
            continue
        path_text = line[3:]
        normalized = path_text.strip('"')
        if normalized.startswith(f"{ONBOARDING_ROOT_RELATIVE.as_posix()}/"):
            continue
        if normalized in ignored:
            continue
        paths.append(path_text)
    return sorted(paths)


def _working_tree_sha256(
    game_repo: Path,
    *,
    ignored_exact: Iterable[Path] = (),
) -> str:
    """Bind changed/untracked bytes without hashing the whole game repository."""

    ignored = {path.as_posix() for path in ignored_exact}
    tracked_changes = _run_git_bytes(
        game_repo, "diff", "--name-only", "-z", "HEAD", "--"
    ).split(b"\0")
    untracked = _run_git_bytes(
        game_repo, "ls-files", "--others", "--exclude-standard", "-z"
    ).split(b"\0")
    changed_paths = {
        raw.decode("utf-8", errors="surrogateescape")
        for raw in (*tracked_changes, *untracked)
        if raw
    }
    selected_paths = sorted(
        path
        for path in changed_paths
        if path not in ignored
        and not path.startswith(f"{ONBOARDING_ROOT_RELATIVE.as_posix()}/")
    )

    digest = hashlib.sha256()
    for relative in selected_paths:
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
        if path.exists() and not path.is_symlink():
            digest.update(f"mode:{path.stat().st_mode & 0o111:o}".encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def _repo_files(game_repo: Path) -> list[str]:
    raw = _run_git(
        game_repo,
        "ls-files",
        "--cached",
        "--others",
        "--exclude-standard",
        "-z",
    )
    files = [item for item in raw.split("\0") if item]
    result: list[str] = []
    for relative in files:
        parts = Path(relative).parts
        if any(part in IGNORED_DIRECTORY_NAMES for part in parts):
            continue
        if relative.startswith(f"{ONBOARDING_ROOT_RELATIVE.as_posix()}/"):
            continue
        path = (game_repo / relative).resolve()
        if _is_within(path, game_repo) and path.is_file():
            result.append(relative)
    return sorted(set(result))


def _candidate_score(relative: str) -> int:
    lower = relative.lower()
    score = sum(3 for term in CANDIDATE_TERMS if term in lower)
    if Path(relative).suffix.lower() in {".gd", ".cs", ".ts", ".js", ".py"}:
        score += 2
    if lower.startswith(("settings/", "setting/", "data/", "locales/", "tests/")):
        score += 1
    return score


def _looks_like_locale_csv(path: Path) -> bool:
    lower = path.as_posix().lower()
    if any(term in lower for term in ("locale", "localization", "i18n")):
        return True
    if path.suffix.lower() != ".csv":
        return False
    try:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            header = next(csv.reader(stream), [])
    except (OSError, UnicodeDecodeError, csv.Error):
        return False
    normalized = {column.strip().lower() for column in header}
    has_key = bool(normalized.intersection({"key", "keys", "id", "locale_key"}))
    has_locale = bool(
        normalized.intersection({"en", "zh", "zh_hant", "zh_hans", "ja", "jp"})
    )
    return has_key and has_locale


def _factory_state_complete(game_repo: Path) -> bool:
    required = (
        PROFILE_RELATIVE,
        PRODUCTION_RELATIVE,
        OBSERVATION_RELATIVE,
        MODEL_RELATIVE,
        GRAMMAR_RELATIVE,
        LESSONS_RELATIVE,
    )
    return all((game_repo / path).is_file() for path in required)


def probe_repository(
    game_repo_text: str,
    output_text: str,
    *,
    max_candidates: int = 200,
) -> OnboardingResult:
    """Write a bounded, non-semantic repository probe at the canonical path."""

    game_repo = _resolve_game_repo(game_repo_text)
    output_path = _resolve_cli_owned_path(game_repo, output_text)
    canonical_output = (game_repo / PROBE_RELATIVE).resolve()
    if output_path != canonical_output:
        raise OnboardingError(
            f"probe output must be {PROBE_RELATIVE.as_posix()}"
        )
    if max_candidates < 1 or max_candidates > 1000:
        raise OnboardingError("max_candidates must be between 1 and 1000")

    files = _repo_files(game_repo)
    if not files:
        raise OnboardingError("Case 2 requires a non-blank existing repository")
    revision = _run_git(game_repo, "rev-parse", "HEAD").strip()
    branch = _run_git(game_repo, "rev-parse", "--abbrev-ref", "HEAD").strip()
    markers = [marker for marker in PROJECT_MARKERS if (game_repo / marker).is_file()]

    scored_candidates = [
        (_candidate_score(relative), relative)
        for relative in files
        if Path(relative).suffix.lower() in CANDIDATE_EXTENSIONS
    ]
    scored_candidates = [item for item in scored_candidates if item[0] > 0]
    scored_candidates.sort(key=lambda item: (-item[0], item[1]))
    selected_candidates = [
        {"path": relative, "score": score}
        for score, relative in scored_candidates[:max_candidates]
    ]
    locale_candidates = [
        relative for relative in files if _looks_like_locale_csv(game_repo / relative)
    ][:100]
    command_candidates = [
        relative
        for relative in files
        if any(term in relative.lower() for term in TEST_COMMAND_TERMS)
    ][:100]

    status = ALREADY_CASE3 if _factory_state_complete(game_repo) else CASE2_PROBE_READY
    payload = {
        "schema_version": PROBE_SCHEMA_VERSION,
        "status": status,
        "repository": {
            "revision": revision,
            "branch": branch,
            "dirty_paths": _dirty_paths(game_repo),
            "working_tree_sha256": _working_tree_sha256(game_repo),
            "tracked_or_unignored_file_count": len(files),
            "project_markers": markers,
        },
        "candidate_files": selected_candidates,
        "candidate_file_count_before_limit": len(scored_candidates),
        "candidate_limit": max_candidates,
        "locale_candidates": locale_candidates,
        "validation_command_source_candidates": command_candidates,
        "interpretation_warning": (
            "Paths and scores are search hints only. They do not establish the "
            "live progression driver, objective, action, reward, or authority."
        ),
    }
    rendered = _json_text(payload)
    if output_path.exists():
        existing = output_path.read_text(encoding="utf-8")
        if existing != rendered:
            raise OnboardingError(
                "probe output already exists with different content; remove it "
                "only after preserving intentional game-owned work"
            )
        return OnboardingResult(status, verified_paths=[PROBE_RELATIVE.as_posix()])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")
    return OnboardingResult(status, created_paths=[PROBE_RELATIVE.as_posix()])


def _validate_repository_binding(
    payload: dict[str, Any],
    game_repo: Path,
    errors: list[str],
) -> None:
    repository = payload.get("repository")
    if not isinstance(repository, dict):
        errors.append("repository must be an object")
        return
    probe_path = game_repo / PROBE_RELATIVE
    if not probe_path.is_file():
        errors.append(
            f"missing mechanical repository probe: {PROBE_RELATIVE.as_posix()}"
        )
        probe: dict[str, Any] = {}
    else:
        try:
            probe = _load_json_object(probe_path, "Case 2 repository probe")
        except OnboardingError as error:
            errors.append(str(error))
            probe = {}
    if probe and probe.get("schema_version") != PROBE_SCHEMA_VERSION:
        errors.append(f"repository probe schema_version must be {PROBE_SCHEMA_VERSION}")
    if probe and probe.get("status") != CASE2_PROBE_READY:
        errors.append(
            "repository probe does not classify this repo as Case 2; route "
            "ALREADY_CASE3 through gameplay/AGENTS.md"
        )
    expected_revision = _require_text(
        repository.get("expected_revision"), "repository.expected_revision", errors
    )
    declared_dirty = _require_string_list(
        repository.get("declared_dirty_paths"),
        "repository.declared_dirty_paths",
        errors,
    )
    expected_working_tree_sha256 = _require_text(
        repository.get("working_tree_sha256"),
        "repository.working_tree_sha256",
        errors,
    )
    if expected_working_tree_sha256 and not re.fullmatch(
        r"[0-9a-f]{64}", expected_working_tree_sha256
    ):
        errors.append("repository.working_tree_sha256 must be a SHA-256 hex digest")
    if expected_revision:
        probe_repository_data = probe.get("repository", {}) if probe else {}
        if (
            isinstance(probe_repository_data, dict)
            and probe_repository_data.get("revision") != expected_revision
        ):
            errors.append(
                "repository.expected_revision does not match CASE2_REPO_PROBE.json"
            )
        current_revision = _run_git(game_repo, "rev-parse", "HEAD").strip()
        if current_revision != expected_revision:
            errors.append(
                "repository revision changed since onboarding study: expected "
                f"{expected_revision}, found {current_revision}"
            )
    # Generated outputs must disappear from the post-compile binding, while
    # pre-existing partial/deleted factory state must remain visible on the
    # first compile. The canonical result is the marker that this compiler has
    # already completed once; exact artifact comparison happens separately.
    ignored_outputs = (
        _canonical_outputs_for_input(payload)
        if (game_repo / RESULT_RELATIVE).is_file()
        else ()
    )
    current_dirty = _dirty_paths(game_repo, ignored_exact=ignored_outputs)
    probe_repository_data = probe.get("repository", {}) if probe else {}
    if (
        isinstance(probe_repository_data, dict)
        and probe_repository_data.get("dirty_paths") != declared_dirty
    ):
        errors.append(
            "repository.declared_dirty_paths does not match CASE2_REPO_PROBE.json"
        )
    if declared_dirty != current_dirty:
        errors.append(
            "repository dirty paths changed since onboarding study: expected "
            f"{declared_dirty}, found {current_dirty}"
        )
    if isinstance(probe_repository_data, dict):
        probe_working_tree_sha256 = probe_repository_data.get("working_tree_sha256")
        if probe_working_tree_sha256 != expected_working_tree_sha256:
            errors.append(
                "repository.working_tree_sha256 does not match "
                "CASE2_REPO_PROBE.json"
            )
    current_working_tree_sha256 = _working_tree_sha256(
        game_repo, ignored_exact=ignored_outputs
    )
    if expected_working_tree_sha256 != current_working_tree_sha256:
        errors.append(
            "repository working-tree content changed since onboarding study: "
            f"expected {expected_working_tree_sha256}, found "
            f"{current_working_tree_sha256}"
        )


def _validate_profile(
    profile: Any,
    game_repo: Path,
    errors: list[str],
) -> None:
    if not isinstance(profile, dict):
        errors.append("project_profile must be an object")
        return
    for field_name in ("primary_locale", "target_runtime"):
        _require_text(profile.get(field_name), f"project_profile.{field_name}", errors)
    source_roles = _validate_evidence_refs(
        game_repo,
        profile.get("authoritative_source_refs"),
        "project_profile.authoritative_source_refs",
        errors,
    )
    if "current_state_source" not in source_roles:
        errors.append(
            "project_profile requires a current_state_source evidence ref"
        )
    for field_name in (
        "player_frames",
        "core_fantasy_and_desires",
        "sovereignty_and_red_lines",
        "systems_and_spaces",
        "presentation_and_control",
        "grammar_and_handoff",
        "review_and_evidence_owners",
    ):
        _require_string_list(
            profile.get(field_name),
            f"project_profile.{field_name}",
            errors,
            allow_empty=False,
        )


def _validate_production_adapter(
    adapter: Any,
    game_repo: Path,
    errors: list[str],
) -> None:
    if not isinstance(adapter, dict):
        errors.append("production_adapter must be an object")
        return
    _require_text(
        adapter.get("supported_revision"),
        "production_adapter.supported_revision",
        errors,
    )
    surfaces = adapter.get("runtime_surfaces")
    if not isinstance(surfaces, list) or not surfaces:
        errors.append("production_adapter.runtime_surfaces must not be empty")
        surfaces = []
    for index, surface in enumerate(surfaces):
        label = f"production_adapter.runtime_surfaces[{index}]"
        if not isinstance(surface, dict):
            errors.append(f"{label} must be an object")
            continue
        _require_text(surface.get("surface"), f"{label}.surface", errors)
        _require_text(surface.get("owner"), f"{label}.owner", errors)
        paths = _require_string_list(
            surface.get("paths"), f"{label}.paths", errors, allow_empty=False
        )
        for path_text in paths:
            try:
                _resolve_persisted_owned_path(game_repo, path_text, must_exist=True)
            except OnboardingError as error:
                errors.append(str(error))
        _validate_evidence_refs(
            game_repo, surface.get("evidence_refs"), f"{label}.evidence_refs", errors
        )

    mappings = adapter.get("gameplay_mappings")
    if not isinstance(mappings, list) or not mappings:
        errors.append("production_adapter.gameplay_mappings must not be empty")
        mappings = []
    concerns: set[str] = set()
    for index, mapping in enumerate(mappings):
        label = f"production_adapter.gameplay_mappings[{index}]"
        if not isinstance(mapping, dict):
            errors.append(f"{label} must be an object")
            continue
        concern = _require_text(mapping.get("concern"), f"{label}.concern", errors)
        _require_text(mapping.get("description"), f"{label}.description", errors)
        if concern in concerns:
            errors.append(f"duplicate production mapping concern: {concern}")
        concerns.add(concern)
        _validate_evidence_refs(
            game_repo, mapping.get("evidence_refs"), f"{label}.evidence_refs", errors
        )
    missing_concerns = sorted(REQUIRED_PRODUCTION_CONCERNS - concerns)
    if missing_concerns:
        errors.append(
            "production_adapter.gameplay_mappings lacks required concerns: "
            + ", ".join(missing_concerns)
        )
    for field_name in (
        "validation_commands",
        "integration_constraints",
        "unsupported_capabilities",
    ):
        _require_string_list(
            adapter.get(field_name),
            f"production_adapter.{field_name}",
            errors,
            allow_empty=field_name == "unsupported_capabilities",
        )


def _validate_observation_adapter(
    adapter: Any,
    game_repo: Path,
    errors: list[str],
    warnings: list[str],
) -> None:
    if not isinstance(adapter, dict):
        errors.append("observation_adapter must be an object")
        return
    status = _require_text(adapter.get("status"), "observation_adapter.status", errors)
    if status not in {"AVAILABLE", "NOT_AVAILABLE"}:
        errors.append("observation_adapter.status has an unsupported value")
    _require_text(
        adapter.get("supported_revision"),
        "observation_adapter.supported_revision",
        errors,
    )
    mapping_path = _require_text(
        adapter.get("mapping_path"), "observation_adapter.mapping_path", errors
    )
    sources = adapter.get("evidence_sources")
    if status == "AVAILABLE":
        _validate_evidence_refs(
            game_repo,
            sources,
            "observation_adapter.evidence_sources",
            errors,
        )
        if mapping_path and mapping_path != "NOT_AVAILABLE":
            try:
                _resolve_persisted_owned_path(
                    game_repo, mapping_path, must_exist=True
                )
            except OnboardingError as error:
                errors.append(str(error))
        else:
            errors.append("AVAILABLE observation adapter requires a mapping_path")
    else:
        if mapping_path != "NOT_AVAILABLE":
            errors.append(
                "NOT_AVAILABLE observation adapter must use mapping_path "
                "NOT_AVAILABLE"
            )
        if not isinstance(sources, list) or sources:
            errors.append(
                "NOT_AVAILABLE observation adapter must have empty evidence_sources"
            )
        warnings.append(
            "runtime observation/acceptance remains blocked until instrumentation "
            "and mapping become available; compact Case 3 design may proceed"
        )
    for field_name in (
        "launch_and_capture",
        "provenance_and_ordering",
        "validation_commands",
        "limits_and_gaps",
    ):
        _require_string_list(
            adapter.get(field_name),
            f"observation_adapter.{field_name}",
            errors,
            allow_empty=status == "NOT_AVAILABLE" and field_name != "limits_and_gaps",
        )


def _compile_unit_input(payload: dict[str, Any]) -> dict[str, Any]:
    frontier = payload.get("initial_frontier", {})
    return {
        "schema_version": UNIT_SCHEMA_VERSION,
        "project_id": payload.get("project_id"),
        "project_model_path": MODEL_RELATIVE.as_posix(),
        "frontier": frontier.get("frontier"),
        "applicable_action_ids": frontier.get("applicable_action_ids"),
        "recent_patterns": frontier.get("recent_patterns"),
        "design_constraints": frontier.get("design_constraints"),
    }


def _validate_case3_material_projection(
    payload: dict[str, Any],
    game_repo: Path,
    errors: list[str],
    warnings: list[str],
) -> str:
    model = payload.get("gameplay_model")
    if not isinstance(model, dict):
        errors.append("gameplay_model must be an object")
        return ""
    if model.get("schema_version") != MODEL_SCHEMA_VERSION:
        errors.append(f"gameplay_model.schema_version must be {MODEL_SCHEMA_VERSION}")
    if model.get("project_id") != payload.get("project_id"):
        errors.append("gameplay_model.project_id must match project_id")
    driver = model.get("primary_progression_driver")
    if not isinstance(driver, dict):
        errors.append("gameplay_model.primary_progression_driver must be an object")
        driver = {}
    driver_roles = _validate_evidence_refs(
        game_repo,
        driver.get("evidence_refs"),
        "gameplay_model.primary_progression_driver.evidence_refs",
        errors,
    )
    if "progression_authority" not in driver_roles:
        errors.append(
            "gameplay_model primary progression driver requires a "
            "progression_authority evidence ref"
        )
    actions = model.get("player_actions")
    if not isinstance(actions, list):
        errors.append("gameplay_model.player_actions must be an array")
        actions = []
    action_ids: list[str] = []
    for index, action in enumerate(actions):
        action_label = f"gameplay_model.player_actions[{index}]"
        if not isinstance(action, dict):
            errors.append(f"{action_label} must be an object")
            continue
        action_id = _require_text(action.get("action_id"), f"{action_label}.action_id", errors)
        _require_text(action.get("description"), f"{action_label}.description", errors)
        _require_text(action.get("availability"), f"{action_label}.availability", errors)
        if action_id:
            action_ids.append(action_id)
        rewards = action.get("rewards")
        if not isinstance(rewards, list) or not rewards:
            errors.append(f"{action_label}.rewards must contain at least one reward")
        else:
            for reward_index, reward in enumerate(rewards):
                reward_label = f"{action_label}.rewards[{reward_index}]"
                if not isinstance(reward, dict):
                    errors.append(f"{reward_label} must be an object")
                    continue
                for field_name in ("reward_id", "kind", "description"):
                    _require_text(
                        reward.get(field_name), f"{reward_label}.{field_name}", errors
                    )
        action_roles = _validate_evidence_refs(
            game_repo,
            action.get("evidence_refs"),
            f"{action_label}.evidence_refs",
            errors,
        )
        if "runtime_action" not in action_roles:
            errors.append(
                f"{action_label} requires a runtime_action evidence ref"
            )
    if len(action_ids) != len(set(action_ids)):
        errors.append("gameplay_model contains duplicate action ids")
    model_recent_patterns = _require_string_list(
        model.get("recent_patterns"), "gameplay_model.recent_patterns", errors
    )
    model_design_constraints = _require_string_list(
        model.get("design_constraints"), "gameplay_model.design_constraints", errors
    )

    initial = payload.get("initial_frontier")
    if not isinstance(initial, dict):
        errors.append("initial_frontier must be an object")
        return ""
    objective_dir = _portable_component(
        initial.get("objective_dir"), "initial_frontier.objective_dir", errors
    )
    frontier = initial.get("frontier")
    if not isinstance(frontier, dict):
        errors.append("initial_frontier.frontier must be an object")
        frontier = {}
    locale = frontier.get("objective_locale")
    if isinstance(locale, dict):
        locale_path = locale.get("path")
        try:
            _resolve_persisted_owned_path(game_repo, locale_path, must_exist=True)
        except OnboardingError as error:
            errors.append(str(error))
    frontier_roles = _validate_evidence_refs(
        game_repo,
        frontier.get("evidence_refs"),
        "initial_frontier.frontier.evidence_refs",
        errors,
    )
    for required_role in ("runtime_selection", "runtime_completion"):
        if required_role not in frontier_roles:
            errors.append(
                "initial_frontier.frontier requires a " + required_role + " evidence ref"
            )
    applicable_action_ids = _require_string_list(
        initial.get("applicable_action_ids"),
        "initial_frontier.applicable_action_ids",
        errors,
    )
    unknown_actions = sorted(set(applicable_action_ids) - set(action_ids))
    if unknown_actions:
        errors.append(
            "initial_frontier references unknown action ids: "
            + ", ".join(unknown_actions)
        )
    initial_recent_patterns = _require_string_list(
        initial.get("recent_patterns"), "initial_frontier.recent_patterns", errors
    )
    initial_design_constraints = _require_string_list(
        initial.get("design_constraints"),
        "initial_frontier.design_constraints",
        errors,
    )

    actions_by_id = {
        action.get("action_id"): action
        for action in actions
        if isinstance(action, dict) and isinstance(action.get("action_id"), str)
    }
    full_material_payload = {
        "schema_version": UNIT_SCHEMA_VERSION,
        "project_id": payload.get("project_id"),
        "primary_progression_driver": model.get("primary_progression_driver"),
        "frontier": initial.get("frontier"),
        "player_actions": [
            actions_by_id[action_id]
            for action_id in applicable_action_ids
            if action_id in actions_by_id
        ],
        "recent_patterns": model_recent_patterns + initial_recent_patterns,
        "design_constraints": model_design_constraints + initial_design_constraints,
    }
    preparation = validate_materials(full_material_payload, game_repo)
    errors.extend(f"Case 3 material gate: {error}" for error in preparation.errors)
    warnings.extend(
        f"Case 3 material gate: {warning}" for warning in preparation.warnings
    )
    if preparation.status not in {
        READY_FOR_HOW_DESIGN,
        READY_FOR_NEW_GAMEPLAY_DESIGN,
    }:
        errors.append(
            "compiled frontier does not satisfy the Case 3 material gate: "
            f"{preparation.status}"
        )
    return objective_dir


def _validate_onboarding_input(
    payload: Any,
    game_repo: Path,
) -> tuple[list[str], list[str], str]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(payload, dict):
        return ["input must be an object"], warnings, ""
    if payload.get("schema_version") != INPUT_SCHEMA_VERSION:
        errors.append(f"schema_version must be {INPUT_SCHEMA_VERSION}")
    project_id = _portable_component(payload.get("project_id"), "project_id", errors)
    onboarding_date = _require_text(
        payload.get("onboarding_date"), "onboarding_date", errors
    )
    if onboarding_date and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", onboarding_date):
        errors.append("onboarding_date must use YYYY-MM-DD")

    _validate_repository_binding(payload, game_repo, errors)
    _validate_profile(payload.get("project_profile"), game_repo, errors)
    _validate_production_adapter(
        payload.get("production_adapter"), game_repo, errors
    )
    _validate_observation_adapter(
        payload.get("observation_adapter"), game_repo, errors, warnings
    )
    repository = payload.get("repository")
    expected_revision = (
        repository.get("expected_revision") if isinstance(repository, dict) else None
    )
    for adapter_name in ("production_adapter", "observation_adapter"):
        adapter = payload.get(adapter_name)
        if (
            isinstance(adapter, dict)
            and expected_revision
            and adapter.get("supported_revision") != expected_revision
        ):
            errors.append(
                f"{adapter_name}.supported_revision must match "
                "repository.expected_revision"
            )
    objective_dir = _validate_case3_material_projection(
        payload, game_repo, errors, warnings
    )

    _require_string_list(payload.get("user_rulings"), "user_rulings", errors)
    material_gaps = _require_string_list(
        payload.get("unresolved_material_gaps"),
        "unresolved_material_gaps",
        errors,
    )
    assumptions = _require_string_list(
        payload.get("ai_assumptions"), "ai_assumptions", errors
    )
    if material_gaps:
        errors.append(
            "unresolved_material_gaps must be empty before Case 3 handoff"
        )
    if assumptions:
        errors.append(
            "ai_assumptions must be empty; obtain evidence or a persisted user "
            "ruling before Case 3 handoff"
        )
    if project_id and str(game_repo) in json.dumps(payload, ensure_ascii=False):
        errors.append("onboarding input must not persist the absolute game repo path")
    return errors, warnings, objective_dir


def _render_profile(payload: dict[str, Any]) -> str:
    project_id = payload["project_id"]
    profile = payload["project_profile"]
    model = payload["gameplay_model"]
    refs = profile["authoritative_source_refs"]
    lines = [
        f"# Project Gameplay Profile — `{project_id}`",
        "",
        f"- Onboarding date: `{payload['onboarding_date']}`",
        f"- Source revision: `{payload['repository']['expected_revision']}`",
        "- Source working-tree fingerprint: "
        f"`{payload['repository']['working_tree_sha256']}`",
        f"- Primary locale: `{profile['primary_locale']}`",
        f"- Target runtime/platform: {profile['target_runtime']}",
        f"- Machine gameplay model: `{MODEL_RELATIVE.as_posix()}`",
        "",
        "## Authoritative inputs",
        "",
    ]
    for ref in refs:
        lines.append(
            f"- `{ref['role']}` — `{ref['path']}` — "
            + "; ".join(ref["contains"])
        )
    sections = (
        ("Player frames", "player_frames"),
        ("Core fantasy and player desires", "core_fantasy_and_desires"),
        ("Gameplay sovereignty and red lines", "sovereignty_and_red_lines"),
        ("Systems and playable spaces", "systems_and_spaces"),
        ("Presentation and control", "presentation_and_control"),
        ("Gameplay grammar and handoff", "grammar_and_handoff"),
        ("Human review and evidence owners", "review_and_evidence_owners"),
    )
    for heading, field_name in sections:
        lines.extend(["", f"## {heading}", ""])
        lines.extend(f"- {item}" for item in profile[field_name])
    lines.extend(["", "## Persisted user rulings", ""])
    if payload["user_rulings"]:
        lines.extend(f"- {item}" for item in payload["user_rulings"])
    else:
        lines.append("- None recorded during onboarding.")
    lines.extend(["", "## Implemented player actions", ""])
    lines.append(
        "The descriptions, availability, rewards/consequences, and exact runtime "
        f"evidence are authoritative in `{MODEL_RELATIVE.as_posix()}`."
    )
    if model["player_actions"]:
        lines.extend(
            f"- `{action['action_id']}` — {action['description']}"
            for action in model["player_actions"]
        )
    else:
        lines.append("- None proven; the initial frontier requires new gameplay design.")
    lines.extend(
        [
            "",
            "## Onboarding boundary",
            "",
            "This file reconstructs existing repo semantics. It does not approve "
            "new gameplay, claim fun, or override runtime evidence.",
            "",
        ]
    )
    return "\n".join(lines)


def _render_production_adapter(payload: dict[str, Any]) -> str:
    project_id = payload["project_id"]
    adapter = payload["production_adapter"]
    lines = [
        f"# Production Adapter — `{project_id}`",
        "",
        f"- Adapter version/date: `case2.v1 / {payload['onboarding_date']}`",
        f"- Supported revision: `{adapter['supported_revision']}`",
        "- Source working-tree fingerprint: "
        f"`{payload['repository']['working_tree_sha256']}`",
        "",
        "## Runtime surfaces",
        "",
        "| Surface | Target paths | Producer / owner | Exact evidence |",
        "| --- | --- | --- | --- |",
    ]
    for surface in adapter["runtime_surfaces"]:
        lines.append(
            f"| {surface['surface']} | "
            f"{'<br>'.join(f'`{path}`' for path in surface['paths'])} | "
            f"{surface['owner']} | {_evidence_ref_summary(surface['evidence_refs'])} |"
        )
    lines.extend(
        [
            "",
            "## Gameplay-to-runtime mappings",
            "",
            "| Concern | Existing mapping | Exact evidence |",
            "| --- | --- | --- |",
        ]
    )
    for mapping in adapter["gameplay_mappings"]:
        lines.append(
            f"| `{mapping['concern']}` | {mapping['description']} | "
            f"{_evidence_ref_summary(mapping['evidence_refs'])} |"
        )
    sections = (
        ("Validation commands", "validation_commands"),
        ("Integration constraints", "integration_constraints"),
        ("Unsupported capabilities", "unsupported_capabilities"),
    )
    for heading, field_name in sections:
        lines.extend(["", f"## {heading}", ""])
        values = adapter[field_name]
        lines.extend(f"- {value}" for value in values)
        if not values:
            lines.append("- None declared.")
    lines.extend(
        [
            "",
            "## Production boundary",
            "",
            "Mechanical validation proves code/data/state integrity, not player "
            "reception. New paths or unsupported capabilities require an explicit "
            "plan revision; the adapter does not authorize silent scope expansion.",
            "",
        ]
    )
    return "\n".join(lines)


def _render_observation_adapter(payload: dict[str, Any]) -> str:
    project_id = payload["project_id"]
    adapter = payload["observation_adapter"]
    lines = [
        f"# Observation Adapter — `{project_id}`",
        "",
        f"- Adapter version/date: `case2.v1 / {payload['onboarding_date']}`",
        f"- Supported revision: `{adapter['supported_revision']}`",
        "- Source working-tree fingerprint: "
        f"`{payload['repository']['working_tree_sha256']}`",
        f"- Observation status: `{adapter['status']}`",
        f"- Machine-readable mapping path: `{adapter['mapping_path']}`",
        "",
        "## Evidence sources",
        "",
    ]
    if adapter["evidence_sources"]:
        for ref in adapter["evidence_sources"]:
            lines.append(
                f"- `{ref['role']}` — `{ref['path']}` — "
                + "; ".join(ref["contains"])
            )
    else:
        lines.append("- `NOT_AVAILABLE` — no runtime evidence source is claimed.")
    sections = (
        ("Launch and capture", "launch_and_capture"),
        ("Provenance, ordering, and correlation", "provenance_and_ordering"),
        ("Validation commands", "validation_commands"),
        ("Limits and gaps", "limits_and_gaps"),
    )
    for heading, field_name in sections:
        lines.extend(["", f"## {heading}", ""])
        values = adapter[field_name]
        lines.extend(f"- {value}" for value in values)
        if not values:
            lines.append("- `NOT_AVAILABLE`")
    lines.extend(
        [
            "",
            "## Acceptance boundary",
            "",
            "`NOT_AVAILABLE` permits compact Case 3 design/production planning but "
            "blocks runtime evidence or acceptance claims that require the missing "
            "capability. The reader never infers absent evidence.",
            "",
        ]
    )
    return "\n".join(lines)


def _render_grammar_state(payload: dict[str, Any]) -> str:
    project_id = payload["project_id"]
    return f"""# Gameplay Grammar State — `{project_id}`

This game-owned ledger is derived gameplay-design state, not runtime truth.
Case 2 onboarding creates an empty baseline and does not infer a play history.

- Last approved trace/packet: none
- Source authority: none yet
- State version/date: `v0 / {payload['onboarding_date']}`

## Recent player verbs

None recorded from an approved trace.

## Current rhythm position

Not established.

## Player-knowledge ledger

None recorded from an approved trace.

## Open player expectations

None recorded from an approved trace.

## Budget/cost position

Not established.

## Completion feedback and handoff history

None recorded from an approved trace.
"""


def _render_experience_lessons(payload: dict[str, Any]) -> str:
    project_id = payload["project_id"]
    return f"""# Gameplay Experience Lessons — `{project_id}`

This game-owned ledger stores derived lessons from completed conformance runs
and human playtests. Case 2 onboarding creates an empty baseline; repository
research is not a playtest or acceptance result.

- State version/date: `v0 / {payload['onboarding_date']}`
- Last incorporated acceptance/human-playtest refs: none

## Confirmed conformance lessons

None recorded.

## Human playtest rulings

None recorded by onboarding.

## Reception and observability lessons

None recorded by onboarding.

## Open hypotheses

None recorded. AI onboarding assumptions are forbidden from entering Case 3.

## Do not infer

- A factory pass is not proof of fun.
- One player/run is not universal behavior.
- A verifier's alternate action is not canonical design.
- A derived lesson cannot overwrite a USER ruling.
"""


def _expected_artifacts(
    payload: dict[str, Any],
    objective_dir: str,
    warnings: list[str],
) -> dict[Path, str]:
    unit_relative = Path(
        f"design/gameplay/objective_gameplay/{objective_dir}/"
        "NEXT_GAMEPLAY_UNIT_INPUT.json"
    )
    artifacts: dict[Path, str] = {
        PROFILE_RELATIVE: _render_profile(payload),
        PRODUCTION_RELATIVE: _render_production_adapter(payload),
        OBSERVATION_RELATIVE: _render_observation_adapter(payload),
        MODEL_RELATIVE: _json_text(payload["gameplay_model"]),
        GRAMMAR_RELATIVE: _render_grammar_state(payload),
        LESSONS_RELATIVE: _render_experience_lessons(payload),
        unit_relative: _json_text(_compile_unit_input(payload)),
    }
    hashes = {
        path.as_posix(): _sha256_text(content)
        for path, content in sorted(artifacts.items(), key=lambda item: item[0].as_posix())
    }
    result_payload = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "status": CASE3_READY,
        "project_id": payload["project_id"],
        "source_revision": payload["repository"]["expected_revision"],
        "source_dirty_paths": payload["repository"]["declared_dirty_paths"],
        "source_working_tree_sha256": payload["repository"][
            "working_tree_sha256"
        ],
        "initial_objective_input_path": unit_relative.as_posix(),
        "artifact_sha256": hashes,
        "warnings": warnings,
        "handoff": (
            "Return to gameplay/AGENTS.md. Route OPEN repairs first; otherwise "
            "run Case 3 progression production from the initial objective input."
        ),
    }
    artifacts[RESULT_RELATIVE] = _json_text(result_payload)
    return artifacts


def _prepare_expected(
    game_repo: Path,
    input_path: Path,
) -> tuple[dict[str, Any], dict[Path, str], list[str], list[str]]:
    payload = _load_json_object(input_path, "Case 2 onboarding input")
    errors, warnings, objective_dir = _validate_onboarding_input(payload, game_repo)
    if errors or not objective_dir:
        return payload, {}, errors, warnings
    artifacts = _expected_artifacts(payload, objective_dir, warnings)
    absolute_repo = str(game_repo)
    for relative, content in artifacts.items():
        if "TBD" in content:
            errors.append(f"generated artifact contains TBD: {relative.as_posix()}")
        if absolute_repo in content:
            errors.append(
                f"generated artifact persists absolute game repo path: "
                f"{relative.as_posix()}"
            )
    return payload, artifacts, errors, warnings


def compile_onboarding(
    game_repo_text: str,
    input_text: str,
) -> OnboardingResult:
    """Validate all materials, then create only missing canonical artifacts."""

    game_repo = _resolve_game_repo(game_repo_text)
    input_path = _resolve_cli_owned_path(game_repo, input_text, must_exist=True)
    canonical_input = (game_repo / INPUT_RELATIVE).resolve()
    if input_path != canonical_input:
        raise OnboardingError(f"onboarding input must be {INPUT_RELATIVE.as_posix()}")
    if not input_path.is_file():
        raise OnboardingError(f"onboarding input is not a file: {input_text}")

    payload, artifacts, errors, warnings = _prepare_expected(game_repo, input_path)
    if errors:
        return OnboardingResult(
            BLOCKED_BY_ONBOARDING_MATERIAL, errors=errors, warnings=warnings
        )

    # Resolve and compare every target before creating any directory or file.
    resolved_targets: dict[Path, tuple[Path, str]] = {}
    conflicts: list[str] = []
    for relative, content in artifacts.items():
        target = _resolve_persisted_owned_path(game_repo, relative.as_posix())
        resolved_targets[relative] = (target, content)
        if target.exists():
            if not target.is_file():
                conflicts.append(f"canonical target is not a file: {relative.as_posix()}")
            else:
                existing = target.read_text(encoding="utf-8")
                if existing != content:
                    conflicts.append(
                        "existing factory state differs and will not be overwritten: "
                        + relative.as_posix()
                    )
        elif _is_tracked_path(game_repo, relative):
            conflicts.append(
                "canonical target is tracked but missing from the working tree; "
                "refusing to recreate an intentional deletion: "
                + relative.as_posix()
            )
    if conflicts:
        return OnboardingResult(
            BLOCKED_BY_EXISTING_FACTORY_STATE,
            errors=conflicts,
            warnings=warnings,
        )

    created: list[str] = []
    verified: list[str] = []
    for relative, (target, content) in resolved_targets.items():
        if target.exists():
            verified.append(relative.as_posix())
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        created.append(relative.as_posix())
    return OnboardingResult(
        CASE3_READY,
        warnings=warnings,
        created_paths=sorted(created),
        verified_paths=sorted(verified),
    )


def check_onboarding(
    game_repo_text: str,
    input_text: str,
) -> OnboardingResult:
    """Verify exact generated artifacts and re-run the Case 3 material gate."""

    game_repo = _resolve_game_repo(game_repo_text)
    input_path = _resolve_cli_owned_path(game_repo, input_text, must_exist=True)
    canonical_input = (game_repo / INPUT_RELATIVE).resolve()
    if input_path != canonical_input:
        raise OnboardingError(f"onboarding input must be {INPUT_RELATIVE.as_posix()}")
    payload, artifacts, errors, warnings = _prepare_expected(game_repo, input_path)
    if errors:
        return OnboardingResult(
            BLOCKED_BY_ONBOARDING_MATERIAL, errors=errors, warnings=warnings
        )

    verified: list[str] = []
    for relative, expected in artifacts.items():
        target = _resolve_persisted_owned_path(game_repo, relative.as_posix())
        if not target.exists():
            errors.append(f"generated artifact is missing: {relative.as_posix()}")
            continue
        if not target.is_file():
            errors.append(f"generated artifact is not a file: {relative.as_posix()}")
            continue
        actual = target.read_text(encoding="utf-8")
        if actual != expected:
            errors.append(f"generated artifact is stale or changed: {relative.as_posix()}")
        else:
            verified.append(relative.as_posix())
    if errors:
        return OnboardingResult(
            BLOCKED_BY_ONBOARDING_MATERIAL,
            errors=errors,
            warnings=warnings,
            verified_paths=verified,
        )
    return OnboardingResult(
        CASE3_READY,
        warnings=warnings,
        verified_paths=sorted(verified),
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    probe_parser = subparsers.add_parser("probe")
    probe_parser.add_argument("--game-repo", required=True)
    probe_parser.add_argument("--out", required=True)
    probe_parser.add_argument("--max-candidates", type=int, default=200)

    for command in ("compile", "check"):
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument("--game-repo", required=True)
        command_parser.add_argument("--input", required=True)
    return parser


def _print_result(result: OnboardingResult) -> None:
    print(result.status)
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
        if args.command == "probe":
            result = probe_repository(
                args.game_repo, args.out, max_candidates=args.max_candidates
            )
        elif args.command == "compile":
            result = compile_onboarding(args.game_repo, args.input)
        else:
            result = check_onboarding(args.game_repo, args.input)
    except OnboardingError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    _print_result(result)
    return 0 if result.status in {CASE2_PROBE_READY, ALREADY_CASE3, CASE3_READY} else 2


if __name__ == "__main__":
    raise SystemExit(main())
