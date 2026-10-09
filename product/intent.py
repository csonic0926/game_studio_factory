"""Nonbinding, source-bound whole-product intent. Never an assessment or approval."""
from __future__ import annotations

from pathlib import Path
import re

from factory_core.refs import (FactoryError, confined, exclusive_json, fail, read_json,
                               reference, resolve_ref, unique_refs)
from factory_core.state import identifier, keys, project, project_lock, text, texts

PATH = "design/product_value/PRODUCT_VALUE_INTENT.json"
TEMPLATE = "product/templates/PRODUCT_VALUE_INTENT.json"
WORKFLOW = "product/docs/PROJECT_INITIALIZATION_WORKFLOW.md"
IDEA_PATHS = (
    "design/product/idea/IDEA_FACTORY_REPO_PROBE.json",
    "design/product/idea/IDEA_EXPLORATION.json",
    "design/product/idea/IDEA_EXPLORATION.md",
    "design/product/idea/PRODUCT_THESIS_INPUT.json",
    "design/product/idea/IDEA_FACTORY_RESULT.json",
    "design/product/PRODUCT_THESIS.md",
    "design/product/FACTORY_CONSTRAINTS.json",
    "design/product/PRODUCT_AUTHORITY_REGISTER.json",
)
RECONCILE_CODES = {"STALE_DEPENDENCY", "MISSING_REFERENCE"}



def file_target(game, name):
    path = confined(game, name)
    for parent in path.parents:
        if parent == game.resolve():
            break
        if parent.exists() and not parent.is_dir():
            fail("INVALID_PROJECT", f"parent must be a directory: {parent.relative_to(game)}")
    if path.exists() and not path.is_file():
        fail("INVALID_PROJECT", f"expected a regular file: {name}")
    return path


def source_refs(roots):
    """Exact Idea context membership, not a declaration of active authority."""
    return [reference(roots["game"], name) for name in IDEA_PATHS
            if file_target(roots["game"], name).is_file()]


