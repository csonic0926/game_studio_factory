"""The Director role (factory_core/docs/DIRECTOR_ROLE.md).

In AUTONOMOUS and CLOSED_BETA modes the orchestrating session is the Director: it plays,
judges whether the work is fun and worth continuing, and decides. The judgment may be
wrong; it may not be absent. This module enforces only existence, play evidence and the
decision's effect — never whether the judgment is right.

A boundary advances only on CONTINUE. The latest STOP or KILL note of a task blocks every
production stage until a later note decides otherwise (or the USER changes the mode).
"""
from __future__ import annotations

from pathlib import Path

from .refs import confined, fail, read_json, resolve_ref

NOTE_VERSION = "factory_director_note.v1"
NOTE_DIRECTORY = "design/factory/director"
DECISIONS = ("CONTINUE", "REDIRECT", "STOP", "KILL")
# Major boundaries and the checkpoint stage each one accompanies.
STAGE_BOUNDARY = {"DESIGN_COMPLETE": "DESIGN_FREEZE", "AUTHORIZED": "DESIGN_APPROVAL",
                  "PRODUCING": "PRODUCTION_START", "EVIDENCE_READY": "USER_HANDOFF"}
BOUNDARIES = (*STAGE_BOUNDARY.values(), "EVIDENCE_CONTRADICTION")
BLOCKED_STAGES = ("AUTHORIZED", "PRODUCING", "EVIDENCE_READY", "COMPLETE")
NOTE_FIELDS = {"schema_version", "task_id", "design", "boundary", "author_context_id", "played",
               "fun_judgment", "biggest_risk", "case_against", "decision", "next", "calibration", "written_at"}


def boundary_for(stage: str, mode: str) -> str | None:
    """The boundary a checkpoint stage needs a note for in this mode, or None."""
    from .authorship import AUTONOMOUS_MODES
    if mode not in AUTONOMOUS_MODES:
        return None
    boundary = STAGE_BOUNDARY.get(stage)
    if boundary == "DESIGN_APPROVAL" and mode != "CLOSED_BETA":
        return None   # in AUTONOMOUS the USER approves; the Director judged at the freeze
    return boundary


def validate_note(roots: dict, ref: dict, task_id: str, design_ref: dict | None) -> dict:
    """A Director note: written for this task and design, with at least one played evidence
    reference that still resolves, a plain judgment, the case against and a decision."""
    from .state import keys, text, texts
    if not isinstance(ref, dict) or ref.get("scope") != "game":
        fail("INVALID_DIRECTOR_NOTE", "director note must be a game-owned reference")
    path = Path(ref.get("path", ""))
    if path.parent.as_posix() != f"{NOTE_DIRECTORY}/{task_id}":
        fail("INVALID_DIRECTOR_NOTE", f"director notes live in {NOTE_DIRECTORY}/{task_id}/")
    note = read_json(resolve_ref(roots, ref))
    keys(note, NOTE_FIELDS)
    if note["schema_version"] != NOTE_VERSION or note["task_id"] != task_id:
        fail("INVALID_DIRECTOR_NOTE", f"{NOTE_VERSION} for task {task_id} required")
    if design_ref is not None and note["design"] != design_ref:
        fail("STALE_DIRECTOR_NOTE", "the director note judged another design; judge the design at this boundary")
    if note["boundary"] not in BOUNDARIES:
        fail("INVALID_DIRECTOR_NOTE", f"boundary must be one of {BOUNDARIES}")
    if note["decision"] not in DECISIONS:
        fail("INVALID_DIRECTOR_NOTE", f"decision must be one of {DECISIONS}")
    text(note["author_context_id"])
    for field in ("fun_judgment", "biggest_risk", "case_against", "next", "written_at"):
        text(note[field])
    played = note["played"]
    if not isinstance(played, list) or not played:
        fail("DIRECTOR_DID_NOT_PLAY", "the Director plays before judging: list what was played")
    for item in played:
        keys(item, {"method", "evidence", "observations"})
        text(item["method"])
        text(item["observations"])
        evidence = item["evidence"]
        if not isinstance(evidence, list) or not evidence:
            fail("DIRECTOR_DID_NOT_PLAY", "every play entry cites evidence (simulation output, build log, frames)")
        for evidence_ref in evidence:
            resolve_ref(roots, evidence_ref)
    texts(note["calibration"])
    return note


def notes(game: Path, task_id: str) -> list[tuple[str, dict]]:
    directory = confined(game, f"{NOTE_DIRECTORY}/{task_id}")
    if not directory.is_dir():
        return []
    return [(path.relative_to(game).as_posix(), read_json(path)) for path in sorted(directory.glob("*.json"))]


def check_checkpoint(roots: dict, record: dict, mode: str) -> None:
    """Checkpoint gate: a major boundary needs the Director's CONTINUE; a standing STOP or
    KILL blocks production stages."""
    stage, task_id = record["stage"], record["task_id"]
    if stage in BLOCKED_STAGES:
        history = notes(roots["game"], task_id)
        if history and history[-1][1].get("decision") in ("STOP", "KILL"):
            fail("DIRECTOR_STOPPED", f"the Director's latest note ({history[-1][0]}) decided {history[-1][1]['decision']}; "
                 "write a new judgment or have the USER change the mode")
    boundary = boundary_for(stage, mode)
    ref = record.get("director_note")
    if boundary is None:
        if ref is not None:
            validate_note(roots, ref, task_id, record.get("design"))
        return
    if ref is None:
        fail("DIRECTOR_NOTE_REQUIRED", f"{mode} mode: the {boundary} boundary needs the Director's judgment (factory_core/docs/DIRECTOR_ROLE.md)")
    note = validate_note(roots, ref, task_id, record.get("design"))
    if note["boundary"] != boundary:
        fail("INVALID_DIRECTOR_NOTE", f"stage {stage} needs a {boundary} note, not {note['boundary']}")
    if note["decision"] != "CONTINUE":
        fail("DIRECTOR_DID_NOT_CONTINUE", f"the Director decided {note['decision']} at {boundary}; the boundary advances only on CONTINUE")


def check_director_ruling(roots: dict, ruling: dict, design_ref: dict, binding: dict) -> None:
    """CLOSED_BETA only: the Director approves a reviewed design in the USER's delegated seat.
    Recorded as AI_DIRECTOR, never presented as a USER ruling, invalid in any other mode."""
    from .authorship import delegation, mode
    from .state import keys, text
    keys(ruling, {"schema_version", "owner", "decision", "design", "dependency_fingerprint", "director_note", "rationale"})
    current = mode(roots)
    if current != "CLOSED_BETA" or "DESIGN_APPROVAL" not in delegation(roots).get("seats", []):
        fail("HUMAN_RULING_REQUIRED", "an AI_DIRECTOR ruling is valid only while the USER delegates design approval in CLOSED_BETA mode")
    if (ruling["schema_version"] != "factory_ruling.v2" or ruling["design"] != design_ref
            or ruling["dependency_fingerprint"] != binding["fingerprint"]):
        fail("HUMAN_RULING_REQUIRED", "the Director's ruling must bind the exact reviewed design and dependency closure")
    text(ruling["rationale"])
    task_id = Path(ruling["director_note"].get("path", "")).parent.name
    note = validate_note(roots, ruling["director_note"], task_id, design_ref)
    if note["boundary"] != "DESIGN_APPROVAL":
        fail("INVALID_DIRECTOR_NOTE", "a Director approval cites its DESIGN_APPROVAL note")
    if ruling["decision"] != "APPROVE" or note["decision"] != "CONTINUE":
        fail("USER_REJECTED", "the Director did not approve this design")
