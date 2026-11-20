"""Factory I/O contract for the optional Node pixel-snap engine."""

from __future__ import annotations

import json
import math
import os
import subprocess
from pathlib import Path

from PIL import Image

WORKER = Path(__file__).with_name("pixel_snap") / "worker.js"
PROFILES = ("conservative", "balanced", "chunky", "auto")


def _plan_files(source: Path, out: Path) -> list[dict[str, str]]:
    # Keep the final output component lexical: a dangling link is a collision,
    # not permission to create its target.
    source, out = source.expanduser().absolute(), out.expanduser().absolute()
    if source.is_dir():
        if source.resolve() == out.resolve():
            raise ValueError("Choose an output directory different from the input directory")
        if os.path.lexists(out) and not out.is_dir():
            raise ValueError(f"Expected an output directory: {out}")
        inputs = sorted(p for p in source.iterdir() if p.is_file()
                        and p.suffix.lower() == ".png" and not p.name.startswith((".", "_"))
                        and not p.name.lower().endswith("_snapped.png"))
        if not inputs:
            raise ValueError(f"No eligible PNG files in {source} (nonrecursive)")
        pairs = [(p, out / p.name) for p in inputs]
    else:
        if not source.is_file() or source.suffix.lower() != ".png":
            raise ValueError(f"Expected an input PNG or directory: {source}")
        if out.suffix.lower() != ".png":
            raise ValueError(f"Expected an explicit .png output path: {out}")
        pairs = [(source, out)]

    # Check the entire plan before starting any writes. The encoder also uses
    # exclusive creation, so a later collision cannot overwrite someone else's file.
    for src, dest in pairs:
        if os.path.lexists(dest):
            raise ValueError(f"Refusing to overwrite existing output: {dest}")
        try:
            with Image.open(src, formats=["PNG"]) as im:
                if im.is_animated:
                    raise ValueError(f"Animated PNG is not supported: {src}")
        except Image.DecompressionBombError as exc:
            raise ValueError(f"{src}: {exc}") from exc
    return [{"input": str(src), "output": str(dest)} for src, dest in pairs]


def run_pixel_snap(source: Path, out: Path, *, profile: str, scale: float | None,
                   true_grid: bool) -> dict:
    if profile not in PROFILES:
        raise ValueError(f"Unknown pixel-snap profile: {profile}")
    options = {"profile": profile, "trueGrid": true_grid}
    if scale is not None:
        if not math.isfinite(scale) or scale < 1:
            raise ValueError("--scale must be a finite number >= 1")
        options["targetScale"] = scale
    files = _plan_files(source, out)
    node = os.environ.get("PIXEL_SNAP_NODE") or "node"
    try:
        proc = subprocess.run([node, str(WORKER)], text=True, capture_output=True,
                              input=json.dumps({"files": files, "options": options}))
    except FileNotFoundError as exc:
        raise ValueError("pixel-snap needs Node.js >=20.3 on PATH or via PIXEL_SNAP_NODE") from exc

    records = [json.loads(line) for line in proc.stdout.splitlines()]
    ok = proc.returncode == 0 and len(records) == len(files)
    result = {"ok": ok, "mode": "pixel-snap", "requestedProfile": profile, "trueGrid": true_grid, "files": records}
    if proc.returncode:
        result["error"] = proc.stderr.strip() or f"pixel-snap worker exited {proc.returncode}"
        if proc.returncode < 0 and not records:
            result["error"] += "\nCheck that Node runs; select a working executable via PIXEL_SNAP_NODE."
    elif not ok:
        result["error"] = f"Expected {len(files)} output records, received {len(records)}"
    return result
