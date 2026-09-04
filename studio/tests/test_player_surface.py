from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from studio.player_surface import (
    validate_interaction_contract,
    validate_interaction_contract_review,
    validate_runtime_player_surface_chain,
)
from studio.tests.player_surface_fixture import ref, write_contract_pair, write_json, write_runtime_chain


class PlayerFacingEvidenceGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name) / "game"
        self.repo.mkdir()
        self.factory_revision = "a" * 40
        self.project_id = "sample-game"
        self.unit_id = "unit-one"
        self.game_revision = "b" * 40
        self.build_id = "build-one"
        product = self.repo / "design/product/PRODUCT_THESIS.md"
        product.parent.mkdir(parents=True)
        product.write_text("# Product\n", encoding="utf-8")
        system = self.repo / "design/studio/gameplay_system/core/STUDIO_GAMEPLAY_SYSTEM_MANIFEST.json"
        write_json(system, {"system": "test"})
        self.product_ref = ref(self.repo, product)
        self.system_ref = ref(self.repo, system)
        self.objective_dir = self.repo / f"design/gameplay/objective_gameplay/{self.unit_id}"
        self.transition_ids = ["repair-bridge", "cross-open-route", "return-loop"]
        self.contract_ref, self.contract_review_ref, self.beat_ids = write_contract_pair(
            self.repo, self.objective_dir, project_id=self.project_id,
            objective_id=self.unit_id, factory_revision=self.factory_revision,
            product_ref=self.product_ref, system_ref=self.system_ref,
            transition_ids=self.transition_ids,
        )
        self.card_path = self.objective_dir / "GAMEPLAY_DECISION_CARD.json"
        write_json(self.card_path, {"schema_version": "gameplay_decision_card.v3"})
        self.card_ref = ref(self.repo, self.card_path)
        self.hypothesis_ids = ["hypothesis.player-understands"]
        self.admission_dir = self.repo / "design/studio/admissions/one"
        self.refs = write_runtime_chain(
            self.repo, self.admission_dir, project_id=self.project_id,
            unit_id=self.unit_id, game_revision=self.game_revision,
            build_id=self.build_id, factory_revision=self.factory_revision,
            contract_ref=self.contract_ref, contract_review_ref=self.contract_review_ref,
            card_ref=self.card_ref, system_ref=self.system_ref, beat_ids=self.beat_ids,
            hypothesis_ids=self.hypothesis_ids,
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def validate_contract(self) -> list[str]:
        errors: list[str] = []
        binding = validate_interaction_contract(
            self.repo, self.contract_ref, project_id=self.project_id,
            objective_id=self.unit_id, factory_revision=self.factory_revision,
            product_authority=self.product_ref, studio_gameplay_system=self.system_ref,
            expected_transition_ids=self.transition_ids, errors=errors,
        )
        validate_interaction_contract_review(
            self.repo, self.contract_review_ref, contract=binding,
            product_authority=self.product_ref, studio_gameplay_system=self.system_ref,
            forbidden_context_ids=set(), errors=errors,
        )
        return errors

    def validate_runtime(self) -> list[str]:
        errors: list[str] = []
        validate_runtime_player_surface_chain(
            self.repo, self.refs, project_id=self.project_id, unit_id=self.unit_id,
            game_revision=self.game_revision, build_id=self.build_id,
            factory_revision=self.factory_revision,
            expected_contract_ref=self.contract_ref,
            expected_contract_review_ref=self.contract_review_ref,
            expected_card_ref=self.card_ref, expected_system_ref=self.system_ref,
            expected_beat_ids=set(self.beat_ids),
            expected_answer_bearing_design_ids={
                *self.beat_ids,
                *self.transition_ids,
                *[f"step.{transition_id}" for transition_id in self.transition_ids],
                *[f"scenario.{transition_id}" for transition_id in self.transition_ids],
            },
            expected_target_locale="en",
            expected_player_entry_knowledge=[
                "The player knows the ordinary movement and action controls.",
                "The player has not received an explanation of the intended solution.",
            ],
            hypothesis_ids=set(self.hypothesis_ids),
            design_context_ids={
                "surface-contract-author",
                "surface-contract-reviewer",
                "final-card-reviewer",
            },
            production_context_ids={"production-author"},
            acceptance_reviewer_context_id="acceptance-reviewer", errors=errors,
        )
        return errors

    def rewrite_contract(self, payload: dict) -> None:
        write_json(self.repo / self.contract_ref["path"], payload)
        self.contract_ref = ref(self.repo, self.repo / self.contract_ref["path"])

    def rewrite_runtime_and_comparison(self, runtime: dict) -> None:
        runtime_path = self.repo / self.refs["runtime_interaction_evidence"]["path"]
        write_json(runtime_path, runtime)
        runtime_ref = ref(self.repo, runtime_path)
        comparison_path = self.repo / self.refs["comparison_review"]["path"]
        comparison = json.loads(comparison_path.read_text())
        comparison["runtime_interaction_evidence"] = runtime_ref
        write_json(comparison_path, comparison)
        self.refs["runtime_interaction_evidence"] = runtime_ref
        self.refs["comparison_review"] = ref(self.repo, comparison_path)

    def rewrite_blind_and_comparison(self, blind: dict) -> None:
        blind_path = self.repo / self.refs["blind_observation"]["path"]
        write_json(blind_path, blind)
        blind_ref = ref(self.repo, blind_path)
        comparison_path = self.repo / self.refs["comparison_review"]["path"]
        comparison = json.loads(comparison_path.read_text())
        comparison["blind_observation"] = blind_ref
        write_json(comparison_path, comparison)
        self.refs["blind_observation"] = blind_ref
        self.refs["comparison_review"] = ref(self.repo, comparison_path)

    def rewrite_blind_input_chain(self, blind_input: dict) -> None:
        blind_input_path = self.repo / self.refs["blind_observation_input"]["path"]
        write_json(blind_input_path, blind_input)
        blind_input_ref = ref(self.repo, blind_input_path)
        blind_path = self.repo / self.refs["blind_observation"]["path"]
        blind = json.loads(blind_path.read_text())
        blind["observation_input"] = blind_input_ref
        write_json(blind_path, blind)
        blind_ref = ref(self.repo, blind_path)
        comparison_path = self.repo / self.refs["comparison_review"]["path"]
        comparison = json.loads(comparison_path.read_text())
        comparison["blind_observation"] = blind_ref
        write_json(comparison_path, comparison)
        self.refs["blind_observation_input"] = blind_input_ref
        self.refs["blind_observation"] = blind_ref
        self.refs["comparison_review"] = ref(self.repo, comparison_path)

    def rewrite_comparison(self, comparison: dict) -> None:
        comparison_path = self.repo / self.refs["comparison_review"]["path"]
        write_json(comparison_path, comparison)
        self.refs["comparison_review"] = ref(self.repo, comparison_path)

    def test_complete_visible_interaction_chain_passes(self) -> None:
        self.assertEqual([], self.validate_contract())
        self.assertEqual([], self.validate_runtime())

    def test_contract_with_popup_dialogue_proxy_is_rejected(self) -> None:
        contract = json.loads((self.repo / self.contract_ref["path"]).read_text())
        beat = contract["playable_beats"][0]
        beat["available_input"]["input_kind"] = "DIALOGUE_ADVANCE"
        beat["interaction_sequence"][0]["input_kind"] = "DIALOGUE_ADVANCE"
        beat["interaction_sequence"][0]["response_channels"] = ["DIALOGUE"]
        self.rewrite_contract(contract)
        errors = self.validate_contract()
        self.assertTrue(any("proxy" in item or "non-text visible" in item for item in errors), errors)

    def test_contract_with_screen_description_but_no_input_is_rejected(self) -> None:
        contract = json.loads((self.repo / self.contract_ref["path"]).read_text())
        contract["playable_beats"][0]["interaction_sequence"] = []
        self.rewrite_contract(contract)
        errors = self.validate_contract()
        self.assertTrue(any("ordered input-to-response" in item for item in errors), errors)

    def test_contract_with_one_static_scene_frame_is_rejected(self) -> None:
        contract = json.loads((self.repo / self.contract_ref["path"]).read_text())
        contract["current_scene_composition"] = [
            contract["current_scene_composition"][0]
        ]
        self.rewrite_contract(contract)
        errors = self.validate_contract()
        self.assertTrue(any("must exactly cover" in item for item in errors), errors)

    def test_contract_cannot_relabel_one_static_scene_frame_as_a_sequence(self) -> None:
        contract = json.loads((self.repo / self.contract_ref["path"]).read_text())
        static_artifact = contract["current_scene_composition"][0]["artifact"]
        for item in contract["current_scene_composition"]:
            item["artifact"] = static_artifact
        self.rewrite_contract(contract)
        errors = self.validate_contract()
        self.assertTrue(any("reuse one static visual" in item for item in errors), errors)

    def test_contract_cannot_rename_copies_of_one_static_scene_frame(self) -> None:
        contract = json.loads((self.repo / self.contract_ref["path"]).read_text())
        first_ref = contract["current_scene_composition"][0]["artifact"]
        static_bytes = (self.repo / first_ref["path"]).read_bytes()
        for item in contract["current_scene_composition"][1:]:
            artifact_path = self.repo / item["artifact"]["path"]
            artifact_path.write_bytes(static_bytes)
            item["artifact"] = ref(self.repo, artifact_path)
        self.rewrite_contract(contract)
        errors = self.validate_contract()
        self.assertTrue(any("rename" in item and "static visual" in item for item in errors), errors)

    def test_contract_scene_moments_must_follow_declared_order(self) -> None:
        contract = json.loads((self.repo / self.contract_ref["path"]).read_text())
        composition = contract["current_scene_composition"]
        composition[0], composition[1] = composition[1], composition[0]
        composition[0]["sequence"], composition[1]["sequence"] = 1, 2
        self.rewrite_contract(contract)
        errors = self.validate_contract()
        self.assertTrue(any("temporal order" in item for item in errors), errors)

    def test_contract_capture_moments_must_be_in_temporal_order(self) -> None:
        contract = json.loads((self.repo / self.contract_ref["path"]).read_text())
        contract["playable_beats"][0]["player_surface_evidence_plan"][
            "ordered_capture_moments"
        ].reverse()
        self.rewrite_contract(contract)
        errors = self.validate_contract()
        self.assertTrue(any("in that exact order" in item for item in errors), errors)

    def test_contract_transition_coverage_must_preserve_authoritative_order(self) -> None:
        contract = json.loads((self.repo / self.contract_ref["path"]).read_text())
        first = contract["playable_beats"][0]["system_transition_ids"]
        second = contract["playable_beats"][1]["system_transition_ids"]
        first[0], second[0] = second[0], first[0]
        self.rewrite_contract(contract)
        errors = self.validate_contract()
        self.assertTrue(any("authoritative order" in item for item in errors), errors)

    def test_contract_entry_knowledge_cannot_expose_answer_bearing_beat_id(self) -> None:
        contract_path = self.repo / self.contract_ref["path"]
        contract = json.loads(contract_path.read_text())
        contract["player_entry_knowledge"].append(
            "The intended route is encoded by beat.repair-bridge."
        )
        self.rewrite_contract(contract)
        review_path = self.repo / self.contract_review_ref["path"]
        review = json.loads(review_path.read_text())
        review["interaction_contract"] = self.contract_ref
        write_json(review_path, review)
        self.contract_review_ref = ref(self.repo, review_path)
        errors = self.validate_contract()
        self.assertTrue(any("exposes answer-bearing design ids" in item for item in errors), errors)

    def test_input_without_visible_changed_affordance_is_rejected(self) -> None:
        contract = json.loads((self.repo / self.contract_ref["path"]).read_text())
        contract["playable_beats"][0]["next_affordance"]["discovery_channels"] = ["DIALOGUE"]
        self.rewrite_contract(contract)
        errors = self.validate_contract()
        self.assertTrue(any("next_affordance" in item for item in errors), errors)

    def test_contract_review_must_cover_every_beat_for_every_requirement(self) -> None:
        review_path = self.repo / self.contract_review_ref["path"]
        review = json.loads(review_path.read_text())
        review["requirement_findings"]["visible_entry_cause_and_goal"][
            "beat_ids"
        ].pop()
        write_json(review_path, review)
        self.contract_review_ref = ref(self.repo, review_path)
        errors = self.validate_contract()
        self.assertTrue(any("must exactly cover every contract beat" in item for item in errors), errors)

    def test_runtime_with_only_screenshots_is_rejected(self) -> None:
        runtime_path = self.repo / self.refs["runtime_interaction_evidence"]["path"]
        runtime = json.loads(runtime_path.read_text())
        runtime["evidence_files"] = [
            item for item in runtime["evidence_files"] if item["artifact_type"] != "INPUT_TRACE"
        ]
        self.rewrite_runtime_and_comparison(runtime)
        errors = self.validate_runtime()
        self.assertTrue(any("combine input trace" in item for item in errors), errors)

    def test_runtime_with_only_tests_logs_and_state_json_is_rejected(self) -> None:
        state = self.admission_dir / "state-only.json"
        write_json(state, {"objective_complete": True})
        runtime_path = self.repo / self.refs["runtime_interaction_evidence"]["path"]
        runtime = json.loads(runtime_path.read_text())
        state_ref = ref(self.repo, state)
        runtime["evidence_files"] = [
            {"artifact_type": artifact_type, "artifact": state_ref}
            for artifact_type in ("TEST_RESULT", "DEBUG_LOG", "STATE_JSON")
        ]
        self.rewrite_runtime_and_comparison(runtime)
        errors = self.validate_runtime()
        self.assertTrue(any("combine input trace" in item for item in errors), errors)

    def test_runtime_trace_sequence_must_follow_stored_order(self) -> None:
        runtime_path = self.repo / self.refs["runtime_interaction_evidence"]["path"]
        runtime = json.loads(runtime_path.read_text())
        runtime["ordered_input_trace"].reverse()
        self.rewrite_runtime_and_comparison(runtime)
        errors = self.validate_runtime()
        self.assertTrue(any("contiguous and ordered" in item for item in errors), errors)

    def test_one_static_frame_plus_input_log_cannot_prove_interaction(self) -> None:
        runtime_path = self.repo / self.refs["runtime_interaction_evidence"]["path"]
        runtime = json.loads(runtime_path.read_text())
        static_ref = runtime["ordered_input_trace"][0]["frame_before"]
        for trace in runtime["ordered_input_trace"]:
            for field in ("frame_before", "frame_during", "frame_after"):
                trace[field] = static_ref
        runtime["returned_surface"]["frame"] = static_ref
        runtime["localization_observation"]["evidence"] = [
            {"artifact_type": "FRAME_AFTER", "artifact": static_ref}
        ]
        input_trace = next(
            item for item in runtime["evidence_files"]
            if item["artifact_type"] == "INPUT_TRACE"
        )
        runtime["evidence_files"] = [
            input_trace,
            *[
                {"artifact_type": kind, "artifact": static_ref}
                for kind in ("FRAME_BEFORE", "FRAME_DURING", "FRAME_AFTER")
            ],
        ]
        self.rewrite_runtime_and_comparison(runtime)
        errors = self.validate_runtime()
        self.assertTrue(any("one static frame cannot prove interaction" in item for item in errors), errors)

    def test_runtime_cannot_rename_frame_copies_across_trace_sequences(self) -> None:
        runtime_path = self.repo / self.refs["runtime_interaction_evidence"]["path"]
        runtime = json.loads(runtime_path.read_text())
        first, second = runtime["ordered_input_trace"][:2]
        replacement_refs: dict[str, dict[str, str]] = {}
        for field in ("frame_before", "frame_during", "frame_after"):
            target_path = self.repo / second[field]["path"]
            target_path.write_bytes((self.repo / first[field]["path"]).read_bytes())
            replacement_refs[second[field]["path"]] = ref(self.repo, target_path)
            second[field] = replacement_refs[second[field]["path"]]
        for item in runtime["evidence_files"]:
            path = item["artifact"]["path"]
            if path in replacement_refs:
                item["artifact"] = replacement_refs[path]
        self.rewrite_runtime_and_comparison(runtime)

        input_path = self.repo / self.refs["blind_observation_input"]["path"]
        blind_input = json.loads(input_path.read_text())
        for item in blind_input["surface_artifacts"]:
            path = item["artifact"]["path"]
            if path in replacement_refs:
                item["artifact"] = replacement_refs[path]
        self.rewrite_blind_input_chain(blind_input)

        blind_path = self.repo / self.refs["blind_observation"]["path"]
        blind = json.loads(blind_path.read_text())
        for attempt in blind["observation"]["interaction_observations"]:
            attempt["surface_artifacts"] = [
                replacement_refs.get(item["path"], item)
                for item in attempt["surface_artifacts"]
            ]
        self.rewrite_blind_and_comparison(blind)
        errors = self.validate_runtime()
        self.assertTrue(
            any("rename" in item and "across different interaction sequences" in item for item in errors),
            errors,
        )

    def test_blind_record_after_reading_authority_is_rejected(self) -> None:
        blind_path = self.repo / self.refs["blind_observation"]["path"]
        blind = json.loads(blind_path.read_text())
        blind["context_attestation"]["design_authority_read_before_observation"] = True
        self.rewrite_blind_and_comparison(blind)
        errors = self.validate_runtime()
        self.assertTrue(any("answer-bearing authority" in item for item in errors), errors)

    def test_blind_observer_cannot_reuse_a_design_author_context(self) -> None:
        blind_path = self.repo / self.refs["blind_observation"]["path"]
        blind = json.loads(blind_path.read_text())
        blind["reviewer_context_id"] = "surface-contract-author"
        self.rewrite_blind_and_comparison(blind)
        errors = self.validate_runtime()
        self.assertTrue(any("fresh from design authority" in item for item in errors), errors)

    def test_blind_observer_cannot_reuse_final_card_reviewer_context(self) -> None:
        blind_path = self.repo / self.refs["blind_observation"]["path"]
        blind = json.loads(blind_path.read_text())
        blind["reviewer_context_id"] = "final-card-reviewer"
        self.rewrite_blind_and_comparison(blind)
        errors = self.validate_runtime()
        self.assertTrue(any("fresh from design authority" in item for item in errors), errors)

    def test_blind_input_cannot_inject_answer_as_prior_knowledge(self) -> None:
        input_path = self.repo / self.refs["blind_observation_input"]["path"]
        blind_input = json.loads(input_path.read_text())
        blind_input["player_prior_knowledge"][0] = (
            "The intended answer is to repair the object and follow the opened route."
        )
        self.rewrite_blind_input_chain(blind_input)
        errors = self.validate_runtime()
        self.assertTrue(any("inject intended answers" in item for item in errors), errors)

    def test_blind_input_does_not_expose_answer_bearing_beat_ids(self) -> None:
        input_path = self.repo / self.refs["blind_observation_input"]["path"]
        blind_input = json.loads(input_path.read_text())
        self.assertTrue(
            all(isinstance(item, str) for item in blind_input["player_prior_knowledge"])
        )
        serialized = json.dumps(blind_input["player_prior_knowledge"])
        self.assertNotIn("beat.repair-bridge", serialized)
        self.assertNotIn("beat.cross-open-route", serialized)
        self.assertEqual([], self.validate_runtime())

    def test_blind_input_cannot_hide_design_ids_outside_prior_knowledge(self) -> None:
        leaked_entry = (
            "Start at beat.repair-bridge and follow scenario.repair-bridge."
        )
        runtime_path = self.repo / self.refs["runtime_interaction_evidence"]["path"]
        runtime = json.loads(runtime_path.read_text())
        runtime["scenario_entry_state"] = leaked_entry
        self.rewrite_runtime_and_comparison(runtime)
        input_path = self.repo / self.refs["blind_observation_input"]["path"]
        blind_input = json.loads(input_path.read_text())
        blind_input["scenario_entry_state"] = leaked_entry
        self.rewrite_blind_input_chain(blind_input)
        errors = self.validate_runtime()
        self.assertTrue(
            any("Phase-A-visible" in item and "answer-bearing" in item for item in errors),
            errors,
        )

    def test_blind_input_requires_semantic_deidentification_attestation(self) -> None:
        input_path = self.repo / self.refs["blind_observation_input"]["path"]
        blind_input = json.loads(input_path.read_text())
        blind_input["preparation_attestation"]["intended_answers_removed"] = False
        self.rewrite_blind_input_chain(blind_input)
        errors = self.validate_runtime()
        self.assertTrue(any("preparation must attest" in item for item in errors), errors)

    def test_blind_observer_must_be_fresh_from_input_preparer(self) -> None:
        blind_path = self.repo / self.refs["blind_observation"]["path"]
        blind = json.loads(blind_path.read_text())
        blind["reviewer_context_id"] = "blind-input-preparer"
        self.rewrite_blind_and_comparison(blind)
        errors = self.validate_runtime()
        self.assertTrue(any("prepared and de-identified" in item for item in errors), errors)

    def test_comparison_reviewer_must_be_fresh_from_input_preparer(self) -> None:
        comparison_path = self.repo / self.refs["comparison_review"]["path"]
        comparison = json.loads(comparison_path.read_text())
        comparison["reviewer_context_id"] = "blind-input-preparer"
        self.rewrite_comparison(comparison)
        errors = self.validate_runtime()
        self.assertTrue(any("blind-input preparation" in item for item in errors), errors)

    def test_blind_input_must_include_complete_runtime_surface(self) -> None:
        input_path = self.repo / self.refs["blind_observation_input"]["path"]
        blind_input = json.loads(input_path.read_text())
        before = blind_input["surface_artifacts"][0]
        blind_input["surface_artifacts"] = [before]
        blind_path = self.repo / self.refs["blind_observation"]["path"]
        blind = json.loads(blind_path.read_text())
        for attempt in blind["observation"]["interaction_observations"]:
            attempt["surface_artifacts"] = [before["artifact"]]
        write_json(blind_path, blind)
        self.rewrite_blind_input_chain(blind_input)
        errors = self.validate_runtime()
        self.assertTrue(any("must exactly cover every runtime" in item for item in errors), errors)

    def test_blind_attempt_sequence_must_follow_stored_order(self) -> None:
        blind_path = self.repo / self.refs["blind_observation"]["path"]
        blind = json.loads(blind_path.read_text())
        blind["observation"]["interaction_observations"].reverse()
        self.rewrite_blind_and_comparison(blind)
        errors = self.validate_runtime()
        self.assertTrue(any("attempt sequence must be contiguous and ordered" in item for item in errors), errors)

    def test_comparison_cannot_invent_a_missing_blind_attempt(self) -> None:
        blind_path = self.repo / self.refs["blind_observation"]["path"]
        blind = json.loads(blind_path.read_text())
        blind["observation"]["interaction_observations"].pop()
        self.rewrite_blind_and_comparison(blind)
        errors = self.validate_runtime()
        self.assertTrue(
            any("absent from the sealed blind record" in item for item in errors),
            errors,
        )

    def test_comparison_cannot_swap_blind_attempts_between_beats(self) -> None:
        comparison_path = self.repo / self.refs["comparison_review"]["path"]
        comparison = json.loads(comparison_path.read_text())
        first = comparison["beat_comparisons"][0]["observation_citations"]
        second = comparison["beat_comparisons"][1]["observation_citations"]
        comparison["beat_comparisons"][0]["observation_citations"] = second
        comparison["beat_comparisons"][1]["observation_citations"] = first
        self.rewrite_comparison(comparison)
        errors = self.validate_runtime()
        self.assertTrue(
            any("corresponding to its runtime trace sequences" in item for item in errors),
            errors,
        )

    def test_visually_blocked_localization_is_rejected(self) -> None:
        runtime_path = self.repo / self.refs["runtime_interaction_evidence"]["path"]
        runtime = json.loads(runtime_path.read_text())
        runtime["localization_observation"]["locale"] = "zh-Hant"
        runtime["localization_observation"]["status"] = "OBSERVED_BLOCKED"
        runtime["localization_observation"]["fallback_used"] = True
        runtime["localization_observation"]["garbled_text_present"] = True
        self.rewrite_runtime_and_comparison(runtime)
        errors = self.validate_runtime()
        self.assertTrue(any("localization" in item for item in errors), errors)


if __name__ == "__main__":
    unittest.main()
