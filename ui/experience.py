"""UI experience contracts and measured guardrails, not a player-quality oracle.

All reports are recomputed from hashed capture inputs. Geometry/style annotations
are observations supplied by an exporter, not proof that the semantic labels or
pixels are right. Visual review and unprompted comprehension remain separate.
"""
from __future__ import annotations

import math
import re
import struct
import subprocess
import zlib
from pathlib import Path

from factory_core.refs import (confined, digest, fail, read_json, reference,
                               resolve_ref, sha)

SCHEMA = Path(__file__).parent / "schemas/ui_experience.schema.json"
KINDS = ("PAIRING", "ZONE", "COLOR", "PRIMARY", "REDUNDANCY", "DENSITY", "GOAL")


def shape(value, name):
    """Validate our closed, deliberately small JSON-schema vocabulary, stdlib only.

    Unsupported schema keywords fail rather than silently weakening validation.
    This is not a general-purpose JSON Schema implementation.
    """
    schema = read_json(SCHEMA)

    def check(item, rule, where):
        allowed = {"$schema", "$defs", "$ref", "title", "description", "type", "const", "enum",
                   "properties", "required", "additionalProperties", "items", "minItems", "maxItems",
                   "uniqueItems", "minLength", "maxLength", "pattern", "minimum", "maximum", "anyOf"}
        if set(rule) - allowed:
            fail("INVALID_UI_SCHEMA", f"unsupported keywords: {set(rule) - allowed}")
        if "$ref" in rule:
            ref = rule["$ref"]
            if not ref.startswith("#/$defs/"):
                fail("INVALID_UI_SCHEMA", "only local definitions are supported")
            return check(item, schema["$defs"][ref.split("/")[-1]], where)
        if "anyOf" in rule:
            from factory_core.refs import FactoryError
            for option in rule["anyOf"]:
                try:
                    check(item, option, where)
                    return
                except FactoryError as error:
                    if error.code != "INVALID_UI_EXPERIENCE":
                        raise
            fail("INVALID_UI_EXPERIENCE", f"{where}: no matching shape")
        numeric = isinstance(item, (int, float)) and not isinstance(item, bool) and math.isfinite(item)
        types = {"object": isinstance(item, dict), "array": isinstance(item, list),
                 "string": isinstance(item, str), "boolean": isinstance(item, bool),
                 "number": numeric, "integer": numeric and isinstance(item, int), "null": item is None}
        if "type" in rule and not types[rule["type"]]:
            fail("INVALID_UI_EXPERIENCE", f"{where}: expected {rule['type']}")
        if "const" in rule and item != rule["const"] or "enum" in rule and item not in rule["enum"]:
            fail("INVALID_UI_EXPERIENCE", f"{where}: unexpected value {item!r}")
        if isinstance(item, dict):
            props = rule.get("properties", {})
            if set(rule.get("required", [])) - set(item):
                fail("INVALID_UI_EXPERIENCE", f"{where}: missing fields")
            for key, child in item.items():
                if key in props:
                    check(child, props[key], f"{where}.{key}")
                elif rule.get("additionalProperties") is False:
                    fail("INVALID_UI_EXPERIENCE", f"{where}: unexpected field {key}")
                elif isinstance(rule.get("additionalProperties"), dict):
                    check(child, rule["additionalProperties"], f"{where}.{key}")
        if isinstance(item, list):
            if len(item) < rule.get("minItems", 0) or len(item) > rule.get("maxItems", math.inf):
                fail("INVALID_UI_EXPERIENCE", f"{where}: invalid list length")
            if rule.get("uniqueItems") and len({digest(child) for child in item}) != len(item):
                fail("INVALID_UI_EXPERIENCE", f"{where}: duplicate items")
            for index, child in enumerate(item):
                if "items" in rule:
                    check(child, rule["items"], f"{where}[{index}]")
        if isinstance(item, str):
            if len(item.strip()) < rule.get("minLength", 0) or len(item) > rule.get("maxLength", math.inf) or "pattern" in rule and not re.search(rule["pattern"], item):
                fail("INVALID_UI_EXPERIENCE", f"{where}: invalid text")
        if numeric and (item < rule.get("minimum", -math.inf) or item > rule.get("maximum", math.inf)):
            fail("INVALID_UI_EXPERIENCE", f"{where}: number outside bounds")

    check(value, schema["$defs"][name], name)
    return value


