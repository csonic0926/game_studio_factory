"""Executable rules-model check: bound, current, violation-free; mandatory when AUTONOMOUS."""
import subprocess
import sys
import unittest

from factory_core.refs import FactoryError
from factory_core.state import load_design, requirement_ids
from factory_core.tests import test_authorship as authorship

ROOT = authorship.ROOT
RULE = "gameplay.rules_model_covers_design"


class RulesCheckTests(unittest.TestCase):
    setUp = authorship.AuthorshipModeTests.setUp
    write = authorship.AuthorshipModeTests.write
    user_says = authorship.AuthorshipModeTests.user_says
    go_autonomous = authorship.AuthorshipModeTests.go_autonomous
    inquiry = authorship.AuthorshipModeTests.inquiry
    covered = authorship.AuthorshipModeTests.covered
    rules_model = authorship.AuthorshipModeTests.rules_model
    game_ref = authorship.AuthorshipModeTests.game_ref

    def test_autonomous_requires_bound_rules_check(self):
        self.go_autonomous()
        design, _ = self.covered(self.inquiry())
        design.pop("rules_check")
        with self.assertRaisesRegex(FactoryError, "executable rules-model check"):
            load_design(self.roots, self.write(self.design_ref["path"], design))
        design, design_ref = self.covered(self.inquiry())
        load_design(self.roots, design_ref)
        self.assertIn(RULE, requirement_ids(ROOT, design, "intent_experience", "AUTONOMOUS"))
        self.assertNotIn(RULE, requirement_ids(ROOT, design, "intent_experience"))

    def test_collaborative_needs_no_rules_check_but_validates_one(self):
        load_design(self.roots, self.design_ref)
        broken = [dict(id="gold", statement="Gold never goes negative.", checked_cases=40, violations=1,
                       counterexample="Refresh at 0 gold leaves -1.")]
        with self.assertRaisesRegex(FactoryError, "invariants with violations: \\['gold'\\]"):
            load_design(self.roots, self.covered(self.inquiry(), rules=self.rules_model(invariants=broken))[1])

    def test_inconsistent_worked_example_is_rejected(self):
        self.go_autonomous()
        example = [dict(id="lap-two", statement="The Bow hits the guarded Bow.", status="INCONSISTENT",
                        detail="Guard redirects the hit to the Shield in front.")]
        with self.assertRaisesRegex(FactoryError, "contradict the rules: \\['lap-two'\\]"):
            load_design(self.roots, self.covered(self.inquiry(), rules=self.rules_model(examples=example))[1])
        with self.assertRaisesRegex(FactoryError, "replay every worked example"):
            load_design(self.roots, self.covered(self.inquiry(), rules=self.rules_model(examples=[]))[1])

    def test_rules_model_must_be_sealed_and_current(self):
        self.go_autonomous()
        design, _ = self.covered(self.inquiry())
        model = self.game_ref("rules/model.py")
        design["inputs"] = [item for item in design["inputs"] if item != model]
        with self.assertRaisesRegex(FactoryError, "sealed design input or artifact"):
            load_design(self.roots, self.write(self.design_ref["path"], design))
        design, design_ref = self.covered(self.inquiry())
        self.write("rules/model.py", "print('edited after the check')\n")
        with self.assertRaises(FactoryError):
            load_design(self.roots, design_ref)

    def test_run_rejects_violation_without_counterexample_and_cli_exit(self):
        from gameplay.rules_check import run
        self.write("rules/bad.py", 'import json\nprint(json.dumps({"schema_version": "gameplay_rules_report.v1", '
                   '"invariants": [{"id": "cap", "statement": "Cap holds.", "checked_cases": 3, "violations": 2}], "examples": []}))\n')
        with self.assertRaisesRegex(FactoryError, "counterexample"):
            run(str(self.game), "rules/bad.py", [sys.executable, "rules/bad.py"], "design/gameplay/BAD.json")
        self.rules_model(invariants=[dict(id="cap", statement="Cap holds.", checked_cases=3, violations=1, counterexample="Six on a five board.")])
        out = subprocess.run([sys.executable, str(ROOT / "gameplay/rules_check.py"), "run", "--game-repo", str(self.game),
                              "--model", "rules/model.py", "--output", "design/gameplay/RULES_CHECK.json", "--",
                              sys.executable, "rules/model.py"], capture_output=True, text=True)
        self.assertEqual(out.returncode, 2, out.stdout + out.stderr)
        self.assertIn('"violations": 1', out.stdout)

    def test_balance_target_met_only_when_every_run_is_inside(self):
        self.go_autonomous()
        target = dict(id="color-share", statement="No color dominates winners.", metric="largest color share of winners",
                      bounds=dict(max=0.35), runs=[0.27, 0.43, 0.25], method="60 tournaments per run, distinct seeds")
        with self.assertRaisesRegex(FactoryError, "retune or revise.*color-share"):
            load_design(self.roots, self.covered(self.inquiry(), rules=self.rules_model(balance=[target]))[1])
        single = dict(target, runs=[0.27])
        with self.assertRaisesRegex(FactoryError, "at least 3 independent runs"):
            load_design(self.roots, self.covered(self.inquiry(), rules=self.rules_model(balance=[single]))[1])
        with self.assertRaisesRegex(FactoryError, "declare the design's own measurable balance targets"):
            load_design(self.roots, self.covered(self.inquiry(), rules=self.rules_model(balance=[]))[1])
        design, design_ref = self.covered(self.inquiry(), rules=self.rules_model(balance=[dict(target, runs=[0.27, 0.31, 0.25])]))
        load_design(self.roots, design_ref)
        self.assertIn("gameplay.balance_targets_declared_and_measured", requirement_ids(ROOT, design, "completeness_project", "AUTONOMOUS"))

    def test_collaborative_allows_single_run_but_still_rejects_unmet(self):
        target = dict(id="hard-win-rate", statement="Hard stays hard.", metric="player win rate at three stars",
                      bounds=dict(max=0.3), runs=[0.1], method="one exploratory run")
        load_design(self.roots, self.covered(self.inquiry(), rules=self.rules_model(balance=[target]))[1])
        with self.assertRaisesRegex(FactoryError, "hard-win-rate"):
            load_design(self.roots, self.covered(self.inquiry(), rules=self.rules_model(balance=[dict(target, runs=[0.4])]))[1])
        bad = dict(target, bounds=dict(min=0.5, max=0.2))
        from gameplay.rules_check import run
        with self.assertRaisesRegex(FactoryError, "min <= max"):
            self.rules_model(balance=[bad])


if __name__ == "__main__":
    unittest.main()
