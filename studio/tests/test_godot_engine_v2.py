from __future__ import annotations

import binascii
import hashlib
import io
import json
import os
import shutil
import socket
import struct
import subprocess
import tempfile
import threading
import unittest
import zlib
from pathlib import Path

from studio.godot_engine.api import GodotSession, _validate_live_command, serve_jsonl
from studio.godot_engine.bridge import (
    AUTOLOAD_NAME,
    BridgePlan,
    bridge_check,
    bridge_install,
    bridge_remove,
    bridge_upgrade,
)
from studio.godot_engine.build import run_build
from studio.godot_engine.common import (
    BRIDGE_PROFILE_RELATIVE,
    EVIDENCE_ROOT,
    GodotAutomationError,
    sha256_file,
)
from studio.godot_engine.evidence import EvidenceTransaction, recover_evidence, verify_evidence
from studio.godot_engine.doctor import run_doctor
from studio.godot_engine.protocol import (
    MAX_MESSAGE_BYTES,
    BridgeClient,
    encode_message,
    make_message,
    receive_message,
)
from studio.godot_engine.scenario import compare_traces, normalized_trace, replay_scenario, run_scenario
from studio.godot_engine.schema import validate_profile, validate_scenario
from studio.godot_engine.visual import compare_visual


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True,
        text=True, encoding="utf-8",
    )
    return result.stdout.strip()


def _repo(root: Path) -> Path:
    repo = root / "game"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "tests@example.com")
    _git(repo, "config", "user.name", "Tests")
    (repo / ".gitignore").write_text(".godot/\n", encoding="utf-8")
    (repo / "project.godot").write_text(
        '[application]\nconfig/name="Godot Automation Test"\nrun/main_scene="res://main.tscn"\n',
        encoding="utf-8",
    )
    (repo / "main.tscn").write_text('[gd_scene format=3]\n\n[node name="Main" type="Node"]\n', encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "fixture")
    return repo


def _profile() -> dict:
    return {
        "schema_version": "godot_bridge_profile.v1",
        "profile_id": "test.profile",
        "provider_autoload": "Provider",
        "allowed_input_actions": ["test_action"],
        "allowed_keycodes": [65],
        "allowed_mouse_buttons": [1],
        "project_commands": ["set_value", "fail"],
        "observations": ["value"],
        "checkpoints": ["reset"],
        "structural_nodes": [
            {"id": "ui", "node_path": "/root/Main/UI", "facts": ["class", "visible", "position", "size", "focus"]}
        ],
    }


def _scenario() -> dict:
    return {
        "schema_version": "godot_scenario.v1",
        "scenario_id": "test.scenario",
        "seed": 42,
        "initial_checkpoint": "reset",
        "required_capabilities": ["FRAME_BOUND_EXECUTION", "PROJECT_COMMAND"],
        "fixed_fps": 60,
        "max_frames": 120,
        "steps": [
            {"type": "wait_frames", "frames": 2},
            {"type": "input_action", "action": "test_action", "pressed": True},
            {"type": "wait_frames", "frames": 1},
            {"type": "input_action", "action": "test_action", "pressed": False},
            {"type": "project_command", "command": "set_value", "arguments": {"value": 7}},
            {"type": "wait_until", "condition": {"actual": "value", "operator": "eq", "expected": 7}, "deadline_frames": 5},
            {"type": "snapshot", "snapshot_id": "value", "kind": "OBSERVABLE", "observation": "value"},
            {"type": "assert", "assertion_id": "value.is.7", "actual": "value", "operator": "eq", "expected": 7},
            {"type": "capture_structure", "capture_id": "ui"},
            {"type": "finish", "exit_code": 0},
        ],
        "expected_exit": "BRIDGE_FINISH",
    }


