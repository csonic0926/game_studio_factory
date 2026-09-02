import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from gameplay.new_project_bootstrap import (
    BLOCKED_BY_BOOTSTRAP_MATERIAL,
    BLOCKED_BY_EXISTING_FACTORY_STATE,
    GAMEPLAY_FACTORY_READY,
    INPUT_RELATIVE,
    MODEL_RELATIVE,
    NEW_PROJECT_BOOTSTRAP_INPUT_REQUIRED,
    PROBE_RELATIVE,
    PROFILE_RELATIVE,
    _historical_pending_card_transition_errors,
    check_new_project,
    compile_new_project,
    probe_new_project,
)
from gameplay.design_gate import render_decision_card
from gameplay.prepare import (
    READY_FOR_NEW_GAMEPLAY_DESIGN,
    _compile_unit_payload,
    validate_materials,
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


class NewProjectBootstrapTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.repo = Path(self.temporary_directory.name) / "new_game"
        self.repo.mkdir()
        subprocess.run(
            ["git", "-C", str(self.repo), "init", "-b", "main"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.product = write_json(
            self.repo / "design/product/PRODUCT_AUTHORITY_REGISTER.json",
            {"schema_version": "test", "status": "ACTIVE"},
        )
        self.thesis = self.repo / "design/product/PRODUCT_THESIS.md"
        self.thesis.write_text("# Product\n\nOne bounded campaign cycle.\n", encoding="utf-8")
        self.system = write_json(
            self.repo / "design/studio/gameplay_system/cycle/STUDIO_GAMEPLAY_SYSTEM.json",
            {
                "system_id": "global-cycle",
                "cycle_id": "cycle-v1",
                "system_promise": "One committed operation changes the next command decision.",
                "core_player_verbs": ["prepare", "command", "reinvest"],
                "feedback_state_ids": ["forces", "supply", "intel"],
            },
        )
        self.manifest = write_json(
            self.system.with_name("STUDIO_GAMEPLAY_SYSTEM_MANIFEST.json"),
            {
                "system_id": "global-cycle",
                "gameplay_system": ref(self.repo, self.system),
            },
        )
        self.card = write_json(
            self.repo / "design/gameplay/objective_gameplay/first-cycle/GAMEPLAY_DECISION_CARD.json",
            {
                "project_id": "sample-new-game",
                "objective_id": "first-cycle",
                "factory_revision": "0" * 40,
                "product_authority": ref(self.repo, self.thesis),
                "studio_gameplay_system": ref(self.repo, self.manifest),
                "player_promise": {
                    "claim_id": "promise.system",
                    "text": "One committed operation changes the next command decision.",
                },
                "core_cycle": [
                    {"claim_id": "cycle.prepare", "text": "Prepare one operation."},
                    {"claim_id": "cycle.command", "text": "Command one battle."},
                    {"claim_id": "cycle.persist", "text": "Persist its aftermath."},
                ],
                "material_commitments": [
                    {"claim_id": "scope.first", "text": "First baseline: one complete two-lap operation."}
                ],
                "red_lines": [
                    {"claim_id": "redline.no-expansion", "text": "Do not expand before the first cycle is accepted."}
                ],
                "validation_hypotheses": [],
                "decision_payload_sha256": "a" * 64,
                "human_verdict": {
                    "status": "USER_APPROVED",
                    "source_text": "USER_APPROVED " + "a" * 64,
                    "recorded_at": "2026-09-01T00:00:00Z",
                },
            },
        )
        self.review = write_json(self.card.with_name("GAMEPLAY_DECISION_CARD_FACTORY_REVIEW.json"), {})
        self.register = write_json(
            self.repo / "design/studio/STUDIO_DECISION_CARD_REGISTER.json",
            {
                "entries": [
                    {
                        "state": "USER_APPROVED",
                        "decision_card": ref(self.repo, self.card),
                    }
                ]
            },
        )
        (self.repo / ".gitignore").write_text(".godot/\n", encoding="utf-8")

        self.active_product = {
            "status": "ACTIVE",
            "active_authority": {"product_thesis": ref(self.repo, self.thesis)},
        }
        self.approved_card = json.loads(self.card.read_text(encoding="utf-8"))
        self.product_patch = patch(
            "gameplay.new_project_bootstrap.require_active_product_authority",
            return_value=(self.active_product, []),
        )
        self.card_patch = patch(
            "gameplay.new_project_bootstrap._validate_approved_card",
            return_value=(self.approved_card, []),
        )
        self.product_patch.start()
        self.card_patch.start()

    def tearDown(self) -> None:
        self.card_patch.stop()
        self.product_patch.stop()
        self.temporary_directory.cleanup()

    def _probe_and_write_input(self) -> Path:
        result = probe_new_project(str(self.repo))
        self.assertEqual(NEW_PROJECT_BOOTSTRAP_INPUT_REQUIRED, result.status, result.errors)
        probe = self.repo / PROBE_RELATIVE
        payload = {
            "schema_version": "gameplay_new_project_bootstrap_input.v1",
            "project_id": "sample-new-game",
            "init_date": "2026-09-01",
            "author_context_id": "bootstrap-author",
            "probe": ref(self.repo, probe),
            "technical_profile": {
                "primary_locale": "zh_Hant",
                "target_runtime": "Godot 4 desktop",
                "planned_runtime_roots": ["project.godot", "src", "scenes", "data"],
                "validation_commands": [],
                "integration_constraints": ["Keep campaign and battle state separately owned."],
            },
            "initial_frontier": {
                "objective_dir": "first-cycle",
                "decision": "COMPLETE_CURRENT_UNIT",
                "current_state": "No runtime exists; the approved first cycle awaits design and production.",
                "objective_locale": {
                    "path": "locales/objectives.csv",
                    "key_column": "keys",
                    "locale_column": "zh_Hant",
                    "key": "objective.first_cycle",
                    "text": "First baseline: one complete two-lap operation.",
                    "source_claim_id": "scope.first",
                },
                "completion_condition": "Complete and persist the approved operation loop.",
                "completion_source_claim_ids": ["cycle.prepare", "cycle.command", "cycle.persist"],
                "successor_handoff": {
                    "status": "MISSING",
                    "description": "The second operation is design-authorized but not runtime-wired.",
                    "source_claim_ids": ["redline.no-expansion"],
                },
                "recent_patterns": [],
                "design_constraints": ["Do not claim runtime evidence from this bootstrap."],
            },
            "user_rulings": [],
            "unresolved_material_gaps": [],
            "ai_assumptions": [],
        }
        return write_json(self.repo / INPUT_RELATIVE, payload)

    def test_compile_check_and_prepare_zero_action_frontier(self) -> None:
        self._probe_and_write_input()
        compiled = compile_new_project(str(self.repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(GAMEPLAY_FACTORY_READY, compiled.status, compiled.errors)
        self.assertTrue((self.repo / MODEL_RELATIVE).is_file())
        model = json.loads((self.repo / MODEL_RELATIVE).read_text(encoding="utf-8"))
        self.assertEqual([], model["player_actions"])
        self.assertIn("design-time only", " ".join(compiled.warnings))

        checked = check_new_project(str(self.repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(GAMEPLAY_FACTORY_READY, checked.status, checked.errors)

        unit_path = self.repo / "design/gameplay/objective_gameplay/first-cycle/NEXT_GAMEPLAY_UNIT_INPUT.json"
        unit = json.loads(unit_path.read_text(encoding="utf-8"))
        prepared_payload = _compile_unit_payload(self.repo, unit)
        prepared = validate_materials(prepared_payload, self.repo)
        self.assertEqual(READY_FOR_NEW_GAMEPLAY_DESIGN, prepared.status, prepared.errors)
        self.assertTrue(any("design authority only" in item for item in prepared.warnings))

        repeated = compile_new_project(str(self.repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(GAMEPLAY_FACTORY_READY, repeated.status, repeated.errors)
        self.assertFalse(repeated.created_paths)

    def test_source_change_after_probe_fails_before_outputs(self) -> None:
        self._probe_and_write_input()
        self.thesis.write_text("# Product\n\nChanged after probe.\n", encoding="utf-8")
        result = compile_new_project(str(self.repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(BLOCKED_BY_BOOTSTRAP_MATERIAL, result.status)
        self.assertFalse((self.repo / PROFILE_RELATIVE).exists())
        self.assertTrue(any("source bytes changed" in item for item in result.errors))

    def test_forged_probe_projection_is_not_trusted_even_with_updated_input_hash(self) -> None:
        input_path = self._probe_and_write_input()
        probe_path = self.repo / PROBE_RELATIVE
        probe = json.loads(probe_path.read_text(encoding="utf-8"))
        probe["system_projection"]["system_promise"] = "Forged local promise."
        write_json(probe_path, probe)
        payload = json.loads(input_path.read_text(encoding="utf-8"))
        payload["probe"] = ref(self.repo, probe_path)
        write_json(input_path, payload)
        result = compile_new_project(str(self.repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(BLOCKED_BY_BOOTSTRAP_MATERIAL, result.status)
        self.assertFalse((self.repo / PROFILE_RELATIVE).exists())
        self.assertTrue(any("exact mechanical projection" in item for item in result.errors))

    def test_conflicting_factory_state_blocks_all_new_writes(self) -> None:
        self._probe_and_write_input()
        (self.repo / PROFILE_RELATIVE).parent.mkdir(parents=True, exist_ok=True)
        (self.repo / PROFILE_RELATIVE).write_text("intentional existing state\n", encoding="utf-8")
        result = compile_new_project(str(self.repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(BLOCKED_BY_EXISTING_FACTORY_STATE, result.status)
        self.assertFalse((self.repo / MODEL_RELATIVE).exists())
        self.assertFalse((self.repo / "locales/objectives.csv").exists())

    def test_approved_card_accepts_only_exact_historical_pending_ref_delta(self) -> None:
        rendered = render_decision_card(self.approved_card)
        card_relative = self.card.relative_to(self.repo).as_posix()
        historical_sha = "b" * 64
        alignment = write_json(
            self.repo / "design/studio/interaction_alignment/card/STUDIO_SEMANTIC_ALIGNMENT_INPUT.json",
            {
                "active_authorities": [
                    {"artifact": {"path": card_relative, "sha256": historical_sha}}
                ],
                "authority_changes": [
                    {"artifact": {"path": card_relative, "sha256": historical_sha}}
                ],
                "pending_decisions": [
                    {"decision_card": {"path": card_relative, "sha256": historical_sha}}
                ],
                "candidate_output": {
                    "kind": "DECISION_SURFACE",
                    "text": rendered,
                    "sha256": hashlib.sha256(rendered.encode("utf-8")).hexdigest(),
                },
            },
        )
        register = json.loads(self.register.read_text(encoding="utf-8"))
        register["entries"][0].update(
            {
                "decision_payload_sha256": self.approved_card["decision_payload_sha256"],
                "alignment_input": ref(self.repo, alignment),
            }
        )
        write_json(self.register, register)
        historical_errors = [
            f"active_authorities[0].artifact hash does not match {card_relative}",
            f"authority_changes[0].artifact hash does not match {card_relative}",
            f"pending_decisions[0].decision_card hash does not match {card_relative}",
            "registered Studio decision surface lacks a valid "
            "HUMAN_RULING_GENUINELY_REQUIRED alignment verdict",
        ]
        self.assertEqual(
            [],
            _historical_pending_card_transition_errors(
                self.repo, self.card, self.approved_card, historical_errors
            ),
        )
        unexpected = [*historical_errors, "unrelated authority failure"]
        self.assertEqual(
            unexpected,
            _historical_pending_card_transition_errors(
                self.repo, self.card, self.approved_card, unexpected
            ),
        )


if __name__ == "__main__":
    unittest.main()
