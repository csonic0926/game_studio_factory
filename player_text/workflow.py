"""Exact inventory and evidence checks; no program here judges prose or rewrites it."""
from __future__ import annotations

from collections import Counter
import csv
import io
import json
from pathlib import Path
import re

from factory_core.refs import confined, digest, fail, reference, resolve_ref, sha

FACTORY = Path(__file__).resolve().parents[1]
PRODUCERS = frozenset({"studio", "gameplay", "ui", "story", "asset", "sound"})
KINDS = frozenset({"dialogue", "narration", "description", "lore", "choice", "functional"})
PLACEHOLDERS = re.compile(r"\$?\{[\w.]+\}|%(?:\d+\$)?[-+#0 ]*\d*(?:\.\d+)?[sdifFeEgGouxX]")


def fields(value, required, optional=()):
    if not isinstance(value, dict) or set(required) - value.keys() or value.keys() - set(required) - set(optional):
        fail("INVALID_PLAYER_TEXT", f"expected fields {sorted(required)}; optional {sorted(optional)}")


def text(value):
    if not isinstance(value, str) or not value.strip():
        fail("INVALID_PLAYER_TEXT", "a nonempty string is required")
    return value


def strings(value, *, empty=False):
    if not isinstance(value, list) or (not value and not empty):
        fail("INVALID_PLAYER_TEXT", "a nonempty string list is required")
    for item in value:
        text(item)
    if len(value) != len(set(value)):
        fail("INVALID_PLAYER_TEXT", "duplicate list entry")
    return value


def read(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                fail("INVALID_PLAYER_TEXT", f"duplicate JSON key: {key}")
            result[key] = value
        return result
    return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=unique)


def project_root(value):
    root = Path(value).expanduser().resolve()
    if not root.is_dir() or root.is_relative_to(FACTORY) or FACTORY.is_relative_to(root):
        fail("INVALID_PROJECT", "pass the exact external project directory, not Factory or its parent")
    return root


def current_ref(root, ref):
    if not isinstance(ref, dict) or ref.get("scope") != "game":
        fail("INVALID_PLAYER_TEXT", "evidence must be a current project-owned reference")
    return resolve_ref({"game": root}, ref)


def workflow_fingerprint():
    paths = ["player_text/workflow.py", "player_text/player_text.py", "player_text/WORKFLOW.md",
             "player_text/CONTRACT.md", "factory_core/refs.py"]
    return digest([reference(FACTORY, path, "factory") for path in paths])


def _leaves(value, prefix=""):
    if isinstance(value, str):
        return {prefix: value}
    result = {}
    children = value.items() if isinstance(value, dict) else enumerate(value) if isinstance(value, list) else ()
    for key, child in children:
        token = str(key).replace("~", "~0").replace("/", "~1")
        result.update(_leaves(child, prefix + "/" + token))
    return result


def extract(root, source):
    path = confined(root, source["path"])
    options = source.get("options", {})
    if source["format"] == "json":
        fields(options, set(), {"pointer"})
        values = _leaves(read(path))
        pointer = options.get("pointer", "")
        if not isinstance(pointer, str) or (pointer and not pointer.startswith("/")):
            fail("INVALID_PLAYER_TEXT", "JSON pointer must be empty or start with /")
        values = {k: v for k, v in values.items() if k == pointer or k.startswith(pointer + "/")}
    elif source["format"] == "csv":
        fields(options, {"key_column", "text_column"})
        rows = list(csv.reader(io.StringIO(path.read_text(encoding="utf-8-sig"))))
        if not rows or len(rows[0]) != len(set(rows[0])):
            fail("INVALID_PLAYER_TEXT", "CSV needs unique headers")
        header = rows[0]
        if any(options[k] not in header for k in ("key_column", "text_column")):
            fail("INVALID_PLAYER_TEXT", "CSV column is missing")
        key_index, value_index = (header.index(options[k]) for k in ("key_column", "text_column"))
        values = {}
        for row in rows[1:]:
            if len(row) != len(header):
                fail("INVALID_PLAYER_TEXT", "CSV row width differs from header")
            key = text(row[key_index])
            if key in values:
                fail("INVALID_PLAYER_TEXT", f"duplicate CSV text key: {key}")
            values[key] = row[value_index]
    elif source["format"] == "text":
        fields(options, set())
        values = {"": path.read_text(encoding="utf-8")}
    else:
        fail("INVALID_PLAYER_TEXT", "format must be json, csv or text; export other formats explicitly")
    if not values:
        fail("PLAYER_TEXT_COVERAGE_REQUIRED", f"no text extracted from {source['path']}")
    return values


