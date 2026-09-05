"""Typed, append-only work ledger. A checkpoint is never product authority."""
from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import re

from .catalog import authority_refs, factory_dependencies, CAPABILITIES
from .refs import (FactoryError, confined, digest, encoded, exclusive_json, fail,
                   read_json, reference, resolve_ref, revision, sha, unique_refs, expand_references)

PROJECT_PATH = "design/factory/PROJECT.json"
STAGES = ("DRAFT", "DESIGN_COMPLETE", "REVIEWED", "AUTHORIZED", "PRODUCING", "EVIDENCE_READY", "COMPLETE")
ROLES = ("intent_experience", "completeness_project")
ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,95}$")


def identifier(value):
    if not isinstance(value, str) or not ID.fullmatch(value):
        fail("INVALID_ID", str(value))
    return value


def keys(value, required, optional=()):
    if not isinstance(value, dict) or set(required) - set(value) or set(value) - set(required) - set(optional):
        fail("INVALID_SHAPE", f"requires {sorted(required)}; optional {sorted(optional)}")


def text(value):
    if not isinstance(value, str) or not value.strip():
        fail("INVALID_TEXT", "nonempty text required")
    return value


def texts(value):
    if not isinstance(value, list):
        fail("INVALID_SHAPE", "expected list of text")
    return [text(x) for x in value]


@contextmanager
def project_lock(game: Path):
    """Advisory OS lock survives crashes without stale-lock deletion heuristics.

    All Factory v2 writers participate. Noncooperating editors are checked by
    source hashes immediately before commit; filesystem-wide isolation is not
    claimed. Lock inode is persistent and contains no project/backup data.
    """
    import subprocess
    result = subprocess.run(["git", "-C", str(game), "rev-parse", "--absolute-git-dir"],
                            text=True, capture_output=True, timeout=10)
    if result.returncode:
        fail("INVALID_PROJECT", "writer lock requires an initialized game Git repository")
    path = Path(result.stdout.strip()) / "factory-v2.lock"
    if path.is_symlink():
        fail("UNSAFE_PATH", "Factory lock must not be a symlink")
    with path.open("a+b") as handle:
        if os.name == "nt":  # pragma: no cover - Windows CI path
            import msvcrt
            if path.stat().st_size == 0:
                handle.write(b"\0")
                handle.flush()
            handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                fail("CONCURRENT_WRITE", "another Factory writer holds the project lock")
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                fail("CONCURRENT_WRITE", "another Factory writer holds the project lock")
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def project(game: Path) -> dict:
    path = confined(game, PROJECT_PATH)
    if not path.exists():
        fail("MIGRATION_REQUIRED", "run factory.py migrate --check, then explicit --apply")
    data = read_json(path)
    keys(data, {"schema_version", "workflow_version", "project_id", "factory_revision", "authority_paths", "historical_inventory", "migration_source_digest"})
    if data["schema_version"] != "factory_project.v2" or data["workflow_version"] != 2:
        fail("MIGRATION_REQUIRED", "unknown project format; no implicit migration")
    identifier(data["project_id"])
    texts(data["authority_paths"])
    return data


def latest(game: Path, task_id: str) -> tuple[dict | None, str | None]:
    identifier(task_id)
    game = game.resolve()
    directory = confined(game, f"design/factory/checkpoints/{task_id}")
    paths = sorted(directory.glob("*.json")) if directory.exists() else []
    previous = None
    previous_digest = None
    for generation, path in enumerate(paths, 1):
        confined(game, path.relative_to(game).as_posix())
        record = read_json(path)
        if (path.name != f"{generation:06d}.json" or record.get("generation") != generation
                or record.get("task_id") != task_id or record.get("previous") != previous_digest
                or record.get("schema_version") != "factory_checkpoint.v2"):
            fail("BROKEN_CHECKPOINT_CHAIN", str(path))
        previous, previous_digest = record, sha(path)
    return previous, previous_digest