class StrictContractTests(unittest.TestCase):
    def test_scenario_union_rejects_unknown_and_extra_fields(self) -> None:
        scenario = _scenario()
        scenario["steps"][0]["surprise"] = True
        with self.assertRaisesRegex(GodotAutomationError, "unknown fields"):
            validate_scenario(scenario)
        scenario = _scenario()
        scenario["steps"][0]["type"] = "eval"
        with self.assertRaisesRegex(GodotAutomationError, "unsupported type"):
            validate_scenario(scenario)

    def test_wait_until_requires_a_positive_deadline(self) -> None:
        scenario = _scenario()
        scenario["steps"][5]["deadline_frames"] = 0
        with self.assertRaisesRegex(GodotAutomationError, "positive"):
            validate_scenario(scenario)

    def test_profile_rejects_undeclared_structural_property(self) -> None:
        profile = _profile()
        profile["structural_nodes"][0]["facts"].append("arbitrary_property")
        with self.assertRaisesRegex(GodotAutomationError, "unsupported structural"):
            validate_profile(profile)

    def test_live_command_rejects_arbitrary_method_and_property_mutation(self) -> None:
        for command in (
            {"command": "eval", "source": "quit()"},
            {"command": "set_property", "path": "/root/Main", "name": "visible"},
            {"command": "project_command", "name": "not_declared"},
        ):
            with self.assertRaises(GodotAutomationError):
                _validate_live_command(command, _profile())


class ProtocolTests(unittest.TestCase):
    def test_length_prefixed_json_round_trip(self) -> None:
        left, right = socket.socketpair()
        try:
            message = make_message("event", {"event": {"frame": 9}}, message_id="m1")
            left.sendall(encode_message(message))
            self.assertEqual(message, receive_message(right))
        finally:
            left.close()
            right.close()

    def test_message_limit_and_unknown_fields_are_rejected(self) -> None:
        with self.assertRaisesRegex(GodotAutomationError, "1 MiB"):
            encode_message(make_message("event", {"event": {"value": "x" * MAX_MESSAGE_BYTES}}))
        value = make_message("event", {"event": {}})
        value["extra"] = True
        with self.assertRaisesRegex(GodotAutomationError, "exactly"):
            encode_message(value)

    def test_command_payload_types_are_enforced_before_transport(self) -> None:
        invalid = (
            {"command": "input_action", "action": "jump", "pressed": 1},
            {"command": "mouse_motion", "position": [0], "relative": [0, 0]},
            {"command": "project_command", "name": "setup", "arguments": []},
        )
        for command in invalid:
            with self.assertRaisesRegex(GodotAutomationError, "strict protocol"):
                make_message("command", command)

    def test_non_loopback_client_is_refused(self) -> None:
        with self.assertRaisesRegex(GodotAutomationError, "non-loopback"):
            BridgeClient("0.0.0.0", 1234, "0" * 64, 0.1).connect()

    def test_wrong_session_token_is_rejected_by_handshake(self) -> None:
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]

        def server() -> None:
            stream, _ = listener.accept()
            try:
                hello = make_message("hello", {"bridge_version": "test", "capabilities": [], "single_client": True, "loopback_only": True}, message_id="hello")
                stream.sendall(encode_message(hello))
                handshake = receive_message(stream)
                accepted = handshake["payload"]["token"] == "a" * 64
                stream.sendall(encode_message(make_message("handshake_ack", {"accepted": accepted}, message_id=handshake["message_id"])))
            finally:
                stream.close()
                listener.close()

        thread = threading.Thread(target=server)
        thread.start()
        try:
            with self.assertRaisesRegex(GodotAutomationError, "rejected"):
                BridgeClient("127.0.0.1", port, "b" * 64, 2).connect()
        finally:
            thread.join(timeout=2)


class BridgeInstallerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = _repo(Path(self.temp.name))

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_install_is_dry_run_by_default_and_apply_is_evidence_bound(self) -> None:
        dry = bridge_install(self.repo, autoload=True)
        self.assertIsInstance(dry, BridgePlan)
        self.assertTrue(dry.apply_required)
        self.assertFalse((self.repo / "addons/game_studio_godot_bridge").exists())
        result = bridge_install(self.repo, apply=True, autoload=True, operation_id="bridge.install")
        self.assertEqual("PASS", result.status)
        vendor = self.repo / "addons/game_studio_godot_bridge/bridge.gd"
        self.assertTrue(vendor.is_file())
        self.assertFalse(vendor.is_symlink())
        self.assertIn(AUTOLOAD_NAME, (self.repo / "project.godot").read_text(encoding="utf-8"))
        evidence = json.loads((self.repo / result.artifact_path).read_text(encoding="utf-8"))
        self.assertTrue(evidence["project"]["source_mutated"])
        self.assertTrue(evidence["project"]["source_mutation_allowed"])

    def test_upgrade_and_remove_refuse_manual_vendor_drift(self) -> None:
        bridge_install(self.repo, apply=True, operation_id="bridge.install")
        vendor = self.repo / "addons/game_studio_godot_bridge/bridge.gd"
        vendor.write_text(vendor.read_text(encoding="utf-8") + "\n# manual\n", encoding="utf-8")
        with self.assertRaisesRegex(GodotAutomationError, "vendor drift"):
            bridge_upgrade(self.repo, apply=True, operation_id="bridge.upgrade")
        with self.assertRaisesRegex(GodotAutomationError, "vendor drift"):
            bridge_remove(self.repo, apply=True, operation_id="bridge.remove")

    def test_upgrade_preserves_project_profile_and_remove_leaves_it(self) -> None:
        bridge_install(self.repo, apply=True, autoload=True, operation_id="bridge.install")
        profile_path = self.repo / BRIDGE_PROFILE_RELATIVE
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text(json.dumps(_profile()), encoding="utf-8")
        before = profile_path.read_bytes()
        upgraded = bridge_upgrade(self.repo, apply=True, operation_id="bridge.upgrade")
        self.assertEqual("PASS", upgraded.status)
        self.assertEqual(before, profile_path.read_bytes())
        removed = bridge_remove(self.repo, apply=True, operation_id="bridge.remove")
        self.assertEqual("PASS", removed.status)
        self.assertEqual(before, profile_path.read_bytes())
        self.assertNotIn(AUTOLOAD_NAME, (self.repo / "project.godot").read_text(encoding="utf-8"))

    def test_extra_vendor_file_is_drift_not_a_project_handler(self) -> None:
        bridge_install(self.repo, apply=True, operation_id="bridge.install")
        (self.repo / "addons/game_studio_godot_bridge/custom.gd").write_text("extends Node\n", encoding="utf-8")
        with self.assertRaisesRegex(GodotAutomationError, "file set drift"):
            bridge_check(self.repo)


class EvidenceTransactionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = _repo(Path(self.temp.name))

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_redaction_immutability_and_offline_verify(self) -> None:
        token = "a" * 64
        tx = EvidenceTransaction(self.repo, operation_id="evidence.one", operation_type="DOCTOR", project_dir=self.repo, engine=None, automation_manifest={"token": token}, secrets=(token,))
        tx.write_text("stdout.log", f"repo={self.repo} token={token}", "STDOUT_LOG")
        trace_path = tx.path("session_trace.jsonl")
        trace_path.write_text(json.dumps({"schema_version": "godot_session_trace_record.v1", "sequence": 0, "frame": 0, "kind": "COMMAND", "payload": {"arguments": {"password": "do-not-keep"}}}) + "\n", encoding="utf-8")
        tx.scrub_text_file(trace_path)
        tx.register(trace_path, "SESSION_TRACE")
        result = tx.finalize(status="PASS", invocation={"command": [f"--studio-token={token}"]}, result={})
        text = (self.repo / result.artifact_path).read_text(encoding="utf-8")
        log = (self.repo / EVIDENCE_ROOT / "evidence.one/stdout.log").read_text(encoding="utf-8")
        trace = trace_path.read_text(encoding="utf-8")
        self.assertNotIn(token, text + log + trace)
        self.assertNotIn("do-not-keep", trace)
        self.assertNotIn(str(self.repo), text + log + trace)
        self.assertEqual("PASS", verify_evidence(self.repo, result.artifact_path).status)
        with self.assertRaisesRegex(GodotAutomationError, "cannot be reused"):
            EvidenceTransaction(self.repo, operation_id="evidence.one", operation_type="DOCTOR", project_dir=self.repo, engine=None, automation_manifest={})

    def test_unexpected_source_mutation_turns_pass_into_fail(self) -> None:
        tx = EvidenceTransaction(self.repo, operation_id="evidence.mutate", operation_type="DOCTOR", project_dir=self.repo, engine=None, automation_manifest={})
        (self.repo / "main.tscn").write_text("[gd_scene format=3]\n# changed\n", encoding="utf-8")
        result = tx.finalize(status="PASS", invocation={}, result={})
        self.assertEqual("FAIL", result.status)

    def test_recover_seals_interrupted_operation_as_aborted(self) -> None:
        tx = EvidenceTransaction(self.repo, operation_id="evidence.crash", operation_type="SCENARIO_RUN", project_dir=self.repo, engine=None, automation_manifest={})
        tx.path("raw.log").write_text("partial", encoding="utf-8")
        result = recover_evidence(self.repo, "evidence.crash")
        self.assertEqual("ABORTED", result.status)
        payload = json.loads((self.repo / result.artifact_path).read_text(encoding="utf-8"))
        self.assertEqual("ABORTED", payload["status"])

    def test_trace_comparison_reports_first_state_divergence(self) -> None:
        first = self.repo / "first.jsonl"
        second = self.repo / "second.jsonl"
        base = [
            {"schema_version": "godot_session_trace_record.v1", "sequence": 0, "frame": 2, "kind": "BRIDGE_READY", "payload": {}},
            {"schema_version": "godot_session_trace_record.v1", "sequence": 1, "frame": 3, "kind": "SNAPSHOT", "payload": {"value": 1}},
        ]
        first.write_text("\n".join(json.dumps(item) for item in base) + "\n", encoding="utf-8")
        base[1]["payload"]["value"] = 2
        second.write_text("\n".join(json.dumps(item) for item in base) + "\n", encoding="utf-8")
        result = compare_traces(first, second)
        self.assertEqual("DIVERGED", result["status"])
        self.assertEqual(0, result["first_divergence"])


class BuildRunTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = _repo(Path(self.temp.name))
        self.build = self.repo / ("build.cmd" if os.name == "nt" else "build")
        self.build.write_text("@echo RELEASE_SMOKE\r\n" if os.name == "nt" else "#!/bin/sh\necho RELEASE_SMOKE\n", encoding="utf-8")
        self.build.chmod(0o755)
        _git(self.repo, "add", self.build.name)
        _git(self.repo, "commit", "-qm", "build")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_release_build_smoke_never_enables_bridge(self) -> None:
        result = run_build(self.repo, operation_id="build.release", build_text=self.build.name, mode="release", expected_output=["RELEASE_SMOKE"])
        self.assertEqual("PASS", result.status)
        payload = json.loads((self.repo / result.artifact_path).read_text(encoding="utf-8"))
        self.assertTrue(payload["result"]["release_bridge_disabled"])
        self.assertEqual("NOT_ISSUED", payload["gameplay_verdict"])

    def test_release_build_rejects_bridge_flags(self) -> None:
        with self.assertRaisesRegex(GodotAutomationError, "forbid bridge"):
            run_build(self.repo, operation_id="build.unsafe", build_text=self.build.name, mode="release", arguments=["--studio-adapter-enabled"])


def _write_png(path: Path, rgba: tuple[int, int, int, int]) -> None:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", binascii.crc32(kind + data) & 0xFFFFFFFF)
    raw = b"\x00" + bytes(rgba)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