def snapshot(root, inventory):
    fields(inventory, {"schema_version", "scope", "locales", "locale_authority", "context_sources",
                       "coverage_notes", "sources", "runtime_paths"}, {"discovery_globs"})
    if inventory["schema_version"] != "player_text_inventory.v1" or inventory["scope"] not in ("ALL", "CHANGED"):
        fail("INVALID_PLAYER_TEXT", "inventory needs an ALL or CHANGED scope")
    locales = strings(inventory["locales"])
    current_ref(root, inventory["locale_authority"])
    strings(inventory["coverage_notes"])
    if not isinstance(inventory["context_sources"], list):
        fail("INVALID_PLAYER_TEXT", "context_sources must be a list of exact references")
    for ref in inventory["context_sources"]:
        current_ref(root, ref)
    sources = inventory["sources"]
    if not isinstance(sources, list) or not sources:
        fail("PLAYER_TEXT_COVERAGE_REQUIRED", "inventory must enumerate player-text sources")
    items, files, seen, locations, covered = [], {}, set(), set(), set()
    for source in sources:
        fields(source, {"id", "path", "format", "locale", "kind", "context"},
               {"options", "overrides", "exclude", "protected_forms", "rendered_paths"})
        sid = text(source["id"])
        if sid in seen or source["locale"] not in locales or source["kind"] not in KINDS:
            fail("INVALID_PLAYER_TEXT", "duplicate source id or unknown locale/text kind")
        seen.add(sid)
        text(source["context"])
        values = extract(root, source)
        exclusions = source.get("exclude", {})
        overrides = source.get("overrides", {})
        if not isinstance(exclusions, dict) or not isinstance(overrides, dict):
            fail("INVALID_PLAYER_TEXT", "exclude and overrides must map exact extracted keys")
        if (exclusions.keys() | overrides.keys()) - values.keys() or exclusions.keys() & overrides.keys():
            fail("PLAYER_TEXT_COVERAGE_REQUIRED", "unknown or overlapping exclusion/override")
        for reason in exclusions.values():
            text(reason)
        for key, value in values.items():
            if key in exclusions:
                continue
            text(value)  # A missing shipped translation is not an empty successful review.
            location = (source["path"], source["locale"], key)
            if location in locations:
                fail("PLAYER_TEXT_COVERAGE_REQUIRED", "overlapping source selectors")
            locations.add(location)
            covered.add(source["locale"])
            override = overrides.get(key, {})
            fields(override, set(), {"kind", "context", "protected_forms"})
            kind = override.get("kind", source["kind"])
            if kind not in KINDS:
                fail("INVALID_PLAYER_TEXT", "unknown text kind")
            protected = strings(override.get("protected_forms", source.get("protected_forms", [])), empty=True)
            items.append(dict(id=digest([sid, key, source["locale"]]), source_id=sid, key=key,
                              locale=source["locale"], kind=kind, text=value,
                              context=text(override.get("context", source["context"])), protected_forms=protected))
        for relative in [source["path"], *strings(source.get("rendered_paths", []), empty=True)]:
            files[relative] = sha(confined(root, relative))
    if covered != set(locales):
        fail("PLAYER_TEXT_COVERAGE_REQUIRED", "every shipped locale needs actual text, not only exclusions")
    for relative in strings(inventory["runtime_paths"], empty=True):
        files[relative] = sha(confined(root, relative))
    patterns = strings(inventory.get("discovery_globs", []), empty=inventory["scope"] != "ALL")
    for pattern in patterns:
        confined(root, pattern)  # Reject absolute/traversing patterns before globbing.
        matches = sorted(p for p in root.glob(pattern) if p.is_file())
        if not matches:
            fail("PLAYER_TEXT_COVERAGE_REQUIRED", f"discovery pattern matched no source files: {pattern}")
        for path in matches:
            relative = path.relative_to(root).as_posix()
            files[relative] = sha(confined(root, relative))
    # Before-text captures are evidence of the edit, NOT live references to overwritten files.
    return dict(items=items, files=[dict(source_path=p, source_sha256=h) for p, h in sorted(files.items())])


