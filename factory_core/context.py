"""Read-only diagnostics and role-specific, reconstructible context views."""
from __future__ import annotations

from pathlib import Path

from .catalog import DOCS, authority_refs, method_paths
from .migration import inventory
from .refs import FactoryError, confined, fail, read_json, reference, resolve_ref, expand_references
from .state import (PROJECT_PATH, ROLES, STAGES, dependencies, latest, load_design,
                    project, requirement_ids, verify_record)


def source_view(roots,ref):
    path=resolve_ref(roots,ref)
    # Visual/audio references remain exact first-class dependencies. Never try
    # to decode a PNG/WAV as prose or silently omit its review obligation.
    if path.suffix.lower() in (".md",".txt",".json",".jsonl",".csv",".tsv",".yaml",".yml",".gd",".py",".tscn",".tres"):
        return {"reference":ref,"text":path.read_text(encoding="utf-8")}
    import mimetypes
    return {"reference":ref,"kind":"binary_source","media_type":mimetypes.guess_type(ref["path"])[0] or "application/octet-stream",
            "bytes":len(path.read_bytes()),"required_action":"Inspect with the owning visual/audio/document tool before judging this dependency; this metadata is not a substitute for its content."}


def inspect(roots: dict, task_id: str | None = None) -> dict:
    game = roots["game"]
    history = inventory(game)
    result = {"schema_version": "factory_inspection.v2", "workflow_version": None,
              "status": "MIGRATION_REQUIRED", "blockers": [], "next_action": "migrate --check",
              "history": history, "delivery_eligible": False}
    try:
        p = project(game)
        result["workflow_version"] = p["workflow_version"]
        result["project_id"] = p["project_id"]
        result["status"], result["next_action"] = "PROJECT_READY", "context"
        register_path = confined(game, "design/product/PRODUCT_AUTHORITY_REGISTER.json")
        if register_path.exists():
            status = read_json(register_path).get("status")
            if status == "NO_ACTIVE_PRODUCT_AUTHORITY":
                result["status"], result["next_action"] = status, "idea exploration"
            elif status != "ACTIVE":
                fail("UNKNOWN_AUTHORITY_STATE", "unsupported product lifecycle state")
            else:
                expand_references(roots,[reference(game,"design/product/PRODUCT_AUTHORITY_REGISTER.json")])
        task_ids = [task_id] if task_id else sorted(p.name for p in (game / "design/factory/checkpoints").glob("*") if p.is_dir())
        tasks = []
        for identity in task_ids:
            record, predecessor = latest(game, identity)
            if record:
                item = {"task_id": identity, "stage": record["stage"], "previous": predecessor,
                        "summary": record["summary"], "unresolved": record["unresolved"]}
                try:
                    verify_record(roots, record)
                    item["status"] = "CURRENT_CHECKPOINT"
                    item["next_action"] = {"DRAFT": "continue authoring", "DESIGN_COMPLETE": "independent boundary reviews",
                        "REVIEWED": "exact human ruling", "AUTHORIZED": "production within frozen scope",
                        "PRODUCING": "collect exact-output evidence", "EVIDENCE_READY": "specialist acceptance",
                        "COMPLETE": "inspect specialist acceptance"}[record["stage"]]
                except FactoryError as exc:
                    item["status"], item["next_action"] = exc.code, "revalidate; do not rehash old reviews"
                    result["blockers"].append({"code": exc.code, "message": str(exc), "task_id": identity})
                tasks.append(item)
        result["tasks"] = tasks
        if task_id and not tasks:
            result["next_action"] = "context; checkpoint a new draft"
        elif task_id and tasks:
            result["next_action"] = tasks[0]["next_action"]
        if result["blockers"]:
            result["status"] = "REVALIDATION_REQUIRED"
    except FactoryError as exc:
        result["status"] = exc.code
        result["blockers"].append({"code": exc.code, "message": str(exc)})
    return result


