import json
import unittest
from pathlib import Path


STUDIO_ROOT = Path(__file__).resolve().parents[1]


class StudioFoundationContractTests(unittest.TestCase):
    def test_all_studio_schemas_are_json_objects(self) -> None:
        expected_versions = {
            "accepted_playable_baseline.schema.json": "accepted_playable_baseline.v1",
            "baseline_admission_input.schema.json": "baseline_admission_input.v1",
            "baseline_admission_result.schema.json": "baseline_admission_result.v1",
            "baseline_reconstruction_inventory.schema.json": "baseline_reconstruction_inventory.v1",
            "baseline_regression_review.schema.json": "baseline_regression_review.v1",
            "design_token_research.schema.json": "design_token_research.v1",
            "gameplay_acceptance_review.schema.json": "gameplay_acceptance_review.v1",
            "studio_run_state.schema.json": "studio_run_state.v1",
            "studio_workflow_completion.schema.json": "studio_workflow_completion.v1",
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
            {"path", "sha256", "reviewer_freshness", "verdict"},
            set(review["required"]),
        )

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


if __name__ == "__main__":
    unittest.main()
