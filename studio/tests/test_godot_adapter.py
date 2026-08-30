from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from studio.godot_adapter import (
    FAIL,
    MANIFEST_RELATIVE,
    PASS,
    READY,
    TIMEOUT,
    GodotAdapterError,
    export_godot,
    import_check_godot,
    probe_godot,
    run_godot,
)

ADAPTER_SCRIPT = Path(__file__).resolve().parents[1] / "godot_adapter.py"

FAKE_GODOT = r'''#!/usr/bin/env python3
import pathlib
import sys
import time

args = sys.argv[1:]
if "--version" in args:
    print("4.7.0.stable.fake.abcdef123")
    raise SystemExit(0)
if "--help" in args:
    print("--headless --path --import --quit-after --scene --fixed-fps --log-file --export-debug --export-release --write-movie")
    raise SystemExit(0)

project = pathlib.Path(args[args.index("--path") + 1])
mode_path = project / "fake_mode.txt"
mode = mode_path.read_text(encoding="utf-8").strip() if mode_path.exists() else "success"
if mode == "sleep":
    time.sleep(5)
if mode == "mutate":
    with (project / "main.gd").open("a", encoding="utf-8") as source:
        source.write("\n# fake engine mutation\n")

lines = ["FAKE_GODOT_READY"]
if mode == "error":
    lines.append("SCRIPT ERROR: Parse Error: fake failure")

if "--export-debug" in args or "--export-release" in args:
    switch = "--export-debug" if "--export-debug" in args else "--export-release"
    index = args.index(switch)
    output = pathlib.Path(args[index + 2])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("fake build\n", encoding="utf-8")

text = "\n".join(lines) + "\n"
print(text, end="")
if "--log-file" in args:
    log_path = pathlib.Path(args[args.index("--log-file") + 1])
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(text, encoding="utf-8")
raise SystemExit(0)
'''


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


class GodotAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repo = self.root / "game"
        self.repo.mkdir()
        _git(self.repo, "init", "-q")
        _git(self.repo, "config", "user.email", "tests@example.com")
        _git(self.repo, "config", "user.name", "Tests")
        (self.repo / ".gitignore").write_text(".godot/\n", encoding="utf-8")
        (self.repo / "project.godot").write_text(
            """[application]
config/name="Godot Adapter Test"
run/main_scene="res://main.tscn"

[display]
window/size/viewport_width=320
window/size/viewport_height=180

[rendering]
renderer/rendering_method="gl_compatibility"
renderer/rendering_method.mobile="gl_compatibility"
""",
            encoding="utf-8",
        )
        (self.repo / "main.tscn").write_text(
            """[gd_scene load_steps=2 format=3]

[ext_resource path="res://main.gd" type="Script" id="1"]

[node name="Main" type="Node"]
script = ExtResource("1")
""",
            encoding="utf-8",
        )
        (self.repo / "main.gd").write_text(
            """extends Node

func _ready():
    print("REAL_GODOT_ADAPTER_READY")
    get_tree().quit(0)
""",
            encoding="utf-8",
        )
        (self.repo / "fake_mode.txt").write_text("success\n", encoding="utf-8")
        _git(self.repo, "add", ".")
        _git(self.repo, "commit", "-qm", "fixture")

        self.fake_godot = self.root / "fake-godot"
        self.fake_godot.write_text(FAKE_GODOT, encoding="utf-8")
        self.fake_godot.chmod(0o755)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _payload(self, relative: str) -> dict:
        return json.loads((self.repo / relative).read_text(encoding="utf-8"))

    def _set_fake_mode(self, mode: str) -> None:
        (self.repo / "fake_mode.txt").write_text(mode + "\n", encoding="utf-8")
        _git(self.repo, "add", "fake_mode.txt")
        _git(self.repo, "commit", "-qm", f"fake mode {mode}")

    def test_probe_writes_honest_capability_manifest(self) -> None:
        result = probe_godot(self.repo, godot_bin=str(self.fake_godot))

        self.assertEqual(READY, result.status)
        self.assertEqual(MANIFEST_RELATIVE.as_posix(), result.artifact_path)
        payload = self._payload(result.artifact_path)
        self.assertEqual("godot_engine_capability_manifest.v1", payload["schema_version"])
        self.assertEqual("4.7.0.stable.fake.abcdef123", payload["engine"]["version"])
        capabilities = {
            item["capability_id"]: item["status"] for item in payload["capabilities"]
        }
        self.assertEqual("AVAILABLE", capabilities["HEADLESS_IMPORT_CHECK"])
        self.assertEqual("PARTIAL", capabilities["DETERMINISTIC_FRAME_WINDOW"])
        self.assertEqual("NOT_IMPLEMENTED", capabilities["INPUT_INJECTION"])
        self.assertEqual("NOT_IMPLEMENTED", capabilities["STRUCTURED_RUNTIME_STATE"])
        self.assertNotIn(str(self.root), json.dumps(payload))

    def test_direct_cli_probe_returns_machine_readable_result(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                str(ADAPTER_SCRIPT),
                "probe",
                "--game-repo",
                str(self.repo),
                "--godot-bin",
                str(self.fake_godot),
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        self.assertEqual(0, completed.returncode, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(READY, result["status"])
        self.assertEqual(MANIFEST_RELATIVE.as_posix(), result["artifact_path"])

    def test_import_check_captures_hashed_logs(self) -> None:
        result = import_check_godot(
            self.repo,
            operation_id="import.smoke",
            godot_bin=str(self.fake_godot),
        )

        self.assertEqual(PASS, result.status)
        payload = self._payload(result.artifact_path)
        self.assertEqual("IMPORT_CHECK", payload["operation_type"])
        self.assertEqual(3, len(payload["artifacts"]))
        self.assertFalse(payload["project"]["source_mutated"])
        self.assertEqual(
            payload["project"]["project_file_before"],
            payload["project"]["project_file_after"],
        )
        self.assertEqual("EVIDENCE_ONLY", payload["acceptance_authority"])
        self.assertEqual("NOT_ISSUED", payload["gameplay_verdict"])

    def test_run_captures_expected_output_without_absolute_repo_paths(self) -> None:
        result = run_godot(
            self.repo,
            operation_id="run.smoke",
            godot_bin=str(self.fake_godot),
            scene="res://main.tscn",
            expected_output=["FAKE_GODOT_READY"],
        )

        self.assertEqual(PASS, result.status)
        payload = self._payload(result.artifact_path)
        self.assertEqual("RUN_SCENE", payload["operation_type"])
        self.assertTrue(payload["result"]["assertions"][0]["passed"])
        rendered = json.dumps(payload)
        self.assertNotIn(str(self.repo), rendered)
        self.assertTrue(payload["invocation"]["command"][0].startswith("<GODOT_BINARY:"))

    def test_logged_script_error_fails_even_when_engine_exits_zero(self) -> None:
        self._set_fake_mode("error")
        result = run_godot(
            self.repo,
            operation_id="run.error",
            godot_bin=str(self.fake_godot),
        )

        self.assertEqual(FAIL, result.status)
        payload = self._payload(result.artifact_path)
        self.assertIn(
            "SCRIPT ERROR: Parse Error: fake failure",
            payload["result"]["detected_errors"],
        )

    def test_timeout_terminates_process_and_records_evidence(self) -> None:
        self._set_fake_mode("sleep")
        result = run_godot(
            self.repo,
            operation_id="run.timeout",
            godot_bin=str(self.fake_godot),
            timeout_seconds=0.05,
        )

        self.assertEqual(TIMEOUT, result.status)
        payload = self._payload(result.artifact_path)
        self.assertTrue(payload["result"]["timed_out"])
        self.assertIn(payload["result"]["termination"], {"TERMINATE", "KILL"})

    def test_evidence_operation_id_is_immutable(self) -> None:
        run_godot(
            self.repo,
            operation_id="run.once",
            godot_bin=str(self.fake_godot),
        )
        manifest_path = self.repo / MANIFEST_RELATIVE
        manifest_before = manifest_path.read_bytes()
        with self.assertRaisesRegex(GodotAdapterError, "immutable"):
            run_godot(
                self.repo,
                operation_id="run.once",
                godot_bin=str(self.fake_godot),
            )
        self.assertEqual(manifest_before, manifest_path.read_bytes())

    def test_source_mutation_fails_operation(self) -> None:
        self._set_fake_mode("mutate")
        result = run_godot(
            self.repo,
            operation_id="run.mutates",
            godot_bin=str(self.fake_godot),
        )

        self.assertEqual(FAIL, result.status)
        payload = self._payload(result.artifact_path)
        self.assertTrue(payload["project"]["source_mutated"])
        self.assertNotEqual(
            payload["project"]["source_repository_before"],
            payload["project"]["source_repository_after"],
        )

    def test_empty_output_assertion_is_rejected_without_writing_evidence(self) -> None:
        with self.assertRaisesRegex(GodotAdapterError, "non-empty"):
            run_godot(
                self.repo,
                operation_id="run.empty-marker",
                godot_bin=str(self.fake_godot),
                expected_output=[""],
            )
        self.assertFalse(
            (self.repo / "design/studio/engine/godot/evidence/run.empty-marker").exists()
        )

    def test_repo_and_scene_paths_cannot_escape(self) -> None:
        with self.assertRaisesRegex(GodotAdapterError, "escapes game repo"):
            probe_godot(
                self.repo,
                project_dir_text="../",
                godot_bin=str(self.fake_godot),
            )
        outside = self.root / "outside.tscn"
        outside.write_text("[gd_scene format=3]\n", encoding="utf-8")
        with self.assertRaisesRegex(GodotAdapterError, "does not exist inside"):
            run_godot(
                self.repo,
                operation_id="run.escape",
                godot_bin=str(self.fake_godot),
                scene="res://../outside.tscn",
            )

    def test_export_records_build_as_artifact_not_source_mutation(self) -> None:
        (self.repo / "export_presets.cfg").write_text(
            '[preset.0]\nname="Fake"\nplatform="Linux/BSD"\n',
            encoding="utf-8",
        )
        _git(self.repo, "add", "export_presets.cfg")
        _git(self.repo, "commit", "-qm", "add export preset")

        result = export_godot(
            self.repo,
            operation_id="export.fake",
            preset="Fake",
            output="builds/fake.pck",
            godot_bin=str(self.fake_godot),
        )

        self.assertEqual(PASS, result.status)
        payload = self._payload(result.artifact_path)
        self.assertFalse(payload["project"]["source_mutated"])
        roles = {item["role"] for item in payload["artifacts"]}
        self.assertIn("EXPORTED_BUILD", roles)


class RealGodotAdapterIntegrationTests(unittest.TestCase):
    @unittest.skipUnless(
        shutil.which("godot") or shutil.which("godot4"),
        "Godot is not installed",
    )
    def test_real_godot_import_and_bounded_run(self) -> None:
        binary = shutil.which("godot") or shutil.which("godot4")
        assert binary is not None
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp) / "game"
            repo.mkdir()
            _git(repo, "init", "-q")
            _git(repo, "config", "user.email", "tests@example.com")
            _git(repo, "config", "user.name", "Tests")
            (repo / ".gitignore").write_text(".godot/\n", encoding="utf-8")
            (repo / "project.godot").write_text(
                """[application]
config/name="Real Adapter Smoke"
run/main_scene="res://main.tscn"

[rendering]
renderer/rendering_method="gl_compatibility"
renderer/rendering_method.mobile="gl_compatibility"
""",
                encoding="utf-8",
            )
            (repo / "main.tscn").write_text(
                """[gd_scene load_steps=2 format=3]

[ext_resource path="res://main.gd" type="Script" id="1"]

[node name="Main" type="Node"]
script = ExtResource("1")
""",
                encoding="utf-8",
            )
            (repo / "main.gd").write_text(
                """extends Node

func _ready():
	print("REAL_GODOT_ADAPTER_READY")
	get_tree().quit(0)
""",
                encoding="utf-8",
            )
            # Godot 4.4+ may create adjacent script UID files during the first
            # import.  Establish that canonical imported state before testing
            # the adapter's no-source-mutation invariant.
            subprocess.run(
                [binary, "--headless", "--path", str(repo), "--import"],
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            _git(repo, "add", ".")
            _git(repo, "commit", "-qm", "real fixture")

            imported = import_check_godot(
                repo,
                operation_id="real.import",
                godot_bin=binary,
            )
            run = run_godot(
                repo,
                operation_id="real.run",
                godot_bin=binary,
                expected_output=["REAL_GODOT_ADAPTER_READY"],
                quit_after=10,
            )

            self.assertEqual(PASS, imported.status)
            self.assertEqual(PASS, run.status)
            evidence = json.loads((repo / run.artifact_path).read_text(encoding="utf-8"))
            self.assertEqual([], evidence["result"]["detected_errors"])
            self.assertTrue(evidence["result"]["assertions"][0]["passed"])


if __name__ == "__main__":
    unittest.main()
