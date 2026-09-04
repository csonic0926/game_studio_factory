import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from gameplay.design_gate import (
    _validate_studio_card_projection,
    current_factory_revision,
    decision_payload_sha256,
)
from gameplay.plan import (
    BLOCKED_BY_PLAN_GAP,
    HISTORICAL_PLAN_READABLE,
    READY_FOR_EXECUTION,
    PlanningError,
    validate_production_plan,
)
from studio.tests.player_surface_fixture import write_contract_pair
from gameplay.tests.project_card_fixture import attach_project_review


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

- Step 1 context: `design/gameplay/objective_gameplay/mission.next/NEXT_GAMEPLAY_UNIT_CONTEXT.md`
- Context status: `READY_FOR_HOW_DESIGN`
- Author context id: `full-spec-author`
- Objective: Choose a route and deliberately open its gate.
- Frontier decision: `COMPLETE_CURRENT_UNIT`
- Design status: `USER_APPROVED`

## Expected player experience

- Target player: A player choosing a route through the mission.
- Intended experience: Read the fork, make a deliberate choice, and understand the consequence.
- Required player work: Compare two visible routes and commit to one.
- Earned satisfaction: The selected route opens because of the player's decision.
- Failure / recovery: A wrong route can be reconsidered before the gate is opened.
- Must not become: An automatic gate with no meaningful route choice.

| # | Situation / objective progress | Player purpose or problem | Visible information | Available actions | Rewards / consequences | Meaningful decision or execution | Resulting next situation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Reach a fork. | Choose a route. | Both route costs. | Inspect and select. | The chosen gate activates. | Compare the routes and commit. | Reach the selected gate. |
| 2 | Reach the gate. | Open the chosen path. | The committed route. | Open its gate. | The route becomes traversable. | Execute the committed choice. | Continue through the route. |

## New gameplay additions

- A visible two-route commitment at the gate.

## Completion handoff

