"""Typed, append-only work ledger. A checkpoint is never product authority."""
from __future__ import annotations

from collections import OrderedDict
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
from threading import Lock

from .catalog import authority_refs, factory_dependencies, CAPABILITIES
from .refs import (FactoryError, confined, digest, encoded, exclusive_json, fail,
                   read_json, reference, resolve_ref, revision, sha, unique_refs, expand_references)

PROJECT_PATH = "design/factory/PROJECT.json"
STAGES = ("DRAFT", "DESIGN_COMPLETE", "REVIEWED", "AUTHORIZED", "PRODUCING", "EVIDENCE_READY", "COMPLETE")
ROLES = ("intent_experience", "completeness_project")
ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,95}$")

# Only validated link syntax is memoized, never file identity, the latest record,
# a dependency check, a review/ruling or an authorization decision. Every latest()
# call still enumerates, confines, reads and hashes the entire current chain.
_CHECKPOINT_LINKS = OrderedDict()
_CHECKPOINT_LINK_LOCK = Lock()
_CHECKPOINT_LINK_LIMIT = 4096


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


def project_metadata(game: Path) -> dict:
    """Validate activation metadata without selecting a checkout (relink preflight).

    This grants no task authority. Operational callers must use project().
    """
    path = confined(game, PROJECT_PATH)
    if not path.exists():
        fail("MIGRATION_REQUIRED", "run factory.py migrate --check, then explicit --apply")
    if confined(game, "design/factory/.migration-gpt6.json").exists():
        fail("MIGRATION_RECOVERY_REQUIRED", "finish the prepared GPT-6 transaction before using project state")
    data = read_json(path)
    keys(data, {"schema_version", "workflow_version", "project_id", "factory_revision", "authority_paths", "historical_inventory", "migration_source_digest"})
    if (data["schema_version"], data["workflow_version"]) not in (("factory_project.v2", 2), ("factory_project.v3", 3)):
        fail("MIGRATION_REQUIRED", "unknown project format; no implicit migration")
    identifier(data["project_id"])
    texts(data["authority_paths"])
    return data


def project(game: Path) -> dict:
    data = project_metadata(game)
    if data["workflow_version"] == 3:
        from .astra import check_checkout
        check_checkout(game, Path(__file__).resolve().parents[1])
    return data


def _checkpoint_snapshot(path: Path) -> tuple[bytes, str]:
    try:
        with path.open("rb") as handle:
            before = os.fstat(handle.fileno())
            raw = handle.read()
            after = os.fstat(handle.fileno())
        current = path.stat()
    except OSError as exc:
        fail("INVALID_JSON", f"{path}: {exc}")
    def identity(value):
        return (value.st_dev, value.st_ino, value.st_size,
                value.st_mtime_ns, value.st_ctime_ns)
    if identity(before) != identity(after) or identity(after) != identity(current):
        fail("BROKEN_CHECKPOINT_CHAIN", str(path))
    return raw, hashlib.sha256(raw).hexdigest()


