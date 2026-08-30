"""Shared safety, hashing, repository-binding, and process primitives."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import signal
import subprocess
import tempfile
import time
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any


FACTORY_ROOT = Path(__file__).resolve().parents[2]
ADAPTER_ROOT = Path("design/studio/engine/godot")
EVIDENCE_ROOT = ADAPTER_ROOT / "evidence_v2"
SCHEMA_ROOT = FACTORY_ROOT / "studio" / "schemas"
BRIDGE_SOURCE_ROOT = Path(__file__).resolve().parent / "addon"
BRIDGE_VENDOR_RELATIVE = Path("addons/game_studio_godot_bridge")
BRIDGE_MANIFEST_RELATIVE = ADAPTER_ROOT / "GODOT_BRIDGE_INSTALL_MANIFEST.json"
BRIDGE_PROFILE_RELATIVE = ADAPTER_ROOT / "GODOT_BRIDGE_PROFILE.json"

AUTOMATION_VERSION = "godot_automation.v1"
BRIDGE_VERSION = "game_studio_godot_bridge.v1"
PROTOCOL_VERSION = "godot_bridge_protocol.v1"

OPERATION_STATUSES = {"PASS", "FAIL", "TIMEOUT", "BLOCKED", "ABORTED"}
ASSERTION_STATUSES = {"PASS", "FAIL", "INCONCLUSIVE"}
REPLAY_STATUSES = {"MATCH", "DIVERGED", "INCONCLUSIVE"}
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
TOKEN_ARG_RE = re.compile(r"(?i)(--studio-token(?:=|\s+))([^\s\"']+)")
SECRET_FIELD_RE = re.compile(r"(?i)(token|secret|password|api[_-]?key|authorization)")


class GodotAutomationError(ValueError):
    """The requested operation is invalid, unsafe, or cannot be completed."""


@dataclass(frozen=True)
class OperationResult:
    status: str
    artifact_path: str
    artifact_sha256: str


@dataclass(frozen=True)
class EngineInfo:
    executable: Path
    locator_kind: str
    command_name: str
    version: str
    major: int
    minor: int
    patch: int
    help_text: str

    def public(self) -> dict[str, Any]:
        return {
            "locator_kind": self.locator_kind,
            "command_name": self.command_name,
            "version": self.version,
            "version_parts": {
                "major": self.major,
                "minor": self.minor,
                "patch": self.patch,
            },
        }


@dataclass(frozen=True)
class ProcessCapture:
    command: list[str]
    exit_code: int | None
    stdout: str
    stderr: str
    timed_out: bool
    termination: str
    duration_ms: int


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def pretty_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def atomic_write_json(path: Path, value: Any) -> None:
    atomic_write_bytes(path, pretty_json(value).encode("utf-8"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def directory_digest(path: Path) -> tuple[str, int]:
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


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def repo_relative(game_repo: Path, path: Path) -> str:
    resolved = path.resolve()
    if not is_within(resolved, game_repo):
        raise GodotAutomationError(f"path escapes game repo: {path}")
    value = resolved.relative_to(game_repo.resolve()).as_posix()
    return value or "."


def validate_repo_relative(value: str, *, field: str = "path") -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise GodotAutomationError(f"{field} must be a non-empty repo-relative POSIX path")
    path = PurePosixPath(value)
    if path.is_absolute() or value.startswith("~/") or any(part in {"", ".", ".."} for part in path.parts):
        raise GodotAutomationError(f"{field} must not escape the repository: {value}")
    return value


def resolve_in_repo(
    game_repo: Path,
    raw_path: str | Path,
    *,
    must_exist: bool = False,
    kind: str | None = None,
) -> Path:
    candidate = Path(raw_path).expanduser()
    resolved = (candidate if candidate.is_absolute() else game_repo / candidate).resolve()
    if not is_within(resolved, game_repo):
        raise GodotAutomationError(f"path escapes game repo: {raw_path}")
    if must_exist and not resolved.exists():
        raise GodotAutomationError(f"required path does not exist: {raw_path}")
    if kind == "file" and not resolved.is_file():
        raise GodotAutomationError(f"required file does not exist: {raw_path}")
    if kind == "directory" and not resolved.is_dir():
        raise GodotAutomationError(f"required directory does not exist: {raw_path}")
    return resolved


def run_git(game_repo: Path, *args: str, binary: bool = False) -> str | bytes:
    result = subprocess.run(
        ["git", "-C", str(game_repo), *args],
        check=False,
        capture_output=True,
        text=not binary,
        encoding=None if binary else "utf-8",
    )
    if result.returncode:
        stderr = result.stderr.decode("utf-8", errors="replace") if binary else str(result.stderr)
        raise GodotAutomationError(stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout


def resolve_game_repo(raw_path: str | Path) -> Path:
    game_repo = Path(raw_path).expanduser().resolve()
    if not game_repo.is_dir():
        raise GodotAutomationError(f"game repo does not exist: {game_repo}")
    if game_repo == FACTORY_ROOT or is_within(game_repo, FACTORY_ROOT):
        raise GodotAutomationError("game repo must not be this Factory checkout or its child")
    try:
        git_root = Path(str(run_git(game_repo, "rev-parse", "--show-toplevel")).strip()).resolve()
    except GodotAutomationError as error:
        raise GodotAutomationError("Godot automation requires an existing Git repository") from error
    if git_root != game_repo:
        raise GodotAutomationError(f"game repo must be the Git root, not a child: {game_repo}")
    return game_repo


def resolve_project_dir(game_repo: Path, raw_path: str | Path = ".") -> Path:
    project_dir = resolve_in_repo(game_repo, raw_path, must_exist=True, kind="directory")
    if is_within(project_dir, game_repo / ADAPTER_ROOT):
        raise GodotAutomationError("Godot project cannot live inside the adapter evidence directory")
    if not (project_dir / "project.godot").is_file():
        raise GodotAutomationError(f"Godot project path lacks project.godot: {repo_relative(game_repo, project_dir)}")
    return project_dir


def repository_binding(game_repo: Path, *, ignored_prefixes: Iterable[str] = ()) -> dict[str, Any]:
    ignored = {ADAPTER_ROOT.as_posix(), *ignored_prefixes}
    tracked = run_git(game_repo, "diff", "--name-only", "-z", "HEAD", "--", binary=True)
    untracked = run_git(game_repo, "ls-files", "--others", "--exclude-standard", "-z", binary=True)
    assert isinstance(tracked, bytes) and isinstance(untracked, bytes)
    changed = {
        raw.decode("utf-8", errors="surrogateescape")
        for raw in (*tracked.split(b"\0"), *untracked.split(b"\0"))
        if raw
    }
    selected = sorted(
        value
        for value in changed
        if not any(value == prefix or value.startswith(prefix + "/") for prefix in ignored)
    )
    digest = hashlib.sha256()
    for relative in selected:
        digest.update(relative.encode("utf-8", errors="surrogateescape"))
        digest.update(b"\0")
        path = game_repo / relative
        if path.is_symlink():
            digest.update(b"symlink\0" + path.readlink().as_posix().encode("utf-8"))
        elif path.is_file():
            digest.update(b"file\0" + hashlib.sha256(path.read_bytes()).digest())
        elif not path.exists():
            digest.update(b"missing\0")
        else:
            digest.update(b"other\0")
        digest.update(b"\0")
    return {
        "revision": str(run_git(game_repo, "rev-parse", "HEAD")).strip(),
        "dirty_paths": selected,
        "working_tree_sha256": digest.hexdigest(),
    }


def _discover_executable(requested: str | None) -> tuple[Path, str, str]:
    if requested:
        expanded = Path(requested).expanduser()
        found = shutil.which(requested) if expanded.parent == Path(".") else None
        executable = Path(found).resolve() if found else expanded.resolve()
        kind, name = "EXPLICIT", expanded.name
    else:
        executable, kind, name = Path(), "", ""
        candidates = []
        if os.environ.get("GODOT_BIN"):
            candidates.append((os.environ["GODOT_BIN"], "ENV"))
        candidates.extend((name, "PATH") for name in ("godot", "godot4", "godot-mono"))
        for candidate, candidate_kind in candidates:
            found = shutil.which(candidate)
            if found:
                executable, kind, name = Path(found).resolve(), candidate_kind, Path(candidate).name
                break
        if not name:
            mac = Path("/Applications/Godot.app/Contents/MacOS/Godot")
            if mac.is_file():
                executable, kind, name = mac.resolve(), "MACOS_APPLICATION", "Godot"
    if not name or not executable.is_file():
        raise GodotAutomationError("Godot executable not found; pass --godot-bin or GODOT_BIN")
    if not os.access(executable, os.X_OK):
        raise GodotAutomationError(f"Godot executable is not executable: {name}")
    return executable, kind, name


def _small_command(command: Sequence[str], timeout: float = 15.0) -> str:
    try:
        result = subprocess.run(
            list(command), check=False, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise GodotAutomationError(f"cannot execute {Path(command[0]).name}: {error}") from error
    if result.returncode:
        raise GodotAutomationError(result.stderr.strip() or f"command exited {result.returncode}")
    return ANSI_RE.sub("", result.stdout).strip()


def probe_engine(requested: str | None = None) -> EngineInfo:
    executable, kind, name = _discover_executable(requested)
    version = _small_command([str(executable), "--version"])
    match = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", version)
    if not match or int(match.group(1)) < 4:
        raise GodotAutomationError(f"Godot 4 is required, found {version!r}")
    return EngineInfo(
        executable, kind, name, version,
        int(match.group(1)), int(match.group(2)), int(match.group(3) or 0),
        _small_command([str(executable), "--help"]),
    )


def redact(value: Any, *, secrets: Iterable[str] = ()) -> Any:
    secret_values = {item for item in secrets if item}
    if isinstance(value, Mapping):
        return {
            str(key): "<REDACTED>" if SECRET_FIELD_RE.search(str(key)) else redact(item, secrets=secret_values)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item, secrets=secret_values) for item in value]
    if isinstance(value, tuple):
        return [redact(item, secrets=secret_values) for item in value]
    if isinstance(value, str):
        rendered = TOKEN_ARG_RE.sub(r"\1<REDACTED>", value)
        for secret in secret_values:
            rendered = rendered.replace(secret, "<REDACTED>")
        return rendered
    return value


def sanitize_command(
    command: Sequence[str], *, game_repo: Path, binary: Path | None = None,
    binary_name: str | None = None, secrets: Iterable[str] = (),
) -> list[str]:
    output: list[str] = []
    redact_next = False
    for index, raw in enumerate(command):
        if redact_next:
            output.append("<REDACTED>")
            redact_next = False
            continue
        if raw == "--studio-token":
            output.append(raw)
            redact_next = True
            continue
        if raw.startswith("--studio-token="):
            output.append("--studio-token=<REDACTED>")
            continue
        if index == 0 and binary and Path(raw).resolve() == binary.resolve():
            output.append(f"<GODOT_BINARY:{binary_name or binary.name}>")
            continue
        if "=" in raw:
            option, possible_path = raw.split("=", 1)
            candidate_value = Path(possible_path)
            if candidate_value.is_absolute():
                if is_within(candidate_value, game_repo):
                    output.append(f"{option}=<GAME_REPO>/{repo_relative(game_repo, candidate_value)}")
                elif is_within(candidate_value, FACTORY_ROOT):
                    output.append(f"{option}=<FACTORY_ROOT>/{candidate_value.resolve().relative_to(FACTORY_ROOT).as_posix()}")
                else:
                    output.append(f"{option}=<ABSOLUTE_PATH:{candidate_value.name}>")
                continue
        candidate = Path(raw)
        if candidate.is_absolute() and is_within(candidate, game_repo):
            output.append(f"<GAME_REPO>/{repo_relative(game_repo, candidate)}")
        elif candidate.is_absolute() and is_within(candidate, FACTORY_ROOT):
            output.append(f"<FACTORY_ROOT>/{candidate.resolve().relative_to(FACTORY_ROOT).as_posix()}")
        elif candidate.is_absolute():
            output.append(f"<ABSOLUTE_PATH:{candidate.name}>")
        else:
            output.append(str(redact(raw, secrets=secrets)))
    return output


def _terminate(process: subprocess.Popen[str]) -> str:
    termination = "TERMINATE"
    try:
        if os.name == "nt":
            process.terminate()
        else:
            os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=3)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        termination = "KILL"
        try:
            process.kill() if os.name == "nt" else os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    return termination


def run_process(
    command: Sequence[str], *, cwd: Path, timeout_seconds: float,
    env: Mapping[str, str] | None = None,
) -> ProcessCapture:
    if timeout_seconds <= 0:
        raise GodotAutomationError("timeout_seconds must be positive")
    started = time.monotonic()
    try:
        process = subprocess.Popen(
            list(command), cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace",
            start_new_session=os.name != "nt", env=dict(env) if env else None,
        )
    except OSError as error:
        raise GodotAutomationError(f"cannot start process: {error}") from error
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
        return ProcessCapture(list(command), process.returncode, stdout, stderr, False, "NONE", round((time.monotonic() - started) * 1000))
    except subprocess.TimeoutExpired:
        termination = _terminate(process)
        stdout, stderr = process.communicate()
        return ProcessCapture(list(command), process.returncode, stdout, stderr, True, termination, round((time.monotonic() - started) * 1000))


def start_xvfb_if_needed(
    windowed: bool,
) -> tuple[subprocess.Popen[bytes] | None, dict[str, str] | None]:
    """Provide a bounded virtual display for Linux windowed evidence runs."""
    if not windowed or platform.system() != "Linux" or os.environ.get("DISPLAY"):
        return None, None
    binary = shutil.which("Xvfb")
    if not binary:
        raise GodotAutomationError("windowed Linux visual run requires DISPLAY or Xvfb")
    process = subprocess.Popen(
        [binary, ":99", "-screen", "0", "1280x720x24"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(0.15)
    environment = dict(os.environ)
    environment["DISPLAY"] = ":99"
    return process, environment


def stop_xvfb(process: subprocess.Popen[bytes] | None) -> None:
    if process is None:
        return
    process.terminate()
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise GodotAutomationError(f"cannot read strict JSON {path}: {error}") from error


def ensure_operation_id(operation_id: str) -> str:
    if not isinstance(operation_id, str) or ID_RE.fullmatch(operation_id) is None:
        raise GodotAutomationError(f"operation_id must match {ID_RE.pattern}")
    return operation_id
