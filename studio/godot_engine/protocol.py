"""Loopback-only, single-client, length-prefixed bridge protocol."""

from __future__ import annotations

import json
import re
import socket
import struct
import time
import uuid
from dataclasses import dataclass
from typing import Any

from .common import PROTOCOL_VERSION, GodotAutomationError, canonical_json_bytes, redact


MAX_MESSAGE_BYTES = 1_048_576
HEADER = struct.Struct("<I")
MESSAGE_TYPES = {
    "hello", "handshake", "handshake_ack", "command", "command_ack",
    "event", "error", "shutdown",
}

COMMAND_FIELDS: dict[str, tuple[set[str], set[str]]] = {
    "snapshot": ({"command", "snapshot_id", "kind"}, {"observation"}),
    "input_action": ({"command", "action", "pressed"}, {"strength"}),
    "key_event": ({"command", "keycode", "pressed"}, {"echo", "unicode"}),
    "mouse_button": ({"command", "button_index", "pressed", "position"}, set()),
    "mouse_motion": ({"command", "position", "relative"}, {"button_mask"}),
    "project_command": ({"command", "name"}, {"arguments"}),
    "checkpoint": ({"command", "checkpoint"}, {"arguments"}),
    "capture_structure": ({"command", "capture_id"}, set()),
    "capture_png": ({"command", "capture_id"}, set()),
    "movie_marker": ({"command", "marker"}, set()),
    "shutdown": ({"command"}, {"exit_code"}),
}
TOKEN_RE = re.compile(r"^[0-9a-f]{64}$")


def _exact(payload: dict[str, Any], required: set[str], optional: set[str] = frozenset()) -> bool:
    return required <= payload.keys() and payload.keys() <= required | optional


def _string(value: Any) -> bool:
    return isinstance(value, str) and bool(value)


def _integer(value: Any, *, minimum: int | None = None) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and (minimum is None or value >= minimum)


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _vec2(value: Any) -> bool:
    return isinstance(value, list) and len(value) == 2 and all(_number(item) for item in value)


def _strings(value: Any) -> bool:
    return (
        isinstance(value, list)
        and all(_string(item) for item in value)
        and len(set(value)) == len(value)
    )


def _validate_command(command: str, payload: dict[str, Any]) -> bool:
    if command == "snapshot":
        return (
            _string(payload["snapshot_id"])
            and payload["kind"] in {"OBSERVABLE", "MECHANICAL"}
            and ("observation" not in payload or _string(payload["observation"]))
        )
    if command == "input_action":
        strength = payload.get("strength", 1.0)
        return _string(payload["action"]) and isinstance(payload["pressed"], bool) and _number(strength) and 0 <= strength <= 1
    if command == "key_event":
        return (
            _integer(payload["keycode"], minimum=0)
            and isinstance(payload["pressed"], bool)
            and ("echo" not in payload or isinstance(payload["echo"], bool))
            and ("unicode" not in payload or _integer(payload["unicode"], minimum=0))
        )
    if command == "mouse_button":
        return _integer(payload["button_index"], minimum=0) and isinstance(payload["pressed"], bool) and _vec2(payload["position"])
    if command == "mouse_motion":
        return _vec2(payload["position"]) and _vec2(payload["relative"]) and ("button_mask" not in payload or _integer(payload["button_mask"], minimum=0))
    if command in {"project_command", "checkpoint"}:
        name = payload["name"] if command == "project_command" else payload["checkpoint"]
        return _string(name) and ("arguments" not in payload or isinstance(payload["arguments"], dict))
    if command in {"capture_structure", "capture_png"}:
        return _string(payload["capture_id"])
    if command == "movie_marker":
        return _string(payload["marker"])
    if command == "shutdown":
        return "exit_code" not in payload or _integer(payload["exit_code"])
    return False


def _validate_payload(message_type: str, payload: dict[str, Any]) -> None:
    if message_type == "hello":
        if not (
            _exact(payload, {"bridge_version", "capabilities", "single_client", "loopback_only"})
            and _string(payload["bridge_version"])
            and _strings(payload["capabilities"])
            and payload["single_client"] is True
            and payload["loopback_only"] is True
        ):
            raise GodotAutomationError("hello payload violates strict protocol fields")
    elif message_type == "handshake":
        if not (
            _exact(payload, {"token", "requested_capabilities"})
            and isinstance(payload["token"], str)
            and TOKEN_RE.fullmatch(payload["token"]) is not None
            and _strings(payload["requested_capabilities"])
        ):
            raise GodotAutomationError("handshake payload violates strict protocol fields")
    elif message_type == "handshake_ack":
        if not (
            _exact(payload, {"accepted"}, {"capabilities"})
            and isinstance(payload["accepted"], bool)
            and ("capabilities" not in payload or _strings(payload["capabilities"]))
        ):
            raise GodotAutomationError("handshake_ack payload violates strict protocol fields")
    elif message_type == "command":
        command = payload.get("command")
        if command not in COMMAND_FIELDS:
            raise GodotAutomationError("command payload is not declared by the protocol")
        required, optional = COMMAND_FIELDS[command]
        if not _exact(payload, required, optional) or not _validate_command(command, payload):
            raise GodotAutomationError("command payload violates strict protocol fields")
    elif message_type == "command_ack":
        if not (
            _exact(payload, {"ok"}, {"value", "applied_frame", "file"})
            and payload.get("ok") is True
            and ("applied_frame" not in payload or _integer(payload["applied_frame"], minimum=0))
            and ("file" not in payload or _string(payload["file"]))
        ):
            raise GodotAutomationError("command_ack payload violates strict protocol fields")
    elif message_type == "event":
        if not _exact(payload, {"event"}) or not isinstance(payload["event"], dict):
            raise GodotAutomationError("event payload violates strict protocol fields")
    elif message_type == "error":
        if not _exact(payload, {"error"}) or not isinstance(payload["error"], str):
            raise GodotAutomationError("error payload violates strict protocol fields")
    elif message_type == "shutdown" and payload:
        raise GodotAutomationError("shutdown payload must be empty")


