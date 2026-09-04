#!/usr/bin/env python3
"""Authority-bound Gameplay Factory bootstrap for a total-new game repo.

This module bridges the gap between a commissioned Product/validated Studio
cycle/approved Gameplay Decision Card and the normal objective workflow.  It
creates *design-time* progression/frontier adapters with zero implemented
player actions.  It never manufactures runtime selection, completion, action,
reward, observation, or acceptance evidence.

The existing-project initializer remains reconstruction-only.  New-project
bootstrap is a separate fail-closed transition:

    active Product + validated Studio cycle + registered USER_APPROVED Card
      -> mechanical authority probe
      -> explicit technical/bootstrap input
      -> planned adapters + empty implemented-action model + initial frontier
      -> READY_FOR_NEW_GAMEPLAY_DESIGN
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

try:
    from gameplay.design_gate import (
        CARD_FACTORY_REVIEW_NAME,
        READY_FOR_NEW_GAMEPLAY_DESIGN,
        _validate_decision_card,
        current_factory_revision,
        render_decision_card,
    )
    from studio.product import ACTIVE, require_active_product_authority
except ModuleNotFoundError:  # pragma: no cover - direct script import path.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from gameplay.design_gate import (  # type: ignore[no-redef]
        CARD_FACTORY_REVIEW_NAME,
        READY_FOR_NEW_GAMEPLAY_DESIGN,
        _validate_decision_card,
        current_factory_revision,
        render_decision_card,
    )
    from studio.product import ACTIVE, require_active_product_authority  # type: ignore[no-redef]


FACTORY_ROOT = Path(__file__).resolve().parent.parent

PROBE_SCHEMA_VERSION = "gameplay_new_project_bootstrap_probe.v1"
INPUT_SCHEMA_VERSION = "gameplay_new_project_bootstrap_input.v1"
RESULT_SCHEMA_VERSION = "gameplay_factory_init_result.v2"
MODEL_SCHEMA_VERSION = "gameplay_design_model.v1"
UNIT_SCHEMA_VERSION = "next_gameplay_unit_input.v1"

NEW_PROJECT_GAMEPLAY_AUTHORITY_REQUIRED = "NEW_PROJECT_GAMEPLAY_AUTHORITY_REQUIRED"
NEW_PROJECT_BOOTSTRAP_INPUT_REQUIRED = "NEW_PROJECT_BOOTSTRAP_INPUT_REQUIRED"
GAMEPLAY_FACTORY_READY = "GAMEPLAY_FACTORY_READY"
BLOCKED_BY_BOOTSTRAP_AUTHORITY = "BLOCKED_BY_BOOTSTRAP_AUTHORITY"
BLOCKED_BY_BOOTSTRAP_MATERIAL = "BLOCKED_BY_BOOTSTRAP_MATERIAL"
BLOCKED_BY_EXISTING_FACTORY_STATE = "BLOCKED_BY_EXISTING_FACTORY_STATE"

INIT_ROOT_RELATIVE = Path("design/gameplay/init")
PROBE_RELATIVE = INIT_ROOT_RELATIVE / "GAMEPLAY_NEW_PROJECT_BOOTSTRAP_PROBE.json"
INPUT_RELATIVE = INIT_ROOT_RELATIVE / "GAMEPLAY_NEW_PROJECT_BOOTSTRAP_INPUT.json"
RESULT_RELATIVE = INIT_ROOT_RELATIVE / "GAMEPLAY_FACTORY_INIT_RESULT.json"

PROFILE_RELATIVE = Path("design/gameplay/adapter/PROJECT_GAMEPLAY_PROFILE.md")
PRODUCTION_RELATIVE = Path("design/gameplay/adapter/PRODUCTION_ADAPTER.md")
OBSERVATION_RELATIVE = Path("design/gameplay/adapter/OBSERVATION_ADAPTER.md")
MODEL_RELATIVE = Path("design/gameplay/adapter/GAMEPLAY_DESIGN_MODEL.json")
GRAMMAR_RELATIVE = Path("design/gameplay/state/GAMEPLAY_GRAMMAR_STATE.md")
LESSONS_RELATIVE = Path("design/gameplay/state/EXPERIENCE_LESSONS.md")

STATIC_OUTPUTS = (
    PROFILE_RELATIVE,
    PRODUCTION_RELATIVE,
    OBSERVATION_RELATIVE,
    MODEL_RELATIVE,
    GRAMMAR_RELATIVE,
    LESSONS_RELATIVE,
    RESULT_RELATIVE,
)

PRODUCT_REGISTER_RELATIVE = Path("design/product/PRODUCT_AUTHORITY_REGISTER.json")
DECISION_REGISTER_RELATIVE = Path("design/studio/STUDIO_DECISION_CARD_REGISTER.json")

ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
SHA_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class NewProjectBootstrapError(ValueError):
    """Raised before a bootstrap command mutates canonical output state."""


@dataclass
class NewProjectBootstrapResult:
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


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise NewProjectBootstrapError(f"git {' '.join(args)} failed: {detail}")
    return result


def _resolve_game_repo(raw: str | Path) -> Path:
    repo = Path(raw).expanduser().resolve()
    if not repo.is_dir():
        raise NewProjectBootstrapError(f"game repo does not exist: {repo}")
    if repo == FACTORY_ROOT or _is_within(repo, FACTORY_ROOT):
        raise NewProjectBootstrapError("game repo must not be this factory repo or its child")
    root = _git(repo, "rev-parse", "--show-toplevel").stdout.strip()
    if Path(root).resolve() != repo:
        raise NewProjectBootstrapError("game repo must be the Git root")
    return repo


def _resolve_owned(
    repo: Path, raw: str | Path, *, must_exist: bool = False
) -> Path:
    candidate = Path(raw).expanduser()
    path = (candidate if candidate.is_absolute() else repo / candidate).resolve()
    if not _is_within(path, repo):
        raise NewProjectBootstrapError(f"path escapes game repo: {raw}")
    if must_exist and not path.exists():
        raise NewProjectBootstrapError(f"required path does not exist: {raw}")
    return path


def _relative(repo: Path, path: Path) -> str:
    return path.resolve().relative_to(repo.resolve()).as_posix()


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise NewProjectBootstrapError(f"cannot read {label}: {error}") from error
    if not isinstance(payload, dict):
        raise NewProjectBootstrapError(f"{label} must be a JSON object")
    return payload


def _json_text(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha_file(path: Path) -> str:
    return _sha_bytes(path.read_bytes())


def _ref(repo: Path, path: Path) -> dict[str, str]:
    return {"path": _relative(repo, path), "sha256": _sha_file(path)}


def _current_revision(repo: Path) -> str:
    result = _git(repo, "rev-parse", "--verify", "HEAD", check=False)
    if result.returncode != 0:
        return "UNBORN_HEAD"
    return result.stdout.strip()


def _source_paths(repo: Path, ignored: Iterable[Path] = ()) -> list[str]:
    ignored_paths = {item.as_posix() for item in ignored}
    result = _git(
        repo,
        "ls-files",
        "--cached",
        "--others",
        "--exclude-standard",
        "-z",
    ).stdout
    paths: list[str] = []
    for raw in result.split("\0"):
        if not raw:
            continue
        relative = Path(raw).as_posix()
        if relative.startswith(f"{INIT_ROOT_RELATIVE.as_posix()}/"):
            continue
        if relative in ignored_paths:
            continue
        path = (repo / relative).resolve()
        if _is_within(path, repo) and path.is_file():
            paths.append(relative)
    return sorted(set(paths))


def _tree_sha(repo: Path, paths: Iterable[str]) -> str:
    digest = hashlib.sha256()
    for relative in sorted(paths):
        path = _resolve_owned(repo, relative, must_exist=True)
        if not path.is_file():
            raise NewProjectBootstrapError(f"source path is not a file: {relative}")
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
        digest.update(b"\0")
    return digest.hexdigest()


def _require_text(value: Any, label: str, errors: list[str]) -> str:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label} must be a non-empty string")
        return ""
    text = value.strip()
    if "TBD" in text:
        errors.append(f"{label} must not contain TBD")
    return text


def _require_id(value: Any, label: str, errors: list[str]) -> str:
    text = _require_text(value, label, errors)
    if text and ID_PATTERN.fullmatch(text) is None:
        errors.append(f"{label} must match {ID_PATTERN.pattern}")
    return text


def _require_strings(
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
        errors.append(f"{label} must not be empty")
    values = [_require_text(item, f"{label}[{index}]", errors) for index, item in enumerate(value)]
    values = [item for item in values if item]
    if len(values) != len(set(values)):
        errors.append(f"{label} must not contain duplicates")
    return values


def _require_exact_keys(
    value: Any, label: str, required: set[str], errors: list[str]
) -> dict[str, Any]:
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object")
        return {}
    missing = required - set(value)
    extra = set(value) - required
    for key in sorted(missing):
        errors.append(f"{label} is missing {key}")
    for key in sorted(extra):
        errors.append(f"{label} contains unsupported field {key}")
    return value


def _claim_index(card: dict[str, Any]) -> dict[str, str]:
    claims: dict[str, str] = {}
    promise = card.get("player_promise")
    if isinstance(promise, dict) and isinstance(promise.get("claim_id"), str):
        claims[promise["claim_id"]] = str(promise.get("text", ""))
    for field in (
        "core_cycle",
        "material_commitments",
        "red_lines",
        "validation_hypotheses",
    ):
        for item in card.get(field, []):
            if not isinstance(item, dict) or not isinstance(item.get("claim_id"), str):
                continue
            text = str(item.get("text", ""))
            if field == "validation_hypotheses":
                text += " — reject if: " + str(item.get("falsification_signal", ""))
            claims[item["claim_id"]] = text
    return claims


def _approved_card_candidates(repo: Path) -> list[Path]:
    register_path = repo / DECISION_REGISTER_RELATIVE
    if not register_path.is_file():
        return []
    register = _load_json(register_path, "Studio decision-card register")
    result: list[Path] = []
    for entry in register.get("entries", []):
        if not isinstance(entry, dict) or entry.get("state") != "USER_APPROVED":
            continue
        card_ref = entry.get("decision_card")
        if not isinstance(card_ref, dict) or not isinstance(card_ref.get("path"), str):
            continue
        try:
            card_path = _resolve_owned(repo, card_ref["path"], must_exist=True)
        except NewProjectBootstrapError:
            continue
        if card_path.is_file():
            result.append(card_path)
    return result


def _historical_pending_card_transition_errors(
    repo: Path,
    card_path: Path,
    card: dict[str, Any],
    errors: list[str],
) -> list[str]:
    """Accept only the expected mutable-envelope delta after Card approval.

    A semantic alignment input may bind the PENDING bytes of the canonical Card.
    Recording the exact user verdict changes only ``human_verdict`` and therefore
    the file SHA, while the rendered decision surface and decision-payload SHA
    remain identical.  The Studio register intentionally keeps the historical
    alignment input/review immutable.  Generic alignment validation consequently
    reports those historical Card refs as stale after the authorized transition.

    This compatibility gate removes only that narrow error set.  Every stale ref
    must point to the exact approved Card, share one historical SHA, preserve the
    same rendered decision surface, and remain in the registered alignment input.
    Any other alignment, register, review, authority, or Card error still blocks.
    """

    repo = repo.resolve()
    card_path = card_path.resolve()
    if not errors or card.get("human_verdict", {}).get("status") != "USER_APPROVED":
        return errors
    register_path = repo / DECISION_REGISTER_RELATIVE
    if not register_path.is_file():
        return errors
    register = _load_json(register_path, "Studio decision-card register")
    entry = next(
        (
            item
            for item in register.get("entries", [])
            if isinstance(item, dict)
            and item.get("decision_payload_sha256") == card.get("decision_payload_sha256")
            and item.get("state") == "USER_APPROVED"
        ),
        None,
    )
    if not isinstance(entry, dict):
        return errors
    alignment_ref = entry.get("alignment_input")
    if not isinstance(alignment_ref, dict) or not isinstance(alignment_ref.get("path"), str):
        return errors
    try:
        alignment_path = _resolve_owned(repo, alignment_ref["path"], must_exist=True)
    except NewProjectBootstrapError:
        return errors
    if not alignment_path.is_file() or _sha_file(alignment_path) != alignment_ref.get("sha256"):
        return errors
    alignment = _load_json(alignment_path, "registered semantic alignment input")
    rendered = render_decision_card(card)
    candidate = alignment.get("candidate_output")
    if not isinstance(candidate, dict) or candidate.get("kind") != "DECISION_SURFACE":
        return errors
    if candidate.get("text") != rendered or candidate.get("sha256") != _sha_bytes(
        rendered.encode("utf-8")
    ):
        return errors

    card_relative = _relative(repo, card_path)
    current_sha = _sha_file(card_path)
    allowed_errors: list[str] = []
    historical_shas: set[str] = set()
    collections = (
        ("active_authorities", "artifact"),
        ("authority_changes", "artifact"),
        ("pending_decisions", "decision_card"),
    )
    for collection_name, ref_field in collections:
        collection = alignment.get(collection_name, [])
        if not isinstance(collection, list):
            return errors
        for index, item in enumerate(collection):
            if not isinstance(item, dict):
                continue
            historical_ref = item.get(ref_field)
            if not isinstance(historical_ref, dict):
                continue
            if historical_ref.get("path") != card_relative:
                continue
            digest = historical_ref.get("sha256")
            if not isinstance(digest, str) or SHA_PATTERN.fullmatch(digest) is None:
                return errors
            if digest != current_sha:
                historical_shas.add(digest)
                allowed_errors.append(
                    f"{collection_name}[{index}].{ref_field} hash does not match {card_relative}"
                )
    if len(historical_shas) != 1 or not allowed_errors:
        return errors
    allowed_errors.append(
        "registered Studio decision surface lacks a valid "
        "HUMAN_RULING_GENUINELY_REQUIRED alignment verdict"
    )
    return [] if sorted(errors) == sorted(allowed_errors) else errors


def _validate_approved_card(repo: Path, card_path: Path) -> tuple[dict[str, Any], list[str]]:
    card = _load_json(card_path, "approved Gameplay Decision Card")
    errors: list[str] = []
    revision = current_factory_revision(FACTORY_ROOT)
    _validate_decision_card(
        game_repo=repo,
        card_path=card_path,
        project_id=str(card.get("project_id", "")),
        objective_id=str(card.get("objective_id", "")),
        factory_revision=revision,
        context_status=READY_FOR_NEW_GAMEPLAY_DESIGN,
        errors=errors,
    )
    errors = _historical_pending_card_transition_errors(repo, card_path, card, errors)
    register, product_errors = require_active_product_authority(
        repo, card.get("product_authority") if isinstance(card.get("product_authority"), dict) else None
    )
    errors.extend(product_errors)
    if register and register.get("status") not in {ACTIVE, "LEGACY_ACTIVE_PRODUCT_AUTHORITY"}:
        errors.append("new-project bootstrap requires active Product authority")
    return card, errors


def _resolve_card(repo: Path, card_text: str | None) -> tuple[Path | None, list[str]]:
    if card_text:
        try:
            path = _resolve_owned(repo, card_text, must_exist=True)
        except NewProjectBootstrapError as error:
            return None, [str(error)]
        return path, []
    candidates = _approved_card_candidates(repo)
    if not candidates:
        return None, []
    if len(candidates) > 1:
        return None, [
            "multiple USER_APPROVED decision cards exist; rerun probe-new with an exact --card path"
        ]
    return candidates[0], []


def _compose_probe_payload(
    repo: Path,
    card_path: Path,
    card: dict[str, Any],
    *,
    ignored_outputs: Iterable[Path] = (),
) -> tuple[dict[str, Any], list[str]]:
    """Rebuild the probe from current authority rather than trusting init state."""

    product_ref = card["product_authority"]
    system_ref = card["studio_gameplay_system"]
    system_manifest_path = _resolve_owned(repo, system_ref["path"], must_exist=True)
    system_manifest = _load_json(system_manifest_path, "Studio gameplay-system manifest")
    system_definition_ref = system_manifest.get("gameplay_system")
    if not isinstance(system_definition_ref, dict):
        return {}, ["Studio gameplay-system manifest lacks gameplay_system ref"]
    system_path = _resolve_owned(repo, system_definition_ref["path"], must_exist=True)
    system = _load_json(system_path, "Studio gameplay-system definition")

    authoritative_paths = [
        repo / PRODUCT_REGISTER_RELATIVE,
        _resolve_owned(repo, product_ref["path"], must_exist=True),
        _resolve_owned(repo, system_ref["path"], must_exist=True),
        system_path,
        card_path,
        repo / DECISION_REGISTER_RELATIVE,
        card_path.with_name(CARD_FACTORY_REVIEW_NAME),
    ]
    missing = [
        str(path.relative_to(repo)) for path in authoritative_paths if not path.is_file()
    ]
    if missing:
        return {}, ["required authority artifact is missing: " + ", ".join(missing)]

    ignored = [*STATIC_OUTPUTS, *ignored_outputs]
    source_paths = _source_paths(repo, ignored)
    repository = {
        "expected_revision": _current_revision(repo),
        "source_paths": source_paths,
        "source_tree_sha256": _tree_sha(repo, source_paths),
    }
    return {
        "schema_version": PROBE_SCHEMA_VERSION,
        "project_id": card["project_id"],
        "objective_id": card["objective_id"],
        "factory_revision": card["factory_revision"],
        "repository": repository,
        "authorities": {
            "product_register": _ref(repo, repo / PRODUCT_REGISTER_RELATIVE),
            "product_authority": _ref(repo, _resolve_owned(repo, product_ref["path"])),
            "studio_gameplay_system": _ref(repo, system_manifest_path),
            "studio_gameplay_definition": _ref(repo, system_path),
            "decision_card": _ref(repo, card_path),
            "decision_register": _ref(repo, repo / DECISION_REGISTER_RELATIVE),
            "final_card_review": _ref(
                repo, card_path.with_name(CARD_FACTORY_REVIEW_NAME)
            ),
        },
        "decision_payload_sha256": card["decision_payload_sha256"],
        "system_projection": {
            "system_id": system.get("system_id"),
            "cycle_id": system.get("cycle_id"),
            "system_promise": system.get("system_promise"),
            "core_player_verbs": system.get("core_player_verbs", []),
            "feedback_state_ids": system.get("feedback_state_ids", []),
            "card_claims": _claim_index(card),
        },
        "interpretation_warning": (
            "These artifacts authorize new gameplay design. They do not prove any "
            "runtime selection, completion, player action, reward mutation, observation, "
            "acceptance result, file architecture, or engine implementation."
        ),
    }, []


def probe_new_project(
    game_repo_text: str,
    *,
    card_text: str | None = None,
) -> NewProjectBootstrapResult:
    """Create a mechanical probe from already-approved game-owned authority."""

    repo = _resolve_game_repo(game_repo_text)
    product_register, product_errors = require_active_product_authority(repo)
    if product_errors:
        return NewProjectBootstrapResult(
            NEW_PROJECT_GAMEPLAY_AUTHORITY_REQUIRED,
            warnings=[
                "A total-new repo needs active Product authority before Gameplay bootstrap."
            ],
        )
    if (
        product_register.get("status") != ACTIVE
        or not (repo / PRODUCT_REGISTER_RELATIVE).is_file()
    ):
        return NewProjectBootstrapResult(
            NEW_PROJECT_GAMEPLAY_AUTHORITY_REQUIRED,
            warnings=[
                "New-project bootstrap requires an explicit ACTIVE Product Authority Register; "
                "legacy canonical Product files are insufficient for this causal transition."
            ],
        )
    card_path, selection_errors = _resolve_card(repo, card_text)
    if selection_errors:
        return NewProjectBootstrapResult(
            BLOCKED_BY_BOOTSTRAP_AUTHORITY, errors=selection_errors
        )
    if card_path is None:
        return NewProjectBootstrapResult(
            NEW_PROJECT_GAMEPLAY_AUTHORITY_REQUIRED,
            warnings=[
                "No registered USER_APPROVED Gameplay Decision Card is available for bootstrap."
            ],
        )
    card, errors = _validate_approved_card(repo, card_path)
    if errors:
        return NewProjectBootstrapResult(BLOCKED_BY_BOOTSTRAP_AUTHORITY, errors=errors)

    probe_payload, probe_errors = _compose_probe_payload(repo, card_path, card)
    if probe_errors:
        return NewProjectBootstrapResult(
            BLOCKED_BY_BOOTSTRAP_AUTHORITY, errors=probe_errors
        )
    target = repo / PROBE_RELATIVE
    content = _json_text(probe_payload)
    if target.exists() and target.read_text(encoding="utf-8") != content:
        return NewProjectBootstrapResult(
            BLOCKED_BY_EXISTING_FACTORY_STATE,
            errors=[f"existing bootstrap probe differs: {PROBE_RELATIVE.as_posix()}"],
        )
    created: list[str] = []
    verified: list[str] = []
    if target.exists():
        verified.append(PROBE_RELATIVE.as_posix())
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        created.append(PROBE_RELATIVE.as_posix())
    return NewProjectBootstrapResult(
        NEW_PROJECT_BOOTSTRAP_INPUT_REQUIRED,
        warnings=[
            "Author the explicit technical/frontier bootstrap input; the probe does not invent runtime adapters."
        ],
        created_paths=created,
        verified_paths=verified,
    )


def _validate_ref(repo: Path, value: Any, label: str, errors: list[str]) -> Path | None:
    ref = _require_exact_keys(value, label, {"path", "sha256"}, errors)
    path_text = _require_text(ref.get("path"), f"{label}.path", errors)
    digest = _require_text(ref.get("sha256"), f"{label}.sha256", errors)
    if digest and SHA_PATTERN.fullmatch(digest) is None:
        errors.append(f"{label}.sha256 must be lowercase SHA-256")
    if not path_text:
        return None
    candidate = Path(path_text)
    if candidate.is_absolute():
        errors.append(f"{label}.path must be game-repo-relative")
        return None
    try:
        path = _resolve_owned(repo, path_text, must_exist=True)
    except NewProjectBootstrapError as error:
        errors.append(str(error))
        return None
    if not path.is_file():
        errors.append(f"{label}.path is not a file")
        return None
    if digest and _sha_file(path) != digest:
        errors.append(f"{label} hash does not match {path_text}")
    return path


def _planned_paths(value: Any, label: str, errors: list[str]) -> list[str]:
    paths = _require_strings(value, label, errors, allow_empty=False)
    for index, raw in enumerate(paths):
        path = Path(raw)
        if path.is_absolute() or ".." in path.parts:
            errors.append(f"{label}[{index}] must be a portable game-repo-relative path")
        if raw.startswith("design/"):
            errors.append(f"{label}[{index}] must identify runtime source, not Factory design state")
    return paths


def _validate_input(
    repo: Path, payload: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    required = {
        "schema_version",
        "project_id",
        "init_date",
        "author_context_id",
        "probe",
        "technical_profile",
        "initial_frontier",
        "user_rulings",
        "unresolved_material_gaps",
        "ai_assumptions",
    }
    _require_exact_keys(payload, "bootstrap input", required, errors)
    if payload.get("schema_version") != INPUT_SCHEMA_VERSION:
        errors.append(f"schema_version must be {INPUT_SCHEMA_VERSION}")
    project_id = _require_id(payload.get("project_id"), "project_id", errors)
    init_date = _require_text(payload.get("init_date"), "init_date", errors)
    if init_date and re.fullmatch(r"\d{4}-\d{2}-\d{2}", init_date) is None:
        errors.append("init_date must use YYYY-MM-DD")
    _require_id(payload.get("author_context_id"), "author_context_id", errors)
    probe_path = _validate_ref(repo, payload.get("probe"), "probe", errors)
    probe: dict[str, Any] = {}
    if probe_path is not None:
        if probe_path != (repo / PROBE_RELATIVE).resolve():
            errors.append(f"probe.path must be {PROBE_RELATIVE.as_posix()}")
        probe = _load_json(probe_path, "new-project bootstrap probe")
        if probe.get("schema_version") != PROBE_SCHEMA_VERSION:
            errors.append(f"probe schema_version must be {PROBE_SCHEMA_VERSION}")
        if project_id and probe.get("project_id") != project_id:
            errors.append("project_id does not match bootstrap probe")
        repository = probe.get("repository")
        if not isinstance(repository, dict):
            errors.append("bootstrap probe lacks repository binding")
        else:
            expected_revision = repository.get("expected_revision")
            if expected_revision != _current_revision(repo):
                errors.append("game repository revision changed after bootstrap probe")
            ignored = list(STATIC_OUTPUTS)
            frontier_value = payload.get("initial_frontier")
            if isinstance(frontier_value, dict):
                objective_dir = frontier_value.get("objective_dir")
                locale_value = frontier_value.get("objective_locale")
                if isinstance(objective_dir, str) and ID_PATTERN.fullmatch(objective_dir):
                    ignored.append(
                        Path(f"design/gameplay/objective_gameplay/{objective_dir}/NEXT_GAMEPLAY_UNIT_INPUT.json")
                    )
                if isinstance(locale_value, dict) and isinstance(locale_value.get("path"), str):
                    ignored.append(Path(locale_value["path"]))
            actual_paths = _source_paths(repo, ignored)
            if actual_paths != repository.get("source_paths"):
                errors.append("game repository source paths changed after bootstrap probe")
            else:
                actual_tree = _tree_sha(repo, actual_paths)
                if actual_tree != repository.get("source_tree_sha256"):
                    errors.append("game repository source bytes changed after bootstrap probe")

    technical = _require_exact_keys(
        payload.get("technical_profile"),
        "technical_profile",
        {
            "primary_locale",
            "target_runtime",
            "planned_runtime_roots",
            "validation_commands",
            "integration_constraints",
        },
        errors,
    )
    _require_text(technical.get("primary_locale"), "technical_profile.primary_locale", errors)
    _require_text(technical.get("target_runtime"), "technical_profile.target_runtime", errors)
    _planned_paths(
        technical.get("planned_runtime_roots"),
        "technical_profile.planned_runtime_roots",
        errors,
    )
    _require_strings(
        technical.get("validation_commands"),
        "technical_profile.validation_commands",
        errors,
    )
    _require_strings(
        technical.get("integration_constraints"),
        "technical_profile.integration_constraints",
        errors,
        allow_empty=False,
    )

    frontier = _require_exact_keys(
        payload.get("initial_frontier"),
        "initial_frontier",
        {
            "objective_dir",
            "decision",
            "current_state",
            "objective_locale",
            "completion_condition",
            "completion_source_claim_ids",
            "successor_handoff",
            "recent_patterns",
            "design_constraints",
        },
        errors,
    )
    objective_dir = _require_id(frontier.get("objective_dir"), "initial_frontier.objective_dir", errors)
    decision = _require_text(frontier.get("decision"), "initial_frontier.decision", errors)
    if decision not in {"COMPLETE_CURRENT_UNIT", "ADVANCE_TO_NEXT_UNIT"}:
        errors.append("initial_frontier.decision is unsupported")
    _require_text(frontier.get("current_state"), "initial_frontier.current_state", errors)
    locale = _require_exact_keys(
        frontier.get("objective_locale"),
        "initial_frontier.objective_locale",
        {"path", "key_column", "locale_column", "key", "text", "source_claim_id"},
        errors,
    )
    locale_path_text = _require_text(locale.get("path"), "objective_locale.path", errors)
    if locale_path_text:
        path = Path(locale_path_text)
        if path.is_absolute() or ".." in path.parts or path.suffix.lower() != ".csv":
            errors.append("objective_locale.path must be a portable game-repo-relative CSV path")
        if locale_path_text.startswith("design/"):
            errors.append("objective_locale.path must be a game localization path, not Factory state")
    for key in ("key_column", "locale_column", "key", "text", "source_claim_id"):
        _require_text(locale.get(key), f"objective_locale.{key}", errors)
    completion = _require_text(
        frontier.get("completion_condition"),
        "initial_frontier.completion_condition",
        errors,
    )
    completion_sources = _require_strings(
        frontier.get("completion_source_claim_ids"),
        "initial_frontier.completion_source_claim_ids",
        errors,
        allow_empty=False,
    )
    successor = _require_exact_keys(
        frontier.get("successor_handoff"),
        "initial_frontier.successor_handoff",
        {"status", "description", "source_claim_ids"},
        errors,
    )
    successor_status = _require_text(successor.get("status"), "successor_handoff.status", errors)
    if successor_status not in {"MISSING", "UNKNOWN"}:
        errors.append("new-project successor_handoff.status must be MISSING or UNKNOWN until runtime exists")
    _require_text(successor.get("description"), "successor_handoff.description", errors)
    successor_sources = _require_strings(
        successor.get("source_claim_ids"),
        "successor_handoff.source_claim_ids",
        errors,
        allow_empty=False,
    )
    _require_strings(frontier.get("recent_patterns"), "initial_frontier.recent_patterns", errors)
    _require_strings(frontier.get("design_constraints"), "initial_frontier.design_constraints", errors)

    card: dict[str, Any] = {}
    if probe:
        authorities = probe.get("authorities")
        if not isinstance(authorities, dict):
            errors.append("bootstrap probe lacks authority refs")
        else:
            card_ref = authorities.get("decision_card")
            card_path = _validate_ref(repo, card_ref, "probe.authorities.decision_card", errors)
            if card_path is not None:
                card, card_errors = _validate_approved_card(repo, card_path)
                errors.extend(card_errors)
                if card.get("decision_payload_sha256") != probe.get("decision_payload_sha256"):
                    errors.append("approved decision payload differs from bootstrap probe")
                claims = _claim_index(card)
                source_claim_id = str(locale.get("source_claim_id", ""))
                if source_claim_id not in claims:
                    errors.append("objective_locale.source_claim_id is absent from approved Card")
                elif locale.get("text") != claims[source_claim_id]:
                    errors.append("objective_locale.text must exactly equal its approved Card claim")
                for label, claim_ids in (
                    ("completion_source_claim_ids", completion_sources),
                    ("successor_handoff.source_claim_ids", successor_sources),
                ):
                    for claim_id in claim_ids:
                        if claim_id not in claims:
                            errors.append(f"{label} references unknown approved Card claim {claim_id}")
                if objective_dir and objective_dir != card.get("objective_id"):
                    errors.append("initial_frontier.objective_dir must equal approved Card objective_id")
                if completion and not completion_sources:
                    errors.append("completion_condition requires approved Card claim sources")

                derived_outputs: list[Path] = []
                if objective_dir:
                    derived_outputs.append(
                        Path(
                            "design/gameplay/objective_gameplay/"
                            f"{objective_dir}/NEXT_GAMEPLAY_UNIT_INPUT.json"
                        )
                    )
                if locale_path_text:
                    derived_outputs.append(Path(locale_path_text))
                try:
                    expected_probe, expected_probe_errors = _compose_probe_payload(
                        repo,
                        card_path,
                        card,
                        ignored_outputs=derived_outputs,
                    )
                except NewProjectBootstrapError as error:
                    expected_probe = {}
                    expected_probe_errors = [str(error)]
                errors.extend(expected_probe_errors)
                if expected_probe and probe != expected_probe:
                    errors.append(
                        "bootstrap probe is not the exact mechanical projection of "
                        "current Product/System/Card authority"
                    )

    _require_strings(payload.get("user_rulings"), "user_rulings", errors)
    gaps = _require_strings(payload.get("unresolved_material_gaps"), "unresolved_material_gaps", errors)
    assumptions = _require_strings(payload.get("ai_assumptions"), "ai_assumptions", errors)
    if gaps:
        errors.append("unresolved_material_gaps must be empty before bootstrap compile")
    if assumptions:
        errors.append("ai_assumptions must be empty before bootstrap compile")
    if str(repo) in json.dumps(payload, ensure_ascii=False):
        errors.append("bootstrap input must not persist the absolute game repo path")
    if not technical.get("validation_commands"):
        warnings.append(
            "No validation command exists before runtime creation; production plans must add one before claiming technical verification."
        )
    if locale.get("locale_column") != technical.get("primary_locale"):
        warnings.append(
            "The approved Card claim is emitted in a non-primary authority-language "
            "locale column; production must add and validate the primary-locale player "
            "text before runtime presentation."
        )
    warnings.append(
        "Bootstrap authority is design-time only: implemented actions, rewards, runtime selection/completion, observation, and acceptance remain unproven."
    )
    return probe, card, errors, warnings


def _locale_csv(locale: dict[str, Any]) -> str:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow([locale["key_column"], locale["locale_column"]])
    writer.writerow([locale["key"], locale["text"]])
    return stream.getvalue()


def _evidence_ref(role: str, path: str, contains: list[str]) -> dict[str, Any]:
    return {"role": role, "path": path, "contains": contains}


def _build_model(
    payload: dict[str, Any], probe: dict[str, Any], card: dict[str, Any]
) -> dict[str, Any]:
    system = probe["system_projection"]
    manifest_path = probe["authorities"]["studio_gameplay_system"]["path"]
    card_path = probe["authorities"]["decision_card"]["path"]
    constraints = [item["text"] for item in card.get("red_lines", [])]
    constraints.extend(payload["initial_frontier"]["design_constraints"])
    constraints.append(
        "No player action or reward is implemented until a production plan creates runtime evidence."
    )
    return {
        "schema_version": MODEL_SCHEMA_VERSION,
        "project_id": payload["project_id"],
        "primary_progression_driver": {
            "system_id": system["system_id"],
            "system_kind": "studio_gameplay_cycle",
            "progression_unit": payload["initial_frontier"]["objective_dir"],
            "description": system["system_promise"],
            "evidence_refs": [
                _evidence_ref(
                    "progression_authority",
                    manifest_path,
                    [f'"system_id": "{system["system_id"]}"'],
                ),
                _evidence_ref(
                    "approved_decision_authority",
                    card_path,
                    [card["decision_payload_sha256"]],
                ),
            ],
        },
        "player_actions": [],
        "recent_patterns": payload["initial_frontier"]["recent_patterns"],
        "design_constraints": list(dict.fromkeys(constraints)),
    }


def _build_unit_input(
    payload: dict[str, Any], probe: dict[str, Any], card: dict[str, Any]
) -> dict[str, Any]:
    frontier = payload["initial_frontier"]
    locale = frontier["objective_locale"]
    claims = _claim_index(card)
    card_path = probe["authorities"]["decision_card"]["path"]
    selection_claim = claims[locale["source_claim_id"]]
    completion_tokens = [claims[item] for item in frontier["completion_source_claim_ids"]]
    successor_tokens = [claims[item] for item in frontier["successor_handoff"]["source_claim_ids"]]
    return {
        "schema_version": UNIT_SCHEMA_VERSION,
        "project_id": payload["project_id"],
        "project_model_path": MODEL_RELATIVE.as_posix(),
        "frontier": {
            "decision": frontier["decision"],
            "current_state": frontier["current_state"],
            "objective_id": frontier["objective_dir"],
            "objective_locale": {
                "path": locale["path"],
                "key_column": locale["key_column"],
                "locale_column": locale["locale_column"],
                "key": locale["key"],
                "expected_text": locale["text"],
            },
            "completion_condition": frontier["completion_condition"],
            "successor_handoff": {
                "status": frontier["successor_handoff"]["status"],
                "description": frontier["successor_handoff"]["description"],
            },
            "evidence_refs": [
                _evidence_ref(
                    "design_selection_authority", card_path, [selection_claim]
                ),
                _evidence_ref(
                    "design_completion_authority", card_path, completion_tokens
                ),
                _evidence_ref(
                    "design_successor_authority", card_path, successor_tokens
                ),
            ],
        },
        "applicable_action_ids": [],
        "recent_patterns": [],
        "design_constraints": [],
    }


def _render_profile(
    payload: dict[str, Any], probe: dict[str, Any], card: dict[str, Any]
) -> str:
    system = probe["system_projection"]
    authority_lines = [
        f"- `{name}` — `{value['path']}` — `{value['sha256']}`"
        for name, value in probe["authorities"].items()
    ]
    return "\n".join(
        [
            f"# Project Gameplay Profile — `{payload['project_id']}`",
            "",
            f"- Initialization mode: `NEW_PROJECT_AUTHORITY_BOOTSTRAP`",
            f"- Initialization date: `{payload['init_date']}`",
            f"- Source revision: `{probe['repository']['expected_revision']}`",
            f"- Primary locale: `{payload['technical_profile']['primary_locale']}`",
            f"- Target runtime/platform: {payload['technical_profile']['target_runtime']}",
            f"- Machine gameplay model: `{MODEL_RELATIVE.as_posix()}`",
            "",
            "## Active design authorities",
            "",
            *authority_lines,
            "",
            "## Player frame and promise",
            "",
            f"- {system['system_promise']}",
            f"- Approved first objective: `{card['objective_id']}`",
            "",
            "## Desired gameplay vocabulary",
            "",
            *[f"- `{verb}`" for verb in system["core_player_verbs"]],
            "",
            "## Feedback obligations",
            "",
            *[f"- `{state_id}` must visibly affect the next decision." for state_id in system["feedback_state_ids"]],
            "",
            "## Bootstrap boundary",
            "",
            "This profile projects approved design authority into the first objective. "
            "It records zero implemented player actions and is not runtime, observation, "
            "acceptance, architecture, balance, or fun evidence.",
            "",
        ]
    )


def _render_production_adapter(payload: dict[str, Any]) -> str:
    technical = payload["technical_profile"]
    roots = "<br>".join(f"`{item}`" for item in technical["planned_runtime_roots"])
    commands = technical["validation_commands"] or ["NOT_AVAILABLE_UNTIL_IMPLEMENTED"]
    return "\n".join(
        [
            f"# Production Adapter — `{payload['project_id']}`",
            "",
            "- Adapter mode: `PLANNED_NOT_IMPLEMENTED`",
            f"- Target runtime/platform: {technical['target_runtime']}",
            "- Runtime evidence status: `NONE`",
            "",
            "## Planned ownership envelope",
            "",
            "| Concern | Planned path roots | Current mapping |",
            "| --- | --- | --- |",
            f"| `objective_selection` | {roots} | `NOT_IMPLEMENTED` |",
            f"| `objective_completion` | {roots} | `NOT_IMPLEMENTED` |",
            f"| `player_actions` | {roots} | `NOT_IMPLEMENTED` |",
            f"| `rewards_and_state` | {roots} | `NOT_IMPLEMENTED` |",
            "",
            "## Validation commands",
            "",
            *[f"- {item}" for item in commands],
            "",
            "## Integration constraints",
            "",
            *[f"- {item}" for item in technical["integration_constraints"]],
            "",
            "## Production boundary",
            "",
            "These roots are a bounded planned ownership envelope, not proof "
            "that any file, mapping, action, reward, save path, or validation command "
            "already exists. Production plans must replace each `NOT_IMPLEMENTED` mapping "
            "with exact runtime evidence before acceptance.",
            "",
        ]
    )


def _render_observation_adapter(payload: dict[str, Any]) -> str:
    return f"""# Observation Adapter — `{payload['project_id']}`

