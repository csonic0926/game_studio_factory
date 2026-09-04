from __future__ import annotations

import copy
import hashlib
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from gameplay.design_gate import (
    READY_FOR_NEW_GAMEPLAY_DESIGN,
    _validate_decision_card,
    current_factory_revision,
    decision_payload_sha256,
    main as design_gate_main,
)
from gameplay.project_card_standard import PROJECT_REVIEW_NAME
from gameplay.tests.project_card_fixture import (
    STANDARD_RELATIVE,
    attach_project_review,
    ref,
    write_json,
)
from studio.tests.player_surface_fixture import write_contract_pair


class ProjectOwnedCardStandardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name) / "game"
        self.repo.mkdir()
        self.revision = current_factory_revision(Path(__file__).resolve().parents[2])
        self.objective_dir = self.repo / "design/gameplay/objective_gameplay/direct-unit"
        self.card_path = self.objective_dir / "GAMEPLAY_DECISION_CARD.json"
        contract_ref, contract_review_ref, _ = write_contract_pair(
            self.repo,
            self.objective_dir,
            project_id="portable-game",
            objective_id="direct-unit",
            factory_revision=self.revision,
            product_ref={"path": "", "sha256": ""},
            system_ref={"path": "", "sha256": ""},
            transition_ids=["read", "commit", "return"],
        )
        self.contract_ref = contract_ref
        self.contract_review_ref = contract_review_ref
        self.card = {
            "schema_version": "gameplay_decision_card.v3",
            "card_id": "direct-unit.card.v1",
            "project_id": "portable-game",
            "objective_id": "direct-unit",
            "factory_revision": self.revision,
            "routing": "DIRECT_SPECIALIST",
            "product_authority": {"path": "", "sha256": ""},
            "studio_gameplay_system": {"path": "", "sha256": ""},
            "player_facing_interaction_contract": contract_ref,
            "player_facing_interaction_contract_review": contract_review_ref,
            "author_context_id": "direct-card-author",
            "player_promise": {
                "claim_id": "promise.direct-loop",
                "text": "Read a visible pressure, commit, and return to a changed opportunity.",
            },
            "core_cycle": [
                {"claim_id": "cycle.read", "text": "Read the visible situation and alternatives."},
                {"claim_id": "cycle.commit", "text": "Commit through one concrete world action."},
                {"claim_id": "cycle.return", "text": "See the persistent response and changed next affordance."},
            ],
            "material_commitments": [
                {"claim_id": "scope.direct", "text": "One complete lap with a visible irreversible resolution."}
            ],
            "red_lines": [
                {"claim_id": "redline.proxy", "text": "Dialogue or a completion popup cannot perform the action."}
            ],
            "validation_hypotheses": [
                {
                    "claim_id": "hypothesis.cause",
                    "text": "The player can explain why the returned opportunity changed.",
                    "validation_method_id": "post_play_debrief",
                    "falsification_signal": "The recorded answer cannot connect the action to the returned change.",
                    "status": "TESTABLE_DESIGN",
                }
            ],
            "decision_payload_sha256": "",
            "human_verdict": {"status": "PENDING", "source_text": "PENDING", "recorded_at": "PENDING"},
        }
        attach_project_review(
            self.repo,
            self.objective_dir,
            self.card,
            interaction_contract_ref=contract_ref,
            interaction_contract_review_ref=contract_review_ref,
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def validate(self) -> list[str]:
        errors: list[str] = []
        _validate_decision_card(
            game_repo=self.repo,
            card_path=self.card_path,
            project_id="portable-game",
            objective_id="direct-unit",
            factory_revision=self.revision,
            context_status=READY_FOR_NEW_GAMEPLAY_DESIGN,
            errors=errors,
            pre_human_review=True,
        )
        return errors

    def rewrite_project_review(self, mutate) -> None:
        review_path = self.objective_dir / PROJECT_REVIEW_NAME
        review = json.loads(review_path.read_text())
        mutate(review)
        write_json(review_path, review)
        card = json.loads(self.card_path.read_text())
        card["project_card_review"] = ref(self.repo, review_path)
        write_json(self.card_path, card)

    def test_two_different_project_profiles_pass_without_genre_defaults(self) -> None:
        self.assertEqual([], self.validate())
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = design_gate_main(
                [
                    "validate-project-card-review",
                    "--game-repo",
                    str(self.repo),
                    "--card",
                    str(self.card_path),
                ]
            )
        self.assertEqual(0, code)
        self.assertIn("PASS_PROJECT_CARD_AUTHORING_STANDARD", stdout.getvalue())
        other_temp = tempfile.TemporaryDirectory()
        self.addCleanup(other_temp.cleanup)
        other_repo = Path(other_temp.name) / "turn_game"
        other_repo.mkdir()
        objective = other_repo / "design/gameplay/objective_gameplay/direct-unit"
        contract_ref, review_ref, _ = write_contract_pair(
            other_repo,
            objective,
            project_id="portable-game",
            objective_id="direct-unit",
            factory_revision=self.revision,
            product_ref={"path": "", "sha256": ""},
            system_ref={"path": "", "sha256": ""},
            transition_ids=["read", "commit", "return"],
        )
        card = copy.deepcopy(self.card)
        for field in (
            "project_card_authoring_standard",
            "project_composition_artifacts",
            "project_card_review",
        ):
            card.pop(field, None)
        card["player_facing_interaction_contract"] = contract_ref
        card["player_facing_interaction_contract_review"] = review_ref
        attach_project_review(
            other_repo,
            objective,
            card,
            interaction_contract_ref=contract_ref,
            interaction_contract_review_ref=review_ref,
            profile_kind="turn",
        )
        errors: list[str] = []
        _validate_decision_card(
            game_repo=other_repo,
            card_path=objective / "GAMEPLAY_DECISION_CARD.json",
            project_id="portable-game",
            objective_id="direct-unit",
            factory_revision=self.revision,
            context_status=READY_FOR_NEW_GAMEPLAY_DESIGN,
            errors=errors,
            pre_human_review=True,
        )
        self.assertEqual([], errors)

    def test_factory_contracts_define_only_the_portable_project_envelope(self) -> None:
        gameplay_root = Path(__file__).resolve().parents[1]
        standard_schema = json.loads(
            (
                gameplay_root
                / "schemas/project_gameplay_decision_card_standard.schema.json"
            ).read_text()
        )
        review_schema = json.loads(
            (
                gameplay_root
                / "schemas/gameplay_decision_card_project_review.schema.json"
            ).read_text()
        )
        card_schema = json.loads(
            (gameplay_root / "schemas/gameplay_decision_card.schema.json").read_text()
        )
        standard_template = json.loads(
            (
                gameplay_root
                / "templates/PROJECT_GAMEPLAY_DECISION_CARD_STANDARD.json"
            ).read_text()
        )
        self.assertEqual(
            "project_gameplay_decision_card_standard.v1",
            standard_schema["properties"]["schema_version"]["const"],
        )
        self.assertEqual(
            "gameplay_decision_card_project_review.v1",
            review_schema["properties"]["schema_version"]["const"],
        )
        standard_ref_schema = card_schema["$defs"]["versioned_path_hash"]
        self.assertEqual(
            {"path", "version", "sha256"},
            set(standard_ref_schema["required"]),
        )
        self.assertEqual("DRAFT_NOT_ADOPTED", standard_template["status"])
        self.assertEqual("NOT_ADOPTED", standard_template["adoption"]["status"])
        self.assertTrue(
            all("<" in json.dumps(item) for item in standard_template["vocabulary"])
        )
        self.assertTrue(
            all("<" in json.dumps(item) for item in standard_template["requirements"])
        )
        serialized = json.dumps(standard_template).lower()
        for project_rule in (
            "free movement",
            "social consequence",
            "dialogue order",
        ):
            self.assertNotIn(project_rule, serialized)

    def test_missing_project_standard_is_rejected(self) -> None:
        (self.repo / STANDARD_RELATIVE).unlink()
        self.assertTrue(any("standard" in item and "file" in item for item in self.validate()))

    def test_blank_or_tbd_standard_cannot_be_active(self) -> None:
        template = json.loads(
            (
                Path(__file__).resolve().parents[1]
                / "templates/PROJECT_GAMEPLAY_DECISION_CARD_STANDARD.json"
            ).read_text()
        )
        standard_path = write_json(self.repo / STANDARD_RELATIVE, template)
        card = json.loads(self.card_path.read_text())
        card["project_card_authoring_standard"] = ref(self.repo, standard_path)
        card["decision_payload_sha256"] = decision_payload_sha256(card)
        profile = self.repo / "design/gameplay/adapter/PROJECT_GAMEPLAY_PROFILE.md"
        profile.write_text(
            "# Project Gameplay Profile — `portable-game`\n\n"
            f"- Project Card authoring standard path: `{STANDARD_RELATIVE.as_posix()}`\n"
            "- Project Card authoring standard version: `<PROJECT_STANDARD_VERSION>`\n"
            f"- Project Card authoring standard SHA-256: `{ref(self.repo, standard_path)['sha256']}`\n"
            "- Project Card authoring standard status: `ACTIVE`\n"
        )
        write_json(self.card_path, card)
        errors = self.validate()
        self.assertTrue(any("placeholder" in item for item in errors))
        self.assertTrue(any("status must be ACTIVE" in item for item in errors))

    def test_absolute_or_factory_owned_standard_path_is_rejected(self) -> None:
        card = json.loads(self.card_path.read_text())
        card["project_card_authoring_standard"]["path"] = str(
            Path(__file__).resolve().parents[1]
            / "templates/PROJECT_GAMEPLAY_DECISION_CARD_STANDARD.json"
        )
        card["decision_payload_sha256"] = decision_payload_sha256(card)
        write_json(self.card_path, card)
        self.assertTrue(any("game-repo-relative" in item for item in self.validate()))

    def test_stale_standard_sha_is_rejected(self) -> None:
        standard = self.repo / STANDARD_RELATIVE
        payload = json.loads(standard.read_text())
        payload["repeatable_lap"].append("A material new lap rule.")
        write_json(standard, payload)
        self.assertTrue(any("hash does not match" in item for item in self.validate()))

    def test_missing_or_stale_composition_is_rejected(self) -> None:
        composition = self.repo / self.card["project_composition_artifacts"][0]["path"]
        composition.unlink()
        self.assertTrue(any("composition" in item and "file" in item for item in self.validate()))

    def test_stale_composition_hash_is_rejected(self) -> None:
        composition = self.repo / self.card["project_composition_artifacts"][0]["path"]
        with composition.open("a", encoding="utf-8") as stream:
            stream.write("\nmaterial project composition revision\n")
        self.assertTrue(
            any("composition" in item and "hash does not match" in item for item in self.validate())
        )

    def test_project_review_must_inventory_every_standard_requirement(self) -> None:
        self.rewrite_project_review(lambda review: review["requirement_findings"].pop())
        self.assertTrue(any("misses declared standard requirements" in item for item in self.validate()))

    def test_project_review_must_use_each_requirement_declared_evidence_surface(self) -> None:
        def mutate(review: dict) -> None:
            finding = next(
                item
                for item in review["requirement_findings"]
                if item["requirement_id"] == "project.rendered-completeness"
            )
            finding["evidence_refs"] = [
                {
                    "surface": "COMPOSITION_ARTIFACT",
                    "ref": review["project_composition_artifacts"][0]["artifact_id"],
                }
            ]

        self.rewrite_project_review(mutate)
        self.assertTrue(
            any("declared CARD evidence surface" in item for item in self.validate())
        )

    def test_project_reviewer_must_differ_from_all_material_authors(self) -> None:
        for author_field in (
            "composition_artifact_authors",
            "interaction_contract_author",
            "decision_card_author",
        ):
            with self.subTest(author_field=author_field):
                def mutate(review: dict, field: str = author_field) -> None:
                    value = review["author_context_ids"][field]
                    review["reviewer_context_id"] = value[0] if isinstance(value, list) else value

                self.rewrite_project_review(mutate)
                self.assertTrue(
                    any("reviewer must differ" in item for item in self.validate())
                )

    def test_pass_project_review_cannot_contain_blocking_findings(self) -> None:
        self.rewrite_project_review(
            lambda review: review["blocking_findings"].append("Unresolved scene boundary")
        )
        self.assertTrue(any("blocking_findings must be empty" in item for item in self.validate()))

    def test_direct_specialist_render_and_verdict_fail_without_project_review(self) -> None:
        (self.objective_dir / PROJECT_REVIEW_NAME).unlink()
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            code = design_gate_main(
                [
                    "render-card",
                    "--game-repo",
                    str(self.repo),
                    "--card",
                    str(self.card_path),
                ]
            )
        self.assertEqual(2, code)
        self.assertIn("project Card review", stderr.getvalue())
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            code = design_gate_main(
                [
                    "record-card-verdict",
                    "--game-repo",
                    str(self.repo),
                    "--card",
                    str(self.card_path),
                    "--verdict-token",
                    "USER_APPROVED " + self.card["decision_payload_sha256"],
                    "--recorded-at",
                    "2026-09-04T11:00:00Z",
                ]
            )
        self.assertEqual(2, code)
        self.assertIn("project Card review", stderr.getvalue())

    def test_direct_specialist_exact_project_chain_allows_render_and_verdict(self) -> None:
        rendered = io.StringIO()
        with redirect_stdout(rendered):
            code = design_gate_main(
                [
                    "render-card",
                    "--game-repo",
                    str(self.repo),
                    "--card",
                    str(self.card_path),
                ]
            )
        self.assertEqual(0, code)
        card = json.loads(self.card_path.read_text())
        digest = card["decision_payload_sha256"]
        self.assertIn(digest, rendered.getvalue())
        with redirect_stdout(io.StringIO()):
            code = design_gate_main(
                [
                    "record-card-verdict",
                    "--game-repo",
                    str(self.repo),
                    "--card",
                    str(self.card_path),
                    "--verdict-token",
                    "USER_APPROVED " + digest,
                    "--recorded-at",
                    "2026-09-04T11:00:00Z",
                ]
            )
        self.assertEqual(0, code)
        recorded = json.loads(self.card_path.read_text())
        self.assertEqual("USER_APPROVED", recorded["human_verdict"]["status"])

    def test_pending_card_becomes_ineligible_after_active_standard_revision(self) -> None:
        standard_path = self.repo / STANDARD_RELATIVE
        standard = json.loads(standard_path.read_text())
        standard["version"] = "v2"
        standard["requirements"].append(
            {
                "requirement_id": "project.failure-detail",
                "rule": "The Card exposes the material recovery consequence.",
                "applicability": "Always.",
                "evidence_surface": "CARD",
            }
        )
        write_json(standard_path, standard)
        new_ref = ref(self.repo, standard_path)
        profile = self.repo / "design/gameplay/adapter/PROJECT_GAMEPLAY_PROFILE.md"
        profile.write_text(
            "# Project Gameplay Profile — `portable-game`\n\n"
            f"- Project Card authoring standard path: `{new_ref['path']}`\n"
            "- Project Card authoring standard version: `v2`\n"
            f"- Project Card authoring standard SHA-256: `{new_ref['sha256']}`\n"
            "- Project Card authoring standard status: `ACTIVE`\n"
        )
        stderr = io.StringIO()
        with redirect_stderr(stderr), redirect_stdout(io.StringIO()):
            code = design_gate_main(
                [
                    "render-card",
                    "--game-repo",
                    str(self.repo),
                    "--card",
                    str(self.card_path),
                ]
            )
        self.assertEqual(2, code)
        self.assertIn("standard SHA differs", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
