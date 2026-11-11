"""Real UI checkpoint consumers over synthetic existing Studio chains, not human proof."""
import copy
import unittest
from unittest.mock import patch

from factory_core.refs import FactoryError, read_json, reference
from factory_core.state import checkpoint, latest
from ui.readiness import validate
from ui.tests import test_experience as tests
from ui.tests import experience_fixture as fixtures

ROOT = tests.ROOT


class ReadinessTests(unittest.TestCase):
    setUp = tests.ExperienceTests.setUp
    write = tests.ExperienceTests.write
    artifacts = tests.ExperienceTests.artifacts
    ui_design = tests.ExperienceTests.ui_design
    authorized_gameplay = tests.ExperienceTests.authorized_gameplay
    authorize = tests.ExperienceTests.authorize
    req = tests.ExperienceTests.req
    authorize_ui = tests.ExperienceTests.authorize_ui
    fresh = tests.ExperienceTests.fresh

    def note(self, task_id, design_ref, boundary, evidence):
        directory = self.game / f"design/factory/director/{task_id}"
        number = len(list(directory.glob("*.json"))) + 1
        design = read_json(self.game / design_ref["path"])
        return self.write(f"design/factory/director/{task_id}/{number:06d}.json", dict(schema_version="factory_director_note.v1", task_id=task_id, design=design_ref,
            boundary=boundary, author_context_id=design["author_context_id"], played=[dict(method="Synthetic fixture play only", evidence=evidence, observations="No actual player or game result is claimed.")],
            fun_judgment="Synthetic test judgment.", biggest_risk="Unproven human experience.", case_against="Fixture is not a real game.", decision="CONTINUE", next="Test only.", calibration=[], written_at="2026-11-11T00:00:00Z"))

    def beta_authorize(self, design, ref, task_id):
        from factory_core.state import requirement_ids
        from ui.visual import visual_packet
        evidence = [self.write(f"evidence/{task_id}-fixture-play.txt", "Synthetic play witness only.\n")]
        passes = []
        if design["capability"] == "ui":
            packet = self.write("evidence/visual-packet.json", visual_packet(self.roots, ref, design))
            passes = [self.write(f"evidence/{role}-visual.json", dict(schema_version="ui_visual_first_pass.v1", packet=packet,
                reviewer_context_id=f"{task_id}-{role}", role=role, authority_read=False, findings=[], sealed_at="2026-11-11T00:00:00Z")) for role in ("intent_experience", "completeness_project")]
        def req(stage, previous=None, **extra):
            return dict(task_id=task_id, previous=previous, capability=design["capability"], task=design["task"], stage=stage,
                summary="Synthetic delegated beta fixture.", unresolved=[], artifacts=passes, design=ref, **extra)
        freeze = self.note(task_id, ref, "DESIGN_FREEZE", evidence)
        out = checkpoint(self.roots, req("DESIGN_COMPLETE", director_note=freeze))
        record, _ = latest(self.game, task_id)
        binding = record["dependencies"]
        reviews = [self.write(f"evidence/{task_id}-{role}.json", dict(schema_version="factory_review.v2", role=role, reviewer_context_id=f"{task_id}-{role}",
            fresh=True, peer_reviews_read=[], design=ref, dependency_fingerprint=binding["fingerprint"], verdict="PASS",
            findings={identity:dict(status="PASS", evidence=[ref], rationale="Synthetic protocol coverage.") for identity in requirement_ids(ROOT, design, role, "CLOSED_BETA")},
            source_coverage=[item["scope"] + ":" + item["path"] for item in binding["references"] if item["scope"] != "factory"], decision_coverage=[item["id"] for item in design["decisions"]])) for role in ("intent_experience", "completeness_project")]
        out = checkpoint(self.roots, req("REVIEWED", out["checkpoint"]["sha256"], reviews=reviews))
        approval = self.note(task_id, ref, "DESIGN_APPROVAL", evidence)
        ruling = self.write(f"evidence/{task_id}-ruling.json", dict(schema_version="factory_ruling.v2", owner="AI_DIRECTOR", decision="APPROVE", design=ref,
            dependency_fingerprint=binding["fingerprint"], director_note=approval, rationale="Synthetic delegated design approval, not USER."))
        return checkpoint(self.roots, req("AUTHORIZED", out["checkpoint"]["sha256"], reviews=reviews, ruling=ruling, director_note=approval))

    def ready(self, beta=False):
        from studio.tests.player_surface_fixture import write_runtime_chain
        from gameplay.v2 import validate_design, legacy
        from factory_core.state import project
        if beta:
            from factory_core.authorship import set_mode
            from factory_core.tests.test_authorship import AuthorshipModeTests
            raw = self.write("evidence/delegation.json", dict(role="user", content="Synthetic full delegation to internal closed beta."))
            set_mode(self.roots, "CLOSED_BETA", raw["path"], "Synthetic full delegation", "Synthetic game")
            self.decision_ids = [item["id"] for item in self.design["decisions"]]
            self.game_ref = lambda path: reference(self.game, path)
            self.rules_model = lambda: AuthorshipModeTests.rules_model(self)
            inquiry = AuthorshipModeTests.inquiry(self)
            self.design, self.design_ref = AuthorshipModeTests.covered(self, inquiry)
            out = self.beta_authorize(self.design, self.design_ref, "unit-one")
            self.gameplay_checkpoint = out["checkpoint"]
            design, ref = self.ui_design(reason=None)
            value = fixtures.attach(self, design, ref)
            authorized = self.beta_authorize(design, ref, "unit-one-ui")
        else:
            design, ref, value = self.fresh()
            authorized = self.authorize_ui(ref, design)
        record, _ = latest(self.game, "unit-one-ui")
        upstream = read_json(self.game / design["ui"]["gameplay_checkpoint"]["path"])
        gameplay = read_json(self.game / upstream["design"]["path"])
        validated = validate_design(self.roots, gameplay)
        domain = gameplay["gameplay"]
        intent = next(item for item in upstream["reviews"] if read_json(self.game / item["path"])["role"] == "intent_experience")
        sample = fixtures.bundle(self)
        refs = write_runtime_chain(self.game, self.game / "evidence/chain",
            project_id=project(self.game)["project_id"], unit_id=domain["objective_id"],
            game_revision=sample["game_revision"], build_id=sample["build_id"],
            factory_revision=validated["system"]["factory_revision"], contract_ref=legacy(domain["interaction_contract"]),
            contract_review_ref=legacy(intent), card_ref=legacy(upstream["design"]), system_ref=legacy(domain["system"]),
            beat_ids=sorted(validated["contract"]["beat_ids"]), hypothesis_ids=domain["hypothesis_ids"])
        # Existing chain fixtures use fake image bytes. Replace them with distinct
        # valid synthetic PNGs, then rebuild each dependent hash in order.
        for index, path in enumerate(sorted((self.game / "evidence/chain/player_surface").glob("*.png"))):
            path.write_bytes(fixtures.png(color=(index + 1, 70, 120)))
        for key in ("runtime_interaction_evidence", "blind_observation_input", "blind_observation", "comparison_review"):
            body = fixtures.rehash_tree(self, read_json(self.game / refs[key]["path"]))
            if key == "comparison_review":
                body["ui_fact_observations"] = dict(ui_design=legacy(ref), chain_id="chain.a", facts=[dict(fact_id=fact, status="UNDERSTOOD", observation_citations=["attempt.1"], rationale="Synthetic fixture, not real comprehension evidence.") for fact in value["probes"][0]["fact_ids"]])
            refs[key] = legacy(self.write(refs[key]["path"], body))
        runtime = read_json(self.game / refs["runtime_interaction_evidence"]["path"])
        sample["frames"][0]["image"] = dict(scope="game", **runtime["ordered_input_trace"][0]["frame_before"])
        cap = self.write("evidence/capture.json", sample)
        wrapper = self.write("evidence/chain-input.json", dict(schema_version="ui_runtime_chain.v1", chain_id="chain.a", player_facing_evidence=refs, producer_context_ids=[design["author_context_id"], runtime["producer_context_id"]]))
        blind = read_json(self.game / refs["blind_observation"]["path"])
        outcome = self.write("evidence/outcome.json", dict(schema_version="ui_outcome_review.v1", ui_design=ref, chain_id="chain.a", reviewer_context_id="player-surface-comparison-reviewer",
            results=[dict(probe_id="understand", chain_id="chain.a", scenario_id="decision", status="SUPPORTED", attempt_ids=["attempt.1"], rationale="Synthetic protocol fixture, not an actual usability result.")],
            observation_coverage=[dict(attempt_id=item["attempt_id"], finding_ids=[], rationale="Synthetic fixture has no reported escape.") for item in blind["observation"]["interaction_observations"]]))
        check_results = []
        for index, check in enumerate(read_json(self.game / design["ui"]["verification_plan"]["path"])["mechanical_checks"]):
            result = self.write(f"evidence/mechanical-{index}.json", dict(schema_version="ui_check_result.v1", check_id=check["check_id"],
                status="PASS", game_revision=sample["game_revision"], build_id=sample["build_id"], method=check["method"], evidence=[cap]))
            check_results.append(dict(check_id=check["check_id"], status="PASS", evidence=result))
        mechanical = self.write("evidence/mechanical.json", dict(schema_version="ui_mechanical_report.v2", game_revision=sample["game_revision"], ui_design=ref,
            build_id=sample["build_id"], build_artifact=sample["build_artifact"], checks=check_results))
        feedback = self.write("design/ui/unit-one/feedback/current.json", dict(schema_version="ui_feedback.v1", findings=[]))
        handoff = None
        if beta:
            production = self.note("unit-one-ui", ref, "PRODUCTION_START", [cap])
            checkpoint(self.roots, dict(task_id="unit-one-ui", previous=authorized["checkpoint"]["sha256"], capability="ui", task="ui_design", stage="PRODUCING",
                summary="Synthetic beta production.", unresolved=[], artifacts=record["artifacts"], design=ref, reviews=record["reviews"], ruling=record["ruling"], director_note=production))
            record, _ = latest(self.game, "unit-one-ui")
            handoff = self.note("unit-one-ui", ref, "USER_HANDOFF", [cap])
        data = dict(schema_version="ui_readiness.v1", design=ref, game_revision=sample["game_revision"], build_id=sample["build_id"], captures=[cap], mechanical_report=mechanical,
                    visual_first_passes=record["artifacts"], comparisons=[dict(chain_id="chain.a", runtime_input=wrapper)], outcome_reviews=[outcome], feedback=feedback, director_note=handoff)
        receipt = self.write(value["receipt_path"], data)
        record["artifacts"] = [*record["artifacts"], receipt]
        return design, ref, value, data, receipt, record

    def test_closed_beta_entire_ui_chain_without_daily_user_rulings(self):
        design, ref, value, data, receipt, record = self.ready(beta=True)
        previous = reference(self.game, "design/factory/checkpoints/unit-one-ui/000004.json")["sha256"]
        def req(stage, previous, **extra):
            return dict(task_id="unit-one-ui", previous=previous, capability="ui", task="ui_design", stage=stage,
                summary="Synthetic complete autonomous beta fixture.", unresolved=[], artifacts=record["artifacts"], design=ref, reviews=record["reviews"], ruling=record["ruling"], **extra)
        out = checkpoint(self.roots, req("EVIDENCE_READY", previous, director_note=data["director_note"]))
        accepted = self.write("design/ui/unit-one/ACCEPTANCE.json", dict(schema_version="ui_acceptance.v1", readiness=receipt,
            verdict=dict(owner="AI_DIRECTOR", source=data["director_note"], rationale="Synthetic internal beta judgment, not USER.")))
        record["artifacts"].append(accepted)
        out = checkpoint(self.roots, req("COMPLETE", out["checkpoint"]["sha256"], acceptance=accepted))
        self.assertEqual(out["stage"], "COMPLETE")
        result = validate(self.roots, record, design, accepted, complete=True)
        self.assertEqual(result["status"], "UI_INTERNAL_READY")
        self.assertFalse(result["delivery_eligible"])

    def test_real_chain_consumed_and_rejected_outcomes_block(self):
        design, ref, value, data, receipt, record = self.ready()
        self.assertEqual(validate(self.roots, record, design, receipt)["status"], "UI_EVIDENCE_READY")
        outcome = read_json(self.game / data["outcome_reviews"][0]["path"])
        outcome["results"][0]["status"] = "REJECTED"
        data["outcome_reviews"][0] = self.write(data["outcome_reviews"][0]["path"], outcome)
        receipt = self.write(receipt["path"], data)
        record["artifacts"][-1] = receipt
        with self.assertRaisesRegex(FactoryError, "supported sealed attempts"):
            validate(self.roots, record, design, receipt)

    def test_whole_checkpoint_chain_needs_typed_receipt_and_actual_user_verdict(self):
        design, ref, value, data, receipt, record = self.ready()
        def advance(stage, previous, **extra):
            return checkpoint(self.roots, dict(task_id="unit-one-ui", previous=previous, capability="ui", task="ui_design", stage=stage,
                summary="Synthetic UI lifecycle fixture.", unresolved=[], artifacts=record["artifacts"], design=ref, reviews=record["reviews"], ruling=record["ruling"], **extra))
        out = advance("PRODUCING", reference(self.game, "design/factory/checkpoints/unit-one-ui/000003.json")["sha256"])
        out = advance("EVIDENCE_READY", out["checkpoint"]["sha256"])
        with self.assertRaises(FactoryError):
            advance("COMPLETE", out["checkpoint"]["sha256"], acceptance=receipt)
        action = f"ACCEPT_UI {ref['sha256']} {data['game_revision']} {data['build_id']}"
        raw = self.write("evidence/user-ui-verdict.json", dict(role="user", content=action))
        accepted = self.write("design/ui/unit-one/ACCEPTANCE.json", dict(schema_version="ui_acceptance.v1", readiness=receipt,
            verdict=dict(owner="USER", source=raw, rationale="Synthetic test token, never a real USER verdict.")))
        record["artifacts"].append(accepted)
        out = advance("COMPLETE", out["checkpoint"]["sha256"], acceptance=accepted)
        self.assertEqual(out["stage"], "COMPLETE")
        # No evidence file was rewritten to append the later verdict.
        self.assertEqual(reference(self.game, receipt["path"]), receipt)

    def test_unplanned_observation_coverage_cannot_be_dropped(self):
        design, ref, value, data, receipt, record = self.ready()
        outcome = read_json(self.game / data["outcome_reviews"][0]["path"])
        outcome["observation_coverage"].pop()
        data["outcome_reviews"][0] = self.write(data["outcome_reviews"][0]["path"], outcome)
        receipt = self.write(receipt["path"], data)
        record["artifacts"][-1] = receipt
        with self.assertRaisesRegex(FactoryError, "every sealed attempt"):
            validate(self.roots, record, design, receipt)

    def test_unknown_probe_and_build_substitution_are_rejected(self):
        design, ref, value, data, receipt, record = self.ready()
        data["build_id"] = "f" * 64
        receipt = self.write(receipt["path"], data)
        record["artifacts"][-1] = receipt
        with self.assertRaisesRegex(FactoryError, "same actual runtime build"):
            validate(self.roots, record, design, receipt)

    def test_ui_internal_verdict_does_not_equal_user_or_baseline_acceptance(self):
        design, ref, value, data, receipt, record = self.ready()
        # This consumer test isolates a mode-selected handoff. Full mode switching
        # and Director authorization are separately covered by core tests.
        note = self.write("design/factory/director/unit-one-ui/000001.json", dict(schema_version="factory_director_note.v1", task_id="unit-one-ui", design=ref,
            boundary="USER_HANDOFF", author_context_id=design["author_context_id"], played=[dict(method="synthetic play fixture", evidence=data["captures"], observations="Fixture traces only; no real player.")],
            fun_judgment="Synthetic result.", biggest_risk="Human comprehension unproven.", case_against="No real play.", decision="CONTINUE", next="Synthetic test only.", calibration=[], written_at="2026-11-11T00:00:00Z"))
        data["director_note"] = note
        receipt = self.write(receipt["path"], data)
        record["artifacts"][-1] = receipt
        accepted = self.write("design/ui/unit-one/ACCEPTANCE.json", dict(schema_version="ui_acceptance.v1", readiness=receipt,
            verdict=dict(owner="AI_DIRECTOR", source=note, rationale="Synthetic delegated internal verdict.")))
        record["artifacts"].append(accepted)
        with self.assertRaisesRegex(FactoryError, "not delegated"):
            validate(self.roots, record, design, accepted, complete=True)
        with patch("factory_core.authorship.mode", return_value="CLOSED_BETA"), patch("factory_core.authorship.delegation", return_value=dict(seats=["INTERNAL_PLAYTEST_VERDICT"])):
            result = validate(self.roots, record, design, accepted, complete=True)
        self.assertEqual(result["status"], "UI_INTERNAL_READY")
        self.assertFalse(result["gameplay_accepted"])
        self.assertFalse(result["delivery_eligible"])
        self.assertFalse(result["human_experience_proven"])


if __name__ == "__main__":
    unittest.main()