def load_design(roots: dict, ref: dict) -> dict:
    if ref.get("scope") != "game":
        fail("INVALID_DESIGN", "design must be game-owned")
    d = read_json(resolve_ref(roots, ref))
    keys(d, {"schema_version", "design_id", "capability", "task", "author_context_id", "intent",
             "artifacts", "inputs", "decisions", "requirements", "production_scope", "acceptance"}, {"gameplay", "story"})
    if d["schema_version"] != "factory_design.v2" or d["capability"] not in CAPABILITIES:
        fail("INVALID_DESIGN", "unsupported design type/capability")
    identifier(d["design_id"])
    text(d["task"])
    text(d["author_context_id"])
    text(d["intent"])
    if not isinstance(d["artifacts"], list) or not d["artifacts"]:
        fail("INVALID_DESIGN", "complete design artifacts required; no empty summary package")
    if not isinstance(d["inputs"], list):
        fail("INVALID_DESIGN", "inputs must be a list")
    for item in d["artifacts"] + d["inputs"]:
        resolve_ref(roots, item)
        if item["scope"] not in ("game", "game_git") or (item in d["artifacts"] and item["scope"] != "game"):
            fail("INVALID_DESIGN", "design artifacts must be live game files; inputs may pin normal Git history")
    if not isinstance(d["decisions"], list) or not d["decisions"]:
        fail("INVALID_DESIGN", "human decision surface required for a complete design")
    seen = set()
    for item in d["decisions"]:
        keys(item, {"id", "source", "excerpt", "consequence"})
        identifier(item["id"])
        if item["id"] in seen:
            fail("INVALID_DESIGN", "duplicate decision id")
        seen.add(item["id"])
        if item["source"] not in d["artifacts"]:
            fail("INVALID_DESIGN", "Card must project the one complete design, not an alternate spec")
        source = resolve_ref(roots, item["source"]).read_text(encoding="utf-8")
        if text(item["excerpt"]) not in source or text(item["consequence"]) not in source:
            fail("INVALID_DESIGN", "decision and consequence must be exact design excerpts")
    if not isinstance(d["requirements"], dict):
        fail("INVALID_DESIGN", "requirements must map ids to exact source + obligation")
    for name, requirement in d["requirements"].items():
        text(name)
        keys(requirement, {"source", "obligation"})
        resolve_ref(roots, requirement["source"])
        text(requirement["obligation"])
    scope = texts(d["production_scope"])
    if not scope:
        fail("INVALID_DESIGN", "bounded production file paths required")
    protected = {r["path"] for r in authority_refs(roots["game"], d["capability"], project(roots["game"])["authority_paths"])}
    for path in scope:
        confined(roots["game"], path)
        if path in protected or Path(path).name == "AGENTS.md":
            fail("CONFLICTING_STATE_OWNERSHIP", "generic production cannot mutate adopted authority or sovereignty")
        if any(r["scope"] == "game" and r["path"] == path for r in d["inputs"] + d["artifacts"]):
            fail("CONFLICTING_STATE_OWNERSHIP", "live design/input cannot also be a production output; pin implementation input in Git history")
        if Path(path).name in ("STUDIO_RUN_STATE.json", "STUDIO_DECISION_CARD_REGISTER.json", "ACCEPTED_PLAYABLE_BASELINE.json", "GAMEPLAY_REPAIR_STATE.json"):
            fail("CONFLICTING_STATE_OWNERSHIP", "production cannot write tool-owned registers or work state")
        if path == "AGENTS.md" or path.startswith(("design/factory/", "design/product/", "design/studio/baselines/")):
            fail("INVALID_DESIGN", "production cannot write authority, work ledger, or accepted history")
    texts(d["acceptance"])
    if not d["acceptance"]:
        fail("INVALID_DESIGN", "exact-output acceptance obligations required")
    if "story" in d:
        if d["capability"] != "story": fail("INVALID_DESIGN", "Story applicability belongs only to Story")
        keys(d["story"], {"spoken_output_paths", "scope_evidence"})
        spoken = texts(d["story"]["spoken_output_paths"])
        if set(spoken) - set(scope) or d["story"]["scope_evidence"] not in d["artifacts"]:
            fail("INVALID_DESIGN", "dialogue applicability must be bound to the reviewed output scope and a full source artifact")
    if d["capability"] in ("studio", "gameplay"):
        from gameplay.v2 import validate_design
        validate_design(roots, d)
    return d


def dependencies(roots: dict, design_ref: dict, d: dict) -> dict:
    p = project(roots["game"])
    refs = [design_ref, reference(roots["game"], PROJECT_PATH)]
    refs += d["inputs"] + d["artifacts"]
    refs += [r["source"] for r in d["requirements"].values()]
    refs += authority_refs(roots["game"], d["capability"], p["authority_paths"])
    refs += factory_dependencies(roots["factory"], d["capability"], d["task"])
    refs = expand_references(roots, unique_refs(refs))
    for ref in refs:
        resolve_ref(roots, ref)
    return {"algorithm": "sha256-content-closure.v2", "references": refs, "fingerprint": digest(refs)}


def requirement_ids(factory: Path, d: dict, role: str) -> set[str]:
    rule_map = read_json(factory / "factory_core/rule_map.json")
    return {r["id"] for r in rule_map["rules"] if role in r["reviewers"] and
            ("all" in r["capabilities"] or d["capability"] in r["capabilities"])} | set(d["requirements"])


