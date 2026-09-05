"""Explicit additive migration, hash-preflighted and activation-last.

Historical artifacts are referenced, never rewritten or promoted. Transactions
are cooperative; external editors must not race the final atomic replace.
"""
from __future__ import annotations

import difflib
import os
from pathlib import Path
import tempfile

from .refs import (confined, digest, encoded, exclusive_json, fail, read_json,
                   reference, revision, sha)
from .state import PROJECT_PATH, identifier, project, project_lock

BEGIN = "<!-- game_ai_factory:routing:begin -->"
END = "<!-- game_ai_factory:routing:end -->"
JOURNAL = "design/factory/.migration.json"


def routing_block() -> str:
    return f"""{BEGIN}
## Game Studio Factory routing (managed block — edit via setup.py, not by hand)

Resolve `$STUDIO_ROOT` from `design/STUDIO_FACTORY.local.md`, falling back to
legacy `design/AI_FACTORY.local.md`. Both pointers remain supported.
Run `python3 $STUDIO_ROOT/factory.py inspect --game-repo .` first. This project
uses Factory v2 only after `design/factory/PROJECT.json` activates version 2.
`MIGRATION_REQUIRED` blocks new v2 work; never reinterpret historical approvals.

Whole-game intent uses `game-studio-factory`; deliberately bounded work uses
`idea-factory`, `gameplay-factory`, `game-story-factory`, or the Asset/Sound
landing. Current work and role context come from `factory.py context`.
The primary agent continues design and production. The exact complete design
receives two independent boundary reviews under
`$STUDIO_ROOT/factory_core/docs/WORKFLOW.md`. That adopted v2 **process** replaces
Factory-generated per-step workers, repeated generic transition reviews and
separate Card/spec authors and whole-HEAD freshness, not this project's semantic
or content requirements. For v2, these process replacements also govern earlier
Factory workflow clauses in project sync/authoring documents; all their project
quality obligations and exact pending/historical rulings remain intact.
Card views project one design. Existing authorized repairs do not reopen design.

Product adoption, material design approval and exact-build human playtest remain
USER-owned. Idea exploration may remain open or no-fit. Root/project rules,
product lifecycle, gameplay standards and story sovereignty still bind.
New gameplay acceptance still requires exact-build interaction, isolated blind
observation, informed comparison, human verdict and predecessor regression.
An interactive software demo is not an Accepted Playable Baseline.
Runtime evidence alone cannot authorize or promote gameplay.

Factory outputs belong in this game repo, never in the Factory checkout.
{END}
"""


def split_routing(body: str) -> str:
    if body.count(BEGIN) != body.count(END) or body.count(BEGIN) > 1:
        fail("MALFORMED_ROUTING", "managed marker pair must be unique and ordered")
    if BEGIN not in body:
        return body
    start, end = body.index(BEGIN), body.index(END)
    if end < start:
        fail("MALFORMED_ROUTING", "managed markers are reversed")
    return body[:start] + body[end + len(END):]


def routed(body: str) -> str:
    split_routing(body)  # validate before considering any output
    if BEGIN in body:
        start, end = body.index(BEGIN), body.index(END) + len(END)
        return body[:start] + routing_block().rstrip("\n") + body[end:]
    return body + routing_block().rstrip("\n")


def inventory(game: Path) -> list[dict]:
    """Read-only status facts, not revalidation or imported authorization."""
    paths = set()
    patterns = ("design/studio/*REGISTER.json", "design/product/*REGISTER.json",
                "design/studio/**/ACCEPTED_PLAYABLE_BASELINE*.json",
                "design/studio/**/STUDIO_RUN_STATE.json",
                "design/gameplay/**/GAMEPLAY_DESIGN_VERDICT.json",
                "design/gameplay/**/GAMEPLAY_DECISION_CARD.json",
                "design/gameplay/**/GAMEPLAY_REPAIR_STATE.json")
    for pattern in patterns:
        paths.update(game.glob(pattern))
    result = []
    for path in sorted(paths):
        relative = path.relative_to(game).as_posix()
        data = read_json(confined(game, relative))
        item = {"reference": reference(game, relative), "schema_version": data.get("schema_version"),
                "recorded_status": data.get("status", data.get("state", data.get("human_verdict"))),
                "meaning": "HISTORICAL_ONLY_NOT_NEW_ACCEPTANCE"}
        if "entries" in data:
            item["entries"] = [{k: entry.get(k) for k in ("card_id", "state", "decision_payload_sha256")}
                               for entry in data["entries"]]
        result.append(item)
    return result