@unittest.skipUnless(shutil.which("godot") or shutil.which("godot4"), "Godot is not installed")
class VisualComparisonTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = _repo(Path(self.temp.name))
        _write_png(self.repo / "base.png", (255, 0, 0, 255))
        _write_png(self.repo / "actual.png", (255, 0, 0, 255))
        self.structure = {"schema_version": "godot_structural_capture.v1", "frame": 1, "nodes": [{"id": "ui", "exists": True, "visible": True}]}
        (self.repo / "base_structure.json").write_text(json.dumps(self.structure), encoding="utf-8")
        actual = {**self.structure, "frame": 99}
        (self.repo / "actual_structure.json").write_text(json.dumps(actual), encoding="utf-8")
        (self.repo / "approval.json").write_text(json.dumps({"status": "ACCEPTED_PLAYABLE_BASELINE"}), encoding="utf-8")
        binary = shutil.which("godot") or shutil.which("godot4")
        assert binary
        version = subprocess.run([binary, "--version"], check=True, capture_output=True, text=True).stdout.strip()
        self.environment = {"godot_version": version, "platform": __import__("platform").system(), "renderer": "gl_compatibility", "viewport": [1, 1], "locale": "en", "scale": 1.0}
        self._write_baseline()
        _git(self.repo, "add", ".")
        _git(self.repo, "commit", "-qm", "visual fixture")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _hash(self, name: str) -> str:
        return sha256_file(self.repo / name)

    def _write_baseline(self, tolerances: dict | None = None) -> None:
        baseline = {
            "schema_version": "godot_visual_baseline.v1",
            "baseline_id": "approved.ui",
            "environment": self.environment,
            "source_revision": "0" * 40,
            "image": {"path": "base.png", "sha256": self._hash("base.png")},
            "structure": {"path": "base_structure.json", "sha256": self._hash("base_structure.json")},
            "approval_evidence": {"path": "approval.json", "sha256": self._hash("approval.json")},
        }
        if tolerances is not None:
            baseline["tolerances"] = tolerances
        (self.repo / "baseline.json").write_text(json.dumps(baseline), encoding="utf-8")

    def _compare(self, operation_id: str, environment: dict | None = None):
        return compare_visual(self.repo, operation_id=operation_id, baseline_text="baseline.json", actual_image_text="actual.png", actual_structure_text="actual_structure.json", actual_environment=environment or self.environment)

    def test_exact_default_passes_and_produces_engine_metrics_and_diff(self) -> None:
        result = self._compare("visual.exact")
        self.assertEqual("PASS", result.status)
        payload = json.loads((self.repo / result.artifact_path).read_text(encoding="utf-8"))
        self.assertEqual(0.0, payload["result"]["visual"]["metrics"]["max"])
        roles = {item["role"] for item in payload["artifacts"]}
        self.assertIn("VISUAL_DIFF", roles)

    def test_structural_failure_stops_before_pixel_comparison(self) -> None:
        actual = json.loads((self.repo / "actual_structure.json").read_text(encoding="utf-8"))
        actual["nodes"][0]["visible"] = False
        (self.repo / "actual_structure.json").write_text(json.dumps(actual), encoding="utf-8")
        result = self._compare("visual.structure-fail")
        self.assertEqual("FAIL", result.status)
        payload = json.loads((self.repo / result.artifact_path).read_text(encoding="utf-8"))
        self.assertEqual("INCONCLUSIVE", payload["result"]["visual"]["image_status"])
        self.assertNotIn("IMAGE_METRICS", {item["role"] for item in payload["artifacts"]})

    def test_environment_mismatch_is_blocked(self) -> None:
        environment = {**self.environment, "renderer": "forward_plus"}
        result = self._compare("visual.environment", environment)
        self.assertEqual("BLOCKED", result.status)

    def test_missing_baseline_is_blocked_with_evidence(self) -> None:
        result = compare_visual(self.repo, operation_id="visual.missing", baseline_text="missing.json", actual_image_text="actual.png", actual_structure_text="actual_structure.json", actual_environment=self.environment)
        self.assertEqual("BLOCKED", result.status)

    def test_threshold_failure_keeps_diff_artifact(self) -> None:
        _write_png(self.repo / "actual.png", (0, 0, 255, 255))
        result = self._compare("visual.pixel-fail")
        self.assertEqual("FAIL", result.status)
        payload = json.loads((self.repo / result.artifact_path).read_text(encoding="utf-8"))
        self.assertGreater(payload["result"]["visual"]["metrics"]["changed_pixel_ratio"], 0)
        self.assertIsNotNone(payload["result"]["visual"]["changed_bbox"])

    def test_declared_thresholds_can_pass_without_changing_the_baseline(self) -> None:
        _write_png(self.repo / "actual.png", (250, 0, 0, 255))
        self._write_baseline({"max": 255.0, "mean": 255.0, "rmse": 255.0, "min_psnr": 0.0, "changed_pixel_ratio": 1.0})
        result = self._compare("visual.threshold-pass")
        self.assertEqual("PASS", result.status)


