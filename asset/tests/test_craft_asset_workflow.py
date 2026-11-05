"""Offline contracts. Fake editors are test doubles, never a production provider."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import textwrap
import unittest
from unittest.mock import patch

from PIL import Image

from pipeline.craft_asset_workflow import (
    FACTORY_ROOT, SCHEMA, _references, load_craft_spec, run_craft_assets, validate_export,
)
from pipeline.craft_client import CraftClient, CraftError, check_result, find_cli


class FakeEditor:
    calls = []
    instances = []
    bad_canvas = False
    fail_command = False
    fail_native = False

    def __init__(self, editor, read_root, write_root, log_dir, **kwargs):
        self.editor = editor
        self.cli = "test-double-only"
        self.server = {"serverInfo": {"name": editor, "version": "test"}}
        self.read_root, self.write_root = read_root, write_root
        self.closed = False
        self.instances.append(self)

    def tool(self, name, **params):
        self.calls.append((name, params))
        if name == "command_run":
            if self.fail_command:
                raise CraftError("test engine error")
            return {"id": 42}
        if name in ("save_file", "doc_save"):
            if not self.fail_native:
                Path(params["path"]).write_text("native-test-fixture")
            return {}
        if name in ("open_file", "doc_open"):
            return {"warnings": ["test import warning"]}
        if name in ("export", "doc_export"):
            path = Path(params["path"])
            if path.suffix == ".svg":
                path.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16"><rect width="16" height="16"/></svg>')
            else:
                image = Image.new("RGBA", (2, 2) if self.bad_canvas else (16, 16), (12, 40, 60, 255))
                image.putpixel((0, 0), (0, 0, 0, 0))
                image.save(path)
            return {"warnings": ["flattened export"]}
        return {"layers": [{"id": 42}]}

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.closed = True


class CraftWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.path = self.root / "spec.json"
        self.spec = {
            "schema_version": SCHEMA, "run_id": "test", "output_root": "out", "editor": "vectorcraft",
            "document": {"new": {"width": 16, "height": 16}},
            "steps": [{"command": "shape.rectangle", "params": {"width": 8, "height": 8}},
                      {"command": "paint.setFill", "params": {"ids": ["$step.0.id"], "color": "#183A4A"}}],
            "exports": [{"name": "test.png", "width": 16, "height": 16, "alpha": "transparent"},
                        {"name": "test.svg"}],
        }
        FakeEditor.calls, FakeEditor.instances = [], []
        FakeEditor.bad_canvas = FakeEditor.fail_command = FakeEditor.fail_native = False

    def write(self):
        self.path.write_text(json.dumps(self.spec))
        return self.path

    def run_fake(self, **kwargs):
        with patch("pipeline.craft_asset_workflow.CraftClient", FakeEditor):
            return run_craft_assets(self.write(), **kwargs)

    def test_relative_paths_are_spec_relative(self):
        source = self.root / "base.png"
        Image.new("RGBA", (16, 16), "red").save(source)
        self.spec.update(inputs={"base": "base.png"}, document={"input": "base"})
        spec, root = load_craft_spec(self.write())
        self.assertEqual(spec["inputs"]["base"], str(source))
        self.assertEqual(root, self.root / "out" / "test")

    def test_invalid_contracts_rejected_before_run_directory(self):
        variants = [
            {"schema_version": "prop_asset_workflow_v1"}, {"editor": "gpt_image"}, {"editor": []},
            {"run_id": "../escape"}, {"output_root": ""}, {"steps": {}},
            {"document": {}}, {"document": {"input": "missing"}},
            {"document": {"new": {"width": True, "height": 16}}},
            {"document": {"new": {"width": 16, "height": 16}, "input": "base"}},
            {"exports": []}, {"exports": [{"name": "only.svg"}]},
            {"exports": [{"name": "../escape.png", "width": 16, "height": 16}]},
            {"exports": [{"name": "x.png", "width": 16, "height": 16, "alpha": "maybe"}]},
            {"exports": [{"name": "x.png", "width": 16, "height": 16, "params": {"path": "/tmp/override"}}]},
            {"exports": [{"name": "x.png", "width": 16, "height": 16, "params": {"index": 0}}]},
            {"exports": [{"name": "x.png", "width": 16, "height": 16}, {"name": "X.png", "width": 16, "height": 16}]},
            {"editor": "photocraft"}, {"inputs": {"base": "missing.png"}},
            {"provider": {"name": "mock"}}, {"steps": [{"command": "x", "params": {"x": float("nan")}}]},
        ]
        original = copy.deepcopy(self.spec)
        for variant in variants:
            with self.subTest(variant=variant):
                self.spec = {**original, **variant}
                with self.assertRaises(CraftError):
                    load_craft_spec(self.write())
        self.assertFalse((self.root / "out").exists())

    def test_no_outputs_in_factory_checkout(self):
        with self.assertRaisesRegex(CraftError, "not the Factory"):
            load_craft_spec(self.write(), out=FACTORY_ROOT / "asset" / "output" / "craft-test")

    def test_input_ids_cannot_collide_on_case_insensitive_filesystems(self):
        source = self.root / "input.png"
        Image.new("RGBA", (16, 16), "red").save(source)
        self.spec["inputs"] = {"base": str(source), "BASE": str(source)}
        with self.assertRaisesRegex(CraftError, "case-colliding"):
            load_craft_spec(self.write())

    def test_vector_success_retains_source_and_provenance(self):
        result = self.run_fake()
        root = Path(result["run_root"])
        self.assertTrue(result["ok"])
        self.assertEqual(result["creative_acceptance"], "not_assessed")
        self.assertTrue((root / "source/test.vectorcraft").is_file())
        self.assertTrue((root / "logs/document.reopened.json").is_file())
        manifest = json.loads((root / "deliverables/craft_asset_manifest.json").read_text())
        self.assertEqual(len(manifest["native_source"]["sha256"]), 64)
        self.assertEqual(len(manifest["recipe_sha256"]), 64)
        self.assertEqual(manifest["exports"][0]["alpha_extrema"], [0, 255])
        self.assertTrue(manifest["warnings"])
        self.assertEqual(FakeEditor.calls[2][1]["params"]["ids"], [42])
        names = [name for name, _ in FakeEditor.calls]
        self.assertLess(names.index("save_file"), names.index("open_file"))
        self.assertLess(names.index("open_file"), names.index("export"))
        self.assertTrue(FakeEditor.instances[0].closed)

    def test_photo_input_staged_and_source_never_overwritten(self):
        source = self.root / "base.png"
        Image.new("RGBA", (16, 16), "red").save(source)
        before = source.read_bytes()
        self.spec.update(editor="photocraft", inputs={"base": "base.png"}, document={"input": "base"},
                         steps=[{"command": "file.placeEmbedded", "params": {"path": "$input.base"}}],
                         exports=self.spec["exports"][:1])
        result = self.run_fake()
        root = Path(result["run_root"])
        self.assertEqual(source.read_bytes(), before)
        self.assertEqual((root / "inputs/base.png").read_bytes(), before)
        self.assertEqual(FakeEditor.calls[0], ("doc_open", {"path": str(root / "inputs/base.png")}))
        call = next(params for name, params in FakeEditor.calls if name == "command_run")
        self.assertTrue(call["wait"])
        self.assertEqual(call["params"]["path"], str(root / "inputs/base.png"))
        self.assertTrue((root / "source/test.pcraft").is_file())
        self.assertEqual(FakeEditor.instances[0].write_root, root / "work")
        self.assertEqual(FakeEditor.instances[0].read_root, root)

    def test_existing_run_is_never_overwritten(self):
        result = self.run_fake()
        status = Path(result["run_root"]) / "artifact_status.json"
        before = status.read_bytes()
        with self.assertRaisesRegex(CraftError, "already exists"):
            self.run_fake()
        self.assertEqual(status.read_bytes(), before)

    def test_failed_engine_does_not_promote_outputs(self):
        FakeEditor.fail_command = True
        with self.assertRaisesRegex(CraftError, "engine error"):
            self.run_fake()
        root = self.root / "out/test"
        status = json.loads((root / "artifact_status.json").read_text())
        self.assertFalse(status["ok"])
        self.assertEqual(status["stage"], "failed")
        self.assertFalse((root / "deliverables").exists())
        self.assertTrue(FakeEditor.instances[0].closed)

    def test_missing_native_save_fails_closed(self):
        FakeEditor.fail_native = True
        with self.assertRaisesRegex(CraftError, "artifact"):
            self.run_fake()
        self.assertFalse((self.root / "out/test/deliverables").exists())

    def test_invalid_canvas_fails_before_promotion(self):
        FakeEditor.bad_canvas = True
        with self.assertRaisesRegex(CraftError, "Canvas mismatch"):
            self.run_fake()
        root = self.root / "out/test"
        status = json.loads((root / "artifact_status.json").read_text())
        self.assertEqual(status["failed_stage"], "validation")
        self.assertFalse(status["ok"])
        self.assertFalse(json.loads((root / "logs/validation_summary.json").read_text())["ok"])
        self.assertFalse((root / "deliverables").exists())

    def test_references_fail_on_unknown_or_future_result(self):
        for value in ("$input.missing", "$step.1.id", "$step.-1.id", "$step.0.missing"):
            with self.subTest(value=value), self.assertRaises(CraftError):
                _references(value, {}, [{"id": 12}])
        self.assertEqual(_references([{"ids": ["$step.0.id"]}], {}, [{"id": 12}]), [{"ids": [12]}])

    def test_raster_alpha_and_empty_checks(self):
        path = self.root / "x.png"
        export = {"width": 16, "height": 16, "alpha": "transparent"}
        for color, message in [((12, 20, 30, 255), "transparent"), ((0, 0, 0, 0), "Empty")]:
            Image.new("RGBA", (16, 16), color).save(path)
            with self.assertRaisesRegex(CraftError, message):
                validate_export(path, export, self.root)
        Image.new("RGBA", (16, 16), (20, 30, 40, 200)).save(path)
        with self.assertRaisesRegex(CraftError, "opaque"):
            validate_export(path, {**export, "alpha": "opaque"}, self.root)

    def test_wrong_format_svg_and_symlink_rejected(self):
        path = self.root / "x.png"
        Image.new("RGB", (16, 16), "red").save(path, format="JPEG")
        with self.assertRaisesRegex(CraftError, "Format mismatch"):
            validate_export(path, {"width": 16, "height": 16, "alpha": "any"}, self.root)
        svg = self.root / "x.svg"
        svg.write_text("<html/>")
        with self.assertRaisesRegex(CraftError, "Not an SVG"):
            validate_export(svg, {}, self.root)
        link = self.root / "link.png"
        link.symlink_to(path)
        with self.assertRaisesRegex(CraftError, "escaped"):
            validate_export(link, {}, self.root)


class CraftClientTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def server(self, mode):
        """A real subprocess exercises protocol framing, EOF, deadlines and cleanup."""
        path = self.root / "fake-editor"
        script = textwrap.dedent('''\
            import json, os, sys, time
            from pathlib import Path
            Path("launch.json").write_text(json.dumps({"args": sys.argv[1:], "home": os.environ["HOME"],
                "bridge": os.environ.get("PHOTOCRAFT_CONTROL_PORT")}))
            mode = MODE
            for line in sys.stdin:
                request = json.loads(line)
                if "id" not in request:
                    continue
                method = request["method"]
                if method == "initialize":
                    if mode == "eof":
                        sys.exit(0)
                    if mode == "timeout":
                        time.sleep(10)
                    if mode == "malformed":
                        print("not-json", flush=True)
                        continue
                    result = {"serverInfo": {"name": "fake", "version": "test"}}
                else:
                    if mode == "rpc_error":
                        print(json.dumps({"id": request["id"], "error": {"code": -32602, "message": "bad params"}}), flush=True)
                        continue
                    content = {"ok": False, "error": "engine failed"} if mode == "semantic_error" else {"ok": True}
                    result = {"isError": mode == "tool_error", "content": [{"type": "text", "text": json.dumps(content)}]}
                print(json.dumps({"jsonrpc": "2.0", "method": "notifications/progress", "params": {}}), flush=True)
                print(json.dumps({"jsonrpc": "2.0", "id": request["id"], "result": result}), flush=True)
        ''').replace("MODE", repr(mode))
        path.write_text(f"#!{sys.executable}\n" + script)
        path.chmod(0o755)
        return str(path)

    def client(self, mode="ok", editor="vectorcraft", timeout=2):
        return CraftClient(editor, self.root, self.root / "work", self.root / "logs",
                           cli=self.server(mode), timeout=timeout)

    def test_real_stdio_and_private_roots_environment(self):
        with patch.dict(os.environ, {"PHOTOCRAFT_CONTROL_PORT": "7979", "VECTORCRAFT_AUTOMATION_WRITE_ROOT": "/"}):
            with self.client(editor="photocraft") as client:
                process = client.p
                self.assertEqual(client.tool("command_list"), {"ok": True})
                launch = json.loads((self.root / "work/launch.json").read_text())
                self.assertIsNone(launch["bridge"])
                self.assertEqual(launch["args"].count("--automation-read-root"), 1)
                self.assertEqual(launch["args"][-1], str(self.root / "work"))
                self.assertTrue(launch["home"].startswith(str(self.root / "work")))
        self.assertIsNotNone(process.poll())

    def test_vector_forces_headless(self):
        with self.client():
            launch = json.loads((self.root / "work/launch.json").read_text())
            self.assertIn("--headless", launch["args"])

    def test_eof_and_malformed_json_fail_instead_of_hanging(self):
        for mode, message in [("eof", "EOF"), ("malformed", "invalid MCP JSON")]:
            with self.subTest(mode=mode), self.assertRaisesRegex(CraftError, message):
                self.client(mode)

    def test_timeout_closes_child(self):
        with self.assertRaisesRegex(CraftError, "timed out"):
            self.client("timeout", timeout=0.1)

    def test_interrupted_initialization_reaps_child(self):
        processes = []
        popen = subprocess.Popen

        def capture(*args, **kwargs):
            process = popen(*args, **kwargs)
            processes.append(process)
            return process

        with patch("pipeline.craft_client.subprocess.Popen", side_effect=capture), \
                patch.object(CraftClient, "_rpc", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.client()
        self.assertEqual(len(processes), 1)
        self.assertIsNotNone(processes[0].poll())

    def test_protocol_tool_and_engine_failures(self):
        for mode in ("rpc_error", "tool_error", "semantic_error"):
            with self.subTest(mode=mode), self.client(mode) as client:
                with self.assertRaises(CraftError):
                    client.tool("command_run", id="test")

    def test_nested_or_unfinished_results_are_not_success(self):
        for result in ({"failed": 1}, {"results": [{"ok": False}]}, {"pending": True},
                       {"job": 3}, {"status": "cancelled"}, "cancelled"):
            with self.subTest(result=result), self.assertRaises(CraftError):
                check_result(result, "test")

    def test_missing_explicit_cli_never_falls_back(self):
        with self.assertRaisesRegex(CraftError, "VECTORCRAFT_CLI"):
            find_cli("vectorcraft", str(self.root / "missing"))


if __name__ == "__main__":
    unittest.main()