def validate_message(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise GodotAutomationError("bridge message must be one JSON object")
    expected = {"protocol_version", "type", "message_id", "payload"}
    if set(value) != expected:
        raise GodotAutomationError(f"bridge message fields must be exactly {sorted(expected)}")
    if value["protocol_version"] != PROTOCOL_VERSION:
        raise GodotAutomationError("bridge protocol version mismatch")
    if value["type"] not in MESSAGE_TYPES:
        raise GodotAutomationError("unknown bridge message type")
    if not isinstance(value["message_id"], str) or not 1 <= len(value["message_id"]) <= 128:
        raise GodotAutomationError("bridge message_id is invalid")
    if not isinstance(value["payload"], dict):
        raise GodotAutomationError("bridge payload must be an object")
    _validate_payload(value["type"], value["payload"])
    return value


def encode_message(value: Any) -> bytes:
    payload = canonical_json_bytes(validate_message(value))
    if len(payload) > MAX_MESSAGE_BYTES:
        raise GodotAutomationError("bridge message exceeds 1 MiB limit")
    return HEADER.pack(len(payload)) + payload


def _receive_exact(stream: socket.socket, count: int) -> bytes:
    chunks: list[bytes] = []
    remaining = count
    while remaining:
        chunk = stream.recv(remaining)
        if not chunk:
            raise GodotAutomationError("bridge disconnected during message framing")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def receive_message(stream: socket.socket) -> dict[str, Any]:
    size = HEADER.unpack(_receive_exact(stream, HEADER.size))[0]
    if size < 2 or size > MAX_MESSAGE_BYTES:
        raise GodotAutomationError(f"invalid bridge message length: {size}")
    raw = _receive_exact(stream, size)
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise GodotAutomationError(f"bridge message is not valid UTF-8 JSON: {error}") from error
    return validate_message(value)


def make_message(message_type: str, payload: dict[str, Any], *, message_id: str | None = None) -> dict[str, Any]:
    return validate_message(
        {
            "protocol_version": PROTOCOL_VERSION,
            "type": message_type,
            "message_id": message_id or uuid.uuid4().hex,
            "payload": payload,
        }
    )


@dataclass
class BridgeClient:
    host: str
    port: int
    token: str
    timeout_seconds: float = 10.0
    stream: socket.socket | None = None
    hello: dict[str, Any] | None = None

    def connect(self) -> dict[str, Any]:
        if self.host != "127.0.0.1":
            raise GodotAutomationError("bridge client refuses non-loopback hosts")
        deadline = time.monotonic() + self.timeout_seconds
        last_error: OSError | None = None
        while time.monotonic() < deadline:
            stream = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            stream.settimeout(min(1.0, max(0.1, deadline - time.monotonic())))
            try:
                stream.connect((self.host, self.port))
                self.stream = stream
                break
            except OSError as error:
                last_error = error
                stream.close()
                time.sleep(0.05)
        if self.stream is None:
            raise GodotAutomationError(f"bridge did not accept loopback connection: {last_error}")
        self.stream.settimeout(self.timeout_seconds)
        hello = receive_message(self.stream)
        if hello["type"] != "hello":
            self.close()
            raise GodotAutomationError("bridge did not begin with protocol hello")
        self.hello = hello
        handshake = make_message(
            "handshake",
            {"token": self.token, "requested_capabilities": hello["payload"].get("capabilities", [])},
        )
        self.stream.sendall(encode_message(handshake))
        response = receive_message(self.stream)
        if response["type"] != "handshake_ack" or not response["payload"].get("accepted"):
            self.close()
            raise GodotAutomationError("bridge rejected session handshake")
        return redact(response, secrets=(self.token,))

    def request(self, command: dict[str, Any]) -> dict[str, Any]:
        if self.stream is None:
            raise GodotAutomationError("bridge client is not connected")
        request = make_message("command", command)
        self.stream.sendall(encode_message(request))
        while True:
            response = receive_message(self.stream)
            if response["type"] == "event":
                continue
            if response["message_id"] != request["message_id"]:
                raise GodotAutomationError("bridge response message_id mismatch")
            if response["type"] == "error":
                raise GodotAutomationError(str(response["payload"].get("error", "bridge command failed")))
            if response["type"] != "command_ack":
                raise GodotAutomationError("bridge returned an unexpected response type")
            return response["payload"]

    def close(self) -> None:
        if self.stream is not None:
            try:
                self.stream.close()
            finally:
                self.stream = None

    def __enter__(self) -> "BridgeClient":
        self.connect()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()
