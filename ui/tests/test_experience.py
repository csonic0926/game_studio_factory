"""Behavioral protocol regressions; synthetic data is never production acceptance."""
import copy
import json
import math
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from factory_core.refs import FactoryError, read_json, reference
from factory_core.state import checkpoint, latest, load_design
from ui.experience import KINDS, capture, contract, evaluate, frame_result, genre, shape
from ui.readiness import feedback, validate_checkpoint
from ui.tests import experience_fixture as fixtures
from ui.tests import test_ui_design as base
ROOT = base.ROOT
from ui.visual import comparison_bundles, seal_capture, visual_packet, render_media


class ExperienceTests(unittest.TestCase):
    write = base.UiDesignTests.write
    setUp = base.UiDesignTests.setUp
    artifacts = base.UiDesignTests.artifacts
    ui_design = base.UiDesignTests.ui_design
    authorized_gameplay = base.UiDesignTests.authorized_gameplay
    authorize = base.UiDesignTests.authorize
    req = base.UiDesignTests.req
    authorize_ui = base.UiDesignTests.authorize_ui

    def fresh(self):
        self.authorized_gameplay()
        design, ref = self.ui_design()
        value = fixtures.attach(self, design, ref)
        return design, ref, value

    def measured(self, kind, parameters, elements, **frame):
        sample = dict(frame_id=0, time_ms=0, image={}, elements=elements, overlays_complete=True)
        sample.update(frame)
        return frame_result(dict(kind=kind, parameters=parameters), sample, [100, 100])[0]

    def test_schema_rejects_nan_bool_unknown_and_duplicates(self):
        for value in [dict(viewport=[True, 100]), dict(viewport=[math.nan, 100]), dict(rogue=1)]:
            capture_value = fixtures.bundle(self)
            capture_value.update(value)
            with self.assertRaises(FactoryError):
                capture(self.roots, capture_value)
        value = fixtures.bundle(self)
        value["frames"][0]["elements"] *= 2
        with self.assertRaisesRegex(FactoryError, "duplicate"):
            capture(self.roots, value)

    def test_pairing_same_row_and_legal_group(self):
        params = dict(pairs=[dict(value="number", attribute="sword")], layout="SAME_ROW", tolerance_px=2, group_element=None)
        rows = [fixtures.element("number", [10, 30, 10, 10]), fixtures.element("sword", [10, 10, 10, 10])]
        self.assertEqual(self.measured("PAIRING", params, rows), "FAIL")
        rows[1]["bounds"][1] = 30
        self.assertEqual(self.measured("PAIRING", params, rows), "PASS")
        rows[1]["bounds"][1] = 10
        rows.append(fixtures.element("group", [0, 0, 40, 50]))
        params.update(layout="GROUPED", group_element="group")
        self.assertEqual(self.measured("PAIRING", params, rows), "PASS")

    def test_zone_uses_actual_bounds_not_labels(self):
        params = dict(element_id="global-action", zone_element="chrome")
        rows = [fixtures.element("global-action", [10, 10, 10, 10]), fixtures.element("chrome", [0, 80, 100, 20])]
        self.assertEqual(self.measured("ZONE", params, rows), "FAIL")
        rows[0]["bounds"][1] = 85
        self.assertEqual(self.measured("ZONE", params, rows), "PASS")

    def test_rule_color_does_not_ban_decorative_pixels(self):
        params = dict(reserved=[dict(role="type", color=[1, 0, 0, 1])], element_roles={"line": "direction"}, tolerance=0.01)
        item = fixtures.element("line"); item["color"] = [1, 0, 0, 1]
        self.assertEqual(self.measured("COLOR", params, [item]), "FAIL")
        item["color"] = None
        self.assertEqual(self.measured("COLOR", params, [item]), "UNVERIFIABLE")
        item["color"] = [0.3, 0.3, 0.3, 1]
        self.assertEqual(self.measured("COLOR", params, [item]), "PASS")

    def test_primary_anchor_disabled_and_missing(self):
        params = dict(element_id="next", flow_id="round", anchor=[0.5, 0.5], tolerance=0.05)
        item = fixtures.element("next")
        self.assertEqual(self.measured("PRIMARY", params, [item]), "PASS")
        item["enabled"] = False
        self.assertEqual(self.measured("PRIMARY", params, [item]), "FAIL")
        self.assertEqual(self.measured("PRIMARY", params, []), "UNVERIFIABLE")
        item["enabled"] = True; item["bounds"][1] = 0
        self.assertEqual(self.measured("PRIMARY", params, [item]), "FAIL")

    def test_contextual_repetition_can_be_valid(self):
        params = dict(fact_id="xp", canonical_element="status", repeat_reason=None)
        rows = [fixtures.element("status"), fixtures.element("button")]
        for item in rows: item["fact_ids"] = ["xp"]
        self.assertEqual(self.measured("REDUNDANCY", params, rows), "FAIL")
        params["repeat_reason"] = "Comparison requires local current value next to the price."
        self.assertEqual(self.measured("REDUNDANCY", params, rows), "PASS")
        params["repeat_reason"] = None; rows[1]["fact_ids"] = ["xp-price"]
        self.assertEqual(self.measured("REDUNDANCY", params, rows), "PASS")

    def test_density_crossings_and_incomplete_inventory(self):
        params = dict(overlay_group="targets", max_concurrent=3, max_crossings=0)
        rows = [fixtures.element("one"), fixtures.element("two")]
        for item in rows: item["overlay_group"] = "targets"
        rows[0]["points"] = [[0, 0], [100, 100]]
        rows[1]["points"] = [[100, 0], [0, 100]]
        self.assertEqual(self.measured("DENSITY", params, rows), "FAIL")
        self.assertEqual(self.measured("DENSITY", params, rows, overlays_complete=False), "UNVERIFIABLE")
        rows[1]["points"] = [[0, 10], [90, 100]]
        self.assertEqual(self.measured("DENSITY", params, rows), "PASS")
        rows = [fixtures.element("self-crossing")]
        rows[0].update(overlay_group="targets", points=[[0, 0], [90, 90], [0, 90], [90, 0]])
        self.assertEqual(self.measured("DENSITY", params, rows), "FAIL")

    def test_goal_needs_next_threshold_and_reward_not_just_count(self):
        params = {key:dict(fact_id=key, element_id=key) for key in ("current", "threshold", "reward")}
        rows = [fixtures.element(key) for key in params]
        for item in rows: item["fact_ids"] = [item["element_id"]]
        self.assertEqual(self.measured("GOAL", params, rows[:1]), "UNVERIFIABLE")
        self.assertEqual(self.measured("GOAL", params, rows), "PASS")
        rows[-1]["visible"] = False
        self.assertEqual(self.measured("GOAL", params, rows), "FAIL")

    def test_every_frame_matters_and_preview_is_not_runtime(self):
        design, ref, value = self.fresh()
        sample = fixtures.bundle(self)
        second = copy.deepcopy(sample["frames"][0]); second.update(frame_id=1, time_ms=16)
        second["elements"][0]["enabled"] = False
        sample["frames"].append(second)
        cap = self.write("evidence/runtime.json", sample)
        result = evaluate(self.roots, value, [cap])
        self.assertEqual(result["results"][0]["status"], "FAIL")
        result = evaluate(self.roots, value, value["design_captures"])
        self.assertEqual(result["results"][0]["status"], "UNVERIFIABLE")
        result = evaluate(self.roots, value, value["design_captures"], archival=True)
        self.assertEqual(result["status"], "UI_RETROSPECTIVE_AUDIT")
        self.assertFalse(result["authority"])

    def test_capture_shape_viewport_order_and_hash_are_bound(self):
        sample = fixtures.bundle(self)
        sample["viewport"] = [200, 100]
        with self.assertRaisesRegex(FactoryError, "dimensions"):
            capture(self.roots, sample)
        sample = fixtures.bundle(self)
        sample["frames"].append(copy.deepcopy(sample["frames"][0]))
        sample["frames"][1]["frame_id"] = 1
        with self.assertRaisesRegex(FactoryError, "time ordered"):
            capture(self.roots, sample)
        sample = fixtures.bundle(self)
        (self.game / sample["frames"][0]["image"]["path"]).write_bytes(b"altered")
        with self.assertRaises(FactoryError): capture(self.roots, sample)

    def test_runtime_requires_available_commit_and_typed_consumed_build(self):
        sample = fixtures.bundle(self)
        sample["game_revision"] = "b" * 40
        with self.assertRaisesRegex(FactoryError, "available immutable"):
            capture(self.roots, sample)
        sample = fixtures.bundle(self)
        fake = self.write("evidence/not-a-build.txt", "Unrelated note, not a source manifest.\n")
        sample.update(build_artifact=fake, build_id=fake["sha256"])
        with self.assertRaises(FactoryError): capture(self.roots, sample)

    def test_contract_reuses_ids_and_cannot_defer_must_know_to_human(self):
        design, ref, value = self.fresh()
        self.assertEqual(contract(self.roots, design), value)
        value["probes"][0]["fact_ids"] = ["fact.first-target"]
        design["ui"]["experience"] = self.write(design["ui"]["experience"]["path"], value)
        design["artifacts"][-1] = design["ui"]["experience"]
        with self.assertRaisesRegex(FactoryError, "MUST_KNOW|probe fact assignments"):
            contract(self.roots, design)

    def test_legacy_readable_but_new_transition_requires_contract(self):
        self.authorized_gameplay()
        design, ref = self.ui_design()
        load_design(self.roots, ref)
        validate_checkpoint(self.roots, dict(stage="AUTHORIZED"), design)
        with self.assertRaisesRegex(FactoryError, "experience contract"):
            validate_checkpoint(self.roots, dict(stage="DESIGN_COMPLETE"), design, new_transition=True)

    def test_new_freeze_cannot_omit_objective_feedback(self):
        design, ref, value = self.fresh()
        self.write("design/ui/unit-one/feedback/earlier.json", dict(schema_version="ui_feedback.v1", findings=[]))
        with self.assertRaisesRegex(FactoryError, "existing objective feedback"):
            validate_checkpoint(self.roots, dict(stage="DESIGN_COMPLETE"), design, new_transition=True)
        relocated = self.write("design/ui/unit-one/revision-two/EXPERIENCE.json", value)
        design["artifacts"][-1] = relocated
        design["ui"]["experience"] = relocated
        with self.assertRaisesRegex(FactoryError, "existing objective feedback"):
            validate_checkpoint(self.roots, dict(stage="DESIGN_COMPLETE"), design, new_transition=True)

    def test_first_pass_discrimination_preserves_array_and_scalar_exports(self):
        from ui.readiness import first_pass_refs
        refs = [fixtures.write_bytes(self, f"evidence/{index}.json", raw) for index, raw in enumerate((b'[1,2,3]', b'5', b'{"not":"a visual pass"}'))]
        self.assertEqual(first_pass_refs(self.roots, refs), [])

    def test_readiness_stage_rejects_arbitrary_pass_file(self):
        design, ref, value = self.fresh()
        receipt = self.write(value["receipt_path"], dict(status="PASS"))
        with self.assertRaises(FactoryError):
            validate_checkpoint(self.roots, dict(stage="EVIDENCE_READY", design=ref, artifacts=[receipt]), design)

    def test_visual_packet_excludes_telemetry_and_probes(self):
        design, ref, value = self.fresh()
        packet = visual_packet(self.roots, ref, design)
        shape(packet, "visual_packet")
        self.assertNotIn("fact.first-target", json.dumps(packet))
        self.assertEqual(packet["captures"][0]["path"], "evidence/preview.png")

    def test_genre_detects_absent_features_but_does_not_authorize_them(self):
        profile = read_json(ROOT / "ui/profiles/auto_battler.v1.json")
        value = dict(profile="auto_battler.v1", reason=None, items=[dict(item_id=item["item_id"], disposition="PRESENT", rationale="Synthetic existing state.") for item in profile["items"]])
        genre(value, ROOT)
        value["items"][1]["disposition"] = "UPSTREAM_REQUIRED"
        with self.assertRaisesRegex(FactoryError, "owning design"): genre(value, ROOT)
        value["items"].pop()
        with self.assertRaisesRegex(FactoryError, "incomplete"): genre(value, ROOT)

    def test_media_comparison_refuses_different_states(self):
        before = self.write("evidence/before.json", fixtures.bundle(self, name="before"))
        after_body = fixtures.bundle(self, name="after"); after_body["state_id"] = "other"
        after = self.write("evidence/after.json", after_body)
        with self.assertRaisesRegex(FactoryError, "state_id"): comparison_bundles(self.roots, before, after)

    def test_contact_sheet_and_gif_preserve_originals(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("optional Pillow not installed")
        before = fixtures.bundle(self, name="before")
        after = fixtures.bundle(self, name="after")
        extra = copy.deepcopy(after["frames"][0]); extra.update(frame_id=1, time_ms=60)
        extra["image"] = fixtures.write_bytes(self, "evidence/second.png", fixtures.png(color=(200, 180, 160)))
        after["frames"].append(extra)
        original = (self.game / before["frames"][0]["image"]["path"]).read_bytes()
        refs = render_media(self.roots, [before, after], "evidence/media", "example")
        self.assertEqual({Path(ref["path"]).suffix for ref in refs}, {".png", ".gif"})
        with Image.open(self.game / next(ref["path"] for ref in refs if ref["path"].endswith(".gif"))) as image:
            self.assertEqual(image.n_frames, 2)
        self.assertEqual((self.game / before["frames"][0]["image"]["path"]).read_bytes(), original)

    def test_decision_view_is_checked_projection_not_new_approval(self):
        from ui.visual import decision_view
        design, ref, value = self.fresh()
        with self.assertRaisesRegex(FactoryError, "reviewed checkpoint"):
            decision_view(self.roots, ref, design)
        self.authorize_ui(ref, design)
        view = decision_view(self.roots, ref, design)
        self.assertEqual(view["full_view"]["design"], ref)
        self.assertIn("approval_action", view["full_view"])
        self.assertIn("no baseline is implied", view["html"])
        self.assertIn("Full checked", view["html"])
        self.assertFalse(view["authority"])

    def test_capture_cli_is_explicit_confined_and_nonoverwriting(self):
        raw = fixtures.bundle(self)
        raw["schema_version"] = "ui_capture_export.v1"
        for frame in raw["frames"]: frame["image_path"] = frame.pop("image")["path"]
        raw_ref = self.write("evidence/raw.json", raw)
        args = [sys.executable, str(ROOT / "ui/ui_design.py"), "capture", "--game-repo", str(self.game), "--raw", raw_ref["path"], "--output", "evidence/sealed.json"]
        first = subprocess.run(args, text=True, capture_output=True)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        before = (self.game / "evidence/sealed.json").read_bytes()
        self.assertNotEqual(subprocess.run(args, capture_output=True).returncode, 0)
        self.assertEqual((self.game / "evidence/sealed.json").read_bytes(), before)
        args[-1] = "../escape.json"
        self.assertNotEqual(subprocess.run(args, capture_output=True).returncode, 0)

    def test_feedback_cannot_disappear_downgrade_or_claim_unretsted_repair(self):
        design, ref, value = self.fresh()
        row = dict(finding_id="issue", source=value["design_captures"][0], observation_id="0", problem="Cannot associate value.", player_cost="Wrong purchase.", severity="BLOCKING", disposition="REPAIRED", owner="AI_DIRECTOR", rationale="Synthetic fix.", retest=[], revisit=None, supersedes=None, authorization=None)
        old = self.write("design/ui/unit-one/feedback/old.json", dict(schema_version="ui_feedback.v1", findings=[row]))
        value["feedback_inputs"] = [old]
        data = dict(schema_version="ui_feedback.v1", findings=[])
        with self.assertRaisesRegex(FactoryError, "prior findings"): feedback(self.roots, design, value, ref, data)
        row = copy.deepcopy(row); row["supersedes"] = old
        data["findings"] = [row]
        with self.assertRaisesRegex(FactoryError, "issue"): feedback(self.roots, design, value, ref, data)
        row.update(disposition="ACCEPT_RESIDUAL", revisit="Next beta")
        with self.assertRaisesRegex(FactoryError, "nonblocking"): feedback(self.roots, design, value, ref, data)
        row["severity"] = "NON_BLOCKING"
        with self.assertRaisesRegex(FactoryError, "original problem"): feedback(self.roots, design, value, ref, data)

    def test_director_residual_requires_real_delegation(self):
        design, ref, value = self.fresh()
        row = dict(finding_id="polish", source=value["design_captures"][0], observation_id="0", problem="Slightly busy.", player_cost="Optional attention cost.", severity="NON_BLOCKING", disposition="ACCEPT_RESIDUAL", owner="AI_DIRECTOR", rationale="Core decisions unaffected.", retest=[], revisit="Next layout change", supersedes=None, authorization=None)
        data = dict(schema_version="ui_feedback.v1", findings=[row])
        with self.assertRaisesRegex(FactoryError, "delegated"): feedback(self.roots, design, value, ref, data)
        with patch("factory_core.authorship.mode", return_value="CLOSED_BETA"), patch("factory_core.authorship.delegation", return_value=dict(seats=["INTERNAL_PLAYTEST_VERDICT"])):
            self.assertIn("polish", feedback(self.roots, design, value, ref, data))


if __name__ == "__main__":
    unittest.main()