def check_reviews(roots: dict, design_ref: dict, d: dict, binding: dict, refs: list):
    if not isinstance(refs, list) or len(refs) != 2:
        fail("REVIEW_REQUIRED", "exactly two independent first-pass boundary reviews required")
    contexts = {d["author_context_id"]}
    roles = set()
    for ref in refs:
        review = read_json(resolve_ref(roots, ref))
        keys(review, {"schema_version", "role", "reviewer_context_id", "fresh", "peer_reviews_read",
                      "design", "dependency_fingerprint", "verdict", "findings", "source_coverage", "decision_coverage"})
        role = review["role"]
        if review["schema_version"] != "factory_review.v2" or role not in ROLES or role in roles:
            fail("INVALID_REVIEW", "one review per distinct required role")
        context = text(review["reviewer_context_id"])
        if context in contexts or review["fresh"] is not True or review["peer_reviews_read"] != []:
            fail("REVIEW_NOT_INDEPENDENT", "fresh non-author contexts; first pass cannot read peer conclusions")
        contexts.add(context)
        roles.add(role)
        if review["design"] != design_ref or review["dependency_fingerprint"] != binding["fingerprint"]:
            fail("STALE_REVIEW", "review must bind the exact shared design and current dependency closure")
        if review["verdict"] != "PASS":
            fail("DESIGN_REJECTED", f"{role} requires revision")
        findings = review["findings"]
        required = requirement_ids(roots["factory"], d, role)
        if not isinstance(findings, dict) or set(findings) != required:
            fail("INCOMPLETE_REVIEW", f"{role}: cover exactly {sorted(required)}")
        for finding in findings.values():
            keys(finding, {"status", "evidence", "rationale"})
            if finding["status"] != "PASS":
                fail("DESIGN_REJECTED", f"{role}: failing requirement")
            text(finding["rationale"])
            if not isinstance(finding["evidence"], list) or not finding["evidence"]:
                fail("INCOMPLETE_REVIEW", "finding requires exact design/source evidence")
            for source in finding["evidence"]:
                resolve_ref(roots, source)
                if source not in binding["references"]:
                    fail("INVALID_REVIEW", "finding evidence must be in sealed dependency closure")
        if set(texts(review["decision_coverage"])) != {x["id"] for x in d["decisions"]}:
            fail("INCOMPLETE_REVIEW", "review must cover whole human decision surface")
        expected_sources = {r["scope"] + ":" + r["path"] for r in binding["references"]
                            if r["scope"] != "factory"}
        if set(texts(review["source_coverage"])) != expected_sources:
            fail("INCOMPLETE_REVIEW", "review must inventory every bound project source")


def approval_action(design_ref, binding):
    return f"APPROVE {design_ref['sha256']} {binding['fingerprint']}"


def check_ruling(roots, ref, design_ref, binding):
    ruling = read_json(resolve_ref(roots, ref))
    keys(ruling, {"schema_version", "owner", "decision", "design", "dependency_fingerprint", "source", "quote"})
    if (ruling["schema_version"] != "factory_ruling.v2" or ruling["owner"] != "USER"
            or ruling["design"] != design_ref or ruling["dependency_fingerprint"] != binding["fingerprint"]):
        fail("HUMAN_RULING_REQUIRED", "exact USER ruling on reviewed design required")
    # Origin is an auditable user transcript, not a machine-verifiable identity
    # signature. Harness/operator must preserve raw role and content.
    source = read_json(resolve_ref(roots, ruling["source"]))
    if source.get("role") != "user" or text(ruling["quote"]) not in source.get("content", ""):
        fail("INVALID_RULING_SOURCE", "ruling quote must occur in the raw USER message")
    if ruling["decision"] != "APPROVE":
        fail("USER_REJECTED", "rejected work cannot execute")
    action = approval_action(design_ref, binding)
    if ruling["quote"].strip() != action or source.get("content", "").strip() != action:
        fail("EXACT_APPROVAL_REQUIRED", "USER must submit the exact approval action from the reviewed human view; never infer approval from a quoted rejection")


