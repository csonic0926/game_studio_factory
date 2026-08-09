from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from studio.cycle import BLOCKED, READY, current_factory_revision, validate_gameplay_system


def write_json(repo: Path, relative: str, payload: dict) -> Path:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def ref(repo: Path, relative: str) -> dict[str, str]:
    path = repo / relative
    return {"path": relative, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


class StudioGameplayCycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name) / "game"
        self.repo.mkdir()
        self.factory_revision = current_factory_revision()
        self.root = "design/studio/gameplay_system/core"
        product_input = {
            "causal_links": [
                {"link_id": "judgment-loop"},
                {"link_id": "battle-skin"},
            ]
        }
        write_json(
            self.repo,
            "design/product/idea/PRODUCT_THESIS_INPUT.json",
            product_input,
        )
        product_input_ref = ref(
            self.repo, "design/product/idea/PRODUCT_THESIS_INPUT.json"
        )
        product = """# Product Thesis

## Product causal thesis

### `judgment-loop`

Player judgment must resolve and create the next desire.

### `battle-skin`

The same commitment must be presented and resolved as battle.
"""
        product_path = self.repo / "design/product/PRODUCT_THESIS.md"
        product_path.parent.mkdir(parents=True, exist_ok=True)
        product_path.write_text(product, encoding="utf-8")
        write_json(
            self.repo,
            "design/product/FACTORY_CONSTRAINTS.json",
            {
                "schema_version": "factory_constraints.v2",
                "source_input_sha256": product_input_ref["sha256"],
                "constraints": [
                    {
                        "constraint_id": "core-is-cycle",
                        "factories": ["all"],
                    },
                    {
                        "constraint_id": "battle-is-surface",
                        "factories": ["gameplay"],
                    },
                    {
                        "constraint_id": "story-only",
                        "factories": ["story"],
                    },
                ],
                "non_goals": [
                    {"non_goal_id": "no-attendance-proxy"}
                ],
            },
        )
        self.system_relative = f"{self.root}/STUDIO_GAMEPLAY_SYSTEM.json"
        self.product_review_relative = (
            f"{self.root}/STUDIO_GAMEPLAY_SYSTEM_REVIEW_PRODUCT.json"
        )
        self.cycle_review_relative = (
            f"{self.root}/STUDIO_GAMEPLAY_SYSTEM_REVIEW_CYCLE.json"
        )
        self.manifest_relative = (
            f"{self.root}/STUDIO_GAMEPLAY_SYSTEM_MANIFEST.json"
        )
        self.write_system()
        self.write_reviews_and_manifest()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def system(self) -> dict:
        causal = ["judgment-loop", "battle-skin"]
        constraints = ["core-is-cycle", "battle-is-surface"]
        return {
            "schema_version": "studio_gameplay_system.v2",
            "status": READY,
            "system_id": "core",
            "cycle_id": "forecast-battle-cycle",
            "project_id": "sample",
            "factory_revision": self.factory_revision,
            "product_authority": ref(self.repo, "design/product/PRODUCT_THESIS.md"),
            "product_input": ref(
                self.repo, "design/product/idea/PRODUCT_THESIS_INPUT.json"
            ),
            "factory_constraints": ref(
                self.repo, "design/product/FACTORY_CONSTRAINTS.json"
            ),
            "author_context_id": "system-author",
            "system_promise": "Read a card, commit a call, see it battle, and reinvest the result.",
            "core_player_verbs": ["read", "predict", "battle", "reinvest"],
            "stages": [
                {"stage_id": "choose", "player_goal": "Choose a prediction worth testing."},
                {"stage_id": "locked", "player_goal": "Anticipate the market battle."},
                {"stage_id": "resolved", "player_goal": "Understand the battle result."},
                {"stage_id": "rewarded", "player_goal": "Use the result to pursue a stronger next call."},
            ],
            "state_objects": [
                {"state_id": "judgment-rank", "kind": "PROGRESSION", "owner": "PLAYER", "player_visible": True, "meaning": "Visible judgment record and access tier."},
                {"state_id": "stake-wallet", "kind": "RESOURCE", "owner": "PLAYER", "player_visible": True, "meaning": "Reinvestable game-only battle stake."},
            ],
            "transitions": [
                {"transition_id": "decide", "from_stage_id": "choose", "to_stage_id": "locked", "phase": "PLAYER_DECISION", "player_action": "Read price evidence and choose a card and direction.", "reads_state_ids": ["judgment-rank", "stake-wallet"], "writes_state_ids": [], "visible_consequence": "The forecast becomes the player's battle position.", "motivation_effect": "The player risks visible standing and stake.", "causal_link_ids": causal, "constraint_ids": constraints},
                {"transition_id": "commit", "from_stage_id": "locked", "to_stage_id": "locked", "phase": "COMMITMENT", "player_action": "Lock the prediction.", "reads_state_ids": ["stake-wallet"], "writes_state_ids": ["stake-wallet"], "visible_consequence": "The position cannot be edited.", "motivation_effect": "Commitment creates anticipation.", "causal_link_ids": causal, "constraint_ids": constraints},
                {"transition_id": "resolve", "from_stage_id": "locked", "to_stage_id": "resolved", "phase": "RESOLUTION", "player_action": "Watch the forecast resolve as a card battle.", "reads_state_ids": [], "writes_state_ids": [], "visible_consequence": "Real market movement determines the battle result.", "motivation_effect": "The verdict tests the player's judgment.", "causal_link_ids": causal, "constraint_ids": constraints},
                {"transition_id": "reward", "from_stage_id": "resolved", "to_stage_id": "rewarded", "phase": "REWARD", "player_action": "Claim the result.", "reads_state_ids": [], "writes_state_ids": ["judgment-rank", "stake-wallet"], "visible_consequence": "Rank and wallet visibly change.", "motivation_effect": "The result opens a stronger next opportunity.", "causal_link_ids": causal, "constraint_ids": constraints},
                {"transition_id": "reinvest", "from_stage_id": "rewarded", "to_stage_id": "rewarded", "phase": "REINVESTMENT", "player_action": "Select how to use the changed rank and wallet.", "reads_state_ids": ["judgment-rank", "stake-wallet"], "writes_state_ids": ["judgment-rank", "stake-wallet"], "visible_consequence": "The next opponent, card, or risk tier changes.", "motivation_effect": "Progress creates a new goal rather than a replay prompt.", "causal_link_ids": causal, "constraint_ids": constraints},
                {"transition_id": "return", "from_stage_id": "rewarded", "to_stage_id": "choose", "phase": "RETURN", "player_action": "Enter the next forecast battle.", "reads_state_ids": ["judgment-rank", "stake-wallet"], "writes_state_ids": [], "visible_consequence": "The next decision exposes changed stakes and opportunities.", "motivation_effect": "The player has a concrete reason to predict again.", "causal_link_ids": causal, "constraint_ids": constraints},
            ],
            "cycle_path": ["decide", "commit", "resolve", "reward", "reinvest", "return"],
            "feedback_state_ids": ["judgment-rank", "stake-wallet"],
            "coupled_systems": [
                {"component_id": "forecast-options", "role": "Own the uncertain price decision and commitment.", "transition_ids": ["decide", "commit"], "required_in_first_baseline": True},
                {"component_id": "battle-surface", "role": "Express and resolve the same position as battle.", "transition_ids": ["resolve"], "required_in_first_baseline": True},
                {"component_id": "reward-progression", "role": "Turn resolution into changed next-lap opportunity.", "transition_ids": ["reward", "reinvest", "return"], "required_in_first_baseline": True},
            ],
            "causal_link_coverage": [
                {"link_id": item, "transition_ids": ["decide", "resolve", "reward", "return"], "status": "REALIZED_IN_CYCLE"}
                for item in causal
            ],
            "constraint_coverage": [
                {"constraint_id": item, "transition_ids": ["decide", "resolve", "reward"], "status": "REALIZED_IN_CYCLE"}
                for item in constraints
            ],
            "non_goal_coverage": [{
                "non_goal_id": "no-attendance-proxy",
                "transition_ids": ["reward", "return"],
                "status": "PRESERVED",
                "rationale": "The reward changes opportunity rather than paying attendance.",
            }],
            "two_lap_witness": {
                "lap_one": {"player_goal": "Prove one forecast.", "decision": "Choose the safer card battle.", "resolution": "The market resolves the battle.", "resulting_state": "Rank and wallet increase."},
                "feedback_state_deltas": [
                    {"state_id": "judgment-rank", "before": "Unranked with starter opponent.", "after": "Ranked with a stronger opponent unlocked.", "effect_on_next_decision": "The second decision includes a higher-status opponent."},
                    {"state_id": "stake-wallet", "before": "Starter stake only.", "after": "Enough stake for a different risk tier.", "effect_on_next_decision": "The player can choose a materially different risk/reward."},
                ],
                "lap_two": {"player_goal": "Defend the new rank and use the larger stake.", "decision": "Choose between a stronger opponent and higher-risk card.", "resolution": "The next market battle tests the changed strategy.", "resulting_state": "A new record and opportunity result."},
                "why_second_lap_is_not_repetition": "Lap one changes opponent access, visible rank, and risk capacity used by lap two.",
            },
            "forbidden_linearizations": [
                "A result followed only by a play-again button is not a cycle."
            ],
            "authored_at": "2026-08-05T10:00:00+08:00",
        }

    def write_system(self, payload: dict | None = None) -> None:
        write_json(self.repo, self.system_relative, payload or self.system())

    def review(self, role: str, reviewer: str) -> dict:
        transition_ids = [
            item["transition_id"] for item in json.loads(
                (self.repo / self.system_relative).read_text()
            )["transitions"]
        ]
        return {
            "schema_version": "studio_gameplay_system_review.v2",
            "review_id": f"review-{role.lower().replace('_', '-')}",
            "review_role": role,
            "project_id": "sample",
            "system_id": "core",
            "cycle_id": "forecast-battle-cycle",
            "factory_revision": self.factory_revision,
            "gameplay_system": ref(self.repo, self.system_relative),
            "reviewer_context_id": reviewer,
            "reviewer_freshness": "FRESH",
            "causal_link_ids_reviewed": ["judgment-loop", "battle-skin"] if role == "PRODUCT_FIDELITY" else [],
            "constraint_ids_reviewed": ["core-is-cycle", "battle-is-surface"] if role == "PRODUCT_FIDELITY" else [],
            "non_goal_ids_reviewed": ["no-attendance-proxy"] if role == "PRODUCT_FIDELITY" else [],
            "transition_ids_reviewed": transition_ids,
            "cycle_findings": {"closed_graph": "PASS", "reward_changes_next_decision": "PASS", "second_lap_materially_differs": "PASS", "coupled_systems_preserved": "PASS", "product_boundaries_consistent": "PASS", "gamification_intent_is_reward_cycle": "PASS", "no_proxy_loop": "PASS"},
            "blocking_findings": [],
            "verdict": "PASS_SYSTEM_REVIEW",
            "reviewed_at": "2026-08-05T10:10:00+08:00",
        }

    def write_reviews_and_manifest(self, *, same_reviewer: bool = False) -> None:
        write_json(
            self.repo,
            self.product_review_relative,
            self.review("PRODUCT_FIDELITY", "product-reviewer"),
        )
        write_json(
            self.repo,
            self.cycle_review_relative,
            self.review(
                "CYCLE_CLOSURE",
                "product-reviewer" if same_reviewer else "cycle-reviewer",
            ),
        )
        write_json(
            self.repo,
            self.manifest_relative,
            {
                "schema_version": "studio_gameplay_system_manifest.v1",
                "status": READY,
                "project_id": "sample",
                "system_id": "core",
                "cycle_id": "forecast-battle-cycle",
                "factory_revision": self.factory_revision,
                "gameplay_system": ref(self.repo, self.system_relative),
                "reviews": {
                    "product_fidelity": ref(self.repo, self.product_review_relative),
                    "cycle_closure": ref(self.repo, self.cycle_review_relative),
                },
            },
        )

    def validate(self):
        return validate_gameplay_system(str(self.repo), self.manifest_relative)

    def test_cycle_complete_system_is_ready(self) -> None:
        result = self.validate()
        self.assertEqual(READY, result.status, result.errors)
        self.assertEqual(["judgment-rank", "stake-wallet"], result.feedback_state_ids)

    def test_cycle_requires_active_product_authority(self) -> None:
        write_json(
            self.repo,
            "design/product/PRODUCT_AUTHORITY_REGISTER.json",
            {
                "schema_version": "product_authority_register.v1",
                "project_id": "sample",
                "status": "NO_ACTIVE_PRODUCT_AUTHORITY",
                "active_authority": None,
                "transitions": [],
                "updated_at": "2026-08-05T00:00:00Z",
            },
        )
        result = self.validate()
        self.assertEqual(BLOCKED, result.status)
        self.assertTrue(any("no active Product Thesis" in error for error in result.errors))

    def test_replay_button_without_reward_feedback_is_linear(self) -> None:
        payload = self.system()
        payload["feedback_state_ids"] = ["judgment-rank"]
        for transition in payload["transitions"]:
            if transition["phase"] == "PLAYER_DECISION":
                transition["reads_state_ids"] = ["stake-wallet"]
        payload["two_lap_witness"]["feedback_state_deltas"] = [
            payload["two_lap_witness"]["feedback_state_deltas"][0]
        ]
        self.write_system(payload)
        self.write_reviews_and_manifest()
        result = self.validate()
        self.assertEqual(BLOCKED, result.status)
        self.assertTrue(any("next player decision" in error for error in result.errors))

    def test_reinvestment_cannot_fabricate_a_missing_reward_edge(self) -> None:
        payload = self.system()
        for transition in payload["transitions"]:
            if transition["phase"] == "REWARD":
                transition["writes_state_ids"] = []
        self.write_system(payload)
        self.write_reviews_and_manifest()
        result = self.validate()
        self.assertEqual(BLOCKED, result.status)
        self.assertTrue(any("REWARD" in error for error in result.errors))

    def test_every_product_causal_link_must_be_realized(self) -> None:
        payload = self.system()
        payload["causal_link_coverage"] = payload["causal_link_coverage"][:1]
        self.write_system(payload)
        self.write_reviews_and_manifest()
        result = self.validate()
        self.assertEqual(BLOCKED, result.status)
        self.assertTrue(any("battle-skin" in error for error in result.errors))

    def test_every_product_non_goal_must_be_preserved_and_reviewed(self) -> None:
        payload = self.system()
        payload["non_goal_coverage"] = []
        self.write_system(payload)
        self.write_reviews_and_manifest()
        result = self.validate()
        self.assertEqual(BLOCKED, result.status)
        self.assertTrue(any("no-attendance-proxy" in error for error in result.errors))

    def test_product_review_must_explicitly_check_gamification_as_cycle(self) -> None:
        self.write_system()
        self.write_reviews_and_manifest()
        review = json.loads((self.repo / self.product_review_relative).read_text())
        review["cycle_findings"].pop("gamification_intent_is_reward_cycle")
        write_json(self.repo, self.product_review_relative, review)
        manifest = json.loads((self.repo / self.manifest_relative).read_text())
        manifest["reviews"]["product_fidelity"] = ref(
            self.repo, self.product_review_relative
        )
        write_json(self.repo, self.manifest_relative, manifest)
        result = self.validate()
        self.assertEqual(BLOCKED, result.status)
        self.assertTrue(
            any("gamification_intent_is_reward_cycle" in error for error in result.errors),
            result.errors,
        )

    def test_bounded_scope_cannot_defer_coupled_system(self) -> None:
        payload = self.system()
        payload["coupled_systems"][1]["required_in_first_baseline"] = False
        self.write_system(payload)
        self.write_reviews_and_manifest()
        result = self.validate()
        self.assertEqual(BLOCKED, result.status)
        self.assertTrue(any("cannot defer" in error for error in result.errors))

    def test_independent_review_contexts_are_required(self) -> None:
        self.write_reviews_and_manifest(same_reviewer=True)
        result = self.validate()
        self.assertEqual(BLOCKED, result.status)
        self.assertTrue(any("must be different" in error for error in result.errors))


if __name__ == "__main__":
    unittest.main()
