"""Opt-in, local-engine tests. No network, model calls, or desktop/global MCP use.

FACTORY_CRAFT_LIVE_TESTS=1 VECTORCRAFT_CLI=... PHOTOCRAFT_CLI=... pytest ...
Missing binaries fail the explicitly requested live suite, rather than mocking it.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest

from PIL import Image

from pipeline.craft_asset_workflow import run_craft_assets
from pipeline.craft_client import CraftClient, CraftError, find_cli


EXAMPLES = Path(__file__).resolve().parents[1] / "examples/craft_asset_workflow"


@unittest.skipUnless(os.environ.get("FACTORY_CRAFT_LIVE_TESTS") == "1", "opt-in real Craft editors")
class CraftEditorIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="asset-craft-live-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.clis = {name: find_cli(name) for name in ("vectorcraft", "photocraft")}

    def run_example(self, name, inputs=None):
        spec = json.loads((EXAMPLES / f"{name}.spec.json").read_text())
        spec["output_root"] = str(self.root / "runs")
        if inputs is not None:
            spec["inputs"] = inputs
        path = self.root / f"{name}.spec.json"
        path.write_text(json.dumps(spec))
        result = run_craft_assets(path, cli=self.clis[spec["editor"]])
        self.assertTrue(result["ok"])
        return Path(result["run_root"])

    def test_vector_to_photo_preserves_alpha_and_editable_adjustment(self):
        vector = self.run_example("vector_badge")
        source = vector / "deliverables/badge.png"
        original_bytes = source.read_bytes()
        photo = self.run_example("photo_refine", {"base": str(source)})
        self.assertEqual(source.read_bytes(), original_bytes)
        with Image.open(source) as original, Image.open(photo / "deliverables/refined.png") as edited:
            self.assertEqual(original.size, (128, 128))
            self.assertEqual(edited.size, (128, 128))
            self.assertEqual(original.convert("RGBA").getchannel("A").tobytes(),
                             edited.convert("RGBA").getchannel("A").tobytes())
            self.assertNotEqual(original.convert("RGB").tobytes(), edited.convert("RGB").tobytes())
        self.assertTrue((vector / "source/vector_badge.vectorcraft").is_file())
        self.assertTrue((vector / "deliverables/badge.svg").is_file())
        # Check the delivered native source too (not only the work/ copy).
        with CraftClient("photocraft", self.root, self.root / "verify", self.root / "verify-logs",
                         cli=self.clis["photocraft"]) as client:
            client.tool("doc_open", path=str(photo / "source/photo_refine.pcraft"))
            document = client.tool("doc_inspect")
            self.assertTrue(any(layer.get("kind") == "Adjustment" for layer in document["layers"]))

    def test_photo_new_document_retains_layers(self):
        root = self.run_example("photo_panel")
        document = json.loads((root / "logs/document.reopened.json").read_text())
        self.assertGreaterEqual(len(document["layers"]), 2)
        self.assertTrue((root / "source/photo_panel.pcraft").is_file())

    def test_editors_enforce_file_roots(self):
        allowed = self.root / "allowed"
        allowed.mkdir()
        unlisted = self.root / "unlisted.png"
        Image.new("RGB", (16, 16), "red").save(unlisted)
        original_bytes = unlisted.read_bytes()
        for editor in self.clis:
            with self.subTest(editor=editor):
                with CraftClient(editor, allowed, allowed / editor, self.root / f"{editor}-logs",
                                 cli=self.clis[editor]) as client:
                    with self.assertRaises(CraftError):
                        client.tool("open_file" if editor == "vectorcraft" else "doc_open", path=str(unlisted))
                    if editor == "vectorcraft":
                        client.command("file.new", {"width": 16, "height": 16})
                        tool, suffix = "save_file", ".vectorcraft"
                    else:
                        client.tool("doc_new", width=16, height=16)
                        tool, suffix = "doc_save", ".pcraft"
                    outside = self.root / ("denied" + suffix)
                    with self.assertRaises(CraftError):
                        client.tool(tool, path=str(outside))
                    self.assertFalse(outside.exists())
        self.assertEqual(unlisted.read_bytes(), original_bytes)


if __name__ == "__main__":
    unittest.main()
