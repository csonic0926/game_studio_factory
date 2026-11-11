"""Consume UI evidence at real lifecycle boundaries without minting USER acceptance."""
from __future__ import annotations

import json

from factory_core.refs import confined, fail, read_json, reference, resolve_ref
from ui.experience import contract, evaluate, game_file, indexed, shape


def feedback_directory(roots, design):
    """Upstream objective identity, never the relocatable experience file path."""
    from factory_core.state import identifier
    checkpoint = read_json(game_file(roots, design["ui"]["gameplay_checkpoint"]))
    gameplay = read_json(game_file(roots, checkpoint["design"]))
    identity = identifier(gameplay["gameplay"]["objective_id"])
    return confined(roots["game"], f"design/ui/{identity}/feedback")


def first_pass_refs(roots, refs):
    result = []
    for ref in refs:
        if ref["path"].endswith(".json"):
            try:
                data = json.loads(game_file(roots, ref).read_text(encoding="utf-8"))
            except (ValueError, OSError) as error:
                fail("INVALID_JSON", str(error))
            if isinstance(data, dict) and data.get("schema_version") == "ui_visual_first_pass.v1":
                result.append(ref)
    return result


def visual_passes(roots, record, design, refs):
    """Both same-design reviewers seal observations before the reviewed boundary."""
    from ui.visual import visual_packet
    if len(refs) != 2:
        fail("UI_VISUAL_REVIEW_REQUIRED", "exactly two capture-first records required")
    expected = {read_json(game_file(roots, ref))["role"]: read_json(game_file(roots, ref))["reviewer_context_id"] for ref in record["reviews"]}
    packet = visual_packet(roots, record["design"], design)
    roles = set()
    for ref in refs:
        first = shape(read_json(game_file(roots, ref)), "first_pass")
        if (read_json(game_file(roots, first["packet"])) != packet or
                expected.get(first["role"]) != first["reviewer_context_id"] or first["role"] in roles):
            fail("UI_VISUAL_REVIEW_REQUIRED", "capture-first records must match both actual independent design reviewers")
        roles.add(first["role"])
    if roles != {"intent_experience", "completeness_project"}:
        fail("UI_VISUAL_REVIEW_REQUIRED", "both required reviewer roles must inspect the captures")


def feedback(roots, design, value, current_ref, data):
    """Disposition is append-only and mode-aware; a residual never overrides gates."""
    from factory_core.authorship import mode, delegation
    shape(data, "feedback")
    rows = indexed(data["findings"], "finding_id")
    prior = {}
    for ref in value["feedback_inputs"]:
        old = shape(read_json(game_file(roots, ref)), "feedback")
        for identity, finding in indexed(old["findings"], "finding_id").items():
            if identity in prior:
                # Inputs are ordered history: later revisions must preserve the observation.
                for field in ("source", "observation_id", "problem", "player_cost", "severity"):
                    if prior[identity][field] != finding[field]:
                        fail("UI_FEEDBACK_REWRITTEN", f"changed original observation {identity}")
            prior[identity] = finding
    if set(prior) - set(rows):
        fail("UI_FEEDBACK_DROPPED", "prior findings must receive an explicit disposition")
    for identity, finding in rows.items():
        game_file(roots, finding["source"])
        if identity in prior:
            if finding["supersedes"] not in value["feedback_inputs"]:
                fail("UI_FEEDBACK_REWRITTEN", "updated findings must link their prior record")
            linked = read_json(game_file(roots, finding["supersedes"]))
            if not any(row["finding_id"] == identity for row in linked["findings"]):
                fail("UI_FEEDBACK_REWRITTEN", "supersedes must actually contain this finding")
            for field in ("source", "observation_id", "problem", "player_cost", "severity"):
                if finding[field] != prior[identity][field]:
                    fail("UI_FEEDBACK_REWRITTEN", "disposition cannot edit the original problem or severity")
        if finding["disposition"] == "OPEN":
            fail("UI_FEEDBACK_OPEN", identity)
        if finding["disposition"] == "REPAIRED":
            if not finding["retest"]:
                fail("UI_RETEST_REQUIRED", identity)
            for ref in finding["retest"]:
                game_file(roots, ref)
        if finding["disposition"] == "NOT_APPLICABLE" and finding["severity"] == "BLOCKING":
            fail("UI_HARD_GATE", "a failed required contract needs repair/new design, not an in-place downgrade")
        if finding["disposition"] == "ACCEPT_RESIDUAL":
            if finding["severity"] != "NON_BLOCKING" or not finding["revisit"]:
                fail("UI_HARD_GATE", "only nonblocking risks with a revisit trigger may be retained")
            if finding["owner"] == "AI_DIRECTOR":
                if mode(roots) != "CLOSED_BETA" or "INTERNAL_PLAYTEST_VERDICT" not in delegation(roots).get("seats", []):
                    fail("UI_DELEGATION_REQUIRED", "residual acceptance needs the actual delegated internal verdict seat")
            else:
                authorization = finding["authorization"]
                if authorization is None:
                    fail("UI_USER_RULING_REQUIRED", "USER risk acceptance needs the exact raw submission")
                source = read_json(game_file(roots, authorization))
                action = f"ACCEPT_UI_RISK {identity} {finding['source']['sha256']} {current_ref['sha256']}"
                if source.get("role") != "user" or source.get("content") != action:
                    fail("UI_USER_RULING_REQUIRED", "not the exact USER risk acceptance action")
    return rows


