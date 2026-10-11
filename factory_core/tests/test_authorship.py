"""USER-selected authorship modes: COLLABORATIVE keeps the soft rule, AUTONOMOUS gates Idea coverage.

All fixture USER messages are synthetic test data, not real USER rulings.
"""
import copy
import subprocess
import sys
import unittest

from factory_core.authorship import MODE_PATH, mode, set_mode
from factory_core.refs import FactoryError, read_json
from factory_core.state import dependencies, load_design, requirement_ids
from factory_core.tests import test_gpt6_gameplay as native
from factory_core.tests import test_gameplay_v2 as legacy_tests

ROOT = legacy_tests.ROOT
RULE = "idea.per_idea_inquiry_substantive"


def idea(identity, judgment="ADOPT"):
    return dict(id=identity, idea=f"{identity} as a synthetic mechanism.", authority="AI_HYPOTHESIS",
                player_situation="The player wants to out-read the visible rival.",
                mechanism="It changes which enemy is hit first.", cost_or_tension="It spends a board slot.",
                alternatives=["Leave the slot empty."], evidence=[], assumptions=["Players notice the lane."],
                judgment=judgment, reasons="Synthetic reasoning for a validator fixture.")


class AuthorshipModeTests(unittest.TestCase):
    write = legacy_tests.GameplayV2Tests.write

    def setUp(self):
        native.NativeGameplayTests.setUp(self)
        self.decision_ids = [item["id"] for item in self.design["decisions"]]

    def user_says(self, words, role="user"):
        return self.write("design/factory/transcript/mode-message.json", dict(role=role, content=words))

    def go_autonomous(self):
        source = self.user_says("AI 全權自主創作，禁止跳過 idea")
        return set_mode(self.roots, "autonomous", source["path"], "AI 全權自主創作")

    def inquiry(self, ideas=None, questions=None):
        record = dict(schema_version="idea_inquiry.v1", topic="Lane reading", coupling="Lanes and colors share board slots.",
                      ideas=ideas or [idea("lane-guard")], open_questions=questions or [])
        return self.write("design/product/idea/inquiries/lanes.json", record)

    def rules_model(self, invariants=None, examples=None, balance=None):
        """A tiny game-owned rules model whose command prints its report."""
        report = dict(schema_version="gameplay_rules_report.v1",
                      invariants=invariants or [dict(id="board-capacity", statement="Deployed units never exceed level + 2.", checked_cases=500, violations=0)],
                      examples=[dict(id="lap-two", statement="Lap two's Bow reaches the back row.", status="CONSISTENT", detail="Replayed.")] if examples is None else examples,
                      balance_targets=[dict(id="easy-win-rate", statement="A reading player wins most easy tournaments.", metric="player win rate at one star",
                                            bounds=dict(min=0.5), runs=[0.97, 0.95, 0.98], method="60 simulated tournaments per run, distinct seeds")] if balance is None else balance)
        model = self.write("rules/model.py", "import json\nprint(json.dumps(%r))\n" % report)
        from gameplay.rules_check import run
        run(str(self.game), "rules/model.py", [sys.executable, "rules/model.py"], "design/gameplay/RULES_CHECK.json")
        return self.game_ref("rules/model.py"), self.game_ref("design/gameplay/RULES_CHECK.json")

    def game_ref(self, path):
        from factory_core.refs import reference
        return reference(self.game, path)

    def covered(self, ref, decisions=None, rules=None):
        design = copy.deepcopy(self.design)
        model, record = rules or self.rules_model()
        design["inputs"] = design["inputs"] + [ref, model, record]
        design["rules_check"] = record
        design["idea_coverage"] = dict(inquiries=[ref], decisions=decisions or {
            identity: dict(ideas=["lane-guard"]) if index == 0 else dict(not_a_design_idea="Layout bookkeeping, no player-facing mechanism.")
            for index, identity in enumerate(self.decision_ids)})
        return design, self.write(self.design_ref["path"], design)

    def test_default_mode_is_collaborative_and_coverage_is_optional(self):
        self.assertEqual(mode(self.roots), "COLLABORATIVE")
        load_design(self.roots, self.design_ref)
        design = self.design
        self.assertNotIn(RULE, requirement_ids(ROOT, design, "intent_experience"))

    def test_collaborative_records_open_judgments_without_blocking(self):
        ref = self.inquiry([idea("lane-guard", "OPEN")], [dict(id="q1", question="Is the lane readable?", idea_ids=["lane-guard"], disposition="OPEN")])
        _, design_ref = self.covered(ref)
        load_design(self.roots, design_ref)

    def test_autonomous_requires_inquiry_for_every_decision(self):
        self.go_autonomous()
        self.assertEqual(mode(self.roots), "AUTONOMOUS")
        with self.assertRaisesRegex(FactoryError, "skipping Idea is not allowed"):
            load_design(self.roots, self.design_ref)
        ref = self.inquiry()
        partial = {self.decision_ids[0]: dict(ideas=["lane-guard"])}
        with self.assertRaisesRegex(FactoryError, "classify every material decision"):
            load_design(self.roots, self.covered(ref, partial)[1])
        design, design_ref = self.covered(ref)
        load_design(self.roots, design_ref)
        self.assertIn(RULE, requirement_ids(ROOT, design, "intent_experience", "AUTONOMOUS"))
        self.assertIn(RULE, requirement_ids(ROOT, design, "completeness_project", "AUTONOMOUS"))

    def test_autonomous_rejects_relying_on_unadopted_idea(self):
        self.go_autonomous()
        with self.assertRaisesRegex(FactoryError, "judged OPEN"):
            load_design(self.roots, self.covered(self.inquiry([idea("lane-guard", "OPEN")]))[1])
        with self.assertRaisesRegex(FactoryError, "has no inquiry"):
            load_design(self.roots, self.covered(self.inquiry(), {i: dict(ideas=["missing-idea"]) for i in self.decision_ids})[1])

    def test_autonomous_requires_every_open_question_dispositioned(self):
        self.go_autonomous()
        open_question = dict(id="q1", question="Is the lane readable at phone size?", idea_ids=["lane-guard"], disposition="OPEN")
        with self.assertRaisesRegex(FactoryError, "falsifiable hypothesis"):
            load_design(self.roots, self.covered(self.inquiry(questions=[open_question]))[1])
        hypothesis = dict(open_question, disposition="HYPOTHESIS", falsification="A blind observer cannot say who is hit.",
                          test_stage="runtime blind observation")
        load_design(self.roots, self.covered(self.inquiry(questions=[hypothesis]))[1])
        half = dict(open_question, disposition="DEFERRED", reason="Needs a playtest.")
        with self.assertRaisesRegex(FactoryError, "missing \\['revisit'\\]"):
            load_design(self.roots, self.covered(self.inquiry(questions=[half]))[1])

    def test_inquiry_must_be_sealed_design_input(self):
        self.go_autonomous()
        ref = self.inquiry()
        design, _ = self.covered(ref)
        design["inputs"] = [item for item in design["inputs"] if item != ref]
        with self.assertRaisesRegex(FactoryError, "sealed in the review closure"):
            load_design(self.roots, self.write(self.design_ref["path"], design))

    def test_shallow_inquiry_shape_is_rejected(self):
        self.go_autonomous()
        thin = idea("lane-guard")
        thin["alternatives"] = []
        with self.assertRaisesRegex(FactoryError, "at least one alternative"):
            load_design(self.roots, self.covered(self.inquiry([thin]))[1])
        thin = idea("lane-guard")
        thin["assumptions"] = []
        with self.assertRaisesRegex(FactoryError, "evidence from the unresolved assumptions"):
            load_design(self.roots, self.covered(self.inquiry([thin]))[1])

    def test_mode_switch_changes_review_closure(self):
        design, design_ref = self.covered(self.inquiry())
        before = dependencies(self.roots, design_ref, design)["fingerprint"]
        self.go_autonomous()
        after = dependencies(self.roots, design_ref, design)
        self.assertNotEqual(before, after["fingerprint"])
        self.assertIn(MODE_PATH, [ref["path"] for ref in after["references"]])

    def test_mode_needs_raw_user_words(self):
        source = self.user_says("AI 全權自主創作", role="assistant")
        with self.assertRaisesRegex(FactoryError, "raw USER message"):
            set_mode(self.roots, "autonomous", source["path"], "AI 全權自主創作")
        source = self.user_says("Keep working together.")
        with self.assertRaisesRegex(FactoryError, "raw USER message"):
            set_mode(self.roots, "autonomous", source["path"], "AI 全權自主創作")
        self.assertEqual(mode(self.roots), "COLLABORATIVE")
        self.go_autonomous()
        source = self.user_says("回到人 ＋ AI 協作")
        result = set_mode(self.roots, "collaborative", source["path"], "人 ＋ AI 協作")
        self.assertEqual(result["status"], "MODE_SET")
        self.assertEqual(read_json(self.game / MODE_PATH)["previous"]["path"], MODE_PATH)
        self.assertEqual(mode(self.roots), "COLLABORATIVE")

    def test_idea_cli_reports_open_questions(self):
        self.inquiry(questions=[dict(id="q1", question="Is it readable?", idea_ids=["lane-guard"], disposition="OPEN")])
        out = subprocess.run([sys.executable, str(ROOT / "idea/idea.py"), "check-inquiry", "--game-repo", str(self.game),
                              "--input", "design/product/idea/inquiries/lanes.json"], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("IDEA_INQUIRY_VALID", out.stdout)
        self.assertIn("OPEN_QUESTION: q1", out.stdout)


if __name__ == "__main__":
    unittest.main()
