"""Exact-output Story semantic acceptance, separate from pre-production review."""
from __future__ import annotations

from factory_core.refs import fail, read_json, resolve_ref
from factory_core.state import keys, texts, text

CHECKS = {
    "full_prose", "voice_and_native_dialogue", "knowledge_order", "branch_memory",
    "route_choice_meaning", "emotion_holds_releases_all_channels", "canon_terms",
    "all_shipped_locale_semantics", "final_language_style", "staging_landing_fidelity",
    "cleanroom_fluency_backcheck", "twin_and_sync_deltas", "user_gate_preservation",
}

FLUENCY_PACKET_CONTRACT = (
    'Exact story_fluency_packet.v2 contract: keys are schema_version, locale, beats, '
    'protected_forms, banned_forms, lines. schema_version and locale are strings. '
    'All four other fields are arrays of nonempty strings, never objects. '
    'beats and lines must contain at least one entry; protected_forms and '
    'banned_forms may be empty. Include only frozen beats, spoken lines and '
    'protected/banned forms, never canon explanations or reviewer conclusions.'
)


def validate_fluency_packet(packet, locale):
    keys(packet,{"schema_version","locale","beats","protected_forms","banned_forms","lines"})
    if packet["schema_version"] != "story_fluency_packet.v2" or packet["locale"] != locale:
        fail("INVALID_CLEANROOM_PACKET","cleanroom packet locale/schema differs")
    for field in ("beats","protected_forms","banned_forms","lines"):
        if not isinstance(packet[field],list) or any(not isinstance(x,str) or not x.strip() for x in packet[field]):
            fail("INVALID_CLEANROOM_PACKET",field+': '+FLUENCY_PACKET_CONTRACT)
    if not packet["beats"] or not packet["lines"]:
        fail("INVALID_CLEANROOM_PACKET","spoken text and frozen beats required")
    return packet


