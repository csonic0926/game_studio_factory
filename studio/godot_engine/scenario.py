"""Frame-bound scenario execution and deterministic trace replay."""

from __future__ import annotations

import json
import secrets
import socket
import subprocess
from pathlib import Path
from typing import Any

from .bridge import bridge_check
from .build import build_launcher_command, resolve_build_launcher
from .capability import BRIDGE_CAPABILITIES
from .common import (
    BRIDGE_PROFILE_RELATIVE,
    BRIDGE_MANIFEST_RELATIVE,
    GodotAutomationError,
    OperationResult,
    load_json,
    probe_engine,
    repo_relative,
    resolve_game_repo,
    resolve_in_repo,
    resolve_project_dir,
    run_process,
    sanitize_command,
    sha256_file,
    start_xvfb_if_needed,
    stop_xvfb,
)
from .evidence import EvidenceTransaction
from .schema import load_profile, load_scenario


def _free_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as stream:
        stream.bind(("127.0.0.1", 0))
        return int(stream.getsockname()[1])


def _has_visual_steps(scenario: dict[str, Any]) -> bool:
    return any(step["type"] in {"capture_png", "movie_marker"} for step in scenario["steps"])


def _profile_blockers(scenario: dict[str, Any], profile: dict[str, Any]) -> list[str]:
    """Reject scenario/profile mismatches before launching project code."""
    blockers: list[str] = []
    generic_observations = {"bridge.frame", "bridge.scene", "bridge.viewport", "bridge.input_map"}
    checkpoint = scenario.get("initial_checkpoint")
    if checkpoint is not None and checkpoint not in profile["checkpoints"]:
        blockers.append(f"initial checkpoint is not allowlisted: {checkpoint}")
    for index, step in enumerate(scenario["steps"]):
        kind = step["type"]
        if kind == "input_action" and step["action"] not in profile["allowed_input_actions"]:
            blockers.append(f"steps[{index}] input action is not allowlisted: {step['action']}")
        elif kind == "key_event" and step["keycode"] not in profile["allowed_keycodes"]:
            blockers.append(f"steps[{index}] keycode is not allowlisted: {step['keycode']}")
        elif kind == "mouse_button" and step["button_index"] not in profile["allowed_mouse_buttons"]:
            blockers.append(f"steps[{index}] mouse button is not allowlisted: {step['button_index']}")
        elif kind == "project_command" and step["command"] not in profile["project_commands"]:
            blockers.append(f"steps[{index}] project command is not allowlisted: {step['command']}")
        elif kind == "checkpoint" and step["checkpoint"] not in profile["checkpoints"]:
            blockers.append(f"steps[{index}] checkpoint is not allowlisted: {step['checkpoint']}")
        if kind == "wait_until":
            observation = step["condition"]["actual"]
        elif kind == "assert":
            observation = step["actual"]
        elif kind == "snapshot" and step["kind"] == "OBSERVABLE":
            observation = step.get("observation", "bridge.frame")
        else:
            observation = None
        if observation is not None and observation not in generic_observations and observation not in profile["observations"]:
            blockers.append(f"steps[{index}] observation is not allowlisted: {observation}")
    return blockers


def _assertions_from_trace(path: Path) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    if not path.exists():
        return output
    for record in read_trace(path):
        if record.get("kind") != "ASSERTION":
            continue
        payload = record.get("payload", {})
        output.append(
            {
                "assertion_id": str(payload.get("assertion_id", "runtime")),
                "status": payload.get("status", "INCONCLUSIVE"),
                "expected": payload.get("expected"),
                "actual": payload.get("actual"),
                "detail": str(payload.get("detail", "")),
            }
        )
    return output