def prepare(root, inventory_path):
    ref = reference(root, inventory_path)
    inventory = read(current_ref(root, ref))
    captured = snapshot(root, inventory)
    current_ref(root, ref)
    return dict(schema_version="player_text_packet.v1", workflow_fingerprint=workflow_fingerprint(),
                inventory=ref, scope=inventory["scope"], locales=inventory["locales"], **captured)


def packet(root, packet_path):
    ref = reference(root, packet_path)
    data = read(current_ref(root, ref))
    fields(data, {"schema_version", "workflow_fingerprint", "inventory", "scope", "locales", "items", "files"})
    if data["schema_version"] != "player_text_packet.v1" or data["workflow_fingerprint"] != workflow_fingerprint():
        fail("STALE_PLAYER_TEXT", "packet belongs to another workflow version; prepare new evidence")
    inventory = read(current_ref(root, data["inventory"]))
    return ref, data, inventory


def seal(root, packet_path, producer_context_ids):
    packet_ref, before, inventory = packet(root, packet_path)
    producers = strings(producer_context_ids)
    after = snapshot(root, inventory)
    if {f["source_path"] for f in before["files"]} != {f["source_path"] for f in after["files"]}:
        fail("PLAYER_TEXT_COVERAGE_REQUIRED", "source discovery membership changed; inventory new/deleted sources and prepare again")
    originals = {item["id"]: item for item in before["items"]}
    if before["scope"] != inventory["scope"] or before["locales"] != inventory["locales"]:
        fail("STALE_PLAYER_TEXT", "packet scope/locales do not match its inventory")
    if len(originals) != len(before["items"]) or set(originals) != {item["id"] for item in after["items"]}:
        fail("PLAYER_TEXT_COVERAGE_REQUIRED", "text membership changed; prepare a new inventory, never drop new keys")
    for item in after["items"]:
        old = originals[item["id"]]
        if {k: v for k, v in old.items() if k != "text"} != {k: v for k, v in item.items() if k != "text"}:
            fail("STALE_PLAYER_TEXT", "text context or constraints changed")
        if Counter(PLACEHOLDERS.findall(old["text"])) != Counter(PLACEHOLDERS.findall(item["text"])):
            fail("PLAYER_TEXT_MEANING_REQUIRED", "placeholder identity/count changed")
        for form in item["protected_forms"]:
            if old["text"].count(form) != item["text"].count(form):
                fail("PLAYER_TEXT_MEANING_REQUIRED", f"protected form changed: {form}")
        item["disposition"] = "UNCHANGED" if old["text"] == item["text"] else "REWRITTEN"
    outputs = [reference(root, f["source_path"]) for f in after["files"]]
    current_ref(root, packet_ref)
    current_ref(root, before["inventory"])
    return dict(schema_version="player_text_candidate.v1", workflow_fingerprint=workflow_fingerprint(),
                packet=packet_ref, inventory=before["inventory"], scope=before["scope"], locales=before["locales"],
                producer_context_ids=producers, outputs=outputs, items=after["items"])


def candidate(root, path):
    ref = reference(root, path)
    data = read(current_ref(root, ref))
    fields(data, {"schema_version", "workflow_fingerprint", "packet", "inventory", "scope", "locales",
                  "producer_context_ids", "outputs", "items"})
    current_ref(root, data["packet"])
    expected = seal(root, data["packet"]["path"], data["producer_context_ids"])
    if data != expected:
        fail("STALE_PLAYER_TEXT", "candidate differs from latest text/runtime/context; reseal and rereview")
    return ref, data


