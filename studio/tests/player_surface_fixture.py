from __future__ import annotations

import hashlib
import json
from pathlib import Path

from studio.player_surface import CONTRACT_REQUIREMENTS


def write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def ref(repo: Path, path: Path | str) -> dict[str, str]:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = repo / candidate
    return {
        "path": candidate.resolve().relative_to(repo.resolve()).as_posix(),
        "sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
    }


def write_contract_pair(
    repo: Path,
    objective_dir: Path,
    *,
    project_id: str,
    objective_id: str,
    factory_revision: str,
    product_ref: dict[str, str],
    system_ref: dict[str, str],
    transition_ids: list[str],
) -> tuple[dict[str, str], dict[str, str], list[str]]:
    locale = objective_dir / "evidence/current-scene-readable.png"
    locale.parent.mkdir(parents=True, exist_ok=True)
    locale.write_bytes(b"readable localized frame\n")
    beat_ids = [f"beat.{transition_id}" for transition_id in transition_ids]
    beats = []
    for beat_id, transition_id in zip(beat_ids, transition_ids):
        beats.append({
            "beat_id": beat_id,
            "system_transition_ids": [transition_id],
            "entry_screen_state": "The changed object and route are visible in the current scene.",
            "player_prior_knowledge": "The player knows only the controls and the visible situation.",
            "perceivable_cause": "A character points at a physically changed object in the world.",
            "visible_goal": "Restore the object so the blocked route visibly opens.",
            "available_input": {"input_kind": "MANIPULATION", "control": "press action beside the object", "affordance_cue": "the object highlights when in reach"},
            "required_judgment": "Choose when and where to commit the repair resource.",
            "interaction_sequence": [{
                "step_id": f"step.{transition_id}", "input_kind": "MANIPULATION",
                "control": "press action beside the object", "player_intent": "repair the visible break",
                "visible_response": "the object moves into place and the character steps through",
                "response_channels": ["WORLD_OBJECT", "CHARACTER"], "counts_as_player_work": True,
            }],
            "immediate_visible_response": "The object animates into place and the character crosses.",
            "persistent_visible_change": "On return the repaired object remains in place and the route stays open.",
            "next_affordance": {"description": "The open route and waiting character expose the changed next action.", "discovery_channels": ["WORLD_OBJECT", "CHARACTER"]},
            "allowed_text_support": {"role": "SUPPORT_ONLY", "text_can_complete_action": False, "description": "A short line may name the object but cannot perform the repair."},
            "forbidden_proxy_check": {"proxy_only": False, "disallowed_proxies": ["POPUP_ONLY", "JOURNAL_ONLY", "MARKER_ONLY", "HIDDEN_FLAG_ONLY", "STRAIGHT_TRAVERSAL_ONLY", "DIALOGUE_ADVANCE_ONLY"], "explanation": "Only manipulating the object produces the visible world and character response."},
            "player_surface_evidence_plan": {"scenario_id": f"scenario.{transition_id}", "start_state": "clean save before the visible break", "ordered_capture_moments": ["BEFORE_INPUT", "DURING_INTERACTION", "AFTER_RESPONSE", "RETURNED_CHANGED_AFFORDANCE"]},
        })
    contract_path = objective_dir / "PLAYER_FACING_INTERACTION_CONTRACT.json"
    current_scene_composition = []
    sequence = 0
    for beat_id in beat_ids:
        for surface_moment in (
            "ENTRY", "AFFORDANCE", "EXPECTED_RESPONSE", "PERSISTENT_RETURN"
        ):
            sequence += 1
            visual = objective_dir / f"evidence/current-scene-{sequence}.png"
            visual.write_bytes(
                f"{beat_id} {surface_moment} current scene frame\n".encode("utf-8")
            )
            current_scene_composition.append(
                {
                    "sequence": sequence,
                    "beat_id": beat_id,
                    "surface_moment": surface_moment,
                    "artifact_type": "ANNOTATED_CURRENT_SCENE_FRAME",
                    "artifact": ref(repo, visual),
                }
            )
    contract = {
        "schema_version": "player_facing_interaction_contract.v1", "contract_id": f"{objective_id}.player-surface.v1",
        "project_id": project_id, "objective_id": objective_id, "factory_revision": factory_revision,
        "product_authority": product_ref, "studio_gameplay_system": system_ref,
        "author_context_id": "surface-contract-author", "target_player": "A first-time player using only ordinary controls", "target_locale": "en",
        "player_entry_knowledge": [
            "The player knows the ordinary movement and action controls.",
            "The player has not received an explanation of the intended solution.",
        ],
        "current_scene_composition": current_scene_composition,
        "localization_readability": {"locale": "en", "readability_status": "VERIFIED_READABLE", "fallback_used": False, "garbled_text_present": False, "evidence": [{"artifact_type": "ANNOTATED_CURRENT_SCENE_FRAME", "artifact": ref(repo, locale)}]},
        "playable_beats": beats, "design_status": "TESTABLE_DESIGN", "authored_at": "2026-09-04T09:00:00Z",
    }
    write_json(contract_path, contract)
    contract_ref = ref(repo, contract_path)
    review_path = objective_dir / "PLAYER_FACING_INTERACTION_CONTRACT_REVIEW.json"
    review = {
        "schema_version": "player_facing_interaction_contract_review.v1", "review_id": f"{objective_id}.surface-review.v1", "review_role": "PLAYER_FACING_INTERACTION_DESIGN_REVIEW",
        "project_id": project_id, "objective_id": objective_id, "factory_revision": factory_revision,
        "interaction_contract": contract_ref, "product_authority": product_ref, "studio_gameplay_system": system_ref,
        "reviewer_context_id": "surface-contract-reviewer", "reviewer_freshness": "FRESH", "hypothesis_lifecycle": "TESTABLE_DESIGN_ONLY",
        "requirement_findings": {name: {"verdict": "PASS", "beat_ids": beat_ids, "rationale": f"Every beat concretely satisfies {name}."} for name in CONTRACT_REQUIREMENTS},
        "beat_findings": [{"beat_id": beat_id, "verdict": "PASS_TESTABLE_DESIGN", "rationale": "The sequence exposes cause, work, response, persistence, and next affordance."} for beat_id in beat_ids],
        "blocking_findings": [], "verdict": "PASS_PLAYER_FACING_INTERACTION_DESIGN", "reviewed_at": "2026-09-04T09:05:00Z",
    }
    write_json(review_path, review)
    return contract_ref, ref(repo, review_path), beat_ids


