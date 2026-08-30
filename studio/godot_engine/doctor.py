"""Fail-closed automation capability and observability diagnosis."""

from __future__ import annotations

import platform
import shutil
from pathlib import Path
from typing import Any, Sequence

from .bridge import bridge_check
from .common import (
    BRIDGE_PROFILE_RELATIVE,
    BRIDGE_MANIFEST_RELATIVE,
    GodotAutomationError,
    OperationResult,
    probe_engine,
    repo_relative,
    resolve_game_repo,
    resolve_in_repo,
    resolve_project_dir,
    sha256_file,
)
from .evidence import EvidenceTransaction
from .schema import load_profile


SUPPORTED_MINORS = {(4, 6), (4, 7)}


def run_doctor(
    game_repo_text: str | Path,
    *,
    operation_id: str,
    project_dir_text: str | Path = ".",
    godot_bin: str | None = None,
    profile_text: str | Path | None = None,
    required_evidence_paths: Sequence[str] = (),
    required_capabilities: Sequence[str] = (),
) -> OperationResult:
    game_repo = resolve_game_repo(game_repo_text)
    project_dir = resolve_project_dir(game_repo, project_dir_text)
    engine = probe_engine(godot_bin)
    automation_manifest: dict[str, Any] = {
        "required_evidence_paths": list(required_evidence_paths),
        "required_capabilities": list(required_capabilities),
    }
    bridge_manifest_path = game_repo / BRIDGE_MANIFEST_RELATIVE
    if bridge_manifest_path.is_file():
        automation_manifest["bridge_install_manifest"] = {
            "path": repo_relative(game_repo, bridge_manifest_path),
            "sha256": sha256_file(bridge_manifest_path),
        }
    transaction = EvidenceTransaction(
        game_repo,
        operation_id=operation_id,
        operation_type="DOCTOR",
        project_dir=project_dir,
        engine=engine,
        automation_manifest=automation_manifest,
    )
    checks: list[dict[str, Any]] = []
    blockers: list[str] = []

    supported = (engine.major, engine.minor) in SUPPORTED_MINORS
    checks.append({"check": "SUPPORTED_GODOT_MINOR", "status": "PASS" if supported else "BLOCKED", "detail": engine.version})
    if not supported:
        blockers.append("official support is limited to Godot 4.6.x and 4.7.x")

    try:
        bridge = bridge_check(game_repo, project_dir_text=repo_relative(game_repo, project_dir))
        checks.append({"check": "BRIDGE_INSTALLATION", "status": bridge.status, "detail": "; ".join(bridge.changes)})
        if bridge.status != "PASS":
            blockers.extend(bridge.changes)
    except GodotAutomationError as error:
        checks.append({"check": "BRIDGE_INSTALLATION", "status": "BLOCKED", "detail": str(error)})
        blockers.append(str(error))

    profile_path = resolve_in_repo(game_repo, profile_text if profile_text is not None else BRIDGE_PROFILE_RELATIVE)
    profile: dict[str, Any] | None = None
    if profile_path.is_file():
        profile = load_profile(profile_path)
        transaction.automation_manifest["profile"] = {
            "path": repo_relative(game_repo, profile_path),
            "sha256": sha256_file(profile_path),
            "profile_id": profile["profile_id"],
        }
        checks.append({"check": "OBSERVATION_PROFILE", "status": "PASS", "detail": profile["profile_id"]})
    else:
        checks.append({"check": "OBSERVATION_PROFILE", "status": "BLOCKED", "detail": "project-owned bridge profile is missing"})
        blockers.append("project-owned bridge profile is missing; Adapter will not invent game-specific instrumentation")

    available = {
        "PROJECT_DISCOVERY", "IMPORT_CHECK", "BOUNDED_RUN", "EXPORT_DEBUG",
        "EXPORT_RELEASE", "BUILD_SMOKE", "EVIDENCE_VERIFY", "EVIDENCE_RECOVER",
        "IMAGE_METRICS",
    }
    if profile is not None:
        available.update({"FRAME_BOUND_EXECUTION", "LIVE_SESSION", "STRUCTURAL_CAPTURE", "PNG_CAPTURE"})
        if profile["observations"]:
            available.add("PROJECT_OBSERVATION")
        if profile["checkpoints"]:
            available.add("PROJECT_CHECKPOINT")
        if profile["project_commands"]:
            available.add("PROJECT_COMMAND")
    missing_capabilities = sorted(set(required_capabilities) - available)
    if missing_capabilities:
        blockers.append("missing required capabilities: " + ", ".join(missing_capabilities))
    checks.append({"check": "REQUIRED_CAPABILITIES", "status": "PASS" if not missing_capabilities else "BLOCKED", "detail": ", ".join(missing_capabilities) if missing_capabilities else "all declared capabilities available"})

    missing_paths: list[str] = []
    for value in required_evidence_paths:
        path = resolve_in_repo(game_repo, value)
        if not path.is_file():
            missing_paths.append(value)
    if missing_paths:
        blockers.append("missing declared evidence paths: " + ", ".join(missing_paths))
    checks.append({"check": "DECLARED_EVIDENCE_PATHS", "status": "PASS" if not missing_paths else "BLOCKED", "detail": ", ".join(missing_paths) if missing_paths else "all declared paths exist"})

    visual_runner = platform.system() != "Linux" or bool(__import__("os").environ.get("DISPLAY")) or shutil.which("Xvfb") is not None
    checks.append({"check": "WINDOWED_VISUAL_RUNNER", "status": "PASS" if visual_runner else "BLOCKED", "detail": "native display/Xvfb available" if visual_runner else "Linux requires DISPLAY or Xvfb"})
    report = {
        "schema_version": "godot_automation_doctor.v1",
        "status": "PASS" if not blockers else "BLOCKED",
        "engine": engine.public(),
        "platform": platform.system(),
        "available_capabilities": sorted(available),
        "checks": checks,
        "blockers": blockers,
        "authority_boundary": "Doctor reports technical gaps only and never injects project-specific instrumentation.",
        "acceptance_authority": "EVIDENCE_ONLY",
        "gameplay_verdict": "NOT_ISSUED",
    }
    transaction.write_json("doctor_report.json", report, "DOCTOR_REPORT")
    return transaction.finalize(
        status=report["status"],
        invocation={"command": "doctor", "working_directory": repo_relative(game_repo, project_dir)},
        result={"doctor": report},
    )
