"""Per-idea inquiry records and the design's idea coverage.

An inquiry record keeps the substantive reasoning behind each game-design idea
a design relies on: why the player would care, how the mechanism produces its
consequence, what it costs, which alternatives were weighed, and what is evidence
versus assumption. It never proves that an idea is fun; it proves the inquiry
exists, is identifiable, and is bound to the exact design that relies on it.

Under the USER-selected AUTONOMOUS authorship mode the coverage is a hard gate:
every material design decision is either backed by ADOPTed inquired ideas or
explicitly classified as not a design idea, and no open question is left
without a disposition. COLLABORATIVE mode checks only the shape of whatever
coverage the author chose to record, because the USER is present to judge.
"""
from __future__ import annotations

from factory_core.refs import fail, read_json, resolve_ref

SCHEMA_VERSION = "idea_inquiry.v1"
JUDGMENTS = ("ADOPT", "REJECT", "OPEN")
DISPOSITIONS = {
    "OPEN": (),
    "ANSWERED": ("answer",),
    "HYPOTHESIS": ("falsification", "test_stage"),
    "DEFERRED": ("reason", "revisit"),
}
IDEA_TEXT_FIELDS = ("idea", "player_situation", "mechanism", "cost_or_tension", "reasons")
IDEA_AUTHORITIES = ("USER", "SOURCE", "AI_HYPOTHESIS")
COVERED_CAPABILITIES = ("studio", "gameplay")


def _text(value, where):
    if not isinstance(value, str) or not value.strip():
        fail("INVALID_IDEA_INQUIRY", f"{where}: nonempty text required")
    return value


def _texts(value, where):
    if not isinstance(value, list):
        fail("INVALID_IDEA_INQUIRY", f"{where}: list of text required")
    return [_text(item, where) for item in value]


def _exact_keys(value, required, optional, where):
    if not isinstance(value, dict):
        fail("INVALID_IDEA_INQUIRY", f"{where}: object required")
    missing = set(required) - set(value)
    extra = set(value) - set(required) - set(optional)
    if missing or extra:
        fail("INVALID_IDEA_INQUIRY", f"{where}: missing {sorted(missing)}, unexpected {sorted(extra)}")


def validate_inquiry(data: dict, where: str = "inquiry") -> dict:
    """Validate one inquiry record's shape and return its ideas by id."""
    _exact_keys(data, {"schema_version", "topic", "ideas", "coupling", "open_questions"}, (), where)
    if data["schema_version"] != SCHEMA_VERSION:
        fail("INVALID_IDEA_INQUIRY", f"{where}: schema_version must be {SCHEMA_VERSION}")
    _text(data["topic"], f"{where}.topic")
    _text(data["coupling"], f"{where}.coupling")
    if not isinstance(data["ideas"], list) or not data["ideas"]:
        fail("INVALID_IDEA_INQUIRY", f"{where}: at least one identifiable idea required")
    ideas = {}
    for index, idea in enumerate(data["ideas"]):
        place = f"{where}.ideas[{index}]"
        _exact_keys(idea, {"id", "authority", "alternatives", "evidence", "assumptions", "judgment", *IDEA_TEXT_FIELDS}, (), place)
        identity = _text(idea["id"], f"{place}.id")
        if identity in ideas:
            fail("INVALID_IDEA_INQUIRY", f"{where}: duplicate idea id {identity}")
        if idea["authority"] not in IDEA_AUTHORITIES:
            fail("INVALID_IDEA_INQUIRY", f"{place}.authority must be one of {IDEA_AUTHORITIES}")
        for field in IDEA_TEXT_FIELDS:
            _text(idea[field], f"{place}.{field}")
        if not _texts(idea["alternatives"], f"{place}.alternatives"):
            fail("INVALID_IDEA_INQUIRY", f"{place}: weigh at least one alternative or counterexample")
        evidence = _texts(idea["evidence"], f"{place}.evidence")
        assumptions = _texts(idea["assumptions"], f"{place}.assumptions")
        if not evidence and not assumptions:
            fail("INVALID_IDEA_INQUIRY", f"{place}: separate the evidence from the unresolved assumptions")
        if idea["judgment"] not in JUDGMENTS:
            fail("INVALID_IDEA_INQUIRY", f"{place}.judgment must be one of {JUDGMENTS}")
        ideas[identity] = idea
    if not isinstance(data["open_questions"], list):
        fail("INVALID_IDEA_INQUIRY", f"{where}.open_questions must be a list")
    seen = set()
    for index, question in enumerate(data["open_questions"]):
        place = f"{where}.open_questions[{index}]"
        disposition = question.get("disposition") if isinstance(question, dict) else None
        if disposition not in DISPOSITIONS:
            fail("INVALID_IDEA_INQUIRY", f"{place}.disposition must be one of {sorted(DISPOSITIONS)}")
        _exact_keys(question, {"id", "question", "idea_ids", "disposition", *DISPOSITIONS[disposition]}, (), place)
        identity = _text(question["id"], f"{place}.id")
        if identity in seen:
            fail("INVALID_IDEA_INQUIRY", f"{where}: duplicate open question id {identity}")
        seen.add(identity)
        _text(question["question"], f"{place}.question")
        for idea_id in _texts(question["idea_ids"], f"{place}.idea_ids"):
            if idea_id not in ideas:
                fail("INVALID_IDEA_INQUIRY", f"{place}: unknown idea id {idea_id}")
        for field in DISPOSITIONS[disposition]:
            _text(question[field], f"{place}.{field}")
    return ideas