def _refs(roots, refs):
    if not isinstance(refs, list):
        fail("INVALID_PRODUCT_INTENT", "references must be a list")
    for ref in refs:
        if not isinstance(ref, dict) or ref.get("scope") not in ("game", "game_git"):
            fail("INVALID_PRODUCT_INTENT", "intent sources must be game-owned")
        required = {"scope", "path", "sha256"}
        if ref["scope"] == "game_git":
            required.add("revision")
            if not isinstance(ref.get("revision"), str) or not re.fullmatch(r"[0-9a-f]{40,64}", ref["revision"]):
                fail("INVALID_REFERENCE", "historical source needs a full Git revision")
        keys(ref, required)
        confined(roots["game"], ref["path"])
        if not isinstance(ref["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", ref["sha256"]):
            fail("INVALID_REFERENCE", "source needs a SHA-256")
    if len(unique_refs(refs)) != len(refs):
        fail("INVALID_PRODUCT_INTENT", "duplicate source reference")


def validate(roots, data):
    """Validate honest planning shape and exact evidence; never infer taste/value."""
    from product.value import validate_context
    keys(data, {"schema_version", "state", "source_refs", "offer", "audience", "buying_reason",
                "adequacy_case", "value_hypotheses", "material_unknowns", "next_move",
                "current_build_assessment", "value_claim_eligible", "authority_granted"})
    if (data["schema_version"] != "product_value_intent.v1" or data["state"] not in ("OPEN", "DRAFTED")
            or data["current_build_assessment"] != "NOT_ASSESSED"
            or data["value_claim_eligible"] is not False or data["authority_granted"] is not False):
        fail("INVALID_PRODUCT_INTENT", "intent remains nonbinding and NOT_ASSESSED, never an accepted value result")
    for name in ("buying_reason", "adequacy_case"):
        if data[name] is not None:
            text(data[name])
    texts(data["material_unknowns"])
    text(data["next_move"])
    _refs(roots, data["source_refs"])
    if any(ref["scope"] != "game" for ref in data["source_refs"]):
        fail("INVALID_PRODUCT_INTENT", "Idea context snapshot uses current game sources")
    if not isinstance(data["value_hypotheses"], list):
        fail("INVALID_PRODUCT_INTENT", "value_hypotheses must be a list")
    seen = set()
    all_refs = list(data["source_refs"])
    for hypothesis in data["value_hypotheses"]:
        keys(hypothesis, {"id", "statement", "source_refs"})
        identifier(hypothesis["id"])
        if hypothesis["id"] in seen:
            fail("INVALID_PRODUCT_INTENT", "duplicate hypothesis id")
        seen.add(hypothesis["id"])
        text(hypothesis["statement"])
        _refs(roots, hypothesis["source_refs"])
        all_refs.extend(hypothesis["source_refs"])
    # Context validation retains existing grounded/adopted-offer provenance rules.
    validate_context(roots, data["offer"], data["audience"])
    for ref in all_refs:
        resolve_ref(roots, ref)
    return data


def preflight(roots, *, routing=False):
    """Validate every initializer-owned surface before the first managed write."""
    game = roots["game"]
    markers = ("design/factory/.migration.json", "design/factory/.migration-gpt6.json")
    pointers = ("design/STUDIO_FACTORY.local.md", "design/AI_FACTORY.local.md")
    metadata = "design/factory/PROJECT.json"
    paths = [PATH, *IDEA_PATHS, *markers, *pointers, metadata]
    if routing:
        paths += ["AGENTS.md", "CLAUDE.md", ".gitignore"]
    for name in paths:
        path = file_target(game, name)
        if path.exists():
            if path.suffix == ".json" and name not in markers:
                read_json(path)
            elif path.suffix == ".md" or name == ".gitignore":
                path.read_text(encoding="utf-8")
    if any(confined(game, name).exists() for name in markers):
        fail("MIGRATION_RECOVERY_REQUIRED", "finish the prepared migration before initialization")
    # Initialization is not a request to replace an existing selected checkout.
    # A deliberate link/relink remains the separate setup.py link operation.
    for name in pointers:
        pointer = confined(game, name)
        if not pointer.exists():
            continue
        body = pointer.read_text()
        values = re.findall(r"^STUDIO_ROOT:\s*(.+?)\s*$", body, re.M)
        if not values:
            values = re.findall(r"^FACTORY_ROOT:\s*(.+?)\s*$", body, re.M)
        if len(values) != 1:
            fail("FACTORY_SOURCE_REQUIRED", "existing local pointer must identify one selected checkout")
        if Path(values[0]).expanduser().resolve() != roots["factory"].resolve():
            fail("FACTORY_SOURCE_MISMATCH", "initialize using the selected checkout; an explicit relink is separate")
        break  # Canonical pointer wins; legacy is a fallback, not a second owner.
    if confined(game, metadata).exists():
        selected = project(game)
        if selected["workflow_version"] == 3:
            from factory_core.astra import check_checkout
            check_checkout(game, roots["factory"])
    if routing and confined(game, "AGENTS.md").exists():
        from factory_core.migration import split_routing
        split_routing(confined(game, "AGENTS.md").read_text())
    path = confined(game, PATH)
    if path.exists():
        try:
            validate(roots, read_json(path))
        except FactoryError as exc:
            if exc.code not in RECONCILE_CODES:
                raise
            # Old exact inputs are preserved, never automatically refreshed.


def inspect(roots):
    """Rebuild a read-only planning view separately from current authority."""
    from product.value import _authority
    out = {"status": "PRODUCT_INTENT_MISSING", "authority_granted": False,
           "value_claim_eligible": False, "current_build_assessment": "NOT_ASSESSED",
           "blockers": [], "next_action": "product/product.py start, then author nonbinding whole-value intent"}
    try:
        current = source_refs(roots)
        out.update(current_source_refs=current, idea_authority=_authority(roots))
        path = file_target(roots["game"], PATH)
        if not path.exists():
            return out
        data = read_json(path)
        out.update(reference=reference(roots["game"], PATH), intent=data)
        validate(roots, data)
        if unique_refs(data["source_refs"]) != unique_refs(current):
            fail("STALE_DEPENDENCY", "Idea source membership/content changed; read and reconcile, do not silently rehash")
        out.update(status="PRODUCT_INTENT_" + data["state"], next_action=data["next_move"])
    except (FactoryError, OSError, ValueError, KeyError, TypeError) as exc:
        code = getattr(exc, "code", "INVALID_PRODUCT_INTENT")
        out.update(status="RECONCILIATION_REQUIRED" if code in RECONCILE_CODES else "INVALID_PRODUCT_INTENT",
                   next_action="Read current sources, revise the nonbinding intent and deliberately update exact refs")
        out["blockers"].append({"code": code, "message": str(exc)})
    return out


def seed(roots, *, dry_run=False):
    """Internal writer; caller owns preflight and the shared project lock."""
    path = file_target(roots["game"], PATH)
    created = not path.exists()
    if created:
        data = read_json(roots["factory"] / TEMPLATE)
        data["source_refs"] = source_refs(roots)
        validate(roots, data)
        if not dry_run:
            exclusive_json(path, data)
    out = inspect(roots)
    out["created_paths"] = [PATH] if created and not dry_run else []
    if dry_run:
        out.update(dry_run=True, planned_paths=[PATH] if created else [])
    return out


def start(roots, *, dry_run=False):
    from factory_core.refs import game_root
    roots = {**roots, "game": game_root(roots["game"], roots["factory"])}
    if dry_run:
        preflight(roots)
        return seed(roots, dry_run=True)
    preflight(roots)
    with project_lock(roots["game"]):
        preflight(roots)
        return seed(roots)
