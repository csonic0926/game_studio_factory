"""Bounded editor/debug/release runtime launch verification."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Sequence

from .common import (
    GodotAutomationError,
    OperationResult,
    probe_engine,
    repo_relative,
    resolve_game_repo,
    resolve_in_repo,
    resolve_project_dir,
    run_process,
    sanitize_command,
)
from .evidence import EvidenceTransaction


def resolve_build_launcher(build_path: Path) -> Path:
    if build_path.is_file():
        if os.name != "nt" and not os.access(build_path, os.X_OK):
            raise GodotAutomationError(f"build is not executable: {build_path.name}")
        return build_path
    if build_path.is_dir() and build_path.suffix.lower() == ".app":
        candidates = sorted(path for path in (build_path / "Contents" / "MacOS").iterdir() if path.is_file() and os.access(path, os.X_OK))
        if len(candidates) != 1:
            raise GodotAutomationError("macOS app bundle must contain exactly one executable launcher")
        return candidates[0]
    raise GodotAutomationError("build path must be an executable file or macOS .app bundle")


def build_launcher_command(launcher: Path, arguments: Sequence[str]) -> list[str]:
    """Return a no-shell launcher command, with explicit Windows batch support."""
    if os.name == "nt" and launcher.suffix.lower() in {".cmd", ".bat"}:
        return [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/s", "/c", str(launcher), *arguments]
    return [str(launcher), *arguments]


def run_build(
    game_repo_text: str | Path,
    *,
    operation_id: str,
    build_text: str | Path,
    mode: str,
    project_dir_text: str | Path = ".",
    godot_bin: str | None = None,
    arguments: Sequence[str] = (),
    timeout_seconds: float = 30.0,
    expected_exit_code: int = 0,
    expected_output: Sequence[str] = (),
) -> OperationResult:
    if mode not in {"debug", "release"}:
        raise GodotAutomationError("build mode must be debug or release")
    if any(not isinstance(item, str) or not item for item in expected_output):
        raise GodotAutomationError("expected output markers must be non-empty strings")
    if any(value == "--studio-adapter-enabled" or value.startswith("--studio-token") for value in arguments):
        if mode == "release":
            raise GodotAutomationError("release smoke runs forbid bridge activation arguments")
        raise GodotAutomationError("use scenario/session commands, not build run, for debug bridge control")
    game_repo = resolve_game_repo(game_repo_text)
    project_dir = resolve_project_dir(game_repo, project_dir_text)
    engine = probe_engine(godot_bin)
    build_path = resolve_in_repo(game_repo, build_text, must_exist=True)
    launcher = resolve_build_launcher(build_path)
    transaction = EvidenceTransaction(
        game_repo,
        operation_id=operation_id,
        operation_type="BUILD_RUN",
        project_dir=project_dir,
        engine=engine,
        automation_manifest={
            "build": repo_relative(game_repo, build_path),
            "mode": mode,
            "bridge_enabled": False,
        },
    )
    godot_log_path = transaction.path("godot.log")
    command = build_launcher_command(
        launcher,
        ["--log-file", str(godot_log_path), *arguments],
    )
    capture = run_process(command, cwd=launcher.parent, timeout_seconds=timeout_seconds)
    stdout_path = transaction.write_text("stdout.log", capture.stdout, "STDOUT_LOG")
    stderr_path = transaction.write_text("stderr.log", capture.stderr, "STDERR_LOG")
    transaction.register(build_path, "EXPORTED_BUILD")
    if godot_log_path.exists():
        transaction.scrub_text_file(godot_log_path)
        transaction.register(godot_log_path, "GODOT_LOG")
    combined = capture.stdout + "\n" + capture.stderr
    assertions = [
        {
            "assertion_id": f"output.contains.{index}",
            "status": "PASS" if marker in combined else "FAIL",
            "expected": marker,
            "actual": marker if marker in combined else None,
            "detail": "bounded build output marker",
        }
        for index, marker in enumerate(expected_output)
    ]
    assertions.insert(
        0,
        {
            "assertion_id": "process.exit_code",
            "status": "PASS" if capture.exit_code == expected_exit_code else "FAIL",
            "expected": expected_exit_code,
            "actual": capture.exit_code,
            "detail": f"{mode} build bounded smoke exit",
        },
    )
    if capture.timed_out:
        status = "TIMEOUT"
    elif all(item["status"] == "PASS" for item in assertions):
        status = "PASS"
    else:
        status = "FAIL"
    return transaction.finalize(
        status=status,
        invocation={
            "command": sanitize_command(command, game_repo=game_repo),
            "working_directory": repo_relative(game_repo, launcher.parent),
            "timeout_seconds": timeout_seconds,
            "headless": False,
        },
        result={
            "process": {
                "exit_code": capture.exit_code,
                "timed_out": capture.timed_out,
                "termination": capture.termination,
                "duration_ms": capture.duration_ms,
            },
            "release_bridge_disabled": mode == "release",
        },
        assertions=assertions,
        limitations=[
            "A release PASS is only a bounded launch/crash/log smoke result.",
            "No build run issues a gameplay verdict or promotes a baseline.",
        ],
    )