def _checkpoint_record(path: Path, raw: bytes) -> dict:
    try:
        # Preserve refs.read_json's strict UTF-8 and universal newline behavior.
        value = json.loads(raw.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n"))
    except ValueError as exc:
        fail("INVALID_JSON", f"{path}: {exc}")
    if not isinstance(value, dict):
        fail("INVALID_JSON", f"{path}: expected object")
    return value


def latest(game: Path, task_id: str) -> tuple[dict | None, str | None]:
    identifier(task_id)
    game = game.resolve()
    directory = confined(game, f"design/factory/checkpoints/{task_id}")
    paths = sorted(directory.glob("*.json")) if directory.exists() else []
    previous = None
    previous_digest = None
    for generation, path in enumerate(paths, 1):
        confined(game, path.relative_to(game).as_posix())
        raw, current_digest = _checkpoint_snapshot(path)
        with _CHECKPOINT_LINK_LOCK:
            link = _CHECKPOINT_LINKS.get(current_digest)
            if link is not None:
                _CHECKPOINT_LINKS.move_to_end(current_digest)
        record = None
        # A fresh full latest record prevents caller mutations poisoning a cache.
        if link is None or generation == len(paths):
            record = _checkpoint_record(path, raw)
            link = (record.get("generation"), record.get("task_id"),
                    record.get("previous"), record.get("schema_version"))
        if (path.name != f"{generation:06d}.json"
                or link != (generation, task_id, previous_digest, "factory_checkpoint.v2")):
            fail("BROKEN_CHECKPOINT_CHAIN", str(path))
        with _CHECKPOINT_LINK_LOCK:
            _CHECKPOINT_LINKS[current_digest] = link
            _CHECKPOINT_LINKS.move_to_end(current_digest)
            if len(_CHECKPOINT_LINKS) > _CHECKPOINT_LINK_LIMIT:
                _CHECKPOINT_LINKS.popitem(last=False)
        previous, previous_digest = record, current_digest
    return previous, previous_digest


def load_design(roots: dict, ref: dict, *, _legacy_player_text=False) -> dict:
    if ref.get("scope") != "game":
        fail("INVALID_DESIGN", "design must be game-owned")
    d = read_json(resolve_ref(roots, ref))
    keys(d, {"schema_version", "design_id", "capability", "task", "author_context_id", "intent",
             "artifacts", "inputs", "decisions", "requirements", "production_scope", "acceptance"}, {"gameplay", "story", "product", "methods", "decision_sections", "idea_coverage", "rules_check", "ui", "player_text"})
    version = project(roots["game"])["workflow_version"]
    if version == 3 and d['schema_version'] == 'factory_design.v2':
        fail('HISTORICAL_WORKFLOW_REQUIRED', 'v2 work is historical; continue with a new v3 task/design, not rewritten approval')
    if d["schema_version"] != f"factory_design.v{version}" or d["capability"] not in CAPABILITIES:
        fail("INVALID_DESIGN", "unsupported design type/capability")
    if version == 2 and ("methods" in d or "decision_sections" in d or "idea_coverage" in d or "rules_check" in d):
        fail("INVALID_DESIGN", "GPT-6 fields require an explicitly migrated v3 project")
    if version == 3:
        from .astra import selected_methods, validate_sections
        selected_methods(roots["factory"], d["capability"], d["task"], d.get("methods", []))
        validate_sections(roots, d)
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
    if version == 3 or "player_text" in d:
        from player_text.workflow import validate_design as validate_player_text_design
        # Only continuation.audit may select this after verifying the complete
        # pre-feature historical closure. Never invent a reviewed NONE binding.
        # Normal drafts/checkpoints and every explicit binding stay strict.
        if not (_legacy_player_text and version == 3 and "player_text" not in d):
            validate_player_text_design(roots, d)
    if "story" in d:
        if d["capability"] != "story": fail("INVALID_DESIGN", "Story applicability belongs only to Story")
        keys(d["story"], {"spoken_output_paths", "scope_evidence"}, {'runtime_output_paths'} if version == 3 else ())
        spoken = texts(d["story"]["spoken_output_paths"])
        if set(spoken) - set(scope) or d["story"]["scope_evidence"] not in d["artifacts"]:
            fail("INVALID_DESIGN", "dialogue applicability must be bound to the reviewed output scope and a full source artifact")
        if version == 3:
            runtime = texts(d['story'].get('runtime_output_paths'))
            if set(runtime) - set(scope):
                fail('INVALID_DESIGN', 'runtime applicability must be part of reviewed production scope')
            from .story_profile import resolve
            profile = resolve(roots['game'], project(roots['game'])['authority_paths'], roots['factory'])
            if profile['medium'] == 'standalone' and runtime:
                fail('INVALID_DESIGN', 'standalone Story cannot claim engine output; adopt an explicit game adapter first')
    elif version == 3 and d['capability'] == 'story':
        fail('INVALID_DESIGN', 'v3 Story requires explicit spoken/runtime applicability and scope evidence')
    if "product" in d or d["capability"] == "product":
        from product.value import validate_design_binding
        validate_design_binding(roots, d)
    if d["capability"] in ("studio", "gameplay"):
        from gameplay.v2 import validate_design
        validate_design(roots, d)
    if d["capability"] == "ui" or "ui" in d:
        if version != 3:
            fail("INVALID_DESIGN", "the UI design capability requires the explicitly migrated v3 workflow")
        from ui.ui_design import validate_design as validate_ui_design
        validate_ui_design(roots, d)
    if version == 3:
        from idea.inquiry import validate_coverage
        from gameplay.rules_check import validate_design as validate_rules_check
        from .authorship import mode
        current_mode = mode(roots)
        validate_coverage(roots, d, current_mode)
        validate_rules_check(roots, d, current_mode)
    return d


def dependencies(roots: dict, design_ref: dict, d: dict) -> dict:
    p = project(roots["game"])
    refs = [design_ref, reference(roots["game"], PROJECT_PATH)]
    refs += d["inputs"] + d["artifacts"]
    refs += [r["source"] for r in d["requirements"].values()]
    refs += authority_refs(roots["game"], d["capability"], p["authority_paths"])
    if p["workflow_version"] == 3:
        from .authorship import mode_reference
        refs += [ref for ref in [mode_reference(roots["game"])] if ref]
    refs += factory_dependencies(roots["factory"], d["capability"], d["task"], p["workflow_version"], d.get("methods", []))
    refs = expand_references(roots, unique_refs(refs))
    for ref in refs:
        resolve_ref(roots, ref)
    return {"algorithm": "sha256-content-closure.v2", "references": refs, "fingerprint": digest(refs)}


def requirement_ids(factory: Path, d: dict, role: str, mode: str = "COLLABORATIVE",
                    *, historical_factory_revision=None) -> set[str]:
    """Mode-scoped rules (e.g. AUTONOMOUS per-idea inquiry) apply only in their mode."""
    if historical_factory_revision:
        from .refs import GitFile
        rule_map = read_json(GitFile(factory, "factory_core/rule_map.json", historical_factory_revision))
    else:
        rule_map = read_json(factory / "factory_core/rule_map.json")
    return {r["id"] for r in rule_map["rules"] if role in r["reviewers"] and
            ("all" in r["capabilities"] or d["capability"] in r["capabilities"]) and
            int(d["schema_version"].rsplit("v", 1)[1]) in r.get("workflow_versions", (2, 3)) and
            mode in r.get("modes", (mode,))} | set(d["requirements"])


def check_reviews(roots: dict, design_ref: dict, d: dict, binding: dict, refs: list,
                  historical_factory_revision=None):
    if not isinstance(refs, list) or len(refs) != 2:
        fail("REVIEW_REQUIRED", "exactly two independent first-pass boundary reviews required")
    contexts = {d["author_context_id"]}
    roles = set()
    from .authorship import mode
    current_mode = mode(roots) if project(roots["game"])["workflow_version"] == 3 else "COLLABORATIVE"
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
        required = requirement_ids(roots["factory"], d, role, current_mode,
                                   historical_factory_revision=historical_factory_revision)
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
                if historical_factory_revision and source.get('scope') == 'factory':
                    # Only explicit historical-contract verification uses this path.
                    # Ordinary checkpoints never pass this argument or renew old proof.
                    from .refs import GitFile
                    import hashlib
                    raw = GitFile(roots['factory'], source['path'], historical_factory_revision).read_bytes()
                    if hashlib.sha256(raw).hexdigest() != source['sha256']:
                        fail('STALE_DEPENDENCY', 'historical review evidence differs from exact Git bytes')
                else:
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
    if isinstance(ruling, dict) and ruling.get("owner") == "AI_DIRECTOR":
        # CLOSED_BETA: the Director holds the USER's delegated approval seat.
        from .director import check_director_ruling
        check_director_ruling(roots, ruling, design_ref, binding)
        return
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
    ensure_current_task(roots['game'], record['task_id'])
    if record["stage"] in ("AUTHORIZED", "PRODUCING", "EVIDENCE_READY", "COMPLETE"):
        register_path = confined(roots["game"], "design/product/PRODUCT_AUTHORITY_REGISTER.json")
        if register_path.exists() and read_json(register_path).get("status") != "ACTIVE" and not independent_story(roots, record):
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
    if project(roots["game"])["workflow_version"] == 3:
        # The Director's judgment must exist at major boundaries in autonomous modes.
        from .authorship import mode
        from .director import check_checkpoint
        check_checkpoint(roots, record, mode(roots))
        from player_text.workflow import validate_checkpoint as validate_player_text_checkpoint
        validate_player_text_checkpoint(roots, record, d)
        from ui.readiness import validate_checkpoint as validate_ui_checkpoint
        validate_ui_checkpoint(roots, record, d)
    for ref in record["artifacts"]:
        resolve_ref(roots, ref)
    if record["stage"] == "COMPLETE":
        # The owning specialist validated admission before publication. Future
        # reads verify its immutable reference without recursively admitting it.
        expand_references(roots, [record["acceptance"]])


def checkpoint(roots: dict, request: dict) -> dict:
    keys(request, {"task_id", "previous", "capability", "task", "stage", "summary", "unresolved", "artifacts"},
         {"design", "reviews", "ruling", "acceptance", "director_note"})
    task_id = identifier(request["task_id"])
    stage = request["stage"]
    if stage not in STAGES or request["capability"] not in CAPABILITIES:
        fail("INVALID_CHECKPOINT", "unknown stage/capability")
    text(request["summary"])
    texts(request["unresolved"])
    game = roots["game"]
    project(game)
    ensure_current_task(game, task_id)
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
        if record.get("director_note") is None:
            record.pop("director_note", None)
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
        if record.get("design"):
            from ui.readiness import validate_checkpoint as validate_ui_transition
            validate_ui_transition(roots, record, d, new_transition=True)
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


def ensure_current_task(game, task_id):
    if project(game)['workflow_version'] == 3:
        receipt = read_json(confined(game, 'design/factory/ROUTING_RECEIPT.json'))
        if task_id in receipt.get('historical_tasks', []):
            fail('HISTORICAL_WORKFLOW_REQUIRED', 'migration preserves this task as history; create a new task citing it')


def independent_story(roots, record):
    if record['capability'] != 'story' or project(roots['game'])['workflow_version'] != 3:
        return False
    from .story_profile import resolve
    return resolve(roots['game'], project(roots['game'])['authority_paths'], roots['factory'])['medium'] == 'standalone'