def indexed(rows, key):
    result = {row[key]: row for row in rows}
    if len(result) != len(rows):
        fail("INVALID_UI_EXPERIENCE", f"duplicate {key}")
    return result


def game_file(roots, ref):
    if not isinstance(ref, dict) or ref.get("scope") not in ("game", "game_git"):
        fail("INVALID_UI_EXPERIENCE", "game-owned evidence required")
    return resolve_ref(roots, ref)


def contract(roots, design):
    """Load the optional relation layer; legacy designs remain readable."""
    ref = design.get("ui", {}).get("experience")
    if ref is None:
        return None
    if ref not in design["artifacts"]:
        fail("INVALID_UI_EXPERIENCE", "ui.experience must be a sealed design artifact")
    value = shape(read_json(game_file(roots, ref)), "contract")
    from ui.ui_design import load_artifacts, contract_ids
    parts = load_artifacts(roots, design)
    facts = indexed(parts["information_model"]["facts"], "fact_id")
    _, steps = contract_ids(read_json(game_file(roots, parts["information_model"]["interaction_contract"])))
    screens = {screen["surface_id"] for screen in parts["screen_contracts"]["surfaces"]}
    scenarios = indexed(value["scenarios"], "scenario_id")
    for scenario in scenarios.values():
        if scenario["surface_id"] not in screens or not set(scenario["step_ids"]) <= steps:
            fail("UI_COVERAGE", "scenario must name existing surfaces and interaction steps")
    checks = indexed(value["checks"], "check_id")
    for check in checks.values():
        shape(check["parameters"], check["kind"].lower())
        if not set(check["scenario_ids"]) <= set(scenarios):
            fail("UI_COVERAGE", "check names unknown scenario")
        params = check["parameters"]
        needed = ([params["fact_id"]] if check["kind"] == "REDUNDANCY" else
                  [params[key]["fact_id"] for key in ("current", "threshold", "reward")] if check["kind"] == "GOAL" else [])
        if any(fact not in facts or facts[fact]["need"] == "FORBIDDEN" for fact in needed):
            fail("UI_COVERAGE", "semantic check must use existing, non-forbidden facts")
    kinds = {check["kind"] for check in checks.values()}
    if set(value["not_applicable"]) != set(KINDS) - kinds:
        fail("UI_COVERAGE", "each semantic domain needs a check or reviewed not-applicable reason")
    probes = indexed(value["probes"], "probe_id")
    chains = {chain["chain_id"] for chain in parts["verification_plan"]["blind_chains"]}
    for probe in probes.values():
        if not set(probe["scenario_ids"]) <= set(scenarios) or probe["chain_id"] not in chains:
            fail("UI_COVERAGE", "probe must bind known scenarios and blind chain")
        if any(fact not in facts or facts[fact]["need"] == "FORBIDDEN" for fact in probe["fact_ids"]):
            fail("UI_COVERAGE", "probe needs existing non-forbidden facts")
    if {probe["chain_id"] for probe in probes.values()} != chains:
        fail("UI_COVERAGE", "all existing verification-plan blind chains need internal probes")
    for chain in parts["verification_plan"]["blind_chains"]:
        covered = {fact for probe in probes.values() if probe["chain_id"] == chain["chain_id"] for fact in probe["fact_ids"]}
        if set(chain["must_know_fact_ids"]) - covered:
            fail("UI_COVERAGE", "probe fact assignments must cover each existing blind chain")
    # Required understanding must never be assigned only to a future human in beta.
    required_facts = {fact for probe in probes.values() for fact in probe["fact_ids"]}
    if {key for key, fact in facts.items() if fact["need"] == "MUST_KNOW"} - required_facts:
        fail("UI_COVERAGE", "every MUST_KNOW fact needs an internal unprompted probe")
    if any(not any(sid in probe["scenario_ids"] for probe in probes.values()) for sid in scenarios):
        fail("UI_COVERAGE", "every scenario needs an outcome probe, not just geometric checks")
    if value["receipt_path"] not in design["production_scope"]:
        fail("INVALID_UI_EXPERIENCE", "readiness receipt must be an authorized production output")
    views = indexed(value["visual_decisions"], "decision_id")
    decisions = indexed(design["decisions"], "id")
    if set(views) != set(decisions):
        fail("UI_COVERAGE", "visual index must cover the complete decision surface")
    for identity, view in views.items():
        decision = decisions[identity]
        if view["excerpt"] not in decision["excerpt"] or view["consequence"] not in decision["consequence"]:
            fail("INVALID_UI_EXPERIENCE", "index text must be exact excerpts, never another spec")
        for key in ("before", "after"):
            if view[key] is not None and view[key] not in value["design_captures"]:
                fail("UI_COVERAGE", "visual comparison must cite sealed design captures")
    sealed = design["inputs"] + design["artifacts"]
    for ref in value["design_captures"] + value["feedback_inputs"]:
        if ref not in sealed:
            fail("INVALID_UI_EXPERIENCE", "captures and prior feedback must join the sealed input closure")
        game_file(roots, ref)
    genre(value["genre"], roots["factory"])
    for ref in value["design_captures"]:
        capture(roots, read_json(game_file(roots, ref)))
    return value


