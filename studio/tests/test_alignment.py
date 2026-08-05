from __future__ import annotations

import hashlib
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from gameplay.design_gate import (
    decision_payload_sha256,
    main as design_gate_main,
    render_decision_card,
)
from studio.alignment import (
    AlignmentValidationError,
    HUMAN_RULING_GENUINELY_REQUIRED,
    current_factory_revision,
    load_decision_register,
    record_card_verdict,
    register_pending_card,
    require_registered_card,
    text_sha256,
    validate_alignment_review,
)


def write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def ref(repo: Path, path: Path) -> dict[str, str]:
    return {
        "path": path.resolve().relative_to(repo.resolve()).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


class StudioSemanticAlignmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name) / "game"
        self.repo.mkdir()
        self.revision = current_factory_revision()
        self.product = self.repo / "design/product/PRODUCT_THESIS.md"
        self.product.parent.mkdir(parents=True)
        self.product.write_text(
            "# Product Thesis\n\nPrice judgment is the battle.\n", encoding="utf-8"
        )
        self.user_text = "I have a new idea: make the loser counterpick the winner's card."

    def tearDown(self) -> None:
        self.temp.cleanup()

    def card(self, objective_id: str) -> dict:
        card = {
            "schema_version": "gameplay_decision_card.v1",
            "card_id": f"card.{objective_id}",
            "project_id": "sample",
            "objective_id": objective_id,
            "factory_revision": self.revision,
            "routing": "STUDIO_WHOLE_GAME",
            "product_authority": ref(self.repo, self.product),
            "studio_gameplay_system": {
                "path": "design/studio/gameplay_system/sample/STUDIO_GAMEPLAY_SYSTEM_MANIFEST.json",
                "sha256": "1" * 64,
            },
            "author_context_id": f"author.{objective_id}",
            "player_promise": {
                "claim_id": "promise.system",
                "text": "The result changes the next legal card-price decision.",
            },
            "core_cycle": [
                {"claim_id": "cycle.choose", "text": "Choose one market challenge."},
                {"claim_id": "cycle.resolve", "text": "Resolve it from the market."},
                {"claim_id": "cycle.return", "text": "Counterpick under changed rules."},
            ],
            "material_commitments": [
                {"claim_id": "commitment.counterpick", "text": "The loser counterpicks."}
            ],
            "red_lines": [
                {"claim_id": "redline.1", "text": "Watching a score is not a battle move."}
            ],
            "validation_hypotheses": [],
            "decision_payload_sha256": "",
            "human_verdict": {
                "status": "PENDING",
                "source_text": "PENDING",
                "recorded_at": "PENDING",
            },
        }
        card["decision_payload_sha256"] = decision_payload_sha256(card)
        return card

    def alignment_artifacts(
        self,
        card_path: Path,
        *,
        interaction_id: str,
        pending: list[dict] | None = None,
        reviewer: str = "fresh.reviewer",
    ) -> tuple[Path, Path]:
        card = json.loads(card_path.read_text(encoding="utf-8"))
        rendered = render_decision_card(card)
        root = self.repo / f"design/studio/interaction_alignment/{interaction_id}"
        input_path = root / "STUDIO_SEMANTIC_ALIGNMENT_INPUT.json"
        alignment_input = {
            "schema_version": "studio_semantic_alignment_input.v1",
            "interaction_id": interaction_id,
            "project_id": "sample",
            "factory_revision": self.revision,
            "trigger": "HUMAN_DECISION_SURFACE",
            "author_context_id": card["author_context_id"],
            "user_input": {
                "text": self.user_text,
                "sha256": text_sha256(self.user_text),
            },
            "active_authorities": [
                {
                    "authority_id": "product.current",
                    "authority_kind": "PRODUCT",
                    "artifact": ref(self.repo, self.product),
                }
            ],
            "pending_decisions": pending or [],
            "input_deltas": [
                {
                    "delta_id": "delta.counterpick",
                    "source_quote": "make the loser counterpick the winner's card",
                    "classification": "ADD",
                    "target_authority_ids": ["product.current"],
                    "interpretation": "Add a result-bound counterpick without replacing price judgment.",
                }
            ],
            "proposed_transition": "REQUEST_HUMAN_RULING",
            "candidate_output": {
                "kind": "DECISION_SURFACE",
                "text": rendered,
                "sha256": text_sha256(rendered),
            },
            "output_claims": [
                {
                    "claim_id": "output.promise",
                    "output_quote": card["player_promise"]["text"],
                    "provenance": "PRESERVED_AUTHORITY",
                    "source_authority_ids": ["product.current"],
                    "source_quotes": [],
                },
                {
                    "claim_id": "output.counterpick",
                    "output_quote": "The loser counterpicks.",
                    "provenance": "NEW_USER_INPUT",
                    "source_authority_ids": [],
                    "source_quotes": ["make the loser counterpick the winner's card"],
                },
            ],
            "human_questions": [
                {
                    "question_id": "question.approve",
                    "question_quote": f"Reply: `USER_APPROVED {card['decision_payload_sha256']}`",
                    "material_consequence": "Approval authorizes full-spec refinement.",
                    "searched_authority_ids": ["product.current"],
                    "why_unresolved": "Only the user may approve a Studio decision surface.",
                }
            ],
            "authored_at": "2026-08-05T15:00:00+08:00",
        }
        write_json(input_path, alignment_input)
        review_path = root / "STUDIO_SEMANTIC_ALIGNMENT_REVIEW.json"
        checks = {
            "input_delta_complete": "PASS",
            "authority_continuity": "PASS",
            "claim_provenance": "PASS",
            "question_necessity": "PASS",
            "semantic_non_substitution": "PASS",
            "routing_and_scope": "PASS",
            "human_boundary": "PASS",
            "surface_proportionality": "PASS",
            "pending_decision_disposition": "PASS",
        }
        review = {
            "schema_version": "studio_semantic_alignment_review.v1",
            "review_id": f"review.{interaction_id}",
            "project_id": "sample",
            "factory_revision": self.revision,
            "alignment_input": ref(self.repo, input_path),
            "reviewer_context_id": reviewer,
            "reviewer_freshness": "FRESH",
            "checks": checks,
            "findings": [
                {
                    "finding_id": "finding.aligned",
                    "status": "PASS",
                    "user_input_quote": "make the loser counterpick the winner's card",
                    "authority_ids": ["product.current"],
                    "candidate_output_quote": "The loser counterpicks.",
                    "rationale": "The output preserves the price-battle authority and realizes the new delta.",
                }
            ],
            "blocking_findings": [],
            "verdict": "HUMAN_RULING_GENUINELY_REQUIRED",
            "reviewed_at": "2026-08-05T15:01:00+08:00",
        }
        write_json(review_path, review)
        return input_path, review_path

    def test_fresh_alignment_review_can_present_exact_decision_surface(self) -> None:
        card_path = write_json(
            self.repo / "design/gameplay/objective_gameplay/first/GAMEPLAY_DECISION_CARD.json",
            self.card("first"),
        )
        input_path, review_path = self.alignment_artifacts(
            card_path, interaction_id="turn.first"
        )
        result = validate_alignment_review(
            self.repo,
            input_path,
            review_path,
            expected_output_text=render_decision_card(json.loads(card_path.read_text())),
            expected_output_kind="DECISION_SURFACE",
        )
        self.assertEqual(HUMAN_RULING_GENUINELY_REQUIRED, result.status, result.errors)
        self.assertEqual([], result.errors)

    def test_candidate_author_cannot_self_review(self) -> None:
        card_path = write_json(
            self.repo / "design/gameplay/objective_gameplay/first/GAMEPLAY_DECISION_CARD.json",
            self.card("first"),
        )
        card = json.loads(card_path.read_text())
        input_path, review_path = self.alignment_artifacts(
            card_path,
            interaction_id="turn.first",
            reviewer=card["author_context_id"],
        )
        result = validate_alignment_review(self.repo, input_path, review_path)
        self.assertTrue(any("must be fresh" in error for error in result.errors))

    def test_new_registered_card_supersedes_old_pending_payload(self) -> None:
        old_path = write_json(
            self.repo / "design/gameplay/objective_gameplay/old/GAMEPLAY_DECISION_CARD.json",
            self.card("old"),
        )
        old_input, old_review = self.alignment_artifacts(
            old_path, interaction_id="turn.old"
        )
        old_card = json.loads(old_path.read_text())
        register_pending_card(
            self.repo,
            old_path,
            old_input,
            old_review,
            expected_output_text=render_decision_card(old_card),
            supersede_payloads=[],
            recorded_at="2026-08-05T15:02:00+08:00",
        )

        new_path = write_json(
            self.repo / "design/gameplay/objective_gameplay/new/GAMEPLAY_DECISION_CARD.json",
            self.card("new"),
        )
        pending = [
            {
                "decision_payload_sha256": old_card["decision_payload_sha256"],
                "decision_card": ref(self.repo, old_path),
                "disposition": "SUPERSEDE_PENDING",
            }
        ]
        new_input, new_review = self.alignment_artifacts(
            new_path, interaction_id="turn.new", pending=pending
        )
        new_card = json.loads(new_path.read_text())
        register_pending_card(
            self.repo,
            new_path,
            new_input,
            new_review,
            expected_output_text=render_decision_card(new_card),
            supersede_payloads=[old_card["decision_payload_sha256"]],
            recorded_at="2026-08-05T15:03:00+08:00",
        )

        register, errors = load_decision_register(self.repo)
        self.assertEqual([], errors)
        by_payload = {
            item["decision_payload_sha256"]: item for item in register["entries"]
        }
        self.assertEqual(
            "SUPERSEDED", by_payload[old_card["decision_payload_sha256"]]["state"]
        )
        self.assertEqual(
            new_card["decision_payload_sha256"],
            by_payload[old_card["decision_payload_sha256"]]["superseded_by"],
        )
        old_errors: list[str] = []
        require_registered_card(
            self.repo, old_path, required_state="PENDING", errors=old_errors
        )
        self.assertTrue(any("superseded" in error for error in old_errors))
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            exit_code = design_gate_main(
                [
                    "render-card",
                    "--game-repo",
                    str(self.repo),
                    "--card",
                    str(old_path),
                ]
            )
        self.assertEqual(2, exit_code)
        self.assertIn("superseded", stderr.getvalue())
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = design_gate_main(
                [
                    "render-card",
                    "--game-repo",
                    str(self.repo),
                    "--card",
                    str(new_path),
                ]
            )
        self.assertEqual(0, exit_code)
        self.assertIn(new_card["decision_payload_sha256"], stdout.getvalue())
        with self.assertRaisesRegex(AlignmentValidationError, "superseded payload"):
            record_card_verdict(
                self.repo,
                old_path,
                verdict_token=f"USER_APPROVED {old_card['decision_payload_sha256']}",
                recorded_at="2026-08-05T15:04:00+08:00",
            )

    def test_exact_verdict_promotes_registered_pending_card(self) -> None:
        card_path = write_json(
            self.repo / "design/gameplay/objective_gameplay/first/GAMEPLAY_DECISION_CARD.json",
            self.card("first"),
        )
        input_path, review_path = self.alignment_artifacts(
            card_path, interaction_id="turn.first"
        )
        card = json.loads(card_path.read_text())
        register_pending_card(
            self.repo,
            card_path,
            input_path,
            review_path,
            expected_output_text=render_decision_card(card),
            supersede_payloads=[],
            recorded_at="2026-08-05T15:02:00+08:00",
        )
        token = f"USER_APPROVED {card['decision_payload_sha256']}"
        record_card_verdict(
            self.repo,
            card_path,
            verdict_token=token,
            recorded_at="2026-08-05T15:03:00+08:00",
        )
        errors: list[str] = []
        require_registered_card(
            self.repo, card_path, required_state="USER_APPROVED", errors=errors
        )
        self.assertEqual([], errors)
        updated = json.loads(card_path.read_text())
        self.assertEqual("USER_APPROVED", updated["human_verdict"]["status"])
        self.assertEqual(token, updated["human_verdict"]["source_text"])

    def test_first_register_can_invalidate_pre_register_pending_card(self) -> None:
        old_path = write_json(
            self.repo / "design/gameplay/objective_gameplay/legacy/GAMEPLAY_DECISION_CARD.json",
            self.card("legacy"),
        )
        old_card = json.loads(old_path.read_text())
        new_path = write_json(
            self.repo / "design/gameplay/objective_gameplay/new/GAMEPLAY_DECISION_CARD.json",
            self.card("new"),
        )
        pending = [
            {
                "decision_payload_sha256": old_card["decision_payload_sha256"],
                "decision_card": ref(self.repo, old_path),
                "disposition": "SUPERSEDE_PENDING",
            }
        ]
        input_path, review_path = self.alignment_artifacts(
            new_path, interaction_id="turn.migrate", pending=pending
        )
        new_card = json.loads(new_path.read_text())
        register_pending_card(
            self.repo,
            new_path,
            input_path,
            review_path,
            expected_output_text=render_decision_card(new_card),
            supersede_payloads=[old_card["decision_payload_sha256"]],
            recorded_at="2026-08-05T15:05:00+08:00",
        )
        register, errors = load_decision_register(self.repo)
        self.assertEqual([], errors)
        by_payload = {
            item["decision_payload_sha256"]: item for item in register["entries"]
        }
        self.assertEqual(
            "SUPERSEDED", by_payload[old_card["decision_payload_sha256"]]["state"]
        )
        self.assertEqual(
            "PENDING", by_payload[new_card["decision_payload_sha256"]]["state"]
        )


if __name__ == "__main__":
    unittest.main()
