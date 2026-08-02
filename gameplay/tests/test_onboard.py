import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from gameplay.onboard import (
    ALREADY_CASE3,
    BLOCKED_BY_EXISTING_FACTORY_STATE,
    BLOCKED_BY_ONBOARDING_MATERIAL,
    CASE2_PROBE_READY,
    CASE3_READY,
    INPUT_RELATIVE,
    MODEL_RELATIVE,
    PROFILE_RELATIVE,
    PROBE_RELATIVE,
    RESULT_RELATIVE,
    OnboardingError,
    check_onboarding,
    compile_onboarding,
    probe_repository,
)


class Case2OnboardingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.game_repo = Path(self.temporary_directory.name) / "foreign_game"
        self.game_repo.mkdir()
        self._git("init", "-b", "main")
        self._git("config", "user.email", "test@example.com")
        self._git("config", "user.name", "Test User")
        (self.game_repo / "project.godot").write_text(
            '[application]\nconfig/name="Foreign Game"\n', encoding="utf-8"
        )
        (self.game_repo / "locales.csv").write_text(
            "keys,en,zh_Hant\nround.next,Prepare for the next round.,準備下一回合。\n",
            encoding="utf-8",
        )
        (self.game_repo / "game.gd").write_text(
            "const PRIMARY_DRIVER = 'round_sequence'\n"
            "const CURRENT_STATE = 'shop_phase'\n"
            "const OBJECTIVE_KEY = 'round.next'\n"
            "func select_objective(): return OBJECTIVE_KEY\n"
            "func complete_objective(): return battle_finished\n"
            "func buy_card(): return 'roster_power'\n"
            "func grant_reward(): return coins\n",
            encoding="utf-8",
        )
        tests_dir = self.game_repo / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_game.gd").write_text(
            "func test_round_progression(): pass\n", encoding="utf-8"
        )
        self._git("add", ".")
        self._git("commit", "-m", "initial foreign game")
        self.revision = self._git("rev-parse", "HEAD").strip()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def _git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(self.game_repo), *args],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        return result.stdout

    def _payload(self) -> dict:
        runtime_ref = {
            "role": "runtime_surface",
            "path": "game.gd",
            "contains": ["PRIMARY_DRIVER"],
        }
        return {
            "schema_version": "case2_onboarding_input.v1",
            "project_id": "foreign_game",
            "onboarding_date": "2026-08-03",
            "repository": {
                "expected_revision": self.revision,
                "declared_dirty_paths": [],
            },
            "gameplay_model": {
                "schema_version": "gameplay_design_model.v1",
                "project_id": "foreign_game",
                "primary_progression_driver": {
                    "system_id": "round_sequence",
                    "system_kind": "round_sequence",
                    "progression_unit": "round",
                    "description": "Shop preparation advances into one battle round.",
                    "evidence_refs": [
                        {
                            "role": "progression_authority",
                            "path": "game.gd",
                            "contains": ["PRIMARY_DRIVER = 'round_sequence'"],
                        }
                    ],
                },
                "player_actions": [
                    {
                        "action_id": "buy_card",
                        "description": "Buy one offered card for the roster.",
                        "availability": "During the shop phase with enough coins.",
                        "rewards": [
                            {
                                "reward_id": "roster_power",
                                "kind": "power",
                                "description": "The roster gains a usable unit or upgrade.",
                            }
                        ],
                        "evidence_refs": [
                            {
                                "role": "runtime_action",
                                "path": "game.gd",
                                "contains": ["func buy_card"],
                            }
                        ],
                    }
                ],
                "recent_patterns": [],
                "design_constraints": ["The existing round sequence remains linear."],
            },
            "initial_frontier": {
                "objective_dir": "round.next",
                "frontier": {
                    "decision": "COMPLETE_CURRENT_UNIT",
                    "current_state": "The shop phase is active before the next battle.",
                    "objective_id": "round.next",
                    "objective_locale": {
                        "path": "locales.csv",
                        "key_column": "keys",
                        "locale_column": "zh_Hant",
                        "key": "round.next",
                        "expected_text": "準備下一回合。",
                    },
                    "completion_condition": (
                        "The battle finishes and complete_objective returns true."
                    ),
                    "successor_handoff": {
                        "status": "WIRED",
                        "description": "Battle completion returns to the next shop phase.",
                    },
                    "evidence_refs": [
                        {
                            "role": "runtime_selection",
                            "path": "game.gd",
                            "contains": ["func select_objective"],
                        },
                        {
                            "role": "runtime_completion",
                            "path": "game.gd",
                            "contains": ["func complete_objective"],
                        },
                    ],
                },
                "applicable_action_ids": ["buy_card"],
                "recent_patterns": [],
                "design_constraints": [],
            },
            "project_profile": {
                "primary_locale": "zh_Hant",
                "target_runtime": "Godot desktop auto-battler",
                "authoritative_source_refs": [
                    {
                        "role": "current_state_source",
                        "path": "game.gd",
                        "contains": ["CURRENT_STATE = 'shop_phase'"],
                    }
                ],
                "player_frames": ["Returning player entering a normal shop phase."],
                "core_fantasy_and_desires": [
                    "Build a stronger roster before automatic combat resolves."
                ],
                "sovereignty_and_red_lines": [
                    "Roster preparation remains player-controlled."
                ],
                "systems_and_spaces": ["Shop preparation and battle resolution."],
                "presentation_and_control": [
                    "Shop input belongs to the player; battle resolution is automatic."
                ],
                "grammar_and_handoff": [
                    "Shop completion hands control to battle, then back to shop."
                ],
                "review_and_evidence_owners": [
                    "The user owns gameplay rulings; tests own mechanical regression."
                ],
            },
            "production_adapter": {
                "supported_revision": self.revision,
                "runtime_surfaces": [
                    {
                        "surface": "round progression and shop actions",
                        "paths": ["game.gd"],
                        "owner": "game.gd",
                        "evidence_refs": [runtime_ref],
                    }
                ],
                "gameplay_mappings": [
                    {
                        "concern": "objective_selection",
                        "description": "select_objective returns the live locale key.",
                        "evidence_refs": [
                            {
                                "role": "mapping",
                                "path": "game.gd",
                                "contains": ["func select_objective"],
                            }
                        ],
                    },
                    {
                        "concern": "objective_completion",
                        "description": "complete_objective reads battle completion.",
                        "evidence_refs": [
                            {
                                "role": "mapping",
                                "path": "game.gd",
                                "contains": ["func complete_objective"],
                            }
                        ],
                    },
                    {
                        "concern": "player_actions",
                        "description": "buy_card mutates the roster during shop control.",
                        "evidence_refs": [
                            {
                                "role": "mapping",
                                "path": "game.gd",
                                "contains": ["func buy_card"],
                            }
                        ],
                    },
                    {
                        "concern": "rewards_and_state",
                        "description": "grant_reward and buy_card own coins and roster power.",
                        "evidence_refs": [
                            {
                                "role": "mapping",
                                "path": "game.gd",
                                "contains": ["func grant_reward"],
                            }
                        ],
                    },
                ],
                "validation_commands": ["godot --headless --path . --quit"],
                "integration_constraints": [
                    "Keep progression, action, and reward mutations in game.gd."
                ],
                "unsupported_capabilities": [],
            },
            "observation_adapter": {
                "status": "NOT_AVAILABLE",
                "supported_revision": self.revision,
                "mapping_path": "NOT_AVAILABLE",
                "evidence_sources": [],
                "launch_and_capture": [],
                "provenance_and_ordering": [],
                "validation_commands": [],
                "limits_and_gaps": [
                    "Runtime acceptance is blocked until instrumentation is added."
                ],
            },
            "user_rulings": [],
            "unresolved_material_gaps": [],
            "ai_assumptions": [],
        }

    def _write_input(self, payload: dict | None = None) -> Path:
        if not (self.game_repo / PROBE_RELATIVE).exists():
            probe_repository(str(self.game_repo), PROBE_RELATIVE.as_posix())
        probe = json.loads((self.game_repo / PROBE_RELATIVE).read_text())
        selected_payload = payload or self._payload()
        selected_payload["repository"]["declared_dirty_paths"] = probe["repository"][
            "dirty_paths"
        ]
        selected_payload["repository"]["working_tree_sha256"] = probe["repository"][
            "working_tree_sha256"
        ]
        input_path = self.game_repo / INPUT_RELATIVE
        input_path.parent.mkdir(parents=True, exist_ok=True)
        input_path.write_text(
            json.dumps(selected_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return input_path

    def test_probe_writes_bounded_non_semantic_inventory(self) -> None:
        result = probe_repository(
            str(self.game_repo), PROBE_RELATIVE.as_posix(), max_candidates=3
        )
        self.assertEqual(CASE2_PROBE_READY, result.status)
        probe = json.loads((self.game_repo / PROBE_RELATIVE).read_text())
        self.assertEqual(self.revision, probe["repository"]["revision"])
        self.assertRegex(probe["repository"]["working_tree_sha256"], r"^[0-9a-f]{64}$")
        self.assertLessEqual(len(probe["candidate_files"]), 3)
        self.assertIn("locales.csv", probe["locale_candidates"])
        self.assertIn("do not establish", probe["interpretation_warning"])

    def test_probe_rejects_illegal_output_before_creating_directory(self) -> None:
        outside = Path(self.temporary_directory.name) / "outside" / "probe.json"
        with self.assertRaises(OnboardingError):
            probe_repository(str(self.game_repo), str(outside))
        self.assertFalse(outside.parent.exists())

    def test_valid_compile_creates_case3_ready_handoff_and_check_passes(self) -> None:
        self._write_input()
        result = compile_onboarding(str(self.game_repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(CASE3_READY, result.status)
        self.assertTrue((self.game_repo / PROFILE_RELATIVE).is_file())
        self.assertTrue((self.game_repo / MODEL_RELATIVE).is_file())
        self.assertTrue((self.game_repo / RESULT_RELATIVE).is_file())
        unit_path = (
            self.game_repo
            / "design/gameplay/objective_gameplay/round.next/"
            "NEXT_GAMEPLAY_UNIT_INPUT.json"
        )
        self.assertTrue(unit_path.is_file())
        self.assertNotIn("TBD", (self.game_repo / PROFILE_RELATIVE).read_text())
        self.assertNotIn(
            str(self.game_repo), (self.game_repo / PROFILE_RELATIVE).read_text()
        )
        check = check_onboarding(str(self.game_repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(CASE3_READY, check.status)
        self.assertEqual(8, len(check.verified_paths))

    def test_not_available_observation_is_explicit_warning_not_fake_evidence(self) -> None:
        self._write_input()
        result = compile_onboarding(str(self.game_repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(CASE3_READY, result.status)
        self.assertTrue(any("acceptance remains blocked" in warning for warning in result.warnings))
        observation = (
            self.game_repo / "design/gameplay/adapter/OBSERVATION_ADAPTER.md"
        ).read_text()
        self.assertIn("Observation status: `NOT_AVAILABLE`", observation)

    def test_case3_successor_warning_survives_onboarding_handoff(self) -> None:
        payload = self._payload()
        payload["initial_frontier"]["frontier"]["successor_handoff"] = {
            "status": "MISSING",
            "description": "The next shop handoff is not wired yet.",
        }
        self._write_input(payload)
        result = compile_onboarding(str(self.game_repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(CASE3_READY, result.status)
        self.assertTrue(any("successor" in warning for warning in result.warnings))

    def test_missing_runtime_completion_blocks_without_partial_outputs(self) -> None:
        payload = self._payload()
        payload["initial_frontier"]["frontier"]["evidence_refs"] = [
            payload["initial_frontier"]["frontier"]["evidence_refs"][0]
        ]
        self._write_input(payload)
        result = compile_onboarding(str(self.game_repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(BLOCKED_BY_ONBOARDING_MATERIAL, result.status)
        self.assertTrue(any("runtime_completion" in error for error in result.errors))
        self.assertFalse((self.game_repo / MODEL_RELATIVE).exists())

    def test_malformed_non_applicable_action_cannot_enter_stable_model(self) -> None:
        payload = self._payload()
        payload["gameplay_model"]["player_actions"].append(
            {
                "action_id": "inspect_card",
                "description": "Inspect a card not used by this frontier.",
                "availability": "During the shop phase.",
                "rewards": [],
                "evidence_refs": [
                    {
                        "role": "runtime_action",
                        "path": "game.gd",
                        "contains": ["func buy_card"],
                    }
                ],
            }
        )
        self._write_input(payload)
        result = compile_onboarding(str(self.game_repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(BLOCKED_BY_ONBOARDING_MATERIAL, result.status)
        self.assertTrue(
            any("player_actions[1].rewards" in error for error in result.errors)
        )
        self.assertFalse((self.game_repo / MODEL_RELATIVE).exists())

    def test_missing_probe_blocks_without_factory_state(self) -> None:
        self._write_input()
        (self.game_repo / PROBE_RELATIVE).unlink()
        result = compile_onboarding(str(self.game_repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(BLOCKED_BY_ONBOARDING_MATERIAL, result.status)
        self.assertTrue(any("missing mechanical repository probe" in error for error in result.errors))
        self.assertFalse((self.game_repo / MODEL_RELATIVE).exists())

    def test_unresolved_material_gap_blocks_handoff(self) -> None:
        payload = self._payload()
        payload["unresolved_material_gaps"] = ["Cannot identify the live round owner."]
        self._write_input(payload)
        result = compile_onboarding(str(self.game_repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(BLOCKED_BY_ONBOARDING_MATERIAL, result.status)
        self.assertTrue(any("unresolved_material_gaps" in error for error in result.errors))

    def test_ai_assumption_cannot_become_case3_authority(self) -> None:
        payload = self._payload()
        payload["ai_assumptions"] = ["Players probably want faster rounds."]
        self._write_input(payload)
        result = compile_onboarding(str(self.game_repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(BLOCKED_BY_ONBOARDING_MATERIAL, result.status)
        self.assertTrue(any("ai_assumptions" in error for error in result.errors))

    def test_revision_change_after_study_blocks_handoff(self) -> None:
        self._write_input()
        (self.game_repo / "new.txt").write_text("new committed state\n")
        self._git("add", "new.txt")
        self._git("commit", "-m", "change source revision")
        result = compile_onboarding(str(self.game_repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(BLOCKED_BY_ONBOARDING_MATERIAL, result.status)
        self.assertTrue(any("revision changed" in error for error in result.errors))

    def test_dirty_paths_change_after_study_blocks_handoff(self) -> None:
        self._write_input()
        with (self.game_repo / "game.gd").open("a", encoding="utf-8") as stream:
            stream.write("# changed after study\n")
        result = compile_onboarding(str(self.game_repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(BLOCKED_BY_ONBOARDING_MATERIAL, result.status)
        self.assertTrue(any("dirty paths changed" in error for error in result.errors))

    def test_dirty_file_content_change_with_same_path_blocks_handoff(self) -> None:
        with (self.game_repo / "game.gd").open("a", encoding="utf-8") as stream:
            stream.write("# dirty before study\n")
        result = probe_repository(str(self.game_repo), PROBE_RELATIVE.as_posix())
        self.assertEqual(CASE2_PROBE_READY, result.status)
        payload = self._payload()
        payload["repository"]["declared_dirty_paths"] = ["game.gd"]
        self._write_input(payload)
        with (self.game_repo / "game.gd").open("a", encoding="utf-8") as stream:
            stream.write("# changed again after study\n")
        result = compile_onboarding(str(self.game_repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(BLOCKED_BY_ONBOARDING_MATERIAL, result.status)
        self.assertTrue(
            any("working-tree content changed" in error for error in result.errors)
        )

    def test_adapter_revision_must_match_studied_revision(self) -> None:
        payload = self._payload()
        payload["production_adapter"]["supported_revision"] = "wrong-revision"
        self._write_input(payload)
        result = compile_onboarding(str(self.game_repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(BLOCKED_BY_ONBOARDING_MATERIAL, result.status)
        self.assertTrue(
            any("supported_revision must match" in error for error in result.errors)
        )

    def test_production_adapter_requires_all_case3_concerns(self) -> None:
        payload = self._payload()
        payload["production_adapter"]["gameplay_mappings"] = payload[
            "production_adapter"
        ]["gameplay_mappings"][:-1]
        self._write_input(payload)
        result = compile_onboarding(str(self.game_repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(BLOCKED_BY_ONBOARDING_MATERIAL, result.status)
        self.assertTrue(any("rewards_and_state" in error for error in result.errors))

    def test_existing_different_factory_state_blocks_all_writes(self) -> None:
        profile_path = self.game_repo / PROFILE_RELATIVE
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text("intentional existing profile\n")
        self._write_input()
        result = compile_onboarding(str(self.game_repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(BLOCKED_BY_EXISTING_FACTORY_STATE, result.status)
        self.assertFalse((self.game_repo / MODEL_RELATIVE).exists())
        self.assertEqual("intentional existing profile\n", profile_path.read_text())

    def test_tracked_deleted_factory_state_is_not_recreated(self) -> None:
        profile_path = self.game_repo / PROFILE_RELATIVE
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text("tracked profile\n")
        self._git("add", PROFILE_RELATIVE.as_posix())
        self._git("commit", "-m", "add partial factory profile")
        self.revision = self._git("rev-parse", "HEAD").strip()
        profile_path.unlink()
        self._write_input()
        payload = json.loads((self.game_repo / INPUT_RELATIVE).read_text())
        payload["repository"]["declared_dirty_paths"] = [
            PROFILE_RELATIVE.as_posix()
        ]
        (self.game_repo / INPUT_RELATIVE).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        )
        result = compile_onboarding(str(self.game_repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(BLOCKED_BY_EXISTING_FACTORY_STATE, result.status)
        self.assertFalse(profile_path.exists())

    def test_compile_is_idempotent_when_every_artifact_is_exact(self) -> None:
        self._write_input()
        first = compile_onboarding(str(self.game_repo), INPUT_RELATIVE.as_posix())
        second = compile_onboarding(str(self.game_repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(CASE3_READY, first.status)
        self.assertEqual(CASE3_READY, second.status)
        self.assertFalse(second.created_paths)
        self.assertEqual(8, len(second.verified_paths))

    def test_staged_onboarding_files_do_not_invalidate_the_probe(self) -> None:
        self._write_input()
        self._git("add", PROBE_RELATIVE.as_posix(), INPUT_RELATIVE.as_posix())
        result = compile_onboarding(str(self.game_repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(CASE3_READY, result.status)

    def test_absolute_persisted_evidence_path_is_rejected(self) -> None:
        payload = self._payload()
        payload["gameplay_model"]["primary_progression_driver"]["evidence_refs"][0][
            "path"
        ] = str(self.game_repo / "game.gd")
        self._write_input(payload)
        result = compile_onboarding(str(self.game_repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(BLOCKED_BY_ONBOARDING_MATERIAL, result.status)
        self.assertTrue(any("game-repo-relative" in error for error in result.errors))

    def test_check_detects_changed_generated_artifact(self) -> None:
        self._write_input()
        compile_onboarding(str(self.game_repo), INPUT_RELATIVE.as_posix())
        with (self.game_repo / PROFILE_RELATIVE).open("a", encoding="utf-8") as stream:
            stream.write("changed\n")
        result = check_onboarding(str(self.game_repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(BLOCKED_BY_ONBOARDING_MATERIAL, result.status)
        self.assertTrue(any("stale or changed" in error for error in result.errors))

    def test_check_reports_missing_generated_artifact(self) -> None:
        self._write_input()
        compile_onboarding(str(self.game_repo), INPUT_RELATIVE.as_posix())
        (self.game_repo / PROFILE_RELATIVE).unlink()
        result = check_onboarding(str(self.game_repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(BLOCKED_BY_ONBOARDING_MATERIAL, result.status)
        self.assertTrue(any("artifact is missing" in error for error in result.errors))

    def test_probe_recognizes_complete_case3_state(self) -> None:
        self._write_input()
        compile_onboarding(str(self.game_repo), INPUT_RELATIVE.as_posix())
        (self.game_repo / PROBE_RELATIVE).unlink()
        result = probe_repository(str(self.game_repo), PROBE_RELATIVE.as_posix())
        self.assertEqual(ALREADY_CASE3, result.status)


if __name__ == "__main__":
    unittest.main()