def chain(roots, design, record, wrapper, readiness, value):
    """Use the existing runtime/blind/comparison validator; no weaker UI-only clone."""
    from ui.ui_design import entry_gate
    from gameplay.v2 import validate_design, legacy
    from factory_core.state import project
    from studio.player_surface import validate_runtime_player_surface_chain
    shape(wrapper, "runtime_chain")
    gameplay = entry_gate(roots, design)
    domain = gameplay["gameplay"]
    upstream = read_json(game_file(roots, design["ui"]["gameplay_checkpoint"]))
    upstream_reviews = [read_json(resolve_ref(roots, ref)) for ref in upstream["reviews"]]
    intent_ref = next(ref for ref, review in zip(upstream["reviews"], upstream_reviews) if review["role"] == "intent_experience")
    validated = validate_design(roots, gameplay)
    interaction = validated["contract"]
    refs = wrapper["player_facing_evidence"]
    comparison = read_json(game_file(roots, {"scope": "game", **refs["comparison_review"]}))
    runtime = read_json(game_file(roots, {"scope": "game", **refs["runtime_interaction_evidence"]}))
    reviews = [read_json(game_file(roots, ref)) for ref in record["reviews"]]
    contexts = {design["author_context_id"], gameplay["author_context_id"],
                *(review["reviewer_context_id"] for review in reviews + upstream_reviews)}
    producer = runtime.get("producer_context_id")
    if producer not in wrapper["producer_context_ids"] or design["author_context_id"] not in wrapper["producer_context_ids"]:
        fail("UI_CONTEXT_MISMATCH", "record all actual producers, including the continuing UI author")
    errors = []
    scenarios = indexed(value["scenarios"], "scenario_id")
    locales = {scenarios[sid]["locale"] for probe in value["probes"] if probe["chain_id"] == wrapper["chain_id"] for sid in probe["scenario_ids"]}
    if len(locales) != 1:
        fail("UI_LOCALE_MISMATCH", "each UI comprehension chain must test one explicit reviewed locale")
    validate_runtime_player_surface_chain(roots["game"], refs,
        project_id=project(roots["game"])["project_id"], unit_id=domain["objective_id"],
        game_revision=readiness["game_revision"], build_id=readiness["build_id"],
        factory_revision=runtime.get("factory_revision"),
        expected_contract_ref=legacy(domain["interaction_contract"]),
        expected_contract_review_ref=legacy(intent_ref), expected_card_ref=legacy(upstream["design"]),
        expected_system_ref=legacy(domain["system"]), expected_beat_ids=interaction["beat_ids"],
        expected_answer_bearing_design_ids=interaction["answer_bearing_design_ids"],
        expected_target_locale=next(iter(locales)),
        expected_player_entry_knowledge=interaction["player_entry_knowledge"],
        hypothesis_ids=set(domain["hypothesis_ids"]), design_context_ids=contexts,
        production_context_ids=set(wrapper["producer_context_ids"]),
        acceptance_reviewer_context_id=design["author_context_id"], errors=errors)
    ui_facts = comparison.get("ui_fact_observations")
    if not ui_facts or ui_facts.get("ui_design") != legacy(readiness["design"]):
        errors.append("comparison must bind this exact UI design and its required facts")
    elif ui_facts.get("chain_id") != wrapper["chain_id"]:
        errors.append("comparison chain id differs from UI verification plan")
    if errors:
        fail("UI_COMPREHENSION_REJECTED", "; ".join(errors))
    blind = read_json(game_file(roots, {"scope": "game", **refs["blind_observation"]}))
    return comparison, blind


