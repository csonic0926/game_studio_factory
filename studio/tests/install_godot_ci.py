#!/usr/bin/env python3
"""Install one official Godot release asset on a GitHub-hosted CI runner."""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import stat
import tempfile
import urllib.request
import zipfile
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True, help="stable version such as 4.7.2")
    args = parser.parse_args()
    version = args.version
    system = platform.system()
    asset = {
        "Darwin": f"Godot_v{version}-stable_macos.universal.zip",
        "Linux": f"Godot_v{version}-stable_linux.x86_64.zip",
        "Windows": f"Godot_v{version}-stable_win64.exe.zip",
    }.get(system)
    if asset is None:
        raise SystemExit(f"unsupported CI platform: {system}")
    url = f"https://github.com/godotengine/godot/releases/download/{version}-stable/{asset}"
    root = Path(os.environ.get("RUNNER_TEMP", tempfile.gettempdir())) / f"godot-{version}"
    root.mkdir(parents=True, exist_ok=True)
    archive = root / asset
    request = urllib.request.Request(url, headers={"User-Agent": "game-studio-factory-ci"})
    with urllib.request.urlopen(request, timeout=120) as response, archive.open("wb") as output:
        shutil.copyfileobj(response, output)
    with zipfile.ZipFile(archive) as bundle:
        bundle.extractall(root)
    if system == "Darwin":
        source = next(root.rglob("Godot.app/Contents/MacOS/Godot"))
    elif system == "Windows":
        source = next(root.glob("Godot*.exe"))
    else:
        source = next(path for path in root.glob("Godot*linux*x86_64*") if path.is_file())
    source.chmod(source.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    bin_dir = root / "bin"
    bin_dir.mkdir(exist_ok=True)
    launcher = bin_dir / ("godot.exe" if system == "Windows" else "godot")
    if system == "Windows":
        shutil.copy2(source, launcher)
    else:
        launcher.symlink_to(source)
    with Path(os.environ["GITHUB_PATH"]).open("a", encoding="utf-8") as output:
        output.write(str(bin_dir) + "\n")
    with Path(os.environ["GITHUB_ENV"]).open("a", encoding="utf-8") as output:
        output.write(f"GODOT_BIN={launcher}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