- Adapter mode: `NEW_PROJECT_AUTHORITY_BOOTSTRAP`
- Observation status: `NOT_AVAILABLE`
- Mapping path: `NOT_AVAILABLE`

## Evidence sources

- None. Design authority is not runtime observation.

## Launch and capture

- `NOT_AVAILABLE`

## Provenance, ordering, and correlation

- `NOT_AVAILABLE`

## Validation commands

- `NOT_AVAILABLE`

## Limits and gaps

- Runtime instrumentation, normalized events, causal ordering, correlation ids,
  screenshots, deterministic replay, and acceptance evidence do not exist yet.
- Production may proceed from approved design, but runtime-evidence and gameplay-
  acceptance claims remain blocked until a project-owned adapter is implemented.
"""


def _render_grammar(payload: dict[str, Any]) -> str:
    return f"""# Gameplay Grammar State — `{payload['project_id']}`

- Initialization mode: `NEW_PROJECT_AUTHORITY_BOOTSTRAP`
- State version/date: `v0 / {payload['init_date']}`
- Last approved implementation trace: none

No runtime play history exists. Approved Card claims remain design authority;
they are not rewritten here as observed actions, rhythms, knowledge, or costs.
"""


def _render_lessons(payload: dict[str, Any]) -> str:
    return f"""# Gameplay Experience Lessons — `{payload['project_id']}`