def source_set(game: Path, authority_paths=()) -> dict:
    """Migration watches all current project authority and historical JSON.

    Does not open/change assets, engine caches or untracked game artifacts.
    Membership catches added relevant authority while a preview is pending.
    """
    names = {"AGENTS.md", *authority_paths}
    for pattern in ("design/**/*.json", "design/**/AGENTS.md", "design/**/adapter/*.md",
                    "design/**/adapter/*.csv", "design/product/*.md"):
        names.update(p.relative_to(game).as_posix() for p in game.glob(pattern) if p.is_file())
    names = {p for p in names if not p.startswith("design/factory/")}
    return {p: sha(confined(game, p)) if confined(game, p).exists() else None for p in sorted(names)}


def preview(game: Path, factory: Path, project_id: str, authority_paths=()) -> dict:
    identifier(project_id)
    if confined(game, PROJECT_PATH).exists() and not confined(game, JOURNAL).exists():
        p = project(game)
        if p["project_id"] != project_id or sorted(authority_paths) != p["authority_paths"]:
            fail("MIGRATION_CONFLICT", "existing migration identity/authorities differ")
        return {"status": "ALREADY_MIGRATED", "changes": [], "source_digest": p["migration_source_digest"]}
    if confined(game, JOURNAL).exists():
        journal = read_json(confined(game, JOURNAL))
        if journal["project_id"] != project_id or journal["authority_paths"] != sorted(authority_paths):
            fail("MIGRATION_CONFLICT", "pending transaction identity differs")
        return {"status": "MIGRATION_RECOVERY_REQUIRED", "source_digest": journal["source_digest"],
                "changes": list(journal["targets"])}
    for path in authority_paths:
        sha(confined(game, path))
    sources = source_set(game, authority_paths)
    old = confined(game, "AGENTS.md").read_text() if sources["AGENTS.md"] else ""
    new = routed(old)
    source_digest = digest({"sources": sources, "project_id": project_id,
                            "authority_paths": sorted(authority_paths), "routing": routing_block()})
    return {"status": "MIGRATION_AVAILABLE", "source_digest": source_digest,
            "changes": ["AGENTS.md", "design/factory/ROUTING_RECEIPT.json", PROJECT_PATH],
            "routing_diff": "".join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                                                       fromfile="AGENTS.md (current)", tofile="AGENTS.md (v2 routing)")),
            "history": inventory(game), "historical_rulings_reissued": False,
            "untracked_cleanup": False, "game_content_changes": False}


