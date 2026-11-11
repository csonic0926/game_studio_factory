"""Explicit UI capture sealing, capture-first packets and checked visual indexes.

No engine is launched by the CLI. The Godot exporter is awaited by the game's
isolated, authorized runner. Outputs are opt-in and exclusive, never overwrites.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import subprocess
from pathlib import Path
from urllib.parse import quote

from factory_core.refs import (FactoryError, confined, exclusive_json, fail, read_json,
                               reference, resolve_ref)
from ui.experience import capture, contract, evaluate, game_file, shape


def seal_capture(roots, raw):
    shape(raw, "raw_capture")
    value = {key: child for key, child in raw.items() if key != "frames"}
    value["schema_version"] = "ui_runtime_capture.v1"
    value["frames"] = []
    for frame in raw["frames"]:
        row = {key: child for key, child in frame.items() if key != "image_path"}
        row["image"] = reference(roots["game"], frame["image_path"])
        value["frames"].append(row)
    capture(roots, value)
    if value["origin"] == "RUNTIME":
        manifest = read_json(game_file(roots, value["build_artifact"]))
        for source in manifest["sources"]:
            live = reference(roots["game"], source["path"])
            if live["sha256"] != source["sha256"]:
                fail("INVALID_UI_CAPTURE", "consumed source changed since the captured build revision")
    return value


def build_manifest(roots, paths, entrypoint):
    """Prepare exact consumed source identities BEFORE starting an isolated runner."""
    import hashlib
    from factory_core.refs import revision, GitFile
    committed = revision(roots["game"])
    sources = []
    for path in paths:
        historical = GitFile(roots["game"], path, committed)
        checksum = hashlib.sha256(historical.read_bytes()).hexdigest()
        if reference(roots["game"], path)["sha256"] != checksum:
            fail("INVALID_UI_CAPTURE", "commit consumed runtime sources before capture; do not silently stamp dirty code")
        sources.append(dict(scope="game_git", path=path, sha256=checksum, revision=committed))
    tree = subprocess.run(["git", "-C", str(roots["game"]), "rev-parse", committed + "^{tree}"], text=True, capture_output=True, timeout=10)
    value = dict(schema_version="ui_capture_build.v1", game_revision=committed, git_tree=tree.stdout.strip(), entrypoint=entrypoint, sources=sources, binary=None)
    shape(value, "build_manifest")
    if "project.godot" not in paths or entrypoint not in paths:
        fail("INVALID_UI_CAPTURE", "include project.godot and the actual runner entrypoint")
    return value


def visual_packet(roots, design_ref, design):
    value = contract(roots, design)
    if value is None:
        fail("UI_EXPERIENCE_REQUIRED", "capture-first packets require a new experience contract")
    images, presentations = [], []
    for ref in value["design_captures"]:
        bundle = capture(roots, read_json(game_file(roots, ref)))
        images.extend(frame["image"] for frame in bundle["frames"])
        presentations.append({key: bundle[key] for key in ("origin", "locale", "viewport")})
    # Do not deliver telemetry, facts, intended outcomes or the author's diagnoses.
    # This is expert visual review, NOT the separate Studio blind Phase A packet.
    return {"schema_version": "ui_visual_packet.v1", "design": design_ref,
            "captures": images, "presentations": presentations,
            "instructions": "Inspect all raw images/sequences first. Record what they communicate, what may be missed/misread, and unknowns. Seal ui_visual_first_pass.v1 with your actual context/role before requesting full Factory context. Do not open the design locator before sealing. A still cannot prove discoverability, timing, interaction or human comprehension. Then review the whole exact design; this packet is not gameplay blind evidence."}


def comparison_bundles(roots, before, after):
    bundles = [capture(roots, read_json(game_file(roots, ref))) if ref is not None else None for ref in (before, after)]
    if all(bundles):
        for key in ("state_id", "surface_id", "locale", "viewport"):
            if bundles[0][key] != bundles[1][key]:
                fail("UI_COMPARISON_MISMATCH", f"before/after differ in {key}")
        times = [[frame["time_ms"] - bundle["frames"][0]["time_ms"] for frame in bundle["frames"]] for bundle in bundles]
        if times[0] != times[1]:
            fail("UI_COMPARISON_MISMATCH", "visual choices need the same sampled time window")
    return bundles


def render_media(roots, bundles, directory, identity):
    """Make a labelled contact sheet and timed GIF; retain original images unchanged."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        fail("UI_MEDIA_DEPENDENCY_REQUIRED", "install ui/requirements-visual.txt to render contact sheets/GIFs")
    if sum(bundle["viewport"][0] * bundle["viewport"][1] * len(bundle["frames"]) for bundle in bundles if bundle) > 64_000_000:
        fail("UI_MEDIA_BUDGET_REQUIRED", "select a bounded comparison window (at most 64 million input pixels); originals remain preserved")
    outputs = []
    loaded = []
    for label, bundle in zip(("BEFORE", "AFTER"), bundles):
        if bundle is None:
            continue
        frames = []
        for frame in bundle["frames"]:
            with Image.open(game_file(roots, frame["image"])) as original:
                frames.append(original.convert("RGB"))
        loaded.append((label, frames[0]))
        if len(frames) > 1:
            durations = [max(1, round(after["time_ms"] - before["time_ms"])) for before, after in zip(bundle["frames"], bundle["frames"][1:])]
            durations.append(durations[-1])
            target = confined(roots["game"], f"{directory}/{identity}-{label.lower()}.gif")
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as handle:
                frames[0].save(handle, format="GIF", save_all=True, append_images=frames[1:], duration=durations, loop=0)
            outputs.append(reference(roots["game"], target.relative_to(roots["game"]).as_posix()))
    if loaded:
        canvas = Image.new("RGB", (sum(frame.width for _, frame in loaded), 28 + max(frame.height for _, frame in loaded)), "white")
        draw = ImageDraw.Draw(canvas)
        left = 0
        for label, frame in loaded:
            draw.text((left + 4, 6), label + " (original pixel size)", fill="black")
            canvas.paste(frame, (left, 28))
            left += frame.width
        target = confined(roots["game"], f"{directory}/{identity}-comparison.png")
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as handle:
            canvas.save(handle, format="PNG")
        outputs.append(reference(roots["game"], target.relative_to(roots["game"]).as_posix()))
    return outputs


