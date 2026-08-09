from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from studio.alignment import current_factory_revision, material_output_lines, text_sha256
from studio.product import (
    ACTIVE,
    ARCHIVED,
    NO_ACTIVE,
    activate_product_authority,
    archive_product_authority,
    load_product_register,
    prepare_product_archive,
    product_authority_status,
)


def write_json(path: Path, value: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def ref(repo: Path, path: Path) -> dict[str, str]:
    return {
        "path": path.relative_to(repo).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


class ProductAuthorityLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name) / "game"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.revision = current_factory_revision()
        self._write_canonical("old-direction", "Commission the old direction")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _write_canonical(self, direction_id: str, quote: str) -> None:
        product = self.repo / "design/product/PRODUCT_THESIS.md"
        product.parent.mkdir(parents=True, exist_ok=True)
        product.write_text(f"# Product Thesis\n\n{direction_id}\n", encoding="utf-8")
        write_json(
            self.repo / "design/product/FACTORY_CONSTRAINTS.json",
            {"schema_version": "factory_constraints.v2", "project_id": "sample", "non_goals": [{"non_goal_id": "keep-runtime"}]},
        )
        write_json(
            self.repo / "design/product/idea/PRODUCT_THESIS_INPUT.json",
            {
                "schema_version": "product_thesis_input.v2",
                "project_id": "sample",
                "commission": {
                    "authorized": True,
                    "authorization_quote": quote,
                    "selected_direction_id": direction_id,
                },
            },
        )
        write_json(
            self.repo / "design/product/idea/IDEA_FACTORY_RESULT.json",
            {"schema_version": "idea_factory_result.v1", "project_id": "sample"},
        )
        write_json(
            self.repo / "design/product/idea/IDEA_EXPLORATION.json",
            {"schema_version": "idea_exploration.v1", "frontier_state": "DIRECTION_EMERGED"},
        )
        (self.repo / "design/product/idea/IDEA_EXPLORATION.md").write_text(
            "# Emerged direction\n", encoding="utf-8"
        )

    def _pending_card(self) -> Path:
        return write_json(
            self.repo / "design/gameplay/objective_gameplay/old/GAMEPLAY_DECISION_CARD.json",
            {
                "card_id": "card.old",
                "objective_id": "old",
                "decision_payload_sha256": "1" * 64,
                "human_verdict": {
                    "status": "PENDING",
                    "source_text": "PENDING",
                    "recorded_at": "PENDING",
                },
            },
        )

    def _alignment(self, snapshot_path: Path, card_path: Path) -> tuple[Path, Path]:
        snapshot = json.loads(snapshot_path.read_text())
        thesis_ref = next(
            item["archived_artifact"]
            for item in snapshot["authority_artifacts"]
            if item["canonical_path"] == "design/product/PRODUCT_THESIS.md"
        )
        user_text = "Archive the old direction and do not keep its cards pending."
        candidate = "Archived the old product direction without deleting runtime work."
        root = self.repo / "design/studio/interaction_alignment/archive.old"
        input_path = root / "STUDIO_SEMANTIC_ALIGNMENT_INPUT.json"
        claim_id = "output.archive"
        alignment_input = {
            "schema_version": "studio_semantic_alignment_input.v3",
            "interaction_id": "archive.old",
            "project_id": "sample",
            "factory_revision": self.revision,
            "trigger": "REVISED_AUTHORITY",
            "author_context_id": "archive.author",
            "user_input": {"text": user_text, "sha256": text_sha256(user_text)},
            "response_bindings": [],
            "active_authorities": [
                {
                    "authority_id": "product.current",
                    "authority_kind": "PRODUCT",
                    "artifact": thesis_ref,
                }
            ],
            "authority_changes": [],
            "pending_decisions": [
                {
                    "decision_payload_sha256": "1" * 64,
                    "decision_card": ref(self.repo, card_path),
                    "disposition": "WITHDRAW_BY_PRODUCT_ARCHIVE",
                }
            ],
            "input_deltas": [
                {
                    "delta_id": "delta.archive",
                    "source_quote": user_text,
                    "response_binding_ids": [],
                    "classification": "REVOKE",
                    "target_authority_ids": ["product.current"],
                    "interpretation": "Archive the whole product authority and withdraw pending cards.",
                }
            ],
            "proposed_transition": "ARCHIVE_PRODUCT_DIRECTION",
            "candidate_output": {
                "kind": "MATERIAL_RESPONSE",
                "text": candidate,
                "sha256": text_sha256(candidate),
            },
            "output_claims": [
                {
                    "claim_id": claim_id,
                    "output_quote": candidate,
                    "provenance": "NEW_USER_INPUT",
                    "source_authority_ids": [],
                    "source_response_binding_ids": [],
                    "source_quotes": [user_text],
                }
            ],
            "human_questions": [],
            "authored_at": "2026-08-06T00:00:00+08:00",
        }
        write_json(input_path, alignment_input)
        review_path = root / "STUDIO_SEMANTIC_ALIGNMENT_REVIEW.json"
        review = {
            "schema_version": "studio_semantic_alignment_review.v3",
            "review_id": "review.archive.old",
            "project_id": "sample",
            "factory_revision": self.revision,
            "alignment_input": ref(self.repo, input_path),
            "reviewer_context_id": "archive.reviewer",
            "reviewer_freshness": "FRESH",
            "checks": {
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
            },
            "independent_claim_inventory": [
                {
                    "review_claim_id": "review-claim.archive",
                    "candidate_output_quote": material_output_lines(candidate)[0],
                    "author_claim_id": claim_id,
                    "assessed_provenance": "NEW_USER_INPUT",
                    "status": "PASS",
                    "rationale": "The raw user input explicitly archives the direction.",
                }
            ],
            "findings": [
                {
                    "finding_id": "finding.archive",
                    "status": "PASS",
                    "user_input_quote": user_text,
                    "response_binding_ids": [],
                    "authority_ids": ["product.current"],
                    "authority_change_ids": [],
                    "candidate_output_quote": candidate,
                    "rationale": "The transition preserves runtime work but revokes product authority.",
                }
            ],
            "blocking_findings": [],
            "verdict": "PASS_ALIGNMENT",
            "reviewed_at": "2026-08-06T00:01:00+08:00",
        }
        write_json(review_path, review)
        return input_path, review_path

    def _activation_alignment(self, quote: str) -> tuple[Path, Path]:
        root = self.repo / "design/studio/interaction_alignment/commission.vault"
        input_path = root / "STUDIO_SEMANTIC_ALIGNMENT_INPUT.json"
        candidate = "The commissioned Product Thesis is ready for Studio cycle synthesis."
        changes = [
            ("product.input", "PRODUCT_AUTHORITY_INPUT", "design/product/idea/PRODUCT_THESIS_INPUT.json"),
            ("product.thesis", "PRODUCT_THESIS", "design/product/PRODUCT_THESIS.md"),
            ("product.constraints", "FACTORY_CONSTRAINTS", "design/product/FACTORY_CONSTRAINTS.json"),
            ("product.result", "IDEA_FACTORY_RESULT", "design/product/idea/IDEA_FACTORY_RESULT.json"),
        ]
        alignment_input = {
            "schema_version": "studio_semantic_alignment_input.v3",
            "interaction_id": "commission.vault",
            "project_id": "sample",
            "factory_revision": self.revision,
            "trigger": "REVISED_AUTHORITY",
            "author_context_id": "commission.author",
            "user_input": {"text": quote, "sha256": text_sha256(quote)},
            "response_bindings": [],
            "active_authorities": [],
            "authority_changes": [
                {
                    "change_id": change_id,
                    "operation": "ACTIVATE",
                    "authority_kind": kind,
                    "artifact": ref(self.repo, self.repo / path),
                }
                for change_id, kind, path in changes
            ],
            "pending_decisions": [],
            "input_deltas": [{
                "delta_id": "delta.commission",
                "source_quote": quote,
                "response_binding_ids": [],
                "classification": "ADD",
                "target_authority_ids": [],
                "interpretation": "Activate the exact commissioned Product Thesis package.",
            }],
            "proposed_transition": "ACTIVATE_PRODUCT_AUTHORITY",
            "candidate_output": {"kind": "MATERIAL_RESPONSE", "text": candidate, "sha256": text_sha256(candidate)},
            "output_claims": [{
                "claim_id": "output.commission",
                "output_quote": candidate,
                "provenance": "AI_SYNTHESIS",
                "source_authority_ids": [],
                "source_response_binding_ids": [],
                "source_quotes": [quote],
            }],
            "human_questions": [],
            "authored_at": "2026-08-06T00:02:30+08:00",
        }
        write_json(input_path, alignment_input)
        review_path = root / "STUDIO_SEMANTIC_ALIGNMENT_REVIEW.json"
        review = {
            "schema_version": "studio_semantic_alignment_review.v3",
            "review_id": "review.commission.vault",
            "project_id": "sample",
            "factory_revision": self.revision,
            "alignment_input": ref(self.repo, input_path),
            "reviewer_context_id": "commission.reviewer",
            "reviewer_freshness": "FRESH",
            "checks": {
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
            },
            "independent_claim_inventory": [{
                "review_claim_id": "review-claim.commission",
                "candidate_output_quote": candidate,
                "author_claim_id": "output.commission",
                "assessed_provenance": "AI_SYNTHESIS",
                "status": "PASS",
                "rationale": "The response reports the reviewed authority transition without expanding it.",
            }],
            "findings": [{
                "finding_id": "finding.commission",
                "status": "PASS",
                "user_input_quote": quote,
                "response_binding_ids": [],
                "authority_ids": [],
                "authority_change_ids": [item[0] for item in changes],
                "candidate_output_quote": candidate,
                "rationale": "Every activated artifact preserves the commissioned direction and user provenance.",
            }],
            "blocking_findings": [],
            "verdict": "PASS_ALIGNMENT",
            "reviewed_at": "2026-08-06T00:02:45+08:00",
        }
        write_json(review_path, review)
        return input_path, review_path

    def test_archive_is_native_fail_closed_transition_without_fake_card_verdict(self) -> None:
        prepared = prepare_product_archive(
            self.repo, "archive.old", prepared_at="2026-08-06T00:00:00+08:00"
        )
        self.assertEqual("PRODUCT_AUTHORITY_ARCHIVE_PREPARED", prepared.status)
        snapshot_path = (
            self.repo
            / "design/studio/product_authority_transitions/archive.old/PRODUCT_AUTHORITY_ARCHIVE_SNAPSHOT.json"
        )
        card_path = self._pending_card()
        input_path, review_path = self._alignment(snapshot_path, card_path)
        result = archive_product_authority(
            self.repo,
            snapshot_path,
            input_path,
            review_path,
            recorded_at="2026-08-06T00:02:00+08:00",
        )
        self.assertEqual(ARCHIVED, result.status)
        self.assertFalse((self.repo / "design/product/PRODUCT_THESIS.md").exists())
        self.assertTrue(
            (
                self.repo
                / "design/product/archive/archive.old/PRODUCT_THESIS.md"
            ).is_file()
        )
        self.assertEqual(NO_ACTIVE, product_authority_status(self.repo).status)
        register = json.loads(
            (self.repo / "design/studio/STUDIO_DECISION_CARD_REGISTER.json").read_text()
        )
        self.assertEqual("PRODUCT_ARCHIVED", register["entries"][0]["state"])
        unchanged_card = json.loads(card_path.read_text())
        self.assertEqual("PENDING", unchanged_card["human_verdict"]["status"])
        # Historical alignment remains verifiable because it binds the immutable snapshot.
        from studio.alignment import validate_alignment_review

        checked = validate_alignment_review(self.repo, input_path, review_path)
        self.assertEqual("PASS_ALIGNMENT", checked.status, checked.errors)

    def test_new_commission_reactivates_after_archive(self) -> None:
        snapshot = prepare_product_archive(
            self.repo, "archive.old", prepared_at="2026-08-06T00:00:00+08:00"
        )
        self.assertEqual("PRODUCT_AUTHORITY_ARCHIVE_PREPARED", snapshot.status)
        snapshot_path = (
            self.repo
            / "design/studio/product_authority_transitions/archive.old/PRODUCT_AUTHORITY_ARCHIVE_SNAPSHOT.json"
        )
        card = self._pending_card()
        input_path, review_path = self._alignment(snapshot_path, card)
        archive_product_authority(
            self.repo,
            snapshot_path,
            input_path,
            review_path,
            recorded_at="2026-08-06T00:02:00+08:00",
        )
        self._write_canonical("vault-direction", "Commission the Vault direction")
        activation_input, activation_review = self._activation_alignment(
            "Commission the Vault direction"
        )
        activated = activate_product_authority(
            self.repo,
            activation_input,
            activation_review,
            authority_id="vault-direction",
            recorded_at="2026-08-06T00:03:00+08:00",
        )
        self.assertEqual("PRODUCT_AUTHORITY_ACTIVATED", activated.status)
        register, errors = load_product_register(self.repo)
        self.assertEqual([], errors)
        self.assertEqual(ACTIVE, register["status"])
        self.assertEqual("vault-direction", register["active_authority"]["authority_id"])
        transition = register["transitions"][-1]
        self.assertEqual(ref(self.repo, activation_input), transition["alignment_input"])
        self.assertEqual(ref(self.repo, activation_review), transition["alignment_review"])


if __name__ == "__main__":
    unittest.main()
