"""Private, capability-scoped stdio sessions for the two ArtCraft editors.

Like sound/scoring/mix.py's SoundCraft client, but with bounded waits and EOF
handling. No global MCP configuration, desktop session or image provider changes.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import queue
import shutil
import subprocess
import threading
import time


EDITORS = {"vectorcraft": ".vectorcraft", "photocraft": ".pcraft"}


class CraftError(RuntimeError):
    pass


def find_cli(editor: str, override: str | None = None) -> str:
    if editor not in EDITORS:
        raise CraftError(f"Unknown editor: {editor}")
    env_key = f"{editor.upper()}_CLI"
    explicit = override or os.environ.get(env_key)
    candidates = [explicit] if explicit else [f"{editor}-cli", f"~/.local/bin/{editor}-cli"]
    for candidate in candidates:
        expanded = os.path.expanduser(candidate)
        found = shutil.which(expanded)
        if found:
            return str(Path(found).resolve())
    raise CraftError(f"{editor}-cli not executable: set {env_key}, use --cli, or add it to PATH")


def check_result(value, context: str) -> None:
    """MCP success is not necessarily engine success (or a finished operation)."""
    if isinstance(value, dict):
        failed = value.get("failed", 0)
        if (value.get("ok") is False or value.get("success") is False
                or value.get("error") or (isinstance(failed, (int, float)) and failed > 0)
                or value.get("pending") or value.get("cancelled") or "job" in value
                or value.get("status") in ("pending", "cancelled", "failed")):
            raise CraftError(f"{context}: unsuccessful or unfinished result: {str(value)[:1200]}")
        # Batch envelopes can otherwise hide a failed step.
        for result in value.get("results", []) if isinstance(value.get("results"), list) else []:
            check_result(result, context)
    elif isinstance(value, str) and value.lower() in ("cancelled", "pending"):
        raise CraftError(f"{context}: {value}")


class CraftClient:
    """One synchronous request at a time; always close (prefer a with block)."""

    def __init__(self, editor: str, read_root: Path, write_root: Path,
                 log_dir: Path, *, cli: str | None = None, timeout: float = 120):
        if not math.isfinite(timeout) or timeout <= 0:
            raise CraftError("timeout must be a finite positive number of seconds")
        self.editor, self.timeout = editor, timeout
        self.cli = find_cli(editor, cli)
        self._id = 0
        self._lines: queue.Queue = queue.Queue()
        self.p = None
        self._reader = None
        self._stderr = None
        self._trace = None
        read_root, write_root, log_dir = (p.expanduser().resolve() for p in (read_root, write_root, log_dir))
        write_root.mkdir(parents=True, exist_ok=True)
        log_dir.mkdir(parents=True, exist_ok=True)
        home = write_root / ".session-home"
        home.mkdir(exist_ok=True)
        args = [self.cli, "mcp"]
        if editor == "vectorcraft":
            args.append("--headless")
        # PhotoCraft accepts ONE read root, unlike VectorCraft/SoundCraft.
        args += ["--automation-read-root", str(read_root.resolve()),
                 "--automation-write-root", str(write_root.resolve())]
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(("PHOTOCRAFT_", "VECTORCRAFT_"))}
        # In particular, never inherit PHOTOCRAFT_CONTROL_PORT/token (bridge mode).
        env.update(HOME=str(home), XDG_CONFIG_HOME=str(home / "config"),
                   XDG_CACHE_HOME=str(home / "cache"), XDG_DATA_HOME=str(home / "data"))
        try:
            self._stderr = (log_dir / "editor.stderr.log").open("w", encoding="utf-8")
            self._trace = (log_dir / "calls.jsonl").open("w", encoding="utf-8")
            self.p = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                      stderr=self._stderr, text=True, encoding="utf-8",
                                      cwd=write_root, env=env)
            self._reader = threading.Thread(target=self._read_lines, daemon=True)
            self._reader.start()
            self.server = self._rpc("initialize", {
                "protocolVersion": "2025-06-18", "capabilities": {},
                "clientInfo": {"name": "asset-factory-craft", "version": "1"},
            })
            self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        except BaseException:  # Also reap the child if initialization is interrupted.
            self.close()
            raise

    def _read_lines(self):
        try:
            for line in self.p.stdout:
                self._lines.put(line)
        finally:
            self._lines.put(None)

    def _send(self, message):
        try:
            self.p.stdin.write(json.dumps(message, ensure_ascii=False, allow_nan=False) + "\n")
            self.p.stdin.flush()
        except (OSError, ValueError) as error:
            raise CraftError(f"{self.editor}: could not send MCP request: {error}") from error

    def _rpc(self, method: str, params: dict):
        self._id += 1
        request = {"jsonrpc": "2.0", "id": self._id, "method": method, "params": params}
        self._trace.write(json.dumps({"request": request}, ensure_ascii=False) + "\n")
        self._trace.flush()
        self._send(request)
        deadline = time.monotonic() + self.timeout
        while True:
            remaining = deadline - time.monotonic()
            try:
                line = self._lines.get(timeout=max(0, remaining)) if remaining > 0 else None
            except queue.Empty:
                raise CraftError(f"{self.editor}: MCP {method} timed out after {self.timeout}s") from None
            if remaining <= 0:
                raise CraftError(f"{self.editor}: MCP {method} timed out after {self.timeout}s")
            if line is None:
                raise CraftError(f"{self.editor}: MCP EOF during {method}; see editor.stderr.log")
            try:
                message = json.loads(line)
            except ValueError as error:
                raise CraftError(f"{self.editor}: invalid MCP JSON: {line[:200]}") from error
            if not isinstance(message, dict):
                raise CraftError(f"{self.editor}: MCP response must be an object")
            if "method" in message:  # progress/log notifications or unsupported server requests
                if "id" in message:
                    self._send({"jsonrpc": "2.0", "id": message["id"],
                                "error": {"code": -32601, "message": "Client method not supported"}})
                continue
            if message.get("id") != self._id:
                continue
            self._trace.write(json.dumps({"response": message}, ensure_ascii=False) + "\n")
            self._trace.flush()
            if "error" in message:
                raise CraftError(f"{self.editor}: MCP {method}: {message['error']}")
            if "result" not in message:
                raise CraftError(f"{self.editor}: missing MCP result for {method}")
            return message["result"]

    def tool(self, tool_name: str, **arguments):
        result = self._rpc("tools/call", {"name": tool_name, "arguments": arguments})
        if not isinstance(result, dict):
            raise CraftError(f"{self.editor}: invalid tool result for {tool_name}")
        text = "\n".join(c.get("text", "") for c in result.get("content", []) if c.get("type") == "text")
        if result.get("isError"):
            raise CraftError(f"{self.editor} {tool_name}: {text[:1600]}")
        value = result.get("structuredContent")
        if value is None:
            try:
                value = json.loads(text)
            except ValueError:
                value = text
        check_result(value, f"{self.editor} {tool_name}")
        return value

    def command(self, command: str, params: dict):
        extra = {"wait": True} if self.editor == "photocraft" else {}
        return self.tool("command_run", id=command, params=params, **extra)

    def close(self):
        if self.p is not None:
            try:
                self.p.stdin.close()
            except (OSError, ValueError):
                pass
            try:
                self.p.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.p.kill()
                self.p.wait(timeout=5)
            if self._reader:
                self._reader.join(timeout=2)
            self.p.stdout.close()
            self.p = None
        for stream in (self._stderr, self._trace):
            if stream:
                stream.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
