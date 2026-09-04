import json
import unittest
from pathlib import Path


STUDIO_ROOT = Path(__file__).resolve().parents[1]


class StudioFoundationContractTests(unittest.TestCase):
    def test_all_studio_schemas_are_json_objects(self) -> None:
        expected_versions = {
            "accepted_playable_baseline.schema.json": "accepted_playable_baseline.v3",
            "baseline_admission_input.schema.json": "baseline_admission_input.v1",
            "baseline_admission_result.schema.json": "baseline_admission_result.v1",
            "baseline_reconstruction_inventory.schema.json": "baseline_reconstruction_inventory.v1",
            "baseline_regression_review.schema.json": "baseline_regression_review.v1",
            "design_token_research.schema.json": "design_token_research.v1",
            "gameplay_acceptance_input.schema.json": "gameplay_acceptance_input.v3",
            "gameplay_acceptance_review.schema.json": "gameplay_acceptance_review.v4",
            "godot_engine_capability_manifest.schema.json": "godot_engine_capability_manifest.v1",
            "godot_engine_evidence.schema.json": "godot_engine_evidence.v1",
            "godot_automation_evidence.schema.json": "godot_automation_evidence.v1",
            "godot_automation_doctor.schema.json": "godot_automation_doctor.v1",
            "godot_bridge_install_manifest.schema.json": "godot_bridge_install_manifest.v1",
            "godot_bridge_result.schema.json": "godot_bridge_result.v1",
            "godot_bridge_profile.schema.json": "godot_bridge_profile.v1",
            "godot_operation_pending.schema.json": "godot_operation_pending.v1",
            "godot_scenario.schema.json": "godot_scenario.v1",
            "godot_session_trace_record.schema.json": "godot_session_trace_record.v1",
            "godot_structural_capture.schema.json": "godot_structural_capture.v1",
            "godot_visual_baseline.schema.json": "godot_visual_baseline.v1",
            "godot_visual_comparison.schema.json": "godot_visual_comparison.v1",
            "product_authority_archive_snapshot.schema.json": "product_authority_archive_snapshot.v1",
            "product_authority_register.schema.json": "product_authority_register.v1",
            "player_facing_blind_observation.schema.json": "player_facing_blind_observation.v1",
            "player_facing_blind_observation_input.schema.json": "player_facing_blind_observation_input.v1",
            "player_facing_comparison_review.schema.json": "player_facing_comparison_review.v1",
            "player_facing_runtime_interaction_evidence.schema.json": "player_facing_runtime_interaction_evidence.v1",
            "studio_gameplay_system.schema.json": "studio_gameplay_system.v2",
            "studio_gameplay_system_manifest.schema.json": "studio_gameplay_system_manifest.v1",
            "studio_gameplay_system_review.schema.json": "studio_gameplay_system_review.v2",
            "studio_semantic_alignment_input.schema.json": "studio_semantic_alignment_input.v3",
            "studio_semantic_alignment_review.schema.json": "studio_semantic_alignment_review.v3",
            "studio_decision_card_register.schema.json": "studio_decision_card_register.v1",
            "studio_run_state.schema.json": "studio_run_state.v3",
            "studio_workflow_completion.schema.json": "studio_workflow_completion.v2",
        }
        for name, version in expected_versions.items():
            payload = json.loads((STUDIO_ROOT / "schemas" / name).read_text())
            self.assertEqual("object", payload["type"])
            self.assertEqual(version, payload["properties"]["schema_version"]["const"])

        bridge_message = json.loads(
            (STUDIO_ROOT / "schemas/godot_bridge_message.schema.json").read_text()
        )
        self.assertEqual("object", bridge_message["type"])
        self.assertEqual(
            "godot_bridge_protocol.v1",
            bridge_message["properties"]["protocol_version"]["const"],
        )

    def test_baseline_schema_forbids_demo_only_delivery(self) -> None:
        payload = json.loads(
            (STUDIO_ROOT / "schemas/accepted_playable_baseline.schema.json").read_text()
        )
        eligibility = payload["properties"]["delivery_eligibility"]["properties"]
        self.assertFalse(eligibility["interactive_demo_only"]["const"])
        self.assertTrue(eligibility["minimum_gameplay_passed"]["const"])
        self.assertEqual(0, eligibility["blocking_gap_ids"]["maxItems"])

    def test_acceptance_review_is_one_closed_object(self) -> None:
        payload = json.loads(
            (STUDIO_ROOT / "schemas/accepted_playable_baseline.schema.json").read_text()
        )
        review = payload["$defs"]["gameplay_unit"]["properties"]["acceptance_review"]
        self.assertFalse(review["additionalProperties"])
        self.assertEqual(
            {
                "path", "sha256", "reviewer_freshness", "verdict",
                "experience_authority", "human_playtest_status",
                "studio_gameplay_system", "cycle_id", "cycle_status",
            },
            set(review["required"]),
        )

    def test_acceptance_contract_binds_experience_and_human_verdict(self) -> None:
        acceptance_input = json.loads(
            (STUDIO_ROOT / "schemas/gameplay_acceptance_input.schema.json").read_text()
        )
        self.assertIn("experience_authority", acceptance_input["required"])
        self.assertIn("expected_player_experience", acceptance_input["required"])
        self.assertIn("studio_gameplay_system", acceptance_input["required"])
        self.assertIn("cycle_acceptance", acceptance_input["required"])
        self.assertIn("player_facing_interaction_contract", acceptance_input["required"])
        self.assertIn("player_facing_evidence", acceptance_input["required"])
        review = json.loads(
            (STUDIO_ROOT / "schemas/gameplay_acceptance_review.schema.json").read_text()
        )
        human = review["properties"]["human_playtest"]
        self.assertEqual("HUMAN_PLAYTEST_ACCEPTED", human["properties"]["status"]["const"])
        self.assertEqual("USER", human["properties"]["verdict_owner"]["const"])
        self.assertIn("verdict_payload_sha256", human["required"])
        self.assertIn("observed_two_lap_cycle", review["required"])
        self.assertIn("player_facing_evidence", review["required"])

        runtime = json.loads(
            (
                STUDIO_ROOT
                / "schemas/player_facing_runtime_interaction_evidence.schema.json"
            ).read_text()
        )
        self.assertIn("$defs", runtime)
        self.assertNotIn("$defs", runtime["properties"])
        for field in (
            "ordered_input_trace",
            "observable_changes",
            "returned_surface",
            "localization_observation",
            "evidence_files",
        ):
            self.assertIn(field, runtime["properties"])

    def test_baseline_promotion_names_repaired_or_new_units(self) -> None:
        payload = json.loads(
            (STUDIO_ROOT / "schemas/accepted_playable_baseline.schema.json").read_text()
        )
        promotion = payload["properties"]["promotion"]
        self.assertIn("promoted_unit_ids", promotion["required"])
        self.assertEqual(1, promotion["properties"]["promoted_unit_ids"]["minItems"])
        self.assertIn("source_workflow_handoffs", promotion["required"])

    def test_admission_templates_expose_both_cases(self) -> None:
        reconstruction = json.loads(
            (STUDIO_ROOT / "templates/BASELINE_RECONSTRUCTION_INPUT.json").read_text()
        )
        promotion = json.loads(
            (STUDIO_ROOT / "templates/BASELINE_PROMOTION_INPUT.json").read_text()
        )
        self.assertEqual("RECONSTRUCT", reconstruction["admission_mode"])
        self.assertEqual("PROMOTE", promotion["admission_mode"])
        self.assertEqual({"path": "", "sha256": ""}, reconstruction["workflow_completion"])
        self.assertNotEqual("", promotion["workflow_completion"]["path"])

    def test_research_requires_all_three_distance_rings(self) -> None:
        payload = json.loads(
            (STUDIO_ROOT / "schemas/design_token_research.schema.json").read_text()
        )
        rings = payload["properties"]["searched_rings"]
        self.assertEqual(3, rings["minItems"])
        self.assertEqual(3, rings["maxItems"])
        self.assertEqual(
            {"SAME_TYPE", "CROSS_GENRE", "NON_GAME"},
            set(rings["items"]["enum"]),
        )

    def test_open_research_template_can_start_without_fake_sources(self) -> None:
        schema = json.loads(
            (STUDIO_ROOT / "schemas/design_token_research.schema.json").read_text()
        )
        template = json.loads(
            (STUDIO_ROOT / "templates/DESIGN_TOKEN_RESEARCH.json").read_text()
        )
        self.assertEqual("OPEN_FRONTIER", template["research_status"])
        self.assertEqual([], template["sources"])
        self.assertNotIn("minItems", schema["properties"]["sources"])

    def test_delivered_state_requires_build_and_no_blockers(self) -> None:
        payload = json.loads(
            (STUDIO_ROOT / "schemas/studio_run_state.schema.json").read_text()
        )
        delivered = payload["allOf"][0]["then"]["properties"]
        self.assertTrue(delivered["delivery"]["properties"]["eligible"]["const"])
        self.assertEqual(1, delivered["delivery"]["properties"]["build_paths"]["minItems"])
        self.assertEqual(0, delivered["blockers"]["maxItems"])

    def test_public_skill_has_minimal_frontmatter(self) -> None:
        body = (STUDIO_ROOT / "skills/game-studio-factory/SKILL.md").read_text()
        self.assertTrue(body.startswith("---\n"))
        self.assertIn("\nname: game-studio-factory\n", body)
        self.assertNotIn("TODO", body)

    def test_semantic_alignment_requires_fresh_evidence_bound_review(self) -> None:
        payload = json.loads(
            (STUDIO_ROOT / "schemas/studio_semantic_alignment_review.schema.json").read_text()
        )
        self.assertEqual(
            "FRESH", payload["properties"]["reviewer_freshness"]["const"]
        )
        required_checks = set(payload["properties"]["checks"]["required"])
        self.assertIn("authority_continuity", required_checks)
        self.assertIn("response_binding_fidelity", required_checks)
        self.assertIn("authority_change_fidelity", required_checks)
        self.assertIn("material_claim_coverage", required_checks)
        self.assertIn("question_necessity", required_checks)
        self.assertIn("semantic_non_substitution", required_checks)
        self.assertIn("pending_decision_disposition", required_checks)
        self.assertIn("independent_claim_inventory", payload["required"])

    def test_final_card_review_is_separate_and_covers_gameplay_sufficiency(self) -> None:
        factory_root = STUDIO_ROOT.parent
        payload = json.loads(
            (
                factory_root
                / "gameplay/schemas/gameplay_decision_card_factory_review.schema.json"
            ).read_text()
        )
        self.assertEqual(
            "gameplay_decision_card_factory_review.v2",
            payload["properties"]["schema_version"]["const"],
        )
        findings = payload["properties"]["requirement_findings"]
        required = set(findings["required"])
        self.assertIn("playable_span_sufficiency_not_inflated", required)
        self.assertIn("meaningful_choice_not_certain_click", required)
        self.assertIn("non_gameplay_activity_not_counted", required)
        self.assertIn("player_work_world_response_carry_forward", required)
        self.assertIn("two_lap_decision_materially_differs", required)
        self.assertIn("applicable_factory_gates_complete", required)
        self.assertIn("player_facing_interaction_concretely_designed", required)
        self.assertEqual(
            {
                "PASS_CARD_FACTORY_COMPLIANCE",
                "REVISE_CARD_BEFORE_HUMAN",
            },
            set(payload["properties"]["verdict"]["enum"]),
        )

        reviewer_skill = (
            STUDIO_ROOT
            / "skills/studio-gameplay-decision-card-reviewer/SKILL.md"
        ).read_text()
        self.assertIn("certain-outcome", reviewer_skill)
        self.assertIn("dialogue advance", reviewer_skill)
        self.assertIn("semantic-alignment reviewer", reviewer_skill)
        self.assertIn("must differ", reviewer_skill)

    def test_player_facing_design_review_can_record_a_blocked_result(self) -> None:
        schema = json.loads(
            (
                STUDIO_ROOT.parent
                / "gameplay/schemas/player_facing_interaction_contract_review.schema.json"
            ).read_text()
        )
        beat_verdicts = schema["properties"]["beat_findings"]["items"][
            "properties"
        ]["verdict"]["enum"]
        self.assertIn("BLOCK", beat_verdicts)
        self.assertNotIn("maxItems", schema["properties"]["blocking_findings"])
        self.assertEqual(
            1,
            schema["allOf"][0]["else"]["properties"]["blocking_findings"][
                "minItems"
            ],
        )

    def test_player_facing_blind_schema_seals_deidentified_attempt_records(self) -> None:
        factory_root = STUDIO_ROOT.parent
        contract = json.loads(
            (
                factory_root
                / "gameplay/schemas/player_facing_interaction_contract.schema.json"
            ).read_text()
        )
        self.assertIn("player_entry_knowledge", contract["required"])
        self.assertEqual(
            "#/$defs/text",
            contract["properties"]["player_entry_knowledge"]["items"]["$ref"],
        )

        blind_input = json.loads(
            (
                STUDIO_ROOT
                / "schemas/player_facing_blind_observation_input.schema.json"
            ).read_text()
        )
        self.assertEqual(
            "#/$defs/text",
            blind_input["properties"]["player_prior_knowledge"]["items"]["$ref"],
        )
        self.assertIn("preparation_attestation", blind_input["required"])
        preparation = blind_input["properties"]["preparation_attestation"]
        for field in (
            "answer_bearing_design_ids_removed",
            "intended_answers_removed",
            "future_beat_knowledge_removed",
            "only_phase_a_allowed_materials_present",
        ):
            self.assertIs(True, preparation["properties"][field]["const"])
        blind = json.loads(
            (STUDIO_ROOT / "schemas/player_facing_blind_observation.schema.json").read_text()
        )
        attempts = blind["properties"]["observation"]["properties"][
            "interaction_observations"
        ]
        self.assertEqual("#/$defs/interaction_observation", attempts["items"]["$ref"])
        self.assertEqual(
            "^attempt\\.[1-9][0-9]*$",
            blind["$defs"]["interaction_observation"]["properties"]["attempt_id"][
                "pattern"
            ],
        )

    def test_design_conformance_schema_preserves_hypothesis_lifecycle(self) -> None:
        schema = json.loads(
            (
                STUDIO_ROOT.parent
                / "gameplay/schemas/gameplay_design_conformance_review.schema.json"
            ).read_text()
        )
        self.assertEqual(
            "gameplay_design_conformance_review.v2",
            schema["properties"]["schema_version"]["const"],
        )
        verdicts = set(
            schema["$defs"]["claim_coverage"]["properties"]["verdict"]["enum"]
        )
        self.assertEqual({"PASS_DESIGN_CLAIM", "TESTABLE_DESIGN"}, verdicts)

    def test_decision_register_has_explicit_superseded_state(self) -> None:
        payload = json.loads(
            (STUDIO_ROOT / "schemas/studio_decision_card_register.schema.json").read_text()
        )
        states = payload["properties"]["entries"]["items"]["properties"]["state"]["enum"]
        self.assertIn("SUPERSEDED", states)
        self.assertIn("PRODUCT_ARCHIVED", states)


if __name__ == "__main__":
    unittest.main()
