"""UI Design capability: starts from authorized gameplay; the artifacts cover every rule,
step, event and preview; FORBIDDEN facts never leak; the mechanical report is complete.

All fixture content is synthetic test data, not a real design or USER ruling.
"""
import copy
import subprocess
import sys
import unittest

from factory_core.refs import FactoryError, read_json
from factory_core.state import dependencies, load_design, requirement_ids
from factory_core.tests import test_gpt6_gameplay as native
from factory_core.tests import test_gameplay_v2 as legacy_tests
from ui.ui_design import contract_ids

ROOT = legacy_tests.ROOT
UI_DIR = "design/ui/unit-one"


class UiDesignTests(unittest.TestCase):
    write = legacy_tests.GameplayV2Tests.write
    req = legacy_tests.GameplayV2Tests.req
    authorize = legacy_tests.GameplayV2Tests.authorize

    def setUp(self):
        native.NativeGameplayTests.setUp(self)
        contract = read_json(self.game / self.contract["path"])
        self.beats, self.steps = contract_ids(contract)
        self.assertTrue(self.beats and self.steps)

    # ------------------------------------------------------------ fixture builders

    def artifacts(self):
        beats, steps = sorted(self.beats), sorted(self.steps)
        model = dict(schema_version="ui_information_model.v1", objective_id="unit-one", interaction_contract=self.contract,
            rules=[dict(rule_id="rule.guard", source="rules/model.py#guard", statement="A Shield takes hits aimed behind it.",
                        fact_ids=["fact.first-target", "fact.guard-hit"])],
            decisions=[dict(step_id=step, fact_ids=["fact.first-target"]) for step in steps],
            facts=[dict(fact_id="fact.first-target", statement="Whom each unit strikes first.", source="rules/model.py#targets",
                        need="MUST_KNOW", serves=beats, when=["BEFORE_DECISION"], channel="DISCLOSED", canonical_wording="first target"),
                   dict(fact_id="fact.guard-hit", statement="A guarded hit lands on the Shield.", source="rules/model.py#guard",
                        need="MUST_KNOW", serves=beats[:1], when=["DURING_RESOLUTION"], channel="TRANSIENT_CUE", canonical_wording="Guard"),
                   dict(fact_id="fact.winner-forecast", statement="Who will win before the fight.", source="design#D15",
                        need="FORBIDDEN", serves=beats[:1], when=["BEFORE_DECISION"], channel=None, canonical_wording="forecast",
                        guard="Lines show first targets only; no simulation result is drawn before Fight.")])
        model["rules"].append(dict(rule_id="rule.no-forecast", source="design#D15", statement="The winner is never shown before the fight.",
                                   fact_ids=["fact.first-target", "fact.winner-forecast"]))
        attention = dict(schema_version="ui_attention_plan.v1",
            protected_elements=[dict(element_id="card-numbers", description="ATK and HP plates of every card")],
            events=[dict(event_id="event.guard", source="fight log guarded=true", fact_ids=["fact.guard-hit"], cue="Guard badge over the Shield",
                         max_latency_ms=500, min_readable_ms=500, clock="REAL_TIME", skip_behavior="cleared by Skip",
                         max_concurrent_per_object=1, priority=10, on_collision="WAIT", max_wait_ms=500, never_covers=["card-numbers"])],
            beats=[dict(beat_id=beat, first_focus="the rival board", calm_until="the player taps a unit") for beat in beats])
        screens = dict(schema_version="ui_screen_contracts.v1", surfaces=[dict(
            surface_id="board", beats=beats,
            layers=[dict(layer_id="lines", order=10, protects=[]), dict(layer_id="plates", order=12, protects=["card-numbers"]),
                    dict(layer_id="badges", order=30, protects=[])],
            placements=[dict(fact_id="fact.first-target", channel="DISCLOSED", layer_id="lines", size_class="line"),
                        dict(fact_id="fact.guard-hit", channel="TRANSIENT_CUE", layer_id="badges", size_class="30px")],
            density=dict(persistent_item_ceiling=12, disclosure_controls=["tap a unit", "hold Lines"]),
            inputs=[dict(input_id="drag", step_ids=steps, response="the unit follows the finger and lines update live",
                         persistent_change="the unit stands on the drop cell", preview="the board as it would land",
                         preview_equality_check="drag preview equals the board after drop")],
            terminology=[dict(fact_id="fact.guard-hit", wording="Guard")])])
        verification = dict(schema_version="ui_verification_plan.v1",
            mechanical_checks=[dict(check_id="check.badge-timing", kind="timing", covers=["event.guard"], method="tests/test_badges.gd"),
                               dict(check_id="check.preview", kind="preview_equality", covers=["board:drag"], method="tests/test_preview.gd")],
            blind_chains=[dict(chain_id="chain.a", must_know_fact_ids=["fact.first-target", "fact.guard-hit"],
                               hypotheses=[dict(hypothesis_id="h.lines", statement="Players read a tapped unit's aim.",
                                                falsifier="The observer cannot tell who aims at a tapped unit.", fallback="Outline the aiming cards.")])],
            user_playtest_signals=[dict(signal_id="signal.drags", question="How many drags per placement change?", fact_ids=[])])
        return dict(information_model=model, attention_plan=attention, screen_contracts=screens, verification_plan=verification)

    def ui_design(self, parts=None, gameplay_checkpoint=None, reason="Synthetic fixture: the sample game has no executable rules model."):
        parts = parts or self.artifacts()
        refs = {name: self.write(f"{UI_DIR}/{name.upper()}.json", body) for name, body in parts.items()}
        text = "UI-1: tapped units show their own line and the lines that end on them.\n"
        doc = self.write(f"{UI_DIR}/UI_DESIGN.md", text)
        design = dict(schema_version="factory_design.v3", design_id="unit-one-ui", capability="ui", task="ui_design",
            author_context_id="ui-author", intent="Make the board readable for the decide beat.",
            artifacts=[doc, *refs.values()], inputs=[gameplay_checkpoint or self.gameplay_checkpoint, self.contract],
            decisions=[dict(id="ui-1", source=doc, excerpt=text.strip(), consequence=text.strip())],
            requirements={}, production_scope=["scripts/unit_one_ui.gd"], acceptance=["Mechanical report, blind chain and USER playtest."],
            methods=[], decision_sections=[dict(id="ui-1", source=doc, text=text.strip(), decision_ids=["ui-1"])],
            ui=dict(gameplay_checkpoint=gameplay_checkpoint or self.gameplay_checkpoint, **refs))
        if reason is not None:
            design["ui"]["rules_model_absent_reason"] = reason
        return design, self.write(f"{UI_DIR}/FACTORY_DESIGN.json", design)

    def authorized_gameplay(self):
        out, _refs, _ruling = self.authorize()
        self.gameplay_checkpoint = out["checkpoint"]
        return out

    # ------------------------------------------------------------ tests

    def test_gate_requires_authorized_gameplay(self):
        from factory_core.state import checkpoint
        out = checkpoint(self.roots, self.req("DESIGN_COMPLETE"))
        self.gameplay_checkpoint = out["checkpoint"]
        with self.assertRaisesRegex(FactoryError, "AUTHORIZED before UI design"):
            load_design(self.roots, self.ui_design()[1])

    def test_valid_ui_design_loads_with_ui_reviews_and_gameplay_closure(self):
        self.authorized_gameplay()
        design, ref = self.ui_design()
        load_design(self.roots, ref)
        required = requirement_ids(ROOT, design, "intent_experience")
        self.assertIn("ui.preview_equals_outcome", required)
        self.assertIn("ui.no_forbidden_fact_leaked", required)
        self.assertNotIn("gameplay.minimum_cycle_complete_slice", required)
        paths = {r["path"] for r in dependencies(self.roots, ref, design)["references"]}
        self.assertIn("ui/docs/UI_DESIGN_CAPABILITY.md", paths)
        self.assertIn(self.gameplay_checkpoint["path"], paths)

    def test_rules_model_reason_needed_without_rules_check(self):
        self.authorized_gameplay()
        with self.assertRaisesRegex(FactoryError, "rules_model_absent_reason"):
            load_design(self.roots, self.ui_design(reason=None)[1])

    def test_superseded_gameplay_blocks(self):
        out = self.authorized_gameplay()
        from factory_core.state import checkpoint
        checkpoint(self.roots, self.req("DRAFT", out["checkpoint"]["sha256"]))
        with self.assertRaisesRegex(FactoryError, "no longer the current authorized design"):
            load_design(self.roots, self.ui_design()[1])

    def test_every_rule_step_and_fact_is_covered(self):
        self.authorized_gameplay()
        parts = self.artifacts()
        parts["information_model"]["decisions"] = parts["information_model"]["decisions"][1:]
        with self.assertRaisesRegex(FactoryError, "every contract step lists the facts it needs"):
            load_design(self.roots, self.ui_design(parts)[1])
        parts = self.artifacts()
        parts["information_model"]["rules"][0]["fact_ids"] = ["fact.winner-forecast"]
        with self.assertRaisesRegex(FactoryError, "at least one fact the player may see"):
            load_design(self.roots, self.ui_design(parts)[1])
        parts = self.artifacts()
        parts["screen_contracts"]["surfaces"][0]["placements"] = parts["screen_contracts"]["surfaces"][0]["placements"][1:]
        with self.assertRaisesRegex(FactoryError, "fact.first-target is placed on no surface"):
            load_design(self.roots, self.ui_design(parts)[1])

    def test_forbidden_fact_never_leaks(self):
        self.authorized_gameplay()
        parts = self.artifacts()
        parts["screen_contracts"]["surfaces"][0]["placements"].append(
            dict(fact_id="fact.winner-forecast", channel="EXPLANATION", layer_id="badges", size_class="30px"))
        with self.assertRaisesRegex(FactoryError, "places FORBIDDEN fact"):
            load_design(self.roots, self.ui_design(parts)[1])
        parts = self.artifacts()
        parts["information_model"]["facts"][2].pop("guard")
        with self.assertRaisesRegex(FactoryError, "guard"):
            load_design(self.roots, self.ui_design(parts)[1])

    def test_attention_is_bounded_and_every_cue_fact_has_an_event(self):
        self.authorized_gameplay()
        parts = self.artifacts()
        parts["attention_plan"]["events"][0]["max_wait_ms"] = 9200
        with self.assertRaisesRegex(FactoryError, "exceeds max_latency_ms"):
            load_design(self.roots, self.ui_design(parts)[1])
        parts = self.artifacts()
        parts["attention_plan"]["events"][0].pop("max_wait_ms")
        with self.assertRaisesRegex(FactoryError, "a waiting cue needs a bound"):
            load_design(self.roots, self.ui_design(parts)[1])
        parts = self.artifacts()
        parts["attention_plan"]["events"] = [dict(parts["attention_plan"]["events"][0], fact_ids=["fact.first-target"])]
        with self.assertRaisesRegex(FactoryError, "transient-cue facts with no event"):
            load_design(self.roots, self.ui_design(parts)[1])

    def test_previews_terminology_and_verification(self):
        self.authorized_gameplay()
        parts = self.artifacts()
        parts["screen_contracts"]["surfaces"][0]["inputs"][0].pop("preview_equality_check")
        with self.assertRaisesRegex(FactoryError, "a preview must equal what it previews"):
            load_design(self.roots, self.ui_design(parts)[1])
        parts = self.artifacts()
        parts["screen_contracts"]["surfaces"][0]["terminology"] = [dict(fact_id="fact.guard-hit", wording="Block")]
        with self.assertRaisesRegex(FactoryError, "canonical is 'Guard'"):
            load_design(self.roots, self.ui_design(parts)[1])
        parts = self.artifacts()
        parts["verification_plan"]["mechanical_checks"] = parts["verification_plan"]["mechanical_checks"][:1]
        with self.assertRaisesRegex(FactoryError, "every event and every preview needs a mechanical check"):
            load_design(self.roots, self.ui_design(parts)[1])
        parts = self.artifacts()
        parts["verification_plan"]["blind_chains"][0]["must_know_fact_ids"] = ["fact.first-target"]
        with self.assertRaisesRegex(FactoryError, "MUST_KNOW facts no blind chain or USER signal verifies"):
            load_design(self.roots, self.ui_design(parts)[1])

    def test_mechanical_report_and_cli(self):
        self.authorized_gameplay()
        design, ref = self.ui_design()
        log = self.write("design/ui/unit-one/reports/badge.log", "PASS\n")
        report = dict(schema_version="ui_mechanical_report.v1", game_revision="a" * 40, ui_design=ref,
                      checks=[dict(check_id="check.badge-timing", status="PASS", evidence=log)])
        from ui.ui_design import validate_report
        with self.assertRaisesRegex(FactoryError, "planned checks with no result"):
            validate_report(self.roots, design, report)
        report["checks"].append(dict(check_id="check.preview", status="FAIL", evidence=log))
        with self.assertRaisesRegex(FactoryError, "mechanical checks failed"):
            validate_report(self.roots, design, report)
        report["checks"][1]["status"] = "PASS"
        self.assertEqual(validate_report(self.roots, design, report)["status"], "UI_MECHANICAL_PASS")
        self.write("design/ui/unit-one/REPORT.json", report)
        out = subprocess.run([sys.executable, str(ROOT / "ui/ui_design.py"), "report", "--game-repo", str(self.game),
                              "--design", ref["path"], "--report", "design/ui/unit-one/REPORT.json"], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        out = subprocess.run([sys.executable, str(ROOT / "ui/ui_design.py"), "check", "--game-repo", str(self.game),
                              "--design", ref["path"]], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn("UI_DESIGN_CONSISTENT", out.stdout)

    def authorize_ui(self, ref, design):
        """The ordinary v3 chain for the ui design: DESIGN_COMPLETE, two reviews, USER ruling."""
        from factory_core.state import approval_action, checkpoint, latest
        req = lambda stage, previous=None, **kw: dict(task_id="unit-one-ui", previous=previous, capability="ui", task="ui_design",
            stage=stage, summary="Synthetic UI design fixture.", unresolved=[], artifacts=[], design=ref, **kw)
        out = checkpoint(self.roots, req("DESIGN_COMPLETE"))
        record, _ = latest(self.game, "unit-one-ui")
        binding = record["dependencies"]
        refs = []
        for role in ("intent_experience", "completeness_project"):
            refs.append(self.write(f"design/reviews/ui-{role}.json", dict(schema_version="factory_review.v2", role=role,
                reviewer_context_id=f"ui-{role}", fresh=True, peer_reviews_read=[], design=ref, dependency_fingerprint=binding["fingerprint"],
                verdict="PASS", findings={i: dict(status="PASS", evidence=[ref], rationale="Synthetic.") for i in requirement_ids(ROOT, design, role)},
                source_coverage=[r["scope"] + ":" + r["path"] for r in binding["references"] if r["scope"] != "factory"],
                decision_coverage=[d["id"] for d in design["decisions"]])))
        out = checkpoint(self.roots, req("REVIEWED", out["checkpoint"]["sha256"], reviews=refs))
        action = approval_action(ref, binding)
        raw = self.write("design/rulings/UI_RAW.json", dict(role="user", content=action))
        ruling = self.write("design/rulings/UI_APPROVAL.json", dict(schema_version="factory_ruling.v2", owner="USER", decision="APPROVE",
            design=ref, dependency_fingerprint=binding["fingerprint"], source=raw, quote=action))
        return checkpoint(self.roots, req("AUTHORIZED", out["checkpoint"]["sha256"], reviews=refs, ruling=ruling))

    def test_ui_plans_must_cite_the_authorized_ui_design(self):
        from ui.ui_binding import UiImpactBinding
        from ui.ui_design import plan_binding_errors
        self.authorized_gameplay()
        gameplay_path = self.gameplay_checkpoint["path"]
        plain = [("plans[0]", UiImpactBinding(touches_ui=True))]
        self.assertEqual(plan_binding_errors(self.game, gameplay_path, plain), [])
        design, ref = self.ui_design()
        out = self.authorize_ui(ref, design)
        cited = {k: out["checkpoint"][k] for k in ("path", "sha256")}
        self.assertTrue(any("cite the authorized UI design" in e for e in plan_binding_errors(self.game, gameplay_path, plain)))
        good = [("plans[0]", UiImpactBinding(touches_ui=True, ui_design_checkpoint=cited))]
        self.assertEqual(plan_binding_errors(self.game, gameplay_path, good), [])
        stale = [("plans[0]", UiImpactBinding(touches_ui=True, ui_design_checkpoint=dict(cited, sha256="0" * 64)))]
        self.assertTrue(any("not a current authorized UI design" in e for e in plan_binding_errors(self.game, gameplay_path, stale)))
        non_ui = [("plans[0]", UiImpactBinding(touches_ui=False))]
        self.assertEqual(plan_binding_errors(self.game, gameplay_path, non_ui), [])

    def test_comparison_judges_every_must_know_fact_of_the_chain(self):
        from ui.ui_design import validate_fact_observations
        self.authorized_gameplay()
        _design, ref = self.ui_design()
        cited = {"path": ref["path"], "sha256": ref["sha256"]}
        fact = lambda fid, status="UNDERSTOOD": dict(fact_id=fid, status=status, observation_citations=["attempt.1"], rationale="Synthetic.")
        value = dict(ui_design=cited, chain_id="chain.a", facts=[fact("fact.first-target"), fact("fact.guard-hit")])
        errors = []
        validate_fact_observations(self.game, value, {"attempt.1"}, errors)
        self.assertEqual(errors, [])
        errors = []
        validate_fact_observations(self.game, dict(value, facts=[fact("fact.first-target"), fact("fact.guard-hit", "NOT_UNDERSTOOD")]), {"attempt.1"}, errors)
        self.assertTrue(any("NOT_UNDERSTOOD" in e for e in errors), errors)
        errors = []
        validate_fact_observations(self.game, dict(value, facts=[fact("fact.first-target")]), {"attempt.1"}, errors)
        self.assertTrue(any("exactly the chain's MUST_KNOW facts" in e for e in errors), errors)
        errors = []
        validate_fact_observations(self.game, value, {"attempt.2"}, errors)
        self.assertTrue(any("sealed blind attempts" in e for e in errors), errors)

    def test_ui_binding_only_on_ui_designs(self):
        self.authorized_gameplay()
        gameplay = copy.deepcopy(self.design)
        gameplay["ui"] = dict(gameplay_checkpoint=self.gameplay_checkpoint)
        with self.assertRaisesRegex(FactoryError, "only to a ui design"):
            load_design(self.roots, self.write("design/gameplay/OTHER_DESIGN.json", gameplay))


if __name__ == "__main__":
    unittest.main()
