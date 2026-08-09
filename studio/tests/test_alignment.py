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
    material_output_lines,
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
        question_quote = f"Reply: `USER_APPROVED {card['decision_payload_sha256']}`"
        claims = []
        for index, line in enumerate(material_output_lines(rendered, [question_quote]), 1):
            provenance = "AI_SYNTHESIS"
            source_authority_ids = ["product.current"]
            source_quotes = []
            if "The loser counterpicks." in line:
                provenance = "NEW_USER_INPUT"
                source_authority_ids = []
                source_quotes = ["make the loser counterpick the winner's card"]
            elif "result changes the next legal card-price decision" in line:
                provenance = "PRESERVED_AUTHORITY"
            claims.append(
                {
                    "claim_id": f"output.line.{index}",
                    "output_quote": line,
                    "provenance": provenance,
                    "source_authority_ids": source_authority_ids,
                    "source_response_binding_ids": [],
                    "source_quotes": source_quotes,
                }
            )
        alignment_input = {
            "schema_version": "studio_semantic_alignment_input.v3",
            "interaction_id": interaction_id,
            "project_id": "sample",
            "factory_revision": self.revision,
            "trigger": "HUMAN_DECISION_SURFACE",
            "author_context_id": card["author_context_id"],
            "user_input": {
                "text": self.user_text,
                "sha256": text_sha256(self.user_text),
            },
            "response_bindings": [],
            "active_authorities": [
                {
                    "authority_id": "product.current",
                    "authority_kind": "PRODUCT",
                    "artifact": ref(self.repo, self.product),
                }
            ],
            "authority_changes": [],
            "pending_decisions": pending or [],
            "input_deltas": [
                {
                    "delta_id": "delta.counterpick",
                    "source_quote": "make the loser counterpick the winner's card",
                    "response_binding_ids": [],
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
            "output_claims": claims,
            "human_questions": [
                {
                    "question_id": "question.approve",
                    "question_quote": question_quote,
                    "answer_options": [],
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
            "response_binding_fidelity": "PASS",
            "authority_continuity": "PASS",
            "authority_change_fidelity": "PASS",
            "claim_provenance": "PASS",
            "material_claim_coverage": "PASS",
            "question_necessity": "PASS",
            "semantic_non_substitution": "PASS",
            "routing_and_scope": "PASS",
            "human_boundary": "PASS",
            "surface_proportionality": "PASS",
            "pending_decision_disposition": "PASS",
        }
        review = {
            "schema_version": "studio_semantic_alignment_review.v3",
            "review_id": f"review.{interaction_id}",
            "project_id": "sample",
            "factory_revision": self.revision,
            "alignment_input": ref(self.repo, input_path),
            "reviewer_context_id": reviewer,
            "reviewer_freshness": "FRESH",
            "checks": checks,
            "independent_claim_inventory": [
                {
                    "review_claim_id": f"review.line.{index}",
                    "candidate_output_quote": claim["output_quote"],
                    "author_claim_id": claim["claim_id"],
                    "assessed_provenance": claim["provenance"],
                    "status": "PASS",
                    "rationale": "Fresh reviewer independently matched this complete material line.",
                }
                for index, claim in enumerate(claims, 1)
            ],
            "findings": [
                {
                    "finding_id": "finding.aligned",
                    "status": "PASS",
                    "user_input_quote": "make the loser counterpick the winner's card",
                    "response_binding_ids": [],
                    "authority_ids": ["product.current"],
                    "authority_change_ids": [],
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

    def test_uninventoried_material_output_line_is_rejected(self) -> None:
        card_path = write_json(
            self.repo / "design/gameplay/objective_gameplay/first/GAMEPLAY_DECISION_CARD.json",
            self.card("first"),
        )
        input_path, review_path = self.alignment_artifacts(
            card_path, interaction_id="turn.uninventoried"
        )
        alignment_input = json.loads(input_path.read_text())
        candidate = alignment_input["candidate_output"]["text"] + "\nAI made this the whole product axis."
        alignment_input["candidate_output"] = {
            "kind": "DECISION_SURFACE",
            "text": candidate,
            "sha256": text_sha256(candidate),
        }
        write_json(input_path, alignment_input)
        review = json.loads(review_path.read_text())
        review["alignment_input"] = ref(self.repo, input_path)
        write_json(review_path, review)
        result = validate_alignment_review(self.repo, input_path, review_path)
        self.assertTrue(
            any("uninventoried material line" in error for error in result.errors),
            result.errors,
        )

    def test_fresh_reviewer_must_inventory_every_material_line(self) -> None:
        card_path = write_json(
            self.repo / "design/gameplay/objective_gameplay/first/GAMEPLAY_DECISION_CARD.json",
            self.card("first"),
        )
        input_path, review_path = self.alignment_artifacts(
            card_path, interaction_id="turn.review-coverage"
        )
        review = json.loads(review_path.read_text())
        omitted = review["independent_claim_inventory"].pop()["candidate_output_quote"]
        write_json(review_path, review)
        result = validate_alignment_review(self.repo, input_path, review_path)
        self.assertIn("reviewer omitted material candidate line: " + omitted, result.errors)

    def test_reference_evidence_cannot_be_labeled_repo_evidence(self) -> None:
        card_path = write_json(
            self.repo / "design/gameplay/objective_gameplay/first/GAMEPLAY_DECISION_CARD.json",
            self.card("first"),
        )
        input_path, review_path = self.alignment_artifacts(
            card_path, interaction_id="turn.reference"
        )
        reference_path = self.repo / "design/studio/research/reference.json"
        write_json(reference_path, {"source": "Official reference supports digital sharing."})
        alignment_input = json.loads(input_path.read_text())
        alignment_input["active_authorities"].append(
            {
                "authority_id": "reference.official",
                "authority_kind": "REFERENCE_EVIDENCE",
                "artifact": ref(self.repo, reference_path),
            }
        )
        claim = alignment_input["output_claims"][0]
        claim["provenance"] = "REPO_EVIDENCE"
        claim["source_authority_ids"] = ["reference.official"]
        claim["source_quotes"] = ["Official reference supports digital sharing."]
        write_json(input_path, alignment_input)
        review = json.loads(review_path.read_text())
        review["alignment_input"] = ref(self.repo, input_path)
        write_json(review_path, review)
        result = validate_alignment_review(self.repo, input_path, review_path)
        self.assertTrue(
            any("REPO_EVIDENCE must cite only REPO_EVIDENCE" in error for error in result.errors),
            result.errors,
        )

    def test_question_substring_cannot_exempt_material_claims(self) -> None:
        card_path = write_json(
            self.repo / "design/gameplay/objective_gameplay/first/GAMEPLAY_DECISION_CARD.json",
            self.card("first"),
        )
        input_path, review_path = self.alignment_artifacts(
            card_path, interaction_id="turn.question-substring"
        )
        alignment_input = json.loads(input_path.read_text())
        alignment_input["human_questions"][0]["question_quote"] = "Reply"
        write_json(input_path, alignment_input)
        review = json.loads(review_path.read_text())
        review["alignment_input"] = ref(self.repo, input_path)
        write_json(review_path, review)
        result = validate_alignment_review(self.repo, input_path, review_path)
        self.assertTrue(
            any("must cover a complete candidate line" in error for error in result.errors),
            result.errors,
        )

    def test_markdown_heading_remains_a_material_claim(self) -> None:
        self.assertEqual(
            ["**Product direction:**", "Keep the exhibition reward loop."],
            material_output_lines(
                "**Product direction:**\nKeep the exhibition reward loop."
            ),
        )

    def test_one_token_reply_requires_exact_prior_option_binding(self) -> None:
        card_path = write_json(
            self.repo / "design/gameplay/objective_gameplay/first/GAMEPLAY_DECISION_CARD.json",
            self.card("first"),
        )
        input_path, review_path = self.alignment_artifacts(
            card_path, interaction_id="turn.unbound-b"
        )
        alignment_input = json.loads(input_path.read_text())
        alignment_input["user_input"] = {"text": "b", "sha256": text_sha256("b")}
        alignment_input["input_deltas"][0]["source_quote"] = "b"
        write_json(input_path, alignment_input)
        review = json.loads(review_path.read_text())
        review["alignment_input"] = ref(self.repo, input_path)
        review["findings"][0]["user_input_quote"] = "b"
        write_json(review_path, review)
        result = validate_alignment_review(self.repo, input_path, review_path)
        self.assertTrue(
            any("one-token user reply requires" in error for error in result.errors),
            result.errors,
        )

    def test_bound_option_reply_is_recorded_as_user_owned_request(self) -> None:
        prior_root = self.repo / "design/studio/interaction_alignment/turn.prior"
        prior_input_path = prior_root / "STUDIO_SEMANTIC_ALIGNMENT_INPUT.json"
        prior_surface = (
            "Which production order should Studio use?\n"
            "A = update all five production documents now.\n"
            "B = reissue the decision card first; update the five production documents only after approval."
        )
        prior_input = {
            "schema_version": "studio_semantic_alignment_input.v3",
            "interaction_id": "turn.prior",
            "project_id": "sample",
            "factory_revision": self.revision,
            "trigger": "BLOCKING_HUMAN_QUESTION",
            "author_context_id": "prior.author",
            "user_input": {"text": "Choose the safe order.", "sha256": text_sha256("Choose the safe order.")},
            "response_bindings": [],
            "active_authorities": [{"authority_id": "product.current", "authority_kind": "PRODUCT", "artifact": ref(self.repo, self.product)}],
            "authority_changes": [],
            "pending_decisions": [],
            "input_deltas": [{"delta_id": "delta.order", "source_quote": "Choose the safe order.", "response_binding_ids": [], "classification": "AMBIGUOUS", "target_authority_ids": ["product.current"], "interpretation": "Ask which safe production order the user wants."}],
            "proposed_transition": "REQUEST_HUMAN_RULING",
            "candidate_output": {"kind": "HUMAN_QUESTION", "text": prior_surface, "sha256": text_sha256(prior_surface)},
            "output_claims": [
                {"claim_id": "prior.a", "output_quote": "A = update all five production documents now.", "provenance": "AI_SYNTHESIS", "source_authority_ids": ["product.current"], "source_response_binding_ids": [], "source_quotes": []},
                {"claim_id": "prior.b", "output_quote": "B = reissue the decision card first; update the five production documents only after approval.", "provenance": "AI_SYNTHESIS", "source_authority_ids": ["product.current"], "source_response_binding_ids": [], "source_quotes": []},
            ],
            "human_questions": [{
                "question_id": "question.order",
                "question_quote": "Which production order should Studio use?",
                "answer_options": [
                    {"option_id": "a", "option_quote": "A = update all five production documents now.", "accepted_response_tokens": ["a", "A"]},
                    {"option_id": "b", "option_quote": "B = reissue the decision card first; update the five production documents only after approval.", "accepted_response_tokens": ["b", "B"]},
                ],
                "material_consequence": "The ruling changes the order of authority and plan updates.",
                "searched_authority_ids": ["product.current"],
                "why_unresolved": "Only the user can select the production order.",
            }],
            "authored_at": "2026-08-07T00:00:00+08:00",
        }
        write_json(prior_input_path, prior_input)
        prior_review_path = prior_root / "STUDIO_SEMANTIC_ALIGNMENT_REVIEW.json"
        prior_review = {
            "schema_version": "studio_semantic_alignment_review.v3",
            "review_id": "review.turn.prior",
            "project_id": "sample",
            "factory_revision": self.revision,
            "alignment_input": ref(self.repo, prior_input_path),
            "reviewer_context_id": "prior.reviewer",
            "reviewer_freshness": "FRESH",
            "checks": {key: "PASS" for key in (
                "input_delta_complete", "response_binding_fidelity", "authority_continuity",
                "authority_change_fidelity", "claim_provenance", "material_claim_coverage",
                "question_necessity", "semantic_non_substitution", "routing_and_scope",
                "human_boundary", "surface_proportionality", "pending_decision_disposition",
            )},
            "independent_claim_inventory": [
                {"review_claim_id": "prior.review.a", "candidate_output_quote": "A = update all five production documents now.", "author_claim_id": "prior.a", "assessed_provenance": "AI_SYNTHESIS", "status": "PASS", "rationale": "Exact option A was reviewed."},
                {"review_claim_id": "prior.review.b", "candidate_output_quote": "B = reissue the decision card first; update the five production documents only after approval.", "author_claim_id": "prior.b", "assessed_provenance": "AI_SYNTHESIS", "status": "PASS", "rationale": "Exact option B was reviewed."},
            ],
            "findings": [],
            "blocking_findings": [],
            "verdict": "HUMAN_RULING_GENUINELY_REQUIRED",
            "reviewed_at": "2026-08-07T00:01:00+08:00",
        }
        write_json(prior_review_path, prior_review)

        card_path = write_json(
            self.repo / "design/gameplay/objective_gameplay/first/GAMEPLAY_DECISION_CARD.json",
            self.card("first"),
        )
        input_path, review_path = self.alignment_artifacts(
            card_path, interaction_id="turn.bound-b"
        )
        alignment_input = json.loads(input_path.read_text())
        alignment_input["user_input"] = {"text": "b", "sha256": text_sha256("b")}
        alignment_input["response_bindings"] = [{
            "binding_id": "reply.b",
            "response_quote": "b",
            "prior_alignment_input": ref(self.repo, prior_input_path),
            "prior_alignment_review": ref(self.repo, prior_review_path),
            "question_id": "question.order",
            "selected_option_id": "b",
            "selected_option_quote": "B = reissue the decision card first; update the five production documents only after approval.",
        }]
        alignment_input["input_deltas"][0]["source_quote"] = "b"
        alignment_input["input_deltas"][0]["response_binding_ids"] = ["reply.b"]
        bound_claim = next(
            claim
            for claim in alignment_input["output_claims"]
            if claim["provenance"] == "NEW_USER_INPUT"
        )
        bound_claim["provenance"] = "BOUND_USER_RESPONSE"
        bound_claim["source_authority_ids"] = []
        bound_claim["source_response_binding_ids"] = ["reply.b"]
        bound_claim["source_quotes"] = [
            "b",
            "B = reissue the decision card first; update the five production documents only after approval.",
        ]
        write_json(input_path, alignment_input)
        review = json.loads(review_path.read_text())
        review["alignment_input"] = ref(self.repo, input_path)
        next(
            item
            for item in review["independent_claim_inventory"]
            if item["author_claim_id"] == bound_claim["claim_id"]
        )["assessed_provenance"] = "BOUND_USER_RESPONSE"
        review["findings"][0]["user_input_quote"] = "b"
        review["findings"][0]["response_binding_ids"] = ["reply.b"]
        write_json(review_path, review)
        result = validate_alignment_review(self.repo, input_path, review_path)
        self.assertEqual(HUMAN_RULING_GENUINELY_REQUIRED, result.status, result.errors)

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