def context(roots: dict, capability: str, task: str, role="author", task_id=None, design=None) -> dict:
    # Never return inspect/history, expected answers, source paths or checkpoint
    # summaries to a blind observer. Existing player_surface protocol owns its
    # separately sanitized/attested packet and sealed comparison.
    if role == "blind_observer":
        fail("BLIND_CONTEXT_REQUIRES_SANITIZED_PROTOCOL",
             "use studio player-surface Phase A; generic project context is forbidden")
    if role not in ("author", "human", *ROLES):
        fail("UNKNOWN_ROLE", role)
    game, factory = roots["game"], roots["factory"]
    p = project(game)
    record, previous = latest(game, task_id) if task_id else (None, None)
    if design is None and record:
        design = record["design"]
    result = {"schema_version": "factory_context.v2", "role": role, "authority": False,
              "capability": capability, "task": task,
              "constraints": [], "methods": method_paths(factory, capability, task)}
    contracts=["design.schema.json","checkpoint_request.schema.json","review.schema.json","ruling.schema.json"]
    if capability=="story":contracts.append("story_output_acceptance.schema.json")
    result["contracts"]=[reference(factory,"factory_core/schemas/"+name,"factory") for name in contracts]
    refs = authority_refs(game, capability, p["authority_paths"])
    refs += [reference(factory, name, "factory") for name in ["factory_core/docs/WORKFLOW.md", *DOCS[capability]]]
    for ref in refs:
        result["constraints"].append(source_view(roots,ref))
    if role == "author":
        result["work"] = ({k: record[k] for k in ("stage", "summary", "unresolved", "artifacts")} if record else None)
        result["previous"] = previous
    if design:
        d = load_design(roots, design)
        if (d["capability"], d["task"]) != (capability, task):
            fail("WRONG_TASK", "design capability/task mismatch")
        binding = dependencies(roots, design, d)
        result.update(design=design, dependency_fingerprint=binding["fingerprint"],
                      source_references=[r for r in binding["references"] if r["scope"] != "factory"], decisions=d["decisions"])
        result["design_artifacts"] = [source_view(roots,ref) for ref in d["artifacts"] + d["inputs"]]
        if role in ROLES:
            result["review_requirements"] = sorted(requirement_ids(factory, d, role))
            rules = read_json(factory / "factory_core/rule_map.json")["rules"]
            source_paths = sorted({r["source"] for r in rules if r["id"] in result["review_requirements"]})
            result["review_sources"] = [reference(factory, p, "factory") for p in source_paths]
            result["review_rule"] = "Fresh non-author first pass; do not read any peer review. Review the entire exact design, not author-selected claims."
        if role == "human":
            from .state import check_reviews, approval_action
            if not record or record["stage"] not in STAGES[STAGES.index("REVIEWED"):]:
                fail("REVIEW_REQUIRED", "human Card is a checked projection after both reviews")
            check_reviews(roots, design, d, binding, record["reviews"])
            # The human view references the full reviewed design; its decision
            # surface consists only of exact excerpts, never a second spec.
            result.pop("design_artifacts")
            result.pop("constraints")
            result["design_link"] = design
            result["status"] = "PENDING_HUMAN_RULING"
            result["approval_action"] = approval_action(design, binding)
    elif role != "author":
        fail("DESIGN_REQUIRED", "review and human roles need an exact complete design")
    return result


def provider_result(roots: dict, path: str) -> dict:
    """Read existing provider status, without running/replacing its pipeline."""
    source = confined(roots["game"], path)
    data = read_json(source)
    deliverables = []
    ok = data.get("ok") is True
    stage = data.get("stage", data.get("status", "UNKNOWN"))
    if isinstance(data.get("variants"), dict) and data["variants"]:
        variants = data["variants"]
        ok = all(v.get("validation", {}).get("status") == "pass" and
                 v.get("deliverable", {}).get("status") == "ok" for v in variants.values())
        deliverables = [v.get("deliverable", {}).get("primary_artifact") for v in variants.values()]
        stage = "done" if ok else "validation_or_delivery_incomplete"
    elif data.get("deliverable"):
        deliverables = [data["deliverable"]]
    refs = []
    for deliverable in deliverables:
        if not isinstance(deliverable, str):
            fail("INVALID_PROVIDER_RESULT", "deliverable must name a file")
        candidate = Path(deliverable)
        if candidate.is_absolute():
            if not candidate.resolve().is_relative_to(roots["game"].resolve()):
                fail("UNSAFE_PATH", "provider deliverable lies outside game root")
            relative = candidate.resolve().relative_to(roots["game"].resolve()).as_posix()
        else:
            relative = (Path(path).parent / candidate).as_posix()
        refs.append(reference(roots["game"], relative))
    return {"source": reference(roots["game"], path), "ok": bool(ok and refs),
            "stage": stage, "deliverables": refs,
            "errors": data.get("errors", data.get("error", [])),
            "acceptance": "TECHNICAL_PROVIDER_RESULT_NOT_GAMEPLAY_ACCEPTANCE"}
