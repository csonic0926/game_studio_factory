"""Render an isolated synthetic scene through the real exporter; no game copies."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class GodotCaptureTests(unittest.TestCase):
    def test_real_render_export_and_seal(self):
        required = os.environ.get("FACTORY_REQUIRE_UI_CAPTURE") == "1"
        engine = shutil.which("godot")
        if not engine:
            if required: self.fail("required Godot capture test has no engine")
            self.skipTest("Godot not installed")
        if shutil.disk_usage(tempfile.gettempdir()).free < 2 * 1024 ** 3 + 64 * 1024 ** 2:
            if required: self.fail("insufficient capture budget plus 2 GiB reserve")
            self.skipTest("insufficient capture budget plus 2 GiB reserve; no cleanup authorized")
        retained = os.environ.get("UI_CAPTURE_TEST_OUTPUT")
        if retained:
            game = Path(retained).resolve()
            game.mkdir(parents=True, exist_ok=False)
        else:
            temporary = tempfile.TemporaryDirectory(prefix="ui-exporter-test-")
            self.addCleanup(temporary.cleanup)
            game = Path(temporary.name).resolve()
        (game / "project.godot").write_text('config_version=5\n[application]\nconfig/name="Synthetic UI Export Test"\n[display]\nwindow/size/viewport_width=400\nwindow/size/viewport_height=240\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n')
        shutil.copyfile(ROOT / "ui/godot_engine/capture.gd", game / "capture.gd")
        (game / "runner.gd").write_text('''extends SceneTree
const Capture = preload("res://capture.gd")
func _initialize() -> void:
    call_deferred("run")
func run() -> void:
    var panel := Control.new()
    root.add_child(panel)
    var background := ColorRect.new()
    background.size = Vector2(400, 240)
    background.color = Color(0.9, 0.9, 0.9, 1)
    background.set_meta("ui_element_id", "chrome")
    panel.add_child(background)
    var action := Button.new()
    action.position = Vector2(150, 100)
    action.size = Vector2(100, 40)
    action.text = "Next"
    action.set_meta("ui_element_id", "advance")
    panel.add_child(action)
    await process_frame
    var frame: Dictionary = await Capture.sample(panel, "frame.png", 0, 0, true)
    if frame.is_empty():
        quit(2)
        return
    var build: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://build.json"))
    var value := {"schema_version":"ui_capture_export.v1", "origin":"RUNTIME", "game_revision":build.game_revision,
        "build_id":FileAccess.get_sha256("res://build.json"), "build_artifact":{"scope":"game","path":"build.json","sha256":FileAccess.get_sha256("res://build.json")},
        "exporter":{"scope":"game_git","path":"capture.gd","sha256":FileAccess.get_sha256("res://capture.gd"),"revision":build.game_revision},
        "scenario_id":"smoke", "state_id":"ready", "surface_id":"panel", "locale":"en", "viewport":[400,240], "frames":[frame]}
    var file := FileAccess.open("res://raw.json", FileAccess.WRITE)
    file.store_string(JSON.stringify(value))
    file.close()
    quit(0)
''')
        def run(args, **kwargs):
            result = subprocess.run(args, text=True, capture_output=True, timeout=90, **kwargs)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return result
        run(["git", "init", "-q", "-b", "main", str(game)])
        run(["git", "-C", str(game), "add", "project.godot", "runner.gd", "capture.gd"])
        run(["git", "-C", str(game), "-c", "user.name=Synthetic", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "Synthetic exporter test"])
        cli = [sys.executable, "-B", str(ROOT / "ui/ui_design.py")]
        run([*cli, "capture-build", "--game-repo", str(game), "--sources", "project.godot", "runner.gd", "capture.gd", "--entrypoint", "runner.gd", "--output", "build.json"])
        command = [engine, "--path", str(game), "--rendering-method", "gl_compatibility", "--position", "9000,9000", "--resolution", "400x240", "--audio-driver", "Dummy", "--script", "res://runner.gd"]
        if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
            xvfb = shutil.which("xvfb-run")
            if not xvfb: self.fail("real rendering requires Xvfb or a display; headless dummy frames are not evidence")
            command = [xvfb, "-a", *command]
        result = run(command)
        (game / "engine.log").write_text(result.stdout + result.stderr)
        self.assertNotIn("SCRIPT ERROR", result.stdout + result.stderr)
        run([*cli, "capture", "--game-repo", str(game), "--raw", "raw.json", "--output", "capture.json"])
        data = json.loads((game / "capture.json").read_text())
        elements = {item["element_id"]:item for item in data["frames"][0]["elements"]}
        self.assertEqual(elements["advance"]["bounds"], [150, 100, 100, 40])
        self.assertTrue(elements["advance"]["enabled"] and elements["advance"]["visible"])
        for actual, expected in zip(elements["chrome"]["color"], [0.9, 0.9, 0.9, 1]):
            self.assertAlmostEqual(actual, expected, places=5)
        from PIL import Image
        with Image.open(game / "frame.png") as image:
            self.assertEqual(image.size, (400, 240))
            self.assertGreater(len(image.getcolors(400 * 240) or []), 2)