def replace_checked(path: Path, before: str | None, content: bytes):
    current = sha(path) if path.exists() else None
    if current != before:
        fail("CONCURRENT_WRITE", f"changed before write: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".factory-write-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(content)
            out.flush()
            os.fsync(out.fileno())
        if (sha(path) if path.exists() else None) != before:
            fail("CONCURRENT_WRITE", f"changed while staging: {path}")
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def apply(game: Path, factory: Path, project_id: str, expected: str, authority_paths=()) -> dict:
    with project_lock(game):
        check = preview(game, factory, project_id, authority_paths)
        if check["status"] == "ALREADY_MIGRATED":
            return check
        if expected != check["source_digest"]:
            fail("CONCURRENT_WRITE", "preview/source digest changed; inspect a new migration diff")
        journal_path = confined(game, JOURNAL)
        if journal_path.exists():
            journal = read_json(journal_path)
        else:
            sources = source_set(game, authority_paths)
            old = confined(game, "AGENTS.md").read_text() if sources["AGENTS.md"] else ""
            new = routed(old)
            import hashlib
            new_sha = hashlib.sha256(new.encode()).hexdigest()
            metadata = {"schema_version": "factory_project.v2", "workflow_version": 2,
                        "project_id": project_id, "factory_revision": revision(factory),
                        "authority_paths": sorted(authority_paths), "historical_inventory": inventory(game),
                        "migration_source_digest": expected}
            # Receipt records hashes only (not a backup); old root-rule authority
            # remains intact outside the exact managed routing span.
            receipt = {"schema_version": "factory_routing_receipt.v2", "before_sha256": sources["AGENTS.md"],
                       "after_sha256": new_sha, "outside_routing_sha256": hashlib.sha256(split_routing(old).encode()).hexdigest(),
                       "source_digest": expected}
            journal = {"schema_version": "factory_migration_transaction.v2", "project_id": project_id,
                       "authority_paths": sorted(authority_paths), "source_digest": expected,
                       "sources": sources, "routing_sha256": digest(routing_block()), "targets": {"AGENTS.md": new_sha,
                       "design/factory/ROUTING_RECEIPT.json": digest(receipt), PROJECT_PATH: digest(metadata)},
                       "metadata": metadata, "receipt": receipt}
            # Complete output/source preflight before even publishing intent.
            if digest({"sources": sources, "project_id": project_id,
                       "authority_paths": sorted(authority_paths), "routing": routing_block()}) != expected:
                fail("CONCURRENT_WRITE", "sources changed during migration preflight")
            for name, expected_hash in journal["targets"].items():
                path = confined(game, name)
                if name != "AGENTS.md" and path.exists() and sha(path) != expected_hash:
                    fail("CONCURRENT_WRITE", f"migration target already exists: {name}")
            # metadata/receipt are new outputs, not copies of old artifacts.
            exclusive_json(journal_path, journal)
        if journal.get("routing_sha256") != digest(routing_block()):
            fail("MIGRATION_IMPLEMENTATION_CHANGED", "recovery requires the exact routing implementation that prepared this transaction")
        for name, expected_hash in journal["targets"].items():
            path = confined(game, name)
            if name != "AGENTS.md" and path.exists() and sha(path) != expected_hash:
                fail("CONCURRENT_WRITE", f"pending migration output changed: {name}")
        sources = source_set(game, authority_paths)
        for name in set(sources) | set(journal["sources"]):
            actual = sources.get(name)
            before = journal["sources"].get(name)
            after = journal["targets"].get(name)
            if actual != before and not (after is not None and actual == after):
                fail("CONCURRENT_WRITE", f"pending migration source changed: {name}")
        agents = confined(game, "AGENTS.md")
        if (sha(agents) if agents.exists() else None) != journal["targets"]["AGENTS.md"]:
            old = agents.read_text() if agents.exists() else ""
            content = routed(old).encode()
            import hashlib
            if hashlib.sha256(content).hexdigest() != journal["targets"]["AGENTS.md"]:
                fail("MIGRATION_IMPLEMENTATION_CHANGED", "routing bytes do not match prepared transaction")
            replace_checked(agents, journal["sources"]["AGENTS.md"], content)
        for name, payload in (("design/factory/ROUTING_RECEIPT.json", journal["receipt"]),
                              (PROJECT_PATH, journal["metadata"])):
            path = confined(game, name)
            if path.exists():
                if sha(path) != journal["targets"][name]:
                    fail("CONCURRENT_WRITE", f"pending migration output changed: {name}")
            else:
                # Activation metadata is the last write; partial prior output
                # remains MIGRATION_REQUIRED until this exclusive publication.
                exclusive_json(path, payload)
        for name, expected_hash in journal["targets"].items():
            if sha(confined(game, name)) != expected_hash:
                fail("CONCURRENT_WRITE", "migration output changed before finalization")
        journal_path.unlink()
        return {"status": "MIGRATED", "source_digest": expected, "changes": list(journal["targets"]),
                "historical_rulings_reissued": False, "game_content_changes": False}


def routing_reference_valid(game: Path, relative: str, expected: str) -> bool:
    """Narrow v2 compatibility for an old standard's root routing reference.

    Never changes an old hash or validates an old review. Only the exact
    before/after routing transaction is recognized; semantic edits fail closed.
    """
    if relative != "AGENTS.md" or not confined(game, PROJECT_PATH).exists():
        return False
    receipt_path = confined(game, "design/factory/ROUTING_RECEIPT.json")
    if not receipt_path.exists():
        return False
    receipt = read_json(receipt_path)
    import hashlib
    current = confined(game, relative)
    return (receipt.get("before_sha256") == expected and receipt.get("after_sha256") == sha(current)
            and receipt.get("outside_routing_sha256") == hashlib.sha256(split_routing(current.read_text()).encode()).hexdigest())
