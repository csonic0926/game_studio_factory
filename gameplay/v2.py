"""Versioned bridge: reuse domain checks, replace only v1 process choreography."""
from __future__ import annotations

from pathlib import Path

from factory_core.refs import fail, read_json, resolve_ref


def legacy(ref):
    return {"path": ref["path"], "sha256": ref["sha256"]}


def validate_design(roots: dict, d: dict):
    from factory_core.state import keys, project
    from gameplay.project_card_standard import validate_project_standard, validate_composition_artifacts
    from studio.cycle import _validate_system
    from studio.player_surface import validate_interaction_contract

    domain = d.get("gameplay")
    if domain is None:
        fail("GAMEPLAY_DESIGN_REQUIRED", "cycle, player-surface and adopted project standard are mandatory")
    keys(domain, {"objective_id", "objective", "system", "interaction_contract", "project_standard", "composition_artifacts", "routing", "hypothesis_ids", "material_coverage"})
    for name in ("objective", "system", "interaction_contract"):
        if domain[name] not in d["artifacts"]:
            fail("GAMEPLAY_DESIGN_REQUIRED", f"{name} must be a reviewed complete-design artifact")
    from factory_core.state import texts
    texts(domain["hypothesis_ids"])
    repo = roots["game"]
    pid = project(repo)["project_id"]
    system_path = resolve_ref(roots, domain["system"])
    system_payload = read_json(system_path)
    provenance = system_payload.get("factory_revision", "")
    errors = []
    from gameplay.design_gate import _extract_material_spec
    material, author = _extract_material_spec(resolve_ref(roots, domain["objective"]).read_text(), errors)
    if author != d["author_context_id"]:
        errors.append("objective and complete design must identify the same continuing author")
    coverage = domain["material_coverage"]
    if not isinstance(coverage, dict) or set(coverage) != set(material):
        errors.append("human decision view must cover every material full-spec statement")
    else:
        decisions = {item["id"]:item for item in d["decisions"]}
        for name, ids in coverage.items():
            if not isinstance(ids, list) or not ids or any(i not in decisions for i in ids):
                errors.append(f"unknown/missing Card projection for {name}")
                continue
            if not any(material[name] in decisions[i]["excerpt"] or material[name] in decisions[i]["consequence"] for i in ids):
                errors.append(f"human view omits material statement {name}")
    system = _validate_system(repo, system_path, factory_revision=provenance, errors=errors)
    if system.get("project_id") != pid:
        errors.append("gameplay system belongs to another project")
    if system.get("author_context_id") != d["author_context_id"]:
        errors.append("complete design and system must identify the continuing primary author")
    # The system's graph schema is retained. Its Git revision remains internal
    # provenance consistency, not a v2 comparison against today's HEAD.
    contract = validate_interaction_contract(repo, legacy(domain["interaction_contract"]),
        project_id=pid, objective_id=domain["objective_id"], factory_revision=provenance,
        product_authority=system_payload.get("product_authority", {}),
        studio_gameplay_system=legacy(domain["system"]),
        expected_transition_ids=[t["transition_id"] for t in system_payload.get("transitions", [])], errors=errors)
    standard = validate_project_standard(repo, domain["project_standard"], project_id=pid,
        routing=domain["routing"], errors=errors)
    compositions = validate_composition_artifacts(repo, domain["composition_artifacts"],
        standard_binding=standard, errors=errors)
    refs = {(r["path"], r["sha256"]) for r in d["artifacts"] + d["inputs"]}
    required_paths = [domain["project_standard"], *domain["composition_artifacts"]]
    for ref in required_paths:
        # Composition records are existing schema objects; refs live directly
        # on them. Required content must be present in the sealed design set.
        if (ref.get("path"), ref.get("sha256")) not in refs:
            errors.append("project standard/composition must be included in reviewed artifacts or inputs")
    required = standard.get("requirement_ids", [])
    if set(required) - set(d["requirements"]):
        errors.append("complete design requirement map omits adopted project requirements")
    if errors:
        fail("GAMEPLAY_DESIGN_INVALID", "; ".join(errors))
    return {"system": system, "contract": contract, "standard": standard, "compositions": compositions}


def authorized_objective(roots: dict, checkpoint_ref: dict, objective_path: str, objective_sha: str):
    from factory_core.state import latest, load_design, verify_record
    from factory_core.refs import sha
    record_path = resolve_ref(roots, checkpoint_ref)
    record = read_json(record_path)
    current, current_sha = latest(roots["game"], record["task_id"])
    sealed_by_completion = bool(current and current.get("stage") == "COMPLETE" and
        current.get("previous") == sha(record_path) and current.get("design") == record.get("design"))
    if (current_sha != sha(record_path) and not sealed_by_completion) or record["stage"] not in ("AUTHORIZED", "PRODUCING", "EVIDENCE_READY"):
        fail("HUMAN_RULING_REQUIRED", "production requires the current authorized checkpoint, not superseded history")
    verify_record(roots, record)
    d = load_design(roots, record["design"])
    expected = {"scope": "game", "path": objective_path, "sha256": objective_sha}
    if d.get("gameplay", {}).get("objective") != expected:
        fail("WRONG_OBJECTIVE", "production plan objective differs from approved complete design")
    return record, d
