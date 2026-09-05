"""Factory v2 acceptance bridge; existing runtime/human/regression gates remain."""
from __future__ import annotations

from pathlib import Path

from factory_core.refs import FactoryError, fail, read_json, resolve_ref
from factory_core.state import keys, project, texts
from gameplay.v2 import authorized_objective, legacy, validate_design

VERSION = "factory_gameplay_acceptance_input.v2"


def validate_acceptance_input(game: Path, payload: dict, *, project_id: str, unit_id: str,
                              game_revision: str, build_id: str, factory_revision: str,
                              authority_ref: dict, product_authority_ref: dict,
                              production_context_ids: set, acceptance_reviewer_context_id: str,
                              errors: list) -> dict:
    from studio.baseline import _validate_two_lap_cycle_observation
    from studio.player_surface import validate_runtime_player_surface_chain
    roots = {"game": game, "factory": Path(__file__).resolve().parents[1]}
    empty = {"schema_version": VERSION, "studio_gameplay_system": {"path": "", "sha256": ""},
             "cycle_id": "", "feedback_state_ids": [], "player_facing_evidence": {}}
    try:
        keys(payload, {"schema_version", "project_id", "unit_id", "game_revision", "build_id", "factory_revision",
                       "checkpoint", "experience_authority", "studio_gameplay_system", "cycle_id",
                       "cycle_acceptance", "player_facing_evidence", "playtest_questions", "non_claims"})
        for field, expected in (("schema_version", VERSION), ("project_id", project_id), ("unit_id", unit_id),
                                ("game_revision", game_revision), ("build_id", build_id), ("factory_revision", factory_revision),
                                ("experience_authority", authority_ref)):
            if payload[field] != expected:
                fail("ACCEPTANCE_IDENTITY_MISMATCH", field)
        if project(roots["game"])["project_id"] != project_id:
            fail("WRONG_PROJECT", "acceptance belongs to another project")
        record, design = authorized_objective(roots, payload["checkpoint"], authority_ref["path"], authority_ref["sha256"])
        if record["stage"] != "EVIDENCE_READY":
            fail("EVIDENCE_REQUIRED", "acceptance requires exact-output evidence checkpoint")
        if design["gameplay"]["routing"] != "STUDIO_WHOLE_GAME":
            fail("WRONG_ROUTING", "whole-game baseline requires a Studio design")
        validated = validate_design(roots, design)
        system = validated["system"]
        contract = validated["contract"]
        domain = design["gameplay"]
        if system["product_authority"] != product_authority_ref:
            fail("WRONG_PRODUCT", "admission must bind the active design's product")
        if payload["studio_gameplay_system"] != legacy(domain["system"]) or payload["cycle_id"] != system["cycle_id"]:
            fail("WRONG_SYSTEM", "acceptance must bind exact reviewed graph")
        questions, nonclaims = texts(payload["playtest_questions"]), texts(payload["non_claims"])
        if not questions or not nonclaims:
            fail("ACCEPTANCE_INCOMPLETE", "playtest questions and non-claims required")
        feedback = list(system["_validated"]["feedback_state_ids"])
        _validate_two_lap_cycle_observation(payload["cycle_acceptance"], "v2 cycle acceptance", set(feedback), errors)
        reviews = [read_json(resolve_ref(roots, ref)) for ref in record["reviews"]]
        design_contexts = {design["author_context_id"], *(r["reviewer_context_id"] for r in reviews)}
        if acceptance_reviewer_context_id in design_contexts | production_context_ids:
            fail("REVIEW_NOT_INDEPENDENT", "runtime acceptance reviewer cannot author/review design or produce")
        intent_ref = next(ref for ref, review in zip(record["reviews"], reviews) if review["role"] == "intent_experience")
        evidence_refs = {tuple(sorted(ref.items())) for ref in record["artifacts"]}
        for ref in payload["player_facing_evidence"].values():
            current = {"scope": "game", **ref}
            if tuple(sorted(current.items())) not in evidence_refs:
                fail("EVIDENCE_MISMATCH", "runtime chain must be in the exact evidence checkpoint")
        chain = validate_runtime_player_surface_chain(game, payload["player_facing_evidence"],
            project_id=project_id, unit_id=unit_id, game_revision=game_revision, build_id=build_id,
            factory_revision=factory_revision, expected_contract_ref=legacy(domain["interaction_contract"]),
            expected_contract_review_ref=legacy(intent_ref), expected_card_ref=legacy(record["design"]),
            expected_system_ref=legacy(domain["system"]), expected_beat_ids=contract["beat_ids"],
            expected_answer_bearing_design_ids=contract["answer_bearing_design_ids"],
            expected_target_locale=contract["target_locale"], expected_player_entry_knowledge=contract["player_entry_knowledge"],
            hypothesis_ids=set(domain["hypothesis_ids"]), design_context_ids=design_contexts,
            production_context_ids=production_context_ids,
            acceptance_reviewer_context_id=acceptance_reviewer_context_id, errors=errors)
        return {"schema_version": VERSION, "studio_gameplay_system": legacy(domain["system"]),
                "cycle_id": system["cycle_id"], "feedback_state_ids": feedback,
                "player_facing_evidence": {key: chain[key] for key in payload["player_facing_evidence"]}}
    except FactoryError as exc:
        errors.append(f"{exc.code}: {exc}")
        return empty