def reading_packet(data):
    # Opaque ids, no answer-bearing locale keys, sources, originals, intended meanings or constraints.
    return dict(schema_version="player_text_reading_packet.v1", items=[
        {k: item[k] for k in ("id", "locale", "kind", "context", "text")} for item in data["items"]])


def _results(rows, ids, fields_required):
    if not isinstance(rows, list):
        fail("INVALID_PLAYER_TEXT", "results must be a list")
    seen = set()
    for row in rows:
        fields(row, {"id", *fields_required})
        identity = row["id"]
        if identity not in ids or identity in seen:
            fail("PLAYER_TEXT_COVERAGE_REQUIRED", "unknown or duplicate reviewed text id")
        seen.add(identity)
    if seen != ids:
        fail("PLAYER_TEXT_COVERAGE_REQUIRED", "every text in every locale needs its own result, including unchanged text")


def check(root, candidate_path, reading_path, backcheck_path):
    candidate_ref, data = candidate(root, candidate_path)
    reading_ref, back_ref = reference(root, reading_path), reference(root, backcheck_path)
    reading, back = read(current_ref(root, reading_ref)), read(current_ref(root, back_ref))
    fields(reading, {"schema_version", "packet_sha256", "reader_context_id", "reader_kind", "fresh", "sources_read", "results"})
    plain_digest = digest(reading_packet(data))
    if (reading["schema_version"] != "player_text_reading.v1" or reading["packet_sha256"] != plain_digest
            or reading["fresh"] is not True or reading["sources_read"] != [plain_digest]
            or reading["reader_kind"] not in ("AI", "HUMAN")):
        fail("INVALID_PLAYER_TEXT_READING", "first reading must use only the exact sanitized packet")
    reader = text(reading["reader_context_id"])
    if reader in data["producer_context_ids"]:
        fail("REVIEW_NOT_INDEPENDENT", "the text producer cannot supply its own first reading")
    ids = {item["id"] for item in data["items"]}
    _results(reading["results"], ids, {"understood", "status", "rationale"})
    for row in reading["results"]:
        text(row["understood"]); text(row["rationale"])
        if row["status"] != "PASS":
            fail("PLAYER_TEXT_REVISION_REQUIRED", "first reader found unresolved language difficulty")
    fields(back, {"schema_version", "candidate", "reading", "reviewer_context_id", "fresh", "coverage", "results"})
    if (back["schema_version"] != "player_text_backcheck.v1" or back["candidate"] != candidate_ref
            or back["reading"] != reading_ref or back["fresh"] is not True):
        fail("STALE_PLAYER_TEXT", "backcheck must bind this exact candidate and immutable reading")
    reviewer = text(back["reviewer_context_id"])
    if reviewer in {*data["producer_context_ids"], reader}:
        fail("REVIEW_NOT_INDEPENDENT", "informed backcheck must be distinct from producer and first reader")
    inventory = read(current_ref(root, data["inventory"]))
    coverage = back["coverage"]
    fields(coverage, {"status", "rationale", "evidence"})
    text(coverage["rationale"])
    required = [data["inventory"], inventory["locale_authority"], *inventory["context_sources"], *data["outputs"]]
    if not isinstance(coverage["evidence"], list) or any(ref not in coverage["evidence"] for ref in required):
        fail("PLAYER_TEXT_COVERAGE_REQUIRED", "coverage review must inspect inventory, locale authority, meaning sources and every runtime/text source")
    for ref in coverage["evidence"]:
        current_ref(root, ref)
    if coverage["status"] != "PASS":
        fail("PLAYER_TEXT_COVERAGE_REQUIRED", "whole declared scope and exclusions must be independently reviewed")
    _results(back["results"], ids, {"meaning", "language", "presentation", "rationale"})
    for row in back["results"]:
        text(row["rationale"])
        if any(row[key] != "PASS" for key in ("meaning", "language", "presentation")):
            fail("PLAYER_TEXT_REVISION_REQUIRED", "meaning, native language or actual presentation remains unresolved")
    # Detect ordinary concurrent edits before publishing evidence. Not a lock on unrelated editors.
    candidate(root, candidate_path)
    current_ref(root, reading_ref); current_ref(root, back_ref)
    return dict(schema_version="player_text_receipt.v1", status="PLAYER_TEXT_EVIDENCE_VALID",
                workflow_fingerprint=workflow_fingerprint(), candidate=candidate_ref, reading=reading_ref,
                backcheck=back_ref, scope=data["scope"], locales=data["locales"], text_count=len(ids),
                reader_kind=reading["reader_kind"], human_comprehension_proven=False, gameplay_accepted=False)