def validate_acceptance(roots, record, design, ref):
    report = read_json(resolve_ref(roots, ref))
    keys(report, {"schema_version", "design", "dependency_fingerprint", "outputs", "reviewer_context_id",
                  "fresh", "verdict", "checks", "technical_evidence", "shipped_locales", "locale_coverage",
                  "cleanroom_evidence"})
    if (report["schema_version"] != "story_output_acceptance.v2" or report["design"] != record["design"]
            or report["dependency_fingerprint"] != record["dependencies"]["fingerprint"]):
        fail("STALE_ACCEPTANCE", "Story acceptance must bind exact design/dependencies")
    contexts = {design["author_context_id"]}
    contexts.update(read_json(resolve_ref(roots,r))["reviewer_context_id"] for r in record["reviews"])
    if report["fresh"] is not True or text(report["reviewer_context_id"]) in contexts:
        fail("REVIEW_NOT_INDEPENDENT", "latest-output QA must be independent of author and design reviewers")
    if report["verdict"] != "PASS" or set(report["checks"]) != CHECKS:
        fail("STORY_ACCEPTANCE_REQUIRED", "latest-output semantic QA must pass every Story obligation")
    for check in report["checks"].values():
        keys(check, {"status", "rationale", "evidence"})
        if check["status"] != "PASS":
            fail("STORY_ACCEPTANCE_REQUIRED", "Story QA has an unresolved finding")
        text(check["rationale"])
        if not isinstance(check["evidence"],list) or not check["evidence"]:
            fail("STORY_ACCEPTANCE_REQUIRED", "every finding needs exact-output/source evidence")
        for item in check["evidence"]: resolve_ref(roots,item)
    if report["outputs"] != record["artifacts"] or not report["outputs"]:
        fail("EVIDENCE_MISMATCH", "QA covers every and only the latest output checkpoint")
    for output in report["outputs"]: resolve_ref(roots,output)
    from factory_core.story_profile import resolve
    from factory_core.state import project
    adopted = resolve(roots["game"], project(roots["game"])["authority_paths"], roots["factory"])
    locales = adopted["shipped_locales"]
    if report["shipped_locales"] != locales or set(texts(report["locale_coverage"])) != set(locales):
        fail("LOCALE_COVERAGE_REQUIRED", "QA must cover the adopted profile's actual shipped locales")
    profile = adopted["profile"]
    if profile not in record["dependencies"]["references"] or profile not in report["checks"]["all_shipped_locale_semantics"]["evidence"]:
        fail("LOCALE_COVERAGE_REQUIRED", "locale authority must be sealed and cited")
    output_paths = {r["path"] for r in report["outputs"] if r["scope"] == "game"}
    if set(design["production_scope"]) - output_paths:
        fail("EVIDENCE_MISMATCH", "every planned Story deliverable requires latest-output QA")
    if not isinstance(report["technical_evidence"], list) or not report["technical_evidence"]:
        fail("STORY_ACCEPTANCE_REQUIRED", "typed technical evidence required")
    covered = set()
    for item in report["technical_evidence"]:
        technical = read_json(resolve_ref(roots,item))
        keys(technical,{"schema_version","outputs","checks"})
        if technical["schema_version"] != "story_technical_evidence.v2" or technical["outputs"] != report["outputs"]:
            fail("EVIDENCE_MISMATCH", "technical checks must bind the exact latest output set")
        for name, finding in technical["checks"].items():
            keys(finding,{"status","command","exit_code","log"})
            text(finding["command"])
            resolve_ref(roots,finding["log"])
            if finding["status"] != "PASS" or finding["exit_code"] != 0:
                fail("STORY_ACCEPTANCE_REQUIRED", "technical evidence has a failing check")
            covered.add(name)
    if {"style_lint","glossary","routing","locale_integrity"} - covered:
        fail("STORY_ACCEPTANCE_REQUIRED", "lint/glossary/routing/locale checks must run; unavailable capabilities require explicit checker skip evidence")
    if not isinstance(report["cleanroom_evidence"],list):
        fail("STORY_ACCEPTANCE_REQUIRED","typed cleanroom evidence required")
    applicability = design.get("story")
    if applicability is not None and not applicability["spoken_output_paths"]:
        evidence = report["checks"]["cleanroom_fluency_backcheck"]["evidence"]
        if applicability["scope_evidence"] not in evidence or not any(r in report["outputs"] for r in evidence):
            fail("STORY_ACCEPTANCE_REQUIRED", "NOT_APPLICABLE must cite the reviewed no-dialogue change scope and exact latest output")
        if report["cleanroom_evidence"]:
            fail("STORY_ACCEPTANCE_REQUIRED", "do not manufacture dialogue work for a no-dialogue task")
        return {"status":"STORY_OUTPUT_ACCEPTED", "gameplay_accepted":False, "cleanroom":"NOT_APPLICABLE_REVIEWED_SCOPE"}
    languages=set()
    contexts.add(report["reviewer_context_id"])
    for item in report["cleanroom_evidence"]:
        clean = read_json(resolve_ref(roots,item))
        keys(clean,{"schema_version","locale","packet","outputs","worker_context_id","fresh",
                    "sources_read","verdict","canon_backcheck"})
        if clean["schema_version"] != "story_cleanroom_evidence.v2" or clean["locale"] not in locales or clean["locale"] in languages:
            fail("STORY_ACCEPTANCE_REQUIRED","one typed cleanroom/back-check per shipped locale")
        identity=text(clean["worker_context_id"])
        if clean["fresh"] is not True or identity in contexts or clean["sources_read"] != [clean["packet"]]:
            fail("REVIEW_NOT_INDEPENDENT","cleanroom reads only its sanitized packet in a fresh context")
        contexts.add(identity)
        packet=read_json(resolve_ref(roots,clean["packet"]))
        validate_fluency_packet(packet,clean["locale"])
        if clean["verdict"] != "PASS" or not clean["outputs"] or any(r not in report["outputs"] for r in clean["outputs"]):
            fail("EVIDENCE_MISMATCH","cleanroom must bind latest landed outputs, not stale prose")
        back=read_json(resolve_ref(roots,clean["canon_backcheck"]))
        keys(back,{"schema_version","packet","outputs","reviewer_context_id","sources","verdict","rationale"})
        if (back["schema_version"] != "story_canon_backcheck.v2" or back["packet"] != clean["packet"]
                or back["outputs"] != clean["outputs"] or back["verdict"] != "PASS" or profile not in back["sources"]):
            fail("STORY_ACCEPTANCE_REQUIRED","canon-aware back-check must pass exact cleaned output and profile")
        text(back["rationale"])
        back_identity=text(back["reviewer_context_id"])
        if back_identity in contexts: fail("REVIEW_NOT_INDEPENDENT","canon back-check must be separate from cleanroom and design/QA contexts")
        contexts.add(back_identity)
        for source in back["sources"]: resolve_ref(roots,source)
        languages.add(clean["locale"])
    if languages != set(locales):
        fail("LOCALE_COVERAGE_REQUIRED","cleanroom and canon-aware back-check must cover every shipped locale")
    return {"status":"STORY_OUTPUT_ACCEPTED", "gameplay_accepted":False}