@unittest.skipUnless(shutil.which("godot") or shutil.which("godot4"), "Godot is not installed")
class RealBridgeIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = tempfile.TemporaryDirectory()
        cls.repo = _repo(Path(cls.temp.name))
        project = cls.repo / "project.godot"
        project.write_text(
            '''[application]\nconfig/name="Bridge Integration"\nrun/main_scene="res://main.tscn"\n\n[display]\nwindow/size/viewport_width=64\nwindow/size/viewport_height=64\n\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n\n[autoload]\nProvider="*res://provider.gd"\n\n[input]\ntest_action={\n"deadzone": 0.5,\n"events": []\n}\n''',
            encoding="utf-8",
        )
        (cls.repo / "main.tscn").write_text(
            '''[gd_scene format=3]\n\n[node name="Main" type="Node"]\n\n[node name="UI" type="Control" parent="."]\noffset_right = 64.0\noffset_bottom = 64.0\n''',
            encoding="utf-8",
        )
        (cls.repo / "provider.gd").write_text(
            '''extends Node\nvar value := 0\nvar resolved := false\nfunc _process(_delta):\n\tif Input.is_action_pressed("test_action") and not resolved:\n\t\tresolved = true\n\t\tGameStudioGodotBridge.record_project_resolved_action("test_action", {"owner": "project"})\nfunc studio_bridge_command(name, arguments):\n\tif name == "set_value": value = int(arguments.get("value", 0)); return value\n\tif name == "fail": return {"ok": false, "error": "fixture project command failed"}\n\treturn null\nfunc studio_bridge_observe(_name): return value\nfunc studio_bridge_checkpoint(_name, _arguments): value = 0; resolved = false; return true\nfunc studio_bridge_mechanical_snapshot(): return {"value": value}\n''',
            encoding="utf-8",
        )
        _git(cls.repo, "add", ".")
        _git(cls.repo, "commit", "-qm", "runtime fixture")
        bridge_install(cls.repo, apply=True, autoload=True, operation_id="bridge.install")
        profile_path = cls.repo / BRIDGE_PROFILE_RELATIVE
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text(json.dumps(_profile()), encoding="utf-8")
        (cls.repo / "scenario.json").write_text(json.dumps(_scenario()), encoding="utf-8")
        binary = shutil.which("godot") or shutil.which("godot4")
        assert binary
        subprocess.run([binary, "--headless", "--path", str(cls.repo), "--import"], check=True, capture_output=True, text=True)
        _git(cls.repo, "add", ".")
        _git(cls.repo, "commit", "-qm", "installed bridge fixture")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp.cleanup()

    def test_same_scenario_three_times_has_identical_normalized_input_state_trace(self) -> None:
        traces = []
        for index in range(3):
            result = run_scenario(self.repo, operation_id=f"scenario.stable-{index}", scenario_text="scenario.json")
            self.assertEqual("PASS", result.status)
            trace = self.repo / EVIDENCE_ROOT / f"scenario.stable-{index}/session_trace.jsonl"
            traces.append(normalized_trace(trace))
        self.assertEqual(traces[0], traces[1])
        self.assertEqual(traces[1], traces[2])
        kinds = [item["kind"] for item in traces[0]]
        self.assertIn("INJECTED_INPUT", kinds)
        self.assertIn("PROJECT_RESOLVED_ACTION", kinds)

    def test_replay_matches_same_seed_checkpoint_and_trace(self) -> None:
        first = run_scenario(self.repo, operation_id="scenario.reference", scenario_text="scenario.json")
        self.assertEqual("PASS", first.status)
        reference = EVIDENCE_ROOT / "scenario.reference/session_trace.jsonl"
        replay = replay_scenario(self.repo, operation_id="scenario.replay", scenario_text="scenario.json", reference_trace_text=reference)
        self.assertEqual("PASS", replay.status)
        payload = json.loads((self.repo / replay.artifact_path).read_text(encoding="utf-8"))
        self.assertEqual("MATCH", payload["replay"]["status"])

    def test_live_session_handshake_snapshot_command_and_shutdown(self) -> None:
        with GodotSession(self.repo, operation_id="session.live", seed=42, initial_checkpoint="reset") as session:
            session.input_action("test_action", True)
            session.input_action("test_action", False)
            frame = session.snapshot("frame")
            self.assertTrue(frame["ok"])
            changed = session.command_request({"command": "project_command", "name": "set_value", "arguments": {"value": 11}})
            self.assertEqual(11, changed["value"])
            observed = session.snapshot("value", "value")
            self.assertEqual(11, observed["value"])
        assert session.result
        self.assertEqual("PASS", session.result.status)
        bridge_result = json.loads((self.repo / EVIDENCE_ROOT / "session.live/bridge_result.json").read_text(encoding="utf-8"))
        self.assertEqual(42, bridge_result["seed"])
        self.assertEqual("reset", bridge_result["initial_checkpoint"])

    def test_live_jsonl_capture_disconnect_and_process_failure_are_bounded(self) -> None:
        input_stream = io.StringIO(json.dumps({"id": "frame", "command": {"command": "snapshot", "snapshot_id": "frame", "kind": "OBSERVABLE", "observation": "bridge.frame"}}) + "\n")
        output_stream = io.StringIO()
        jsonl_result = serve_jsonl(GodotSession(self.repo, operation_id="session.jsonl"), input_stream, output_stream)
        self.assertEqual("PASS", jsonl_result.status)
        self.assertEqual("PASS", json.loads(output_stream.getvalue())["status"])

        with GodotSession(self.repo, operation_id="session.capture", windowed=True) as capture_session:
            capture_session.capture_png("live")
        assert capture_session.result
        capture_evidence = json.loads((self.repo / capture_session.result.artifact_path).read_text(encoding="utf-8"))
        self.assertIn("PNG_CAPTURE", {item["role"] for item in capture_evidence["artifacts"]})

        with GodotSession(self.repo, operation_id="session.disconnect", connect_timeout_seconds=2) as disconnected:
            assert disconnected.client
            disconnected.client.close()
        assert disconnected.result
        self.assertEqual("FAIL", disconnected.result.status)

        with GodotSession(self.repo, operation_id="session.process-failure", connect_timeout_seconds=2) as crashed:
            assert crashed.process
            crashed.process.kill()
            crashed.process.wait(timeout=3)
        assert crashed.result
        self.assertEqual("FAIL", crashed.result.status)

    def test_doctor_reports_bridge_profile_and_required_observability(self) -> None:
        result = run_doctor(self.repo, operation_id="doctor.ready", required_capabilities=["PROJECT_OBSERVATION", "PROJECT_CHECKPOINT"])
        self.assertEqual("PASS", result.status)
        payload = json.loads((self.repo / result.artifact_path).read_text(encoding="utf-8"))
        self.assertEqual([], payload["result"]["doctor"]["blockers"])

    def test_unknown_capability_and_release_bridge_are_blocked(self) -> None:
        scenario = _scenario()
        scenario["required_capabilities"].append("ARBITRARY_EVAL")
        (self.repo / "blocked_scenario.json").write_text(json.dumps(scenario), encoding="utf-8")
        missing = run_scenario(self.repo, operation_id="scenario.capability-blocked", scenario_text="blocked_scenario.json")
        self.assertEqual("BLOCKED", missing.status)
        release = run_scenario(self.repo, operation_id="scenario.release-blocked", scenario_text="scenario.json", runtime_kind="release_export")
        self.assertEqual("BLOCKED", release.status)

    def test_scenario_timeout_project_failure_input_contract_and_inconclusive_replay(self) -> None:
        timeout_scenario = _scenario()
        timeout_scenario["steps"][5]["condition"]["expected"] = 999
        (self.repo / "timeout_scenario.json").write_text(json.dumps(timeout_scenario), encoding="utf-8")
        timed_out = run_scenario(self.repo, operation_id="scenario.condition-timeout", scenario_text="timeout_scenario.json")
        self.assertEqual("FAIL", timed_out.status)

        command_failure = _scenario()
        command_failure["steps"][4]["command"] = "fail"
        (self.repo / "command_failure_scenario.json").write_text(json.dumps(command_failure), encoding="utf-8")
        failed = run_scenario(self.repo, operation_id="scenario.command-failure", scenario_text="command_failure_scenario.json")
        self.assertEqual("FAIL", failed.status)

        input_scenario = _scenario()
        input_scenario["required_capabilities"].extend(["KEY_INPUT", "MOUSE_INPUT"])
        input_scenario["steps"][-1:-1] = [
            {"type": "key_event", "keycode": 65, "pressed": True},
            {"type": "key_event", "keycode": 65, "pressed": False},
            {"type": "mouse_motion", "position": [10, 10], "relative": [2, 1]},
            {"type": "mouse_button", "button_index": 1, "pressed": True, "position": [10, 10]},
            {"type": "mouse_button", "button_index": 1, "pressed": False, "position": [10, 10]},
            {"type": "snapshot", "snapshot_id": "mechanical", "kind": "MECHANICAL"},
        ]
        (self.repo / "input_scenario.json").write_text(json.dumps(input_scenario), encoding="utf-8")
        inputs = run_scenario(self.repo, operation_id="scenario.input-contract", scenario_text="input_scenario.json")
        self.assertEqual("PASS", inputs.status)
        trace = normalized_trace(self.repo / EVIDENCE_ROOT / "scenario.input-contract/session_trace.jsonl")
        injected_kinds = [record["payload"]["kind"] for record in trace if record["kind"] == "INJECTED_INPUT"]
        self.assertIn("KEY", injected_kinds)
        self.assertIn("MOUSE_BUTTON", injected_kinds)
        self.assertIn("MOUSE_MOTION", injected_kinds)

        reference = run_scenario(self.repo, operation_id="scenario.inconclusive-reference", scenario_text="scenario.json")
        self.assertEqual("PASS", reference.status)
        changed_seed = _scenario()
        changed_seed["seed"] += 1
        (self.repo / "changed_seed_scenario.json").write_text(json.dumps(changed_seed), encoding="utf-8")
        replay = replay_scenario(
            self.repo,
            operation_id="scenario.inconclusive-replay",
            scenario_text="changed_seed_scenario.json",
            reference_trace_text=EVIDENCE_ROOT / "scenario.inconclusive-reference/session_trace.jsonl",
        )
        self.assertEqual("BLOCKED", replay.status)
        replay_evidence = json.loads((self.repo / replay.artifact_path).read_text(encoding="utf-8"))
        self.assertEqual("INCONCLUSIVE", replay_evidence["replay"]["status"])

    def test_windowed_capture_and_movie_are_hashed_artifacts(self) -> None:
        scenario = _scenario()
        scenario["required_capabilities"].append("PNG_CAPTURE")
        scenario["steps"][-1:-1] = [
            {"type": "capture_png", "capture_id": "window"},
            {"type": "movie_marker", "marker": "capture.complete"},
        ]
        (self.repo / "visual_scenario.json").write_text(json.dumps(scenario), encoding="utf-8")
        result = run_scenario(self.repo, operation_id="scenario.windowed", scenario_text="visual_scenario.json", windowed=True)
        self.assertEqual("PASS", result.status)
        payload = json.loads((self.repo / result.artifact_path).read_text(encoding="utf-8"))
        roles = {item["role"] for item in payload["artifacts"]}
        self.assertIn("PNG_CAPTURE", roles)
        self.assertIn("MOVIE_CAPTURE", roles)
        self.assertIn("GODOT_LOG", roles)


if __name__ == "__main__":
    unittest.main()
