"""Dispatch completed-task checks to the owning specialist, never mint verdicts."""
from __future__ import annotations

from .refs import fail, read_json, resolve_ref


def validate(roots, record, design, ref):
    if not ref:
        fail("SPECIALIST_ACCEPTANCE_REQUIRED", "exact specialist acceptance reference required")
    path = resolve_ref(roots, ref)
    if design["capability"] == "story":
        from story.v2 import validate_acceptance
        return validate_acceptance(roots, record, design, ref)
    if design["capability"] in ("studio", "gameplay"):
        from studio.baseline import check_baseline_admission, BASELINE_ADMISSION_VALID
        report = read_json(path)
        if report.get("schema_version") != "baseline_admission_input.v1":
            fail("SPECIALIST_ACCEPTANCE_REQUIRED", "gameplay closure requires a checked baseline admission, not arbitrary PASS evidence")
        result = check_baseline_admission(str(roots["game"]), ref["path"])
        if result.status != BASELINE_ADMISSION_VALID:
            fail("SPECIALIST_ACCEPTANCE_REQUIRED", "; ".join(result.errors) or result.status)
        units = report.get("admitted_units", [])
        objective = design["gameplay"]["objective"]
        if not any(unit.get("unit_id") == design["gameplay"]["objective_id"] and
                   unit.get("authority") == {"path": objective["path"], "sha256":objective["sha256"]} for unit in units):
            fail("WRONG_ACCEPTANCE", "baseline does not accept this exact objective")
        return {"status":"BASELINE_ADMISSION_VALID", "gameplay_accepted":True}
    if design["capability"] in ("asset", "sound"):
        from .context import provider_result
        result = provider_result(roots, ref["path"])
        if not result["ok"] or any(r not in record["artifacts"] for r in result["deliverables"]):
            fail("SPECIALIST_ACCEPTANCE_REQUIRED", "exact successful provider deliverables required")
        return {"status": "PROVIDER_PIPELINE_COMPLETED", "gameplay_accepted": False,
                "creative_quality": "not certified by a technical status reader"}
    fail("SPECIALIST_ACCEPTANCE_REQUIRED", f"use the {design['capability']} specialist result; no generic acceptance substitute")
