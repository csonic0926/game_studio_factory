"""The Director role: in autonomous modes a judgment may be wrong but may not be absent.

All fixture USER messages and Director notes are synthetic test data.
"""
import unittest

from factory_core.authorship import set_mode
from factory_core.refs import FactoryError
from factory_core.state import approval_action, checkpoint, latest, requirement_ids, verify_record
from factory_core.tests import test_authorship as authorship

ROOT = authorship.ROOT
TASK = "unit-one"


class DirectorTests(unittest.TestCase):
    setUp = authorship.AuthorshipModeTests.setUp
    write = authorship.AuthorshipModeTests.write
    user_says = authorship.AuthorshipModeTests.user_says
    go_autonomous = authorship.AuthorshipModeTests.go_autonomous
    inquiry = authorship.AuthorshipModeTests.inquiry
    covered = authorship.AuthorshipModeTests.covered
    rules_model = authorship.AuthorshipModeTests.rules_model
    game_ref = authorship.AuthorshipModeTests.game_ref

    def req(self, stage, previous=None, **kw):
        return dict(task_id=TASK, previous=previous, capability="studio", task="objective", stage=stage,
                    summary="Synthetic director fixture.", unresolved=[], artifacts=[], design=self.design_ref, **kw)

    def note(self, boundary, decision="CONTINUE", number=1, played=True):
        evidence = self.write("design/play/simulation.log", "round 3: moving the sword changed the result\n")
        body = dict(schema_version="factory_director_note.v1", task_id=TASK, design=self.design_ref, boundary=boundary,
                    author_context_id="orchestrator", fun_judgment="The lane read matters in close rounds.",
                    biggest_risk="Stats may dominate placement.", case_against="Only close rounds reward reading.",
                    decision=decision, next="Measure decision leverage before polish.", calibration=[],
                    written_at="2026-10-14T20:00:00+08:00",
                    played=[dict(method="simulated ten rounds deciding each drag myself", evidence=[evidence],
                                 observations="Three of ten drags changed a result.")] if played else [])
        return self.write(f"design/factory/director/{TASK}/{number:06d}.json", body)

    def autonomous_design(self):
        self.go_autonomous()
        self.design, self.design_ref = self.covered(self.inquiry())

    def reviews(self, out):
        record, _ = latest(self.game, TASK)
        binding = record["dependencies"]
        refs = []
        for role in ("intent_experience", "completeness_project"):
            refs.append(self.write(f"design/reviews/{role}.json", dict(schema_version="factory_review.v2", role=role,
                reviewer_context_id=role, fresh=True, peer_reviews_read=[], design=self.design_ref, dependency_fingerprint=binding["fingerprint"],
                verdict="PASS", findings={i: dict(status="PASS", evidence=[self.design_ref], rationale="Synthetic.")
                                          for i in requirement_ids(ROOT, self.design, role, self.current_mode)},
                source_coverage=[r["scope"] + ":" + r["path"] for r in binding["references"] if r["scope"] != "factory"],
                decision_coverage=[d["id"] for d in self.design["decisions"]])))
        return checkpoint(self.roots, self.req("REVIEWED", out["checkpoint"]["sha256"], reviews=refs)), refs, binding

    # ------------------------------------------------------------ tests

    def test_collaborative_needs_no_director_note(self):
        out = checkpoint(self.roots, self.req("DESIGN_COMPLETE"))
        self.assertEqual(out["stage"], "DESIGN_COMPLETE")

    def test_autonomous_boundary_needs_a_judgment_that_played(self):
        self.autonomous_design()
        with self.assertRaisesRegex(FactoryError, "needs the Director's judgment"):
            checkpoint(self.roots, self.req("DESIGN_COMPLETE"))
        with self.assertRaisesRegex(FactoryError, "plays before judging"):
            checkpoint(self.roots, self.req("DESIGN_COMPLETE", director_note=self.note("DESIGN_FREEZE", played=False)))
        with self.assertRaisesRegex(FactoryError, "needs a DESIGN_FREEZE note"):
            checkpoint(self.roots, self.req("DESIGN_COMPLETE", director_note=self.note("PRODUCTION_START")))
        with self.assertRaisesRegex(FactoryError, "advances only on CONTINUE"):
            checkpoint(self.roots, self.req("DESIGN_COMPLETE", director_note=self.note("DESIGN_FREEZE", "REDIRECT")))
        out = checkpoint(self.roots, self.req("DESIGN_COMPLETE", director_note=self.note("DESIGN_FREEZE")))
        self.assertEqual(out["stage"], "DESIGN_COMPLETE")

    def test_note_must_judge_this_design(self):
        self.autonomous_design()
        stale = self.note("DESIGN_FREEZE")
        self.design["intent"] = "A changed design after the judgment."
        self.design_ref = self.write(self.design_ref["path"], self.design)
        with self.assertRaisesRegex(FactoryError, "judged another design"):
            checkpoint(self.roots, self.req("DESIGN_COMPLETE", director_note=stale))

    def test_standing_stop_blocks_production(self):
        self.autonomous_design()
        self.current_mode = "AUTONOMOUS"
        out = checkpoint(self.roots, self.req("DESIGN_COMPLETE", director_note=self.note("DESIGN_FREEZE")))
        out, refs, binding = self.reviews(out)
        action = approval_action(self.design_ref, binding)
        raw = self.write("design/rulings/RAW.json", dict(role="user", content=action))
        ruling = self.write("design/rulings/APPROVAL.json", dict(schema_version="factory_ruling.v2", owner="USER", decision="APPROVE",
            design=self.design_ref, dependency_fingerprint=binding["fingerprint"], source=raw, quote=action))
        out = checkpoint(self.roots, self.req("AUTHORIZED", out["checkpoint"]["sha256"], reviews=refs, ruling=ruling))
        stop = self.note("EVIDENCE_CONTRADICTION", "STOP", number=2)
        with self.assertRaisesRegex(FactoryError, "decided STOP"):
            checkpoint(self.roots, self.req("PRODUCING", out["checkpoint"]["sha256"], reviews=refs, ruling=ruling, director_note=stop))
        produce = self.note("PRODUCTION_START", number=3)
        out = checkpoint(self.roots, self.req("PRODUCING", out["checkpoint"]["sha256"], reviews=refs, ruling=ruling, director_note=produce))
        self.assertEqual(out["stage"], "PRODUCING")

    def test_closed_beta_director_approves_and_revocation_invalidates(self):
        source = self.user_says("AI 完整交付產品我才落手試玩")
        with self.assertRaisesRegex(FactoryError, "delegation seats"):
            set_mode(self.roots, "closed_beta", source["path"], "AI 完整交付產品我才落手試玩", "Simplest Auto Battler", ["SHIP_IT"])
        set_mode(self.roots, "closed_beta", source["path"], "AI 完整交付產品我才落手試玩", "Simplest Auto Battler")
        self.current_mode = "CLOSED_BETA"
        self.design, self.design_ref = self.covered(self.inquiry())
        out = checkpoint(self.roots, self.req("DESIGN_COMPLETE", director_note=self.note("DESIGN_FREEZE")))
        out, refs, binding = self.reviews(out)
        approve = self.note("DESIGN_APPROVAL", number=2)
        ruling = self.write("design/rulings/DIRECTOR_APPROVAL.json", dict(schema_version="factory_ruling.v2", owner="AI_DIRECTOR",
            decision="APPROVE", design=self.design_ref, dependency_fingerprint=binding["fingerprint"], director_note=approve,
            rationale="The core read is worth building; the leverage risk is measured first in production."))
        with self.assertRaisesRegex(FactoryError, "needs the Director's judgment"):
            checkpoint(self.roots, self.req("AUTHORIZED", out["checkpoint"]["sha256"], reviews=refs, ruling=ruling))
        out = checkpoint(self.roots, self.req("AUTHORIZED", out["checkpoint"]["sha256"], reviews=refs, ruling=ruling, director_note=approve))
        self.assertEqual(out["stage"], "AUTHORIZED")
        record, _ = latest(self.game, TASK)
        back = self.user_says("回到 AI 全權自主創作")
        set_mode(self.roots, "autonomous", back["path"], "AI 全權自主創作")
        with self.assertRaises(FactoryError):
            verify_record(self.roots, record)

    def test_director_ruling_refused_outside_closed_beta(self):
        self.autonomous_design()
        self.current_mode = "AUTONOMOUS"
        out = checkpoint(self.roots, self.req("DESIGN_COMPLETE", director_note=self.note("DESIGN_FREEZE")))
        out, refs, binding = self.reviews(out)
        ruling = self.write("design/rulings/DIRECTOR_APPROVAL.json", dict(schema_version="factory_ruling.v2", owner="AI_DIRECTOR",
            decision="APPROVE", design=self.design_ref, dependency_fingerprint=binding["fingerprint"],
            director_note=self.note("DESIGN_APPROVAL", number=2), rationale="Synthetic."))
        with self.assertRaisesRegex(FactoryError, "only while the USER delegates design approval"):
            checkpoint(self.roots, self.req("AUTHORIZED", out["checkpoint"]["sha256"], reviews=refs, ruling=ruling))


if __name__ == "__main__":
    unittest.main()