def genre(value, factory):
    shape(value, "genre")
    if value["profile"] == "NONE":
        if not value["reason"] or value["items"]:
            fail("UI_COVERAGE", "NONE needs a reason and no invented profile entries")
        return
    profile = read_json(confined(factory, f"ui/profiles/{value['profile']}.json"))
    entries = indexed(value["items"], "item_id")
    if set(entries) != {item["item_id"] for item in profile["items"]}:
        fail("UI_COVERAGE", "genre expectation inventory is incomplete")
    # Gaps are explicit work for their owner, not permission for UI to add rules.
    if any(item["disposition"] in ("GAP", "UPSTREAM_REQUIRED") for item in entries.values()):
        fail("UI_GENRE_GAP", "resolve or justify genre gaps through the owning design before freeze")


def capture(roots, value):
    shape(value, "capture")
    commit = subprocess.run(["git", "-C", str(roots["game"]), "cat-file", "-e", value["game_revision"] + "^{commit}"], capture_output=True, timeout=10)
    if commit.returncode:
        fail("INVALID_UI_CAPTURE", "game_revision must identify an available immutable game commit")
    build = shape(read_json(game_file(roots, value["build_artifact"])), "build_manifest")
    tree = subprocess.run(["git", "-C", str(roots["game"]), "rev-parse", value["game_revision"] + "^{tree}"], capture_output=True, text=True, timeout=10)
    if build["game_revision"] != value["game_revision"] or build["git_tree"] != tree.stdout.strip():
        fail("INVALID_UI_CAPTURE", "source manifest must identify the exact available game revision/tree")
    sources = indexed(build["sources"], "path")
    if "project.godot" not in sources or build["entrypoint"] not in sources:
        fail("INVALID_UI_CAPTURE", "Godot build manifest must include project.godot and its actual entrypoint")
    if not build["entrypoint"].endswith((".gd", ".tscn")):
        fail("INVALID_UI_CAPTURE", "Godot entrypoint must be a pinned runner script or scene")
    for source in sources.values():
        if source.get("scope") != "game_git" or source.get("revision") != value["game_revision"]:
            fail("INVALID_UI_CAPTURE", "consumed source files must pin the build revision")
        game_file(roots, source)
    if build["binary"] is not None:
        game_file(roots, build["binary"])
    if value["build_id"] != value["build_artifact"]["sha256"]:
        fail("INVALID_UI_CAPTURE", "build identity must equal the hashed build artifact")
    resolve_ref(roots, value["exporter"])
    indexed(value["frames"], "frame_id")
    previous = -1
    for frame in value["frames"]:
        if frame["time_ms"] <= previous:
            fail("INVALID_UI_CAPTURE", "frames must be strictly time ordered")
        previous = frame["time_ms"]
        indexed(frame["elements"], "element_id")
        raw = game_file(roots, frame["image"]).read_bytes()
        validate_png(raw, value["viewport"])
    return value


