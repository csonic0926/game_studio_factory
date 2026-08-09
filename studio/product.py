#!/usr/bin/env python3
"""Product-authority lifecycle for the Game Studio operator.

Product Thesis compilation and product-direction lifecycle are distinct causal
transitions.  Idea Factory commissions one exact thesis; Studio may later
archive that whole direction only from an explicit user revocation that has
already passed fresh semantic alignment.

Archive is not deletion and is not a backup convention.  ``prepare-archive``
creates one immutable, manifest-bound authority snapshot while the canonical
authority is still active.  ``archive`` then marks the product inactive,
withdraws every pending Studio decision surface without fabricating per-card
human verdict tokens, and removes only the canonical product-authority files.
Gameplay, code, assets, baselines, and evidence stay in place as historical
material; the register prevents them from acting as current authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    from studio.alignment import (
        ALIGNMENT_INPUT_VERSION,
        DECISION_REGISTER_PATH,
        DECISION_REGISTER_VERSION,
        PASS_ALIGNMENT,
        AlignmentValidationError,
        current_factory_revision,
        load_decision_register,
        path_ref,
        text_sha256,
        validate_alignment_review,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script invocation.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from studio.alignment import (  # type: ignore[no-redef]
        ALIGNMENT_INPUT_VERSION,
        DECISION_REGISTER_PATH,
        DECISION_REGISTER_VERSION,
        PASS_ALIGNMENT,
        AlignmentValidationError,
        current_factory_revision,
        load_decision_register,
        path_ref,
        text_sha256,
        validate_alignment_review,
    )


FACTORY_ROOT = Path(__file__).resolve().parents[1]
REGISTER_VERSION = "product_authority_register.v1"
SNAPSHOT_VERSION = "product_authority_archive_snapshot.v1"
REGISTER_PATH = Path("design/product/PRODUCT_AUTHORITY_REGISTER.json")
TRANSITIONS_ROOT = Path("design/studio/product_authority_transitions")
ARCHIVE_ROOT = Path("design/product/archive")

ACTIVE = "ACTIVE"
NO_ACTIVE = "NO_ACTIVE_PRODUCT_AUTHORITY"
LEGACY_ACTIVE = "LEGACY_ACTIVE_PRODUCT_AUTHORITY"
ARCHIVE_PREPARED = "PRODUCT_AUTHORITY_ARCHIVE_PREPARED"
ARCHIVED = "PRODUCT_AUTHORITY_ARCHIVED"
ACTIVATED = "PRODUCT_AUTHORITY_ACTIVATED"
BLOCKED = "BLOCKED_BY_PRODUCT_AUTHORITY_STATE"

ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")

REQUIRED_CANONICAL = (
    Path("design/product/PRODUCT_THESIS.md"),
    Path("design/product/FACTORY_CONSTRAINTS.json"),
    Path("design/product/idea/PRODUCT_THESIS_INPUT.json"),
    Path("design/product/idea/IDEA_FACTORY_RESULT.json"),
)
OPTIONAL_CANONICAL = (
    Path("design/product/idea/IDEA_EXPLORATION.json"),
    Path("design/product/idea/IDEA_EXPLORATION.md"),
    Path("design/product/idea/IDEA_FACTORY_REPO_PROBE.json"),
)


class ProductAuthorityError(ValueError):
    """Raised when lifecycle state cannot be safely interpreted or changed."""


@dataclass
class ProductAuthorityResult:
    status: str
    errors: list[str] = field(default_factory=list)
    created_paths: list[str] = field(default_factory=list)
    verified_paths: list[str] = field(default_factory=list)
    removed_paths: list[str] = field(default_factory=list)


def _run_git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise ProductAuthorityError(
            result.stderr.strip() or result.stdout.strip() or "git command failed"
        )
    return result


def _repo(raw: str | Path) -> Path:
    repo = Path(raw).expanduser().resolve()
    if not repo.is_dir():
        raise ProductAuthorityError(f"game repo is not a directory: {repo}")
    root = Path(_run_git(repo, "rev-parse", "--show-toplevel").stdout.strip()).resolve()
    if root != repo:
        raise ProductAuthorityError(f"game repo must be its Git root: {repo}")
    if repo == FACTORY_ROOT or FACTORY_ROOT in repo.parents:
        raise ProductAuthorityError("game repo must not be the Factory checkout")
    return repo


def _readable_repo(raw: str | Path) -> Path:
    """Resolve a read-only consumer root without imposing Git on unit fixtures."""

    repo = Path(raw).expanduser().resolve()
    if not repo.is_dir():
        raise ProductAuthorityError(f"game repo is not a directory: {repo}")
    if repo == FACTORY_ROOT or FACTORY_ROOT in repo.parents:
        raise ProductAuthorityError("game repo must not be the Factory checkout")
    return repo


def _json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ProductAuthorityError(f"cannot read {label}: {error}") from error
    if not isinstance(value, dict):
        raise ProductAuthorityError(f"{label} must be a JSON object")
    return value


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve(repo: Path, raw: str | Path, *, must_exist: bool = False) -> Path:
    path = Path(raw)
    resolved = (path if path.is_absolute() else repo / path).resolve()
    try:
        resolved.relative_to(repo)
    except ValueError as error:
        raise ProductAuthorityError(f"path escapes game repo: {raw}") from error
    if must_exist and not resolved.is_file():
        raise ProductAuthorityError(f"required file is missing: {raw}")
    return resolved


def _artifact_ref(repo: Path, path: Path) -> dict[str, str]:
    return path_ref(repo, path)


def _validate_ref(repo: Path, value: Any, label: str) -> tuple[dict[str, str], Path]:
    if not isinstance(value, dict) or set(value) != {"path", "sha256"}:
        raise ProductAuthorityError(f"{label} must contain exactly path and sha256")
    raw_path = value.get("path")
    digest = value.get("sha256")
    if not isinstance(raw_path, str) or not raw_path:
        raise ProductAuthorityError(f"{label}.path must be non-empty")
    if not isinstance(digest, str) or SHA256_PATTERN.fullmatch(digest) is None:
        raise ProductAuthorityError(f"{label}.sha256 must be lowercase SHA-256")
    path = _resolve(repo, raw_path, must_exist=True)
    if _file_sha(path) != digest:
        raise ProductAuthorityError(f"{label} hash does not match {raw_path}")
    return {"path": raw_path, "sha256": digest}, path


def _canonical_project(repo: Path) -> str:
    product_input = _json(repo / REQUIRED_CANONICAL[2], "Product Thesis input")
    result = _json(repo / REQUIRED_CANONICAL[3], "Idea Factory result")
    project = product_input.get("project_id")
    if not isinstance(project, str) or ID_PATTERN.fullmatch(project) is None:
        raise ProductAuthorityError("Product Thesis input has no portable project_id")
    if result.get("project_id") != project:
        raise ProductAuthorityError("Idea Factory result belongs to another project")
    return project


def _canonical_refs(repo: Path) -> dict[str, dict[str, str]]:
    missing = [path.as_posix() for path in REQUIRED_CANONICAL if not (repo / path).is_file()]
    if missing:
        raise ProductAuthorityError(
            "canonical product authority is incomplete: " + ", ".join(missing)
        )
    return {
        "product_thesis": _artifact_ref(repo, repo / REQUIRED_CANONICAL[0]),
        "factory_constraints": _artifact_ref(repo, repo / REQUIRED_CANONICAL[1]),
        "product_input": _artifact_ref(repo, repo / REQUIRED_CANONICAL[2]),
        "idea_result": _artifact_ref(repo, repo / REQUIRED_CANONICAL[3]),
    }


def _validate_register(repo: Path, value: dict[str, Any]) -> None:
    required = {
        "schema_version", "project_id", "status", "active_authority",
        "transitions", "updated_at",
    }
    if set(value) != required:
        raise ProductAuthorityError("Product authority register has unsupported structure")
    if value.get("schema_version") != REGISTER_VERSION:
        raise ProductAuthorityError("Product authority register has unsupported schema_version")
    project = value.get("project_id")
    if not isinstance(project, str) or ID_PATTERN.fullmatch(project) is None:
        raise ProductAuthorityError("Product authority register has invalid project_id")
    if value.get("status") not in {ACTIVE, NO_ACTIVE}:
        raise ProductAuthorityError("Product authority register has unsupported status")
    if not isinstance(value.get("transitions"), list):
        raise ProductAuthorityError("Product authority register transitions must be an array")
    if not isinstance(value.get("updated_at"), str) or not value["updated_at"]:
        raise ProductAuthorityError("Product authority register updated_at is required")
    active = value.get("active_authority")
    if value.get("status") == NO_ACTIVE:
        if active is not None:
            raise ProductAuthorityError("inactive product register cannot name active authority")
    else:
        if not isinstance(active, dict):
            raise ProductAuthorityError("active product register requires active_authority")
        required_active = {
            "authority_id", "product_thesis", "factory_constraints",
            "product_input", "idea_result", "activated_at",
        }
        if set(active) != required_active:
            raise ProductAuthorityError("active_authority has unsupported structure")
        if not isinstance(active.get("authority_id"), str) or ID_PATTERN.fullmatch(
            active.get("authority_id", "")
        ) is None:
            raise ProductAuthorityError("active product authority_id is invalid")
        for key in ("product_thesis", "factory_constraints", "product_input", "idea_result"):
            _validate_ref(repo, active.get(key), f"active_authority.{key}")


def load_product_register(game_repo: str | Path) -> tuple[dict[str, Any], list[str]]:
    try:
        repo = _repo(game_repo)
        path = repo / REGISTER_PATH
        if not path.is_file():
            return {}, [f"Product authority register is missing: {REGISTER_PATH.as_posix()}"]
        value = _json(path, "Product authority register")
        _validate_register(repo, value)
        return value, []
    except ProductAuthorityError as error:
        return {}, [str(error)]


def product_authority_status(game_repo: str | Path) -> ProductAuthorityResult:
    repo = _repo(game_repo)
    path = repo / REGISTER_PATH
    if path.is_file():
        value = _json(path, "Product authority register")
        try:
            _validate_register(repo, value)
        except ProductAuthorityError as error:
            return ProductAuthorityResult(BLOCKED, errors=[str(error)])
        return ProductAuthorityResult(str(value["status"]), verified_paths=[REGISTER_PATH.as_posix()])
    complete = all((repo / path).is_file() for path in REQUIRED_CANONICAL)
    partial = [path.as_posix() for path in REQUIRED_CANONICAL if (repo / path).is_file()]
    if complete:
        return ProductAuthorityResult(LEGACY_ACTIVE, verified_paths=partial)
    if partial:
        return ProductAuthorityResult(
            BLOCKED,
            errors=["partial legacy product authority exists: " + ", ".join(partial)],
        )
    return ProductAuthorityResult(NO_ACTIVE)


def require_active_product_authority(
    game_repo: str | Path,
    product_ref: dict[str, str] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    try:
        repo = _readable_repo(game_repo)
    except ProductAuthorityError as error:
        return {}, [str(error)]
    register_path = repo / REGISTER_PATH
    if not register_path.is_file():
        legacy_paths = {
            "product_thesis": REQUIRED_CANONICAL[0],
            "factory_constraints": REQUIRED_CANONICAL[1],
            "product_input": REQUIRED_CANONICAL[2],
        }
        missing = [
            path.as_posix() for path in legacy_paths.values() if not (repo / path).is_file()
        ]
        if missing:
            return {}, ["canonical product authority is incomplete: " + ", ".join(missing)]
        refs = {
            key: _artifact_ref(repo, repo / path)
            for key, path in legacy_paths.items()
        }
        if product_ref is not None and product_ref != refs["product_thesis"]:
            return {}, ["product authority does not match legacy canonical Product Thesis"]
        return {"status": LEGACY_ACTIVE, "active_authority": refs}, []
    value = _json(register_path, "Product authority register")
    try:
        _validate_register(repo, value)
    except ProductAuthorityError as error:
        return {}, [str(error)]
    if value.get("status") != ACTIVE:
        return value, ["no active Product Thesis; Studio must return to Idea exploration"]
    active = value["active_authority"]
    if product_ref is not None and product_ref != active["product_thesis"]:
        return value, ["product authority does not match the active Product Authority Register"]
    return value, []


def prepare_product_archive(
    game_repo: str | Path,
    transition_id: str,
    *,
    prepared_at: str,
) -> ProductAuthorityResult:
    repo = _repo(game_repo)
    if ID_PATTERN.fullmatch(transition_id) is None:
        raise ProductAuthorityError("transition_id is not portable")
    if not prepared_at.strip():
        raise ProductAuthorityError("prepared_at is required")
    project = _canonical_project(repo)
    _canonical_refs(repo)
    register_path = repo / REGISTER_PATH
    if register_path.is_file():
        register = _json(register_path, "Product authority register")
        _validate_register(repo, register)
        if register.get("status") != ACTIVE:
            raise ProductAuthorityError("only active product authority can be archived")

    archive_dir = repo / ARCHIVE_ROOT / transition_id
    entries: list[dict[str, Any]] = []
    created: list[str] = []
    verified: list[str] = []
    for canonical in REQUIRED_CANONICAL + OPTIONAL_CANONICAL:
        source = repo / canonical
        if not source.is_file():
            continue
        relative_inside_product = canonical.relative_to("design/product")
        destination = archive_dir / relative_inside_product
        if destination.exists():
            if not destination.is_file() or _file_sha(destination) != _file_sha(source):
                raise ProductAuthorityError(
                    f"archive destination differs from canonical source: {destination}"
                )
            verified.append(destination.relative_to(repo).as_posix())
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            created.append(destination.relative_to(repo).as_posix())
        entries.append(
            {
                "canonical_path": canonical.as_posix(),
                "archived_artifact": _artifact_ref(repo, destination),
            }
        )

    snapshot = {
        "schema_version": SNAPSHOT_VERSION,
        "transition_id": transition_id,
        "project_id": project,
        "factory_revision": current_factory_revision(),
        "prepared_at": prepared_at,
        "authority_artifacts": entries,
    }
    snapshot_path = repo / TRANSITIONS_ROOT / transition_id / "PRODUCT_AUTHORITY_ARCHIVE_SNAPSHOT.json"
    rendered = _json_text(snapshot)
    if snapshot_path.exists():
        if snapshot_path.read_text(encoding="utf-8") != rendered:
            raise ProductAuthorityError("archive snapshot already exists with different bytes")
        verified.append(snapshot_path.relative_to(repo).as_posix())
    else:
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_text(rendered, encoding="utf-8")
        created.append(snapshot_path.relative_to(repo).as_posix())
    return ProductAuthorityResult(
        ARCHIVE_PREPARED,
        created_paths=created,
        verified_paths=verified,
    )


def _load_snapshot(repo: Path, path: Path) -> tuple[dict[str, Any], dict[str, dict[str, str]]]:
    value = _json(path, "Product authority archive snapshot")
    required = {
        "schema_version", "transition_id", "project_id", "factory_revision",
        "prepared_at", "authority_artifacts",
    }
    if set(value) != required or value.get("schema_version") != SNAPSHOT_VERSION:
        raise ProductAuthorityError("archive snapshot has unsupported structure")
    if value.get("factory_revision") != current_factory_revision():
        raise ProductAuthorityError("archive snapshot factory_revision does not match Factory HEAD")
    entries = value.get("authority_artifacts")
    if not isinstance(entries, list):
        raise ProductAuthorityError("archive snapshot authority_artifacts must be an array")
    by_canonical: dict[str, dict[str, str]] = {}
    for index, item in enumerate(entries):
        if not isinstance(item, dict) or set(item) != {"canonical_path", "archived_artifact"}:
            raise ProductAuthorityError(f"archive snapshot item {index} is malformed")
        canonical = item.get("canonical_path")
        if not isinstance(canonical, str) or canonical in by_canonical:
            raise ProductAuthorityError("archive snapshot canonical paths must be unique")
        ref, _ = _validate_ref(repo, item.get("archived_artifact"), f"snapshot[{index}]")
        by_canonical[canonical] = ref
        canonical_path = repo / canonical
        if not canonical_path.is_file() or _file_sha(canonical_path) != ref["sha256"]:
            raise ProductAuthorityError(
                f"canonical product artifact changed after archive preparation: {canonical}"
            )
    for required in REQUIRED_CANONICAL:
        if required.as_posix() not in by_canonical:
            raise ProductAuthorityError(
                f"archive snapshot omits required product artifact: {required.as_posix()}"
            )
    return value, by_canonical


def _decision_register_for_archive(
    repo: Path,
    alignment_input: dict[str, Any],
    alignment_input_path: Path,
    alignment_review_path: Path,
    *,
    project_id: str,
    recorded_at: str,
) -> tuple[dict[str, Any] | None, list[str]]:
    pending = [
        item for item in alignment_input.get("pending_decisions", [])
        if isinstance(item, dict)
    ]
    withdraw = {
        str(item.get("decision_payload_sha256")): item
        for item in pending
        if item.get("disposition") == "WITHDRAW_BY_PRODUCT_ARCHIVE"
    }
    if len(withdraw) != len(pending):
        raise ProductAuthorityError(
            "product archive alignment must withdraw every inventoried pending decision"
        )

    register_path = repo / DECISION_REGISTER_PATH
    if register_path.is_file():
        register, errors = load_decision_register(repo)
        if errors:
            raise ProductAuthorityError("; ".join(errors))
        if register.get("project_id") != project_id:
            raise ProductAuthorityError("decision-card register belongs to another project")
    elif not pending:
        return None, []
    else:
        register = {
            "schema_version": DECISION_REGISTER_VERSION,
            "project_id": project_id,
            "entries": [],
            "updated_at": recorded_at,
        }

    entries = register.get("entries", [])
    by_payload = {
        str(item.get("decision_payload_sha256")): item
        for item in entries if isinstance(item, dict)
    }
    registered_pending = {
        digest for digest, item in by_payload.items() if item.get("state") == "PENDING"
    }
    if registered_pending - set(withdraw):
        raise ProductAuthorityError(
            "alignment omits registered pending decisions: "
            + ", ".join(sorted(registered_pending - set(withdraw)))
        )

    alignment_input_ref = _artifact_ref(repo, alignment_input_path)
    alignment_review_ref = _artifact_ref(repo, alignment_review_path)
    for digest, pending_item in withdraw.items():
        if SHA256_PATTERN.fullmatch(digest) is None:
            raise ProductAuthorityError(f"invalid pending payload SHA: {digest}")
        card_ref, card_path = _validate_ref(
            repo, pending_item.get("decision_card"), f"pending decision {digest}"
        )
        card = _json(card_path, f"pending decision card {digest}")
        if card.get("decision_payload_sha256") != digest:
            raise ProductAuthorityError(f"pending decision card payload differs: {digest}")
        entry = by_payload.get(digest)
        if entry is None:
            entry = {
                "card_id": card.get("card_id"),
                "objective_id": card.get("objective_id"),
                "decision_payload_sha256": digest,
                "decision_card": card_ref,
                "state": "PRODUCT_ARCHIVED",
                "alignment_input": alignment_input_ref,
                "alignment_review": alignment_review_ref,
                "supersedes": [],
                "superseded_by": "",
                "recorded_at": recorded_at,
                "updated_at": recorded_at,
            }
            if not isinstance(entry["card_id"], str) or not isinstance(entry["objective_id"], str):
                raise ProductAuthorityError("pending decision card lacks ids")
            entries.append(entry)
            by_payload[digest] = entry
        else:
            if entry.get("state") != "PENDING":
                raise ProductAuthorityError(
                    f"only a PENDING decision may be withdrawn by product archive: {digest}"
                )
            entry["state"] = "PRODUCT_ARCHIVED"
            entry["alignment_input"] = alignment_input_ref
            entry["alignment_review"] = alignment_review_ref
            entry["updated_at"] = recorded_at
    register["updated_at"] = recorded_at
    return register, sorted(withdraw)


def archive_product_authority(
    game_repo: str | Path,
    snapshot_path: str | Path,
    alignment_input_path: str | Path,
    alignment_review_path: str | Path,
    *,
    recorded_at: str,
) -> ProductAuthorityResult:
    repo = _repo(game_repo)
    if not recorded_at.strip():
        raise ProductAuthorityError("recorded_at is required")
    snapshot_file = _resolve(repo, snapshot_path, must_exist=True)
    alignment_input_file = _resolve(repo, alignment_input_path, must_exist=True)
    alignment_review_file = _resolve(repo, alignment_review_path, must_exist=True)
    snapshot, archive_refs = _load_snapshot(repo, snapshot_file)

    result = validate_alignment_review(repo, alignment_input_file, alignment_review_file)
    if result.errors or result.status != PASS_ALIGNMENT:
        raise ProductAuthorityError(
            "; ".join(result.errors)
            or "product archive requires a fresh PASS_ALIGNMENT review"
        )
    alignment_input = _json(alignment_input_file, "semantic alignment input")
    if alignment_input.get("schema_version") != ALIGNMENT_INPUT_VERSION:
        raise ProductAuthorityError("product archive requires current semantic alignment input")
    if alignment_input.get("proposed_transition") != "ARCHIVE_PRODUCT_DIRECTION":
        raise ProductAuthorityError(
            "product archive alignment must propose ARCHIVE_PRODUCT_DIRECTION"
        )
    if alignment_input.get("project_id") != snapshot.get("project_id"):
        raise ProductAuthorityError("archive alignment project differs from snapshot")
    user_input = alignment_input.get("user_input", {})
    if text_sha256(str(user_input.get("text", ""))) != user_input.get("sha256"):
        raise ProductAuthorityError("archive alignment does not bind exact user input")

    current_refs = _canonical_refs(repo)
    archive_thesis = archive_refs[REQUIRED_CANONICAL[0].as_posix()]
    if current_refs["product_thesis"]["sha256"] != archive_thesis["sha256"]:
        raise ProductAuthorityError("archive snapshot is not the active canonical Product Thesis")

    register_path = repo / REGISTER_PATH
    if register_path.is_file():
        register = _json(register_path, "Product authority register")
        _validate_register(repo, register)
        if register.get("status") != ACTIVE:
            raise ProductAuthorityError("Product Authority Register is already inactive")
        if register["active_authority"]["product_thesis"] != current_refs["product_thesis"]:
            raise ProductAuthorityError("register active thesis differs from canonical thesis")
        history = list(register.get("transitions", []))
    else:
        history = []

    decision_register, withdrawn = _decision_register_for_archive(
        repo,
        alignment_input,
        alignment_input_file,
        alignment_review_file,
        project_id=str(snapshot["project_id"]),
        recorded_at=recorded_at,
    )
    transition = {
        "transition_id": snapshot["transition_id"],
        "action": "ARCHIVED_BY_USER",
        "factory_revision": current_factory_revision(),
        "user_input": {
            "text": user_input["text"],
            "sha256": user_input["sha256"],
        },
        "authority_snapshot": _artifact_ref(repo, snapshot_file),
        "alignment_input": _artifact_ref(repo, alignment_input_file),
        "alignment_review": _artifact_ref(repo, alignment_review_file),
        "withdrawn_pending_payloads": withdrawn,
        "recorded_at": recorded_at,
    }
    if any(item.get("transition_id") == transition["transition_id"] for item in history):
        raise ProductAuthorityError("product archive transition_id already exists")
    history.append(transition)
    product_register = {
        "schema_version": REGISTER_VERSION,
        "project_id": snapshot["project_id"],
        "status": NO_ACTIVE,
        "active_authority": None,
        "transitions": history,
        "updated_at": recorded_at,
    }

    # State becomes fail-closed before canonical pointers disappear.  The
    # immutable archive snapshot and alignment artifacts already exist.
    register_path.parent.mkdir(parents=True, exist_ok=True)
    register_path.write_text(_json_text(product_register), encoding="utf-8")
    created = [REGISTER_PATH.as_posix()]
    if decision_register is not None:
        decision_path = repo / DECISION_REGISTER_PATH
        decision_path.parent.mkdir(parents=True, exist_ok=True)
        decision_path.write_text(_json_text(decision_register), encoding="utf-8")
        created.append(DECISION_REGISTER_PATH)

    removed: list[str] = []
    for canonical in REQUIRED_CANONICAL + OPTIONAL_CANONICAL:
        path = repo / canonical
        if path.is_file():
            path.unlink()
            removed.append(canonical.as_posix())
    return ProductAuthorityResult(
        ARCHIVED,
        created_paths=created,
        verified_paths=[_artifact_ref(repo, snapshot_file)["path"]],
        removed_paths=removed,
    )


def activate_product_authority(
    game_repo: str | Path,
    alignment_input_path: str | Path,
    alignment_review_path: str | Path,
    *,
    authority_id: str,
    recorded_at: str,
) -> ProductAuthorityResult:
    repo = _repo(game_repo)
    if ID_PATTERN.fullmatch(authority_id) is None:
        raise ProductAuthorityError("authority_id is not portable")
    if not recorded_at.strip():
        raise ProductAuthorityError("recorded_at is required")
    refs = _canonical_refs(repo)
    project = _canonical_project(repo)
    product_input = _json(repo / REQUIRED_CANONICAL[2], "Product Thesis input")
    commission = product_input.get("commission")
    if not isinstance(commission, dict) or commission.get("authorized") is not True:
        raise ProductAuthorityError("Product Thesis input has no explicit commission")
    quote = commission.get("authorization_quote")
    if not isinstance(quote, str) or not quote.strip():
        raise ProductAuthorityError("Product Thesis commission quote is missing")

    alignment = validate_alignment_review(
        repo,
        alignment_input_path,
        alignment_review_path,
    )
    if alignment.status != PASS_ALIGNMENT:
        raise ProductAuthorityError(
            "product activation requires PASS_ALIGNMENT: " + "; ".join(alignment.errors)
        )
    if alignment.proposed_transition != "ACTIVATE_PRODUCT_AUTHORITY":
        raise ProductAuthorityError(
            "product activation alignment must propose ACTIVATE_PRODUCT_AUTHORITY"
        )
    expected_changes = {
        ("PRODUCT_THESIS", refs["product_thesis"]["path"], refs["product_thesis"]["sha256"]),
        ("FACTORY_CONSTRAINTS", refs["factory_constraints"]["path"], refs["factory_constraints"]["sha256"]),
        ("PRODUCT_AUTHORITY_INPUT", refs["product_input"]["path"], refs["product_input"]["sha256"]),
        ("IDEA_FACTORY_RESULT", refs["idea_result"]["path"], refs["idea_result"]["sha256"]),
    }
    actual_changes = {
        (
            str(change.get("authority_kind", "")),
            str(change.get("artifact", {}).get("path", "")),
            str(change.get("artifact", {}).get("sha256", "")),
        )
        for change in alignment.authority_changes
        if change.get("operation") == "ACTIVATE"
    }
    if actual_changes != expected_changes:
        raise ProductAuthorityError(
            "product activation alignment must bind the exact four canonical authority artifacts"
        )
    alignment_input_file = Path(alignment_input_path)
    if not alignment_input_file.is_absolute():
        alignment_input_file = repo / alignment_input_file
    alignment_review_file = Path(alignment_review_path)
    if not alignment_review_file.is_absolute():
        alignment_review_file = repo / alignment_review_file
    aligned_input = _json(alignment_input_file.resolve(), "Product activation alignment input")
    aligned_user_input = aligned_input.get("user_input")
    if not isinstance(aligned_user_input, dict):
        raise ProductAuthorityError("product activation alignment has no exact user input")
    aligned_user_text = aligned_user_input.get("text")
    if not isinstance(aligned_user_text, str) or quote not in aligned_user_text:
        raise ProductAuthorityError(
            "Product Thesis commission quote is not present in the activation user input"
        )

    register_path = repo / REGISTER_PATH
    if register_path.is_file():
        register = _json(register_path, "Product authority register")
        _validate_register(repo, register)
        if register.get("project_id") != project:
            raise ProductAuthorityError("Product Authority Register belongs to another project")
        if register.get("status") == ACTIVE:
            active = register["active_authority"]
            if active.get("authority_id") == authority_id and all(
                active.get(key) == refs[key]
                for key in ("product_thesis", "factory_constraints", "product_input", "idea_result")
            ):
                return ProductAuthorityResult(
                    ACTIVATED, verified_paths=[REGISTER_PATH.as_posix()]
                )
            raise ProductAuthorityError("a different Product Thesis is already active")
        history = list(register.get("transitions", []))
    else:
        history = []
    active = {
        "authority_id": authority_id,
        **refs,
        "activated_at": recorded_at,
    }
    history.append(
        {
            "transition_id": f"commission.{authority_id}",
            "action": "COMMISSIONED_BY_USER",
            "factory_revision": current_factory_revision(),
            "user_input": {
                "text": aligned_user_text,
                "sha256": text_sha256(aligned_user_text),
            },
            "authority_snapshot": refs["product_thesis"],
            "alignment_input": path_ref(repo, alignment_input_file),
            "alignment_review": path_ref(repo, alignment_review_file),
            "withdrawn_pending_payloads": [],
            "recorded_at": recorded_at,
        }
    )
    register = {
        "schema_version": REGISTER_VERSION,
        "project_id": project,
        "status": ACTIVE,
        "active_authority": active,
        "transitions": history,
        "updated_at": recorded_at,
    }
    register_path.parent.mkdir(parents=True, exist_ok=True)
    register_path.write_text(_json_text(register), encoding="utf-8")
    return ProductAuthorityResult(ACTIVATED, created_paths=[REGISTER_PATH.as_posix()])


def _print_result(result: ProductAuthorityResult) -> int:
    print(result.status)
    for path in result.created_paths:
        print(f"CREATED: {path}")
    for path in result.verified_paths:
        print(f"VERIFIED: {path}")
    for path in result.removed_paths:
        print(f"ARCHIVED_CANONICAL_REMOVED: {path}")
    for error in result.errors:
        print(f"ERROR: {error}", file=sys.stderr)
    return 0 if not result.errors and result.status != BLOCKED else 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    status = sub.add_parser("status")
    status.add_argument("--game-repo", required=True)
    prepare = sub.add_parser("prepare-archive")
    prepare.add_argument("--game-repo", required=True)
    prepare.add_argument("--transition-id", required=True)
    prepare.add_argument("--prepared-at", required=True)
    archive = sub.add_parser("archive")
    archive.add_argument("--game-repo", required=True)
    archive.add_argument("--snapshot", required=True)
    archive.add_argument("--alignment-input", required=True)
    archive.add_argument("--alignment-review", required=True)
    archive.add_argument("--recorded-at", required=True)
    activate = sub.add_parser("activate")
    activate.add_argument("--game-repo", required=True)
    activate.add_argument("--authority-id", required=True)
    activate.add_argument("--alignment-input", required=True)
    activate.add_argument("--alignment-review", required=True)
    activate.add_argument("--recorded-at", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "status":
            result = product_authority_status(args.game_repo)
        elif args.command == "prepare-archive":
            result = prepare_product_archive(
                args.game_repo, args.transition_id, prepared_at=args.prepared_at
            )
        elif args.command == "archive":
            result = archive_product_authority(
                args.game_repo,
                args.snapshot,
                args.alignment_input,
                args.alignment_review,
                recorded_at=args.recorded_at,
            )
        else:
            result = activate_product_authority(
                args.game_repo,
                args.alignment_input,
                args.alignment_review,
                authority_id=args.authority_id,
                recorded_at=args.recorded_at,
            )
    except (ProductAuthorityError, AlignmentValidationError) as error:
        print(BLOCKED)
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    return _print_result(result)


if __name__ == "__main__":
    raise SystemExit(main())