def write_runtime_chain(
    repo: Path,
    admission_dir: Path,
    *,
    project_id: str,
    unit_id: str,
    game_revision: str,
    build_id: str,
    factory_revision: str,
    contract_ref: dict[str, str],
    contract_review_ref: dict[str, str],
    card_ref: dict[str, str],
    system_ref: dict[str, str],
    beat_ids: list[str],
    hypothesis_ids: list[str],
) -> dict[str, dict[str, str]]:
    evidence_dir = admission_dir / "player_surface"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    paths = {}
    for name, content in {
        "returned.png": b"returned\n",
        "input-trace.jsonl": b'{"input":"action"}\n', "structure.json": b'{"visible":true}\n',
    }.items():
        path = evidence_dir / name
        path.write_bytes(content)
        paths[name] = path
    clean_start = {"save_identity": f"clean-{unit_id}", "save_state": "CLEAN_START", "start_state": "fresh objective entry"}
    trace = []
    changes = []
    trace_paths_by_sequence: dict[int, dict[str, Path]] = {}
    for sequence, beat_id in enumerate(beat_ids, 1):
        sequence_paths: dict[str, Path] = {}
        for moment in ("before", "during", "after"):
            path = evidence_dir / f"{moment}-{sequence}.png"
            path.write_bytes(f"{beat_id} {moment}\n".encode("utf-8"))
            sequence_paths[moment] = path
        trace_paths_by_sequence[sequence] = sequence_paths
        trace.append({"sequence": sequence, "beat_id": beat_id, "input_kind": "MANIPULATION", "control": "press action beside the object", "player_intent": "repair the visible break", "frame_before": ref(repo, sequence_paths["before"]), "frame_during": ref(repo, sequence_paths["during"]), "frame_after": ref(repo, sequence_paths["after"]), "observed_response": "The object moved and the character crossed."})
        changes.append({"beat_id": beat_id, "before": "Object broken and route closed.", "after": "Object repaired and route open.", "response_channels": ["WORLD_OBJECT", "CHARACTER"]})
    runtime_path = admission_dir / "PLAYER_FACING_RUNTIME_INTERACTION_EVIDENCE.json"
    runtime = {
        "schema_version": "player_facing_runtime_interaction_evidence.v1", "evidence_id": f"{unit_id}.runtime-surface.v1",
        "project_id": project_id, "unit_id": unit_id, "game_revision": game_revision, "build_id": build_id, "factory_revision": factory_revision,
        "interaction_contract": contract_ref, "producer_context_id": "runtime-capture-context", "clean_start": clean_start,
        "scenario_entry_state": "The broken object and waiting character are visible.",
        "capture_environment": {"engine": "Godot", "window_mode": "WINDOWED", "rendering_mode": "IN_ENGINE"},
        "ordered_input_trace": trace,
        "structural_evidence": {"status": "CAPTURED", "evidence": [{"artifact_type": "STRUCTURAL_UI", "artifact": ref(repo, paths["structure.json"])}], "rationale": "The capture confirms the interactive object is visible and enabled."},
        "observable_changes": changes,
        "returned_surface": {"frame": ref(repo, paths["returned.png"]), "visible_next_affordance": "The open route leads to the waiting character's next task.", "discovery_channels": ["WORLD_OBJECT", "CHARACTER"]},
        "localization_observation": {"locale": "en", "status": "OBSERVED_READABLE", "fallback_used": False, "garbled_text_present": False, "evidence": [{"artifact_type": "FRAME_AFTER", "artifact": ref(repo, trace_paths_by_sequence[len(beat_ids)]["after"])}]},
        "evidence_files": [
            {"artifact_type": "INPUT_TRACE", "artifact": ref(repo, paths["input-trace.jsonl"])},
            *[
                {
                    "artifact_type": f"FRAME_{moment.upper()}",
                    "artifact": ref(repo, trace_paths_by_sequence[sequence][moment]),
                }
                for sequence in range(1, len(beat_ids) + 1)
                for moment in ("before", "during", "after")
            ],
        ], "captured_at": "2026-09-04T10:00:00Z",
    }
    write_json(runtime_path, runtime)
    runtime_ref = ref(repo, runtime_path)
    blind_input_path = admission_dir / "PLAYER_FACING_BLIND_OBSERVATION_INPUT.json"
    blind_input = {
        "schema_version": "player_facing_blind_observation_input.v1", "observation_input_id": f"{unit_id}.blind-input.v1",
        "project_id": project_id, "unit_id": unit_id, "game_revision": game_revision, "build_id": build_id,
        "clean_start": clean_start, "scenario_entry_state": runtime["scenario_entry_state"],
        "player_prior_knowledge": [
            "The player knows the ordinary movement and action controls.",
            "The player has not received an explanation of the intended solution.",
        ],
        "normal_controls": ["move", "action"],
        "surface_artifacts": [
            *[
                {
                    "artifact_type": "SCREEN_FRAME",
                    "artifact": ref(repo, trace_paths_by_sequence[sequence][moment]),
                }
                for sequence in range(1, len(beat_ids) + 1)
                for moment in ("before", "during", "after")
            ],
            {"artifact_type": "SCREEN_FRAME", "artifact": ref(repo, paths["returned.png"])},
        ],
        "context_policy": {"authority_access": "FORBIDDEN_BEFORE_OBSERVATION", "allowed_materials": "PLAYER_SURFACE_ONLY"},
        "preparation_attestation": {
            "preparer_context_id": "blind-input-preparer",
            "answer_bearing_design_ids_removed": True,
            "intended_answers_removed": True,
            "future_beat_knowledge_removed": True,
            "only_phase_a_allowed_materials_present": True,
        },
        "prepared_at": "2026-09-04T10:05:00Z",
    }
    write_json(blind_input_path, blind_input)
    blind_input_ref = ref(repo, blind_input_path)
    blind_path = admission_dir / "PLAYER_FACING_BLIND_OBSERVATION.json"
    blind = {
        "schema_version": "player_facing_blind_observation.v1", "observation_id": f"{unit_id}.blind.v1",
        "project_id": project_id, "unit_id": unit_id, "game_revision": game_revision, "build_id": build_id, "observation_input": blind_input_ref,
        "reviewer_context_id": "blind-player-observer", "reviewer_freshness": "FRESH",
        "context_attestation": {"design_authority_read_before_observation": False, "author_explanation_received": False, "only_player_surface_materials_used": True},
        "observation": {
            "interaction_observations": [
                {
                    "attempt_id": f"attempt.{sequence}",
                    "sequence": sequence,
                    "surface_artifacts": [
                        ref(repo, trace_paths_by_sequence[sequence]["before"]),
                        ref(repo, trace_paths_by_sequence[sequence]["during"]),
                        ref(repo, trace_paths_by_sequence[sequence]["after"]),
                        *(
                            [ref(repo, paths["returned.png"])]
                            if sequence == len(beat_ids)
                            else []
                        ),
                    ],
                    "cause": "A visibly broken object prevents a waiting character from crossing.",
                    "goal": "Restore the object so the blocked route opens.",
                    "affordance": "The nearby object highlights and accepts the ordinary action control.",
                    "input_and_judgment": "Move beside the object and decide when to press action.",
                    "visible_response": "The object moves into place and the character crosses.",
                    "persistent_change": "The route remains open after the response.",
                    "next_motive": "Follow the character through the opened route.",
                    "localization_readability": "Visible English text is readable without fallback or garbling.",
                }
                for sequence, _beat_id in enumerate(beat_ids, 1)
            ],
            "lost_or_passive_points": [],
        },
        "observed_at": "2026-09-04T10:10:00Z",
    }
    write_json(blind_path, blind)
    blind_ref = ref(repo, blind_path)
    comparison_path = admission_dir / "PLAYER_FACING_COMPARISON_REVIEW.json"
    dimensions = {name: "OBSERVED" for name in ["cause", "goal", "affordance", "input_and_judgment", "visible_response", "persistent_change", "next_motive"]}
    comparison = {
        "schema_version": "player_facing_comparison_review.v1", "review_id": f"{unit_id}.comparison.v1", "review_role": "PLAYER_FACING_AUTHORITY_COMPARISON",
        "project_id": project_id, "unit_id": unit_id, "game_revision": game_revision, "build_id": build_id, "factory_revision": factory_revision,
        "runtime_interaction_evidence": runtime_ref, "blind_observation": blind_ref, "interaction_contract": contract_ref,
        "interaction_contract_review": contract_review_ref, "decision_card": card_ref, "studio_gameplay_system": system_ref,
        "reviewer_context_id": "player-surface-comparison-reviewer", "reviewer_freshness": "FRESH",
        "context_independence": {"blind_record_precedes_authority_access": True, "blind_observer_context_id": "blind-player-observer", "comparison_reviewer_is_distinct": True},
        "beat_comparisons": [{"beat_id": beat_id, "observation_citations": [f"attempt.{index}"], "trace_sequences": [index], **dimensions} for index, beat_id in enumerate(beat_ids, 1)],
        "hypothesis_observations": [{"claim_id": claim_id, "status": "OBSERVED_SUPPORT", "observation_citations": ["attempt.1"], "rationale": "The sealed blind observation records the intended cause, work, and result."} for claim_id in hypothesis_ids],
        "localization_readability": {"status": "OBSERVED_READABLE", "observation_citations": ["attempt.1"]},
        "blocking_findings": [], "verdict": "PASS_PLAYER_FACING_COMPARISON", "reviewed_at": "2026-09-04T10:15:00Z",
    }
    write_json(comparison_path, comparison)
    return {"runtime_interaction_evidence": runtime_ref, "blind_observation_input": blind_input_ref, "blind_observation": blind_ref, "comparison_review": ref(repo, comparison_path)}
