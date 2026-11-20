"""Black-box checks of the public Factory CLI; npm test does not need the source repo."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from PIL import Image

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"
CLI = HERE.parents[2] / "itf.py"
GOLDEN = json.loads((HERE / "upstream.json").read_text())


class PixelSnapTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def cli(self, *args, success=True, env=None):
        proc = subprocess.run([sys.executable, CLI, "pixel-snap", *map(str, args)], cwd=self.root,
                              capture_output=True, text=True, env=env)
        self.assertEqual(proc.returncode == 0, success, proc.stderr + proc.stdout)
        result = json.loads(proc.stdout)
        self.assertEqual(result["ok"], success)
        return result

    def test_original_pixels_and_metadata(self):
        for mode, expected in GOLDEN.items():
            args = ["--profile", mode] if mode != "scale5" else ["--profile", "balanced", "--scale", "5"]
            for native in (False, True):
                with self.subTest(mode=mode, true_grid=native):
                    dst = self.root / f"{mode}-{native}"
                    report = self.cli("--input", FIXTURES, "--out", dst, *args, *(["--true-grid"] if native else []))
                    records = report["files"]
                    self.assertEqual([Path(r["output"]).name for r in records], sorted(expected))
                    for rec in records:
                        name = Path(rec["input"]).name
                        self.assertEqual(rec["output"], str(dst / name))
                        ref = expected[name]
                        for key in ("profile", "targetScale", "gridW", "gridH", "finalColors", "sourceUniqueColors"):
                            self.assertEqual(rec[key], ref[key], (name, key))
                        with Image.open(dst / name) as im, Image.open(FIXTURES / name) as src:
                            self.assertEqual((rec["width"], rec["height"]), src.size)
                            self.assertEqual(im.size, (rec["outputWidth"], rec["outputHeight"]))
                            self.assertEqual(im.size, (ref["gridW"], ref["gridH"]) if native else src.size)
                            rgba = im.convert("RGBA").tobytes()
                        digest = ref["gridRgba256" if native else "rgba256"]
                        self.assertEqual(hashlib.sha256(rgba).hexdigest(), digest, name)
                        if name in ("room.png", "sprite.png"):
                            self.assertEqual(set(rgba[3::4]), {255} if name == "room.png" else {0, 255})

    def test_single_default_and_explicit_output_only(self):
        src, dst = self.root / "source.PNG", self.root / "delivery" / "icon.png"
        original = (FIXTURES / "icon.png").read_bytes()
        src.write_bytes(original)
        info, = self.cli("--input", src, "--out", dst)["files"]
        self.assertEqual((info["profile"], info["targetScale"]), ("conservative", 2))
        with Image.open(dst) as im:
            digest = hashlib.sha256(im.convert("RGBA").tobytes()).hexdigest()
        self.assertEqual(digest, GOLDEN["conservative"]["icon.png"]["rgba256"])
        self.cli("--input", src, "--out", src, success=False)
        self.cli("--input", src, "--out", dst, success=False)
        proc = subprocess.run([sys.executable, CLI, "pixel-snap", "--input", src], capture_output=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(src.read_bytes(), original)
        self.assertEqual(set(self.root.iterdir()), {src, dst.parent})

    def test_batch_selection_and_collision_preflight(self):
        src, dst = self.root / "in", self.root / "out"
        src.mkdir()
        for name in ("a.PNG", "b.png", "_skip.png", ".hidden.png", "old_snapped.png"):
            shutil.copyfile(FIXTURES / "icon.png", src / name)
        (src / "nested").mkdir()
        shutil.copyfile(FIXTURES / "sprite.png", src / "nested" / "c.png")
        dst.mkdir()
        (dst / "b.png").write_bytes(b"preexisting")
        self.cli("--input", src, "--out", dst, success=False)
        self.assertEqual(list(dst.iterdir()), [dst / "b.png"])
        self.assertEqual((dst / "b.png").read_bytes(), b"preexisting")
        self.cli("--input", src, "--out", src, success=False)
        files = self.cli("--input", src, "--out", self.root / "clean")["files"]
        self.assertEqual([Path(f["output"]).name for f in files], ["a.PNG", "b.png"])

    def test_encoder_never_replaces_a_late_collision(self):
        # Model a destination claimed after the CLI's preflight. Test the
        # actual write boundary without relying on the timing of two processes.
        dest = self.root / "claimed.png"
        dest.write_bytes(b"another caller's pixels")
        job = {"files": [{"input": str(FIXTURES / "icon.png"), "output": str(dest)}], "options": {}}
        proc = subprocess.run([os.environ.get("PIXEL_SNAP_NODE") or "node", HERE.parent / "worker.js"],
                              input=json.dumps(job), capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("EEXIST", proc.stderr)
        self.assertEqual(dest.read_bytes(), b"another caller's pixels")

    def test_rejects_invalid_inputs_before_output(self):
        dst = self.root / "out.png"
        for value in ("0", "-1", "nan", "inf"):
            self.cli("--input", FIXTURES / "icon.png", "--out", dst, "--scale", value, success=False)
        self.cli("--input", self.root, "--out", self.root / "batch", success=False)
        bad = self.root / "bad.png"
        bad.write_bytes(b"not a PNG")
        self.cli("--input", bad, "--out", dst, success=False)
        frame = Image.new("RGBA", (4, 4), "red")
        frame.save(bad, save_all=True, append_images=[Image.new("RGBA", frame.size, "blue")])
        result = self.cli("--input", bad, "--out", dst, success=False)
        self.assertIn("Animated PNG", result["error"])
        result = self.cli("--input", FIXTURES / "room.png", "--out", dst, success=False,
                          env={**os.environ, "PIXEL_SNAP_NODE": str(self.root / "missing-node")})
        self.assertIn("PIXEL_SNAP_NODE", result["error"])
        self.assertFalse(dst.exists())
        self.assertFalse((self.root / "batch").exists())

    def test_auto_large_scene_and_one_cell_minimum(self):
        src, dst = self.root / "wide.png", self.root / "tiny.png"
        Image.new("RGB", (768, 129), "navy").save(src)
        info, = self.cli("--input", src, "--out", dst, "--profile", "auto",
                         "--scale", "2000", "--true-grid")["files"]
        self.assertEqual((info["profile"], info["outputWidth"], info["outputHeight"]), ("chunky", 1, 1))


if __name__ == "__main__":
    unittest.main()
