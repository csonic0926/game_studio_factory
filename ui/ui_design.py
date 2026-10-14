"""UI Design capability (ui/docs/UI_DESIGN_CAPABILITY.md): make UI correct, not pretty.

A `ui` design starts only from solid gameplay and binds four game-owned artifacts:
the Player Information Model (what the player must, may and must not know), the
Attention and Motion Plan (what draws the eye, when, for how long), the Screen
Contracts (where each fact lives and how every input answers) and the Verification
Plan (mechanical, blind comprehension and USER playtest layers, never merged).

This module checks only what is mechanical: the entry gate on the gameplay
authority, structural completeness and cross-coverage of the artifacts, and the
exact-build mechanical report. Whether the facts are the right facts and the plan
leads the eye well stays with the two reviewers, blind observation and the USER.

CLI:
  python3 ui/ui_design.py check  --game-repo <GAME> --design <design json>
  python3 ui/ui_design.py report --game-repo <GAME> --design <design json> --report <report json>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

FACTORY = Path(__file__).resolve().parents[1]
if str(FACTORY) not in sys.path:
    sys.path.insert(0, str(FACTORY))

from factory_core.refs import FactoryError, fail, read_json, resolve_ref  # noqa: E402

BINDING_KEYS = {"gameplay_checkpoint", "information_model", "attention_plan", "screen_contracts", "verification_plan"}
BINDING_OPTIONAL = {"rules_model_absent_reason"}
NEEDS = ("MUST_KNOW", "ON_DEMAND", "MAY_KNOW", "FORBIDDEN")
CHANNELS = ("PERSISTENT", "DISCLOSED", "TRANSIENT_CUE", "EXPLANATION")
MOMENTS = ("BEFORE_DECISION", "DURING_RESOLUTION", "AFTER_OUTCOME", "ALWAYS")
CLOCKS = ("REAL_TIME", "GAME_SPEED")
COLLISIONS = ("REPLACE", "WAIT", "MERGE", "DROP", "STACK")
GAMEPLAY_CAPABILITIES = ("studio", "gameplay")
AUTHORIZED_OR_LATER = ("AUTHORIZED", "PRODUCING", "EVIDENCE_READY", "COMPLETE")
VERSIONS = {"information_model": "ui_information_model.v1", "attention_plan": "ui_attention_plan.v1",
            "screen_contracts": "ui_screen_contracts.v1", "verification_plan": "ui_verification_plan.v1"}
REPORT_VERSION = "ui_mechanical_report.v1"


# ---------------------------------------------------------------- small shape helpers

def _shape(value, required, optional=(), where="ui"):
    if not isinstance(value, dict):
        fail("INVALID_UI_DESIGN", f"{where} must be an object")
    missing = set(required) - set(value)
    extra = set(value) - set(required) - set(optional)
    if missing or extra:
        fail("INVALID_UI_DESIGN", f"{where}: missing {sorted(missing)} unexpected {sorted(extra)}")


def _text(value, where):
    if not isinstance(value, str) or not value.strip():
        fail("INVALID_UI_DESIGN", f"{where} must be non-empty text")
    return value


def _list(value, where, allow_empty=False):
    if not isinstance(value, list) or (not value and not allow_empty):
        fail("INVALID_UI_DESIGN", f"{where} must be a {'list' if allow_empty else 'non-empty list'}")
    return value


def _ids(items, key, where):
    seen = set()
    for item in items:
        identity = _text(item.get(key), f"{where}.{key}")
        if identity in seen:
            fail("INVALID_UI_DESIGN", f"{where}: duplicate {key} {identity}")
        seen.add(identity)
    return seen


def _positive(value, where):
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        fail("INVALID_UI_DESIGN", f"{where} must be a positive integer")
    return value


def _game_ref(ref, where):
    if not isinstance(ref, dict) or ref.get("scope") != "game":
        fail("INVALID_UI_DESIGN", f"{where} must be a game-owned reference")
    return ref


# ---------------------------------------------------------------- entry gate

def entry_gate(roots: dict, design: dict) -> dict:
    """UI design starts only from solid gameplay: a current AUTHORIZED (or later) gameplay
    or studio checkpoint with no unresolved questions, an executable rules check (or an
    explicit reason there is no rules model) and an existing interaction contract.
    Returns the gameplay design."""
    from factory_core.state import latest
    binding = design["ui"]
    checkpoint_ref = _game_ref(binding["gameplay_checkpoint"], "ui.gameplay_checkpoint")
    if checkpoint_ref not in design["inputs"]:
        fail("UI_GATE_GAMEPLAY", "the gameplay checkpoint must be a sealed design input")
    checkpoint = read_json(resolve_ref(roots, checkpoint_ref))
    if checkpoint.get("schema_version") != "factory_checkpoint.v2" or checkpoint.get("capability") not in GAMEPLAY_CAPABILITIES:
        fail("UI_GATE_GAMEPLAY", "the UI design must start from a gameplay or studio checkpoint")
    if checkpoint.get("stage") not in AUTHORIZED_OR_LATER:
        fail("UI_GATE_GAMEPLAY", f"gameplay must be AUTHORIZED before UI design (stage {checkpoint.get('stage')})")
    current, _digest = latest(roots["game"], checkpoint["task_id"])
    if current is None or current.get("design") != checkpoint.get("design") or current.get("stage") not in AUTHORIZED_OR_LATER:
        fail("UI_GATE_GAMEPLAY", "the bound gameplay checkpoint is no longer the current authorized design for its task")
    if checkpoint.get("unresolved"):
        fail("UI_GATE_GAMEPLAY", f"gameplay has unresolved questions: {checkpoint['unresolved']}")
    gameplay = read_json(resolve_ref(roots, checkpoint["design"]))
    if "rules_check" not in gameplay:
        reason = binding.get("rules_model_absent_reason")
        if not isinstance(reason, str) or not reason.strip():
            fail("UI_GATE_RULES", "the gameplay design binds no rules check; state rules_model_absent_reason or run gameplay/rules_check.py first")
    elif "rules_model_absent_reason" in binding:
        fail("UI_GATE_RULES", "rules_model_absent_reason is only for gameplay without a rules check")
    return gameplay


def contract_ids(contract: dict) -> tuple[set, set]:
    """Beat ids and interaction step ids of a player-facing interaction contract."""
    beats, steps = set(), set()
    for beat in contract.get("playable_beats", []):
        beats.add(beat.get("beat_id"))
        for step in beat.get("interaction_sequence", []):
            steps.add(step.get("step_id"))
    beats.discard(None)
    steps.discard(None)
    return beats, steps


# ---------------------------------------------------------------- artifacts

def check_information_model(model: dict, contract_beats: set, contract_steps: set) -> dict:
    _shape(model, {"schema_version", "objective_id", "interaction_contract", "rules", "decisions", "facts"}, (), "information_model")
    if model["schema_version"] != VERSIONS["information_model"]:
        fail("INVALID_UI_DESIGN", f"information_model.schema_version must be {VERSIONS['information_model']}")
    rules = _list(model["rules"], "information_model.rules")
    for rule in rules:
        _shape(rule, {"rule_id", "source", "statement", "fact_ids"}, (), "information_model.rules[]")
        _text(rule["source"], "rule.source")
        _text(rule["statement"], "rule.statement")
        _list(rule["fact_ids"], f"rule {rule.get('rule_id')}.fact_ids")
    _ids(rules, "rule_id", "information_model.rules")
    facts = _list(model["facts"], "information_model.facts")
    for fact in facts:
        _shape(fact, {"fact_id", "statement", "source", "need", "serves", "when", "channel", "canonical_wording"},
               ("guard",), "information_model.facts[]")
        where = f"fact {fact.get('fact_id')}"
        _text(fact["statement"], f"{where}.statement")
        _text(fact["source"], f"{where}.source")
        if fact["need"] not in NEEDS:
            fail("INVALID_UI_DESIGN", f"{where}.need must be one of {NEEDS}")
        if fact["need"] == "FORBIDDEN":
            _text(fact.get("guard"), f"{where}.guard (what could leak it and why it does not)")
            if fact["channel"] is not None:
                fail("INVALID_UI_DESIGN", f"{where}: a FORBIDDEN fact has no channel (null)")
        else:
            if "guard" in fact:
                fail("INVALID_UI_DESIGN", f"{where}: only FORBIDDEN facts carry a guard")
            if fact["channel"] not in CHANNELS:
                fail("INVALID_UI_DESIGN", f"{where}.channel must be one of {CHANNELS}")
        for beat in _list(fact["serves"], f"{where}.serves"):
            if beat not in contract_beats:
                fail("UI_COVERAGE", f"{where} serves unknown contract beat {beat}")
        for moment in _list(fact["when"], f"{where}.when"):
            if moment not in MOMENTS:
                fail("INVALID_UI_DESIGN", f"{where}.when must use {MOMENTS}")
        _text(fact["canonical_wording"], f"{where}.canonical_wording")
    fact_ids = _ids(facts, "fact_id", "information_model.facts")
    by_id = {fact["fact_id"]: fact for fact in facts}
    used = set()
    for rule in rules:
        unknown = set(rule["fact_ids"]) - fact_ids
        if unknown:
            fail("UI_COVERAGE", f"rule {rule['rule_id']} maps to unknown facts {sorted(unknown)}")
        if all(by_id[f]["need"] == "FORBIDDEN" for f in rule["fact_ids"]):
            fail("UI_COVERAGE", f"rule {rule['rule_id']} needs at least one fact the player may see")
        used.update(rule["fact_ids"])
    decisions = _list(model["decisions"], "information_model.decisions")
    for decision in decisions:
        _shape(decision, {"step_id", "fact_ids"}, (), "information_model.decisions[]")
        for fact_id in _list(decision["fact_ids"], f"decision {decision.get('step_id')}.fact_ids"):
            if fact_id not in fact_ids:
                fail("UI_COVERAGE", f"decision {decision['step_id']} needs unknown fact {fact_id}")
            if by_id[fact_id]["need"] == "FORBIDDEN":
                fail("UI_COVERAGE", f"decision {decision['step_id']} cannot depend on FORBIDDEN fact {fact_id}")
        used.update(decision["fact_ids"])
    decided = _ids(decisions, "step_id", "information_model.decisions")
    if decided != contract_steps:
        fail("UI_COVERAGE", f"every contract step lists the facts it needs: missing {sorted(contract_steps - decided)} unknown {sorted(decided - contract_steps)}")
    orphan = fact_ids - used
    if orphan:
        fail("UI_COVERAGE", f"facts tied to no rule or decision: {sorted(orphan)}")
    wordings = {}
    for fact in facts:
        wordings.setdefault(fact["canonical_wording"], []).append(fact["fact_id"])
    clashes = {w: ids for w, ids in wordings.items() if len(ids) > 1}
    if clashes:
        fail("UI_TERMINOLOGY", f"one wording names several facts: {clashes}")
    return by_id


def check_attention_plan(plan: dict, facts: dict, contract_beats: set) -> dict:
    _shape(plan, {"schema_version", "protected_elements", "events", "beats"}, (), "attention_plan")
    if plan["schema_version"] != VERSIONS["attention_plan"]:
        fail("INVALID_UI_DESIGN", f"attention_plan.schema_version must be {VERSIONS['attention_plan']}")
    protected = _list(plan["protected_elements"], "attention_plan.protected_elements")
    for element in protected:
        _shape(element, {"element_id", "description"}, (), "protected_elements[]")
        _text(element["description"], "protected element description")
    protected_ids = _ids(protected, "element_id", "attention_plan.protected_elements")
    events = _list(plan["events"], "attention_plan.events")
    cued = set()
    for event in events:
        _shape(event, {"event_id", "source", "fact_ids", "cue", "max_latency_ms", "min_readable_ms", "clock",
                       "skip_behavior", "max_concurrent_per_object", "priority", "on_collision", "never_covers"},
               ("max_wait_ms",), "attention_plan.events[]")
        where = f"event {event.get('event_id')}"
        _text(event["source"], f"{where}.source")
        _text(event["cue"], f"{where}.cue")
        _text(event["skip_behavior"], f"{where}.skip_behavior")
        latency = _positive(event["max_latency_ms"], f"{where}.max_latency_ms")
        _positive(event["min_readable_ms"], f"{where}.min_readable_ms")
        _positive(event["max_concurrent_per_object"], f"{where}.max_concurrent_per_object")
        if not isinstance(event["priority"], int) or isinstance(event["priority"], bool):
            fail("INVALID_UI_DESIGN", f"{where}.priority must be an integer")
        if event["clock"] not in CLOCKS:
            fail("INVALID_UI_DESIGN", f"{where}.clock must be one of {CLOCKS}")
        if event["on_collision"] not in COLLISIONS:
            fail("INVALID_UI_DESIGN", f"{where}.on_collision must be one of {COLLISIONS}")
        if event["on_collision"] in ("WAIT", "MERGE"):
            wait = _positive(event.get("max_wait_ms"), f"{where}.max_wait_ms (a waiting cue needs a bound)")
            if wait > latency:
                fail("UI_ATTENTION_UNBOUNDED", f"{where}: max_wait_ms {wait} exceeds max_latency_ms {latency}")
        elif "max_wait_ms" in event:
            fail("INVALID_UI_DESIGN", f"{where}: max_wait_ms applies only to WAIT or MERGE")
        for fact_id in _list(event["fact_ids"], f"{where}.fact_ids"):
            if fact_id not in facts:
                fail("UI_COVERAGE", f"{where} carries unknown fact {fact_id}")
            if facts[fact_id]["need"] == "FORBIDDEN":
                fail("UI_LEAK", f"{where} would show FORBIDDEN fact {fact_id}")
        for element in _list(event["never_covers"], f"{where}.never_covers", allow_empty=True):
            if element not in protected_ids:
                fail("UI_COVERAGE", f"{where} protects unknown element {element}")
        cued.update(event["fact_ids"])
    event_ids = _ids(events, "event_id", "attention_plan.events")
    missing = {f for f, fact in facts.items() if fact["channel"] == "TRANSIENT_CUE"} - cued
    if missing:
        fail("UI_COVERAGE", f"transient-cue facts with no event: {sorted(missing)}")
    beats = _list(plan["beats"], "attention_plan.beats")
    for beat in beats:
        _shape(beat, {"beat_id", "first_focus", "calm_until"}, (), "attention_plan.beats[]")
        _text(beat["first_focus"], f"beat {beat.get('beat_id')}.first_focus")
        _text(beat["calm_until"], f"beat {beat.get('beat_id')}.calm_until")
    planned = _ids(beats, "beat_id", "attention_plan.beats")
    if planned != contract_beats:
        fail("UI_COVERAGE", f"every contract beat names its first focus: missing {sorted(contract_beats - planned)} unknown {sorted(planned - contract_beats)}")
    return {"events": event_ids, "protected": protected_ids}


def check_screen_contracts(contracts: dict, facts: dict, attention: dict, contract_beats: set, contract_steps: set) -> dict:
    _shape(contracts, {"schema_version", "surfaces"}, (), "screen_contracts")
    if contracts["schema_version"] != VERSIONS["screen_contracts"]:
        fail("INVALID_UI_DESIGN", f"screen_contracts.schema_version must be {VERSIONS['screen_contracts']}")
    surfaces = _list(contracts["surfaces"], "screen_contracts.surfaces")
    placed = {}
    inputs, previews, steps_answered = set(), set(), set()
    for surface in surfaces:
        _shape(surface, {"surface_id", "beats", "layers", "placements", "density", "inputs", "terminology"}, (), "surfaces[]")
        sid = surface["surface_id"]
        where = f"surface {sid}"
        for beat in _list(surface["beats"], f"{where}.beats"):
            if beat not in contract_beats:
                fail("UI_COVERAGE", f"{where} names unknown beat {beat}")
        layers = _list(surface["layers"], f"{where}.layers")
        orders = []
        for layer in layers:
            _shape(layer, {"layer_id", "order", "protects"}, (), f"{where}.layers[]")
            if not isinstance(layer["order"], int) or isinstance(layer["order"], bool):
                fail("INVALID_UI_DESIGN", f"{where} layer order must be an integer")
            orders.append(layer["order"])
            for element in _list(layer["protects"], f"{where} layer {layer['layer_id']}.protects", allow_empty=True):
                if element not in attention["protected"]:
                    fail("UI_COVERAGE", f"{where} layer protects unknown element {element}")
        if len(set(orders)) != len(orders):
            fail("INVALID_UI_DESIGN", f"{where}: layer orders must be distinct")
        layer_ids = _ids(layers, "layer_id", f"{where}.layers")
        density = surface["density"]
        _shape(density, {"persistent_item_ceiling", "disclosure_controls"}, (), f"{where}.density")
        _positive(density["persistent_item_ceiling"], f"{where}.density.persistent_item_ceiling")
        controls = _list(density["disclosure_controls"], f"{where}.density.disclosure_controls", allow_empty=True)
        for placement in _list(surface["placements"], f"{where}.placements"):
            _shape(placement, {"fact_id", "channel", "layer_id", "size_class"}, (), f"{where}.placements[]")
            fact_id = placement["fact_id"]
            if fact_id not in facts:
                fail("UI_COVERAGE", f"{where} places unknown fact {fact_id}")
            if facts[fact_id]["need"] == "FORBIDDEN":
                fail("UI_LEAK", f"{where} places FORBIDDEN fact {fact_id}")
            if placement["channel"] != facts[fact_id]["channel"]:
                fail("UI_COVERAGE", f"{where} shows {fact_id} through {placement['channel']}, the model says {facts[fact_id]['channel']}")
            if placement["layer_id"] not in layer_ids:
                fail("UI_COVERAGE", f"{where} places {fact_id} on unknown layer {placement['layer_id']}")
            _text(placement["size_class"], f"{where} {fact_id}.size_class")
            if placement["channel"] == "DISCLOSED" and not controls:
                fail("UI_COVERAGE", f"{where} discloses {fact_id} but names no disclosure control")
            placed.setdefault(fact_id, set()).update(surface["beats"])
        for item in _list(surface["inputs"], f"{where}.inputs", allow_empty=True):
            _shape(item, {"input_id", "step_ids", "response", "persistent_change"}, ("preview", "preview_equality_check"), f"{where}.inputs[]")
            iid = f"{sid}:{_text(item['input_id'], f'{where} input_id')}"
            if iid in inputs:
                fail("INVALID_UI_DESIGN", f"duplicate input {iid}")
            inputs.add(iid)
            _text(item["response"], f"{iid}.response (every input answers visibly)")
            _text(item["persistent_change"], f"{iid}.persistent_change")
            for step in _list(item["step_ids"], f"{iid}.step_ids", allow_empty=True):
                if step not in contract_steps:
                    fail("UI_COVERAGE", f"{iid} names unknown contract step {step}")
                steps_answered.add(step)
            if "preview" in item:
                _text(item["preview"], f"{iid}.preview")
                _text(item.get("preview_equality_check"), f"{iid}.preview_equality_check (a preview must equal what it previews)")
                previews.add(iid)
            elif "preview_equality_check" in item:
                fail("INVALID_UI_DESIGN", f"{iid}: preview_equality_check without a preview")
        for term in _list(surface["terminology"], f"{where}.terminology", allow_empty=True):
            _shape(term, {"fact_id", "wording"}, (), f"{where}.terminology[]")
            if term["fact_id"] not in facts:
                fail("UI_TERMINOLOGY", f"{where} terminology names unknown fact {term['fact_id']}")
            if term["wording"] != facts[term["fact_id"]]["canonical_wording"]:
                fail("UI_TERMINOLOGY", f"{where} words {term['fact_id']} as {term['wording']!r}, canonical is {facts[term['fact_id']]['canonical_wording']!r}")
    _ids(surfaces, "surface_id", "screen_contracts.surfaces")
    for fact_id, fact in facts.items():
        if fact["need"] in ("MUST_KNOW", "ON_DEMAND"):
            reachable = placed.get(fact_id, set())
            if not reachable:
                fail("UI_COVERAGE", f"{fact['need']} fact {fact_id} is placed on no surface")
            unreached = set(fact["serves"]) - reachable
            if unreached:
                fail("UI_COVERAGE", f"{fact_id} is not on a surface of the beats it serves: {sorted(unreached)}")
    unanswered = contract_steps - steps_answered
    if unanswered:
        fail("UI_COVERAGE", f"contract steps with no input or response on any surface: {sorted(unanswered)}")
    return {"inputs": inputs, "previews": previews}


def check_verification_plan(plan: dict, facts: dict, attention: dict, screens: dict) -> set:
    _shape(plan, {"schema_version", "mechanical_checks", "blind_chains", "user_playtest_signals"}, (), "verification_plan")
    if plan["schema_version"] != VERSIONS["verification_plan"]:
        fail("INVALID_UI_DESIGN", f"verification_plan.schema_version must be {VERSIONS['verification_plan']}")
    checks = _list(plan["mechanical_checks"], "verification_plan.mechanical_checks")
    covered = set()
    for check in checks:
        _shape(check, {"check_id", "kind", "covers", "method"}, (), "mechanical_checks[]")
        _text(check["kind"], "check.kind")
        _text(check["method"], f"check {check.get('check_id')}.method")
        covered.update(_list(check["covers"], f"check {check.get('check_id')}.covers"))
    check_ids = _ids(checks, "check_id", "verification_plan.mechanical_checks")
    known = set(facts) | attention["events"] | screens["inputs"]
    unknown = covered - known
    if unknown:
        fail("UI_COVERAGE", f"mechanical checks cover unknown ids {sorted(unknown)}")
    missing = (attention["events"] | screens["previews"]) - covered
    if missing:
        fail("UI_COVERAGE", f"every event and every preview needs a mechanical check: {sorted(missing)}")
    must_know = {f for f, fact in facts.items() if fact["need"] == "MUST_KNOW"}
    observed = set()
    for chain in _list(plan["blind_chains"], "verification_plan.blind_chains"):
        _shape(chain, {"chain_id", "must_know_fact_ids", "hypotheses"}, (), "blind_chains[]")
        for fact_id in _list(chain["must_know_fact_ids"], f"chain {chain.get('chain_id')}.must_know_fact_ids"):
            if fact_id not in must_know:
                fail("UI_COVERAGE", f"chain {chain['chain_id']} lists {fact_id}, which is not a MUST_KNOW fact")
            observed.add(fact_id)
        for hypothesis in _list(chain["hypotheses"], f"chain {chain.get('chain_id')}.hypotheses", allow_empty=True):
            _shape(hypothesis, {"hypothesis_id", "statement", "falsifier", "fallback"}, (), "hypotheses[]")
            for field in ("statement", "falsifier", "fallback"):
                _text(hypothesis[field], f"hypothesis {hypothesis.get('hypothesis_id')}.{field}")
    signals = _list(plan["user_playtest_signals"], "verification_plan.user_playtest_signals")
    for signal in signals:
        _shape(signal, {"signal_id", "question", "fact_ids"}, (), "user_playtest_signals[]")
        _text(signal["question"], f"signal {signal.get('signal_id')}.question")
        for fact_id in _list(signal["fact_ids"], f"signal {signal.get('signal_id')}.fact_ids", allow_empty=True):
            if fact_id not in facts:
                fail("UI_COVERAGE", f"signal {signal['signal_id']} names unknown fact {fact_id}")
            observed.add(fact_id)
    _ids(signals, "signal_id", "verification_plan.user_playtest_signals")
    unverified = must_know - observed
    if unverified:
        fail("UI_COVERAGE", f"MUST_KNOW facts no blind chain or USER signal verifies: {sorted(unverified)}")
    return check_ids


def load_artifacts(roots: dict, design: dict) -> dict:
    binding = design["ui"]
    loaded = {}
    for name in VERSIONS:
        ref = _game_ref(binding[name], f"ui.{name}")
        if ref not in design["artifacts"]:
            fail("INVALID_UI_DESIGN", f"ui.{name} must be one of the design's sealed artifacts")
        loaded[name] = read_json(resolve_ref(roots, ref))
    return loaded


def validate_artifacts(roots: dict, design: dict, gameplay: dict) -> dict:
    loaded = load_artifacts(roots, design)
    model = loaded["information_model"]
    contract_ref = _game_ref(model.get("interaction_contract"), "information_model.interaction_contract")
    if contract_ref not in design["inputs"]:
        fail("UI_GATE_CONTRACT", "the interaction contract must be a sealed UI design input")
    if contract_ref["path"] not in {r["path"] for r in gameplay["inputs"] + gameplay["artifacts"]}:
        fail("UI_GATE_CONTRACT", "the interaction contract must be the one the authorized gameplay design binds")
    contract = read_json(resolve_ref(roots, contract_ref))
    beats, steps = contract_ids(contract)
    if not beats or not steps:
        fail("UI_GATE_CONTRACT", "the interaction contract has no playable beats or interaction steps")
    facts = check_information_model(model, beats, steps)
    attention = check_attention_plan(loaded["attention_plan"], facts, beats)
    screens = check_screen_contracts(loaded["screen_contracts"], facts, attention, beats, steps)
    checks = check_verification_plan(loaded["verification_plan"], facts, attention, screens)
    return {"facts": len(facts), "events": len(attention["events"]), "inputs": len(screens["inputs"]),
            "previews": len(screens["previews"]), "mechanical_checks": sorted(checks)}


def validate_design(roots: dict, design: dict) -> dict:
    """Design gate for capability `ui` (called from factory_core.state.load_design)."""
    if design["capability"] != "ui":
        if "ui" in design:
            fail("INVALID_UI_DESIGN", "the ui binding belongs only to a ui design")
        return {}
    if "ui" not in design:
        fail("INVALID_UI_DESIGN", "a ui design binds its gameplay checkpoint and four artifacts under 'ui'")
    _shape(design["ui"], BINDING_KEYS, BINDING_OPTIONAL, "ui")
    gameplay = entry_gate(roots, design)
    return validate_artifacts(roots, design, gameplay)


# ---------------------------------------------------------------- exact-build mechanical report

def validate_report(roots: dict, design: dict, report: dict) -> dict:
    """The mechanical layer on one exact build: every planned check ran and passed."""
    _shape(report, {"schema_version", "game_revision", "ui_design", "checks"}, (), "mechanical report")
    if report["schema_version"] != REPORT_VERSION:
        fail("INVALID_UI_REPORT", f"schema_version must be {REPORT_VERSION}")
    _text(report["game_revision"], "report.game_revision")
    if read_json(resolve_ref(roots, _game_ref(report["ui_design"], "report.ui_design"))) != design:
        fail("INVALID_UI_REPORT", "the report must bind this exact ui design")
    planned = set(validate_design(roots, design)["mechanical_checks"])
    results = _list(report["checks"], "report.checks")
    seen = {}
    for result in results:
        _shape(result, {"check_id", "status", "evidence"}, (), "report.checks[]")
        if result["status"] not in ("PASS", "FAIL"):
            fail("INVALID_UI_REPORT", "check status is PASS or FAIL")
        resolve_ref(roots, _game_ref(result["evidence"], f"check {result['check_id']}.evidence"))
        seen[result["check_id"]] = result["status"]
    missing = planned - set(seen)
    if missing:
        fail("UI_REPORT_INCOMPLETE", f"planned checks with no result: {sorted(missing)}")
    failed = sorted(c for c, status in seen.items() if status != "PASS")
    if failed:
        fail("UI_CHECK_FAILED", f"mechanical checks failed: {failed}")
    return {"status": "UI_MECHANICAL_PASS", "checks": len(seen), "game_revision": report["game_revision"]}


# ---------------------------------------------------------------- blind comprehension (Studio comparison)

FACT_STATUSES = ("UNDERSTOOD", "NOT_UNDERSTOOD", "NOT_SHOWN")


def validate_fact_observations(repo: Path, value, sealed_attempt_ids: set, errors: list) -> None:
    """A comparison's judgment of one blind chain against the UI design: every MUST_KNOW fact
    the verification plan assigns to the chain, judged from the observer's own fields.
    Acceptance needs every fact UNDERSTOOD (errors are appended, the Studio validator style)."""
    from factory_core.refs import confined, sha
    if not isinstance(value, dict) or set(value) != {"ui_design", "chain_id", "facts"}:
        errors.append("comparison review.ui_fact_observations must be {ui_design, chain_id, facts}")
        return
    ref = value["ui_design"]
    try:
        if not isinstance(ref, dict) or set(ref) != {"path", "sha256"} or sha(confined(repo, ref["path"])) != ref["sha256"]:
            raise FactoryError("STALE", "ui design ref")
        design = read_json(confined(repo, ref["path"]))
        plan = read_json(confined(repo, design["ui"]["verification_plan"]["path"]))
    except (FactoryError, KeyError, TypeError):
        errors.append("comparison review.ui_fact_observations.ui_design must reference the current UI design")
        return
    chains = {chain.get("chain_id"): chain for chain in plan.get("blind_chains", [])}
    chain = chains.get(value["chain_id"])
    if chain is None:
        errors.append(f"comparison review.ui_fact_observations.chain_id {value['chain_id']!r} is not a blind chain of the UI design")
        return
    facts = value["facts"] if isinstance(value["facts"], list) else []
    judged = []
    for item in facts:
        if not isinstance(item, dict) or set(item) != {"fact_id", "status", "observation_citations", "rationale"}:
            errors.append("comparison review.ui_fact_observations.facts[] must be {fact_id, status, observation_citations, rationale}")
            continue
        judged.append(item["fact_id"])
        if item["status"] not in FACT_STATUSES:
            errors.append(f"ui fact {item['fact_id']} status must be one of {FACT_STATUSES}")
        elif item["status"] != "UNDERSTOOD":
            errors.append(f"ui fact {item['fact_id']} was {item['status']} by the blind observer; the UI design is not accepted")
        citations = item["observation_citations"]
        if not isinstance(citations, list) or not citations or not set(citations) <= sealed_attempt_ids:
            errors.append(f"ui fact {item['fact_id']} must cite sealed blind attempts")
        if not isinstance(item["rationale"], str) or not item["rationale"].strip():
            errors.append(f"ui fact {item['fact_id']} needs a rationale")
    if sorted(judged) != sorted(chain["must_know_fact_ids"]) or len(judged) != len(set(judged)):
        errors.append("comparison review.ui_fact_observations must judge exactly the chain's MUST_KNOW facts")


# ---------------------------------------------------------------- production plan binding

def authorized_ui_checkpoints(game: Path, gameplay_checkpoint_path: str) -> dict:
    """Current AUTHORIZED (or later) ui checkpoints whose design starts from this gameplay
    checkpoint: {checkpoint path: sha256}."""
    from factory_core.refs import sha
    from factory_core.state import latest
    found = {}
    root = game / "design/factory/checkpoints"
    if not root.is_dir():
        return found
    for task_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        try:
            record, _digest = latest(game, task_dir.name)
        except FactoryError:
            continue
        if not record or record.get("capability") != "ui" or record.get("stage") not in AUTHORIZED_OR_LATER:
            continue
        design = read_json(game / record["design"]["path"])
        if design.get("ui", {}).get("gameplay_checkpoint", {}).get("path") != gameplay_checkpoint_path:
            continue
        path = sorted(task_dir.glob("*.json"))[-1]
        relative = path.relative_to(game).as_posix()
        found[relative] = sha(path)
    return found


def plan_binding_errors(game: Path, gameplay_checkpoint_path: str, bindings: list) -> list:
    """UI plans of a gameplay that has an authorized UI design must cite that design's
    current checkpoint; a cited checkpoint must be one of them."""
    errors = []
    authorized = authorized_ui_checkpoints(game, gameplay_checkpoint_path)
    for label, binding in bindings:
        cited = binding.ui_design_checkpoint
        if cited is None:
            if binding.touches_ui and authorized:
                errors.append(f"{label} touches UI; cite the authorized UI design checkpoint in ui_impact.ui_design_checkpoint ({sorted(authorized)})")
            continue
        if not isinstance(cited, dict) or set(cited) != {"path", "sha256"}:
            errors.append(f"{label}.ui_impact.ui_design_checkpoint must be {{path, sha256}}")
            continue
        if authorized.get(cited["path"]) != cited["sha256"]:
            errors.append(f"{label}.ui_impact.ui_design_checkpoint is not a current authorized UI design for this gameplay")
    return errors


def _roots(game: str) -> dict:
    from factory_core.refs import game_root
    return {"game": game_root(game, FACTORY), "factory": FACTORY}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("check", "report"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--game-repo", required=True)
        cmd.add_argument("--design", required=True, help="game-relative path of the ui design JSON")
        if name == "report":
            cmd.add_argument("--report", required=True, help="game-relative path of the mechanical report JSON")
    args = parser.parse_args(argv)
    try:
        roots = _roots(args.game_repo)
        from factory_core.refs import confined
        design = read_json(confined(roots["game"], args.design))
        if args.command == "check":
            if design.get("capability") != "ui":
                fail("INVALID_UI_DESIGN", "not a ui design")
            result = {"status": "UI_DESIGN_CONSISTENT", **validate_design(roots, design)}
        else:
            result = validate_report(roots, design, read_json(confined(roots["game"], args.report)))
    except FactoryError as error:
        print(json.dumps({"status": "BLOCKED", "code": error.code, "message": str(error)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