def validate_coverage(roots: dict, design: dict, mode: str) -> None:
    """Check the design's idea coverage; AUTONOMOUS makes it mandatory and complete."""
    coverage = design.get("idea_coverage")
    from factory_core.authorship import AUTONOMOUS_MODES
    autonomous = mode in AUTONOMOUS_MODES
    if coverage is None:
        if autonomous and design["capability"] in COVERED_CAPABILITIES:
            fail("IDEA_INQUIRY_REQUIRED", "AUTONOMOUS mode: bind per-idea inquiry for every material decision; skipping Idea is not allowed")
        return
    if not isinstance(coverage, dict) or set(coverage) != {"inquiries", "decisions"}:
        fail("INVALID_IDEA_COVERAGE", "idea_coverage requires exactly inquiries and decisions")
    inquiries = coverage["inquiries"]
    if not isinstance(inquiries, list) or not inquiries:
        fail("INVALID_IDEA_COVERAGE", "at least one inquiry record required")
    ideas, questions = {}, []
    for ref in inquiries:
        if not isinstance(ref, dict) or ref.get("scope") != "game" or ref not in design["inputs"]:
            fail("INVALID_IDEA_COVERAGE", "each inquiry must be a game-owned design input so it is sealed in the review closure")
        record = read_json(resolve_ref(roots, ref))
        for identity, idea in validate_inquiry(record, ref["path"]).items():
            if identity in ideas:
                fail("INVALID_IDEA_COVERAGE", f"idea id {identity} appears in more than one inquiry")
            ideas[identity] = idea
        questions += record["open_questions"]
    decisions = coverage["decisions"]
    expected = {item["id"] for item in design["decisions"]}
    if not isinstance(decisions, dict) or set(decisions) != expected:
        missing = sorted(expected - set(decisions)) if isinstance(decisions, dict) else sorted(expected)
        fail("IDEA_COVERAGE_INCOMPLETE", f"classify every material decision; missing {missing}")
    relied = set()
    for decision_id, entry in decisions.items():
        if not isinstance(entry, dict) or len(entry) != 1 or not ({"ideas"} >= set(entry) or {"not_a_design_idea"} >= set(entry)):
            fail("INVALID_IDEA_COVERAGE", f"{decision_id}: give either ideas or a not_a_design_idea reason")
        if "not_a_design_idea" in entry:
            _text(entry["not_a_design_idea"], f"{decision_id}.not_a_design_idea")
            continue
        names = entry["ideas"]
        if not isinstance(names, list) or not names:
            fail("INVALID_IDEA_COVERAGE", f"{decision_id}: list the inquired ideas it relies on")
        for name in names:
            if name not in ideas:
                fail("IDEA_COVERAGE_INCOMPLETE", f"{decision_id}: idea {name} has no inquiry")
            relied.add(name)
    if not autonomous:
        return
    for name in sorted(relied):
        if ideas[name]["judgment"] != "ADOPT":
            fail("IDEA_NOT_ADOPTED", f"AUTONOMOUS mode: the design relies on idea {name} judged {ideas[name]['judgment']}")
    for question in questions:
        if question["disposition"] == "OPEN":
            fail("OPEN_QUESTION_UNDISPOSITIONED",
                 f"AUTONOMOUS mode: answer {question['id']}, turn it into a falsifiable hypothesis with a test stage, or defer it with a reason")
