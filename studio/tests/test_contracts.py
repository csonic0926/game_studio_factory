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
            "gameplay_acceptance_input.schema.json": "gameplay_acceptance_input.v2",
            "gameplay_acceptance_review.schema.json": "gameplay_acceptance_review.v3",
            "product_authority_archive_snapshot.schema.json": "product_authority_archive_snapshot.v1",
            "product_authority_register.schema.json": "product_authority_register.v1",
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
        review = json.loads(
            (STUDIO_ROOT / "schemas/gameplay_acceptance_review.schema.json").read_text()
        )
        human = review["properties"]["human_playtest"]
        self.assertEqual("HUMAN_PLAYTEST_ACCEPTED", human["properties"]["status"]["const"])
        self.assertEqual("USER", human["properties"]["verdict_owner"]["const"])
        self.assertIn("verdict_payload_sha256", human["required"])
        self.assertIn("observed_two_lap_cycle", review["required"])

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

    def test_decision_register_has_explicit_superseded_state(self) -> None:
        payload = json.loads(
            (STUDIO_ROOT / "schemas/studio_decision_card_register.schema.json").read_text()
        )
        states = payload["properties"]["entries"]["items"]["properties"]["state"]["enum"]
        self.assertIn("SUPERSEDED", states)
        self.assertIn("PRODUCT_ARCHIVED", states)


if __name__ == "__main__":
    unittest.main()
