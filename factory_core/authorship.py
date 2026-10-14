"""USER-selected authorship mode for a migrated project.

COLLABORATIVE (default, also when no mode file exists): human and AI design
together; the USER is present to catch skipped inquiry, so Idea coverage is
recorded as the author chooses. AUTONOMOUS: the AI creates with full delegation;
per-idea Idea inquiry and open-question dispositions become hard design gates
and an extra review requirement. CLOSED_BETA: AUTONOMOUS taken to full delegation;
the AI delivers a complete product before the USER first plays, and the Director
(the orchestrating session, factory_core/docs/DIRECTOR_ROLE.md) holds the delegated
USER seats, recorded as AI_DIRECTOR and never as USER rulings. In both autonomous
modes the Director must judge at major boundaries. Only a USER ruling selects the
mode; it is never inferred from a model name or switched by the operator on its own.
"""
from __future__ import annotations

from .refs import confined, exclusive_json, fail, read_json, reference, resolve_ref

MODE_PATH = "design/factory/AUTHORSHIP_MODE.json"
MODES = ("COLLABORATIVE", "AUTONOMOUS", "CLOSED_BETA")
# Modes without the USER at every design boundary: AUTONOMOUS obligations apply to both.
AUTONOMOUS_MODES = ("AUTONOMOUS", "CLOSED_BETA")
DELEGABLE_SEATS = ("DESIGN_APPROVAL", "INTERNAL_PLAYTEST_VERDICT")
SCHEMA_VERSION = "factory_authorship_mode.v1"


def validate_record(roots: dict, data: dict) -> str:
    from .state import keys, text
    keys(data, {"schema_version", "mode", "owner", "source", "quote"}, {"previous", "delegation"})
    if data["schema_version"] != SCHEMA_VERSION or data["owner"] != "USER" or data["mode"] not in MODES:
        fail("INVALID_AUTHORSHIP_MODE", f"{SCHEMA_VERSION} with owner USER and mode in {MODES} required")
    if data["mode"] == "CLOSED_BETA":
        # The USER names the product delegated to the closed beta and the seats handed over.
        delegated = data.get("delegation")
        keys(delegated, {"product", "seats"})
        text(delegated["product"])
        seats = delegated["seats"]
        if not isinstance(seats, list) or not seats or set(seats) - set(DELEGABLE_SEATS) or len(seats) != len(set(seats)):
            fail("INVALID_AUTHORSHIP_MODE", f"CLOSED_BETA delegation seats must be a subset of {DELEGABLE_SEATS}")
    elif "delegation" in data:
        fail("INVALID_AUTHORSHIP_MODE", "only CLOSED_BETA carries a delegation")
    # Like design rulings, origin is an auditable raw USER message, not a
    # machine-verifiable signature; the harness must preserve role and content.
    source = read_json(resolve_ref(roots, data["source"]))
    if source.get("role") != "user" or text(data["quote"]) not in source.get("content", ""):
        fail("INVALID_RULING_SOURCE", "authorship mode quote must occur in the raw USER message")
    return data["mode"]


def mode(roots: dict) -> str:
    path = confined(roots["game"], MODE_PATH)
    if not path.exists():
        return "COLLABORATIVE"
    return validate_record(roots, read_json(path))


def delegation(roots: dict) -> dict:
    """The CLOSED_BETA delegation ({product, seats}), or {} in any other mode."""
    path = confined(roots["game"], MODE_PATH)
    if not path.exists():
        return {}
    data = read_json(path)
    validate_record(roots, data)
    return data.get("delegation", {}) if data["mode"] == "CLOSED_BETA" else {}


def mode_reference(game):
    """The mode file joins every design closure so a switch invalidates old reviews."""
    return reference(game, MODE_PATH) if confined(game, MODE_PATH).exists() else None


def set_mode(roots: dict, selected: str, source: str, quote: str, product: str | None = None, seats: list | None = None) -> dict:
    from .state import project, project_lock
    selected = selected.upper()
    game = roots["game"]
    project(game)
    record = {"schema_version": SCHEMA_VERSION, "mode": selected, "owner": "USER",
              "source": reference(game, source), "quote": quote}
    if selected == "CLOSED_BETA":
        record["delegation"] = {"product": product or "", "seats": list(seats or DELEGABLE_SEATS)}
    validate_record(roots, record)
    path = confined(game, MODE_PATH)
    with project_lock(game):
        if path.exists():
            current = read_json(path)
            if current.get("mode") == selected and current.get("delegation") == record.get("delegation"):
                return {"status": "MODE_UNCHANGED", "mode": selected, "record": reference(game, MODE_PATH)}
            record["previous"] = reference(game, MODE_PATH)
            path.unlink()
        exclusive_json(path, record)
    return {"status": "MODE_SET", "mode": selected, "record": reference(game, MODE_PATH),
            "note": "Designs reviewed under the previous mode need a new draft and fresh reviews."}