def decision_view(roots, design_ref, design, *, output=None, media_directory=None):
    """Project exact reviewed text and matched captures, never issue another approval."""
    from factory_core.context import context
    from factory_core.state import latest
    records = []
    for directory in sorted((roots["game"] / "design/factory/checkpoints").glob("*")):
        if directory.is_dir():
            record, _ = latest(roots["game"], directory.name)
            if record and record.get("design") == design_ref:
                records.append(record)
    if len(records) != 1:
        fail("REVIEW_REQUIRED", "one current reviewed checkpoint must select this design")
    record = records[0]
    checked = context(roots, capability="ui", task=design["task"], task_id=record["task_id"], role="human", design=design_ref)
    value = contract(roots, design)
    if value is None:
        fail("UI_EXPERIENCE_REQUIRED", "visual index requires a reviewed experience contract")
    base = confined(roots["game"], output).parent if output else roots["game"]
    def url(ref):
        return html.escape(quote(os.path.relpath(game_file(roots, ref), base), safe="/"), quote=True)
    cards, media = [], []
    for index, view in enumerate(value["visual_decisions"]):
        bundles = comparison_bundles(roots, view["before"], view["after"])
        images = []
        for label, bundle in zip(("Before", "After"), bundles):
            if bundle is None:
                images.append(f"<figure>{label}: unavailable; no baseline is implied.</figure>")
            else:
                origin = html.escape(bundle["origin"])
                images.append(f'<figure><figcaption>{label} — {origin}</figcaption><a href="{url(bundle["frames"][0]["image"])}"><img src="{url(bundle["frames"][0]["image"])}" alt="{label} capture"></a></figure>')
        if media_directory:
            media.extend(render_media(roots, bundles, media_directory, f"decision-{index + 1}"))
        cards.append(f'<details class="decision" {"open" if index == 0 else ""}><summary>{html.escape(view["decision_id"])} — {html.escape(view["excerpt"])}</summary><p>Consequence: {html.escape(view["consequence"])}</p><p>Risk / unknown: {html.escape(view["risk"])}</p><div class="pair">{"".join(images)}</div></details>')
    page = '<!doctype html><meta charset="utf-8"><title>UI decision entry</title><style>body{font:16px system-ui;max-width:1100px;margin:2rem auto;color:#202020}main{display:block}.decision{margin:.8rem 0;padding:.6rem;border-bottom:1px solid #ddd}.pair{display:flex;gap:1rem}figure{margin:0;flex:1}img{max-width:100%;max-height:360px;object-fit:contain}pre{white-space:pre-wrap}details{margin-top:2rem}summary{cursor:pointer}h2{font-size:1.1rem}</style>'
    page += '<h1>UI decision entry</h1><p>Exact reviewed projection, not a new specification. Previews are not runtime proof. Open the full checked view before ruling.</p>'
    page += f'<p>{len(cards)} decisions · <a href="#complete">Full checked design and exact action</a></p><main>{"".join(cards)}</main>'
    page += f'<details id="complete"><summary>Full checked human view — no omitted decisions</summary><pre>{html.escape(json.dumps(checked, ensure_ascii=False, indent=2))}</pre></details>'
    if media:
        page += '<h2>Matched sequences and comparison sheets</h2>' + ''.join(f'<p><a href="{url(ref)}">{html.escape(Path(ref["path"]).name)}</a></p>' for ref in media)
    return {"status": "UI_DECISION_VIEW", "html": page, "full_view": checked, "media": media, "authority": False}


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("capture-build", "capture", "evaluate", "review-packet", "decision-view"))
    parser.add_argument("--game-repo", required=True)
    parser.add_argument("--design")
    parser.add_argument("--contract", help="standalone contract; archival audit only")
    parser.add_argument("--archive", action="store_true")
    parser.add_argument("--captures", nargs="*", default=[])
    parser.add_argument("--raw", help="game-relative Godot exporter JSON")
    parser.add_argument("--sources", nargs="+", help="complete consumed game-source inventory, before running Godot")
    parser.add_argument("--entrypoint", help="actual isolated runner source path")
    parser.add_argument("--output", help="new game-relative output; fails if it exists")
    parser.add_argument("--media-directory", help="new game-relative contact-sheet/GIF outputs")
    args = parser.parse_args(argv)
    try:
        from ui.ui_design import _roots
        roots = _roots(args.game_repo)
        if args.output and confined(roots["game"], args.output).exists():
            fail("CONCURRENT_WRITE", "output already exists; publish a new immutable artifact")
        if args.media_directory and confined(roots["game"], args.media_directory).exists():
            fail("CONCURRENT_WRITE", "media directory already exists; select a new run")
        if args.command == "capture-build":
            if not args.sources or not args.entrypoint:
                fail("INVALID_UI_COMMAND", "capture-build needs --sources and --entrypoint")
            result = build_manifest(roots, args.sources, args.entrypoint)
        elif args.command == "capture":
            if not args.raw or args.design or args.contract or args.archive:
                fail("INVALID_UI_COMMAND", "capture needs --raw, without a design or archive override")
            result = seal_capture(roots, read_json(confined(roots["game"], args.raw)))
        else:
            if args.archive:
                if args.command != "evaluate" or not args.contract or args.design:
                    fail("INVALID_UI_COMMAND", "archival audit needs --contract, not a live design")
                value = read_json(confined(roots["game"], args.contract))
            else:
                if not args.design or args.contract:
                    fail("INVALID_UI_COMMAND", "current operation needs --design")
                from factory_core.state import load_design
                design_ref = reference(roots["game"], args.design)
                design = load_design(roots, design_ref)
                value = contract(roots, design)
            if args.command == "evaluate":
                if value is None:
                    fail("UI_EXPERIENCE_REQUIRED", "no experience contract")
                result = evaluate(roots, value, [reference(roots["game"], path) for path in args.captures], archival=args.archive)
            elif args.command == "review-packet":
                result = visual_packet(roots, design_ref, design)
            else:
                result = decision_view(roots, design_ref, design, output=args.output, media_directory=args.media_directory)
        if args.output:
            target = confined(roots["game"], args.output)
            if args.command == "decision-view":
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("x", encoding="utf-8") as handle:
                    handle.write(result["html"])
            else:
                exclusive_json(target, result)
            print(json.dumps({"status": result.get("status", "UI_CAPTURE_BUILD_PREPARED" if args.command == "capture-build" else "UI_CAPTURE_SEALED"), "output": reference(roots["game"], args.output)}))
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return int(result.get("status") == "UI_MEASUREMENTS_BLOCKED")
    except (FactoryError, OSError) as error:
        print(json.dumps({"status": "BLOCKED", "code": getattr(error, "code", "UI_IO_ERROR"), "message": str(error)}))
        return 1
