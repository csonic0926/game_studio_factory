"""Editable vector/raster production, separate from generative image providers.

craft_asset_workflow_v1: a fresh private editor session, an explicit recipe,
native-source round trip, exports, and engineering (not creative) validation.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile
import xml.etree.ElementTree as ET

from PIL import Image

from .craft_client import CraftClient, CraftError, EDITORS


SCHEMA = "craft_asset_workflow_v1"
FACTORY_ROOT = Path(__file__).resolve().parents[2]
SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,95}\Z")
SAFE_FILE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")
RASTER_FORMATS = {".png": "PNG", ".jpg": "JPEG", ".webp": "WEBP"}


def _json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _object(value, label: str, keys: set[str] | None = None) -> dict:
    if not isinstance(value, dict):
        raise CraftError(f"{label} must be an object")
    if keys is not None and set(value) - keys:
        raise CraftError(f"Unknown {label} fields: {sorted(set(value) - keys)}")
    return value


def _size(value, label: str) -> None:
    if type(value) is not int or not 1 <= value <= 16384:
        raise CraftError(f"{label} must be an integer from 1 to 16384")


def _resolve(value, base: Path, label: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise CraftError(f"{label} must be a nonempty path")
    path = Path(value).expanduser()
    return (path if path.is_absolute() else base / path).resolve()


def load_craft_spec(spec_path: Path, *, out: Path | None = None) -> tuple[dict, Path]:
    spec_path = spec_path.expanduser().resolve()
    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        # Reject NaN/Infinity even inside editor-native params.
        json.dumps(spec, allow_nan=False)
    except (ValueError, OSError) as error:
        raise CraftError(f"Cannot read craft spec: {error}") from error
    _object(spec, "spec", {"schema_version", "run_id", "output_root", "editor", "inputs",
                           "document", "steps", "exports"})
    if spec.get("schema_version") != SCHEMA:
        raise CraftError(f"schema_version must be {SCHEMA}")
    if not isinstance(spec.get("run_id"), str) or not SAFE_ID.fullmatch(spec["run_id"]):
        raise CraftError("run_id must be a safe single-component identifier")
    if not isinstance(spec.get("editor"), str) or spec["editor"] not in EDITORS:
        raise CraftError("editor must be vectorcraft or photocraft (not an image provider)")
    output_root = _resolve(spec.get("output_root"), spec_path.parent, "output_root")
    run_root = out.expanduser().resolve() if out is not None else output_root / spec["run_id"]
    if run_root == FACTORY_ROOT or FACTORY_ROOT in run_root.parents:
        raise CraftError("Craft outputs belong in the target game repo (or temporary test storage), not the Factory checkout")
    inputs = _object(spec.setdefault("inputs", {}), "inputs")
    input_names = set()
    for key, value in inputs.items():
        if not SAFE_ID.fullmatch(key) or key.lower() in input_names:
            raise CraftError(f"Invalid or case-colliding input id: {key}")
        input_names.add(key.lower())
        path = _resolve(value, spec_path.parent, f"inputs.{key}")
        if not path.is_file():
            raise CraftError(f"Input is not a file: {path}")
        inputs[key] = str(path)
    document = _object(spec.get("document"), "document", {"new", "input"})
    if len(document) != 1:
        raise CraftError("document must have exactly one of new or input")
    if "new" in document:
        new = _object(document["new"], "document.new")
        for field in ("width", "height"):
            _size(new.get(field), f"document.new.{field}")
    elif not isinstance(document["input"], str) or document["input"] not in inputs:
        raise CraftError("document.input must name an entry in inputs")
    if not isinstance(spec.get("steps"), list):
        raise CraftError("steps must be a list (empty is allowed for conversion)")
    for i, step in enumerate(spec["steps"]):
        _object(step, f"steps[{i}]", {"command", "params"})
        if not isinstance(step.get("command"), str) or not step["command"].strip():
            raise CraftError(f"steps[{i}].command must be a command id from craft-commands")
        _object(step.setdefault("params", {}), f"steps[{i}].params")
    exports = spec.get("exports")
    if not isinstance(exports, list) or not exports:
        raise CraftError("exports must be a nonempty list including at least one PNG")
    names = set()
    for i, export in enumerate(exports):
        _object(export, f"exports[{i}]", {"name", "width", "height", "alpha", "params"})
        name = export.get("name")
        if not isinstance(name, str) or not SAFE_FILE.fullmatch(name) or name.lower() in names:
            raise CraftError("Export names must be unique safe filenames, without directories")
        names.add(name.lower())
        suffix = Path(name).suffix
        allowed = set(RASTER_FORMATS) | ({".svg"} if spec["editor"] == "vectorcraft" else set())
        if suffix not in allowed:
            raise CraftError(f"Unsupported {spec['editor']} export: {name}; choose {sorted(allowed)}")
        params = _object(export.setdefault("params", {}), f"exports[{i}].params")
        if set(params) & {"path", "format", "index", "range"}:
            raise CraftError("Export params may not override path/format/document index or request a multi-file range")
        if suffix in RASTER_FORMATS:
            for field in ("width", "height"):
                _size(export.get(field), f"exports[{i}].{field}")
            alpha = export.setdefault("alpha", "any")
            if alpha not in ("any", "transparent", "opaque"):
                raise CraftError("alpha must be any, transparent, or opaque")
            if suffix == ".jpg" and alpha == "transparent":
                raise CraftError("JPEG cannot preserve transparency; use PNG or WebP")
        elif set(export) & {"width", "height", "alpha"}:
            raise CraftError("SVG size/alpha assertions belong on its companion PNG export")
    if not any(Path(e["name"]).suffix == ".png" for e in exports):
        raise CraftError("Include a PNG export for visual review and raster validation")
    spec["output_root"] = str(output_root)
    return spec, run_root


def _references(value, inputs: dict, results: list):
    """Exact JSON string references, never shell/text interpolation."""
    if isinstance(value, list):
        return [_references(v, inputs, results) for v in value]
    if isinstance(value, dict):
        return {k: _references(v, inputs, results) for k, v in value.items()}
    if isinstance(value, str):
        if value.startswith("$input."):
            try:
                return inputs[value[7:]]
            except KeyError:
                raise CraftError(f"Unknown input reference: {value}") from None
        if value.startswith("$step."):
            parts = value[6:].split(".")
            try:
                if not parts[0].isdigit():
                    raise KeyError(parts[0])
                result = results[int(parts[0])]
                for part in parts[1:]:
                    result = result[int(part)] if isinstance(result, list) and part.isdigit() else result[part]
                return result
            except (IndexError, KeyError, TypeError):
                raise CraftError(f"Unknown/forward step result reference: {value}") from None
    return value


def _file(path: Path, root: Path) -> dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size == 0 or root.resolve() not in path.resolve().parents:
        raise CraftError(f"Missing, empty or escaped artifact: {path}")
    return {"bytes": path.stat().st_size, "sha256": _sha(path)}


def validate_export(path: Path, export: dict, root: Path) -> dict:
    record = {"name": path.name, **_file(path, root)}
    if path.suffix == ".svg":
        try:
            node = ET.parse(path).getroot()
        except ET.ParseError as error:
            raise CraftError(f"Invalid SVG: {path.name}: {error}") from error
        if node.tag != "{http://www.w3.org/2000/svg}svg":
            raise CraftError(f"Not an SVG document: {path.name}")
        record.update(format="SVG", viewBox=node.get("viewBox"))
        return record
    try:
        with Image.open(path) as image:
            image.load()
            if image.format != RASTER_FORMATS[path.suffix]:
                raise CraftError(f"Format mismatch: {path.name} contains {image.format}")
            if image.size != (export["width"], export["height"]):
                raise CraftError(f"Canvas mismatch: {path.name} is {image.size}, expected {(export['width'], export['height'])}")
            rgba = image.convert("RGBA")
            alpha = rgba.getchannel("A")
            low, high = alpha.getextrema()
            if high == 0:
                raise CraftError(f"Empty (fully transparent) export: {path.name}")
            if export["alpha"] == "transparent" and low != 0:
                raise CraftError(f"No fully transparent background pixels: {path.name}")
            if export["alpha"] == "opaque" and low != 255:
                raise CraftError(f"Expected opaque pixels throughout: {path.name}")
            record.update(format=image.format, width=image.width, height=image.height,
                          alpha_extrema=[low, high], alpha_bbox=list(alpha.getbbox()))
    except (OSError, ValueError, Image.DecompressionBombError) as error:
        raise CraftError(f"Cannot decode export {path.name}: {error}") from error
    return record


def discover_commands(editor: str, *, query: str = "", cli: str | None = None, timeout: float = 120) -> dict:
    # Discovery does not need authority over any project or the global MCP session.
    with tempfile.TemporaryDirectory(prefix="asset-craft-discovery-") as directory:
        root = Path(directory)
        with CraftClient(editor, root, root / "work", root / "logs", cli=cli, timeout=timeout) as client:
            commands = client.tool("command_list", filter=query)
            return {"ok": True, "editor": editor, "server": client.server, "commands": commands}


def run_craft_assets(spec_path: Path, *, out: Path | None = None,
                     cli: str | None = None, timeout: float = 120) -> dict:
    spec, root = load_craft_spec(spec_path, out=out)
    try:
        root.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        raise CraftError(f"Run already exists (never overwritten): {root}; choose a new run_id or --out") from None
    stage = "prepare"
    status = {"ok": False, "schema_version": SCHEMA, "run_root": str(root),
              "editor": spec["editor"], "creative_acceptance": "not_assessed"}
    warnings = []
    try:
        for directory in ("request", "inputs", "work", "logs"):
            (root / directory).mkdir()
        _json(root / "request" / "spec.json", spec)
        _json(root / "artifact_status.json", {**status, "stage": stage})
        inputs, provenance = {}, {}
        for key, value in spec["inputs"].items():
            source = Path(value)
            target = root / "inputs" / (key + source.suffix)
            source_hash = _sha(source)
            shutil.copyfile(source, target)
            if _sha(target) != source_hash:
                raise CraftError(f"Input changed while staging: {source}")
            inputs[key] = str(target)
            provenance[key] = {"path": str(source), "sha256": source_hash,
                               "snapshot": str(target.relative_to(root))}
        _json(root / "request" / "inputs.json", provenance)
        stage = "editor"
        with CraftClient(spec["editor"], root, root / "work", root / "logs", cli=cli, timeout=timeout) as client:
            _json(root / "request" / "editor.json", {"cli": client.cli, "server": client.server})

            def call(name, **params):
                result = client.tool(name, **params)
                if isinstance(result, dict) and result.get("warnings"):
                    warnings.append({"operation": params.get("id", name), "warnings": result["warnings"]})
                return result

            def command(name, params):
                extra = {"wait": True} if spec["editor"] == "photocraft" else {}
                return call("command_run", id=name, params=params, **extra)

            vector = spec["editor"] == "vectorcraft"
            open_tool, save_tool = ("open_file", "save_file") if vector else ("doc_open", "doc_save")
            document = spec["document"]
            if "new" in document:
                if vector:
                    command("file.new", document["new"])
                else:
                    call("doc_new", **document["new"])
            else:
                call(open_tool, path=inputs[document["input"]])
            stage = "editing"
            results = []
            for i, step in enumerate(spec["steps"]):
                stage = f"editing:{i}"
                results.append(command(step["command"], _references(step["params"], inputs, results)))
            _json(root / "logs" / "step_results.json", results)
            _json(root / "logs" / "document.before_save.json", call("doc_inspect"))
            stage = "native_roundtrip"
            native = root / "work" / (spec["run_id"] + EDITORS[spec["editor"]])
            if native.exists() or native.is_symlink():
                raise CraftError(f"Recipe already wrote reserved native path: {native.name}")
            call(save_tool, path=str(native))
            native_record = _file(native, root / "work")
            # Export from the reopened native source, not just the in-memory edit.
            call(open_tool, path=str(native))
            _json(root / "logs" / "document.reopened.json", call("doc_inspect"))
            stage = "exporting"
            for export in spec["exports"]:
                path = root / "work" / export["name"]
                # Earlier recipe commands must not leave a stale apparent export.
                if path.exists() or path.is_symlink():
                    raise CraftError(f"Recipe already wrote reserved export path: {path.name}")
                call("export" if vector else "doc_export", path=str(path),
                     format=path.suffix[1:], **export["params"])
            editor_info = {"cli": client.cli, "server": client.server}
        stage = "validation"
        checked = [validate_export(root / "work" / e["name"], e, root / "work") for e in spec["exports"]]
        summary = {"ok": True, "scope": "file_format_canvas_alpha_and_native_reopen",
                   "creative_acceptance": "not_assessed", "review_required": True,
                   "downstream_validation_required": True, "warnings": warnings, "exports": checked}
        _json(root / "logs" / "validation_summary.json", summary)
        # Only promote a complete, technically validated set; partial output stays in work/.
        stage = "publishing"
        (root / "deliverables").mkdir()
        (root / "source").mkdir()
        shutil.copyfile(native, root / "source" / native.name)
        for export in spec["exports"]:
            shutil.copyfile(root / "work" / export["name"], root / "deliverables" / export["name"])
        native_record["path"] = f"source/{native.name}"
        manifest = {"schema_version": SCHEMA, "run_id": spec["run_id"], "editor": spec["editor"],
                    "editor_info": editor_info, "recipe_sha256": _sha(root / "request" / "spec.json"),
                    "inputs": provenance, "native_source": native_record,
                    "exports": [{**e, "path": f"deliverables/{e['name']}"} for e in checked],
                    "creative_acceptance": "not_assessed", "warnings": warnings}
        _json(root / "deliverables" / "craft_asset_manifest.json", manifest)
        _json(root / "deliverables" / "validation_summary.json", summary)
        preview = next(e["name"] for e in spec["exports"] if e["name"].endswith(".png"))
        status.update(ok=True, stage="complete", deliverables="deliverables/", native_source=native_record["path"],
                      preview=f"deliverables/{preview}", review_required=True, warnings=warnings)
        _json(root / "artifact_status.json", status)
        return status
    except (Exception, KeyboardInterrupt) as error:
        if stage == "validation":
            _json(root / "logs" / "validation_summary.json", {"ok": False, "error": str(error),
                  "creative_acceptance": "not_assessed", "warnings": warnings})
        _json(root / "artifact_status.json", {**status, "ok": False, "stage": "failed",
                                             "failed_stage": stage, "error": str(error), "warnings": warnings})
        if isinstance(error, KeyboardInterrupt):
            raise
        raise CraftError(f"{stage}: {error} (run: {root})") from error