def validate_png(raw, viewport):
    """Check complete noninterlaced 8-bit PNG pixels, not just a forged header."""
    if len(raw) < 24 or raw[:8] != b"\x89PNG\r\n\x1a\n" or list(struct.unpack(">II", raw[16:24])) != viewport:
        fail("INVALID_UI_CAPTURE", "PNG dimensions must match the declared viewport")
    position, compressed, header, ended = 8, bytearray(), None, False
    while position + 12 <= len(raw):
        size = struct.unpack(">I", raw[position:position + 4])[0]
        kind = raw[position + 4:position + 8]
        data = raw[position + 8:position + 8 + size]
        end = position + 12 + size
        if end > len(raw) or zlib.crc32(kind + data) != struct.unpack(">I", raw[end - 4:end])[0]:
            fail("INVALID_UI_CAPTURE", "truncated/corrupt PNG chunk")
        if kind == b"IHDR":
            if header is not None or position != 8 or size != 13:
                fail("INVALID_UI_CAPTURE", "invalid PNG header")
            header = struct.unpack(">IIBBBBB", data)
        elif kind == b"IDAT":
            compressed.extend(data)
        elif kind == b"IEND":
            ended = size == 0 and end == len(raw)
            break
        position = end
    if not ended or header is None:
        fail("INVALID_UI_CAPTURE", "PNG is incomplete")
    width, height, depth, color, compression, filtering, interlace = header
    channels = {0: 1, 2: 3, 4: 2, 6: 4}.get(color)
    if depth != 8 or channels is None or compression or filtering or interlace:
        fail("INVALID_UI_CAPTURE", "capture needs complete noninterlaced 8-bit grayscale/RGB/RGBA PNG")
    stride = width * channels + 1
    expected = height * stride
    try:
        decoder = zlib.decompressobj()
        pixels = decoder.decompress(compressed, expected + 1)
    except zlib.error:
        fail("INVALID_UI_CAPTURE", "invalid compressed PNG pixels")
    if len(pixels) != expected or not decoder.eof or decoder.unused_data or any(pixels[offset] > 4 for offset in range(0, expected, stride)):
        fail("INVALID_UI_CAPTURE", "incomplete/invalid PNG pixels")


def visible(element, viewport):
    if element is None or not element["visible"]:
        return False
    x, y, width, height = element["bounds"]
    return width > 0 and height > 0 and x >= 0 and y >= 0 and x + width <= viewport[0] and y + height <= viewport[1]


def contains(outer, inner):
    x, y, width, height = outer
    left, top, wide, high = inner
    return x <= left and y <= top and left + wide <= x + width and top + high <= y + height


def crosses(first, second):
    def orientation(left, middle, right):
        return (middle[0] - left[0]) * (right[1] - left[1]) - (middle[1] - left[1]) * (right[0] - left[0])
    left, right = first
    start, end = second
    return orientation(left, right, start) * orientation(left, right, end) < 0 and orientation(start, end, left) * orientation(start, end, right) < 0


