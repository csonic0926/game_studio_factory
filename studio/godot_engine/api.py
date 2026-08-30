"""Synchronous Python live-session API and JSONL harness."""

from __future__ import annotations

import json
import os
import secrets
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, TextIO

from .bridge import bridge_check
from .build import build_launcher_command, resolve_build_launcher
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
    sanitize_command,
    sha256_file,
    start_xvfb_if_needed,
    stop_xvfb,
)
from .evidence import EvidenceTransaction
from .protocol import BridgeClient
from .schema import load_profile


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as stream:
        stream.bind(("127.0.0.1", 0))
        return int(stream.getsockname()[1])


def _validate_live_command(command: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(command, dict) or not isinstance(command.get("command"), str):
        raise GodotAutomationError("live command must be a command object")
    kind = command["command"]
    allowed = {
        "snapshot", "input_action", "key_event", "mouse_button", "mouse_motion",
        "project_command", "checkpoint", "capture_structure", "capture_png",
        "movie_marker", "shutdown",
    }
    if kind not in allowed:
        raise GodotAutomationError("live command is not declared; arbitrary eval/mutation is forbidden")
    if kind == "input_action" and command.get("action") not in profile["allowed_input_actions"]:
        raise GodotAutomationError("input action is not allowlisted by the bridge profile")
    if kind == "key_event" and command.get("keycode") not in profile["allowed_keycodes"]:
        raise GodotAutomationError("keycode is not allowlisted by the bridge profile")
    if kind == "mouse_button" and command.get("button_index") not in profile["allowed_mouse_buttons"]:
        raise GodotAutomationError("mouse button is not allowlisted by the bridge profile")
    if kind == "project_command" and command.get("name") not in profile["project_commands"]:
        raise GodotAutomationError("project command is not allowlisted by the bridge profile")
    if kind == "checkpoint" and command.get("checkpoint") not in profile["checkpoints"]:
        raise GodotAutomationError("checkpoint is not allowlisted by the bridge profile")
    if kind == "snapshot" and command.get("kind", "OBSERVABLE") == "OBSERVABLE":
        observation = command.get("observation", "bridge.frame")
        if observation not in {"bridge.frame", "bridge.scene", "bridge.viewport", "bridge.input_map"} and observation not in profile["observations"]:
            raise GodotAutomationError("observation is not allowlisted by the bridge profile")
    return command


class GodotSession:
    """One debug/editor Godot process controlled over authenticated loopback TCP.

    Commands execute on the bridge's next safe process frame.  Closing the
    context finalizes immutable evidence even when the controlled process fails.
    """

    def __init__(
        self,
        game_repo: str | Path,
        *,
        operation_id: str,
        project_dir: str | Path = ".",
        profile: str | Path | None = None,
        godot_bin: str | None = None,
        runtime_kind: str = "editor",
        build: str | Path | None = None,
        windowed: bool = False,
        fixed_fps: int = 60,
        seed: int | None = None,
        initial_checkpoint: str | None = None,
        connect_timeout_seconds: float = 15.0,
    ) -> None:
        self.game_repo = resolve_game_repo(game_repo)
        self.project_dir = resolve_project_dir(self.game_repo, project_dir)
        self.profile_path = resolve_in_repo(
            self.game_repo,
            profile if profile is not None else BRIDGE_PROFILE_RELATIVE,
            must_exist=True,
            kind="file",
        )
        self.profile = load_profile(self.profile_path)
        self.engine = probe_engine(godot_bin)
        if runtime_kind not in {"editor", "debug_export"}:
            raise GodotAutomationError("live bridge sessions support only editor or debug_export runtime")
        if fixed_fps < 1:
            raise GodotAutomationError("fixed_fps must be positive")
        if seed is not None and (not isinstance(seed, int) or isinstance(seed, bool)):
            raise GodotAutomationError("live session seed must be an integer or null")
        if initial_checkpoint is not None and initial_checkpoint not in self.profile["checkpoints"]:
            raise GodotAutomationError("live session initial checkpoint is not allowlisted")
        check = bridge_check(self.game_repo, project_dir_text=repo_relative(self.game_repo, self.project_dir))
        if check.status != "PASS":
            raise GodotAutomationError("bridge check is blocked: " + "; ".join(check.changes))
        self.runtime_kind = runtime_kind
        self.build = resolve_in_repo(self.game_repo, build, must_exist=True) if build else None
        if runtime_kind == "debug_export" and self.build is None:
            raise GodotAutomationError("debug_export live session requires build path")
        self.windowed = windowed
        self.fixed_fps = fixed_fps
        self.seed = seed
        self.initial_checkpoint = initial_checkpoint
        self.connect_timeout_seconds = connect_timeout_seconds
        self.token = secrets.token_hex(32)
        self.port = _free_port()
        automation_manifest: dict[str, Any] = {
            "profile": {
                "path": repo_relative(self.game_repo, self.profile_path),
                "sha256": sha256_file(self.profile_path),
                "profile_id": self.profile["profile_id"],
            },
            "runtime_kind": runtime_kind,
            "fixed_fps": fixed_fps,
            "seed": seed,
            "initial_checkpoint": initial_checkpoint,
        }
        bridge_manifest_path = self.game_repo / BRIDGE_MANIFEST_RELATIVE
        if bridge_manifest_path.is_file():
            automation_manifest["bridge_install_manifest"] = {
                "path": repo_relative(self.game_repo, bridge_manifest_path),
                "sha256": sha256_file(bridge_manifest_path),
            }
        self.transaction = EvidenceTransaction(
            self.game_repo,
            operation_id=operation_id,
            operation_type="LIVE_SESSION",
            project_dir=self.project_dir,
            engine=self.engine,
            automation_manifest=automation_manifest,
            secrets=(self.token,),
        )
        self.stdout_path = self.transaction.path("stdout.log")
        self.stderr_path = self.transaction.path("stderr.log")
        self.godot_log_path = self.transaction.path("godot.log")
        self.transaction.register(self.stdout_path, "STDOUT_LOG")
        self.transaction.register(self.stderr_path, "STDERR_LOG")
        self.process: subprocess.Popen[str] | None = None
        self._xvfb: subprocess.Popen[bytes] | None = None
        self.client: BridgeClient | None = None
        self.command: list[str] = []
        self._stdout_stream: TextIO | None = None
        self._stderr_stream: TextIO | None = None
        self.result: OperationResult | None = None

    def _command(self) -> list[str]:
        bridge_args = [
            "--studio-adapter-enabled",
            f"--studio-token={self.token}",
            f"--studio-port={self.port}",
            f"--studio-output-dir={self.transaction.operation_dir}",
            f"--studio-profile={self.profile_path}",
        ]
        if self.seed is not None:
            bridge_args.append(f"--studio-seed={self.seed}")
        if self.initial_checkpoint is not None:
            bridge_args.append(f"--studio-initial-checkpoint={self.initial_checkpoint}")
        if self.runtime_kind == "editor":
            command = [str(self.engine.executable)]
            if not self.windowed:
                command.append("--headless")
            else:
                command.append("--windowed")
            command.extend([
                "--path", str(self.project_dir), "--fixed-fps", str(self.fixed_fps),
                "--log-file", str(self.godot_log_path), "--", *bridge_args,
            ])
            return command
        assert self.build is not None
        launcher = resolve_build_launcher(self.build)
        self.transaction.register(self.build, "EXECUTED_DEBUG_BUILD")
        return build_launcher_command(
            launcher,
            [
                "--windowed" if self.windowed else "--headless",
                "--fixed-fps", str(self.fixed_fps),
                "--log-file", str(self.godot_log_path), "--", *bridge_args,
            ],
        )

    def __enter__(self) -> "GodotSession":
        self.command = self._command()
        self._stdout_stream = self.stdout_path.open("w", encoding="utf-8")
        self._stderr_stream = self.stderr_path.open("w", encoding="utf-8")
        try:
            self._xvfb, environment = start_xvfb_if_needed(self.windowed)
            self.process = subprocess.Popen(
                self.command,
                cwd=self.project_dir,
                stdout=self._stdout_stream,
                stderr=self._stderr_stream,
                text=True,
                encoding="utf-8",
                errors="replace",
                start_new_session=os.name != "nt",
                env=environment,
            )
            self.client = BridgeClient("127.0.0.1", self.port, self.token, self.connect_timeout_seconds)
            self.client.connect()
            return self
        except Exception:
            if self.process is not None and self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait()
            self._finish("BLOCKED", {"startup_failed": True})
            raise

    def command_request(self, command: dict[str, Any]) -> dict[str, Any]:
        if self.client is None or self.process is None:
            raise GodotAutomationError("GodotSession is not active")
        if self.process.poll() is not None:
            raise GodotAutomationError(f"Godot process exited before command with code {self.process.returncode}")
        if command.get("command") == "capture_png" and not self.windowed:
            raise GodotAutomationError("headless dummy renderer cannot establish valid PNG evidence")
        return self.client.request(_validate_live_command(command, self.profile))

    def input_action(self, action: str, pressed: bool, strength: float = 1.0) -> dict[str, Any]:
        return self.command_request({"command": "input_action", "action": action, "pressed": pressed, "strength": strength})

    def snapshot(self, snapshot_id: str, observation: str = "bridge.frame") -> dict[str, Any]:
        return self.command_request({"command": "snapshot", "snapshot_id": snapshot_id, "kind": "OBSERVABLE", "observation": observation})

    def capture_png(self, capture_id: str) -> dict[str, Any]:
        if not self.windowed:
            raise GodotAutomationError("headless dummy renderer cannot establish valid PNG evidence")
        return self.command_request({"command": "capture_png", "capture_id": capture_id})

    def close(self) -> OperationResult:
        if self.result is not None:
            return self.result
        status = "PASS"
        details: dict[str, Any] = {}
        if self.client is not None:
            try:
                if self.process is not None and self.process.poll() is None:
                    self.client.request({"command": "shutdown", "exit_code": 0})
            except GodotAutomationError as error:
                status = "FAIL"
                details["shutdown_error"] = str(error)
            finally:
                self.client.close()
        if status == "FAIL" and self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            details["terminated_after_control_failure"] = True
        if self.process is not None:
            try:
                exit_code = self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.terminate()
                try:
                    exit_code = self.process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    exit_code = self.process.wait()
                status = "TIMEOUT"
            details["exit_code"] = exit_code
            if exit_code != 0 and status == "PASS":
                status = "FAIL"
        return self._finish(status, details)

    def _finish(self, status: str, details: dict[str, Any]) -> OperationResult:
        if self.result is not None:
            return self.result
        if self._stdout_stream is not None:
            self._stdout_stream.close()
            self._stdout_stream = None
        if self._stderr_stream is not None:
            self._stderr_stream.close()
            self._stderr_stream = None
        stop_xvfb(self._xvfb)
        self._xvfb = None
        self.transaction.scrub_text_file(self.stdout_path)
        self.transaction.scrub_text_file(self.stderr_path)
        if self.godot_log_path.exists():
            self.transaction.scrub_text_file(self.godot_log_path)
            self.transaction.register(self.godot_log_path, "GODOT_LOG")
        for path, role in (
            (self.transaction.path("session_trace.jsonl"), "SESSION_TRACE"),
            (self.transaction.path("bridge_result.json"), "BRIDGE_RESULT"),
        ):
            if path.exists():
                self.transaction.register(path, role)
        for path in sorted(self.transaction.operation_dir.glob("capture_*.png")):
            self.transaction.register(path, "PNG_CAPTURE")
        for path in sorted(self.transaction.operation_dir.glob("structure_*.json")):
            self.transaction.register(path, "STRUCTURAL_CAPTURE")
        self.result = self.transaction.finalize(
            status=status,
            invocation={
                "command": sanitize_command(self.command, game_repo=self.game_repo, binary=self.engine.executable if self.runtime_kind == "editor" else None, binary_name=self.engine.command_name, secrets=(self.token,)),
                "working_directory": repo_relative(self.game_repo, self.project_dir),
                "headless": not self.windowed,
            },
            result=details,
        )
        return self.result

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if exc is not None:
            if self.client is not None:
                self.client.close()
            if self.process is not None and self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait()
            self._finish("FAIL", {"exception": type(exc).__name__, "process_exit_code": self.process.returncode if self.process else None})
            return
        self.close()


def serve_jsonl(session: GodotSession, input_stream: TextIO = sys.stdin, output_stream: TextIO = sys.stdout) -> OperationResult:
    with session:
        for line_number, line in enumerate(input_stream, 1):
            if not line.strip():
                continue
            request_id: Any = None
            try:
                value = json.loads(line)
                if not isinstance(value, dict) or set(value) != {"id", "command"} or not isinstance(value["command"], dict):
                    raise GodotAutomationError("JSONL request fields must be exactly id and command")
                request_id = value["id"]
                response = session.command_request(value["command"])
                rendered = {"id": request_id, "status": "PASS", "result": response}
            except (json.JSONDecodeError, GodotAutomationError) as error:
                rendered = {"id": request_id, "status": "FAIL", "error": str(error), "line": line_number}
            output_stream.write(json.dumps(rendered, ensure_ascii=False, sort_keys=True) + "\n")
            output_stream.flush()
    assert session.result is not None
    return session.result
