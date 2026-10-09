"""Validate reviewed value claims. This module does not decide commercial value.

Qualitative conclusions belong to the author and independent informed reviewers.
A sound negative assessment is completed work; only the exact grounded actual
or adopted offer can pass the narrower Studio value-claim gate.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path
import re

from factory_core.catalog import authority_refs, factory_dependencies
from factory_core.refs import (confined, digest, encoded, exclusive_json, expand_references,
                               fail, read_json, reference, resolve_ref, unique_refs)
from factory_core.state import identifier, keys, latest, project_lock, text, texts, verify_record
from studio.product import (ACTIVE, LEGACY_ACTIVE, NO_ACTIVE, BLOCKED,
                            REGISTER_PATH, product_authority_status)

ROOT = Path(__file__).resolve().parents[1]
BASE = "design/product_value"
ROLES = ("intent_experience", "completeness_project")
JUDGMENTS = ("SUPPORTED", "VALUE_GAP", "EVIDENCE_INSUFFICIENT", "CONTEXT_UNRESOLVED")
GROUNDINGS = ("GROUNDED", "HYPOTHESIS", "UNKNOWN")
OFFERS = ("CURRENT_OFFER", "ADOPTED_OFFER", "PROPOSED_OFFER", "SCENARIO", "UNKNOWN")
KINDS = ("EXPERIENCE", "VISUAL", "AUDIO", "SOURCE", "TEST")
FINDINGS = ("whole_value_case", "decisive_counterevidence", "experience_reaches_promise",
            "coherence_and_sacrifices", "offer_and_authority", "evidence_selection_and_limits")


def paths(identity):
    identifier(identity)
    root = f"{BASE}/{identity}"
    return dict(input=f"{root}/PRODUCT_VALUE_ASSESSMENT.json",
                report=f"{root}/PRODUCT_VALUE_REPORT.md", result=f"{root}/PRODUCT_VALUE_RESULT.json")


def _enum(value, choices, label):
    if value not in choices:
        fail("INVALID_PRODUCT_ASSESSMENT", f"{label} must be one of {choices}")


def _refs(roots, values, *, allow_empty=False):
    if not isinstance(values, list) or (not allow_empty and not values):
        fail("INVALID_PRODUCT_ASSESSMENT", "exact source references required")
    for ref in values:
        if not isinstance(ref, dict) or ref.get("scope") not in ("game", "game_git"):
            fail("INVALID_PRODUCT_ASSESSMENT", "assessment sources must be game-owned")
        resolve_ref(roots, ref)
    if len(unique_refs(values)) != len(values):
        fail("INVALID_PRODUCT_ASSESSMENT", "duplicate source reference")
    return values


def validate_context(roots, offer, audience):
    keys(offer, {"status", "grounding", "amount", "currency", "platform", "region", "as_of", "provenance", "rationale", "adoption"})
    _enum(offer["status"], OFFERS, "offer status")
    _enum(offer["grounding"], GROUNDINGS, "offer grounding")
    for field in ("platform", "region", "as_of", "rationale"):
        text(offer[field])
    if offer["amount"] is not None:
        if not isinstance(offer["amount"], str) or not re.fullmatch(r"\d+(?:\.\d+)?", offer["amount"]):
            fail("INVALID_PRODUCT_ASSESSMENT", "price must be an explicit nonnegative decimal string, never a score")
        try:
            if not Decimal(offer["amount"]).is_finite():
                raise InvalidOperation
        except InvalidOperation:
            fail("INVALID_PRODUCT_ASSESSMENT", "invalid price")
    if offer["currency"] is not None and (not isinstance(offer["currency"], str) or not re.fullmatch(r"[A-Z]{3}", offer["currency"])):
        fail("INVALID_PRODUCT_ASSESSMENT", "currency must be an explicit three-letter code")
    grounded = offer["grounding"] == "GROUNDED"
    _refs(roots, offer["provenance"], allow_empty=not grounded)
    if grounded and (offer["amount"] is None or offer["currency"] is None or offer["status"] == "UNKNOWN"):
        fail("INVALID_PRODUCT_ASSESSMENT", "grounded offer needs explicit price, currency and status")
    adoption = offer["adoption"]
    if offer["status"] == "ADOPTED_OFFER":
        keys(adoption, {"source", "quote"})
        _refs(roots, [adoption["source"]])
        source = read_json(resolve_ref(roots, adoption["source"]))
        if source.get("role") != "user" or text(adoption["quote"]) not in source.get("content", ""):
            fail("PRODUCT_ADOPTION_SOURCE_REQUIRED", "adopted offer requires its exact quote in a raw USER source; reviewers judge adoption meaning")
        if adoption["source"] not in offer["provenance"]:
            fail("PRODUCT_ADOPTION_SOURCE_REQUIRED", "adoption must be part of the declared offer provenance")
    elif adoption is not None:
        fail("INVALID_PRODUCT_ASSESSMENT", "only ADOPTED_OFFER may carry an adoption record")
    keys(audience, {"grounding", "description", "provenance", "rationale"})
    _enum(audience["grounding"], GROUNDINGS, "audience grounding")
    text(audience["description"])
    text(audience["rationale"])
    _refs(roots, audience["provenance"], allow_empty=audience["grounding"] != "GROUNDED")


def _authority(roots):
    game = roots["game"]
    status = product_authority_status(game)
    register_exists = confined(game, REGISTER_PATH.as_posix()).exists()
    # Absence is not archival. Standalone review of an existing legacy product
    # needs no new commission. Partial canonical authority is never guessed.
    return {"status": status.status, "register_exists": register_exists, "errors": status.errors,
            "claim_blocked": status.status == BLOCKED or (register_exists and status.status != ACTIVE)}


def _mandatory(roots):
    game = roots["game"]
    extra = []
    metadata = confined(game, "design/factory/PROJECT.json")
    if metadata.exists():
        payload = read_json(metadata)
        extra = texts(payload.get("authority_paths", []))
        extra.append("design/factory/PROJECT.json")
    return authority_refs(game, "product", extra)


def validate_assessment(roots, ref):
    if ref.get("scope") != "game":
        fail("INVALID_PRODUCT_ASSESSMENT", "assessment must be game-owned")
    a = read_json(resolve_ref(roots, ref))
    keys(a, {"schema_version", "assessment_id", "author_context_id", "subject", "offer", "audience", "report", "evidence",
             "judgment", "material_unknowns", "conditionality", "next_move"})
    if a["schema_version"] != "product_value_assessment.v1":
        fail("INVALID_PRODUCT_ASSESSMENT", "unsupported assessment schema")
    owned = paths(a["assessment_id"])
    if ref["path"] != owned["input"]:
        fail("INVALID_PRODUCT_ASSESSMENT", "assessment identity must match its owned input path")
    text(a["author_context_id"])
    keys(a["subject"], {"title", "build"})
    text(a["subject"]["title"])
    build = a["subject"]["build"]
    if build is not None:
        _refs(roots, [build])
    validate_context(roots, a["offer"], a["audience"])
    _refs(roots, [a["report"]])
    if a["report"].get("scope") != "game" or a["report"]["path"] != owned["report"]:
        fail("INVALID_PRODUCT_ASSESSMENT", "full report must use the assessment-owned report path")
    text(resolve_ref(roots, a["report"]).read_text(encoding="utf-8"))
    _enum(a["judgment"], JUDGMENTS, "judgment")
    texts(a["material_unknowns"])
    texts(a["conditionality"])
    keys(a["next_move"], {"action", "owner", "reason", "what_would_change_judgment"})
    for value in a["next_move"].values():
        text(value)
    if not isinstance(a["evidence"], list):
        fail("INVALID_PRODUCT_ASSESSMENT", "evidence must be a list; empty is honest when unavailable")
    ids = set()
    experiential = False
    for e in a["evidence"]:
        keys(e, {"id", "kind", "reference", "build", "observation", "limitations"})
        identifier(e["id"])
        if e["id"] in ids:
            fail("INVALID_PRODUCT_ASSESSMENT", "duplicate evidence id")
        ids.add(e["id"])
        _enum(e["kind"], KINDS, "evidence kind")
        _refs(roots, [e["reference"]])
        text(e["observation"])
        text(e["limitations"])
        if e["build"] is not None:
            _refs(roots, [e["build"]])
            if e["build"] != build:
                fail("WRONG_PRODUCT_BUILD", "evidence must describe the assessed exact build")
        if e["kind"] == "EXPERIENCE":
            if build is None or e["build"] != build:
                fail("WRONG_PRODUCT_BUILD", "experiential evidence requires the exact assessed build")
            experiential = True
    unknown = a["offer"]["grounding"] == "UNKNOWN" or a["audience"]["grounding"] == "UNKNOWN"
    if unknown and a["judgment"] != "CONTEXT_UNRESOLVED":
        fail("UNRESOLVED_PRODUCT_CONTEXT", "unknown offer/audience must remain CONTEXT_UNRESOLVED")
    if a["judgment"] == "SUPPORTED":
        if not experiential:
            fail("PRODUCT_EXPERIENCE_REQUIRED", "support needs actual build-bound experience, not tests or screenshots alone")
        if a["material_unknowns"]:
            fail("UNRESOLVED_PRODUCT_CONTEXT", "untested material promises cannot yield SUPPORTED")
        if a["offer"]["amount"] is None or a["offer"]["currency"] is None:
            fail("UNRESOLVED_PRODUCT_CONTEXT", "support needs an explicit scoped price")
    return a


def prepare(roots, input_path):
    ref = reference(roots["game"], input_path)
    a = validate_assessment(roots, ref)
    mandatory = _mandatory(roots)
    refs = expand_references(roots, unique_refs([ref, *mandatory, *factory_dependencies(roots["factory"], "product", "assessment", 2)]))
    # This receipt uses its independent v1 contract on any legacy/v2/v3 game;
    # it never calls migrate or borrows an existing task's authorization.
    return {"status": "PRODUCT_REVIEW_PACKAGE_VALID", "assessment": ref,
            "assessment_id": a["assessment_id"], "dependencies": {"references": refs, "fingerprint": digest(refs)},
            "mandatory_authority": mandatory, "authority": _authority(roots), "judgment": a["judgment"],
            "review_roles": list(ROLES), "review_findings": list(FINDINGS), "authority_granted": False}


def _review(roots, ref, package, a):
    if ref.get("scope") != "game" or not ref["path"].startswith(f"{BASE}/{a['assessment_id']}/reviews/"):
        fail("INVALID_PRODUCT_REVIEW", "review must belong to the assessment's review directory")
    r = read_json(resolve_ref(roots, ref))
    keys(r, {"schema_version", "role", "reviewer_context_id", "fresh", "peer_reviews_read", "assessment", "dependency_fingerprint",
             "verdict", "findings", "source_coverage"})
    if r["schema_version"] != "product_value_review.v1":
        fail("INVALID_PRODUCT_REVIEW", "unsupported review schema")
    _enum(r["role"], ROLES, "review role")
    text(r["reviewer_context_id"])
    if r["fresh"] is not True or r["peer_reviews_read"] != [] or r["reviewer_context_id"] == a["author_context_id"]:
        fail("REVIEW_NOT_INDEPENDENT", "fresh non-author, peer-isolated review required")
    if r["assessment"] != package["assessment"] or r["dependency_fingerprint"] != package["dependencies"]["fingerprint"]:
        fail("STALE_PRODUCT_REVIEW", "review must bind the exact current assessment and source closure")
    if r["verdict"] != "AGREE":
        fail("PRODUCT_ASSESSMENT_REJECTED", "revise assessment and obtain fresh reviews; preserve the failed report")
    keys(r["findings"], set(FINDINGS))
    for finding in r["findings"].values():
        keys(finding, {"rationale", "evidence"})
        text(finding["rationale"])
        _refs(roots, finding["evidence"])
        if any(source not in package["dependencies"]["references"] for source in finding["evidence"]):
            fail("INVALID_PRODUCT_REVIEW", "finding evidence must belong to the reviewed closure")
    expected = {digest(source) for source in package["dependencies"]["references"] if source["scope"] != "factory"}
    supplied = texts(r["source_coverage"])
    if len(supplied) != len(set(supplied)) or set(supplied) != expected:
        fail("INCOMPLETE_PRODUCT_REVIEW", "review must cover every exact non-Factory source, including historical revisions")
    return r


def _qualifications(a, authority):
    reasons = list(a["conditionality"])
    if a["offer"]["status"] not in ("CURRENT_OFFER", "ADOPTED_OFFER"):
        reasons.append(f"Offer is {a['offer']['status']}; it is not the current or explicitly adopted offer")
    if a["offer"]["grounding"] != "GROUNDED" or a["audience"]["grounding"] != "GROUNDED":
        reasons.append("Offer and audience must both be grounded")
    if a["material_unknowns"]:
        reasons.extend(a["material_unknowns"])
    if authority["claim_blocked"]:
        reasons.append("Product authority is explicitly inactive or incomplete")
    return reasons


def _expected(roots, input_path, review_refs):
    p = prepare(roots, input_path)
    a = validate_assessment(roots, p["assessment"])
    if len(review_refs) != 2:
        fail("PRODUCT_REVIEWS_REQUIRED", "two independent whole-assessment reviews required")
    reviews = [_review(roots, ref, p, a) for ref in review_refs]
    if len({r["role"] for r in reviews}) != 2 or len({r["reviewer_context_id"] for r in reviews}) != 2:
        fail("REVIEW_NOT_INDEPENDENT", "distinct required roles and reviewer contexts required")
    conditions = _qualifications(a, p["authority"])
    return {"schema_version": "product_value_result.v1", "mode": "standalone_assessment",
            "assessment_id": a["assessment_id"], "assessment": p["assessment"], "reviews": unique_refs(review_refs),
            "dependencies": p["dependencies"], "mandatory_authority": p["mandatory_authority"], "authority": p["authority"],
            "subject": a["subject"], "claim_scope": {"offer": a["offer"], "audience": a["audience"]},
            "judgment": a["judgment"], "qualifications": conditions, "next_move": a["next_move"],
            "mechanical_status": "RECORD_VALID", "value_claim_eligible": a["judgment"] == "SUPPORTED" and not conditions,
            "user_accepted": False, "delivery_eligible": False}


def record(roots, input_path, review_paths):
    with project_lock(roots["game"]):
        reviews = [reference(roots["game"], path) for path in review_paths]
        result = _expected(roots, input_path, reviews)
        target_path = paths(result["assessment_id"])["result"]
        target = confined(roots["game"], target_path)
        if target.exists():
            if target.read_bytes() != encoded(result):
                fail("IMMUTABLE_PRODUCT_RESULT", "existing result differs; preserve it and use a new assessment id")
        else:
            # A second complete read detects concurrent changes by noncooperating
            # editors. The lock coordinates Factory writers, not all processes.
            if _expected(roots, input_path, reviews) != result:
                fail("CONCURRENT_WRITE", "assessment sources changed before publication")
            exclusive_json(target, result)
        return {"status": "PRODUCT_ASSESSMENT_RECORDED", "result": reference(roots["game"], target_path), **result}


def check(roots, result_path):
    ref = reference(roots["game"], result_path)
    result = read_json(resolve_ref(roots, ref))
    if result.get("schema_version") != "product_value_result.v1":
        fail("INVALID_PRODUCT_RESULT", "exact Product result required; arbitrary PASS is not acceptance")
    if result_path != paths(result.get("assessment_id"))["result"]:
        fail("INVALID_PRODUCT_RESULT", "result path does not match assessment identity")
    expected = _expected(roots, result["assessment"]["path"], result["reviews"])
    if result != expected:
        fail("STALE_PRODUCT_RESULT", "current source/authority closure differs; never rehash old reviews")
    return {"status": "PRODUCT_ASSESSMENT_CHECKED", "result": ref, **result}


def gate(roots, result_path, build_path):
    result = check(roots, result_path)
    requested = reference(roots["game"], build_path)
    reasons = list(result["qualifications"])
    if result["subject"]["build"] != requested:
        reasons.append("Requested build differs from the exact assessed build")
    if result["judgment"] != "SUPPORTED":
        reasons.append(f"Judgment is {result['judgment']}")
    eligible = result["value_claim_eligible"] and not reasons
    return {"status": "PRODUCT_VALUE_CLAIM_SUPPORTED" if eligible else "PRODUCT_VALUE_CLAIM_BLOCKED",
            "ok": eligible, "claim_scope": result["claim_scope"], "subject": result["subject"],
            "judgment": result["judgment"], "qualifications": reasons, "result": result["result"],
            "source_freshness": "Unchanged recorded sources only; refresh external offer evidence before a new claim",
            "user_accepted": False, "delivery_eligible": False}


def inspect(roots):
    reports = []
    for path in sorted(confined(roots["game"], BASE).glob("*/PRODUCT_VALUE_RESULT.json")):
        relative = path.relative_to(roots["game"]).as_posix()
        reports.append(reference(roots["game"], relative))
    return {"status": "PRODUCT_ASSESSMENT_AVAILABLE", "authority": _authority(roots), "results": reports,
            "next_action": "Reconstruct the actual offer and buyer; encounter the experience carrying the promise",
            "authority_granted": False}


def validate_design_binding(roots, design):
    binding = design.get("product")
    if design["capability"] != "product":
        if "product" in design:
            fail("INVALID_PRODUCT_DESIGN", "Product binding belongs only to Product designs")
        return
    keys(binding, {"assessment_id", "subject", "offer", "audience", "result_path", "required_output_paths"})
    owned = paths(binding["assessment_id"])
    keys(binding["subject"], {"title", "build"})
    text(binding["subject"]["title"])
    if binding["subject"]["build"] is not None:
        _refs(roots, [binding["subject"]["build"]])
    validate_context(roots, binding["offer"], binding["audience"])
    required = texts(binding["required_output_paths"])
    if len(required) != len(set(required)) or not set(owned.values()).issubset(required):
        fail("INVALID_PRODUCT_DESIGN", "required outputs must uniquely include assessment, full report and result")
    if binding["result_path"] != owned["result"] or not set(required).issubset(design["production_scope"]):
        fail("INVALID_PRODUCT_DESIGN", "Product result/required outputs must match identity and approved production scope")
    for path in required:
        confined(roots["game"], path)


def validate_acceptance(roots, record, design, ref):
    validate_design_binding(roots, design)
    b = design["product"]
    if ref.get("scope") != "game" or ref.get("path") != b["result_path"]:
        fail("WRONG_PRODUCT_ACCEPTANCE", "result must be the sealed task's expected result path")
    result = check(roots, ref["path"])
    if result["result"] != ref or result["assessment_id"] != b["assessment_id"] or result["subject"] != b["subject"]:
        fail("WRONG_PRODUCT_ACCEPTANCE", "result must bind the sealed assessment identity and subject")
    if result["claim_scope"] != {"offer": b["offer"], "audience": b["audience"]}:
        fail("WRONG_PRODUCT_ACCEPTANCE", "result offer/audience differs from the reviewed task")
    evidence, previous_digest = latest(roots["game"], record["task_id"])
    if (not evidence or evidence["stage"] != "EVIDENCE_READY" or evidence["design"] != record["design"]
            or previous_digest != record["previous"]):
        fail("PRODUCT_EVIDENCE_CHECKPOINT_REQUIRED", "actual preceding EVIDENCE_READY checkpoint must bind this design")
    verify_record(roots, evidence)
    reserved_contexts = {design["author_context_id"]}
    reserved_contexts.update(read_json(resolve_ref(roots, review))["reviewer_context_id"] for review in record["reviews"])
    if any(read_json(resolve_ref(roots, review))["reviewer_context_id"] in reserved_contexts for review in result["reviews"]):
        fail("REVIEW_NOT_INDEPENDENT", "output value reviewers must be fresh from task author and design reviewers")
    for path in b["required_output_paths"]:
        current = reference(roots["game"], path)
        if current not in evidence["artifacts"] or current not in record["artifacts"]:
            fail("PRODUCT_OUTPUT_MISSING", "every required current output must already be in EVIDENCE_READY and remain in COMPLETE")
    if ref not in evidence["artifacts"] or ref not in record["artifacts"]:
        fail("PRODUCT_OUTPUT_MISSING", "exact result must already be evidence-ready")
    return {"status": "PRODUCT_ASSESSMENT_COMPLETE", "judgment": result["judgment"],
            "value_claim_eligible": result["value_claim_eligible"], "gameplay_accepted": False,
            "user_accepted": False, "delivery_eligible": False}