def validate(roots, record, design, ref, *, complete=False):
    """Recompute observations and consume independent outcomes for one exact UI build."""
    from ui.ui_design import validate_report
    from factory_core.authorship import mode, delegation
    from factory_core.director import validate_note
    value = contract(roots, design)
    if value is None:
        fail("UI_EXPERIENCE_REQUIRED", "legacy design needs a new reviewed experience contract for new readiness")
    acceptance = shape(read_json(game_file(roots, ref)), "acceptance") if complete else None
    readiness_ref = acceptance["readiness"] if acceptance is not None else ref
    if acceptance is not None and (ref not in record["artifacts"] or ref["path"] not in design["production_scope"]):
        fail("UI_EVIDENCE_MISMATCH", "append-only acceptance must be an authorized checkpoint artifact")
    data = shape(read_json(game_file(roots, readiness_ref)), "readiness")
    if readiness_ref not in record["artifacts"] or data["design"] != record["design"] or readiness_ref["path"] != value["receipt_path"]:
        fail("UI_EVIDENCE_MISMATCH", "readiness must bind the exact design and authorized receipt path")
    measured = evaluate(roots, value, data["captures"])
    if measured["status"] != "UI_MEASUREMENTS_PASS":
        fail("UI_MEASUREMENTS_BLOCKED", "required measurements failed or are unverifiable")
    for capture_ref in data["captures"]:
        bundle = read_json(game_file(roots, capture_ref))
        if bundle["origin"] != "RUNTIME" or any(bundle[key] != data[key] for key in ("game_revision", "build_id")):
            fail("UI_EVIDENCE_MISMATCH", "all evidence must identify the same actual runtime build")
    report = read_json(game_file(roots, data["mechanical_report"]))
    validate_report(roots, design, report)
    if report["schema_version"] != "ui_mechanical_report.v2" or any(report[key] != data[key] for key in ("game_revision", "build_id")):
        fail("UI_EVIDENCE_MISMATCH", "new UI readiness needs a v2 mechanical report on this exact build, not merely the same revision")
    visual_passes(roots, record, design, data["visual_first_passes"])
    if any(ref not in record["artifacts"] for ref in data["visual_first_passes"]):
        fail("UI_VISUAL_REVIEW_REQUIRED", "readiness must preserve the checkpoint's capture-first records")
    feedback_path = game_file(roots, data["feedback"])
    if feedback_path.parent != feedback_directory(roots, design) or data["feedback"]["path"] not in design["production_scope"]:
        fail("UI_FEEDBACK_DROPPED", "new feedback must land in the authorized canonical objective inventory")
    rows = feedback(roots, design, value, record["design"], shape(read_json(feedback_path), "feedback"))
    comparisons = indexed(data["comparisons"], "chain_id")
    probes = indexed(value["probes"], "probe_id")
    if set(comparisons) != {probe["chain_id"] for probe in probes.values()}:
        fail("UI_COMPREHENSION_REQUIRED", "all and only planned chains are required")
    chains = {}
    for identity, item in comparisons.items():
        wrapper = read_json(game_file(roots, item["runtime_input"]))
        if wrapper.get("chain_id") != identity:
            fail("UI_CONTEXT_MISMATCH", "chain wrapper identity differs")
        chains[identity] = chain(roots, design, record, wrapper, data, value)
        blind_ref = {"scope": "game", **wrapper["player_facing_evidence"]["blind_observation"]}
        for index, problem in enumerate(chains[identity][1]["observation"]["lost_or_passive_points"]):
            matched = [row for row in rows.values() if row["source"] == blind_ref and row["observation_id"] == f"lost.{index}"]
            if len(matched) != 1 or matched[0]["problem"] != problem:
                fail("UI_FEEDBACK_DROPPED", "every blind lost/passive point needs its own preserved disposition, even if owned elsewhere")
    outcome_reviews = [shape(read_json(game_file(roots, outcome_ref)), "outcome_review") for outcome_ref in data["outcome_reviews"]]
    outcomes = {}
    for outcome in outcome_reviews:
        if outcome["ui_design"] != record["design"] or outcome["chain_id"] not in chains:
            fail("UI_COMPREHENSION_REQUIRED", "outcome review must bind current design and a planned chain")
        comparison, blind = chains[outcome["chain_id"]]
        if outcome["reviewer_context_id"] != comparison["reviewer_context_id"]:
            fail("UI_CONTEXT_MISMATCH", "the informed comparer judges probe outcomes")
        attempts = indexed(blind["observation"]["interaction_observations"], "attempt_id")
        coverage = indexed(outcome["observation_coverage"], "attempt_id")
        if set(coverage) != set(attempts):
            fail("UI_FEEDBACK_DROPPED", "every sealed attempt must be considered for unexpected UI escapes")
        for row in coverage.values():
            if not set(row["finding_ids"]) <= set(rows):
                fail("UI_FEEDBACK_DROPPED", "unexpected findings must join the disposition record")
        for row in outcome["results"]:
            identity = row["probe_id"]
            key = (identity, row["scenario_id"])
            if key in outcomes or identity not in probes or row["chain_id"] != outcome["chain_id"] or probes[identity]["chain_id"] != outcome["chain_id"] or row["scenario_id"] not in probes[identity]["scenario_ids"]:
                fail("UI_COMPREHENSION_REQUIRED", "duplicate, unknown or misbound probe outcome")
            if row["status"] != "SUPPORTED" or not set(row["attempt_ids"]) <= set(attempts):
                fail("UI_COMPREHENSION_REJECTED", "required outcomes need actual supported sealed attempts")
            images = {frame["image"]["sha256"] for cap in data["captures"]
                      for bundle in [read_json(game_file(roots, cap))] if bundle["scenario_id"] == row["scenario_id"]
                      for frame in bundle["frames"]}
            cited_images = {image["sha256"] for identity in row["attempt_ids"] for image in attempts[identity]["surface_artifacts"]}
            if not images & cited_images:
                fail("UI_COMPREHENSION_REQUIRED", "probe must cite the actual scenario surface, not another state")
            outcomes[key] = row
    if set(outcomes) != {(identity, sid) for identity, probe in probes.items() for sid in probe["scenario_ids"]}:
        fail("UI_COMPREHENSION_REQUIRED", "every required probe needs an independent outcome")
    for first_ref in data["visual_first_passes"]:
        first = read_json(game_file(roots, first_ref))
        for index, finding in enumerate(first["findings"]):
            matched = [row for row in rows.values() if row["source"] == first_ref and row["observation_id"] == str(index)]
            if len(matched) != 1:
                fail("UI_FEEDBACK_DROPPED", "capture-first observations must have dispositions, including unknowns")
            row = matched[0]
            if row["problem"] != finding["observation"] or row["player_cost"] != finding["player_cost"] or finding["classification"] == "BLOCKING" and row["severity"] != "BLOCKING":
                fail("UI_FEEDBACK_REWRITTEN", "disposition cannot rewrite/downgrade the sealed visual observation")
    for identity, finding in rows.items():
        if finding["disposition"] == "REPAIRED":
            for retest_ref in finding["retest"]:
                retest = shape(read_json(game_file(roots, retest_ref)), "retest")
                if retest["finding_id"] != identity or retest["design"] != record["design"]:
                    fail("UI_RETEST_REQUIRED", "retest must bind this finding and current design")
                scenario_ids = [retest["failure_scenario_id"], *retest["variant_scenario_ids"]]
                if len(set(scenario_ids)) != len(scenario_ids) or any(ref not in data["captures"] for ref in retest["captures"]):
                    fail("UI_RETEST_REQUIRED", "original and unseen variant must use current measured captures")
                sampled = [read_json(game_file(roots, cap)) for cap in retest["captures"]]
                if {sample["scenario_id"] for sample in sampled} != set(scenario_ids):
                    fail("UI_RETEST_REQUIRED", "all original/variant states need actual measured captures")
                states = {(sample["state_id"], sample["locale"], tuple(sample["viewport"])) for sample in sampled}
                pixels = {sample["frames"][0]["image"]["sha256"] for sample in sampled}
                if len(states) != len(scenario_ids) or len(pixels) != len(scenario_ids):
                    fail("UI_RETEST_REQUIRED", "renamed identical states/frames are not unseen variants")
                if not set(scenario_ids) <= {sid for _, sid in outcomes}:
                    fail("UI_RETEST_REQUIRED", "retest needs independently supported original/variant outcomes")
    note = None
    if mode(roots) in ("AUTONOMOUS", "CLOSED_BETA"):
        if data["director_note"] is None:
            fail("DIRECTOR_NOTE_REQUIRED", "Director must play, judge and decide, not defer to a later USER")
        note = validate_note(roots, data["director_note"], record["task_id"], record["design"])
        if note["decision"] != "CONTINUE" or note["boundary"] != "USER_HANDOFF":
            fail("DIRECTOR_DID_NOT_CONTINUE", "UI readiness needs the Director's handoff judgment")
        if note["author_context_id"] != design["author_context_id"]:
            fail("UI_CONTEXT_MISMATCH", "the continuing orchestrator owns the Director's judgment, not another scoped reviewer")
        evidence = [item for play in note["played"] for item in play["evidence"]]
        if not any(item in data["captures"] for item in evidence):
            fail("DIRECTOR_DID_NOT_PLAY", "Director play must cite this build's actual UI surface")
        if any(row["disposition"] == "ACCEPT_RESIDUAL" for row in rows.values()) and data["feedback"] not in evidence:
            fail("UI_FEEDBACK_DROPPED", "Director handoff must consume the exact retained-risk inventory")
    status = "UI_EVIDENCE_READY"
    if complete:
        verdict = acceptance["verdict"]
        source = read_json(game_file(roots, verdict["source"]))
        if verdict["owner"] == "AI_DIRECTOR":
            if mode(roots) != "CLOSED_BETA" or "INTERNAL_PLAYTEST_VERDICT" not in delegation(roots).get("seats", []):
                fail("UI_DELEGATION_REQUIRED", "not delegated to the Director")
            if verdict["source"] != data["director_note"] or source != note:
                fail("UI_VERDICT_REQUIRED", "AI internal verdict must cite its checked Director note")
            status = "UI_INTERNAL_READY"
        else:
            action = f"ACCEPT_UI {record['design']['sha256']} {data['game_revision']} {data['build_id']}"
            if source.get("role") != "user" or source.get("content") != action:
                fail("UI_USER_RULING_REQUIRED", "exact raw USER UI verdict required")
            status = "UI_SPECIALIST_ACCEPTED"
    return {"status": status, "gameplay_accepted": False, "delivery_eligible": False,
            "human_experience_proven": False, "measurements": measured}


