#!/usr/bin/env python3
"""Idea Factory exploration recorder, authority validator, and compiler.

The Idea Factory accepts a sparse user seed, references, and/or an early game
repository.  It first preserves an open, non-binding discovery frontier where
incompatibility, several directions, or no answer are all valid.  A Product
Thesis can be compiled only after one direction genuinely emerges and the user
explicitly commissions it.  AI delegation authorizes judgment, not forced
closure.

All filled artifacts land in the game repository.  This factory checkout owns
only the reusable tool, schemas, templates, workflow, and tests.
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


INPUT_SCHEMA_VERSION = "product_thesis_input.v2"
EXPLORATION_SCHEMA_VERSION = "idea_exploration.v1"
PROBE_SCHEMA_VERSION = "idea_factory_repo_probe.v2"
CONSTRAINTS_SCHEMA_VERSION = "factory_constraints.v2"
RESULT_SCHEMA_VERSION = "idea_factory_result.v1"

IDEA_EXPLORATION_REQUIRED = "IDEA_EXPLORATION_REQUIRED"
IDEA_EXPLORATION_OPEN = "IDEA_EXPLORATION_OPEN"
IDEA_REFERENCE_NO_FIT = "IDEA_REFERENCE_NO_FIT"
IDEA_DIRECTIONS_AVAILABLE = "IDEA_DIRECTIONS_AVAILABLE"
IDEA_DIRECTION_EMERGED = "IDEA_DIRECTION_EMERGED"
PRODUCT_DIRECTION_REVIEW_REQUIRED = "PRODUCT_DIRECTION_REVIEW_REQUIRED"
IDEA_FACTORY_READY = "IDEA_FACTORY_READY"
IDEA_FACTORY_ALREADY_READY = "IDEA_FACTORY_ALREADY_READY"
BLOCKED_BY_IDEA_MATERIAL = "BLOCKED_BY_IDEA_MATERIAL"
BLOCKED_BY_EXISTING_PRODUCT_STATE = "BLOCKED_BY_EXISTING_PRODUCT_STATE"

FACTORY_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_RELATIVE = Path("design/product/idea")
PROBE_RELATIVE = WORKSPACE_RELATIVE / "IDEA_FACTORY_REPO_PROBE.json"
EXPLORATION_RELATIVE = WORKSPACE_RELATIVE / "IDEA_EXPLORATION.json"
EXPLORATION_MD_RELATIVE = WORKSPACE_RELATIVE / "IDEA_EXPLORATION.md"
INPUT_RELATIVE = WORKSPACE_RELATIVE / "PRODUCT_THESIS_INPUT.json"
RESULT_RELATIVE = WORKSPACE_RELATIVE / "IDEA_FACTORY_RESULT.json"
THESIS_RELATIVE = Path("design/product/PRODUCT_THESIS.md")
CONSTRAINTS_RELATIVE = Path("design/product/FACTORY_CONSTRAINTS.json")

GENERATED_RELATIVES = {
    PROBE_RELATIVE,
    EXPLORATION_RELATIVE,
    EXPLORATION_MD_RELATIVE,
    INPUT_RELATIVE,
    RESULT_RELATIVE,
    THESIS_RELATIVE,
    CONSTRAINTS_RELATIVE,
}

AUTHORITY_VALUES = {
    "USER_FIXED",
    "REPO_COMMITMENT",
    "AI_RECOMMENDED",
    "AI_DELEGATED",
    "VALIDATION_REQUIRED",
}
BINDING_AUTHORITIES = {"USER_FIXED", "REPO_COMMITMENT", "AI_DELEGATED"}
FACTORY_VALUES = {"all", "gameplay", "story", "asset", "sound", "production"}
EXPLORATION_STATES = {
    "OPEN",
    "REFERENCE_NO_FIT",
    "LIVE_DIRECTIONS",
    "DIRECTION_EMERGED",
}
REFERENCE_RELATIONS = {
    "UNRESOLVED",
    "COMPATIBLE_PRINCIPLE",
    "CONTRADICTION",
    "ANTI_REFERENCE",
    "NO_PRODUCTIVE_RELATION",
}
DIRECTION_DISPOSITIONS = {"LIVE", "REJECTED", "EMERGED"}
ANCHOR_AUTHORITIES = {"USER", "REPO", "REFERENCE", "AI_HYPOTHESIS"}
THESIS_FIELDS = (
    "product_promise",
    "audience_relationship",
    "commercial_shape",
    "experience_intent",
    "retention_or_replay_thesis",
    "differentiation",
    "scope_shape",
)
PROJECT_MARKERS = (
    "project.godot",
    "package.json",
    "Cargo.toml",
    "pyproject.toml",
    "ProjectSettings/ProjectVersion.txt",
    "README.md",
)
CANDIDATE_TERMS = (
    "readme",
    "design",
    "vision",
    "pitch",
    "idea",
    "concept",
    "product",
    "game",
    "roadmap",
    "audience",
    "market",
    "monet",
    "price",
    "retention",
    "emotion",
    "theme",
    "loop",
    "mechanic",
    "progress",
)
TEXT_EXTENSIONS = {".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".csv"}
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


class IdeaFactoryError(ValueError):
    """Raised before a command creates or overwrites an artifact."""


@dataclass
class IdeaFactoryResult:
    status: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    created_paths: list[str] = field(default_factory=list)
    verified_paths: list[str] = field(default_factory=list)
    review_decision_ids: list[str] = field(default_factory=list)


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
        stdout = result.stdout
        if isinstance(stderr, bytes):
            detail = stderr.decode("utf-8", errors="replace").strip()
        else:
            detail = stderr.strip()
        if not detail:
            if isinstance(stdout, bytes):
                detail = stdout.decode("utf-8", errors="replace").strip()
            else:
                detail = stdout.strip()
        raise IdeaFactoryError(f"git {' '.join(args)} failed: {detail}")
    return result.stdout


def _repository_revision(game_repo: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(game_repo), "rev-parse", "--verify", "HEAD"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip() if result.returncode == 0 else "UNBORN_HEAD"


def _repository_branch(game_repo: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(game_repo), "symbolic-ref", "--short", "HEAD"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
    )
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    return "DETACHED_HEAD"


def _resolve_game_repo(raw_path: str) -> Path:
    game_repo = Path(raw_path).expanduser().resolve()
    if not game_repo.is_dir():
        raise IdeaFactoryError(f"game repo does not exist: {game_repo}")
    if game_repo == FACTORY_ROOT or _is_within(game_repo, FACTORY_ROOT):
        raise IdeaFactoryError("game repo must not be this factory repo or a child")
    git_root_text = str(_run_git(game_repo, "rev-parse", "--show-toplevel")).strip()
    if Path(git_root_text).resolve() != game_repo:
        raise IdeaFactoryError(f"game repo must be the Git root, not a child: {game_repo}")
    return game_repo


def _resolve_owned_path(game_repo: Path, raw_path: str, *, must_exist: bool = False) -> Path:
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise IdeaFactoryError("path must be a non-empty string")
    candidate = Path(raw_path).expanduser()
    resolved = candidate.resolve() if candidate.is_absolute() else (game_repo / candidate).resolve()
    if not _is_within(resolved, game_repo):
        raise IdeaFactoryError(f"path escapes game repo: {raw_path}")
    if must_exist and not resolved.exists():
        raise IdeaFactoryError(f"required path does not exist: {raw_path}")
    return resolved


def _resolve_persisted_path(game_repo: Path, raw_path: Any, *, must_exist: bool = False) -> Path:
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise IdeaFactoryError("persisted paths must be non-empty strings")
    if Path(raw_path).expanduser().is_absolute():
        raise IdeaFactoryError(f"persisted path must be game-repo-relative: {raw_path}")
    return _resolve_owned_path(game_repo, raw_path, must_exist=must_exist)


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False) + "\n"


def _load_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise IdeaFactoryError(f"cannot read {label} JSON: {error}") from error
    if not isinstance(value, dict):
        raise IdeaFactoryError(f"{label} JSON must contain an object")
    return value


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _generated_path(relative: str) -> bool:
    path = Path(relative)
    return path in GENERATED_RELATIVES or path.as_posix().startswith(
        WORKSPACE_RELATIVE.as_posix() + "/"
    )


def _dirty_paths(game_repo: Path) -> list[str]:
    text = str(_run_git(game_repo, "status", "--porcelain=v1", "--untracked-files=all"))
    paths: list[str] = []
    for line in text.splitlines():
        if len(line) < 4:
            continue
        raw = line[3:]
        normalized = raw.strip('"')
        if " -> " in normalized:
            normalized = normalized.split(" -> ", 1)[1].strip('"')
        if _generated_path(normalized):
            continue
        paths.append(raw)
    return sorted(paths)


def _working_tree_sha256(game_repo: Path) -> str:
    if _repository_revision(game_repo) == "UNBORN_HEAD":
        tracked_raw = _run_git(game_repo, "ls-files", "--cached", "-z", binary=True)
    else:
        tracked_raw = _run_git(
            game_repo, "diff", "--name-only", "-z", "HEAD", "--", binary=True
        )
    untracked_raw = _run_git(
        game_repo, "ls-files", "--others", "--exclude-standard", "-z", binary=True
    )
    assert isinstance(tracked_raw, bytes) and isinstance(untracked_raw, bytes)
    changed_paths = {
        raw.decode("utf-8", errors="surrogateescape")
        for raw in (*tracked_raw.split(b"\0"), *untracked_raw.split(b"\0"))
        if raw
    }
    selected = sorted(path for path in changed_paths if not _generated_path(path))
    digest = hashlib.sha256()
    for relative in selected:
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
        if any(part in IGNORED_DIRECTORY_NAMES for part in Path(relative).parts):
            continue
        path = (game_repo / relative).resolve()
        if _is_within(path, game_repo) and path.is_file():
            result.append(relative)
    return sorted(set(result))


def _snapshot(game_repo: Path) -> dict[str, Any]:
    return {
        "revision": _repository_revision(game_repo),
        "branch": _repository_branch(game_repo),
        "dirty_paths": _dirty_paths(game_repo),
        "working_tree_sha256": _working_tree_sha256(game_repo),
    }


def _candidate_score(relative: str) -> int:
    lower = relative.lower()
    score = sum(2 for term in CANDIDATE_TERMS if term in lower)
    suffix = Path(relative).suffix.lower()
    if suffix in TEXT_EXTENSIONS:
        score += 2
    if lower in {"readme.md", "game_design.md", "design.md"}:
        score += 5
    if lower.startswith(("design/", "docs/", "doc/")):
        score += 2
    return score


def _canonical_complete(game_repo: Path) -> bool:
    return all((game_repo / path).is_file() for path in (
        INPUT_RELATIVE,
        RESULT_RELATIVE,
        THESIS_RELATIVE,
        CONSTRAINTS_RELATIVE,
    ))


def start_idea_factory(
    game_repo_text: str,
    *,
    max_candidates: int = 120,
    reopen: bool = False,
) -> IdeaFactoryResult:
    game_repo = _resolve_game_repo(game_repo_text)
    had_product_authority = _canonical_complete(game_repo)
    if had_product_authority and not reopen:
        checked = check_product_thesis(
            game_repo_text,
            INPUT_RELATIVE.as_posix(),
            enforce_repository_binding=False,
        )
        if checked.status == IDEA_FACTORY_READY:
            checked.status = IDEA_FACTORY_ALREADY_READY
        return checked
    if not reopen:
        partial = [
            path.as_posix()
            for path in (RESULT_RELATIVE, THESIS_RELATIVE, CONSTRAINTS_RELATIVE)
            if (game_repo / path).exists()
        ]
        if partial:
            return IdeaFactoryResult(
                BLOCKED_BY_EXISTING_PRODUCT_STATE,
                errors=[
                    "partial canonical product state already exists; Idea Factory will not "
                    "overwrite or reinterpret it: " + ", ".join(partial)
                ],
            )
    exploration_path = game_repo / EXPLORATION_RELATIVE
    if exploration_path.is_file():
        markdown_path = game_repo / EXPLORATION_MD_RELATIVE
        if markdown_path.is_file():
            result = check_exploration(
                game_repo_text,
                EXPLORATION_RELATIVE.as_posix(),
            )
        else:
            result = record_exploration(
                game_repo_text,
                EXPLORATION_RELATIVE.as_posix(),
            )
    else:
        result = probe_repository(
            game_repo_text,
            max_candidates=max_candidates,
            refresh_existing=reopen,
        )
    if reopen and had_product_authority:
        result.warnings.append(
            "Existing Product Thesis files are preserved only as the direction under "
            "reconsideration. They are not REPO_COMMITMENT evidence and must not anchor "
            "the reopened answer."
        )
    return result


def probe_repository(
    game_repo_text: str,
    *,
    max_candidates: int = 120,
    refresh_existing: bool = False,
) -> IdeaFactoryResult:
    game_repo = _resolve_game_repo(game_repo_text)
    if max_candidates < 1 or max_candidates > 500:
        raise IdeaFactoryError("max_candidates must be between 1 and 500")
    output_path = (game_repo / PROBE_RELATIVE).resolve()
    files = _repo_files(game_repo)
    candidates = sorted(
        (
            (_candidate_score(relative), relative)
            for relative in files
            if Path(relative).suffix.lower() in TEXT_EXTENSIONS
        ),
        key=lambda item: (-item[0], item[1]),
    )
    candidates = [item for item in candidates if item[0] > 0]
    snapshot = _snapshot(game_repo)
    payload = {
        "schema_version": PROBE_SCHEMA_VERSION,
        "status": IDEA_EXPLORATION_REQUIRED,
        "repository": {
            **snapshot,
            "tracked_or_unignored_file_count": len(files),
            "project_markers": [marker for marker in PROJECT_MARKERS if (game_repo / marker).is_file()],
        },
        "candidate_product_materials": [
            {"path": relative, "score": score}
            for score, relative in candidates[:max_candidates]
        ],
        "candidate_count_before_limit": len(candidates),
        "candidate_limit": max_candidates,
        "interpretation_warning": (
            "Candidates are bounded study hints, not product authority. Existing code may "
            "be exploratory or accidental. Exploration may validly find incompatibility, "
            "several live directions, or no product answer. Do not force a commission."
        ),
    }
    rendered = _json_text(payload)
    if output_path.exists():
        if output_path.read_text(encoding="utf-8") != rendered:
            if refresh_existing:
                output_path.write_text(rendered, encoding="utf-8")
                return IdeaFactoryResult(
                    IDEA_EXPLORATION_REQUIRED,
                    created_paths=[PROBE_RELATIVE.as_posix()],
                    warnings=[
                        "The mechanical probe was explicitly refreshed for a reopened "
                        "exploration; existing product authority was not changed."
                    ],
                )
            raise IdeaFactoryError(
                "Idea Factory probe exists for a different repository snapshot; "
                "preserve intentional work, then explicitly regenerate the probe"
            )
        return IdeaFactoryResult(
            IDEA_EXPLORATION_REQUIRED,
            verified_paths=[PROBE_RELATIVE.as_posix()],
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")
    return IdeaFactoryResult(
        IDEA_EXPLORATION_REQUIRED,
        created_paths=[PROBE_RELATIVE.as_posix()],
    )


def _require_text(value: Any, label: str, errors: list[str]) -> str:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label} must be a non-empty string")
        return ""
    text = value.strip()
    if re.search(r"\b(TBD|TODO|REPLACE_ME)\b", text, flags=re.IGNORECASE):
        errors.append(f"{label} contains an unresolved placeholder")
    return text


def _string_list(
    value: Any,
    label: str,
    errors: list[str],
    *,
    allow_empty: bool = True,
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


def _portable_id(value: Any, label: str, errors: list[str]) -> str:
    text = _require_text(value, label, errors)
    if text and not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", text):
        errors.append(f"{label} must be a portable lowercase id")
    return text


def _validate_evidence_refs(
    game_repo: Path,
    refs: Any,
    label: str,
    errors: list[str],
    *,
    allow_empty: bool,
) -> None:
    if not isinstance(refs, list):
        errors.append(f"{label} must be an array")
        return
    if not refs and not allow_empty:
        errors.append(f"{label} must contain at least one evidence ref")
    for index, ref in enumerate(refs):
        item_label = f"{label}[{index}]"
        if not isinstance(ref, dict):
            errors.append(f"{item_label} must be an object")
            continue
        path_text = _require_text(ref.get("path"), f"{item_label}.path", errors)
        contains = _string_list(
            ref.get("contains"), f"{item_label}.contains", errors, allow_empty=False
        )
        if not path_text:
            continue
        try:
            path = _resolve_persisted_path(game_repo, path_text, must_exist=True)
        except IdeaFactoryError as error:
            errors.append(str(error))
            continue
        if not path.is_file():
            errors.append(f"evidence ref is not a file: {path_text}")
            continue
        try:
            body = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(f"evidence ref is not UTF-8 text: {path_text}")
            continue
        for token in contains:
            if token not in body:
                errors.append(f"evidence token not found in {path_text}: {token}")


def _validate_repository_binding(payload: dict[str, Any], game_repo: Path, errors: list[str]) -> None:
    repository = payload.get("repository")
    if not isinstance(repository, dict):
        errors.append("repository must be an object")
        return
    probe_path = game_repo / PROBE_RELATIVE
    if not probe_path.is_file():
        errors.append(f"missing mechanical probe: {PROBE_RELATIVE.as_posix()}")
        return
    try:
        probe = _load_json_object(probe_path, "Idea Factory repository probe")
    except IdeaFactoryError as error:
        errors.append(str(error))
        return
    if probe.get("schema_version") != PROBE_SCHEMA_VERSION:
        errors.append(f"probe schema_version must be {PROBE_SCHEMA_VERSION}")
    probe_repo = probe.get("repository") if isinstance(probe.get("repository"), dict) else {}
    expected_revision = _require_text(
        repository.get("expected_revision"), "repository.expected_revision", errors
    )
    declared_dirty = _string_list(
        repository.get("declared_dirty_paths"), "repository.declared_dirty_paths", errors
    )
    expected_tree = _require_text(
        repository.get("working_tree_sha256"), "repository.working_tree_sha256", errors
    )
    if expected_revision and expected_revision != probe_repo.get("revision"):
        errors.append("input expected_revision does not match the mechanical probe")
    if declared_dirty != probe_repo.get("dirty_paths"):
        errors.append("input declared_dirty_paths do not match the mechanical probe")
    if expected_tree and expected_tree != probe_repo.get("working_tree_sha256"):
        errors.append("input working_tree_sha256 does not match the mechanical probe")
    current = _snapshot(game_repo)
    if expected_revision and expected_revision != current["revision"]:
        errors.append("repository revision changed after Idea Factory study")
    if declared_dirty != current["dirty_paths"]:
        errors.append("repository dirty paths changed after Idea Factory study")
    if expected_tree and expected_tree != current["working_tree_sha256"]:
        errors.append("repository dirty content changed after Idea Factory study")


def _validate_source_ids(
    raw_ids: Any,
    label: str,
    decision_ids: set[str],
    errors: list[str],
) -> list[str]:
    ids = _string_list(raw_ids, label, errors, allow_empty=False)
    for decision_id in ids:
        if decision_id not in decision_ids:
            errors.append(f"{label} references unknown decision_id: {decision_id}")
    return ids


def _exploration_status(frontier_state: str) -> str:
    return {
        "OPEN": IDEA_EXPLORATION_OPEN,
        "REFERENCE_NO_FIT": IDEA_REFERENCE_NO_FIT,
        "LIVE_DIRECTIONS": IDEA_DIRECTIONS_AVAILABLE,
        "DIRECTION_EMERGED": IDEA_DIRECTION_EMERGED,
    }.get(frontier_state, BLOCKED_BY_IDEA_MATERIAL)


def _validate_exploration_payload(
    payload: dict[str, Any],
    game_repo: Path,
    *,
    enforce_repository_binding: bool = True,
) -> list[str]:
    """Validate non-binding discovery without demanding a product answer."""

    errors: list[str] = []
    if payload.get("schema_version") != EXPLORATION_SCHEMA_VERSION:
        errors.append(f"schema_version must be {EXPLORATION_SCHEMA_VERSION}")
    _portable_id(payload.get("project_id"), "project_id", errors)
    if enforce_repository_binding:
        _validate_repository_binding(payload, game_repo, errors)
    else:
        repository = payload.get("repository")
        if not isinstance(repository, dict):
            errors.append("repository must be an object")
        else:
            _require_text(
                repository.get("expected_revision"),
                "repository.expected_revision",
                errors,
            )
            _string_list(
                repository.get("declared_dirty_paths"),
                "repository.declared_dirty_paths",
                errors,
            )
            working_tree_sha = _require_text(
                repository.get("working_tree_sha256"),
                "repository.working_tree_sha256",
                errors,
            )
            if working_tree_sha and not re.fullmatch(r"[0-9a-f]{64}", working_tree_sha):
                errors.append("repository.working_tree_sha256 must be a SHA-256")

    seed = payload.get("seed")
    reference_ids: set[str] = set()
    if not isinstance(seed, dict):
        errors.append("seed must be an object")
    else:
        _require_text(seed.get("user_request"), "seed.user_request", errors)
        references = seed.get("references")
        if not isinstance(references, list):
            errors.append("seed.references must be an array")
            references = []
        for index, reference in enumerate(references):
            label = f"seed.references[{index}]"
            if not isinstance(reference, dict):
                errors.append(f"{label} must be an object")
                continue
            reference_id = _portable_id(
                reference.get("reference_id"), f"{label}.reference_id", errors
            )
            if reference_id in reference_ids:
                errors.append(f"duplicate reference_id: {reference_id}")
            if reference_id:
                reference_ids.add(reference_id)
            _require_text(
                reference.get("user_instruction"),
                f"{label}.user_instruction",
                errors,
            )
            _string_list(
                reference.get("source_urls"),
                f"{label}.source_urls",
                errors,
            )

    anchors = payload.get("anchors")
    if not isinstance(anchors, list):
        errors.append("anchors must be an array")
        anchors = []
    anchor_ids: set[str] = set()
    for index, anchor in enumerate(anchors):
        label = f"anchors[{index}]"
        if not isinstance(anchor, dict):
            errors.append(f"{label} must be an object")
            continue
        anchor_id = _portable_id(anchor.get("anchor_id"), f"{label}.anchor_id", errors)
        if anchor_id in anchor_ids:
            errors.append(f"duplicate anchor_id: {anchor_id}")
        if anchor_id:
            anchor_ids.add(anchor_id)
        _require_text(anchor.get("statement"), f"{label}.statement", errors)
        authority = anchor.get("authority")
        if authority not in ANCHOR_AUTHORITIES:
            errors.append(f"{label}.authority has an unsupported value")
        source_quote = anchor.get("source_quote", "")
        evidence_refs = anchor.get("evidence_refs", [])
        source_urls = anchor.get("source_urls", [])
        if authority == "USER":
            _require_text(source_quote, f"{label}.source_quote", errors)
        if authority == "REPO":
            _validate_evidence_refs(
                game_repo,
                evidence_refs,
                f"{label}.evidence_refs",
                errors,
                allow_empty=False,
            )
        else:
            _validate_evidence_refs(
                game_repo,
                evidence_refs,
                f"{label}.evidence_refs",
                errors,
                allow_empty=True,
            )
        urls = _string_list(source_urls, f"{label}.source_urls", errors)
        if authority == "REFERENCE" and not urls and not source_quote:
            errors.append(
                f"{label} must identify reference evidence with source_quote or source_urls"
            )

    relations = payload.get("reference_relations")
    if not isinstance(relations, list):
        errors.append("reference_relations must be an array")
        relations = []
    relation_ids: set[str] = set()
    no_fit_relation = False
    for index, relation in enumerate(relations):
        label = f"reference_relations[{index}]"
        if not isinstance(relation, dict):
            errors.append(f"{label} must be an object")
            continue
        reference_id = _portable_id(
            relation.get("reference_id"), f"{label}.reference_id", errors
        )
        if reference_id in relation_ids:
            errors.append(f"duplicate reference relation: {reference_id}")
        if reference_id:
            relation_ids.add(reference_id)
        if reference_id and reference_id not in reference_ids:
            errors.append(f"{label} references an unknown seed reference: {reference_id}")
        relation_value = relation.get("relation")
        if relation_value not in REFERENCE_RELATIONS:
            errors.append(f"{label}.relation has an unsupported value")
        if relation_value in {"CONTRADICTION", "NO_PRODUCTIVE_RELATION"}:
            no_fit_relation = True
        _require_text(relation.get("explanation"), f"{label}.explanation", errors)

    directions = payload.get("directions")
    if not isinstance(directions, list):
        errors.append("directions must be an array")
        directions = []
    direction_ids: set[str] = set()
    emerged_ids: list[str] = []
    live_count = 0
    for index, direction in enumerate(directions):
        label = f"directions[{index}]"
        if not isinstance(direction, dict):
            errors.append(f"{label} must be an object")
            continue
        direction_id = _portable_id(
            direction.get("direction_id"), f"{label}.direction_id", errors
        )
        if direction_id in direction_ids:
            errors.append(f"duplicate direction_id: {direction_id}")
        if direction_id:
            direction_ids.add(direction_id)
        disposition = direction.get("disposition")
        if disposition not in DIRECTION_DISPOSITIONS:
            errors.append(f"{label}.disposition has an unsupported value")
        if disposition in {"LIVE", "EMERGED"}:
            live_count += 1
        if disposition == "EMERGED" and direction_id:
            emerged_ids.append(direction_id)
        _require_text(direction.get("proposition"), f"{label}.proposition", errors)
        _require_text(direction.get("why_live"), f"{label}.why_live", errors)
        _string_list(direction.get("tensions"), f"{label}.tensions", errors)

    frontier_state = payload.get("frontier_state")
    if frontier_state not in EXPLORATION_STATES:
        errors.append("frontier_state has an unsupported value")
        frontier_state = ""
    _require_text(payload.get("frontier_summary"), "frontier_summary", errors)
    _string_list(payload.get("open_questions"), "open_questions", errors)
    _require_text(payload.get("next_move"), "next_move", errors)
    assumptions = _string_list(payload.get("ai_assumptions"), "ai_assumptions", errors)
    if assumptions:
        errors.append(
            "ai_assumptions must be empty; record uncertain ideas as AI_HYPOTHESIS "
            "anchors or open tensions"
        )

    if frontier_state == "REFERENCE_NO_FIT" and not no_fit_relation:
        errors.append(
            "REFERENCE_NO_FIT requires a CONTRADICTION or NO_PRODUCTIVE_RELATION"
        )
    if frontier_state == "LIVE_DIRECTIONS" and live_count < 1:
        errors.append("LIVE_DIRECTIONS requires at least one live direction")
    if frontier_state == "DIRECTION_EMERGED" and len(emerged_ids) != 1:
        errors.append("DIRECTION_EMERGED requires exactly one EMERGED direction")
    if frontier_state != "DIRECTION_EMERGED" and emerged_ids:
        errors.append("an EMERGED direction requires frontier_state DIRECTION_EMERGED")
    return errors


def _render_exploration(payload: dict[str, Any]) -> str:
    sections = [
        "# Idea Exploration",
        "",
        f"Project: `{payload['project_id']}`",
        f"Frontier state: `{payload['frontier_state']}`",
        "",
        "> This is non-binding discovery material. It may record incompatibility,",
        "> uncertainty, or several live directions. It is not a Product Thesis.",
        "",
        "## Current frontier",
        "",
        payload["frontier_summary"],
        "",
    ]
    references = payload["reference_relations"]
    if references:
        sections.extend(["## Reference relationships", ""])
        for item in references:
            sections.append(
                f"- **`{item['reference_id']}` — `{item['relation']}`:** "
                f"{item['explanation']}"
            )
        sections.append("")
    sections.extend(["## Anchors and hypotheses", ""])
    if payload["anchors"]:
        for item in payload["anchors"]:
            sections.append(
                f"- **`{item['anchor_id']}` — `{item['authority']}`:** "
                f"{item['statement']}"
            )
    else:
        sections.append("No additional anchors recorded.")
    sections.extend(["", "## Directions", ""])
    if payload["directions"]:
        for item in payload["directions"]:
            sections.extend(
                [
                    f"### `{item['direction_id']}` — `{item['disposition']}`",
                    "",
                    item["proposition"],
                    "",
                    f"Why it remains in view: {item['why_live']}",
                    "",
                    "Tensions:",
                    *([f"- {value}" for value in item["tensions"]] or ["- None recorded."]),
                    "",
                ]
            )
    else:
        sections.extend(
            [
                "No direction is required at this frontier. Absence is a valid result.",
                "",
            ]
        )
    sections.extend(["## Open questions", ""])
    sections.extend(
        [f"- {value}" for value in payload["open_questions"]]
        or ["No question is currently required."]
    )
    sections.extend(["", "## Next exploration move", "", payload["next_move"], ""])
    return "\n".join(sections).rstrip() + "\n"


def record_exploration(game_repo_text: str, input_text: str) -> IdeaFactoryResult:
    game_repo = _resolve_game_repo(game_repo_text)
    input_path = _resolve_owned_path(game_repo, input_text, must_exist=True)
    if input_path != (game_repo / EXPLORATION_RELATIVE).resolve():
        raise IdeaFactoryError(f"exploration input must be {EXPLORATION_RELATIVE.as_posix()}")
    payload = _load_json_object(input_path, "Idea exploration")
    errors = _validate_exploration_payload(payload, game_repo)
    if errors:
        return IdeaFactoryResult(BLOCKED_BY_IDEA_MATERIAL, errors=errors)
    rendered = _render_exploration(payload)
    target = game_repo / EXPLORATION_MD_RELATIVE
    created: list[str] = []
    verified: list[str] = []
    warnings: list[str] = []
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding="utf-8")
        created.append(EXPLORATION_MD_RELATIVE.as_posix())
    elif target.read_text(encoding="utf-8") == rendered:
        verified.append(EXPLORATION_MD_RELATIVE.as_posix())
    else:
        target.write_text(rendered, encoding="utf-8")
        created.append(EXPLORATION_MD_RELATIVE.as_posix())
        warnings.append(
            "Updated the derived non-binding exploration view; product authority was untouched."
        )
    return IdeaFactoryResult(
        _exploration_status(payload["frontier_state"]),
        warnings=warnings,
        created_paths=created,
        verified_paths=verified,
    )


def check_exploration(game_repo_text: str, input_text: str) -> IdeaFactoryResult:
    game_repo = _resolve_game_repo(game_repo_text)
    input_path = _resolve_owned_path(game_repo, input_text, must_exist=True)
    if input_path != (game_repo / EXPLORATION_RELATIVE).resolve():
        raise IdeaFactoryError(f"exploration input must be {EXPLORATION_RELATIVE.as_posix()}")
    payload = _load_json_object(input_path, "Idea exploration")
    errors = _validate_exploration_payload(payload, game_repo)
    if errors:
        return IdeaFactoryResult(BLOCKED_BY_IDEA_MATERIAL, errors=errors)
    target = game_repo / EXPLORATION_MD_RELATIVE
    expected = _render_exploration(payload)
    if not target.is_file():
        errors.append(f"missing generated artifact: {EXPLORATION_MD_RELATIVE.as_posix()}")
    elif target.read_text(encoding="utf-8") != expected:
        errors.append(
            f"generated artifact is stale or changed: {EXPLORATION_MD_RELATIVE.as_posix()}"
        )
    if errors:
        return IdeaFactoryResult(BLOCKED_BY_IDEA_MATERIAL, errors=errors)
    return IdeaFactoryResult(
        _exploration_status(payload["frontier_state"]),
        verified_paths=[EXPLORATION_MD_RELATIVE.as_posix()],
    )


def _validate_commission_gate(
    payload: dict[str, Any],
    game_repo: Path,
    errors: list[str],
    *,
    enforce_repository_binding: bool,
) -> None:
    commission = payload.get("commission")
    if not isinstance(commission, dict):
        errors.append("commission must be an object")
        return
    authorized = commission.get("authorized")
    if authorized is not True:
        errors.append(
            "commission.authorized must be true; exploration and AI delegation do not "
            "by themselves authorize a Product Thesis"
        )
    _require_text(
        commission.get("authorization_quote"),
        "commission.authorization_quote",
        errors,
    )
    selected_direction_id = _portable_id(
        commission.get("selected_direction_id"),
        "commission.selected_direction_id",
        errors,
    )
    path_text = _require_text(
        commission.get("exploration_path"),
        "commission.exploration_path",
        errors,
    )
    expected_sha = _require_text(
        commission.get("exploration_sha256"),
        "commission.exploration_sha256",
        errors,
    )
    if expected_sha and not re.fullmatch(r"[0-9a-f]{64}", expected_sha):
        errors.append("commission.exploration_sha256 must be a SHA-256")
    if not path_text:
        return
    try:
        exploration_path = _resolve_persisted_path(
            game_repo,
            path_text,
            must_exist=True,
        )
    except IdeaFactoryError as error:
        errors.append(str(error))
        return
    if exploration_path != (game_repo / EXPLORATION_RELATIVE).resolve():
        errors.append(f"commission.exploration_path must be {EXPLORATION_RELATIVE.as_posix()}")
        return
    raw_exploration = exploration_path.read_text(encoding="utf-8")
    if expected_sha and _sha256_text(raw_exploration) != expected_sha:
        errors.append("commission.exploration_sha256 does not match the selected exploration")
    try:
        exploration = _load_json_object(exploration_path, "Idea exploration")
    except IdeaFactoryError as error:
        errors.append(str(error))
        return
    exploration_errors = _validate_exploration_payload(
        exploration,
        game_repo,
        enforce_repository_binding=enforce_repository_binding,
    )
    errors.extend(exploration_errors)
    exploration_view = game_repo / EXPLORATION_MD_RELATIVE
    if not exploration_view.is_file():
        errors.append(
            f"commission requires checked exploration view: {EXPLORATION_MD_RELATIVE.as_posix()}"
        )
    elif not exploration_errors and exploration_view.read_text(
        encoding="utf-8"
    ) != _render_exploration(exploration):
        errors.append("commission exploration view is stale or changed")
    if exploration.get("frontier_state") != "DIRECTION_EMERGED":
        errors.append(
            "commission requires an exploration whose frontier_state is DIRECTION_EMERGED"
        )
    selected = [
        item
        for item in exploration.get("directions", [])
        if isinstance(item, dict)
        and item.get("direction_id") == selected_direction_id
        and item.get("disposition") == "EMERGED"
    ]
    if selected_direction_id and len(selected) != 1:
        errors.append(
            "commission.selected_direction_id must identify the one EMERGED direction"
        )
    product_repository = payload.get("repository")
    exploration_repository = exploration.get("repository")
    if isinstance(product_repository, dict) and isinstance(exploration_repository, dict):
        for key in ("expected_revision", "declared_dirty_paths", "working_tree_sha256"):
            if product_repository.get(key) != exploration_repository.get(key):
                errors.append(f"product repository.{key} does not match the exploration")


def _validate_payload(
    payload: dict[str, Any],
    game_repo: Path,
    *,
    enforce_repository_binding: bool = True,
) -> tuple[list[str], list[str], dict[str, dict[str, Any]]]:
    errors: list[str] = []
    review_ids: list[str] = []
    decisions_by_id: dict[str, dict[str, Any]] = {}
    if payload.get("schema_version") != INPUT_SCHEMA_VERSION:
        errors.append(f"schema_version must be {INPUT_SCHEMA_VERSION}")
    _portable_id(payload.get("project_id"), "project_id", errors)
    if enforce_repository_binding:
        _validate_repository_binding(payload, game_repo, errors)
    else:
        repository = payload.get("repository")
        if not isinstance(repository, dict):
            errors.append("repository must be an object")
        else:
            _require_text(
                repository.get("expected_revision"),
                "repository.expected_revision",
                errors,
            )
            _string_list(
                repository.get("declared_dirty_paths"),
                "repository.declared_dirty_paths",
                errors,
            )
            working_tree_sha = _require_text(
                repository.get("working_tree_sha256"),
                "repository.working_tree_sha256",
                errors,
            )
            if working_tree_sha and not re.fullmatch(r"[0-9a-f]{64}", working_tree_sha):
                errors.append("repository.working_tree_sha256 must be a SHA-256")

    _validate_commission_gate(
        payload,
        game_repo,
        errors,
        enforce_repository_binding=enforce_repository_binding,
    )

    seed = payload.get("seed")
    if not isinstance(seed, dict):
        errors.append("seed must be an object")
    else:
        _require_text(seed.get("user_seed"), "seed.user_seed", errors)
        _validate_evidence_refs(
            game_repo,
            seed.get("existing_material_refs", []),
            "seed.existing_material_refs",
            errors,
            allow_empty=True,
        )

    delegation = payload.get("delegation")
    if not isinstance(delegation, dict):
        errors.append("delegation must be an object")
        delegation = {}
    delegated = delegation.get("authorized")
    if not isinstance(delegated, bool):
        errors.append("delegation.authorized must be a boolean")
        delegated = False
    authorization_quote = delegation.get("authorization_quote", "")
    if delegated:
        _require_text(authorization_quote, "delegation.authorization_quote", errors)
    elif authorization_quote:
        errors.append("delegation.authorization_quote must be empty when not authorized")
    delegation_scope = _string_list(
        delegation.get("scope_decision_ids", []),
        "delegation.scope_decision_ids",
        errors,
    )

    decisions = payload.get("decisions")
    if not isinstance(decisions, list) or not decisions:
        errors.append("decisions must contain at least one decision")
        decisions = []
    for index, decision in enumerate(decisions):
        label = f"decisions[{index}]"
        if not isinstance(decision, dict):
            errors.append(f"{label} must be an object")
            continue
        decision_id = _portable_id(decision.get("decision_id"), f"{label}.decision_id", errors)
        if decision_id in decisions_by_id:
            errors.append(f"duplicate decision_id: {decision_id}")
        elif decision_id:
            decisions_by_id[decision_id] = decision
        _require_text(decision.get("topic"), f"{label}.topic", errors)
        _require_text(decision.get("question"), f"{label}.question", errors)
        _require_text(decision.get("decision"), f"{label}.decision", errors)
        _require_text(decision.get("rationale"), f"{label}.rationale", errors)
        authority = decision.get("authority")
        if authority not in AUTHORITY_VALUES:
            errors.append(f"{label}.authority has an unsupported value")
        material = decision.get("material_to_downstream")
        if not isinstance(material, bool):
            errors.append(f"{label}.material_to_downstream must be a boolean")
            material = False
        source_quote = decision.get("source_quote", "")
        evidence_refs = decision.get("evidence_refs", [])
        if authority == "USER_FIXED":
            _require_text(source_quote, f"{label}.source_quote", errors)
            _validate_evidence_refs(
                game_repo, evidence_refs, f"{label}.evidence_refs", errors, allow_empty=True
            )
        elif authority == "REPO_COMMITMENT":
            if source_quote:
                errors.append(f"{label}.source_quote must be empty for REPO_COMMITMENT")
            _validate_evidence_refs(
                game_repo, evidence_refs, f"{label}.evidence_refs", errors, allow_empty=False
            )
        elif authority == "AI_DELEGATED":
            if not delegated:
                errors.append(f"{label} uses AI_DELEGATED without explicit delegation")
            if decision_id and "*" not in delegation_scope and decision_id not in delegation_scope:
                errors.append(f"{label} is outside delegation.scope_decision_ids")
            _validate_evidence_refs(
                game_repo, evidence_refs, f"{label}.evidence_refs", errors, allow_empty=True
            )
        else:
            _validate_evidence_refs(
                game_repo, evidence_refs, f"{label}.evidence_refs", errors, allow_empty=True
            )
        if authority == "AI_RECOMMENDED" and material and decision_id:
            review_ids.append(decision_id)
        if authority == "VALIDATION_REQUIRED" and material:
            errors.append(f"{label} cannot be both VALIDATION_REQUIRED and downstream-binding")
        alternatives = decision.get("alternatives_considered")
        _string_list(alternatives, f"{label}.alternatives_considered", errors)

    decision_ids = set(decisions_by_id)
    for scoped_id in delegation_scope:
        if scoped_id != "*" and scoped_id not in decision_ids:
            errors.append(
                "delegation.scope_decision_ids references unknown decision_id: "
                + scoped_id
            )

    def binding_source_ids(raw_ids: Any, label: str) -> list[str]:
        ids = _validate_source_ids(raw_ids, label, decision_ids, errors)
        for source_id in ids:
            decision = decisions_by_id.get(source_id, {})
            authority = decision.get("authority")
            if decision.get("material_to_downstream") is not True:
                errors.append(
                    f"{label} cites {source_id}, which must be marked "
                    "material_to_downstream"
                )
            if authority == "AI_RECOMMENDED":
                review_ids.append(source_id)
            elif authority not in BINDING_AUTHORITIES:
                errors.append(
                    f"{label} cites non-binding decision {source_id}; uncertain claims "
                    "belong in validation_hypotheses"
                )
        return ids

    thesis = payload.get("product_thesis")
    if not isinstance(thesis, dict):
        errors.append("product_thesis must be an object")
        thesis = {}
    for field_name in THESIS_FIELDS:
        block = thesis.get(field_name)
        label = f"product_thesis.{field_name}"
        if not isinstance(block, dict):
            errors.append(f"{label} must be an object")
            continue
        _require_text(block.get("statement"), f"{label}.statement", errors)
        binding_source_ids(
            block.get("source_decision_ids"),
            f"{label}.source_decision_ids",
        )

    causal_links = payload.get("causal_links")
    if not isinstance(causal_links, list) or not causal_links:
        errors.append("causal_links must contain at least one complete product causal link")
        causal_links = []
    seen_link_ids: set[str] = set()
    for index, link in enumerate(causal_links):
        label = f"causal_links[{index}]"
        if not isinstance(link, dict):
            errors.append(f"{label} must be an object")
            continue
        link_id = _portable_id(link.get("link_id"), f"{label}.link_id", errors)
        if link_id in seen_link_ids:
            errors.append(f"duplicate link_id: {link_id}")
        seen_link_ids.add(link_id)
        for field_name in ("desired_outcome", "player_reason", "experience_mechanism"):
            _require_text(link.get(field_name), f"{label}.{field_name}", errors)
        _string_list(
            link.get("downstream_implications"),
            f"{label}.downstream_implications",
            errors,
            allow_empty=False,
        )
        _string_list(link.get("forbidden_proxies"), f"{label}.forbidden_proxies", errors)
        binding_source_ids(
            link.get("source_decision_ids"),
            f"{label}.source_decision_ids",
        )

    non_goals = payload.get("non_goals")
    if not isinstance(non_goals, list) or not non_goals:
        errors.append("non_goals must contain at least one explicit sacrifice or exclusion")
        non_goals = []
    for index, item in enumerate(non_goals):
        label = f"non_goals[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object")
            continue
        _portable_id(item.get("non_goal_id"), f"{label}.non_goal_id", errors)
        _require_text(item.get("statement"), f"{label}.statement", errors)
        _require_text(item.get("reason"), f"{label}.reason", errors)
        binding_source_ids(
            item.get("source_decision_ids"),
            f"{label}.source_decision_ids",
        )

    hypotheses = payload.get("validation_hypotheses")
    if not isinstance(hypotheses, list):
        errors.append("validation_hypotheses must be an array")
        hypotheses = []
    for index, item in enumerate(hypotheses):
        label = f"validation_hypotheses[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object")
            continue
        _portable_id(item.get("hypothesis_id"), f"{label}.hypothesis_id", errors)
        for field_name in ("hypothesis", "why_uncertain", "falsification_signal", "cheapest_test"):
            _require_text(item.get(field_name), f"{label}.{field_name}", errors)
        _validate_source_ids(
            item.get("source_decision_ids"),
            f"{label}.source_decision_ids",
            decision_ids,
            errors,
        )

    constraints = payload.get("factory_constraints")
    if not isinstance(constraints, list) or not constraints:
        errors.append("factory_constraints must contain at least one downstream constraint")
        constraints = []
    seen_constraint_ids: set[str] = set()
    for index, item in enumerate(constraints):
        label = f"factory_constraints[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object")
            continue
        constraint_id = _portable_id(item.get("constraint_id"), f"{label}.constraint_id", errors)
        if constraint_id in seen_constraint_ids:
            errors.append(f"duplicate constraint_id: {constraint_id}")
        seen_constraint_ids.add(constraint_id)
        factories = _string_list(
            item.get("factories"), f"{label}.factories", errors, allow_empty=False
        )
        for factory in factories:
            if factory not in FACTORY_VALUES:
                errors.append(f"{label}.factories contains unsupported factory: {factory}")
        _require_text(item.get("requirement"), f"{label}.requirement", errors)
        _require_text(item.get("rationale"), f"{label}.rationale", errors)
        binding_source_ids(
            item.get("source_decision_ids"),
            f"{label}.source_decision_ids",
        )

    unresolved = _string_list(
        payload.get("unresolved_material_questions"),
        "unresolved_material_questions",
        errors,
    )
    assumptions = _string_list(payload.get("ai_assumptions"), "ai_assumptions", errors)
    if unresolved:
        review_ids.extend(f"unresolved:{index + 1}" for index in range(len(unresolved)))
    if assumptions:
        errors.append("ai_assumptions must be empty; convert each to a recommendation, delegated decision, or validation hypothesis")
    return errors, sorted(set(review_ids)), decisions_by_id


def _decision_authority_table(decisions: list[dict[str, Any]]) -> str:
    rows = ["| Decision | Topic | Authority | Decision |", "| --- | --- | --- | --- |"]
    for item in decisions:
        rows.append(
            "| `{}` | {} | `{}` | {} |".format(
                item.get("decision_id", ""),
                str(item.get("topic", "")).replace("|", "\\|"),
                item.get("authority", ""),
                str(item.get("decision", "")).replace("|", "\\|"),
            )
        )
    return "\n".join(rows)


def _render_product_thesis(payload: dict[str, Any]) -> str:
    thesis = payload["product_thesis"]
    headings = {
        "product_promise": "Product promise",
        "audience_relationship": "Audience relationship",
        "commercial_shape": "Commercial shape",
        "experience_intent": "Experience and expression intent",
        "retention_or_replay_thesis": "Retention / replay thesis",
        "differentiation": "Differentiation",
        "scope_shape": "Scope shape",
    }
    sections = [
        "# Product Thesis",
        "",
        f"Project: `{payload['project_id']}`",
        "",
        "> This is product authority compiled by Idea Factory. Decisions retain",
        "> explicit provenance; validation hypotheses are not promises or facts.",
        "",
    ]
    for key in THESIS_FIELDS:
        block = thesis[key]
        source_text = ", ".join(f"`{item}`" for item in block["source_decision_ids"])
        sections.extend(
            [f"## {headings[key]}", "", block["statement"], "", f"Sources: {source_text}", ""]
        )
    sections.extend(["## Product causal thesis", ""])
    for link in payload["causal_links"]:
        sections.extend(
            [
                f"### `{link['link_id']}`",
                "",
                f"- **Desired outcome:** {link['desired_outcome']}",
                f"- **Why the player would care or return:** {link['player_reason']}",
                f"- **Experience mechanism:** {link['experience_mechanism']}",
                "- **Downstream implications:**",
                *[f"  - {item}" for item in link["downstream_implications"]],
                "- **Forbidden proxy substitutions:**",
                *([f"  - {item}" for item in link["forbidden_proxies"]] or ["  - None declared."]),
                "",
            ]
        )
    sections.extend(["## Deliberate sacrifices and non-goals", ""])
    for item in payload["non_goals"]:
        sections.append(f"- **`{item['non_goal_id']}` — {item['statement']}** {item['reason']}")
    sections.extend(["", "## Validation hypotheses", ""])
    if payload["validation_hypotheses"]:
        for item in payload["validation_hypotheses"]:
            sections.extend(
                [
                    f"### `{item['hypothesis_id']}`",
                    "",
                    f"- **Hypothesis:** {item['hypothesis']}",
                    f"- **Why uncertain:** {item['why_uncertain']}",
                    f"- **Falsification signal:** {item['falsification_signal']}",
                    f"- **Cheapest test:** {item['cheapest_test']}",
                    "",
                ]
            )
    else:
        sections.extend(["No validation hypotheses declared.", ""])
    sections.extend(
        [
            "## Decision provenance",
            "",
            _decision_authority_table(payload["decisions"]),
            "",
            "## Producer reasoning and alternatives",
            "",
        ]
    )
    for item in payload["decisions"]:
        alternatives = item["alternatives_considered"]
        evidence = item["evidence_refs"]
        sections.extend(
            [
                f"### `{item['decision_id']}`",
                "",
                f"- **Question:** {item['question']}",
                f"- **Decision:** {item['decision']}",
                f"- **Why:** {item['rationale']}",
                f"- **Authority:** `{item['authority']}`",
                f"- **User source quote:** {item['source_quote'] or 'none'}",
                "- **Alternatives considered:**",
                *([f"  - {alternative}" for alternative in alternatives] or ["  - None declared."]),
                "- **Repository evidence:**",
                *(
                    [
                        "  - `{}` containing {}".format(
                            ref["path"],
                            ", ".join(f"`{token}`" for token in ref["contains"]),
                        )
                        for ref in evidence
                    ]
                    or ["  - None; this decision is not claimed as a repository commitment."]
                ),
                "",
            ]
        )
    sections.extend(
        [
            "## Commission gate",
            "",
            f"- Exploration: `{payload['commission']['exploration_path']}`",
            f"- Selected direction: `{payload['commission']['selected_direction_id']}`",
            f"- Authorization text: {payload['commission']['authorization_quote']}",
            "",
            "## Delegation record",
            "",
            f"- Authorized: `{str(payload['delegation']['authorized']).lower()}`",
            f"- Scope: {', '.join(payload['delegation']['scope_decision_ids']) or 'none'}",
            f"- Authorization text: {payload['delegation']['authorization_quote'] or 'none'}",
            "",
        ]
    )
    return "\n".join(sections).rstrip() + "\n"


def _render_constraints(payload: dict[str, Any], input_sha256: str) -> str:
    decisions = {
        item["decision_id"]: {
            "authority": item["authority"],
            "topic": item["topic"],
        }
        for item in payload["decisions"]
    }
    value = {
        "schema_version": CONSTRAINTS_SCHEMA_VERSION,
        "project_id": payload["project_id"],
        "source_input_path": INPUT_RELATIVE.as_posix(),
        "source_input_sha256": input_sha256,
        "product_thesis_path": THESIS_RELATIVE.as_posix(),
        "constraints": payload["factory_constraints"],
        "non_goals": payload["non_goals"],
        "validation_hypotheses": payload["validation_hypotheses"],
        "decision_authority_index": decisions,
        "consumer_rule": (
            "Factories must obey applicable constraints and preserve every non-goal. "
            "Non-goals may bound a mechanic but may not silently erase a declared product "
            "causal or reward loop. Validation hypotheses are uncertain tests, not binding "
            "product facts. A contradiction returns to Idea Factory."
        ),
    }
    return _json_text(value)


def _expected_outputs(payload: dict[str, Any], input_text: str) -> dict[Path, str]:
    input_sha = _sha256_text(input_text)
    thesis = _render_product_thesis(payload)
    constraints = _render_constraints(payload, input_sha)
    revision = payload["repository"]["expected_revision"]
    result_value = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "status": IDEA_FACTORY_READY,
        "project_id": payload["project_id"],
        "repository_revision": revision,
        "source_input_path": INPUT_RELATIVE.as_posix(),
        "source_input_sha256": input_sha,
        "generated_artifacts": [
            {"path": THESIS_RELATIVE.as_posix(), "sha256": _sha256_text(thesis)},
            {"path": CONSTRAINTS_RELATIVE.as_posix(), "sha256": _sha256_text(constraints)},
        ],
    }
    return {
        THESIS_RELATIVE: thesis,
        CONSTRAINTS_RELATIVE: constraints,
        RESULT_RELATIVE: _json_text(result_value),
    }


def compile_product_thesis(game_repo_text: str, input_text: str) -> IdeaFactoryResult:
    game_repo = _resolve_game_repo(game_repo_text)
    input_path = _resolve_owned_path(game_repo, input_text, must_exist=True)
    if input_path != (game_repo / INPUT_RELATIVE).resolve():
        raise IdeaFactoryError(f"input must be {INPUT_RELATIVE.as_posix()}")
    raw_input = input_path.read_text(encoding="utf-8")
    payload = _load_json_object(input_path, "Product Thesis input")
    errors, review_ids, _ = _validate_payload(payload, game_repo)
    if errors:
        return IdeaFactoryResult(BLOCKED_BY_IDEA_MATERIAL, errors=errors)
    if review_ids:
        return IdeaFactoryResult(
            PRODUCT_DIRECTION_REVIEW_REQUIRED,
            warnings=[
                "One complete AI producer recommendation exists, but these material "
                "decisions are not yet user-fixed or explicitly delegated. Present the "
                "recommendation in plain language and ask only the smallest decisive questions."
            ],
            review_decision_ids=review_ids,
        )
    outputs = _expected_outputs(payload, raw_input)
    differing = [
        relative.as_posix()
        for relative, expected in outputs.items()
        if (game_repo / relative).exists()
        and (game_repo / relative).read_text(encoding="utf-8") != expected
    ]
    if differing:
        return IdeaFactoryResult(
            BLOCKED_BY_EXISTING_PRODUCT_STATE,
            errors=[
                "canonical product state differs from the compiled input; no artifact was "
                "written: " + ", ".join(differing)
            ],
        )
    created: list[str] = []
    verified: list[str] = []
    for relative, expected in outputs.items():
        target = game_repo / relative
        if target.exists():
            verified.append(relative.as_posix())
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(expected, encoding="utf-8")
        created.append(relative.as_posix())
    return IdeaFactoryResult(
        IDEA_FACTORY_READY,
        created_paths=created,
        verified_paths=verified,
    )


def check_product_thesis(
    game_repo_text: str,
    input_text: str,
    *,
    enforce_repository_binding: bool = True,
) -> IdeaFactoryResult:
    game_repo = _resolve_game_repo(game_repo_text)
    input_path = _resolve_owned_path(game_repo, input_text, must_exist=True)
    if input_path != (game_repo / INPUT_RELATIVE).resolve():
        raise IdeaFactoryError(f"input must be {INPUT_RELATIVE.as_posix()}")
    raw_input = input_path.read_text(encoding="utf-8")
    payload = _load_json_object(input_path, "Product Thesis input")
    errors, review_ids, _ = _validate_payload(
        payload,
        game_repo,
        enforce_repository_binding=enforce_repository_binding,
    )
    if errors:
        return IdeaFactoryResult(BLOCKED_BY_IDEA_MATERIAL, errors=errors)
    if review_ids:
        return IdeaFactoryResult(
            PRODUCT_DIRECTION_REVIEW_REQUIRED,
            review_decision_ids=review_ids,
        )
    expected = _expected_outputs(payload, raw_input)
    verified: list[str] = []
    for relative, expected_text in expected.items():
        target = game_repo / relative
        if not target.is_file():
            errors.append(f"missing generated artifact: {relative.as_posix()}")
        elif target.read_text(encoding="utf-8") != expected_text:
            errors.append(f"generated artifact is stale or changed: {relative.as_posix()}")
        else:
            verified.append(relative.as_posix())
    if errors:
        return IdeaFactoryResult(
            BLOCKED_BY_IDEA_MATERIAL,
            errors=errors,
            verified_paths=verified,
        )
    return IdeaFactoryResult(IDEA_FACTORY_READY, verified_paths=sorted(verified))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    start_parser = subparsers.add_parser("start")
    start_parser.add_argument("--game-repo", required=True)
    start_parser.add_argument("--max-candidates", type=int, default=120)
    start_parser.add_argument(
        "--reopen",
        action="store_true",
        help="open non-binding exploration beside existing product authority",
    )
    for command in ("explore", "check-exploration", "compile", "check"):
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument("--game-repo", required=True)
        command_parser.add_argument("--input", required=True)
    return parser


def _print_result(result: IdeaFactoryResult) -> None:
    print(result.status)
    for decision_id in result.review_decision_ids:
        print(f"REVIEW: {decision_id}")
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
            result = start_idea_factory(
                args.game_repo,
                max_candidates=args.max_candidates,
                reopen=args.reopen,
            )
        elif args.command == "explore":
            result = record_exploration(args.game_repo, args.input)
        elif args.command == "check-exploration":
            result = check_exploration(args.game_repo, args.input)
        elif args.command == "compile":
            result = compile_product_thesis(args.game_repo, args.input)
        else:
            result = check_product_thesis(args.game_repo, args.input)
    except IdeaFactoryError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    _print_result(result)
    successful = {
        IDEA_EXPLORATION_REQUIRED,
        IDEA_EXPLORATION_OPEN,
        IDEA_REFERENCE_NO_FIT,
        IDEA_DIRECTIONS_AVAILABLE,
        IDEA_DIRECTION_EMERGED,
        PRODUCT_DIRECTION_REVIEW_REQUIRED,
        IDEA_FACTORY_READY,
        IDEA_FACTORY_ALREADY_READY,
    }
    return 0 if result.status in successful else 2


if __name__ == "__main__":
    raise SystemExit(main())
