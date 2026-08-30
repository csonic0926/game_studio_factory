"""Versioned runtime bridge addon installer and profile checks."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .common import (
    BRIDGE_MANIFEST_RELATIVE,
    BRIDGE_PROFILE_RELATIVE,
    BRIDGE_SOURCE_ROOT,
    BRIDGE_VENDOR_RELATIVE,
    BRIDGE_VERSION,
    GodotAutomationError,
    OperationResult,
    atomic_write_bytes,
    atomic_write_json,
    load_json,
    repo_relative,
    resolve_game_repo,
    resolve_project_dir,
    sha256_file,
    utc_now,
)
from .schema import load_profile, validate_profile
from .evidence import EvidenceTransaction


AUTOLOAD_NAME = "GameStudioGodotBridge"
AUTOLOAD_VALUE = "*res://addons/game_studio_godot_bridge/bridge.gd"


@dataclass(frozen=True)
class BridgePlan:
    status: str
    action: str
    apply_required: bool
    changes: tuple[str, ...]

    def public(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "action": self.action,
            "apply_required": self.apply_required,
            "changes": list(self.changes),
            "acceptance_authority": "EVIDENCE_ONLY",
            "gameplay_verdict": "NOT_ISSUED",
        }


def _source_files() -> list[Path]:
    files = sorted(path for path in BRIDGE_SOURCE_ROOT.rglob("*") if path.is_file())
    if not files:
        raise GodotAutomationError("Factory bridge addon source is missing")
    return files


def _manifest_path(game_repo: Path) -> Path:
    return game_repo / BRIDGE_MANIFEST_RELATIVE


def _read_manifest(game_repo: Path) -> dict[str, Any] | None:
    path = _manifest_path(game_repo)
    if not path.exists():
        return None
    payload = load_json(path)
    if not isinstance(payload, dict) or payload.get("schema_version") != "godot_bridge_install_manifest.v1":
        raise GodotAutomationError("existing bridge install manifest has an unsupported schema")
    return payload


def _autoload_line() -> str:
    return f'{AUTOLOAD_NAME}="{AUTOLOAD_VALUE}"'


def _add_autoload(project_file: Path) -> None:
    text = project_file.read_text(encoding="utf-8")
    wanted = _autoload_line()
    if wanted in text.splitlines():
        return
    for line in text.splitlines():
        if line.strip().startswith(AUTOLOAD_NAME + "="):
            raise GodotAutomationError(f"project.godot already defines conflicting autoload {AUTOLOAD_NAME}")
    lines = text.splitlines()
    section_index = next((index for index, line in enumerate(lines) if line.strip() == "[autoload]"), None)
    if section_index is None:
        rendered = text.rstrip() + f"\n\n[autoload]\n{wanted}\n"
    else:
        insert = len(lines)
        for index in range(section_index + 1, len(lines)):
            if lines[index].strip().startswith("["):
                insert = index
                break
        lines.insert(insert, wanted)
        rendered = "\n".join(lines) + "\n"
    atomic_write_bytes(project_file, rendered.encode("utf-8"))


def _remove_autoload(project_file: Path) -> None:
    text = project_file.read_text(encoding="utf-8")
    lines = text.splitlines()
    wanted = _autoload_line()
    conflicts = [line for line in lines if line.strip().startswith(AUTOLOAD_NAME + "=") and line.strip() != wanted]
    if conflicts:
        raise GodotAutomationError(f"autoload {AUTOLOAD_NAME} was manually changed; refusing removal")
    lines = [line for line in lines if line.strip() != wanted]
    atomic_write_bytes(project_file, ("\n".join(lines).rstrip() + "\n").encode("utf-8"))


def _verify_vendor(game_repo: Path, manifest: dict[str, Any]) -> None:
    expected: set[Path] = set()
    for item in manifest.get("vendor_files", []):
        path = game_repo / item["path"]
        expected.add(path.resolve())
        if not path.is_file() or sha256_file(path) != item["sha256"]:
            raise GodotAutomationError(
                f"bridge vendor drift detected; refusing to overwrite or remove: {item.get('path')}"
            )
    project_dir = game_repo / manifest["project_dir"]
    vendor_root = project_dir / BRIDGE_VENDOR_RELATIVE
    actual = {path.resolve() for path in vendor_root.rglob("*") if path.is_file()} if vendor_root.exists() else set()
    if actual != expected:
        extra = sorted(path.name for path in actual - expected)
        missing = sorted(path.name for path in expected - actual)
        raise GodotAutomationError(
            f"bridge vendor file set drift detected; extra={extra}, missing={missing}"
        )


def bridge_check(
    game_repo_text: str | Path,
    *,
    project_dir_text: str | Path = ".",
) -> BridgePlan:
    game_repo = resolve_game_repo(game_repo_text)
    project_dir = resolve_project_dir(game_repo, project_dir_text)
    manifest = _read_manifest(game_repo)
    if manifest is None:
        return BridgePlan("BLOCKED", "CHECK", False, ("bridge is not installed",))
    _verify_vendor(game_repo, manifest)
    if manifest["project_dir"] != repo_relative(game_repo, project_dir):
        raise GodotAutomationError("bridge manifest belongs to a different project_dir")
    if manifest["autoload_enabled"] and _autoload_line() not in (project_dir / "project.godot").read_text(encoding="utf-8").splitlines():
        raise GodotAutomationError("bridge autoload manifest and project.godot disagree")
    profile_path = game_repo / BRIDGE_PROFILE_RELATIVE
    changes = ["vendor files match installation manifest"]
    if profile_path.exists():
        load_profile(profile_path)
        changes.append("project-owned bridge profile is valid")
    else:
        changes.append("project-owned bridge profile is missing")
    status = "PASS" if profile_path.exists() else "BLOCKED"
    return BridgePlan(status, "CHECK", False, tuple(changes))


def bridge_install(
    game_repo_text: str | Path,
    *,
    project_dir_text: str | Path = ".",
    apply: bool = False,
    autoload: bool = False,
    operation_id: str | None = None,
) -> BridgePlan | OperationResult:
    game_repo = resolve_game_repo(game_repo_text)
    project_dir = resolve_project_dir(game_repo, project_dir_text)
    manifest = _read_manifest(game_repo)
    if manifest is not None:
        _verify_vendor(game_repo, manifest)
        return BridgePlan("PASS", "INSTALL", False, ("matching bridge installation already exists",))
    destination = project_dir / BRIDGE_VENDOR_RELATIVE
    if destination.exists() and any(destination.iterdir()):
        raise GodotAutomationError("unmanaged bridge addon directory already exists; refusing overwrite")
    changes = [f"copy {len(_source_files())} versioned vendor files to {repo_relative(game_repo, destination)}"]
    if autoload:
        changes.append(f"enable opt-in autoload {AUTOLOAD_NAME} in project.godot")
    if not apply:
        return BridgePlan("PASS", "INSTALL", True, tuple(changes))
    if not operation_id:
        raise GodotAutomationError("bridge install --apply requires --operation-id")
    transaction = EvidenceTransaction(
        game_repo,
        operation_id=operation_id,
        operation_type="BRIDGE_INSTALL",
        project_dir=project_dir,
        engine=None,
        automation_manifest={"bridge_version": BRIDGE_VERSION, "autoload": autoload},
        source_mutation_allowed=True,
    )
    records: list[dict[str, str]] = []
    for source in _source_files():
        relative = source.relative_to(BRIDGE_SOURCE_ROOT)
        target = destination / relative
        atomic_write_bytes(target, source.read_bytes())
        records.append({"path": repo_relative(game_repo, target), "sha256": sha256_file(target)})
    if autoload:
        _add_autoload(project_dir / "project.godot")
    payload = {
        "schema_version": "godot_bridge_install_manifest.v1",
        "bridge_version": BRIDGE_VERSION,
        "installed_at": utc_now(),
        "project_dir": repo_relative(game_repo, project_dir),
        "autoload_enabled": autoload,
        "autoload_name": AUTOLOAD_NAME,
        "vendor_files": records,
        "project_file_sha256_after": sha256_file(project_dir / "project.godot"),
        "acceptance_authority": "EVIDENCE_ONLY",
        "gameplay_verdict": "NOT_ISSUED",
    }
    path = _manifest_path(game_repo)
    atomic_write_json(path, payload)
    transaction.write_json("bridge_install_manifest.json", payload, "BRIDGE_INSTALL_MANIFEST")
    return transaction.finalize(
        status="PASS",
        invocation={"command": "bridge install --apply", "autoload": autoload},
        result={"install_manifest": {"path": repo_relative(game_repo, path), "sha256": sha256_file(path)}},
    )


def bridge_upgrade(
    game_repo_text: str | Path,
    *,
    project_dir_text: str | Path = ".",
    apply: bool = False,
    operation_id: str | None = None,
) -> BridgePlan | OperationResult:
    game_repo = resolve_game_repo(game_repo_text)
    project_dir = resolve_project_dir(game_repo, project_dir_text)
    manifest = _read_manifest(game_repo)
    if manifest is None:
        raise GodotAutomationError("bridge is not installed; use bridge install")
    _verify_vendor(game_repo, manifest)
    changes = (f"replace hash-matching vendor files with {BRIDGE_VERSION}", "preserve project profile and provider")
    if not apply:
        return BridgePlan("PASS", "UPGRADE", True, changes)
    if not operation_id:
        raise GodotAutomationError("bridge upgrade --apply requires --operation-id")
    transaction = EvidenceTransaction(
        game_repo,
        operation_id=operation_id,
        operation_type="BRIDGE_UPGRADE",
        project_dir=project_dir,
        engine=None,
        automation_manifest={"bridge_version": BRIDGE_VERSION},
        source_mutation_allowed=True,
    )
    autoload = bool(manifest["autoload_enabled"])
    destination = project_dir / BRIDGE_VENDOR_RELATIVE
    expected_paths: set[Path] = set()
    records: list[dict[str, str]] = []
    for source in _source_files():
        target = destination / source.relative_to(BRIDGE_SOURCE_ROOT)
        expected_paths.add(target.resolve())
        atomic_write_bytes(target, source.read_bytes())
        records.append({"path": repo_relative(game_repo, target), "sha256": sha256_file(target)})
    for item in manifest["vendor_files"]:
        old = (game_repo / item["path"]).resolve()
        if old not in expected_paths and old.exists():
            old.unlink()
    payload = {**manifest, "bridge_version": BRIDGE_VERSION, "installed_at": utc_now(), "vendor_files": records, "project_file_sha256_after": sha256_file(project_dir / "project.godot")}
    path = _manifest_path(game_repo)
    atomic_write_json(path, payload)
    transaction.write_json("bridge_install_manifest.json", payload, "BRIDGE_INSTALL_MANIFEST")
    return transaction.finalize(
        status="PASS",
        invocation={"command": "bridge upgrade --apply"},
        result={"install_manifest": {"path": repo_relative(game_repo, path), "sha256": sha256_file(path)}},
    )


def bridge_remove(
    game_repo_text: str | Path,
    *,
    project_dir_text: str | Path = ".",
    apply: bool = False,
    operation_id: str | None = None,
) -> BridgePlan | OperationResult:
    game_repo = resolve_game_repo(game_repo_text)
    project_dir = resolve_project_dir(game_repo, project_dir_text)
    manifest = _read_manifest(game_repo)
    if manifest is None:
        return BridgePlan("PASS", "REMOVE", False, ("bridge is already absent",))
    _verify_vendor(game_repo, manifest)
    changes = ("remove only hash-matching vendor files", "preserve project profile and provider")
    if not apply:
        return BridgePlan("PASS", "REMOVE", True, changes)
    if not operation_id:
        raise GodotAutomationError("bridge remove --apply requires --operation-id")
    transaction = EvidenceTransaction(
        game_repo,
        operation_id=operation_id,
        operation_type="BRIDGE_REMOVE",
        project_dir=project_dir,
        engine=None,
        automation_manifest={"bridge_version": manifest["bridge_version"]},
        source_mutation_allowed=True,
    )
    if manifest["autoload_enabled"]:
        _remove_autoload(project_dir / "project.godot")
    for item in manifest["vendor_files"]:
        (game_repo / item["path"]).unlink()
    vendor_root = project_dir / BRIDGE_VENDOR_RELATIVE
    for directory in sorted((path for path in vendor_root.rglob("*") if path.is_dir()), reverse=True):
        try:
            directory.rmdir()
        except OSError:
            pass
    try:
        vendor_root.rmdir()
    except OSError:
        pass
    _manifest_path(game_repo).unlink()
    report = {"status": "PASS", "removed_bridge_version": manifest["bridge_version"], "profile_preserved": (game_repo / BRIDGE_PROFILE_RELATIVE).exists(), "acceptance_authority": "EVIDENCE_ONLY", "gameplay_verdict": "NOT_ISSUED"}
    report_path = transaction.write_json("bridge_removal_report.json", report, "BRIDGE_REMOVAL_REPORT")
    return transaction.finalize(
        status="PASS",
        invocation={"command": "bridge remove --apply"},
        result={"removal_report": {"path": repo_relative(game_repo, report_path), "sha256": sha256_file(report_path)}},
    )


def profile_validate(path: str | Path) -> dict[str, Any]:
    profile_path = Path(path).expanduser().resolve()
    profile = load_profile(profile_path)
    return {
        "status": "PASS",
        "schema_version": profile["schema_version"],
        "profile_id": profile["profile_id"],
        "sha256": sha256_file(profile_path),
        "capabilities": {
            "input_actions": len(profile["allowed_input_actions"]),
            "project_commands": len(profile["project_commands"]),
            "observations": len(profile["observations"]),
            "checkpoints": len(profile["checkpoints"]),
            "structural_nodes": len(profile["structural_nodes"]),
        },
    }


def write_profile(path: Path, payload: dict[str, Any]) -> None:
    validate_profile(payload)
    if path.exists():
        raise GodotAutomationError("project-owned profile already exists and is never overwritten")
    atomic_write_json(path, payload)