def read_trace(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as error:
        raise GodotAutomationError(f"cannot read session trace: {error}") from error
    for index, line in enumerate(lines):
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            raise GodotAutomationError(f"session trace line {index + 1} is invalid JSON: {error}") from error
        if not isinstance(value, dict):
            raise GodotAutomationError(f"session trace line {index + 1} is not an object")
        expected = {"schema_version", "sequence", "frame", "kind", "payload"}
        if set(value) != expected or value["schema_version"] != "godot_session_trace_record.v1":
            raise GodotAutomationError(f"session trace line {index + 1} violates the strict record contract")
        if value["sequence"] != index:
            raise GodotAutomationError("session trace sequence is not append-only contiguous")
        records.append(value)
    return records


def normalized_trace(path: Path) -> list[dict[str, Any]]:
    records = read_trace(path)
    base_frame = next((int(record["frame"]) for record in records if record["kind"] == "BRIDGE_READY"), 0)
    material = {
        "INJECTED_INPUT", "PROJECT_RESOLVED_ACTION", "COMMAND", "OBSERVATION",
        "COMMAND_ACK", "SNAPSHOT", "ASSERTION", "STRUCTURE", "CAPTURE",
        "MOVIE_MARKER", "ERROR", "FINISH",
    }
    normalized: list[dict[str, Any]] = []
    for record in records:
        if record["kind"] not in material:
            continue
        payload = dict(record["payload"])
        artifact_name = payload.get("file")
        if record["kind"] in {"STRUCTURE", "CAPTURE"} and isinstance(artifact_name, str):
            artifact = path.parent / artifact_name
            payload["artifact_sha256"] = sha256_file(artifact) if artifact.is_file() else None
        normalized.append(
            {"frame": int(record["frame"]) - base_frame, "kind": record["kind"], "payload": payload}
        )
    return normalized


def compare_traces(reference: Path, actual: Path) -> dict[str, Any]:
    reference_normalized = normalized_trace(reference)
    actual_normalized = normalized_trace(actual)
    first: int | None = None
    for index, pair in enumerate(zip(reference_normalized, actual_normalized)):
        if pair[0] != pair[1]:
            first = index
            break
    if first is None and len(reference_normalized) != len(actual_normalized):
        first = min(len(reference_normalized), len(actual_normalized))
    return {
        "status": "MATCH" if first is None else "DIVERGED",
        "reference_trace_sha256": sha256_file(reference),
        "actual_trace_sha256": sha256_file(actual),
        "first_divergence": first,
    }


def _scenario_operation(
    game_repo_text: str | Path,
    *,
    operation_id: str,
    scenario_text: str | Path,
    project_dir_text: str | Path = ".",
    profile_text: str | Path | None = None,
    godot_bin: str | None = None,
    runtime_kind: str = "editor",
    build_text: str | Path | None = None,
    timeout_seconds: float = 120.0,
    windowed: bool = False,
    reference_trace_text: str | Path | None = None,
) -> OperationResult:
    game_repo = resolve_game_repo(game_repo_text)
    project_dir = resolve_project_dir(game_repo, project_dir_text)
    scenario_path = resolve_in_repo(game_repo, scenario_text, must_exist=True, kind="file")
    profile_path = resolve_in_repo(
        game_repo,
        profile_text if profile_text is not None else BRIDGE_PROFILE_RELATIVE,
        must_exist=True,
        kind="file",
    )
    scenario = load_scenario(scenario_path)
    profile = load_profile(profile_path)
    engine = probe_engine(godot_bin)
    if runtime_kind not in {"editor", "debug_export", "release_export"}:
        raise GodotAutomationError("runtime_kind must be editor, debug_export, or release_export")
    manifest = {
        "scenario": {"path": repo_relative(game_repo, scenario_path), "sha256": sha256_file(scenario_path), "scenario_id": scenario["scenario_id"], "seed": scenario["seed"], "initial_checkpoint": scenario["initial_checkpoint"]},
        "profile": {"path": repo_relative(game_repo, profile_path), "sha256": sha256_file(profile_path), "profile_id": profile["profile_id"]},
        "runtime_kind": runtime_kind,
        "windowed": windowed,
    }
    bridge_manifest_path = game_repo / BRIDGE_MANIFEST_RELATIVE
    if bridge_manifest_path.is_file():
        manifest["bridge_install_manifest"] = {
            "path": repo_relative(game_repo, bridge_manifest_path),
            "sha256": sha256_file(bridge_manifest_path),
        }
    transaction = EvidenceTransaction(
        game_repo,
        operation_id=operation_id,
        operation_type="SCENARIO_REPLAY" if reference_trace_text else "SCENARIO_RUN",
        project_dir=project_dir,
        engine=engine,
        automation_manifest=manifest,
    )
    trace_path = transaction.path("session_trace.jsonl")
    result_path = transaction.path("bridge_result.json")
    stdout_path = transaction.path("stdout.log")
    stderr_path = transaction.path("stderr.log")
    benchmark_path = transaction.path("benchmark.json")
    movie_path = transaction.path("movie.avi")
    godot_log_path = transaction.path("godot.log")
    transaction.register(stdout_path, "STDOUT_LOG")
    transaction.register(stderr_path, "STDERR_LOG")
    missing = sorted(set(scenario["required_capabilities"]) - BRIDGE_CAPABILITIES)
    blockers: list[str] = []
    try:
        check = bridge_check(game_repo, project_dir_text=repo_relative(game_repo, project_dir))
        if check.status != "PASS":
            blockers.extend(check.changes)
    except GodotAutomationError as error:
        blockers.append(str(error))
    if missing:
        blockers.append(f"scenario requires unknown capabilities: {', '.join(missing)}")
    blockers.extend(_profile_blockers(scenario, profile))
    if runtime_kind == "release_export":
        blockers.append("release builds cannot activate the runtime bridge")
    if _has_visual_steps(scenario) and not windowed:
        blockers.append("headless dummy rendering cannot establish valid visual capture")
    if blockers:
        transaction.write_text("stdout.log", "", "STDOUT_LOG")
        transaction.write_text("stderr.log", "\n".join(blockers) + "\n", "STDERR_LOG")
        return transaction.finalize(
            status="BLOCKED",
            invocation={"runtime_kind": runtime_kind},
            result={"blockers": blockers},
        )
    token = secrets.token_hex(32)
    port = _free_loopback_port()
    bridge_args = [
        "--studio-adapter-enabled",
        f"--studio-token={token}",
        f"--studio-port={port}",
        f"--studio-output-dir={transaction.operation_dir}",
        f"--studio-profile={profile_path}",
        f"--studio-scenario={scenario_path}",
    ]
    movie_enabled = any(step["type"] == "movie_marker" for step in scenario["steps"])
    movie_args = ["--write-movie", str(movie_path)] if movie_enabled else []
    if runtime_kind == "editor":
        command = [str(engine.executable)]
        if not windowed:
            command.append("--headless")
        else:
            command.append("--windowed")
        command.extend([
            "--path", str(project_dir), "--fixed-fps", str(scenario["fixed_fps"]),
            "--quit-after", str(scenario["max_frames"] + 5), "--benchmark",
            "--benchmark-file", str(benchmark_path), "--log-file", str(godot_log_path),
            *movie_args, "--", *bridge_args,
        ])
    else:
        if build_text is None:
            raise GodotAutomationError("debug_export scenario run requires --build")
        build_path = resolve_in_repo(game_repo, build_text, must_exist=True)
        launcher = resolve_build_launcher(build_path)
        transaction.register(build_path, "EXECUTED_DEBUG_BUILD")
        runtime_arguments = ["--windowed"] if windowed else ["--headless"]
        runtime_arguments.extend([
            "--fixed-fps", str(scenario["fixed_fps"]), "--log-file", str(godot_log_path),
            *movie_args, "--", *bridge_args,
        ])
        command = build_launcher_command(launcher, runtime_arguments)
    sanitized = sanitize_command(command, game_repo=game_repo, binary=engine.executable if runtime_kind == "editor" else None, binary_name=engine.command_name, secrets=(token,))
    xvfb: subprocess.Popen[bytes] | None = None
    env = None
    try:
        xvfb, env = start_xvfb_if_needed(windowed)
        capture = run_process(command, cwd=project_dir, timeout_seconds=timeout_seconds, env=env)
    finally:
        stop_xvfb(xvfb)
    stdout_path.write_text(transaction.scrub_text(capture.stdout), encoding="utf-8")
    stderr_path.write_text(transaction.scrub_text(capture.stderr), encoding="utf-8")
    for path, role in ((trace_path, "SESSION_TRACE"), (result_path, "BRIDGE_RESULT"), (benchmark_path, "PERFORMANCE_BENCHMARK")):
        if path.exists():
            transaction.scrub_text_file(path)
            transaction.register(path, role)
    if godot_log_path.exists():
        transaction.scrub_text_file(godot_log_path)
        transaction.register(godot_log_path, "GODOT_LOG")
    if movie_path.exists():
        transaction.register(movie_path, "MOVIE_CAPTURE")
    for path in sorted(transaction.operation_dir.glob("capture_*.png")):
        transaction.register(path, "PNG_CAPTURE")
    for path in sorted(transaction.operation_dir.glob("structure_*.json")):
        transaction.register(path, "STRUCTURAL_CAPTURE")
    assertions = _assertions_from_trace(trace_path)
    bridge_result = load_json(result_path) if result_path.exists() else None
    expected_project_exit = scenario["expected_exit"] in {"PROJECT_EXIT", "EITHER"}
    bridge_pass = isinstance(bridge_result, dict) and bridge_result.get("status") == "PASS"
    project_exit_pass = expected_project_exit and capture.exit_code == 0 and trace_path.exists()
    if capture.timed_out:
        status = "TIMEOUT"
    elif capture.exit_code != 0 or not (bridge_pass or project_exit_pass):
        status = "FAIL"
    elif any(item["status"] != "PASS" for item in assertions):
        status = "FAIL"
    else:
        status = "PASS"
    replay = None
    if reference_trace_text is not None:
        reference = resolve_in_repo(game_repo, reference_trace_text, must_exist=True, kind="file")
        reference_result_path = reference.parent / "bridge_result.json"
        if not reference_result_path.exists():
            replay = {
                "status": "INCONCLUSIVE",
                "reference_trace_sha256": sha256_file(reference),
                "actual_trace_sha256": sha256_file(trace_path) if trace_path.exists() else "0" * 64,
                "first_divergence": None,
            }
            status = "BLOCKED" if status == "PASS" else status
        else:
            reference_result = load_json(reference_result_path)
            if reference_result.get("seed") != scenario["seed"] or reference_result.get("initial_checkpoint") != scenario["initial_checkpoint"]:
                replay = {
                    "status": "INCONCLUSIVE",
                    "reference_trace_sha256": sha256_file(reference),
                    "actual_trace_sha256": sha256_file(trace_path) if trace_path.exists() else "0" * 64,
                    "first_divergence": None,
                }
                status = "BLOCKED" if status == "PASS" else status
            elif trace_path.exists():
                replay = compare_traces(reference, trace_path)
                if replay["status"] == "DIVERGED" and status == "PASS":
                    status = "FAIL"
    return transaction.finalize(
        status=status,
        invocation={
            "command": sanitized,
            "working_directory": repo_relative(game_repo, project_dir),
            "timeout_seconds": timeout_seconds,
            "headless": not windowed,
        },
        result={
            "process": {"exit_code": capture.exit_code, "timed_out": capture.timed_out, "termination": capture.termination, "duration_ms": capture.duration_ms},
            "bridge": bridge_result,
        },
        assertions=assertions,
        replay=replay,
    )


def run_scenario(game_repo_text: str | Path, **kwargs: Any) -> OperationResult:
    return _scenario_operation(game_repo_text, **kwargs)


def replay_scenario(game_repo_text: str | Path, **kwargs: Any) -> OperationResult:
    if not kwargs.get("reference_trace_text"):
        raise GodotAutomationError("scenario replay requires reference_trace_text")
    return _scenario_operation(game_repo_text, **kwargs)


def validate_scenario_file(path_text: str | Path) -> dict[str, Any]:
    path = Path(path_text).expanduser().resolve()
    scenario = load_scenario(path)
    return {
        "status": "PASS",
        "schema_version": scenario["schema_version"],
        "scenario_id": scenario["scenario_id"],
        "steps": len(scenario["steps"]),
        "required_capabilities": scenario["required_capabilities"],
    }