def frame_result(check, frame, viewport):
    """Return measured status and reason; no inferred semantics from missing data."""
    elements = indexed(frame["elements"], "element_id")
    params, kind = check["parameters"], check["kind"]

    def get(identity):
        if identity not in elements:
            raise LookupError(identity)
        return elements[identity]

    def on_screen(identity):
        return visible(get(identity), viewport)

    try:
        if kind == "PAIRING":
            pairs = [(get(pair["value"]), get(pair["attribute"])) for pair in params["pairs"]]
            valid = all(visible(value, viewport) and visible(attribute, viewport) for value, attribute in pairs)
            if params["layout"] == "SAME_ROW":
                valid = valid and all(abs((a["bounds"][1] + a["bounds"][3] / 2) - (b["bounds"][1] + b["bounds"][3] / 2)) <= params["tolerance_px"] for a, b in pairs)
            else:
                group = get(params["group_element"])
                valid = valid and all(contains(group["bounds"], item["bounds"]) for pair in pairs for item in pair)
        elif kind == "ZONE":
            zone, item = get(params["zone_element"]), get(params["element_id"])
            valid = visible(item, viewport) and contains(zone["bounds"], item["bounds"])
        elif kind == "COLOR":
            valid = True
            for identity, role in params["element_roles"].items():
                item = get(identity)
                if not item["visible"]:
                    continue
                if item["color"] is None:
                    raise LookupError(f"{identity}.effective draw color")
                for reserved in params["reserved"]:
                    distance = max(abs(a - b) for a, b in zip(item["color"], reserved["color"]))
                    if distance <= params["tolerance"] and role != reserved["role"]:
                        valid = False
        elif kind == "PRIMARY":
            item = get(params["element_id"])
            x, y, width, height = item["bounds"]
            actual = [(x + width / 2) / viewport[0], (y + height / 2) / viewport[1]]
            valid = on_screen(params["element_id"]) and item["enabled"] and max(abs(a - b) for a, b in zip(actual, params["anchor"])) <= params["tolerance"]
        elif kind == "REDUNDANCY":
            canonical = get(params["canonical_element"])
            if params["fact_id"] not in canonical["fact_ids"]:
                raise LookupError("canonical fact binding")
            copies = [item for item in elements.values() if params["fact_id"] in item["fact_ids"] and visible(item, viewport)]
            valid = visible(canonical, viewport) and (len(copies) <= 1 or bool(params["repeat_reason"]))
        elif kind == "GOAL":
            valid = True
            for key in ("current", "threshold", "reward"):
                binding = params[key]
                item = get(binding["element_id"])
                if binding["fact_id"] not in item["fact_ids"]:
                    raise LookupError(f"{key}.fact binding")
                valid = valid and visible(item, viewport)
        else:  # DENSITY: bounded counts and geometric crossings, not readability.
            if not frame["overlays_complete"]:
                raise LookupError("complete overlay inventory")
            lines = [item for item in elements.values() if item["overlay_group"] == params["overlay_group"] and item["visible"]]
            if any(len(item["points"]) < 2 for item in lines):
                raise LookupError("overlay paths")
            segments = [(item["element_id"], (start, end)) for item in lines for start, end in zip(item["points"], item["points"][1:])]
            crossing_count = sum(crosses(first[1], second[1]) for index, first in enumerate(segments) for second in segments[index + 1:])
            valid = len(lines) <= params["max_concurrent"] and crossing_count <= params["max_crossings"]
        return ("PASS" if valid else "FAIL"), f"{kind}: measured frame {frame['frame_id']}"
    except LookupError as error:
        return "UNVERIFIABLE", f"missing runtime observation: {error}"


def evaluate(roots, value, capture_refs, *, archival=False):
    """Recompute checks over every supplied frame and require every declared scenario."""
    shape(value, "contract")
    scenarios = indexed(value["scenarios"], "scenario_id")
    indexed(value["checks"], "check_id")
    bundles = {}
    for ref in capture_refs:
        bundle = capture(roots, read_json(game_file(roots, ref)))
        sid = bundle["scenario_id"]
        if sid in bundles or sid not in scenarios:
            fail("INVALID_UI_CAPTURE", "one bundle per known scenario required")
        scenario = scenarios[sid]
        for key in ("state_id", "surface_id", "locale", "viewport"):
            if scenario[key] != bundle[key]:
                fail("INVALID_UI_CAPTURE", f"scenario {sid} mismatches {key}")
        bundles[sid] = bundle
    results = []
    for check in value["checks"]:
        shape(check["parameters"], check["kind"].lower())
        for sid in check["scenario_ids"]:
            bundle = bundles.get(sid)
            if bundle is None or not archival and bundle["origin"] != "RUNTIME":
                rows = [("UNVERIFIABLE", "missing exact runtime capture")]
            else:
                rows = [frame_result(check, frame, bundle["viewport"]) for frame in bundle["frames"]]
            status = "FAIL" if any(row[0] == "FAIL" for row in rows) else "UNVERIFIABLE" if any(row[0] == "UNVERIFIABLE" for row in rows) else "PASS"
            results.append({"check_id": check["check_id"], "scenario_id": sid, "status": status,
                            "observations": [reason for _, reason in rows]})
    complete = set(bundles) == set(scenarios) and (archival or all(bundle["origin"] == "RUNTIME" for bundle in bundles.values())) and all(row["status"] == "PASS" for row in results)
    return {"schema_version": "ui_experience_report.v1", "status": "UI_RETROSPECTIVE_AUDIT" if archival else "UI_MEASUREMENTS_PASS" if complete else "UI_MEASUREMENTS_BLOCKED",
            "contract_sha256": digest(value), "captures": capture_refs, "results": results,
            "missing_scenarios": sorted(set(scenarios) - set(bundles)),
            "authority": False, "comprehension_proven": False}