def verify(root, receipt_path):
    receipt_ref = reference(root, receipt_path)
    receipt = read(current_ref(root, receipt_ref))
    for key in ("candidate", "reading", "backcheck"):
        current_ref(root, receipt[key])
    result = check(root, *(receipt[key]["path"] for key in ("candidate", "reading", "backcheck")))
    if receipt != result:
        fail("STALE_PLAYER_TEXT", "receipt differs from current exact-output evidence")
    current_ref(root, receipt_ref)
    return result


def validate_design(roots, design):
    """v3-only applicability. No historical v1/v2 review is silently upgraded."""
    binding = design.get("player_text")
    if design["schema_version"] != "factory_design.v3":
        if binding is not None:
            fail("INVALID_DESIGN", "player_text design binding requires explicit v3; standalone workflow remains available")
        return
    if binding is None:
        if design["capability"] in PRODUCERS:
            fail("PLAYER_TEXT_SCOPE_REQUIRED", "v3 player-content producers must declare ALL, CHANGED or reviewed NONE")
        return
    fields(binding, {"scope", "scope_evidence", "receipt_path"})
    if binding["scope"] not in ("ALL", "CHANGED", "NONE") or binding["scope_evidence"] not in design["artifacts"]:
        fail("PLAYER_TEXT_SCOPE_REQUIRED", "scope needs a complete reviewed design artifact")
    if binding["scope"] == "NONE":
        if binding["receipt_path"] is not None:
            fail("PLAYER_TEXT_SCOPE_REQUIRED", "NONE must not manufacture a text receipt")
    elif binding["receipt_path"] not in design["production_scope"]:
        fail("PLAYER_TEXT_SCOPE_REQUIRED", "receipt must be in the authorized production scope")


def validate_checkpoint(roots, record, design):
    if design["schema_version"] != "factory_design.v3" or record["stage"] not in ("EVIDENCE_READY", "COMPLETE"):
        return
    binding = design.get("player_text")
    if not binding or binding["scope"] == "NONE":
        return
    root = roots["game"]
    receipt_ref = reference(root, binding["receipt_path"])
    if receipt_ref not in record["artifacts"]:
        fail("PLAYER_TEXT_EVIDENCE_REQUIRED", "latest-output checkpoint must include the exact text receipt")
    result = verify(root, binding["receipt_path"])
    if result["scope"] != binding["scope"]:
        fail("PLAYER_TEXT_COVERAGE_REQUIRED", "receipt cannot substitute a smaller reviewed scope")
    receipt = read(current_ref(root, receipt_ref))
    _, data = candidate(root, receipt["candidate"]["path"])
    if design["author_context_id"] not in data["producer_context_ids"]:
        fail("REVIEW_NOT_INDEPENDENT", "receipt must include the actual design author among producers")
    for output in data["outputs"]:
        if output["path"] in design["production_scope"] and output not in record["artifacts"]:
            fail("PLAYER_TEXT_EVIDENCE_REQUIRED", "reviewed text must match the checkpoint's latest produced files")
    if design["capability"] == "story":
        from factory_core.story_profile import resolve
        from factory_core.state import project
        profile = resolve(root, project(root)["authority_paths"], roots["factory"])
        if set(result["locales"]) != set(profile["shipped_locales"]):
            fail("PLAYER_TEXT_COVERAGE_REQUIRED", "text receipt must cover Story's actual shipped locales")