def validate_checkpoint(roots, record, design, *, new_transition=False):
    if design.get("capability") != "ui" or design.get("schema_version") != "factory_design.v3":
        return
    value = contract(roots, design)
    if value is not None and record["stage"] in ("REVIEWED", "AUTHORIZED", "PRODUCING", "EVIDENCE_READY", "COMPLETE"):
        passes = first_pass_refs(roots, record["artifacts"])
        visual_passes(roots, record, design, passes)
        if new_transition:
            from factory_core.state import latest
            previous, _ = latest(roots["game"], record["task_id"])
            if previous and previous.get("design") == record["design"] and previous["stage"] in ("REVIEWED", "AUTHORIZED", "PRODUCING", "EVIDENCE_READY"):
                old = first_pass_refs(roots, previous["artifacts"])
                if old != passes:
                    fail("UI_VISUAL_REVIEW_REQUIRED", "carry the original sealed visual passes forward unchanged")
    if new_transition and record["stage"] != "DRAFT":
        if value is None:
            fail("UI_EXPERIENCE_REQUIRED", "new UI boundaries require a reviewed experience contract; historical reading is unchanged")
        if record["stage"] == "DESIGN_COMPLETE":
            # Discovery is bounded to the objective, never sibling games. Only a
            # new freeze requires newly received feedback in its input closure.
            for path in sorted(feedback_directory(roots, design).glob("*.json")):
                ref = reference(roots["game"], path.relative_to(roots["game"]).as_posix())
                if not any(prior["path"] == ref["path"] and prior["sha256"] == ref["sha256"] for prior in value["feedback_inputs"]):
                    fail("UI_FEEDBACK_DROPPED", "new design must bind existing objective feedback")
    if value is not None and record["stage"] in ("EVIDENCE_READY", "COMPLETE"):
        ref = reference(roots["game"], value["receipt_path"])
        if ref not in record["artifacts"]:
            fail("UI_EVIDENCE_REQUIRED", "checkpoint must include the typed exact-output UI receipt")
        validate(roots, record, design, ref)
