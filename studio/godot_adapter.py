#!/usr/bin/env python3
"""Godot 4 CLI adapter for Studio-owned runtime evidence.

The adapter is deliberately evidence-only.  It can discover a Godot project,
run deterministic bounded CLI operations, and persist exact logs/results in the
target game repository.  It cannot issue a gameplay verdict or promote an
Accepted Playable Baseline.

Filled artifacts always land in the target game repo under
``design/studio/engine/godot``.  This Factory checkout contains only the
reusable adapter, schemas, documentation, and tests.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from studio.alignment import current_factory_revision
except ModuleNotFoundError:  # pragma: no cover - direct script invocation.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from studio.alignment import current_factory_revision  # type: ignore[no-redef]


FACTORY_ROOT = Path(__file__).resolve().parents[1]
ADAPTER_VERSION = "godot_cli_adapter.v1"
MANIFEST_VERSION = "godot_engine_capability_manifest.v1"
EVIDENCE_VERSION = "godot_engine_evidence.v1"
ADAPTER_ROOT_RELATIVE = Path("design/studio/engine/godot")
MANIFEST_RELATIVE = ADAPTER_ROOT_RELATIVE / "GODOT_ENGINE_CAPABILITY_MANIFEST.json"
EVIDENCE_ROOT_RELATIVE = ADAPTER_ROOT_RELATIVE / "evidence"

ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
ANSI_PATTERN = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
ENGINE_ERROR_PATTERN = re.compile(
    r"^(?:SCRIPT ERROR|ERROR|FATAL ERROR|CRASH):",
    re.IGNORECASE,
)

PASS = "PASS"
FAIL = "FAIL"
TIMEOUT = "TIMEOUT"
READY = "READY"


class GodotAdapterError(ValueError):
    """Raised when the requested adapter operation is unsafe or impossible."""


@dataclass(frozen=True)
class EngineProbe:
    executable: Path
    locator_kind: str
    command_name: str
    version: str
    version_parts: dict[str, Any]
    help_text: str


@dataclass(frozen=True)
class ProcessResult:
    exit_code: int | None
    stdout: str
    stderr: str
    timed_out: bool
    termination: str


@dataclass(frozen=True)
class GodotAdapterResult:
    status: str
    artifact_path: str
    artifact_sha256: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _json_text(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json_text(payload), encoding="utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _directory_digest(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    total = 0
    for candidate in sorted(path.rglob("*"), key=lambda item: item.as_posix()):
        relative = candidate.relative_to(path).as_posix()
        digest.update(relative.encode("utf-8", errors="surrogateescape"))
        digest.update(b"\0")
        if candidate.is_symlink():
            digest.update(b"symlink\0")
            digest.update(candidate.readlink().as_posix().encode("utf-8"))
        elif candidate.is_file():
            data = candidate.read_bytes()
            digest.update(b"file\0")
            digest.update(hashlib.sha256(data).digest())
            total += len(data)
        elif candidate.is_dir():
            digest.update(b"dir\0")
        digest.update(b"\0")
    return digest.hexdigest(), total


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _relative(game_repo: Path, path: Path) -> str:
    resolved = path.resolve()
    if not _is_within(resolved, game_repo):
        raise GodotAdapterError(f"path escapes game repo: {path}")
    value = resolved.relative_to(game_repo).as_posix()
    return value or "."


def _run_git(game_repo: Path, *args: str, binary: bool = False) -> str | bytes:
    result = subprocess.run(
        ["git", "-C", str(game_repo), *args],
        check=False,
        capture_output=True,
        text=not binary,
        encoding=None if binary else "utf-8",
    )
    if result.returncode != 0:
        error = (
            result.stderr.decode("utf-8", errors="replace")
            if binary
            else str(result.stderr)
        ).strip()
        raise GodotAdapterError(error or f"git {' '.join(args)} failed")
    return result.stdout


def _resolve_game_repo(raw_path: str | Path) -> Path:
    game_repo = Path(raw_path).expanduser().resolve()
    if not game_repo.is_dir():
        raise GodotAdapterError(f"game repo does not exist: {game_repo}")
    if game_repo == FACTORY_ROOT or _is_within(game_repo, FACTORY_ROOT):
        raise GodotAdapterError(
            "game repo must not be this Factory checkout or one of its children"
        )
    try:
        git_root = str(_run_git(game_repo, "rev-parse", "--show-toplevel")).strip()
    except GodotAdapterError as error:
        raise GodotAdapterError("Godot adapter requires an existing Git repository") from error
    if Path(git_root).resolve() != game_repo:
        raise GodotAdapterError(f"game repo must be the Git root, not a child: {game_repo}")
    return game_repo


def _resolve_in_repo(
    game_repo: Path,
    raw_path: str | Path,
    *,
    must_exist: bool = False,
) -> Path:
    candidate = Path(raw_path).expanduser()
    resolved = (candidate if candidate.is_absolute() else game_repo / candidate).resolve()
    if not _is_within(resolved, game_repo):
        raise GodotAdapterError(f"path escapes game repo: {raw_path}")
    if must_exist and not resolved.exists():
        raise GodotAdapterError(f"required path does not exist: {raw_path}")
    return resolved


def _resolve_project_dir(game_repo: Path, raw_path: str | Path) -> Path:
    project_dir = _resolve_in_repo(game_repo, raw_path, must_exist=True)
    if not project_dir.is_dir():
        raise GodotAdapterError(f"Godot project path must be a directory: {raw_path}")
    if _is_within(project_dir, game_repo / ADAPTER_ROOT_RELATIVE):
        raise GodotAdapterError("Godot project must not live inside the adapter evidence directory")
    if not (project_dir / "project.godot").is_file():
        raise GodotAdapterError(
            f"Godot project path does not contain project.godot: {_relative(game_repo, project_dir)}"
        )
    return project_dir


def _ignored_source_path(relative: str, ignored_prefixes: Iterable[str]) -> bool:
    return any(relative == prefix or relative.startswith(prefix + "/") for prefix in ignored_prefixes)


def _repository_binding(
    game_repo: Path,
    *,
    ignored_prefixes: Iterable[str] = (),
) -> dict[str, Any]:
    ignored = {ADAPTER_ROOT_RELATIVE.as_posix(), *ignored_prefixes}
    tracked_raw = _run_git(
        game_repo, "diff", "--name-only", "-z", "HEAD", "--", binary=True
    )
    untracked_raw = _run_git(
        game_repo, "ls-files", "--others", "--exclude-standard", "-z", binary=True
    )
    assert isinstance(tracked_raw, bytes)
    assert isinstance(untracked_raw, bytes)
    changed = {
        raw.decode("utf-8", errors="surrogateescape")
        for raw in (*tracked_raw.split(b"\0"), *untracked_raw.split(b"\0"))
        if raw
    }
    selected = sorted(path for path in changed if not _ignored_source_path(path, ignored))
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
    revision = str(_run_git(game_repo, "rev-parse", "HEAD")).strip()
    return {
        "revision": revision,
        "dirty_paths": selected,
        "working_tree_sha256": digest.hexdigest(),
    }


def _parse_version(version: str) -> dict[str, Any]:
    match = re.search(r"(?P<major>\d+)\.(?P<minor>\d+)(?:\.(?P<patch>\d+))?", version)
    if match is None:
        raise GodotAdapterError(f"cannot parse Godot version: {version!r}")
    return {
        "major": int(match.group("major")),
        "minor": int(match.group("minor")),
        "patch": int(match.group("patch") or 0),
    }


def _discover_executable(requested: str | None) -> tuple[Path, str, str]:
    if requested:
        expanded = Path(requested).expanduser()
        if expanded.is_absolute() or expanded.parent != Path("."):
            executable = expanded.resolve()
        else:
            found = shutil.which(requested)
            executable = Path(found).resolve() if found else expanded.resolve()
        kind = "EXPLICIT"
        command_name = expanded.name
    else:
        executable = Path()
        command_name = ""
        kind = "AUTO"
        for name in (os.environ.get("GODOT_BIN", ""), "godot", "godot4", "godot-mono"):
            if not name:
                continue
            found = shutil.which(name)
            if found:
                executable = Path(found).resolve()
                command_name = Path(name).name
                kind = "ENV" if name == os.environ.get("GODOT_BIN") else "PATH"
                break
        if not command_name:
            mac_binary = Path("/Applications/Godot.app/Contents/MacOS/Godot")
            if mac_binary.is_file():
                executable = mac_binary.resolve()
                command_name = "Godot"
                kind = "MACOS_APPLICATION"
    if not command_name or not executable.is_file():
        raise GodotAdapterError(
            "Godot executable not found; install Godot 4 or pass --godot-bin/GODOT_BIN"
        )
    if not os.access(executable, os.X_OK):
        raise GodotAdapterError(f"Godot executable is not executable: {command_name}")
    return executable, kind, command_name


def _run_small_command(command: Sequence[str], *, timeout: float = 15.0) -> str:
    try:
        result = subprocess.run(
            list(command),
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise GodotAdapterError(f"cannot execute {Path(command[0]).name}: {error}") from error
    if result.returncode != 0:
        raise GodotAdapterError(
            result.stderr.strip() or f"{Path(command[0]).name} exited {result.returncode}"
        )
    return ANSI_PATTERN.sub("", result.stdout).strip()


def _probe_engine(requested: str | None) -> EngineProbe:
    executable, locator_kind, command_name = _discover_executable(requested)
    version = _run_small_command([str(executable), "--version"])
    version_parts = _parse_version(version)
    if version_parts["major"] < 4:
        raise GodotAdapterError(f"Godot adapter requires Godot 4 or newer, found {version}")
    help_text = _run_small_command([str(executable), "--help"])
    return EngineProbe(
        executable=executable,
        locator_kind=locator_kind,
        command_name=command_name,
        version=version,
        version_parts=version_parts,
        help_text=help_text,
    )


def _engine_payload(probe: EngineProbe) -> dict[str, Any]:
    return {
        "locator_kind": probe.locator_kind,
        "command_name": probe.command_name,
        "version": probe.version,
        "version_parts": probe.version_parts,
    }


def _capability(
    capability_id: str,
    status: str,
    evidence_kind: str,
    detail: str,
) -> dict[str, str]:
    return {
        "capability_id": capability_id,
        "status": status,
        "evidence_kind": evidence_kind,
        "detail": detail,
    }


def _capabilities(probe: EngineProbe, project_dir: Path) -> list[dict[str, str]]:
    help_text = probe.help_text
    export_configured = (project_dir / "export_presets.cfg").is_file()
    export_switches_available = (
        "--export-debug" in help_text and "--export-release" in help_text
    )
    if not export_switches_available:
        export_status = "UNAVAILABLE"
        export_detail = "This Godot binary does not expose debug/release export switches."
    elif export_configured:
        export_status = "AVAILABLE"
        export_detail = "Godot export presets are present."
    else:
        export_status = "PROJECT_CONFIGURATION_REQUIRED"
        export_detail = "Add export_presets.cfg before requesting a build export."
    return [
        _capability(
            "PROJECT_DISCOVERY",
            "AVAILABLE",
            "CAPABILITY_MANIFEST",
            "Binds project.godot, Git revision, and dirty working-tree bytes.",
        ),
        _capability(
            "HEADLESS_IMPORT_CHECK",
            "AVAILABLE" if "--import" in help_text and "--headless" in help_text else "UNAVAILABLE",
            "ENGINE_PROCESS_EVIDENCE",
            "Runs Godot import/editor initialization and fails on logged engine/script errors.",
        ),
        _capability(
            "BOUNDED_PROJECT_RUN",
            "AVAILABLE" if "--quit-after" in help_text and "--path" in help_text else "UNAVAILABLE",
            "ENGINE_PROCESS_EVIDENCE",
            "Runs a project or scene for a bounded frame/time window and captures exact logs.",
        ),
        _capability(
            "SCENE_RUN",
            "AVAILABLE" if "--scene" in help_text else "UNAVAILABLE",
            "ENGINE_PROCESS_EVIDENCE",
            "Runs one repo-contained res:// scene through the bounded run operation.",
        ),
        _capability(
            "LOG_CAPTURE",
            "AVAILABLE",
            "HASHED_LOGS",
            "Captures stdout, stderr, and the Godot engine log as hashed artifacts.",
        ),
        _capability("EXPORT_DEBUG", export_status, "BUILD_ARTIFACT", export_detail),
        _capability("EXPORT_RELEASE", export_status, "BUILD_ARTIFACT", export_detail),
        _capability(
            "DETERMINISTIC_FRAME_WINDOW",
            "PARTIAL" if "--fixed-fps" in help_text else "NOT_IMPLEMENTED",
            "ENGINE_PROCESS_EVIDENCE",
            "fixed-fps and quit-after are supported; input replay and state assertions are not yet implemented.",
        ),
        _capability(
            "SCREENSHOT_CAPTURE",
            "NOT_IMPLEMENTED",
            "NONE",
            "Godot exposes movie/image capture, but v1 does not yet validate rendered frame artifacts.",
        ),
        _capability(
            "INPUT_INJECTION",
            "NOT_IMPLEMENTED",
            "NONE",
            "Requires a future editor/runtime bridge rather than unsafe ad-hoc project hooks.",
        ),
        _capability(
            "STRUCTURED_RUNTIME_STATE",
            "NOT_IMPLEMENTED",
            "NONE",
            "Requires a future opt-in runtime observation bridge.",
        ),
    ]


def _write_capability_manifest(
    game_repo: Path,
    project_dir: Path,
    probe: EngineProbe,
) -> GodotAdapterResult:
    project_file = project_dir / "project.godot"
    manifest_path = game_repo / MANIFEST_RELATIVE
    payload = {
        "schema_version": MANIFEST_VERSION,
        "adapter_version": ADAPTER_VERSION,
        "status": READY,
        "factory_revision": current_factory_revision(),
        "generated_at": _utc_now(),
        "project": {
            "project_dir": _relative(game_repo, project_dir),
            "project_file": {
                "path": _relative(game_repo, project_file),
                "sha256": _sha256_file(project_file),
            },
            "source_repository": _repository_binding(game_repo),
        },
        "engine": _engine_payload(probe),
        "capabilities": _capabilities(probe, project_dir),
        "blockers": [],
        "authority_boundary": (
            "Engine capabilities and process results are evidence only; they do not issue "
            "a gameplay verdict or promote an Accepted Playable Baseline."
        ),
    }
    _write_json(manifest_path, payload)
    return GodotAdapterResult(READY, MANIFEST_RELATIVE.as_posix(), _sha256_file(manifest_path))


def probe_godot(
    game_repo_text: str | Path,
    *,
    project_dir_text: str | Path = ".",
    godot_bin: str | None = None,
) -> GodotAdapterResult:
    game_repo = _resolve_game_repo(game_repo_text)
    project_dir = _resolve_project_dir(game_repo, project_dir_text)
    probe = _probe_engine(godot_bin)
    return _write_capability_manifest(game_repo, project_dir, probe)


def _artifact(game_repo: Path, path: Path, role: str) -> dict[str, Any]:
    if path.is_dir():
        digest, size = _directory_digest(path)
        kind = "DIRECTORY"
    else:
        digest = _sha256_file(path)
        size = path.stat().st_size
        kind = "FILE"
    return {
        "role": role,
        "kind": kind,
        "path": _relative(game_repo, path),
        "sha256": digest,
        "size_bytes": size,
    }


def _file_observation(game_repo: Path, path: Path) -> dict[str, Any]:
    exists = path.is_file()
    return {
        "path": _relative(game_repo, path),
        "exists": exists,
        "sha256": _sha256_file(path) if exists else "",
    }


def _sanitized_command(
    command: Sequence[str],
    *,
    executable: Path,
    command_name: str,
    game_repo: Path,
) -> list[str]:
    rendered: list[str] = []
    for index, value in enumerate(command):
        if index == 0 and Path(value).resolve() == executable.resolve():
            rendered.append(f"<GODOT_BINARY:{command_name}>")
            continue
        candidate = Path(value)
        if candidate.is_absolute() and _is_within(candidate.resolve(), game_repo):
            rendered.append(f"<GAME_REPO>/{_relative(game_repo, candidate)}")
        else:
            rendered.append(value)
    return rendered


def _terminate_process(process: subprocess.Popen[str]) -> str:
    termination = "TERMINATE"
    try:
        if os.name != "nt":
            os.killpg(process.pid, signal.SIGTERM)
        else:  # pragma: no cover - exercised on Windows CI only.
            process.terminate()
        process.wait(timeout=3)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        termination = "KILL"
        try:
            if os.name != "nt":
                os.killpg(process.pid, signal.SIGKILL)
            else:  # pragma: no cover - exercised on Windows CI only.
                process.kill()
        except ProcessLookupError:
            pass
    return termination


def _run_process(command: Sequence[str], *, cwd: Path, timeout_seconds: float) -> ProcessResult:
    try:
        process = subprocess.Popen(
            list(command),
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            start_new_session=os.name != "nt",
        )
    except OSError as error:
        raise GodotAdapterError(f"cannot start Godot: {error}") from error
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
        return ProcessResult(process.returncode, stdout, stderr, False, "NONE")
    except subprocess.TimeoutExpired:
        termination = _terminate_process(process)
        stdout, stderr = process.communicate()
        return ProcessResult(process.returncode, stdout, stderr, True, termination)


def _detected_errors(*texts: str) -> list[str]:
    found: list[str] = []
    for text in texts:
        clean = ANSI_PATTERN.sub("", text)
        for raw_line in clean.splitlines():
            line = raw_line.strip()
            if ENGINE_ERROR_PATTERN.match(line) and line not in found:
                found.append(line)
            if len(found) >= 100:
                return found
    return found


def _resolve_scene(project_dir: Path, raw_scene: str | None) -> str | None:
    if raw_scene is None:
        return None
    if not raw_scene.startswith("res://"):
        raise GodotAdapterError("scene must use a repo-contained res:// path")
    relative = raw_scene[len("res://") :]
    if not relative or relative.startswith("/"):
        raise GodotAdapterError("scene must name a file below res://")
    scene_path = (project_dir / relative).resolve()
    if not _is_within(scene_path, project_dir) or not scene_path.is_file():
        raise GodotAdapterError(f"scene does not exist inside the Godot project: {raw_scene}")
    return raw_scene


def _execute_operation(
    game_repo_text: str | Path,
    *,
    project_dir_text: str | Path,
    godot_bin: str | None,
    operation_id: str,
    operation_type: str,
    engine_args: Sequence[str],
    timeout_seconds: float,
    headless: bool,
    expected_output: Sequence[str] = (),
    allowed_artifact: Path | None = None,
) -> GodotAdapterResult:
    if ID_PATTERN.fullmatch(operation_id) is None:
        raise GodotAdapterError(f"operation id must match {ID_PATTERN.pattern}")
    if timeout_seconds <= 0:
        raise GodotAdapterError("timeout seconds must be greater than zero")
    if any(not isinstance(marker, str) or not marker for marker in expected_output):
        raise GodotAdapterError("expected output markers must be non-empty strings")

    game_repo = _resolve_game_repo(game_repo_text)
    project_dir = _resolve_project_dir(game_repo, project_dir_text)
    evidence_dir = game_repo / EVIDENCE_ROOT_RELATIVE / operation_id
    evidence_path = evidence_dir / "GODOT_ENGINE_EVIDENCE.json"
    if evidence_dir.exists():
        raise GodotAdapterError(
            f"operation evidence is immutable and already exists: {_relative(game_repo, evidence_dir)}"
        )

    probe = _probe_engine(godot_bin)
    probe_result = _write_capability_manifest(game_repo, project_dir, probe)
    evidence_dir.mkdir(parents=True)
    stdout_path = evidence_dir / "stdout.log"
    stderr_path = evidence_dir / "stderr.log"
    engine_log_path = evidence_dir / "godot.log"

    ignored_prefixes: list[str] = []
    if allowed_artifact is not None:
        ignored_prefixes.append(_relative(game_repo, allowed_artifact))
    repository_before = _repository_binding(game_repo, ignored_prefixes=ignored_prefixes)
    project_file = project_dir / "project.godot"
    project_file_before = _file_observation(game_repo, project_file)

    command = [str(probe.executable)]
    if headless:
        command.append("--headless")
    command.extend(["--path", str(project_dir), *engine_args, "--log-file", str(engine_log_path)])

    started_at = _utc_now()
    started_clock = time.monotonic()
    process_result = _run_process(command, cwd=project_dir, timeout_seconds=timeout_seconds)
    duration_ms = round((time.monotonic() - started_clock) * 1000)
    finished_at = _utc_now()

    stdout_path.write_text(process_result.stdout, encoding="utf-8")
    stderr_path.write_text(process_result.stderr, encoding="utf-8")
    if not engine_log_path.exists():
        engine_log_path.write_text("", encoding="utf-8")
    engine_log = engine_log_path.read_text(encoding="utf-8", errors="replace")

    detected_errors = _detected_errors(
        process_result.stdout,
        process_result.stderr,
        engine_log,
    )
    combined_output = f"{process_result.stdout}\n{process_result.stderr}\n{engine_log}"
    assertions = [
        {
            "assertion": "OUTPUT_CONTAINS",
            "expected": marker,
            "passed": marker in combined_output,
        }
        for marker in expected_output
    ]
    repository_after = _repository_binding(game_repo, ignored_prefixes=ignored_prefixes)
    project_file_after = _file_observation(game_repo, project_file)
    source_mutated = repository_before != repository_after

    if process_result.timed_out:
        status = TIMEOUT
    elif (
        process_result.exit_code != 0
        or detected_errors
        or any(not item["passed"] for item in assertions)
        or source_mutated
    ):
        status = FAIL
    else:
        status = PASS

    artifacts = [
        _artifact(game_repo, stdout_path, "STDOUT_LOG"),
        _artifact(game_repo, stderr_path, "STDERR_LOG"),
        _artifact(game_repo, engine_log_path, "GODOT_ENGINE_LOG"),
    ]
    if allowed_artifact is not None and allowed_artifact.exists():
        artifacts.append(_artifact(game_repo, allowed_artifact, "EXPORTED_BUILD"))

    manifest_path = game_repo / probe_result.artifact_path
    payload = {
        "schema_version": EVIDENCE_VERSION,
        "adapter_version": ADAPTER_VERSION,
        "operation_id": operation_id,
        "operation_type": operation_type,
        "status": status,
        "factory_revision": current_factory_revision(),
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_ms": duration_ms,
        "project": {
            "project_dir": _relative(game_repo, project_dir),
            "project_file_before": project_file_before,
            "project_file_after": project_file_after,
            "source_repository_before": repository_before,
            "source_repository_after": repository_after,
            "source_mutated": source_mutated,
        },
        "engine": _engine_payload(probe),
        "capability_manifest": {
            "path": probe_result.artifact_path,
            "sha256": _sha256_file(manifest_path),
        },
        "invocation": {
            "command": _sanitized_command(
                command,
                executable=probe.executable,
                command_name=probe.command_name,
                game_repo=game_repo,
            ),
            "working_directory": _relative(game_repo, project_dir),
            "timeout_seconds": timeout_seconds,
            "headless": headless,
        },
        "result": {
            "exit_code": process_result.exit_code,
            "timed_out": process_result.timed_out,
            "termination": process_result.termination,
            "detected_errors": detected_errors,
            "assertions": assertions,
        },
        "artifacts": artifacts,
        "acceptance_authority": "EVIDENCE_ONLY",
        "gameplay_verdict": "NOT_ISSUED",
        "limitations": [
            "A passing process run proves only the recorded engine operation and assertions.",
            "Input injection, structured runtime state, and validated screenshots are not implemented in v1.",
            "This evidence cannot replace fresh gameplay acceptance or a human playtest verdict.",
        ],
    }
    _write_json(evidence_path, payload)
    return GodotAdapterResult(status, _relative(game_repo, evidence_path), _sha256_file(evidence_path))


def import_check_godot(
    game_repo_text: str | Path,
    *,
    operation_id: str,
    project_dir_text: str | Path = ".",
    godot_bin: str | None = None,
    timeout_seconds: float = 120.0,
) -> GodotAdapterResult:
    return _execute_operation(
        game_repo_text,
        project_dir_text=project_dir_text,
        godot_bin=godot_bin,
        operation_id=operation_id,
        operation_type="IMPORT_CHECK",
        engine_args=["--import"],
        timeout_seconds=timeout_seconds,
        headless=True,
    )


def run_godot(
    game_repo_text: str | Path,
    *,
    operation_id: str,
    project_dir_text: str | Path = ".",
    godot_bin: str | None = None,
    scene: str | None = None,
    timeout_seconds: float = 30.0,
    quit_after: int = 2,
    fixed_fps: int = 60,
    headless: bool = True,
    expected_output: Sequence[str] = (),
) -> GodotAdapterResult:
    if quit_after < 1:
        raise GodotAdapterError("quit-after must be at least 1")
    if fixed_fps < 1:
        raise GodotAdapterError("fixed-fps must be at least 1")
    game_repo = _resolve_game_repo(game_repo_text)
    project_dir = _resolve_project_dir(game_repo, project_dir_text)
    resolved_scene = _resolve_scene(project_dir, scene)
    args: list[str] = ["--fixed-fps", str(fixed_fps), "--quit-after", str(quit_after)]
    if resolved_scene is not None:
        args.extend(["--scene", resolved_scene])
    return _execute_operation(
        game_repo,
        project_dir_text=_relative(game_repo, project_dir),
        godot_bin=godot_bin,
        operation_id=operation_id,
        operation_type="RUN_SCENE" if resolved_scene else "RUN_PROJECT",
        engine_args=args,
        timeout_seconds=timeout_seconds,
        headless=headless,
        expected_output=expected_output,
    )


def export_godot(
    game_repo_text: str | Path,
    *,
    operation_id: str,
    preset: str,
    output: str | Path,
    mode: str = "debug",
    project_dir_text: str | Path = ".",
    godot_bin: str | None = None,
    timeout_seconds: float = 600.0,
) -> GodotAdapterResult:
    if not preset.strip():
        raise GodotAdapterError("export preset must not be empty")
    if mode not in {"debug", "release"}:
        raise GodotAdapterError("export mode must be debug or release")
    game_repo = _resolve_game_repo(game_repo_text)
    project_dir = _resolve_project_dir(game_repo, project_dir_text)
    if not (project_dir / "export_presets.cfg").is_file():
        raise GodotAdapterError("export requires project export_presets.cfg")
    output_path = _resolve_in_repo(game_repo, output)
    if _is_within(output_path, game_repo / ADAPTER_ROOT_RELATIVE):
        raise GodotAdapterError("export output must not be inside the adapter evidence directory")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    switch = "--export-debug" if mode == "debug" else "--export-release"
    return _execute_operation(
        game_repo,
        project_dir_text=_relative(game_repo, project_dir),
        godot_bin=godot_bin,
        operation_id=operation_id,
        operation_type="EXPORT_DEBUG" if mode == "debug" else "EXPORT_RELEASE",
        engine_args=[switch, preset, str(output_path)],
        timeout_seconds=timeout_seconds,
        headless=True,
        allowed_artifact=output_path,
    )


def _common_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--game-repo", required=True)
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--godot-bin", default=None)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    probe_parser = subparsers.add_parser("probe", help="write the capability manifest")
    _common_parser(probe_parser)

    import_parser = subparsers.add_parser("import-check", help="run headless import validation")
    _common_parser(import_parser)
    import_parser.add_argument("--operation-id", required=True)
    import_parser.add_argument("--timeout-seconds", type=float, default=120.0)

    run_parser = subparsers.add_parser("run", help="run the project/scene for a bounded window")
    _common_parser(run_parser)
    run_parser.add_argument("--operation-id", required=True)
    run_parser.add_argument("--scene", default=None)
    run_parser.add_argument("--timeout-seconds", type=float, default=30.0)
    run_parser.add_argument("--quit-after", type=int, default=2)
    run_parser.add_argument("--fixed-fps", type=int, default=60)
    run_parser.add_argument("--windowed", action="store_true")
    run_parser.add_argument("--expect-output", action="append", default=[])

    export_parser = subparsers.add_parser("export", help="export a debug/release build")
    _common_parser(export_parser)
    export_parser.add_argument("--operation-id", required=True)
    export_parser.add_argument("--preset", required=True)
    export_parser.add_argument("--output", required=True)
    export_parser.add_argument("--mode", choices=("debug", "release"), default="debug")
    export_parser.add_argument("--timeout-seconds", type=float, default=600.0)
    return parser


def _print_result(result: GodotAdapterResult) -> None:
    print(
        json.dumps(
            {
                "status": result.status,
                "artifact_path": result.artifact_path,
                "artifact_sha256": result.artifact_sha256,
            },
            sort_keys=True,
        )
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "probe":
            result = probe_godot(
                args.game_repo,
                project_dir_text=args.project_dir,
                godot_bin=args.godot_bin,
            )
        elif args.command == "import-check":
            result = import_check_godot(
                args.game_repo,
                operation_id=args.operation_id,
                project_dir_text=args.project_dir,
                godot_bin=args.godot_bin,
                timeout_seconds=args.timeout_seconds,
            )
        elif args.command == "run":
            result = run_godot(
                args.game_repo,
                operation_id=args.operation_id,
                project_dir_text=args.project_dir,
                godot_bin=args.godot_bin,
                scene=args.scene,
                timeout_seconds=args.timeout_seconds,
                quit_after=args.quit_after,
                fixed_fps=args.fixed_fps,
                headless=not args.windowed,
                expected_output=args.expect_output,
            )
        else:
            result = export_godot(
                args.game_repo,
                operation_id=args.operation_id,
                project_dir_text=args.project_dir,
                godot_bin=args.godot_bin,
                preset=args.preset,
                output=args.output,
                mode=args.mode,
                timeout_seconds=args.timeout_seconds,
            )
    except GodotAdapterError as error:
        print(f"GODOT_ADAPTER_ERROR: {error}", file=sys.stderr)
        return 2
    _print_result(result)
    return 0 if result.status in {READY, PASS} else 2


if __name__ == "__main__":
    raise SystemExit(main())
