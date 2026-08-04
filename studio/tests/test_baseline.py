from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from studio.baseline import (
    BASELINE_ADMISSION_VALID,
    BASELINE_ADMITTED,
    BASELINE_PROMOTION_INPUT_REQUIRED,
    BASELINE_RECONSTRUCTION_INPUT_REQUIRED,
    BLOCKED_BY_ADMISSION_MATERIAL,
    BLOCKED_BY_EXISTING_BASELINE,
    BaselineAdmissionError,
    compile_baseline_admission,
    check_baseline_admission,
    start_baseline_admission,
)


def _run(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


def _write(repo: Path, relative: str, content: str) -> Path:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _write_json(repo: Path, relative: str, payload: dict) -> Path:
    return _write(repo, relative, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _ref(repo: Path, relative: str) -> dict[str, str]:
    path = repo / relative
    return {
        "path": relative,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def _commit(repo: Path, message: str) -> str:
    _run(repo, "add", ".")
    _run(repo, "commit", "-m", message)
    return _run(repo, "rev-parse", "HEAD")


class BaselineAdmissionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name) / "game"
        self.repo.mkdir()
        _run(self.repo, "init", "-b", "main")
        _run(self.repo, "config", "user.email", "factory-test@example.invalid")
        _run(self.repo, "config", "user.name", "Factory Test")
        _write(self.repo, "design/product/PRODUCT_THESIS.md", "# Product\nReal game.\n")
        _write(self.repo, "design/gameplay/unit-one.md", "# Unit one\n")
        _write(self.repo, "build/game.bin", "build-one\n")
        _write_json(self.repo, "evidence/acceptance-input-one.json", {"run": "one"})
        _write_json(self.repo, "evidence/runtime-one.json", {"loop": "complete"})
        _write(self.repo, "evidence/verification-one.txt", "PASS\n")
        self.revision_one = _commit(self.repo, "initial playable game")
        self.factory_revision = _run(Path(__file__).resolve().parents[2], "rev-parse", "HEAD")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _acceptance_review(
        self,
        *,
        admission_id: str,
        unit_id: str,
        revision: str,
        build_id: str,
        reviewer: str,
        authority: str,
        evidence: str,
    ) -> dict[str, str]:
        input_relative = (
            f"design/studio/admissions/{admission_id}/"
            f"GAMEPLAY_ACCEPTANCE_INPUT_{unit_id}.json"
        )
        _write_json(
            self.repo,
            input_relative,
            {
                "schema_version": "gameplay_acceptance_input.v1",
                "acceptance_input_id": f"input-{admission_id}-{unit_id}",
                "project_id": "sample-game",
                "unit_id": unit_id,
                "game_revision": revision,
                "build_id": build_id,
                "factory_revision": self.factory_revision,
                "experience_authority": _ref(self.repo, authority),
                "expected_player_experience": {
                    "target_player": "A player encountering this objective for the first time",
                    "intended_experience": "Understand the goal and make a deliberate choice",
                    "required_player_work": "Read state, choose, act, and observe the consequence",
                    "earned_satisfaction": "The visible result follows from the player's choice",
                    "failure_recovery": "A failed choice teaches a recoverable next action",
                    "must_not_become": "An automatic sequence with no meaningful player decision",
                },
                "playtest_questions": [
                    "Did the player understand the goal without reviewer prompting?",
                    "Did the consequence feel caused by the player's action?",
                ],
                "non_claims": [
                    "Passing technical tests alone does not establish this experience."
                ],
                "prepared_at": "2026-08-03T11:58:00Z",
            },
        )
        relative = f"design/studio/admissions/{admission_id}/acceptance-{unit_id}.json"
        _write_json(
            self.repo,
            relative,
            {
                "schema_version": "gameplay_acceptance_review.v2",
                "review_id": f"review-{admission_id}-{unit_id}",
                "project_id": "sample-game",
                "unit_id": unit_id,
                "game_revision": revision,
                "build_id": build_id,
                "factory_revision": self.factory_revision,
                "experience_authority": _ref(self.repo, authority),
                "reviewer_context_id": reviewer,
                "reviewer_freshness": "FRESH",
                "verdict": "ACCEPTED",
                "acceptance_input": _ref(self.repo, input_relative),
                "human_playtest": {
                    "status": "HUMAN_PLAYTEST_ACCEPTED",
                    "verdict_owner": "USER",
                    "verdict_source": "User played this exact build and accepted the experience.",
                    "accepted_at": "2026-08-03T12:02:00Z",
                },
                "evidence_paths": [_ref(self.repo, evidence)],
                "observed_complete_loop": {
                    "goal": "Reach the visible objective",
                    "actions": ["Choose and execute a meaningful action"],
                    "consequences": "The game changes visibly",
                    "completion": "The objective completes and hands off",
                },
                "blocking_findings": [],
                "reviewed_at": "2026-08-03T12:00:00Z",
            },
        )
        return _ref(self.repo, relative)

    def _reconstruction_input(self, admission_id: str = "admission-one") -> tuple[str, dict]:
        review = self._acceptance_review(
            admission_id=admission_id,
            unit_id="unit-one",
            revision=self.revision_one,
            build_id="build-one",
            reviewer="fresh-reviewer-one",
            authority="design/gameplay/unit-one.md",
            evidence="evidence/runtime-one.json",
        )
        inventory_relative = (
            f"design/studio/admissions/{admission_id}/BASELINE_RECONSTRUCTION_INVENTORY.json"
        )
        _write_json(
            self.repo,
            inventory_relative,
            {
                "schema_version": "baseline_reconstruction_inventory.v1",
                "inventory_id": f"inventory-{admission_id}",
                "status": "COMPLETE_CURRENT_PLAYABLE_SCOPE",
                "project_id": "sample-game",
                "game_revision": self.revision_one,
                "author_context_id": "reconstruction-author-one",
                "source_paths": [_ref(self.repo, "design/gameplay/unit-one.md")],
                "discovered_unit_ids": ["unit-one"],
                "excluded_candidates": [],
                "completed_at": "2026-08-03T11:55:00Z",
            },
        )
        payload = {
            "schema_version": "baseline_admission_input.v1",
            "admission_id": admission_id,
            "admission_mode": "RECONSTRUCT",
            "project_id": "sample-game",
            "baseline_id": "baseline-one",
            "game_revision": self.revision_one,
            "studio_goal": "Produce a genuinely playable game",
            "requested_horizon": "one accepted gameplay loop",
            "product_authority": _ref(self.repo, "design/product/PRODUCT_THESIS.md"),
            "runnable_build": {
                "build_id": "build-one",
                "launch_command": "./build/game.bin",
                "artifact_paths": [_ref(self.repo, "build/game.bin")],
                "supported_platforms": ["test"],
            },
            "playable_scope": {
                "entry_condition": "Launch the game",
                "completion_condition": "Complete unit one",
                "expected_minutes": 5,
                "gameplay_loop": "Read goal, act, observe consequence, complete",
            },
            "admitted_units": [
                {
                    "unit_id": "unit-one",
                    "authority": _ref(self.repo, "design/gameplay/unit-one.md"),
                    "player_goal": "Complete the first objective",
                    "meaningful_actions": ["Choose the safe or risky action"],
                    "consequence_or_reward": "The next objective becomes available",
                    "acceptance_review": review,
                }
            ],
            "verification": {
                "commands": ["verify unit one"],
                "result_paths": [_ref(self.repo, "evidence/verification-one.txt")],
                "regression_review": {"path": "", "sha256": ""},
            },
            "known_gaps": [],
            "resolved_gap_ids": [],
            "workflow_completion": {"path": "", "sha256": ""},
            "predecessor_baseline": {"path": "", "sha256": ""},
            "reconstruction": {
                "trigger": "NO_ACCEPTED_BASELINE",
                "reason": "No accepted baseline exists yet",
                "author_context_ids": ["reconstruction-author-one"],
                "inventory": _ref(self.repo, inventory_relative),
                "superseded_baseline": {"path": "", "sha256": ""},
            },
            "acceptance_owner": "USER",
            "accepted_at": "2026-08-03T12:05:00Z",
        }
        relative = f"design/studio/admissions/{admission_id}/BASELINE_ADMISSION_INPUT.json"
        _write_json(self.repo, relative, payload)
        return relative, payload

    def _compile_first_baseline(self) -> tuple[str, dict, dict[str, str]]:
        relative, payload = self._reconstruction_input()
        result = compile_baseline_admission(str(self.repo), relative)
        self.assertEqual(BASELINE_ADMITTED, result.status, result.errors)
        baseline_ref = _ref(
            self.repo,
            "design/studio/baselines/baseline-one/ACCEPTED_PLAYABLE_BASELINE.json",
        )
        return relative, payload, baseline_ref

    def _promotion_input(self, predecessor_ref: dict[str, str]) -> tuple[str, dict]:
        _commit(self.repo, "record baseline one")
        _write(self.repo, "design/gameplay/unit-two.md", "# Unit two\n")
        _write_json(self.repo, "evidence/acceptance-input-two.json", {"run": "two"})
        _write_json(self.repo, "evidence/runtime-two.json", {"loop": "complete"})
        _write(self.repo, "evidence/implementation-two.txt", "IMPLEMENTED\n")
        _write(self.repo, "evidence/verification-two.txt", "NEW PASS\n")
        _write(self.repo, "evidence/regression-one.txt", "OLD PASS\n")
        self.revision_two = _commit(self.repo, "implement unit two")

        admission_id = "admission-two"
        completion_relative = (
            "design/studio/admissions/admission-two/STUDIO_WORKFLOW_COMPLETION.json"
        )
        _write_json(
            self.repo,
            completion_relative,
            {
                "schema_version": "studio_workflow_completion.v2",
                "completion_id": "completion-two",
                "status": "IMPLEMENTED_PENDING_ACCEPTANCE",
                "project_id": "sample-game",
                "game_revision": self.revision_two,
                "factory_revision": self.factory_revision,
                "specialists": ["gameplay", "repo_production"],
                "workflow_kind": "objective_production",
                "unit_ids": ["unit-two"],
                "production_context_ids": ["production-context-two"],
                "source_authorities": [_ref(self.repo, "design/gameplay/unit-two.md")],
                "implementation_results": [_ref(self.repo, "evidence/implementation-two.txt")],
                "test_results": [_ref(self.repo, "evidence/verification-two.txt")],
                "completed_at": "2026-08-03T13:00:00Z",
            },
        )
        review_ref = self._acceptance_review(
            admission_id=admission_id,
            unit_id="unit-two",
            revision=self.revision_two,
            build_id="build-two",
            reviewer="fresh-reviewer-two",
            authority="design/gameplay/unit-two.md",
            evidence="evidence/runtime-two.json",
        )
        regression_relative = (
            "design/studio/admissions/admission-two/BASELINE_REGRESSION_REVIEW.json"
        )
        _write_json(
            self.repo,
            regression_relative,
            {
                "schema_version": "baseline_regression_review.v1",
                "review_id": "regression-two",
                "project_id": "sample-game",
                "game_revision": self.revision_two,
                "build_id": "build-two",
                "reviewer_context_id": "fresh-reviewer-two",
                "reviewer_freshness": "FRESH",
                "predecessor_baseline": predecessor_ref,
                "covered_unit_ids": ["unit-one"],
                "commands": ["regress unit one"],
                "result_paths": [_ref(self.repo, "evidence/regression-one.txt")],
                "status": "PASS",
                "blocking_findings": [],
                "reviewed_at": "2026-08-03T13:10:00Z",
            },
        )
        payload = {
            "schema_version": "baseline_admission_input.v1",
            "admission_id": admission_id,
            "admission_mode": "PROMOTE",
            "project_id": "sample-game",
            "baseline_id": "baseline-two",
            "game_revision": self.revision_two,
            "studio_goal": "Produce a genuinely playable game",
            "requested_horizon": "two accepted gameplay loops",
            "product_authority": _ref(self.repo, "design/product/PRODUCT_THESIS.md"),
            "runnable_build": {
                "build_id": "build-two",
                "launch_command": "./build/game.bin",
                "artifact_paths": [_ref(self.repo, "build/game.bin")],
                "supported_platforms": ["test"],
            },
            "playable_scope": {
                "entry_condition": "Launch the game",
                "completion_condition": "Complete unit two",
                "expected_minutes": 10,
                "gameplay_loop": "Complete unit one, choose in unit two, finish",
            },
            "admitted_units": [
                {
                    "unit_id": "unit-two",
                    "authority": _ref(self.repo, "design/gameplay/unit-two.md"),
                    "player_goal": "Complete the second objective",
                    "meaningful_actions": ["Counter or build greedily"],
                    "consequence_or_reward": "A different result follows the choice",
                    "acceptance_review": review_ref,
                }
            ],
            "verification": {
                "commands": ["verify unit two", "regress unit one"],
                "result_paths": [
                    _ref(self.repo, "evidence/verification-two.txt"),
                    _ref(self.repo, "evidence/regression-one.txt"),
                ],
                "regression_review": _ref(self.repo, regression_relative),
            },
            "known_gaps": [],
            "resolved_gap_ids": [],
            "workflow_completion": _ref(self.repo, completion_relative),
            "predecessor_baseline": predecessor_ref,
            "reconstruction": {
                "trigger": "",
                "reason": "",
                "author_context_ids": [],
                "inventory": {"path": "", "sha256": ""},
                "superseded_baseline": {"path": "", "sha256": ""},
            },
            "acceptance_owner": "USER",
            "accepted_at": "2026-08-03T13:15:00Z",
        }
        relative = "design/studio/admissions/admission-two/BASELINE_ADMISSION_INPUT.json"
        _write_json(self.repo, relative, payload)
        return relative, payload

    def test_start_routes_no_baseline_to_complete_reconstruction(self) -> None:
        result = start_baseline_admission(str(self.repo))
        self.assertEqual(BASELINE_RECONSTRUCTION_INPUT_REQUIRED, result.status)
        self.assertEqual("RECONSTRUCT", result.mode)

    def test_reconstruction_compiles_checks_and_then_routes_to_promotion(self) -> None:
        relative, _, _ = self._compile_first_baseline()
        repeated = compile_baseline_admission(str(self.repo), relative)
        self.assertEqual(BASELINE_ADMITTED, repeated.status, repeated.errors)
        checked = check_baseline_admission(str(self.repo), relative)
        self.assertEqual(BASELINE_ADMISSION_VALID, checked.status, checked.errors)
        routed = start_baseline_admission(str(self.repo))
        self.assertEqual(BASELINE_PROMOTION_INPUT_REQUIRED, routed.status)
        baseline = json.loads(
            (
                self.repo
                / "design/studio/baselines/baseline-one/ACCEPTED_PLAYABLE_BASELINE.json"
            ).read_text()
        )
        self.assertEqual("RECONSTRUCT", baseline["promotion"]["admission_mode"])
        self.assertEqual(["unit-one"], baseline["promotion"]["promoted_unit_ids"])
        self.assertEqual("accepted_playable_baseline.v2", baseline["schema_version"])
        self.assertEqual(self.factory_revision, baseline["factory_revision"])
        self.assertEqual(
            "HUMAN_PLAYTEST_ACCEPTED",
            baseline["accepted_gameplay_units"][0]["acceptance_review"][
                "human_playtest_status"
            ],
        )

    def test_check_tolerates_later_mutable_run_state_progress(self) -> None:
        relative, _, _ = self._compile_first_baseline()
        state_path = self.repo / "design/studio/STUDIO_RUN_STATE.json"
        state = json.loads(state_path.read_text())
        state["status"] = "STUDIO_RESEARCHING"
        state["active_pressure"] = {
            "pressure_id": "pressure-one",
            "diagnosis": "The next choice lacks consequence",
            "player_effect": "Low tension",
        }
        _write_json(self.repo, "design/studio/STUDIO_RUN_STATE.json", state)
        checked = check_baseline_admission(str(self.repo), relative)
        self.assertEqual(BASELINE_ADMISSION_VALID, checked.status, checked.errors)

    def test_promotion_preserves_predecessor_and_adds_accepted_unit(self) -> None:
        _, _, predecessor_ref = self._compile_first_baseline()
        predecessor_bytes = (self.repo / predecessor_ref["path"]).read_bytes()
        relative, _ = self._promotion_input(predecessor_ref)
        result = compile_baseline_admission(str(self.repo), relative)
        self.assertEqual(BASELINE_ADMITTED, result.status, result.errors)
        repeated = compile_baseline_admission(str(self.repo), relative)
        self.assertEqual(BASELINE_ADMITTED, repeated.status, repeated.errors)
        checked = check_baseline_admission(str(self.repo), relative)
        self.assertEqual(BASELINE_ADMISSION_VALID, checked.status, checked.errors)
        self.assertEqual(predecessor_bytes, (self.repo / predecessor_ref["path"]).read_bytes())
        baseline = json.loads(
            (
                self.repo
                / "design/studio/baselines/baseline-two/ACCEPTED_PLAYABLE_BASELINE.json"
            ).read_text()
        )
        self.assertEqual(
            ["unit-one", "unit-two"],
            [unit["unit_id"] for unit in baseline["accepted_gameplay_units"]],
        )
        self.assertEqual("PROMOTE", baseline["promotion"]["admission_mode"])
        self.assertEqual(predecessor_ref["sha256"], baseline["promotion"]["predecessor_baseline_sha256"])

    def test_promotion_rejects_missing_workflow_completion_without_writes(self) -> None:
        _, _, predecessor_ref = self._compile_first_baseline()
        relative, payload = self._promotion_input(predecessor_ref)
        payload["workflow_completion"] = {"path": "", "sha256": ""}
        _write_json(self.repo, relative, payload)
        result = compile_baseline_admission(str(self.repo), relative)
        self.assertEqual(BLOCKED_BY_ADMISSION_MATERIAL, result.status)
        self.assertFalse((self.repo / "design/studio/baselines/baseline-two").exists())

    def test_promotion_workflow_units_must_exactly_match_admitted_units(self) -> None:
        _, _, predecessor_ref = self._compile_first_baseline()
        relative, payload = self._promotion_input(predecessor_ref)
        completion_path = self.repo / payload["workflow_completion"]["path"]
        completion = json.loads(completion_path.read_text())
        completion["unit_ids"] = ["unit-two", "unreviewed-unit"]
        _write_json(self.repo, payload["workflow_completion"]["path"], completion)
        payload["workflow_completion"] = _ref(
            self.repo, payload["workflow_completion"]["path"]
        )
        _write_json(self.repo, relative, payload)
        result = compile_baseline_admission(str(self.repo), relative)
        self.assertEqual(BLOCKED_BY_ADMISSION_MATERIAL, result.status)
        self.assertTrue(any("exactly equal admitted unit ids" in error for error in result.errors))
        self.assertFalse((self.repo / "design/studio/baselines/baseline-two").exists())

    def test_failed_acceptance_verdict_cannot_enter_baseline(self) -> None:
        relative, payload = self._reconstruction_input()
        review_path = self.repo / payload["admitted_units"][0]["acceptance_review"]["path"]
        review = json.loads(review_path.read_text())
        review["verdict"] = "REJECTED"
        review["blocking_findings"] = ["The loop does not yet complete."]
        _write_json(self.repo, payload["admitted_units"][0]["acceptance_review"]["path"], review)
        payload["admitted_units"][0]["acceptance_review"] = _ref(
            self.repo, payload["admitted_units"][0]["acceptance_review"]["path"]
        )
        _write_json(self.repo, relative, payload)
        result = compile_baseline_admission(str(self.repo), relative)
        self.assertEqual(BLOCKED_BY_ADMISSION_MATERIAL, result.status)
        self.assertTrue(any("verdict must be ACCEPTED" in error for error in result.errors))
        self.assertFalse((self.repo / "design/studio/baselines/baseline-one").exists())

    def test_acceptance_review_cannot_reuse_production_context(self) -> None:
        _, _, predecessor_ref = self._compile_first_baseline()
        relative, payload = self._promotion_input(predecessor_ref)
        review_path = self.repo / payload["admitted_units"][0]["acceptance_review"]["path"]
        review = json.loads(review_path.read_text())
        review["reviewer_context_id"] = "production-context-two"
        _write_json(self.repo, payload["admitted_units"][0]["acceptance_review"]["path"], review)
        payload["admitted_units"][0]["acceptance_review"] = _ref(
            self.repo, payload["admitted_units"][0]["acceptance_review"]["path"]
        )
        _write_json(self.repo, relative, payload)
        result = compile_baseline_admission(str(self.repo), relative)
        self.assertEqual(BLOCKED_BY_ADMISSION_MATERIAL, result.status)
        self.assertTrue(any("reuses a production context" in error for error in result.errors))

    def test_acceptance_requires_human_playtest_verdict(self) -> None:
        relative, payload = self._reconstruction_input()
        review_relative = payload["admitted_units"][0]["acceptance_review"]["path"]
        review = json.loads((self.repo / review_relative).read_text())
        review["human_playtest"]["status"] = "NOT_RUN"
        _write_json(self.repo, review_relative, review)
        payload["admitted_units"][0]["acceptance_review"] = _ref(
            self.repo, review_relative
        )
        _write_json(self.repo, relative, payload)
        result = compile_baseline_admission(str(self.repo), relative)
        self.assertEqual(BLOCKED_BY_ADMISSION_MATERIAL, result.status)
        self.assertTrue(any("HUMAN_PLAYTEST_ACCEPTED" in error for error in result.errors))

    def test_admission_acceptance_owner_must_be_user(self) -> None:
        relative, payload = self._reconstruction_input()
        payload["acceptance_owner"] = "fresh-reviewer-one"
        _write_json(self.repo, relative, payload)
        result = compile_baseline_admission(str(self.repo), relative)
        self.assertEqual(BLOCKED_BY_ADMISSION_MATERIAL, result.status)
        self.assertTrue(any("acceptance_owner must be USER" in error for error in result.errors))

    def test_acceptance_input_must_bind_exact_unit_authority(self) -> None:
        relative, payload = self._reconstruction_input()
        review_relative = payload["admitted_units"][0]["acceptance_review"]["path"]
        review = json.loads((self.repo / review_relative).read_text())
        input_relative = review["acceptance_input"]["path"]
        acceptance_input = json.loads((self.repo / input_relative).read_text())
        acceptance_input["experience_authority"] = _ref(
            self.repo, "design/product/PRODUCT_THESIS.md"
        )
        _write_json(self.repo, input_relative, acceptance_input)
        review["acceptance_input"] = _ref(self.repo, input_relative)
        _write_json(self.repo, review_relative, review)
        payload["admitted_units"][0]["acceptance_review"] = _ref(
            self.repo, review_relative
        )
        _write_json(self.repo, relative, payload)
        result = compile_baseline_admission(str(self.repo), relative)
        self.assertEqual(BLOCKED_BY_ADMISSION_MATERIAL, result.status)
        self.assertTrue(any("exact admitted unit authority" in error for error in result.errors))

    def test_factory_revision_must_match_active_contracts(self) -> None:
        relative, payload = self._reconstruction_input()
        review_relative = payload["admitted_units"][0]["acceptance_review"]["path"]
        review = json.loads((self.repo / review_relative).read_text())
        review["factory_revision"] = "0" * 40
        _write_json(self.repo, review_relative, review)
        payload["admitted_units"][0]["acceptance_review"] = _ref(
            self.repo, review_relative
        )
        _write_json(self.repo, relative, payload)
        result = compile_baseline_admission(str(self.repo), relative)
        self.assertEqual(BLOCKED_BY_ADMISSION_MATERIAL, result.status)
        self.assertTrue(any("active Factory" in error for error in result.errors))

    def test_legacy_acceptance_review_cannot_create_new_baseline(self) -> None:
        relative, payload = self._reconstruction_input()
        review_relative = payload["admitted_units"][0]["acceptance_review"]["path"]
        review = json.loads((self.repo / review_relative).read_text())
        review["schema_version"] = "gameplay_acceptance_review.v1"
        for field in (
            "factory_revision", "experience_authority", "human_playtest"
        ):
            review.pop(field)
        review["acceptance_input"] = _ref(
            self.repo, "evidence/acceptance-input-one.json"
        )
        _write_json(self.repo, review_relative, review)
        payload["admitted_units"][0]["acceptance_review"] = _ref(
            self.repo, review_relative
        )
        _write_json(self.repo, relative, payload)
        result = compile_baseline_admission(str(self.repo), relative)
        self.assertEqual(BLOCKED_BY_ADMISSION_MATERIAL, result.status)
        self.assertTrue(any("legacy historical evidence" in error for error in result.errors))

    def test_regression_must_cover_every_predecessor_unit(self) -> None:
        _, _, predecessor_ref = self._compile_first_baseline()
        relative, payload = self._promotion_input(predecessor_ref)
        regression_path = self.repo / payload["verification"]["regression_review"]["path"]
        review = json.loads(regression_path.read_text())
        review["covered_unit_ids"] = []
        _write_json(self.repo, payload["verification"]["regression_review"]["path"], review)
        payload["verification"]["regression_review"] = _ref(
            self.repo, payload["verification"]["regression_review"]["path"]
        )
        _write_json(self.repo, relative, payload)
        result = compile_baseline_admission(str(self.repo), relative)
        self.assertEqual(BLOCKED_BY_ADMISSION_MATERIAL, result.status)
        self.assertTrue(any("exactly every predecessor" in error for error in result.errors))

    def test_reconstruction_mode_is_rejected_after_baseline_exists(self) -> None:
        self._compile_first_baseline()
        _commit(self.repo, "record first admission")
        self.revision_one = _run(self.repo, "rev-parse", "HEAD")
        relative, payload = self._reconstruction_input("admission-rebuild")
        payload["baseline_id"] = "baseline-rebuild"
        _write_json(self.repo, relative, payload)
        result = compile_baseline_admission(str(self.repo), relative)
        self.assertEqual(BLOCKED_BY_ADMISSION_MATERIAL, result.status)
        self.assertTrue(any("EXPLICIT_REBUILD" in error for error in result.errors))

    def test_explicit_reconstruction_supersedes_without_mutating_current_baseline(self) -> None:
        _, _, current_ref = self._compile_first_baseline()
        current_bytes = (self.repo / current_ref["path"]).read_bytes()
        _commit(self.repo, "record first admission")
        self.revision_one = _run(self.repo, "rev-parse", "HEAD")
        relative, payload = self._reconstruction_input("admission-rebuild")
        payload["baseline_id"] = "baseline-rebuilt"
        payload["reconstruction"] = {
            "trigger": "EXPLICIT_REBUILD",
            "reason": "The user requested a complete reconstruction",
            "author_context_ids": ["reconstruction-author-one"],
            "inventory": payload["reconstruction"]["inventory"],
            "superseded_baseline": current_ref,
        }
        _write_json(self.repo, relative, payload)
        routed = start_baseline_admission(str(self.repo), reconstruct=True)
        self.assertEqual(BASELINE_RECONSTRUCTION_INPUT_REQUIRED, routed.status)
        result = compile_baseline_admission(str(self.repo), relative)
        self.assertEqual(BASELINE_ADMITTED, result.status, result.errors)
        self.assertEqual(current_bytes, (self.repo / current_ref["path"]).read_bytes())
        rebuilt = json.loads(
            (
                self.repo
                / "design/studio/baselines/baseline-rebuilt/ACCEPTED_PLAYABLE_BASELINE.json"
            ).read_text()
        )
        self.assertEqual(current_ref, rebuilt["promotion"]["superseded_baseline"])

    def test_reconstruction_inventory_must_equal_all_admitted_units(self) -> None:
        relative, payload = self._reconstruction_input()
        inventory_path = self.repo / payload["reconstruction"]["inventory"]["path"]
        inventory = json.loads(inventory_path.read_text())
        inventory["discovered_unit_ids"] = ["different-unit"]
        _write_json(self.repo, payload["reconstruction"]["inventory"]["path"], inventory)
        payload["reconstruction"]["inventory"] = _ref(
            self.repo, payload["reconstruction"]["inventory"]["path"]
        )
        _write_json(self.repo, relative, payload)
        result = compile_baseline_admission(str(self.repo), relative)
        self.assertEqual(BLOCKED_BY_ADMISSION_MATERIAL, result.status)
        self.assertTrue(any("inventory unit ids" in error for error in result.errors))

    def test_immutable_baseline_is_never_overwritten(self) -> None:
        relative, _ = self._reconstruction_input()
        baseline_path = self.repo / "design/studio/baselines/baseline-one/ACCEPTED_PLAYABLE_BASELINE.json"
        baseline_path.parent.mkdir(parents=True)
        baseline_path.write_text("foreign\n", encoding="utf-8")
        result = compile_baseline_admission(str(self.repo), relative)
        self.assertEqual(BLOCKED_BY_EXISTING_BASELINE, result.status)
        self.assertEqual("foreign\n", baseline_path.read_text())

    def test_runtime_dirty_path_blocks_admission(self) -> None:
        relative, _ = self._reconstruction_input()
        _write(self.repo, "game/runtime.py", "dirty implementation\n")
        result = compile_baseline_admission(str(self.repo), relative)
        self.assertEqual(BLOCKED_BY_ADMISSION_MATERIAL, result.status)
        self.assertTrue(any("must be committed" in error for error in result.errors))

    def test_outside_input_is_rejected_before_output_creation(self) -> None:
        outside = Path(self.temp.name) / "outside.json"
        outside.write_text("{}\n")
        with self.assertRaises(BaselineAdmissionError):
            compile_baseline_admission(str(self.repo), str(outside))
        self.assertFalse((self.repo / "design/studio").exists())


if __name__ == "__main__":
    unittest.main()