- State version/date: `v0 / {payload['init_date']}`
- Last incorporated acceptance/human-playtest refs: none

No conformance or reception lesson is recorded. Factory checks, approved design,
implementation completion, and runnable software must not be relabeled as fun or
human gameplay acceptance.
"""


def _expected_artifacts(
    payload: dict[str, Any], probe: dict[str, Any], card: dict[str, Any], warnings: list[str]
) -> dict[Path, str]:
    frontier = payload["initial_frontier"]
    objective_dir = frontier["objective_dir"]
    locale = frontier["objective_locale"]
    unit_path = Path(
        f"design/gameplay/objective_gameplay/{objective_dir}/NEXT_GAMEPLAY_UNIT_INPUT.json"
    )
    locale_path = Path(locale["path"])
    artifacts: dict[Path, str] = {
        PRODUCTION_RELATIVE: _render_production_adapter(payload),
        OBSERVATION_RELATIVE: _render_observation_adapter(payload),
        MODEL_RELATIVE: _json_text(_build_model(payload, probe, card)),
        GRAMMAR_RELATIVE: _render_grammar(payload),
        LESSONS_RELATIVE: _render_lessons(payload),
        unit_path: _json_text(_build_unit_input(payload, probe, card)),
        locale_path: _locale_csv(locale),
    }
    hashes = {
        path.as_posix(): _sha_bytes(text.encode("utf-8"))
        for path, text in sorted(artifacts.items(), key=lambda item: item[0].as_posix())
    }
    result = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "status": GAMEPLAY_FACTORY_READY,
        "initialization_mode": "NEW_PROJECT_AUTHORITY_BOOTSTRAP",
        "project_id": payload["project_id"],
        "source_revision": probe["repository"]["expected_revision"],
        "source_paths": probe["repository"]["source_paths"],
        "source_tree_sha256": probe["repository"]["source_tree_sha256"],
        "authority_probe": {
            "path": PROBE_RELATIVE.as_posix(),
            "sha256": payload["probe"]["sha256"],
        },
        "approved_decision_payload_sha256": card["decision_payload_sha256"],
        "initial_objective_input_path": unit_path.as_posix(),
        "artifact_sha256": hashes,
        "warnings": warnings,
        "handoff": (
            "Run gameplay/prepare.py context on the initial objective input. "
            "It must return READY_FOR_NEW_GAMEPLAY_DESIGN with zero implemented actions."
        ),
    }
    artifacts[RESULT_RELATIVE] = _json_text(result)
    return artifacts


def _prepare(
    repo: Path, input_path: Path
) -> tuple[dict[str, Any], dict[Path, str], list[str], list[str]]:
    payload = _load_json(input_path, "new-project bootstrap input")
    probe, card, errors, warnings = _validate_input(repo, payload)
    if errors:
        return payload, {}, errors, warnings
    artifacts = _expected_artifacts(payload, probe, card, warnings)
    for relative, content in artifacts.items():
        if "TBD" in content:
            errors.append(f"generated artifact contains TBD: {relative.as_posix()}")
        if str(repo) in content:
            errors.append(f"generated artifact persists absolute game repo path: {relative.as_posix()}")
    return payload, artifacts, errors, warnings


def compile_new_project(
    game_repo_text: str, input_text: str
) -> NewProjectBootstrapResult:
    repo = _resolve_game_repo(game_repo_text)
    input_path = _resolve_owned(repo, input_text, must_exist=True)
    if input_path != (repo / INPUT_RELATIVE).resolve():
        raise NewProjectBootstrapError(f"bootstrap input must be {INPUT_RELATIVE.as_posix()}")
    _, artifacts, errors, warnings = _prepare(repo, input_path)
    if errors:
        return NewProjectBootstrapResult(
            BLOCKED_BY_BOOTSTRAP_MATERIAL, errors=errors, warnings=warnings
        )

    resolved: dict[Path, tuple[Path, str]] = {}
    conflicts: list[str] = []
    for relative, content in artifacts.items():
        target = _resolve_owned(repo, relative)
        resolved[relative] = (target, content)
        if target.exists():
            if not target.is_file():
                conflicts.append(f"canonical bootstrap target is not a file: {relative}")
            elif target.read_text(encoding="utf-8") != content:
                conflicts.append(f"existing factory state differs and will not be overwritten: {relative}")
    if conflicts:
        return NewProjectBootstrapResult(
            BLOCKED_BY_EXISTING_FACTORY_STATE, errors=conflicts, warnings=warnings
        )

    created: list[str] = []
    verified: list[str] = []
    for relative, (target, content) in resolved.items():
        if target.exists():
            verified.append(relative.as_posix())
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        created.append(relative.as_posix())
    return NewProjectBootstrapResult(
        GAMEPLAY_FACTORY_READY,
        warnings=warnings,
        created_paths=sorted(created),
        verified_paths=sorted(verified),
    )


def check_new_project(
    game_repo_text: str, input_text: str
) -> NewProjectBootstrapResult:
    repo = _resolve_game_repo(game_repo_text)
    input_path = _resolve_owned(repo, input_text, must_exist=True)
    if input_path != (repo / INPUT_RELATIVE).resolve():
        raise NewProjectBootstrapError(f"bootstrap input must be {INPUT_RELATIVE.as_posix()}")
    _, artifacts, errors, warnings = _prepare(repo, input_path)
    if errors:
        return NewProjectBootstrapResult(
            BLOCKED_BY_BOOTSTRAP_MATERIAL, errors=errors, warnings=warnings
        )
    verified: list[str] = []
    for relative, expected in artifacts.items():
        target = _resolve_owned(repo, relative)
        if not target.is_file():
            errors.append(f"generated bootstrap artifact is missing: {relative}")
        elif target.read_text(encoding="utf-8") != expected:
            errors.append(f"generated bootstrap artifact is stale or changed: {relative}")
        else:
            verified.append(relative.as_posix())
    if errors:
        return NewProjectBootstrapResult(
            BLOCKED_BY_BOOTSTRAP_MATERIAL,
            errors=errors,
            warnings=warnings,
            verified_paths=verified,
        )
    return NewProjectBootstrapResult(
        GAMEPLAY_FACTORY_READY,
        warnings=warnings,
        verified_paths=sorted(verified),
    )
