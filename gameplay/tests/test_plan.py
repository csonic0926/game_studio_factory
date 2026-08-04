import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from gameplay.design_gate import current_factory_revision
from gameplay.plan import (
    BLOCKED_BY_PLAN_GAP,
    READY_FOR_EXECUTION,
    PlanningError,
    validate_production_plan,
)


class ProductionPlanValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.game_repo = Path(self.temporary_directory.name) / "game"
        self.objective_dir = (
            self.game_repo / "design/gameplay/objective_gameplay/mission.next"
        )
        self.plan_dir = self.objective_dir / "production_plans"
        self.plan_dir.mkdir(parents=True)
        self.objective_relative = (
            "design/gameplay/objective_gameplay/mission.next/OBJECTIVE_GAMEPLAY.md"
        )
        self.manifest_relative = (
            "design/gameplay/objective_gameplay/mission.next/"
            "PRODUCTION_PLAN_MANIFEST.json"
        )
        self.plan_relative = (
            "design/gameplay/objective_gameplay/mission.next/"
            "production_plans/P01_gate.md"
        )
        self.objective_text = """# Objective Gameplay — `mission.next`

- Context status: `READY_FOR_HOW_DESIGN`
- Design status: `USER_APPROVED`

## Expected player experience

- Target player: A player choosing a route through the mission.
- Intended experience: Read the fork, make a deliberate choice, and understand the consequence.
- Required player work: Compare two visible routes and commit to one.
- Earned satisfaction: The selected route opens because of the player's decision.
- Failure / recovery: A wrong route can be reconsidered before the gate is opened.
- Must not become: An automatic gate with no meaningful route choice.

| # | Situation | Result |
| --- | --- | --- |
| 1 | Reach a fork. | Pick a route. |
| 2 | Reach the gate. | Open it. |
"""
        (self.objective_dir / "OBJECTIVE_GAMEPLAY.md").write_text(
            self.objective_text, encoding="utf-8"
        )
        self.objective_sha256 = hashlib.sha256(
            self.objective_text.encode("utf-8")
        ).hexdigest()
        self.factory_revision = current_factory_revision(Path(__file__).resolve().parents[2])
        self.verdict_relative = (
            "design/gameplay/objective_gameplay/mission.next/"
            "GAMEPLAY_DESIGN_VERDICT.json"
        )
        self._write_design_verdict()
        (self.game_repo / "game.gd").write_text("func open_gate():\n\tpass\n", encoding="utf-8")
        self._write_plan()
        self._write_manifest()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def _plan_text(self, *, status: str = READY_FOR_EXECUTION) -> str:
        return f"""# Production Plan — Gate route

- Plan id: `P01`
- Status: `{status}`
- Source objective: `{self.objective_relative}`
- Source SHA-256: `{self.objective_sha256}`
- Objective rows: `1`

## Source authority
Row 1 defines the route fork.

## Required player-visible result
The player sees and can use both routes.

## Existing repo evidence and reuse
`game.gd` already opens the gate.

## Production changes
Add the fork to `game.gd`.

## Locked constraints and non-goals
Do not add a mission branch.

## Verification
Test both routes independently.

## Dependencies and handoff
No prerequisite plan.
"""

    def _write_plan(self, *, status: str = READY_FOR_EXECUTION) -> None:
        (self.plan_dir / "P01_gate.md").write_text(
            self._plan_text(status=status), encoding="utf-8"
        )

    def _write_design_verdict(
        self,
        *,
        context_status: str = "READY_FOR_HOW_DESIGN",
        human_verdict: str = "USER_APPROVED",
        objective_sha256: str | None = None,
        factory_revision: str | None = None,
    ) -> None:
        verdict = {
            "schema_version": "gameplay_design_verdict.v1",
            "verdict_id": "mission.next.design.1",
            "project_id": "sample",
            "objective_id": "mission.next",
            "factory_revision": factory_revision or self.factory_revision,
            "objective_gameplay": {
                "path": self.objective_relative,
                "sha256": objective_sha256 or self.objective_sha256,
            },
            "context_status": context_status,
            "reviewer_context_id": "fresh.design.reviewer.1",
            "reviewer_freshness": "FRESH",
            "factory_verdict": "PASS_DESIGN_REVIEW",
            "human_verdict": human_verdict,
            "human_verdict_source": {
                "kind": (
                    "POST_DRAFT_APPROVAL"
                    if human_verdict == "USER_APPROVED"
                    else "EXPLICIT_DELEGATION"
                ),
                "text": "User approved this exact objective draft.",
                "recorded_at": "2026-08-04T12:00:00+08:00",
            },
            "blocking_findings": [],
            "reviewed_at": "2026-08-04T12:01:00+08:00",
        }
        verdict_path = self.objective_dir / "GAMEPLAY_DESIGN_VERDICT.json"
        verdict_path.write_text(json.dumps(verdict, indent=2) + "\n", encoding="utf-8")
        self.verdict_sha256 = hashlib.sha256(verdict_path.read_bytes()).hexdigest()

    @staticmethod
    def _no_ui_impact() -> dict:
        return {
            "touches_ui": False,
            "adapter_path": "",
            "adapter_sha256": "",
            "rule_ids": [],
            "exemplar_ids": [],
            "validation_scenario_ids": [],
        }

    def _manifest(self) -> dict:
        return {
            "schema_version": "production_plan_manifest.v3",
            "factory_revision": self.factory_revision,
            "project_id": "sample",
            "objective_id": "mission.next",
            "objective_gameplay_path": self.objective_relative,
            "objective_gameplay_sha256": self.objective_sha256,
            "design_verdict": {
                "path": self.verdict_relative,
                "sha256": self.verdict_sha256,
            },
            "planning_status": READY_FOR_EXECUTION,
            "plans": [
                {
                    "plan_id": "P01",
                    "path": self.plan_relative,
                    "title": "Gate route",
                    "status": READY_FOR_EXECUTION,
                    "objective_rows": [1],
                    "depends_on": [],
                    "work_types": ["CONTENT_DATA", "TEST"],
                    "existing_repo_refs": ["game.gd"],
                    "planned_paths": ["game.gd"],
                    "ui_impact": self._no_ui_impact(),
                }
            ],
            "row_coverage": [
                {
                    "objective_row": 1,
                    "disposition": "IMPLEMENT",
                    "plan_ids": ["P01"],
                    "rationale": "The fork is not implemented.",
                },
                {
                    "objective_row": 2,
                    "disposition": "NO_CHANGE_REQUIRED",
                    "plan_ids": [],
                    "rationale": "The existing gate behavior already realizes the transport row.",
                },
            ],
            "blocked_gaps": [],
        }

    def _write_manifest(self, payload: dict | None = None) -> None:
        (self.objective_dir / "PRODUCTION_PLAN_MANIFEST.json").write_text(
            json.dumps(payload or self._manifest(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def _ui_binding(self) -> dict:
        adapter_path = (
            self.game_repo
            / "design/gameplay/adapter/UI_PRODUCTION_ADAPTER.json"
        )
        adapter_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_sha = hashlib.sha256(
            (self.game_repo / "game.gd").read_bytes()
        ).hexdigest()
        evidence_refs = [
            {
                "path": "game.gd",
                "source_sha256": evidence_sha,
            }
        ]
        adapter = {
            "schema_version": "ui_production_adapter.v1",
            "status": "UI_PRODUCTION_ADAPTER_READY",
            "surfaces": [{"evidence_refs": evidence_refs}],
            "rules": [
                {"rule_id": "layout.container", "evidence_refs": evidence_refs}
            ],
            "canonical_exemplars": [
                {"exemplar_id": "main.panel", "evidence_refs": evidence_refs}
            ],
            "viewport_profiles": [{"viewport_id": "desktop"}],
            "localization_profiles": [{"profile_id": "stress"}],
            "validation_scenarios": [{"scenario_id": "desktop.populated"}],
        }
        adapter_path.write_text(json.dumps(adapter) + "\n", encoding="utf-8")
        adapter_sha = hashlib.sha256(adapter_path.read_bytes()).hexdigest()
        result_path = (
            self.game_repo
            / "design/gameplay/ui/UI_PRODUCTION_ADAPTER_RESULT.json"
        )
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(
            json.dumps(
                {
                    "schema_version": "ui_production_adapter_result.v1",
                    "status": "UI_PRODUCTION_ADAPTER_READY",
                    "outputs": {
                        "design/gameplay/adapter/UI_PRODUCTION_ADAPTER.json": adapter_sha
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return {
            "touches_ui": True,
            "adapter_path": "design/gameplay/adapter/UI_PRODUCTION_ADAPTER.json",
            "adapter_sha256": adapter_sha,
            "rule_ids": ["layout.container"],
            "exemplar_ids": ["main.panel"],
            "validation_scenario_ids": ["desktop.populated"],
        }

    def test_valid_manifest_and_persisted_plan_are_ready(self) -> None:
        result = validate_production_plan(
            str(self.game_repo), self.manifest_relative
        )
        self.assertEqual(READY_FOR_EXECUTION, result.status)
        self.assertEqual([1, 2], result.objective_rows)
        self.assertEqual(1, result.plan_count)
        self.assertFalse(result.errors)

    def test_absolute_active_manifest_argument_is_allowed(self) -> None:
        result = validate_production_plan(
            str(self.game_repo),
            str(self.objective_dir / "PRODUCTION_PLAN_MANIFEST.json"),
        )
        self.assertEqual(READY_FOR_EXECUTION, result.status)

    def test_explicit_blocked_plan_gap_is_preserved_without_fake_readiness(self) -> None:
        payload = self._manifest()
        payload["planning_status"] = BLOCKED_BY_PLAN_GAP
        payload["blocked_gaps"] = ["The gate target is not specified."]
        payload["plans"][0]["status"] = BLOCKED_BY_PLAN_GAP
        self._write_plan(status=BLOCKED_BY_PLAN_GAP)
        self._write_manifest(payload)
        result = validate_production_plan(
            str(self.game_repo), self.manifest_relative
        )
        self.assertEqual(BLOCKED_BY_PLAN_GAP, result.status)
        self.assertFalse(result.errors)

    def test_missing_objective_row_coverage_fails_closed(self) -> None:
        payload = self._manifest()
        payload["row_coverage"] = payload["row_coverage"][:1]
        self._write_manifest(payload)
        result = validate_production_plan(
            str(self.game_repo), self.manifest_relative
        )
        self.assertEqual(BLOCKED_BY_PLAN_GAP, result.status)
        self.assertTrue(any("missing objective rows: 2" in error for error in result.errors))

    def test_stale_objective_hash_fails_closed(self) -> None:
        (self.objective_dir / "OBJECTIVE_GAMEPLAY.md").write_text(
            self.objective_text + "\nChanged.\n", encoding="utf-8"
        )
        result = validate_production_plan(
            str(self.game_repo), self.manifest_relative
        )
        self.assertEqual(BLOCKED_BY_PLAN_GAP, result.status)
        self.assertTrue(any("does not match" in error for error in result.errors))

    def test_ready_plan_with_tbd_fails_closed(self) -> None:
        plan_path = self.plan_dir / "P01_gate.md"
        plan_path.write_text(
            self._plan_text() + "\nTBD\n", encoding="utf-8"
        )
        result = validate_production_plan(
            str(self.game_repo), self.manifest_relative
        )
        self.assertEqual(BLOCKED_BY_PLAN_GAP, result.status)
        self.assertTrue(any("still contains TBD" in error for error in result.errors))

    def test_plan_metadata_must_match_manifest(self) -> None:
        plan_path = self.plan_dir / "P01_gate.md"
        plan_path.write_text(
            self._plan_text().replace("- Plan id: `P01`", "- Plan id: `P99`"),
            encoding="utf-8",
        )
        result = validate_production_plan(
            str(self.game_repo), self.manifest_relative
        )
        self.assertEqual(BLOCKED_BY_PLAN_GAP, result.status)
        self.assertTrue(any("Plan id does not match" in error for error in result.errors))

    def test_shared_planned_path_is_rejected(self) -> None:
        second_plan_relative = (
            "design/gameplay/objective_gameplay/mission.next/"
            "production_plans/P02_gate.md"
        )
        second_plan = self._plan_text().replace("P01", "P02").replace(
            "- Objective rows: `1`", "- Objective rows: `2`"
        )
        (self.plan_dir / "P02_gate.md").write_text(second_plan, encoding="utf-8")
        payload = self._manifest()
        payload["plans"].append(
            {
                "plan_id": "P02",
                "path": second_plan_relative,
                "title": "Gate verification",
                "status": READY_FOR_EXECUTION,
                "objective_rows": [2],
                "depends_on": [],
                "work_types": ["TEST"],
                "existing_repo_refs": ["game.gd"],
                "planned_paths": ["game.gd"],
                "ui_impact": self._no_ui_impact(),
            }
        )
        payload["row_coverage"][1] = {
            "objective_row": 2,
            "disposition": "VERIFY_EXISTING",
            "plan_ids": ["P02"],
            "rationale": "The gate behavior needs a regression test.",
        }
        self._write_manifest(payload)
        result = validate_production_plan(
            str(self.game_repo), self.manifest_relative
        )
        self.assertEqual(BLOCKED_BY_PLAN_GAP, result.status)
        self.assertTrue(any("owned by multiple" in error for error in result.errors))

    def test_dependency_cycle_is_rejected(self) -> None:
        second_plan_relative = (
            "design/gameplay/objective_gameplay/mission.next/"
            "production_plans/P02_gate.md"
        )
        second_plan = self._plan_text().replace("P01", "P02").replace(
            "- Objective rows: `1`", "- Objective rows: `2`"
        )
        (self.plan_dir / "P02_gate.md").write_text(second_plan, encoding="utf-8")
        payload = self._manifest()
        payload["plans"][0]["depends_on"] = ["P02"]
        payload["plans"].append(
            {
                "plan_id": "P02",
                "path": second_plan_relative,
                "title": "Gate verification",
                "status": READY_FOR_EXECUTION,
                "objective_rows": [2],
                "depends_on": ["P01"],
                "work_types": ["TEST"],
                "existing_repo_refs": ["game.gd"],
                "planned_paths": ["tests/test_gate.gd"],
                "ui_impact": self._no_ui_impact(),
            }
        )
        payload["row_coverage"][1] = {
            "objective_row": 2,
            "disposition": "VERIFY_EXISTING",
            "plan_ids": ["P02"],
            "rationale": "The gate behavior needs a regression test.",
        }
        self._write_manifest(payload)
        result = validate_production_plan(
            str(self.game_repo), self.manifest_relative
        )
        self.assertEqual(BLOCKED_BY_PLAN_GAP, result.status)
        self.assertTrue(any("contain a cycle" in error for error in result.errors))

    def test_absolute_persisted_plan_path_is_rejected(self) -> None:
        payload = self._manifest()
        payload["plans"][0]["path"] = str(self.plan_dir / "P01_gate.md")
        self._write_manifest(payload)
        with self.assertRaises(PlanningError):
            validate_production_plan(str(self.game_repo), self.manifest_relative)

    def test_plan_outside_canonical_directory_is_rejected(self) -> None:
        outside_plan = self.objective_dir / "P01_gate.md"
        outside_plan.write_text(self._plan_text(), encoding="utf-8")
        payload = self._manifest()
        payload["plans"][0]["path"] = (
            "design/gameplay/objective_gameplay/mission.next/P01_gate.md"
        )
        self._write_manifest(payload)
        with self.assertRaises(PlanningError):
            validate_production_plan(str(self.game_repo), self.manifest_relative)

    def test_legacy_ui_plan_requires_regeneration(self) -> None:
        payload = self._manifest()
        payload["schema_version"] = "production_plan_manifest.v1"
        payload.pop("factory_revision")
        payload.pop("design_verdict")
        payload["plans"][0].pop("ui_impact")
        payload["plans"][0]["work_types"] = ["UI", "TEST"]
        self._write_manifest(payload)
        result = validate_production_plan(str(self.game_repo), self.manifest_relative)
        self.assertEqual(BLOCKED_BY_PLAN_GAP, result.status)
        self.assertTrue(any("legacy v1 UI plan" in error for error in result.errors))

    def test_v2_ui_plan_must_bind_exact_adapter_and_markdown_contract(self) -> None:
        binding = self._ui_binding()
        (self.game_repo / "ui").mkdir(exist_ok=True)
        (self.game_repo / "ui/main.tscn").write_text("[node]\n", encoding="utf-8")
        payload = self._manifest()
        payload["plans"][0]["work_types"] = ["UI", "TEST"]
        payload["plans"][0]["planned_paths"] = ["ui/main.tscn"]
        payload["plans"][0]["ui_impact"] = binding
        self._write_manifest(payload)
        plan = self._plan_text() + f"""
## UI realization contract
- UI adapter: `{binding['adapter_path']}`
- UI adapter SHA-256: `{binding['adapter_sha256']}`
- UI rules: `layout.container`
- UI exemplars: `main.panel`
- UI validation scenarios: `desktop.populated`
"""
        (self.plan_dir / "P01_gate.md").write_text(plan, encoding="utf-8")
        result = validate_production_plan(str(self.game_repo), self.manifest_relative)
        self.assertEqual(READY_FOR_EXECUTION, result.status)
        self.assertFalse(result.errors)
        (self.game_repo / "game.gd").write_text(
            "func open_gate():\n\tpass\n# changed UI authority source\n",
            encoding="utf-8",
        )
        stale = validate_production_plan(str(self.game_repo), self.manifest_relative)
        self.assertEqual(BLOCKED_BY_PLAN_GAP, stale.status)
        self.assertTrue(
            any("UI adapter evidence changed" in error for error in stale.errors)
        )

    def test_obvious_ui_path_cannot_declare_no_ui_impact(self) -> None:
        payload = self._manifest()
        payload["plans"][0]["planned_paths"] = ["ui/main.tscn"]
        payload["plans"][0]["ui_impact"] = {
            "touches_ui": False,
            "adapter_path": "",
            "adapter_sha256": "",
            "rule_ids": [],
            "exemplar_ids": [],
            "validation_scenario_ids": [],
        }
        self._write_manifest(payload)
        result = validate_production_plan(str(self.game_repo), self.manifest_relative)
        self.assertEqual(BLOCKED_BY_PLAN_GAP, result.status)
        self.assertTrue(any("touches_ui=false" in error for error in result.errors))

    def test_ai_draft_cannot_enter_production(self) -> None:
        objective = self.objective_text.replace(
            "- Design status: `USER_APPROVED`",
            "- Design status: `AI_DRAFT_FOR_REVIEW`",
        )
        objective_path = self.objective_dir / "OBJECTIVE_GAMEPLAY.md"
        objective_path.write_text(objective, encoding="utf-8")
        payload = self._manifest()
        payload["objective_gameplay_sha256"] = hashlib.sha256(
            objective.encode("utf-8")
        ).hexdigest()
        self._write_manifest(payload)
        result = validate_production_plan(str(self.game_repo), self.manifest_relative)
        self.assertEqual(BLOCKED_BY_PLAN_GAP, result.status)
        self.assertTrue(any("Design status" in error for error in result.errors))

    def test_new_gameplay_design_requires_post_draft_user_approval(self) -> None:
        objective = self.objective_text.replace(
            "READY_FOR_HOW_DESIGN", "READY_FOR_NEW_GAMEPLAY_DESIGN"
        ).replace("USER_APPROVED", "USER_DELEGATED")
        objective_path = self.objective_dir / "OBJECTIVE_GAMEPLAY.md"
        objective_path.write_text(objective, encoding="utf-8")
        objective_sha = hashlib.sha256(objective.encode("utf-8")).hexdigest()
        self._write_design_verdict(
            context_status="READY_FOR_NEW_GAMEPLAY_DESIGN",
            human_verdict="USER_DELEGATED",
            objective_sha256=objective_sha,
        )
        payload = self._manifest()
        payload["objective_gameplay_sha256"] = objective_sha
        payload["design_verdict"]["sha256"] = self.verdict_sha256
        self._write_manifest(payload)
        result = validate_production_plan(str(self.game_repo), self.manifest_relative)
        self.assertEqual(BLOCKED_BY_PLAN_GAP, result.status)
        self.assertTrue(any("delegation is insufficient" in error for error in result.errors))

    def test_stale_design_verdict_hash_fails_closed(self) -> None:
        payload = self._manifest()
        payload["design_verdict"]["sha256"] = "0" * 64
        self._write_manifest(payload)
        result = validate_production_plan(str(self.game_repo), self.manifest_relative)
        self.assertEqual(BLOCKED_BY_PLAN_GAP, result.status)
        self.assertTrue(any("design_verdict hash" in error for error in result.errors))

    def test_factory_revision_mismatch_fails_closed(self) -> None:
        payload = self._manifest()
        payload["factory_revision"] = "0" * 40
        self._write_manifest(payload)
        result = validate_production_plan(str(self.game_repo), self.manifest_relative)
        self.assertEqual(BLOCKED_BY_PLAN_GAP, result.status)
        self.assertTrue(any("Factory HEAD" in error for error in result.errors))

    def test_legacy_manifest_is_historical_check_only(self) -> None:
        payload = self._manifest()
        payload["schema_version"] = "production_plan_manifest.v2"
        payload.pop("factory_revision")
        payload.pop("design_verdict")
        self._write_manifest(payload)
        active = validate_production_plan(str(self.game_repo), self.manifest_relative)
        self.assertEqual(BLOCKED_BY_PLAN_GAP, active.status)
        self.assertTrue(any("historical-only" in error for error in active.errors))
        historical = validate_production_plan(
            str(self.game_repo),
            self.manifest_relative,
            allow_legacy_historical=True,
        )
        self.assertEqual(READY_FOR_EXECUTION, historical.status)
        self.assertFalse(historical.errors)


if __name__ == "__main__":
    unittest.main()
