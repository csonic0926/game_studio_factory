import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from gameplay.ui import (
    ADAPTER_JSON_RELATIVE,
    ADAPTER_MD_RELATIVE,
    BLOCKED_BY_EXISTING_UI_STATE,
    BLOCKED_BY_UI_MODEL,
    INPUT_RELATIVE,
    PROBE_RELATIVE,
    RESULT_RELATIVE,
    UI_PRODUCTION_ADAPTER_ALREADY_READY,
    UI_PRODUCTION_ADAPTER_INPUT_REQUIRED,
    UI_PRODUCTION_ADAPTER_READY,
    UiWorkflowError,
    check_ui_adapter,
    compile_ui_adapter,
    probe_repository,
    refresh_ui_adapter,
    start_ui_workflow,
)


class UiWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.game_repo = Path(self.temporary_directory.name) / "game"
        self.game_repo.mkdir()
        subprocess.run(
            ["git", "init", "-b", "main", str(self.game_repo)],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        subprocess.run(
            ["git", "-C", str(self.game_repo), "config", "user.email", "test@example.com"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(self.game_repo), "config", "user.name", "Test"],
            check=True,
        )
        (self.game_repo / "project.godot").write_text(
            "[application]\nrun/main_scene=\"res://ui/main.tscn\"\n",
            encoding="utf-8",
        )
        (self.game_repo / "ui").mkdir()
        self.ui_source = self.game_repo / "ui/main.tscn"
        self.ui_source.write_text(
            "[node name=\"AppRoot\" type=\"Control\"]\n"
            "[node name=\"MainPanel\" type=\"MarginContainer\" parent=\".\"]\n"
            "[node name=\"ActionButton\" type=\"Button\" parent=\"MainPanel\"]\n",
            encoding="utf-8",
        )
        (self.game_repo / "ui/main.gd").write_text(
            "extends Control\nsignal action_requested\nfunc refresh_view(state):\n\tpass\n",
            encoding="utf-8",
        )
        subprocess.run(
            ["git", "-C", str(self.game_repo), "add", "."], check=True
        )
        subprocess.run(
            ["git", "-C", str(self.game_repo), "commit", "-m", "fixture"],
            check=True,
            stdout=subprocess.DEVNULL,
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def _probe_and_input(self) -> dict:
        result = probe_repository(str(self.game_repo))
        self.assertEqual(UI_PRODUCTION_ADAPTER_INPUT_REQUIRED, result.status)
        probe_path = self.game_repo / PROBE_RELATIVE
        probe_bytes = probe_path.read_bytes()
        probe = json.loads(probe_bytes)
        evidence = [
            {
                "role": "canonical_scene",
                "path": "ui/main.tscn",
                "contains": ["MainPanel", "MarginContainer"],
            },
            {
                "role": "state_refresh",
                "path": "ui/main.gd",
                "contains": ["refresh_view", "action_requested"],
            },
        ]
        categories = [
            "LAYOUT_STRUCTURE",
            "STATE_OWNERSHIP",
            "SCENE_INTEGRATION",
            "INPUT_AND_LAYERING",
            "RESPONSIVE_COMPOSITION",
            "LOCALIZATION_FIT",
            "VALIDATION",
        ]
        rules = []
        for index, category in enumerate(categories, start=1):
            rules.append(
                {
                    "rule_id": f"ui.rule.{index}",
                    "category": category,
                    "authority": "REPO_EVIDENCE",
                    "requirement": f"Preserve the evidenced {category.lower()} path.",
                    "rationale": "New UI must use the same working construction grammar.",
                    "evidence_refs": evidence,
                    "user_quote": "",
                }
            )
        payload = {
            "schema_version": "ui_production_adapter_input.v1",
            "project_id": "sample-game",
            "probe_path": PROBE_RELATIVE.as_posix(),
            "probe_sha256": hashlib.sha256(probe_bytes).hexdigest(),
            "repository_binding": probe["repository_binding"],
            "surfaces": [
                {
                    "surface_id": "main.table",
                    "responsibility": "Own the primary interactive table surface.",
                    "layout_structure": "AppRoot stretches; MainPanel owns container sizing.",
                    "state_ownership": "Game state is authoritative; the view stores no duplicate model.",
                    "refresh_and_signal_flow": "State changes call refresh_view; input emits action_requested.",
                    "scene_lifecycle": "AppRoot instantiates and tears down MainPanel once per run.",
                    "input_and_layering": "ActionButton owns input below modal overlays.",
                    "evidence_refs": evidence,
                }
            ],
            "canonical_exemplars": [
                {
                    "exemplar_id": "main.panel",
                    "why_canonical": "It is the existing working gameplay surface.",
                    "rules_illustrated": [rule["rule_id"] for rule in rules],
                    "evidence_refs": evidence,
                }
            ],
            "rules": rules,
            "viewport_profiles": [
                {
                    "viewport_id": "desktop.16x9",
                    "width": 1920,
                    "height": 1080,
                    "input_modes": ["mouse", "keyboard"],
                    "composition_requirements": ["MainPanel and ActionButton remain visible."],
                }
            ],
            "localization_profiles": [
                {
                    "profile_id": "stress.all",
                    "locale_ids": ["en", "zh_Hant"],
                    "fit_requirements": ["Labels wrap without clipping or overlap."],
                }
            ],
            "validation_scenarios": [
                {
                    "scenario_id": "main.populated.desktop",
                    "viewport_id": "desktop.16x9",
                    "localization_profile_id": "stress.all",
                    "ui_states": ["empty", "populated", "disabled", "modal"],
                    "interaction_path": ["Open the surface", "Press ActionButton"],
                    "assertions": ["State refreshes once and all controls remain visible."],
                    "capture_requirements": ["Capture every state in both locales."],
                }
            ],
            "anti_patterns": [
                {
                    "anti_pattern_id": "duplicate.view.state",
                    "description": "Do not create a second gameplay state ledger in the view.",
                    "evidence_refs": evidence,
                }
            ],
            "unresolved_material_gaps": [],
            "ai_assumptions": [],
        }
        input_path = self.game_repo / INPUT_RELATIVE
        input_path.parent.mkdir(parents=True, exist_ok=True)
        input_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return payload

    def test_probe_is_bounded_and_non_semantic(self) -> None:
        result = probe_repository(str(self.game_repo), max_candidates=1)
        self.assertEqual(UI_PRODUCTION_ADAPTER_INPUT_REQUIRED, result.status)
        payload = json.loads((self.game_repo / PROBE_RELATIVE).read_text())
        self.assertEqual("NONE", payload["semantic_authority"])
        self.assertLessEqual(len(payload["candidate_files"]), 1)
        self.assertEqual({"path", "score"}, set(payload["candidate_files"][0]))

    def test_ui_contract_schemas_are_valid_json(self) -> None:
        schema_root = Path(__file__).resolve().parents[1] / "schemas"
        for name in (
            "ui_production_repo_probe.schema.json",
            "ui_production_adapter_input.schema.json",
            "ui_production_adapter.schema.json",
            "ui_production_adapter_result.schema.json",
        ):
            payload = json.loads((schema_root / name).read_text(encoding="utf-8"))
            self.assertEqual("object", payload["type"])

    def test_valid_compile_check_and_start_are_idempotent(self) -> None:
        self._probe_and_input()
        compiled = compile_ui_adapter(str(self.game_repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(UI_PRODUCTION_ADAPTER_READY, compiled.status)
        self.assertEqual(
            {p.as_posix() for p in (ADAPTER_JSON_RELATIVE, ADAPTER_MD_RELATIVE, RESULT_RELATIVE)},
            set(compiled.created_paths),
        )
        checked = check_ui_adapter(str(self.game_repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(UI_PRODUCTION_ADAPTER_READY, checked.status)
        started = start_ui_workflow(str(self.game_repo))
        self.assertEqual(UI_PRODUCTION_ADAPTER_ALREADY_READY, started.status)

    def test_unrelated_repo_change_does_not_burn_adapter_reconstruction(self) -> None:
        self._probe_and_input()
        self.assertEqual(
            UI_PRODUCTION_ADAPTER_READY,
            compile_ui_adapter(str(self.game_repo), INPUT_RELATIVE.as_posix()).status,
        )
        (self.game_repo / "gameplay.gd").write_text(
            "func unrelated_gameplay_change():\n\tpass\n", encoding="utf-8"
        )
        checked = check_ui_adapter(str(self.game_repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(UI_PRODUCTION_ADAPTER_READY, checked.status)

    def test_changed_cited_ui_source_invalidates_reuse(self) -> None:
        self._probe_and_input()
        self.assertEqual(
            UI_PRODUCTION_ADAPTER_READY,
            compile_ui_adapter(str(self.game_repo), INPUT_RELATIVE.as_posix()).status,
        )
        self.ui_source.write_text(
            self.ui_source.read_text(encoding="utf-8") + "# still has tokens\n",
            encoding="utf-8",
        )
        checked = check_ui_adapter(str(self.game_repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(BLOCKED_BY_EXISTING_UI_STATE, checked.status)

    def test_explicit_refresh_replaces_only_an_intact_checked_generation(self) -> None:
        self._probe_and_input()
        self.assertEqual(
            UI_PRODUCTION_ADAPTER_READY,
            compile_ui_adapter(str(self.game_repo), INPUT_RELATIVE.as_posix()).status,
        )
        self.ui_source.write_text(
            self.ui_source.read_text(encoding="utf-8") + "# revised grammar\n",
            encoding="utf-8",
        )
        self._probe_and_input()
        blocked_create = compile_ui_adapter(
            str(self.game_repo), INPUT_RELATIVE.as_posix()
        )
        self.assertEqual(BLOCKED_BY_EXISTING_UI_STATE, blocked_create.status)
        refreshed = refresh_ui_adapter(
            str(self.game_repo), INPUT_RELATIVE.as_posix()
        )
        self.assertEqual(UI_PRODUCTION_ADAPTER_READY, refreshed.status)
        self.assertEqual(
            UI_PRODUCTION_ADAPTER_READY,
            check_ui_adapter(str(self.game_repo), INPUT_RELATIVE.as_posix()).status,
        )

    def test_refresh_rejects_tampered_previous_generation(self) -> None:
        self._probe_and_input()
        compile_ui_adapter(str(self.game_repo), INPUT_RELATIVE.as_posix())
        (self.game_repo / ADAPTER_MD_RELATIVE).write_text("tampered\n", encoding="utf-8")
        result = refresh_ui_adapter(str(self.game_repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(BLOCKED_BY_EXISTING_UI_STATE, result.status)
        self.assertTrue(any("modified outside" in error for error in result.errors))

    def test_repo_change_after_probe_fails_closed(self) -> None:
        self._probe_and_input()
        self.ui_source.write_text(self.ui_source.read_text() + "# changed\n")
        result = compile_ui_adapter(str(self.game_repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(BLOCKED_BY_UI_MODEL, result.status)
        self.assertTrue(any("changed after" in error for error in result.errors))

    def test_missing_rule_category_fails_closed(self) -> None:
        payload = self._probe_and_input()
        payload["rules"] = payload["rules"][:-1]
        (self.game_repo / INPUT_RELATIVE).write_text(json.dumps(payload) + "\n")
        result = compile_ui_adapter(str(self.game_repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(BLOCKED_BY_UI_MODEL, result.status)
        self.assertTrue(any("lack required UI categories" in e for e in result.errors))

    def test_unproven_repo_rule_fails_closed(self) -> None:
        payload = self._probe_and_input()
        payload["rules"][0]["evidence_refs"] = []
        (self.game_repo / INPUT_RELATIVE).write_text(json.dumps(payload) + "\n")
        result = compile_ui_adapter(str(self.game_repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(BLOCKED_BY_UI_MODEL, result.status)
        self.assertTrue(any("REPO_EVIDENCE requires" in e for e in result.errors))

    def test_user_ruling_requires_quote(self) -> None:
        payload = self._probe_and_input()
        payload["rules"][0]["authority"] = "USER_RULING"
        payload["rules"][0]["evidence_refs"] = []
        (self.game_repo / INPUT_RELATIVE).write_text(json.dumps(payload) + "\n")
        result = compile_ui_adapter(str(self.game_repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(BLOCKED_BY_UI_MODEL, result.status)
        self.assertTrue(any("user_quote is required" in e for e in result.errors))

    def test_validation_must_cover_each_viewport_and_locale_profile(self) -> None:
        payload = self._probe_and_input()
        payload["viewport_profiles"].append(
            {
                "viewport_id": "mobile.portrait",
                "width": 780,
                "height": 1688,
                "input_modes": ["touch"],
                "composition_requirements": ["No clipped controls."],
            }
        )
        (self.game_repo / INPUT_RELATIVE).write_text(json.dumps(payload) + "\n")
        result = compile_ui_adapter(str(self.game_repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(BLOCKED_BY_UI_MODEL, result.status)
        self.assertTrue(any("mobile.portrait" in e for e in result.errors))

    def test_differing_existing_artifact_blocks_all_canonical_writes(self) -> None:
        self._probe_and_input()
        conflict = self.game_repo / ADAPTER_JSON_RELATIVE
        conflict.parent.mkdir(parents=True, exist_ok=True)
        conflict.write_text("{}\n")
        result = compile_ui_adapter(str(self.game_repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(BLOCKED_BY_EXISTING_UI_STATE, result.status)
        self.assertFalse((self.game_repo / ADAPTER_MD_RELATIVE).exists())
        self.assertFalse((self.game_repo / RESULT_RELATIVE).exists())

    def test_illegal_output_path_creates_nothing(self) -> None:
        outside = Path(self.temporary_directory.name) / "outside/probe.json"
        with self.assertRaises(UiWorkflowError):
            probe_repository(str(self.game_repo), str(outside))
        self.assertFalse(outside.parent.exists())


if __name__ == "__main__":
    unittest.main()
