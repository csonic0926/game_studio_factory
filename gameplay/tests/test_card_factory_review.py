from __future__ import annotations

import copy
import hashlib
import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from gameplay.design_gate import (
    CARD_FACTORY_REVIEW_NAME,
    CARD_FACTORY_REVIEW_AUTHORITY_ID,
    FINAL_CARD_REQUIREMENT_CLAIM_PREFIXES,
    FINAL_CARD_REQUIREMENT_IDS,
    PASS_CARD_FACTORY_REVIEW,
    READY_FOR_NEW_GAMEPLAY_DESIGN,
    _validate_decision_card,
    decision_payload_sha256,
    main as design_gate_main,
    render_decision_card,
    validate_card_factory_review,
)
from studio.tests import test_alignment, test_cycle


def write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def ref(repo: Path, path: Path) -> dict[str, str]:
    return {
        "path": path.resolve().relative_to(repo.resolve()).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


class FinalCardFactoryReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cycle_fixture = test_cycle.StudioGameplayCycleTests(
            methodName="test_cycle_complete_system_is_ready"
        )
        self.cycle_fixture.setUp()
        self.addCleanup(self.cycle_fixture.tearDown)
        self.repo = self.cycle_fixture.repo
        self.revision = self.cycle_fixture.factory_revision
        self.system_path = self.repo / self.cycle_fixture.system_relative
        self.manifest_path = self.repo / self.cycle_fixture.manifest_relative
        self.system = json.loads(self.system_path.read_text(encoding="utf-8"))
        self.objective_dir = (
            self.repo / "design/gameplay/objective_gameplay/final-card"
        )
        self.card_path = self.objective_dir / "GAMEPLAY_DECISION_CARD.json"
        self.review_path = self.objective_dir / CARD_FACTORY_REVIEW_NAME
        self.card = self.make_card()
        write_json(self.card_path, self.card)
        self.review = self.make_review()
        write_json(self.review_path, self.review)

    def make_card(self) -> dict:
        transitions = {
            item["transition_id"]: item for item in self.system["transitions"]
        }
        core_cycle = []
        for transition_id in self.system["cycle_path"]:
            transition = transitions[transition_id]
            core_cycle.append(
                {
                    "claim_id": f"cycle.{transition_id}",
                    "text": " -> ".join(
                        transition[field]
                        for field in (
                            "player_action",
                            "visible_consequence",
                            "motivation_effect",
                        )
                    ),
                }
            )
        card = {
            "schema_version": "gameplay_decision_card.v1",
            "card_id": "final-card.v1",
            "project_id": "sample",
            "objective_id": "final-card",
            "factory_revision": self.revision,
            "routing": "STUDIO_WHOLE_GAME",
            "product_authority": self.system["product_authority"],
            "studio_gameplay_system": ref(self.repo, self.manifest_path),
            "author_context_id": "card-author",
            "player_promise": {
                "claim_id": "promise.system",
                "text": self.system["system_promise"],
            },
            "core_cycle": core_cycle,
            "material_commitments": [
                {
                    "claim_id": f"commitment.{item['component_id']}",
                    "text": item["role"],
                }
                for item in self.system["coupled_systems"]
            ],
            "red_lines": [
                {"claim_id": f"redline.{index}", "text": text}
                for index, text in enumerate(
                    self.system["forbidden_linearizations"], start=1
                )
            ],
            "validation_hypotheses": [
                {
                    "claim_id": "expected.meaningful-work",
                    "text": "The player can explain the judgment made before committing.",
                    "falsification_signal": "The span is understood as certain clicks or passive presentation.",
                }
            ],
            "decision_payload_sha256": "",
            "human_verdict": {
                "status": "PENDING",
                "source_text": "PENDING",
                "recorded_at": "PENDING",
            },
        }
        card["decision_payload_sha256"] = decision_payload_sha256(card)
        return card

    def make_review(self) -> dict:
        claim_ids = [self.card["player_promise"]["claim_id"]]
        for field in (
            "core_cycle",
            "material_commitments",
            "red_lines",
            "validation_hypotheses",
        ):
            claim_ids.extend(item["claim_id"] for item in self.card[field])
        primary_claim = claim_ids[0]
        evidence_by_requirement = {
            requirement_id: [
                next(
                    claim_id
                    for claim_id in claim_ids
                    if claim_id.startswith(prefix)
                )
                for prefix in FINAL_CARD_REQUIREMENT_CLAIM_PREFIXES[requirement_id]
            ]
            for requirement_id in FINAL_CARD_REQUIREMENT_IDS
        }
        return {
            "schema_version": "gameplay_decision_card_factory_review.v1",
            "review_id": "final-card.factory-review.v1",
            "review_role": "FINAL_CARD_FACTORY_COMPLIANCE",
            "project_id": "sample",
            "objective_id": "final-card",
            "factory_revision": self.revision,
            "decision_card": {
                "path": self.card_path.relative_to(self.repo).as_posix(),
                "decision_payload_sha256": self.card["decision_payload_sha256"],
                "rendered_surface_sha256": hashlib.sha256(
                    render_decision_card(self.card).encode("utf-8")
                ).hexdigest(),
            },
            "product_authority": self.system["product_authority"],
            "studio_gameplay_system": ref(self.repo, self.manifest_path),
            "authority_inventory": {
                "product_causal_links": [
                    self.authority_finding(
                        item["link_id"], item["transition_ids"], primary_claim
                    )
                    for item in self.system["causal_link_coverage"]
                ],
                "factory_constraints": [
                    self.authority_finding(
                        item["constraint_id"], item["transition_ids"], primary_claim
                    )
                    for item in self.system["constraint_coverage"]
                ],
                "product_non_goals": [
                    self.authority_finding(
                        item["non_goal_id"], item["transition_ids"], primary_claim
                    )
                    for item in self.system["non_goal_coverage"]
                ],
            },
            "reviewer_context_id": "final-card-reviewer",
            "reviewer_freshness": "FRESH",
            "requirement_findings": {
                requirement_id: {
                    "verdict": "PASS",
                    "evidence_claim_ids": evidence_by_requirement[requirement_id],
                    "rationale": (
                        f"The exact typed Card claims satisfy {requirement_id}."
                    ),
                }
                for requirement_id in FINAL_CARD_REQUIREMENT_IDS
            },
            "claim_inventory": [
                {
                    "claim_id": claim_id,
                    "requirement_ids": [
                        FINAL_CARD_REQUIREMENT_IDS[
                            index % len(FINAL_CARD_REQUIREMENT_IDS)
                        ]
                    ],
                    "verdict": "PASS",
                    "rationale": "The exact Card claim is supported by the bound system.",
                }
                for index, claim_id in enumerate(claim_ids)
            ],
            "blocking_findings": [],
            "verdict": PASS_CARD_FACTORY_REVIEW,
            "reviewed_at": "2026-08-31T12:00:00+08:00",
        }

    @staticmethod
    def authority_finding(
        authority_id: str, transition_ids: list[str], fallback_claim_id: str
    ) -> dict:
        evidence_claim_ids = [
            f"cycle.{transition_id}" for transition_id in transition_ids
        ] or [fallback_claim_id]
        return {
            "authority_id": authority_id,
            "system_transition_ids": transition_ids,
            "requirement_ids": ["active_authority_and_scope_preserved"],
            "evidence_claim_ids": evidence_claim_ids,
            "verdict": "PASS",
            "rationale": (
                f"The exact projected transition claims preserve authority {authority_id}."
            ),
        }

    def test_exact_fresh_whole_result_review_passes(self) -> None:
        result = validate_card_factory_review(
            self.repo, self.card_path, self.review_path
        )
        self.assertEqual(PASS_CARD_FACTORY_REVIEW, result.status, result.errors)
        self.assertEqual([], result.errors)

    def test_missing_claim_inventory_entry_fails_closed(self) -> None:
        review = copy.deepcopy(self.review)
        review["claim_inventory"].pop()
        write_json(self.review_path, review)
        result = validate_card_factory_review(
            self.repo, self.card_path, self.review_path
        )
        self.assertEqual("BLOCKED", result.status)
        self.assertTrue(any("misses Card claims" in item for item in result.errors))

    def test_nonpassing_factory_requirement_fails_closed(self) -> None:
        review = copy.deepcopy(self.review)
        review["requirement_findings"]["meaningful_choice_not_certain_click"][
            "verdict"
        ] = "BLOCK"
        write_json(self.review_path, review)
        result = validate_card_factory_review(
            self.repo, self.card_path, self.review_path
        )
        self.assertEqual("BLOCKED", result.status)
        self.assertTrue(
            any("meaningful_choice_not_certain_click.verdict" in item for item in result.errors)
        )

    def test_requirement_finding_cannot_cite_one_unrelated_claim_type(self) -> None:
        review = copy.deepcopy(self.review)
        review["requirement_findings"]["non_gameplay_activity_not_counted"][
            "evidence_claim_ids"
        ] = [self.card["player_promise"]["claim_id"]]
        write_json(self.review_path, review)
        result = validate_card_factory_review(
            self.repo, self.card_path, self.review_path
        )
        self.assertEqual("BLOCKED", result.status)
        self.assertTrue(
            any("must include a redline. Card claim" in item for item in result.errors)
        )

    def test_review_must_be_fresh_from_all_prior_card_system_contexts(self) -> None:
        review = copy.deepcopy(self.review)
        review["reviewer_context_id"] = "system-author"
        write_json(self.review_path, review)
        result = validate_card_factory_review(
            self.repo, self.card_path, self.review_path
        )
        self.assertEqual("BLOCKED", result.status)
        self.assertTrue(any("must be fresh" in item for item in result.errors))

    def test_authority_inventory_must_cover_every_bound_factory_constraint(self) -> None:
        review = copy.deepcopy(self.review)
        review["authority_inventory"]["factory_constraints"].pop()
        write_json(self.review_path, review)
        result = validate_card_factory_review(
            self.repo, self.card_path, self.review_path
        )
        self.assertEqual("BLOCKED", result.status)
        self.assertTrue(
            any("factory_constraints must exactly cover" in item for item in result.errors)
        )

    def test_each_authority_requires_an_explicit_card_requirement_mapping(self) -> None:
        review = copy.deepcopy(self.review)
        review["authority_inventory"]["factory_constraints"][0][
            "requirement_ids"
        ] = []
        write_json(self.review_path, review)
        result = validate_card_factory_review(
            self.repo, self.card_path, self.review_path
        )
        self.assertEqual("BLOCKED", result.status)
        self.assertTrue(
            any(
                "factory_constraints[0].requirement_ids must be a non-empty array"
                in item
                for item in result.errors
            )
        )

    def test_each_authority_must_map_its_exact_system_transitions_to_card_claims(self) -> None:
        review = copy.deepcopy(self.review)
        finding = review["authority_inventory"]["factory_constraints"][0]
        finding["system_transition_ids"] = finding["system_transition_ids"][:-1]
        write_json(self.review_path, review)
        result = validate_card_factory_review(
            self.repo, self.card_path, self.review_path
        )
        self.assertEqual("BLOCKED", result.status)
        self.assertTrue(
            any(
                "system_transition_ids must exactly match" in item
                for item in result.errors
            )
        )

    def test_review_must_bind_the_exact_rendered_card(self) -> None:
        review = copy.deepcopy(self.review)
        review["decision_card"]["rendered_surface_sha256"] = "0" * 64
        write_json(self.review_path, review)
        result = validate_card_factory_review(
            self.repo, self.card_path, self.review_path
        )
        self.assertEqual("BLOCKED", result.status)
        self.assertTrue(any("rendered Card surface" in item for item in result.errors))

    def test_semantic_reviewer_cannot_reuse_final_card_reviewer_context(self) -> None:
        result = validate_card_factory_review(
            self.repo,
            self.card_path,
            self.review_path,
            forbidden_context_ids={"final-card-reviewer"},
        )
        self.assertEqual("BLOCKED", result.status)
        self.assertTrue(any("semantic-alignment reviewer" in item for item in result.errors))

    def test_register_and_render_require_both_distinct_final_reviews(self) -> None:
        alignment_fixture = test_alignment.StudioSemanticAlignmentTests(
            methodName="test_fresh_alignment_review_can_present_exact_decision_surface"
        )
        alignment_fixture.repo = self.repo
        alignment_fixture.revision = self.revision
        alignment_fixture.product = self.repo / "design/product/PRODUCT_THESIS.md"
        alignment_fixture.user_text = (
            "I have a new idea: make the loser counterpick the winner's card."
        )
        alignment_input, alignment_review = alignment_fixture.alignment_artifacts(
            self.card_path,
            interaction_id="turn.final-card",
            reviewer="semantic-reviewer",
        )
        unbound_stderr = io.StringIO()
        with redirect_stderr(unbound_stderr):
            unbound_exit = design_gate_main(
                [
                    "register-card",
                    "--game-repo",
                    str(self.repo),
                    "--card",
                    str(self.card_path),
                    "--factory-compliance-review",
                    str(self.review_path),
                    "--alignment-input",
                    str(alignment_input),
                    "--alignment-review",
                    str(alignment_review),
                    "--recorded-at",
                    "2026-08-31T12:04:00+08:00",
                ]
            )
        self.assertEqual(2, unbound_exit)
        self.assertIn(
            "must bind the exact final Card Factory review",
            unbound_stderr.getvalue(),
        )

        alignment_input_payload = json.loads(
            alignment_input.read_text(encoding="utf-8")
        )
        alignment_input_payload["active_authorities"].append(
            {
                "authority_id": CARD_FACTORY_REVIEW_AUTHORITY_ID,
                "authority_kind": "REPO_EVIDENCE",
                "artifact": ref(self.repo, self.review_path),
            }
        )
        write_json(alignment_input, alignment_input_payload)
        alignment_payload = json.loads(alignment_review.read_text(encoding="utf-8"))
        alignment_payload["alignment_input"] = ref(self.repo, alignment_input)
        alignment_payload["findings"][0]["candidate_output_quote"] = (
            f"**Promise:** {self.card['player_promise']['text']}"
        )
        write_json(alignment_review, alignment_payload)

        stderr = io.StringIO()
        stdout = io.StringIO()
        with redirect_stderr(stderr), redirect_stdout(stdout):
            exit_code = design_gate_main(
                [
                    "register-card",
                    "--game-repo",
                    str(self.repo),
                    "--card",
                    str(self.card_path),
                    "--factory-compliance-review",
                    str(self.review_path),
                    "--alignment-input",
                    str(alignment_input),
                    "--alignment-review",
                    str(alignment_review),
                    "--recorded-at",
                    "2026-08-31T12:05:00+08:00",
                ]
            )
        self.assertEqual(0, exit_code, stderr.getvalue())

        rendered = io.StringIO()
        with redirect_stderr(stderr), redirect_stdout(rendered):
            exit_code = design_gate_main(
                [
                    "render-card",
                    "--game-repo",
                    str(self.repo),
                    "--card",
                    str(self.card_path),
                ]
            )
        self.assertEqual(0, exit_code, stderr.getvalue())
        self.assertEqual(render_decision_card(self.card), rendered.getvalue())

        self.review_path.unlink()
        missing_review_stderr = io.StringIO()
        with redirect_stderr(missing_review_stderr):
            exit_code = design_gate_main(
                [
                    "render-card",
                    "--game-repo",
                    str(self.repo),
                    "--card",
                    str(self.card_path),
                ]
            )
        self.assertEqual(2, exit_code)
        self.assertIn(
            "cannot read final Card Factory review",
            missing_review_stderr.getvalue(),
        )
        missing_record_stderr = io.StringIO()
        with redirect_stderr(missing_record_stderr):
            missing_record_exit = design_gate_main(
                [
                    "record-card-verdict",
                    "--game-repo",
                    str(self.repo),
                    "--card",
                    str(self.card_path),
                    "--verdict-token",
                    f"USER_APPROVED {self.card['decision_payload_sha256']}",
                    "--recorded-at",
                    "2026-08-31T12:06:00+08:00",
                ]
            )
        self.assertEqual(2, missing_record_exit)
        self.assertIn(
            "cannot read final Card Factory review",
            missing_record_stderr.getvalue(),
        )

        write_json(self.review_path, self.review)
        record_stderr = io.StringIO()
        with redirect_stderr(record_stderr):
            record_exit = design_gate_main(
                [
                    "record-card-verdict",
                    "--game-repo",
                    str(self.repo),
                    "--card",
                    str(self.card_path),
                    "--verdict-token",
                    f"USER_APPROVED {self.card['decision_payload_sha256']}",
                    "--recorded-at",
                    "2026-08-31T12:06:00+08:00",
                ]
            )
        self.assertEqual(0, record_exit, record_stderr.getvalue())
        production_errors: list[str] = []
        _validate_decision_card(
            game_repo=self.repo,
            card_path=self.card_path,
            project_id="sample",
            objective_id="final-card",
            factory_revision=self.revision,
            context_status=READY_FOR_NEW_GAMEPLAY_DESIGN,
            errors=production_errors,
        )
        self.assertEqual([], production_errors)

        self.review_path.unlink()
        production_errors = []
        _validate_decision_card(
            game_repo=self.repo,
            card_path=self.card_path,
            project_id="sample",
            objective_id="final-card",
            factory_revision=self.revision,
            context_status=READY_FOR_NEW_GAMEPLAY_DESIGN,
            errors=production_errors,
        )
        self.assertTrue(
            any("cannot read final Card Factory review" in item for item in production_errors)
        )


if __name__ == "__main__":
    unittest.main()