def verify_record(roots: dict, record: dict):
    if record["stage"] in ("AUTHORIZED", "PRODUCING", "EVIDENCE_READY", "COMPLETE"):
        register_path = confined(roots["game"], "design/product/PRODUCT_AUTHORITY_REGISTER.json")
        if register_path.exists() and read_json(register_path).get("status") != "ACTIVE":
            fail("NO_ACTIVE_PRODUCT_AUTHORITY", "archived or unknown product cannot authorize production")
    for ref in record["artifacts"]:
        resolve_ref(roots, ref)
    if not record.get("design"):
        if record["stage"] != "DRAFT":
            fail("INVALID_CHECKPOINT", "non-draft work requires complete design")
        return
    d = load_design(roots, record["design"])
    current = dependencies(roots, record["design"], d)
    if current != record["dependencies"]:
        fail("REVALIDATION_REQUIRED", "relevant dependencies changed; preserve old checkpoint, re-review new design")
    if STAGES.index(record["stage"]) >= STAGES.index("REVIEWED"):
        check_reviews(roots, record["design"], d, current, record["reviews"])
    if STAGES.index(record["stage"]) >= STAGES.index("AUTHORIZED"):
        check_ruling(roots, record["ruling"], record["design"], current)
    for ref in record["artifacts"]:
        resolve_ref(roots, ref)
    if record["stage"] == "COMPLETE":
        # The owning specialist validated admission before publication. Future
        # reads verify its immutable reference without recursively admitting it.
        expand_references(roots, [record["acceptance"]])


def checkpoint(roots: dict, request: dict) -> dict:
    keys(request, {"task_id", "previous", "capability", "task", "stage", "summary", "unresolved", "artifacts"},
         {"design", "reviews", "ruling", "acceptance"})
    task_id = identifier(request["task_id"])
    stage = request["stage"]
    if stage not in STAGES or request["capability"] not in CAPABILITIES:
        fail("INVALID_CHECKPOINT", "unknown stage/capability")
    text(request["summary"])
    texts(request["unresolved"])
    game = roots["game"]
    project(game)
    with project_lock(game):
        previous, previous_digest = latest(game, task_id)
        if request["previous"] != previous_digest:
            fail("CONCURRENT_WRITE", "checkpoint predecessor changed")
        if previous:
            if any(request[k] != previous[k] for k in ("capability", "task")):
                fail("INVALID_TRANSITION", "task identity cannot change inside a ledger")
            index = STAGES.index(previous["stage"])
            if stage != "DRAFT" and STAGES.index(stage) not in (index, index + 1):
                fail("INVALID_TRANSITION", "advance one verified boundary at a time")
        elif stage not in ("DRAFT", "DESIGN_COMPLETE"):
            fail("INVALID_TRANSITION", "new task starts as draft or complete design, never approved work")
        record = {"schema_version": "factory_checkpoint.v2", **request,
                  "generation": (previous["generation"] + 1) if previous else 1,
                  "factory_revision": revision(roots["factory"]), "dependencies": None,
                  "design": request.get("design"), "reviews": request.get("reviews", []),
                  "ruling": request.get("ruling"), "acceptance": request.get("acceptance")}
        if stage != "DRAFT" and not record["design"]:
            fail("DESIGN_REQUIRED", "complete design reference required")
        if record["design"]:
            d = load_design(roots, record["design"])
            if d["capability"] != request["capability"] or d["task"] != request["task"]:
                fail("INVALID_DESIGN", "design belongs to another capability/task")
            record["dependencies"] = dependencies(roots, record["design"], d)
            if stage != "DRAFT" and previous and previous["stage"] != "DRAFT" and previous.get("design") != record["design"]:
                fail("INVALID_TRANSITION", "changed design must restart at DRAFT before review")
        if stage in ("AUTHORIZED", "PRODUCING", "EVIDENCE_READY", "COMPLETE") and request["unresolved"]:
            fail("UNRESOLVED_BLOCKERS", "resolve blockers before production")
        if previous and previous["stage"] == "COMPLETE":
            fail("TERMINAL_CHECKPOINT", "accepted task is immutable history; create a new task for new work")
        if not isinstance(request["artifacts"], list):
            fail("INVALID_CHECKPOINT", "artifacts must be references")
        for ref in request["artifacts"]:
            resolve_ref(roots, ref)
        if stage == "EVIDENCE_READY" and not request["artifacts"]:
            fail("EVIDENCE_REQUIRED", "exact produced output/evidence references required")
        verify_record(roots, record)
        if stage == "COMPLETE":
            from .acceptance import validate
            validate(roots, record, d, record["acceptance"])
        path = f"design/factory/checkpoints/{task_id}/{record['generation']:06d}.json"
        # Recheck all reads immediately before commit while holding writer lock.
        verify_record(roots, record)
        exclusive_json(confined(game, path), record)
        return {"status": "CHECKPOINT_SAVED", "checkpoint": reference(game, path),
                "stage": stage, "dependency_fingerprint": (record["dependencies"] or {}).get("fingerprint"),
                "delivery_eligible": False}
