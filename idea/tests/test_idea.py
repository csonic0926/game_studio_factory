import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from idea.idea import (
    BLOCKED_BY_EXISTING_PRODUCT_STATE,
    BLOCKED_BY_IDEA_MATERIAL,
    CONSTRAINTS_RELATIVE,
    IDEA_FACTORY_ALREADY_READY,
    IDEA_FACTORY_DIALOGUE_REQUIRED,
    IDEA_FACTORY_READY,
    INPUT_RELATIVE,
    PROBE_RELATIVE,
    PRODUCT_DIRECTION_REVIEW_REQUIRED,
    RESULT_RELATIVE,
    THESIS_RELATIVE,
    IdeaFactoryError,
    check_product_thesis,
    compile_product_thesis,
    start_idea_factory,
)


class IdeaFactoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.game_repo = Path(self.temporary_directory.name) / "early_game"
        self.game_repo.mkdir()
        self._git("init", "-b", "main")
        self._git("config", "user.email", "test@example.com")
        self._git("config", "user.name", "Test User")
        (self.game_repo / "README.md").write_text(
            "# Early Auto Battler\nA small experimental auto battler.\n",
            encoding="utf-8",
        )
        (self.game_repo / "game.gd").write_text(
            "const CURRENT_LOOP = 'draft_then_auto_battle'\n",
            encoding="utf-8",
        )
        self._git("add", ".")
        self._git("commit", "-m", "early prototype")
        started = start_idea_factory(str(self.game_repo))
        self.assertEqual(IDEA_FACTORY_DIALOGUE_REQUIRED, started.status)
        self.probe = json.loads((self.game_repo / PROBE_RELATIVE).read_text())

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

    def _payload(self, authority: str = "AI_DELEGATED") -> dict:
        delegated = authority == "AI_DELEGATED"
        return {
            "schema_version": "product_thesis_input.v1",
            "project_id": "early-auto-battler",
            "repository": {
                "expected_revision": self.probe["repository"]["revision"],
                "declared_dirty_paths": self.probe["repository"]["dirty_paths"],
                "working_tree_sha256": self.probe["repository"]["working_tree_sha256"],
            },
            "seed": {
                "user_seed": "Help decide the product direction for this early auto battler.",
                "existing_material_refs": [
                    {
                        "path": "README.md",
                        "contains": ["experimental auto battler"],
                    }
                ],
            },
            "delegation": {
                "authorized": delegated,
                "authorization_quote": "Please decide the product direction for me." if delegated else "",
                "scope_decision_ids": ["*"] if delegated else [],
            },
            "decisions": [
                {
                    "decision_id": "cozy-mastery-product",
                    "topic": "product promise and commercial shape",
                    "question": "What durable relationship should this small auto battler create?",
                    "decision": (
                        "Make a low-price premium strategy miniature for a small audience "
                        "that returns to master expressive team construction rather than chores."
                    ),
                    "rationale": (
                        "A focused paid scope can trade mass reach and content volume for "
                        "legible depth, replayable mastery, and a distinct authorial feeling."
                    ),
                    "authority": authority,
                    "material_to_downstream": True,
                    "source_quote": "I adopt the recommended product direction." if authority == "USER_FIXED" else "",
                    "evidence_refs": [],
                    "alternatives_considered": [
                        "A broad free-to-play collection treadmill with recurring live content."
                    ],
                }
            ],
            "product_thesis": {
                "product_promise": {
                    "statement": "A compact auto battler where a small roster expresses a personal strategic idea.",
                    "source_decision_ids": ["cozy-mastery-product"],
                },
                "audience_relationship": {
                    "statement": "Serve a smaller group deeply rather than dilute the game for maximum reach.",
                    "source_decision_ids": ["cozy-mastery-product"],
                },
                "commercial_shape": {
                    "statement": "Use a low-price premium purchase with a deliberately bounded content obligation.",
                    "source_decision_ids": ["cozy-mastery-product"],
                },
                "experience_intent": {
                    "statement": "Move the player from curiosity through readable consequence to ownership of a strategy.",
                    "source_decision_ids": ["cozy-mastery-product"],
                },
                "retention_or_replay_thesis": {
                    "statement": "Replay comes from mastery and alternate team expression, not attendance pressure.",
                    "source_decision_ids": ["cozy-mastery-product"],
                },
                "differentiation": {
                    "statement": "Prioritize short, interpretable runs and authored strategic texture over content volume.",
                    "source_decision_ids": ["cozy-mastery-product"],
                },
                "scope_shape": {
                    "statement": "Keep the product small enough that every unit and rule has a recognizable purpose.",
                    "source_decision_ids": ["cozy-mastery-product"],
                },
            },
            "causal_links": [
                {
                    "link_id": "loyalty-through-mastery",
                    "desired_outcome": "A small audience develops high loyalty and replay intent.",
                    "player_reason": "Players can recognize, test, and refine a strategy that feels personally theirs.",
                    "experience_mechanism": "Short runs expose choices and consequences clearly enough to support mastery.",
                    "downstream_implications": [
                        "Gameplay must make pre-battle choices legible in battle outcomes.",
                        "Production should prefer systemic reuse over a large disposable content catalogue."
                    ],
                    "forbidden_proxies": [
                        "Daily login rewards or repetitive grind presented as retention."
                    ],
                    "source_decision_ids": ["cozy-mastery-product"],
                }
            ],
            "non_goals": [
                {
                    "non_goal_id": "mass-market-volume",
                    "statement": "Do not optimize for maximum audience size or endless content cadence.",
                    "reason": "Those obligations would displace the intended small premium mastery product.",
                    "source_decision_ids": ["cozy-mastery-product"],
                }
            ],
            "validation_hypotheses": [
                {
                    "hypothesis_id": "readable-losses-create-replay",
                    "hypothesis": "Players will retry when a loss makes the consequence of their build understandable.",
                    "why_uncertain": "The prototype has not been observed with target players.",
                    "falsification_signal": "Players cannot explain why they lost or do not want another run.",
                    "cheapest_test": "Observe five blind first runs and ask each player to explain one loss.",
                    "source_decision_ids": ["cozy-mastery-product"],
                }
            ],
            "factory_constraints": [
                {
                    "constraint_id": "mastery-not-attendance",
                    "factories": ["gameplay", "production"],
                    "requirement": "Create replay desire through legible mastery, not attendance rewards or grind.",
                    "rationale": "This is the causal mechanism selected for loyalty in a bounded premium product.",
                    "source_decision_ids": ["cozy-mastery-product"],
                }
            ],
            "unresolved_material_questions": [],
            "ai_assumptions": [],
        }

    def _write_input(self, payload: dict) -> Path:
        path = self.game_repo / INPUT_RELATIVE
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        return path

    def test_start_writes_bounded_non_semantic_probe(self) -> None:
        self.assertEqual("idea_factory_repo_probe.v1", self.probe["schema_version"])
        self.assertLessEqual(
            len(self.probe["candidate_product_materials"]),
            self.probe["candidate_limit"],
        )
        self.assertIn("not product authority", self.probe["interpretation_warning"])
        self.assertFalse((self.game_repo / THESIS_RELATIVE).exists())

    def test_start_supports_a_totally_blank_unborn_git_project(self) -> None:
        blank = Path(self.temporary_directory.name) / "blank_game"
        blank.mkdir()
        subprocess.run(
            ["git", "-C", str(blank), "init", "-b", "main"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        result = start_idea_factory(str(blank))
        self.assertEqual(IDEA_FACTORY_DIALOGUE_REQUIRED, result.status)
        probe = json.loads((blank / PROBE_RELATIVE).read_text())
        self.assertEqual("UNBORN_HEAD", probe["repository"]["revision"])

    def test_ai_recommendation_is_complete_but_requires_review(self) -> None:
        self._write_input(self._payload("AI_RECOMMENDED"))
        result = compile_product_thesis(str(self.game_repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(PRODUCT_DIRECTION_REVIEW_REQUIRED, result.status)
        self.assertEqual(["cozy-mastery-product"], result.review_decision_ids)
        self.assertFalse((self.game_repo / THESIS_RELATIVE).exists())

    def test_explicit_ai_delegation_compiles_checks_and_is_idempotent(self) -> None:
        self._write_input(self._payload())
        compiled = compile_product_thesis(str(self.game_repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(IDEA_FACTORY_READY, compiled.status)
        self.assertTrue((self.game_repo / THESIS_RELATIVE).is_file())
        self.assertTrue((self.game_repo / CONSTRAINTS_RELATIVE).is_file())
        checked = check_product_thesis(str(self.game_repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(IDEA_FACTORY_READY, checked.status)
        started = start_idea_factory(str(self.game_repo))
        self.assertEqual(IDEA_FACTORY_ALREADY_READY, started.status)
        repeated = compile_product_thesis(str(self.game_repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(IDEA_FACTORY_READY, repeated.status)
        self.assertFalse(repeated.created_paths)

    def test_completed_product_authority_survives_later_repository_commits(self) -> None:
        self._write_input(self._payload())
        compiled = compile_product_thesis(str(self.game_repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(IDEA_FACTORY_READY, compiled.status)
        self._git("add", "design")
        self._git("commit", "-m", "adopt product thesis")
        (self.game_repo / "game.gd").write_text(
            "const CURRENT_LOOP = 'draft_then_auto_battle'\n"
            "const NEW_IMPLEMENTATION = true\n",
            encoding="utf-8",
        )
        self._git("add", "game.gd")
        self._git("commit", "-m", "continue production")
        started = start_idea_factory(str(self.game_repo))
        self.assertEqual(IDEA_FACTORY_ALREADY_READY, started.status)

    def test_cli_compile_and_check_complete_the_same_handoff(self) -> None:
        self._write_input(self._payload())
        script = Path(__file__).resolve().parents[1] / "idea.py"
        compiled = subprocess.run(
            [
                "python3",
                str(script),
                "compile",
                "--game-repo",
                str(self.game_repo),
                "--input",
                INPUT_RELATIVE.as_posix(),
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(0, compiled.returncode, compiled.stderr)
        self.assertEqual(IDEA_FACTORY_READY, compiled.stdout.splitlines()[0])
        checked = subprocess.run(
            [
                "python3",
                str(script),
                "check",
                "--game-repo",
                str(self.game_repo),
                "--input",
                INPUT_RELATIVE.as_posix(),
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(0, checked.returncode, checked.stderr)
        self.assertEqual(IDEA_FACTORY_READY, checked.stdout.splitlines()[0])

    def test_user_can_adopt_ai_work_without_producer_vocabulary(self) -> None:
        self._write_input(self._payload("USER_FIXED"))
        result = compile_product_thesis(str(self.game_repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(IDEA_FACTORY_READY, result.status)

    def test_ai_delegated_without_authorization_is_rejected(self) -> None:
        payload = self._payload()
        payload["delegation"] = {
            "authorized": False,
            "authorization_quote": "",
            "scope_decision_ids": [],
        }
        self._write_input(payload)
        result = compile_product_thesis(str(self.game_repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(BLOCKED_BY_IDEA_MATERIAL, result.status)
        self.assertTrue(any("without explicit delegation" in error for error in result.errors))

    def test_delegation_scope_cannot_silently_expand(self) -> None:
        payload = self._payload()
        payload["delegation"]["scope_decision_ids"] = ["another-decision"]
        self._write_input(payload)
        result = compile_product_thesis(str(self.game_repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(BLOCKED_BY_IDEA_MATERIAL, result.status)
        self.assertTrue(any("outside delegation" in error for error in result.errors))

    def test_user_fixed_requires_an_exact_source_quote(self) -> None:
        payload = self._payload("USER_FIXED")
        payload["decisions"][0]["source_quote"] = ""
        self._write_input(payload)
        result = compile_product_thesis(str(self.game_repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(BLOCKED_BY_IDEA_MATERIAL, result.status)

    def test_repo_commitment_requires_exact_existing_evidence(self) -> None:
        payload = self._payload("REPO_COMMITMENT")
        payload["decisions"][0]["evidence_refs"] = [
            {"path": "game.gd", "contains": ["NOT_IN_THE_FILE"]}
        ]
        self._write_input(payload)
        result = compile_product_thesis(str(self.game_repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(BLOCKED_BY_IDEA_MATERIAL, result.status)
        self.assertTrue(any("evidence token not found" in error for error in result.errors))

    def test_validation_hypothesis_cannot_become_binding_authority(self) -> None:
        payload = self._payload("VALIDATION_REQUIRED")
        payload["decisions"][0]["material_to_downstream"] = False
        self._write_input(payload)
        result = compile_product_thesis(str(self.game_repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(BLOCKED_BY_IDEA_MATERIAL, result.status)
        self.assertTrue(any("non-binding decision" in error for error in result.errors))

    def test_hidden_ai_assumption_blocks_compilation(self) -> None:
        payload = self._payload()
        payload["ai_assumptions"] = ["Assume players want long sessions."]
        self._write_input(payload)
        result = compile_product_thesis(str(self.game_repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(BLOCKED_BY_IDEA_MATERIAL, result.status)
        self.assertTrue(any("ai_assumptions must be empty" in error for error in result.errors))

    def test_unknown_source_decision_is_rejected(self) -> None:
        payload = self._payload()
        payload["product_thesis"]["commercial_shape"]["source_decision_ids"] = ["unknown"]
        self._write_input(payload)
        result = compile_product_thesis(str(self.game_repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(BLOCKED_BY_IDEA_MATERIAL, result.status)

    def test_repo_change_after_probe_blocks_handoff(self) -> None:
        self._write_input(self._payload())
        (self.game_repo / "game.gd").write_text(
            "const CURRENT_LOOP = 'changed_after_study'\n",
            encoding="utf-8",
        )
        result = compile_product_thesis(str(self.game_repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(BLOCKED_BY_IDEA_MATERIAL, result.status)
        self.assertTrue(any("dirty paths changed" in error or "dirty content changed" in error for error in result.errors))

    def test_differing_existing_product_state_blocks_all_new_writes(self) -> None:
        self._write_input(self._payload())
        thesis = self.game_repo / THESIS_RELATIVE
        thesis.parent.mkdir(parents=True, exist_ok=True)
        thesis.write_text("user-owned different thesis\n", encoding="utf-8")
        result = compile_product_thesis(str(self.game_repo), INPUT_RELATIVE.as_posix())
        self.assertEqual(BLOCKED_BY_EXISTING_PRODUCT_STATE, result.status)
        self.assertFalse((self.game_repo / CONSTRAINTS_RELATIVE).exists())
        self.assertFalse((self.game_repo / RESULT_RELATIVE).exists())
        self.assertEqual("user-owned different thesis\n", thesis.read_text())

    def test_outside_input_is_rejected_before_output_creation(self) -> None:
        outside = Path(self.temporary_directory.name) / "outside.json"
        outside.write_text("{}\n", encoding="utf-8")
        with self.assertRaises(IdeaFactoryError):
            compile_product_thesis(str(self.game_repo), str(outside))
        self.assertFalse((self.game_repo / THESIS_RELATIVE).exists())

    def test_schema_files_are_valid_json(self) -> None:
        schema_root = Path(__file__).resolve().parents[1] / "schemas"
        for path in sorted(schema_root.glob("*.json")):
            with self.subTest(schema=path.name):
                value = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual("object", value["type"])


if __name__ == "__main__":
    unittest.main()