- Objective completion condition: The selected route's gate is opened.
- Player-visible completion response: The chosen route visibly becomes traversable.
- Successor objective/handoff: `WIRED` — Continue through the selected route.
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
        self.card_relative = (
            "design/gameplay/objective_gameplay/mission.next/"
            "GAMEPLAY_DECISION_CARD.json"
        )
        self.card_to_spec_relative = (
            "design/gameplay/objective_gameplay/mission.next/"
            "GAMEPLAY_CONFORMANCE_CARD_TO_SPEC.json"
        )
        self.spec_to_card_relative = (
            "design/gameplay/objective_gameplay/mission.next/"
            "GAMEPLAY_CONFORMANCE_SPEC_TO_CARD.json"
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
        effective_factory_revision = factory_revision or self.factory_revision
        effective_objective_sha = objective_sha256 or self.objective_sha256
        contract_ref, contract_review_ref, _ = write_contract_pair(
            self.game_repo,
            self.objective_dir,
            project_id="sample",
            objective_id="mission.next",
            factory_revision=effective_factory_revision,
            product_ref={"path": "", "sha256": ""},
            system_ref={"path": "", "sha256": ""},
            transition_ids=["read", "commit", "feedback"],
        )
        card = {
            "schema_version": "gameplay_decision_card.v3",
            "card_id": "mission.next.card.1",
            "project_id": "sample",
            "objective_id": "mission.next",
            "factory_revision": effective_factory_revision,
            "routing": "DIRECT_SPECIALIST",
            "product_authority": {"path": "", "sha256": ""},
            "studio_gameplay_system": {"path": "", "sha256": ""},
            "player_facing_interaction_contract": contract_ref,
            "player_facing_interaction_contract_review": contract_review_ref,
            "author_context_id": "card-author",
            "player_promise": {
                "claim_id": "promise.route-choice",
                "text": "Read a route fork, commit to one route, and visibly open its gate.",
            },
            "core_cycle": [
                {"claim_id": "cycle.read", "text": "Read two visible route options."},
                {"claim_id": "cycle.commit", "text": "Commit to one route and open its gate."},
                {"claim_id": "cycle.feedback", "text": "Use the visible route state to continue."},
            ],
            "material_commitments": [
                {"claim_id": "commitment.two-routes", "text": "The gate exposes two routes and records the chosen one."}
            ],
            "red_lines": [
                {"claim_id": "redline.automatic", "text": "The gate must not choose a route automatically."}
            ],
            "validation_hypotheses": [
                {
                    "claim_id": "hypothesis.route-readable",
                    "text": "A first-time player can distinguish the two routes.",
                    "falsification_signal": "A blind player cannot explain the route difference.",
                    "status": "TESTABLE_DESIGN",
                }
            ],
            "decision_payload_sha256": "",
            "human_verdict": {
                "status": human_verdict,
                "source_text": "",
                "recorded_at": "2026-08-04T12:00:00+08:00",
            },
        }
        card["decision_payload_sha256"] = decision_payload_sha256(card)
        card["human_verdict"]["source_text"] = (
            f"{human_verdict} {card['decision_payload_sha256']}"
        )
        card_path = self.objective_dir / "GAMEPLAY_DECISION_CARD.json"
        attach_project_review(
            self.game_repo,
            self.objective_dir,
            card,
            interaction_contract_ref=contract_ref,
            interaction_contract_review_ref=contract_review_ref,
        )
        card_sha = hashlib.sha256(card_path.read_bytes()).hexdigest()

        mapping = {
            "promise.route-choice": [
                "objective.promise", "expected.target_player", "expected.intended_experience"
            ],
            "cycle.read": ["expected.required_player_work", "row.1"],
            "cycle.commit": [
                "expected.earned_satisfaction", "row.2", "completion.objective",
                "completion.response", "completion.successor",
            ],
            "cycle.feedback": ["expected.failure_recovery"],
            "commitment.two-routes": ["addition.1"],
            "redline.automatic": ["expected.must_not_become"],
            "hypothesis.route-readable": ["expected.target_player"],
        }
        card_to_spec = {
            "schema_version": "gameplay_design_conformance_review.v2",
            "review_id": "mission.next.card-to-spec.1",
            "review_role": "CARD_TO_SPEC",
            "project_id": "sample",
            "objective_id": "mission.next",
            "factory_revision": effective_factory_revision,
            "decision_card": {"path": self.card_relative, "sha256": card_sha},
            "objective_gameplay": {
                "path": self.objective_relative,
                "sha256": effective_objective_sha,
            },
            "reviewer_context_id": "card-to-spec-reviewer",
            "reviewer_freshness": "FRESH",
            "claim_coverage": [
                {
                    "claim_id": claim_id,
                    "spec_refs": refs,
                    "verdict": (
                        "TESTABLE_DESIGN"
                        if claim_id.startswith("hypothesis.")
                        else "PASS_DESIGN_CLAIM"
                    ),
                }
                for claim_id, refs in mapping.items()
            ],
            "spec_material_inventory": [],
            "contradictions": [],
            "ambiguities": [],
            "unsupported_material_decisions": [],
            "blocking_findings": [],
            "verdict": "PASS_CONFORMANCE",
            "reviewed_at": "2026-08-04T12:01:00+08:00",
        }
        card_to_spec_path = self.objective_dir / "GAMEPLAY_CONFORMANCE_CARD_TO_SPEC.json"
        card_to_spec_path.write_text(
            json.dumps(card_to_spec, indent=2) + "\n", encoding="utf-8"
        )
        card_to_spec_sha = hashlib.sha256(card_to_spec_path.read_bytes()).hexdigest()

        reverse: dict[str, list[str]] = {}
        for claim_id, spec_refs in mapping.items():
            for spec_ref in spec_refs:
                reverse.setdefault(spec_ref, []).append(claim_id)
        spec_to_card = {
            "schema_version": "gameplay_design_conformance_review.v2",
            "review_id": "mission.next.spec-to-card.1",
            "review_role": "SPEC_TO_CARD",
            "project_id": "sample",
            "objective_id": "mission.next",
            "factory_revision": effective_factory_revision,
            "decision_card": {"path": self.card_relative, "sha256": card_sha},
            "objective_gameplay": {
                "path": self.objective_relative,
                "sha256": effective_objective_sha,
            },
            "reviewer_context_id": "spec-to-card-reviewer",
            "reviewer_freshness": "FRESH",
            "claim_coverage": [],
            "spec_material_inventory": [
                {
                    "spec_ref": spec_ref,
                    "claim_ids": claim_ids,
                    "classification": "AUTHORIZED_BY_CARD",
                    "rationale": "This full-spec item refines the named card claim.",
                }
                for spec_ref, claim_ids in reverse.items()
            ],
            "contradictions": [],
            "ambiguities": [],
            "unsupported_material_decisions": [],
            "blocking_findings": [],
            "verdict": "PASS_CONFORMANCE",
            "reviewed_at": "2026-08-04T12:02:00+08:00",
        }
        spec_to_card_path = self.objective_dir / "GAMEPLAY_CONFORMANCE_SPEC_TO_CARD.json"
        spec_to_card_path.write_text(
            json.dumps(spec_to_card, indent=2) + "\n", encoding="utf-8"
        )
        spec_to_card_sha = hashlib.sha256(spec_to_card_path.read_bytes()).hexdigest()

        verdict = {
            "schema_version": "gameplay_design_verdict.v2",
            "verdict_id": "mission.next.design.1",
            "project_id": "sample",
            "objective_id": "mission.next",
            "factory_revision": effective_factory_revision,
            "objective_gameplay": {
                "path": self.objective_relative,
                "sha256": effective_objective_sha,
            },
            "context_status": context_status,
            "decision_card": {"path": self.card_relative, "sha256": card_sha},
            "conformance_reviews": {
                "card_to_spec": {
                    "path": self.card_to_spec_relative,
                    "sha256": card_to_spec_sha,
                },
                "spec_to_card": {
                    "path": self.spec_to_card_relative,
                    "sha256": spec_to_card_sha,
                },
            },
            "factory_verdict": "PASS_DESIGN_CONFORMANCE",
            "blocking_findings": [],
            "reviewed_at": "2026-08-04T12:03:00+08:00",
        }
        verdict_path = self.objective_dir / "GAMEPLAY_DESIGN_VERDICT.json"
        verdict_path.write_text(json.dumps(verdict, indent=2) + "\n", encoding="utf-8")
        self.verdict_sha256 = hashlib.sha256(verdict_path.read_bytes()).hexdigest()

    def _rebind_changed_card(self, card: dict) -> None:
        card_path = self.objective_dir / "GAMEPLAY_DECISION_CARD.json"
        card_path.write_text(json.dumps(card, indent=2) + "\n", encoding="utf-8")
        card_sha = hashlib.sha256(card_path.read_bytes()).hexdigest()
        review_hashes: dict[str, str] = {}
        for key, filename in (
            ("card_to_spec", "GAMEPLAY_CONFORMANCE_CARD_TO_SPEC.json"),
            ("spec_to_card", "GAMEPLAY_CONFORMANCE_SPEC_TO_CARD.json"),
        ):
            review_path = self.objective_dir / filename
            review = json.loads(review_path.read_text())
            review["decision_card"]["sha256"] = card_sha
            review_path.write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")
            review_hashes[key] = hashlib.sha256(review_path.read_bytes()).hexdigest()
        verdict_path = self.objective_dir / "GAMEPLAY_DESIGN_VERDICT.json"
        verdict = json.loads(verdict_path.read_text())
        verdict["decision_card"]["sha256"] = card_sha
        for key, digest in review_hashes.items():
            verdict["conformance_reviews"][key]["sha256"] = digest
        verdict_path.write_text(json.dumps(verdict, indent=2) + "\n", encoding="utf-8")
        payload = self._manifest()
        payload["design_verdict"]["sha256"] = hashlib.sha256(
            verdict_path.read_bytes()
        ).hexdigest()
        self._write_manifest(payload)

    @staticmethod
    def _no_ui_impact() -> dict:
        return {
            "touches_ui": False,
            "adapter_path": "",
            "adapter_sha256": "",
            "rule_ids": [],
            "exemplar_ids": [],
            "validation_scenario_ids": [],
            "style_blast_radius_scope": "",
            "style_blast_radius": [],
        }

    def _manifest(self) -> dict:
        return {
            "schema_version": "production_plan_manifest.v4",
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
            "schema_version": "ui_production_adapter.v2",
            "status": "UI_PRODUCTION_ADAPTER_READY",
            "visual_grammar_policy": {
                "default_without_explicit_redesign": "PRESERVE_EXISTING_VISUAL_GRAMMAR",
                "redesign_requires": "USER_RULING",
            },
            "surfaces": [{"evidence_refs": evidence_refs}],
            "rules": [
                {
                    "rule_id": "visual.existing-grammar",
                    "category": "VISUAL_GRAMMAR",
                    "evidence_refs": evidence_refs,
                }
            ],
            "canonical_exemplars": [
                {
                    "exemplar_id": "main.panel",
                    "rules_illustrated": ["visual.existing-grammar"],
                    "acceptance_provenance": {
                        "authority": "USER_RULING",
                        "accepted_baseline_path": "",
                        "accepted_baseline_sha256": "",
                        "accepted_game_revision": "",
                        "user_quote": "Keep the existing main panel style.",
                    },
                    "evidence_refs": evidence_refs,
                }
            ],
            "viewport_profiles": [{"viewport_id": "desktop"}],
            "localization_profiles": [{"profile_id": "stress"}],
            "validation_scenarios": [
                {
                    "scenario_id": "desktop.structural",
                    "validation_kind": "STRUCTURAL_FIT",
                    "comparison_methods": ["GEOMETRY_ASSERTION"],
                },
                {
                    "scenario_id": "desktop.visual",
                    "validation_kind": "VISUAL_CONSISTENCY",
                    "comparison_methods": ["RESOURCE_IDENTITY"],
                },
            ],
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
                    "schema_version": "ui_production_adapter_result.v2",
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
            "rule_ids": ["visual.existing-grammar"],
            "exemplar_ids": ["main.panel"],
            "validation_scenario_ids": ["desktop.structural", "desktop.visual"],
            "style_blast_radius_scope": "ALL_UI_CONTROLS_IN_CHANGE_AND_REOPENED_STYLE_BATCH",
            "style_blast_radius": [
                {
                    "target_id": "main.action-button",
                    "target_path": "ui/main.tscn",
                    "control_ids": ["ActionButton"],
                    "change_kind": "NEW_CONTROL",
                    "disposition": "IMPLEMENT_STYLE_CHANGE",
                    "reference_exemplar_ids": ["main.panel"],
                    "visual_rule_ids": ["visual.existing-grammar"],
                    "structural_validation_scenario_ids": ["desktop.structural"],
                    "visual_validation_scenario_ids": ["desktop.visual"],
                }
            ],
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

    def test_v4_ui_plan_must_bind_visual_grammar_blast_radius_and_split_validation(self) -> None:
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
- UI rules: `visual.existing-grammar`
- UI exemplars: `main.panel`
- UI validation scenarios: `desktop.structural, desktop.visual`
## UI style blast radius
- Scope: `ALL_UI_CONTROLS_IN_CHANGE_AND_REOPENED_STYLE_BATCH`
- `main.action-button` — `ui/main.tscn`; controls: `ActionButton`; change: `NEW_CONTROL`; disposition: `IMPLEMENT_STYLE_CHANGE`; references: `main.panel`; visual rules: `visual.existing-grammar`; structural validation: `desktop.structural`; visual validation: `desktop.visual`
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
            "style_blast_radius_scope": "",
            "style_blast_radius": [],
        }
        self._write_manifest(payload)
        result = validate_production_plan(str(self.game_repo), self.manifest_relative)
        self.assertEqual(BLOCKED_BY_PLAN_GAP, result.status)
        self.assertTrue(any("touches_ui=false" in error for error in result.errors))

    def test_ui_plan_must_inventory_every_planned_ui_path(self) -> None:
        binding = self._ui_binding()
        payload = self._manifest()
        payload["plans"][0]["work_types"] = ["UI", "TEST"]
        payload["plans"][0]["planned_paths"] = [
            "ui/main.tscn",
            "scenes/staging_intelligence_panel.tscn",
        ]
        payload["plans"][0]["ui_impact"] = binding
        self._write_manifest(payload)
        result = validate_production_plan(str(self.game_repo), self.manifest_relative)
        self.assertEqual(BLOCKED_BY_PLAN_GAP, result.status)
        self.assertTrue(
            any("does not cover planned UI paths" in error for error in result.errors)
        )

    def test_ui_target_requires_visual_grammar_rule(self) -> None:
        binding = self._ui_binding()
        binding["style_blast_radius"][0]["visual_rule_ids"] = ["missing.visual"]
        payload = self._manifest()
        payload["plans"][0]["work_types"] = ["UI", "TEST"]
        payload["plans"][0]["planned_paths"] = ["ui/main.tscn"]
        payload["plans"][0]["ui_impact"] = binding
        self._write_manifest(payload)
        result = validate_production_plan(str(self.game_repo), self.manifest_relative)
        self.assertEqual(BLOCKED_BY_PLAN_GAP, result.status)
        self.assertTrue(any("unknown rule" in error for error in result.errors))

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

    def test_two_conformance_directions_must_be_exact_inverses(self) -> None:
        review_path = self.objective_dir / "GAMEPLAY_CONFORMANCE_SPEC_TO_CARD.json"
        review = json.loads(review_path.read_text())
        review["spec_material_inventory"][0]["claim_ids"] = ["cycle.read"]
        review_path.write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")

        verdict_path = self.objective_dir / "GAMEPLAY_DESIGN_VERDICT.json"
        verdict = json.loads(verdict_path.read_text())
        verdict["conformance_reviews"]["spec_to_card"]["sha256"] = hashlib.sha256(
            review_path.read_bytes()
        ).hexdigest()
        verdict_path.write_text(json.dumps(verdict, indent=2) + "\n", encoding="utf-8")

        payload = self._manifest()
        payload["design_verdict"]["sha256"] = hashlib.sha256(
            verdict_path.read_bytes()
        ).hexdigest()
        self._write_manifest(payload)
        result = validate_production_plan(str(self.game_repo), self.manifest_relative)
        self.assertEqual(BLOCKED_BY_PLAN_GAP, result.status)
        self.assertTrue(any("exact inverses" in error for error in result.errors))

    def test_full_spec_cannot_hide_uninventoried_material_prose(self) -> None:
        objective = self.objective_text.replace(
            "## Completion handoff",
            "The route also grants an unapproved permanent multiplier.\n\n"
            "## Completion handoff",
        )
        objective_path = self.objective_dir / "OBJECTIVE_GAMEPLAY.md"
        objective_path.write_text(objective, encoding="utf-8")
        objective_sha = hashlib.sha256(objective.encode("utf-8")).hexdigest()
        self._write_design_verdict(objective_sha256=objective_sha)
        payload = self._manifest()
        payload["objective_gameplay_sha256"] = objective_sha
        payload["design_verdict"]["sha256"] = self.verdict_sha256
        self._write_manifest(payload)
        result = validate_production_plan(str(self.game_repo), self.manifest_relative)
        self.assertEqual(BLOCKED_BY_PLAN_GAP, result.status)
        self.assertTrue(any("canonical bullet" in error for error in result.errors))

    def test_studio_routed_card_requires_validated_cycle_system(self) -> None:
        card_path = self.objective_dir / "GAMEPLAY_DECISION_CARD.json"
        card = json.loads(card_path.read_text())
        card["routing"] = "STUDIO_WHOLE_GAME"
        card["decision_payload_sha256"] = decision_payload_sha256(card)
        card["human_verdict"]["source_text"] = (
            f"USER_APPROVED {card['decision_payload_sha256']}"
        )
        card_path.write_text(json.dumps(card, indent=2) + "\n", encoding="utf-8")
        card_sha = hashlib.sha256(card_path.read_bytes()).hexdigest()

        review_hashes: dict[str, str] = {}
        for key, filename in (
            ("card_to_spec", "GAMEPLAY_CONFORMANCE_CARD_TO_SPEC.json"),
            ("spec_to_card", "GAMEPLAY_CONFORMANCE_SPEC_TO_CARD.json"),
        ):
            review_path = self.objective_dir / filename
            review = json.loads(review_path.read_text())
            review["decision_card"]["sha256"] = card_sha
            review_path.write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")
            review_hashes[key] = hashlib.sha256(review_path.read_bytes()).hexdigest()

        verdict_path = self.objective_dir / "GAMEPLAY_DESIGN_VERDICT.json"
        verdict = json.loads(verdict_path.read_text())
        verdict["decision_card"]["sha256"] = card_sha
        for key, digest in review_hashes.items():
            verdict["conformance_reviews"][key]["sha256"] = digest
        verdict_path.write_text(json.dumps(verdict, indent=2) + "\n", encoding="utf-8")

        payload = self._manifest()
        payload["design_verdict"]["sha256"] = hashlib.sha256(
            verdict_path.read_bytes()
        ).hexdigest()
        self._write_manifest(payload)
        result = validate_production_plan(str(self.game_repo), self.manifest_relative)
        self.assertEqual(BLOCKED_BY_PLAN_GAP, result.status)
        self.assertTrue(any("must bind a gameplay system" in error for error in result.errors))

    def test_human_verdict_must_bind_exact_decision_payload_token(self) -> None:
        card_path = self.objective_dir / "GAMEPLAY_DECISION_CARD.json"
        card = json.loads(card_path.read_text())
        card["human_verdict"]["source_text"] = "User said this was probably fine."
        self._rebind_changed_card(card)
        result = validate_production_plan(str(self.game_repo), self.manifest_relative)
        self.assertEqual(BLOCKED_BY_PLAN_GAP, result.status)
        self.assertTrue(any("exact verdict token" in error for error in result.errors))

    def test_design_conformance_hypothesis_cannot_be_marked_pass(self) -> None:
        review_path = self.objective_dir / "GAMEPLAY_CONFORMANCE_CARD_TO_SPEC.json"
        review = json.loads(review_path.read_text())
        hypothesis = next(
            item
            for item in review["claim_coverage"]
            if item["claim_id"] == "hypothesis.route-readable"
        )
        hypothesis["verdict"] = "PASS_DESIGN_CLAIM"
        review_path.write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")

        verdict_path = self.objective_dir / "GAMEPLAY_DESIGN_VERDICT.json"
        verdict = json.loads(verdict_path.read_text())
        verdict["conformance_reviews"]["card_to_spec"]["sha256"] = hashlib.sha256(
            review_path.read_bytes()
        ).hexdigest()
        verdict_path.write_text(json.dumps(verdict, indent=2) + "\n", encoding="utf-8")
        manifest = self._manifest()
        manifest["design_verdict"]["sha256"] = hashlib.sha256(
            verdict_path.read_bytes()
        ).hexdigest()
        self._write_manifest(manifest)

        result = validate_production_plan(str(self.game_repo), self.manifest_relative)
        self.assertEqual(BLOCKED_BY_PLAN_GAP, result.status)
        self.assertTrue(
            any("cannot be labelled PASS or ACCEPTED" in error for error in result.errors),
            result.errors,
        )

    def test_factory_revision_mismatch_fails_closed(self) -> None:
        payload = self._manifest()
        payload["factory_revision"] = "0" * 40
        self._write_manifest(payload)
        result = validate_production_plan(str(self.game_repo), self.manifest_relative)
        self.assertEqual(BLOCKED_BY_PLAN_GAP, result.status)
        self.assertTrue(any("Factory HEAD" in error for error in result.errors))

    def test_explicit_historical_check_reads_recorded_factory_revision(self) -> None:
        historical_revision = "1" * 40
        self._write_design_verdict(factory_revision=historical_revision)
        payload = self._manifest()
        payload["factory_revision"] = historical_revision
        verdict_path = self.objective_dir / "GAMEPLAY_DESIGN_VERDICT.json"
        payload["design_verdict"]["sha256"] = hashlib.sha256(
            verdict_path.read_bytes()
        ).hexdigest()
        self._write_manifest(payload)

        active = validate_production_plan(str(self.game_repo), self.manifest_relative)
        self.assertEqual(BLOCKED_BY_PLAN_GAP, active.status)
        self.assertTrue(any("Factory HEAD" in error for error in active.errors))

        historical = validate_production_plan(
            str(self.game_repo),
            self.manifest_relative,
            allow_legacy_historical=True,
        )
        self.assertEqual(
            HISTORICAL_PLAN_READABLE, historical.status, historical.errors
        )
        self.assertEqual([], historical.errors)
        self.assertTrue(any("does not authorize production" in item for item in historical.warnings))

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
        self.assertEqual(HISTORICAL_PLAN_READABLE, historical.status)
        self.assertFalse(historical.errors)


class StudioDecisionCardProjectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.system = {
            "system_promise": "Choose, earn a changed opportunity, and choose again.",
            "cycle_path": ["decide", "reward", "return"],
            "transitions": [
                {
                    "transition_id": "decide",
                    "player_action": "Choose a risk.",
                    "visible_consequence": "The risk is committed.",
                    "motivation_effect": "Anticipation begins.",
                },
                {
                    "transition_id": "reward",
                    "player_action": "Claim the result.",
                    "visible_consequence": "Opportunity tier changes.",
                    "motivation_effect": "A new risk opens.",
                },
                {
                    "transition_id": "return",
                    "player_action": "Choose again.",
                    "visible_consequence": "The new risk is visible.",
                    "motivation_effect": "The next decision differs.",
                },
            ],
            "coupled_systems": [
                {"component_id": "reward-return", "role": "Reward changes the next choice."}
            ],
            "forbidden_linearizations": ["A replay button alone is not a cycle."],
        }
        self.card = {
            "player_promise": {
                "claim_id": "promise.system",
                "text": self.system["system_promise"],
            },
            "core_cycle": [
                {
                    "claim_id": f"cycle.{item['transition_id']}",
                    "text": " -> ".join(
                        item[field]
                        for field in (
                            "player_action", "visible_consequence", "motivation_effect"
                        )
                    ),
                }
                for item in self.system["transitions"]
            ],
            "material_commitments": [
                {
                    "claim_id": "commitment.reward-return",
                    "text": "Reward changes the next choice.",
                },
                {"claim_id": "scope.one-card", "text": "Use one card in the first slice."},
            ],
            "red_lines": [
                {"claim_id": "redline.1", "text": "A replay button alone is not a cycle."}
            ],
        }

    def test_exact_system_projection_passes(self) -> None:
        errors: list[str] = []
        _validate_studio_card_projection(self.card, self.system, errors)
        self.assertEqual([], errors)

    def test_rewritten_core_cycle_fails(self) -> None:
        self.card["core_cycle"][1]["text"] = "Show a result and replay."
        errors: list[str] = []
        _validate_studio_card_projection(self.card, self.system, errors)
        self.assertTrue(any("exact ordered" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
