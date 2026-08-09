#!/usr/bin/env python3
"""Validate Studio material-turn alignment and decision-card lifecycle.

The gameplay-system and conformance reviewers begin after an interpretation has
already been authored.  This module guards the earlier transition:

    active authority + raw user input -> candidate human-facing output

It does not decide product taste.  A fresh reviewer records whether the
candidate preserves authority, covers the new input, avoids semantic proxies,
and asks the human only questions that the bound authority cannot answer.

Studio decision cards additionally live in one game-owned register.  A newer
pending card may explicitly supersede an older pending payload; a superseded
payload can no longer be rendered or approved even though its immutable card
artifact remains available as history.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


FACTORY_ROOT = Path(__file__).resolve().parents[1]
ALIGNMENT_INPUT_VERSION = "studio_semantic_alignment_input.v3"
ALIGNMENT_REVIEW_VERSION = "studio_semantic_alignment_review.v3"
DECISION_REGISTER_VERSION = "studio_decision_card_register.v1"
DECISION_REGISTER_PATH = "design/studio/STUDIO_DECISION_CARD_REGISTER.json"

PASS_ALIGNMENT = "PASS_ALIGNMENT"
REVISE_BEFORE_USER = "REVISE_BEFORE_USER"
HUMAN_RULING_GENUINELY_REQUIRED = "HUMAN_RULING_GENUINELY_REQUIRED"
PRESENTABLE_VERDICTS = {PASS_ALIGNMENT, HUMAN_RULING_GENUINELY_REQUIRED}

ALIGNMENT_CHECKS = {
    "input_delta_complete",
    "response_binding_fidelity",
    "authority_continuity",
    "authority_change_fidelity",
    "claim_provenance",
    "material_claim_coverage",
    "question_necessity",
    "semantic_non_substitution",
    "routing_and_scope",
    "human_boundary",
    "surface_proportionality",
    "pending_decision_disposition",
}
TRIGGERS = {
    "MATERIAL_USER_INPUT",
    "REVISED_AUTHORITY",
    "HUMAN_DECISION_SURFACE",
    "BLOCKING_HUMAN_QUESTION",
}
AUTHORITY_KINDS = {
    "PRODUCT",
    "STUDIO_GAMEPLAY_SYSTEM",
    "GAMEPLAY_DECISION_CARD",
    "ACCEPTED_BASELINE",
    "REPO_EVIDENCE",
    "REFERENCE_EVIDENCE",
}
DELTA_CLASSES = {"ADD", "MODIFY", "REVOKE", "AMBIGUOUS"}
PROPOSED_TRANSITIONS = {
    "CONTINUE_EXISTING_AUTHORITY",
    "REOPEN_PRODUCT_EXPLORATION",
    "ACTIVATE_PRODUCT_AUTHORITY",
    "REVISE_STUDIO_GAMEPLAY_SYSTEM",
    "REVISE_DECISION_CARD",
    "REQUEST_HUMAN_RULING",
    "NO_MATERIAL_CHANGE",
    "ARCHIVE_PRODUCT_DIRECTION",
}
OUTPUT_KINDS = {"DECISION_SURFACE", "HUMAN_QUESTION", "MATERIAL_RESPONSE"}
CLAIM_PROVENANCE = {
    "PRESERVED_AUTHORITY",
    "NEW_USER_INPUT",
    "BOUND_USER_RESPONSE",
    "REPO_EVIDENCE",
    "REFERENCE_EVIDENCE",
    "AI_SYNTHESIS",
    "AI_HYPOTHESIS",
}
AUTHORITY_CHANGE_OPERATIONS = {"CREATE", "REVISE", "ACTIVATE", "SUPERSEDE", "ARCHIVE"}
AUTHORITY_CHANGE_KINDS = {
    "IDEA_EXPLORATION",
    "PRODUCT_AUTHORITY_INPUT",
    "PRODUCT_THESIS",
    "FACTORY_CONSTRAINTS",
    "IDEA_FACTORY_RESULT",
    "STUDIO_GAMEPLAY_SYSTEM",
    "GAMEPLAY_DECISION_CARD",
    "ACCEPTED_BASELINE",
    "PRODUCTION_PLAN",
}
PENDING_DISPOSITIONS = {
    "PRESERVE_PENDING",
    "SUPERSEDE_PENDING",
    "WITHDRAW_BY_PRODUCT_ARCHIVE",
}
REGISTER_STATES = {
    "PENDING",
    "USER_APPROVED",
    "USER_REJECTED",
    "SUPERSEDED",
    "PRODUCT_ARCHIVED",
}

ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
REVISION_PATTERN = re.compile(r"^[0-9a-f]{7,64}$")


class AlignmentValidationError(ValueError):
    """Raised when an alignment artifact cannot be read at all."""


@dataclass
class AlignmentValidationResult:
    status: str
    errors: list[str] = field(default_factory=list)
    interaction_id: str = ""
    project_id: str = ""
    candidate_output_kind: str = ""
    candidate_output_sha256: str = ""
    review_verdict: str = ""
    proposed_transition: str = ""
    authority_changes: list[dict[str, Any]] = field(default_factory=list)


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def material_output_lines(text: str, question_quotes: list[str] | None = None) -> list[str]:
    """Return candidate lines whose semantic claims require provenance.

    The author controls line wrapping, so the contract deliberately uses exact
    non-empty lines as the smallest machine-checkable coverage unit.  Only
    mechanical wrapper lines (mode headers, fence markers, source lists,
    payload/reply tokens, and separately inventoried whole-line questions) are
    excluded.  Headings remain covered because a title can itself smuggle a
    product conclusion.  Everything else must appear verbatim as one
    output-claim quote; a reviewer cannot silently omit an inconvenient line.
    """

    questions = {quote.strip() for quote in (question_quotes or []) if quote.strip()}
    material: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("```"):
            continue
        if not line:
            continue
        if re.match(r"^(HSFRM|HDPRM|COLLAB):\s", line):
            continue
        if line in {"---", "***", "___"}:
            continue
        if line.startswith("Sources:") or line.startswith("Source:"):
            continue
        if line.startswith("Decision payload:") or line.startswith("Reply:"):
            continue
        if line in questions:
            continue
        material.append(line)
    return material


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def current_factory_revision(factory_root: Path = FACTORY_ROOT) -> str:
    result = subprocess.run(
        ["git", "-C", str(factory_root), "rev-parse", "HEAD"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    revision = result.stdout.strip()
    if result.returncode != 0 or REVISION_PATTERN.fullmatch(revision) is None:
        raise AlignmentValidationError(
            result.stderr.strip() or "Factory checkout has no readable HEAD"
        )
    return revision


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise AlignmentValidationError(f"cannot read {label}: {error}") from error
    if not isinstance(payload, dict):
        raise AlignmentValidationError(f"{label} must be a JSON object")
    return payload


def _keys(value: Any, label: str, required: set[str], errors: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object")
        return {}
    for key in sorted(required - set(value)):
        errors.append(f"{label} is missing {key}")
    for key in sorted(set(value) - required):
        errors.append(f"{label} contains unsupported field {key}")
    return value


def _text(
    value: Any,
    label: str,
    errors: list[str],
    *,
    allow_empty: bool = False,
) -> str:
    if not isinstance(value, str):
        errors.append(f"{label} must be a string")
        return ""
    text = value.strip()
    if not text and not allow_empty:
        errors.append(f"{label} must be a non-empty string")
    if "TBD" in text:
        errors.append(f"{label} must not contain TBD")
    return text


def _exact_text(value: Any, label: str, errors: list[str]) -> str:
    """Validate non-empty text without normalizing bytes used by a SHA binding."""

    if not isinstance(value, str):
        errors.append(f"{label} must be a string")
        return ""
    if not value.strip():
        errors.append(f"{label} must be a non-empty string")
    return value


def _identifier(value: Any, label: str, errors: list[str]) -> str:
    result = _text(value, label, errors)
    if result and ID_PATTERN.fullmatch(result) is None:
        errors.append(f"{label} must match {ID_PATTERN.pattern}")
    return result


def _sha(value: Any, label: str, errors: list[str], *, allow_empty: bool = False) -> str:
    result = _text(value, label, errors, allow_empty=allow_empty)
    if result and SHA256_PATTERN.fullmatch(result) is None:
        errors.append(f"{label} must be 64 lowercase hex characters")
    return result


def _string_list(
    value: Any,
    label: str,
    errors: list[str],
    *,
    allow_empty: bool = True,
) -> list[str]:
    if not isinstance(value, list):
        errors.append(f"{label} must be an array")
        return []
    if not value and not allow_empty:
        errors.append(f"{label} must not be empty")
    result = [_text(item, f"{label}[{index}]", errors) for index, item in enumerate(value)]
    result = [item for item in result if item]
    if len(result) != len(set(result)):
        errors.append(f"{label} must not contain duplicates")
    return result


def _resolve_ref(
    game_repo: Path,
    value: Any,
    label: str,
    errors: list[str],
) -> tuple[dict[str, str], Path | None]:
    payload = _keys(value, label, {"path", "sha256"}, errors)
    path_text = _text(payload.get("path"), f"{label}.path", errors)
    digest = _sha(payload.get("sha256"), f"{label}.sha256", errors)
    if not path_text or not digest:
        return {"path": path_text, "sha256": digest}, None
    relative = Path(path_text)
    if relative.is_absolute():
        errors.append(f"{label}.path must be game-repo-relative")
        return {"path": path_text, "sha256": digest}, None
    path = (game_repo / relative).resolve()
    try:
        path.relative_to(game_repo)
    except ValueError:
        errors.append(f"{label}.path escapes the game repo")
        return {"path": path_text, "sha256": digest}, None
    if not path.is_file():
        errors.append(f"{label}.path does not identify a file: {path_text}")
        return {"path": path_text, "sha256": digest}, None
    if digest and file_sha256(path) != digest:
        errors.append(f"{label} hash does not match {path_text}")
    return {"path": path_text, "sha256": digest}, path


def path_ref(game_repo: Path, path: Path) -> dict[str, str]:
    resolved = path.resolve()
    relative = resolved.relative_to(game_repo.resolve()).as_posix()
    return {"path": relative, "sha256": file_sha256(resolved)}


def _validated_prior_option(
    game_repo: Path,
    raw: Any,
    label: str,
    *,
    current_user_text: str,
    errors: list[str],
) -> tuple[str, dict[str, str]]:
    """Bind an elliptical reply to one exact option on a reviewed prior surface."""

    item = _keys(
        raw,
        label,
        {
            "binding_id", "response_quote", "prior_alignment_input",
            "prior_alignment_review", "question_id", "selected_option_id",
            "selected_option_quote",
        },
        errors,
    )
    binding_id = _identifier(item.get("binding_id"), f"{label}.binding_id", errors)
    response_quote = _text(item.get("response_quote"), f"{label}.response_quote", errors)
    if response_quote and response_quote not in current_user_text:
        errors.append(f"{label}.response_quote is not exact current user input text")
    question_id = _identifier(item.get("question_id"), f"{label}.question_id", errors)
    option_id = _identifier(
        item.get("selected_option_id"), f"{label}.selected_option_id", errors
    )
    option_quote = _text(
        item.get("selected_option_quote"), f"{label}.selected_option_quote", errors
    )
    prior_input_ref, prior_input_path = _resolve_ref(
        game_repo, item.get("prior_alignment_input"), f"{label}.prior_alignment_input", errors
    )
    _, prior_review_path = _resolve_ref(
        game_repo, item.get("prior_alignment_review"), f"{label}.prior_alignment_review", errors
    )
    if prior_input_path is None or prior_review_path is None:
        return binding_id, {
            "response_quote": response_quote,
            "selected_option_quote": option_quote,
        }

    prior_input = _load_json(prior_input_path, f"{label} prior alignment input")
    prior_review = _load_json(prior_review_path, f"{label} prior alignment review")
    if prior_input.get("schema_version") != ALIGNMENT_INPUT_VERSION:
        errors.append(f"{label} prior input cannot expose bindable answer options")
    if prior_review.get("schema_version") != ALIGNMENT_REVIEW_VERSION:
        errors.append(f"{label} prior review does not use the current binding contract")
    if prior_input.get("project_id") != prior_review.get("project_id"):
        errors.append(f"{label} prior alignment project ids do not match")
    if prior_input.get("factory_revision") != prior_review.get("factory_revision"):
        errors.append(f"{label} prior alignment Factory revisions do not match")
    review_bound_input = prior_review.get("alignment_input")
    if review_bound_input != prior_input_ref:
        errors.append(f"{label} prior review does not bind the exact prior input")
    if prior_review.get("reviewer_context_id") == prior_input.get("author_context_id"):
        errors.append(f"{label} prior surface was self-reviewed")
    if prior_review.get("reviewer_freshness") != "FRESH":
        errors.append(f"{label} prior surface lacks a fresh reviewer")
    if prior_review.get("verdict") not in PRESENTABLE_VERDICTS:
        errors.append(f"{label} prior surface was not presentable")
    if prior_review.get("blocking_findings") != []:
        errors.append(f"{label} prior surface contains blocking findings")
    prior_checks = prior_review.get("checks")
    if (
        not isinstance(prior_checks, dict)
        or set(prior_checks) != ALIGNMENT_CHECKS
        or any(value != "PASS" for value in prior_checks.values())
    ):
        errors.append(f"{label} prior surface review did not pass every recorded check")

    candidate = prior_input.get("candidate_output")
    candidate_text = candidate.get("text", "") if isinstance(candidate, dict) else ""
    candidate_sha = candidate.get("sha256", "") if isinstance(candidate, dict) else ""
    if not candidate_text or text_sha256(candidate_text) != candidate_sha:
        errors.append(f"{label} prior surface does not bind its exact candidate text")
    questions = prior_input.get("human_questions")
    if not isinstance(questions, list):
        questions = []
    matched_questions = [
        question
        for question in questions
        if isinstance(question, dict) and question.get("question_id") == question_id
    ]
    if len(matched_questions) != 1:
        errors.append(f"{label}.question_id does not identify one prior question")
        return binding_id, {
            "response_quote": response_quote,
            "selected_option_quote": option_quote,
        }
    options = matched_questions[0].get("answer_options")
    if not isinstance(options, list):
        options = []
    matched_options = [
        option
        for option in options
        if isinstance(option, dict) and option.get("option_id") == option_id
    ]
    if len(matched_options) != 1:
        errors.append(f"{label}.selected_option_id does not identify one prior option")
        return binding_id, {
            "response_quote": response_quote,
            "selected_option_quote": option_quote,
        }
    option = matched_options[0]
    if option.get("option_quote") != option_quote:
        errors.append(f"{label}.selected_option_quote does not match the prior option")
    output_lines = {line.strip() for line in candidate_text.splitlines() if line.strip()}
    if option_quote not in output_lines:
        errors.append(f"{label}.selected_option_quote was not one exact prior surface line")
    question_quotes = [
        str(question.get("question_quote", ""))
        for question in questions
        if isinstance(question, dict)
    ]
    expected_inventory = set(material_output_lines(candidate_text, question_quotes))
    inventory = prior_review.get("independent_claim_inventory")
    inventoried = {
        str(entry.get("candidate_output_quote", "")).strip()
        for entry in inventory
        if isinstance(entry, dict) and entry.get("status") == "PASS"
    } if isinstance(inventory, list) else set()
    if inventoried != expected_inventory:
        errors.append(f"{label} prior reviewer did not inventory the exact prior surface")
    tokens = option.get("accepted_response_tokens")
    if not isinstance(tokens, list) or response_quote.strip() not in tokens:
        errors.append(f"{label}.response_quote is not an accepted token for the selected option")
    return binding_id, {
        "response_quote": response_quote,
        "selected_option_quote": option_quote,
    }


def _validate_alignment_input(
    game_repo: Path,
    payload: dict[str, Any],
    *,
    factory_revision: str,
    errors: list[str],
) -> dict[str, Any]:
    required = {
        "schema_version", "interaction_id", "project_id", "factory_revision",
        "trigger", "author_context_id", "user_input", "response_bindings",
        "active_authorities", "authority_changes", "pending_decisions",
        "input_deltas", "proposed_transition", "candidate_output",
        "output_claims", "human_questions", "authored_at",
    }
    _keys(payload, "semantic alignment input", required, errors)
    if payload.get("schema_version") != ALIGNMENT_INPUT_VERSION:
        errors.append(
            f"semantic alignment input schema_version must be {ALIGNMENT_INPUT_VERSION}"
        )
    interaction_id = _identifier(
        payload.get("interaction_id"), "alignment input.interaction_id", errors
    )
    project_id = _identifier(
        payload.get("project_id"), "alignment input.project_id", errors
    )
    if payload.get("factory_revision") != factory_revision:
        errors.append("semantic alignment input factory_revision does not match Factory HEAD")
    author_context_id = _identifier(
        payload.get("author_context_id"), "alignment input.author_context_id", errors
    )
    if payload.get("trigger") not in TRIGGERS:
        errors.append("semantic alignment input trigger is unsupported")
    _text(payload.get("authored_at"), "alignment input.authored_at", errors)

    user_input = _keys(
        payload.get("user_input"),
        "alignment input.user_input",
        {"text", "sha256"},
        errors,
    )
    user_text = _exact_text(
        user_input.get("text"), "alignment input.user_input.text", errors
    )
    user_sha = _sha(
        user_input.get("sha256"), "alignment input.user_input.sha256", errors
    )
    if user_text and user_sha and text_sha256(user_text) != user_sha:
        errors.append("alignment input user_input SHA does not match its exact text")

    raw_bindings = payload.get("response_bindings")
    if not isinstance(raw_bindings, list):
        errors.append("alignment input.response_bindings must be an array")
        raw_bindings = []
    response_binding_ids: set[str] = set()
    response_bindings: dict[str, dict[str, str]] = {}
    for index, raw in enumerate(raw_bindings):
        binding_id, binding = _validated_prior_option(
            game_repo,
            raw,
            f"response_bindings[{index}]",
            current_user_text=user_text,
            errors=errors,
        )
        if binding_id in response_binding_ids:
            errors.append(f"duplicate response binding_id: {binding_id}")
        if binding_id:
            response_binding_ids.add(binding_id)
            response_bindings[binding_id] = binding
    if re.fullmatch(r"[A-Za-z0-9]", user_text.strip()) and not response_bindings:
        errors.append(
            "one-token user reply requires an exact binding to the reviewed prior option"
        )

    active = payload.get("active_authorities")
    if not isinstance(active, list):
        errors.append("alignment input.active_authorities must be an array")
        active = []
    authority_ids: set[str] = set()
    authority_kinds: dict[str, str] = {}
    authority_paths: dict[str, Path] = {}
    for index, raw in enumerate(active):
        item = _keys(
            raw,
            f"active_authorities[{index}]",
            {"authority_id", "authority_kind", "artifact"},
            errors,
        )
        authority_id = _identifier(
            item.get("authority_id"), f"active_authorities[{index}].authority_id", errors
        )
        if authority_id in authority_ids:
            errors.append(f"duplicate authority_id: {authority_id}")
        authority_ids.add(authority_id)
        authority_kind = item.get("authority_kind")
        if authority_kind not in AUTHORITY_KINDS:
            errors.append(f"active_authorities[{index}].authority_kind is unsupported")
        elif authority_id:
            authority_kinds[authority_id] = str(authority_kind)
        _, authority_path = _resolve_ref(
            game_repo, item.get("artifact"), f"active_authorities[{index}].artifact", errors
        )
        if authority_id and authority_path is not None:
            authority_paths[authority_id] = authority_path

    raw_changes = payload.get("authority_changes")
    if not isinstance(raw_changes, list):
        errors.append("alignment input.authority_changes must be an array")
        raw_changes = []
    authority_change_ids: set[str] = set()
    authority_changes: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_changes):
        item = _keys(
            raw,
            f"authority_changes[{index}]",
            {"change_id", "operation", "authority_kind", "artifact"},
            errors,
        )
        change_id = _identifier(
            item.get("change_id"), f"authority_changes[{index}].change_id", errors
        )
        if change_id in authority_change_ids:
            errors.append(f"duplicate authority change_id: {change_id}")
        authority_change_ids.add(change_id)
        if item.get("operation") not in AUTHORITY_CHANGE_OPERATIONS:
            errors.append(f"authority_changes[{index}].operation is unsupported")
        if item.get("authority_kind") not in AUTHORITY_CHANGE_KINDS:
            errors.append(f"authority_changes[{index}].authority_kind is unsupported")
        artifact_ref, artifact_path = _resolve_ref(
            game_repo,
            item.get("artifact"),
            f"authority_changes[{index}].artifact",
            errors,
        )
        if change_id and artifact_path is not None:
            authority_changes.append(
                {
                    "change_id": change_id,
                    "operation": item.get("operation"),
                    "authority_kind": item.get("authority_kind"),
                    "artifact": artifact_ref,
                }
            )

    pending = payload.get("pending_decisions")
    if not isinstance(pending, list):
        errors.append("alignment input.pending_decisions must be an array")
        pending = []
    pending_payloads: set[str] = set()
    superseded_payloads: set[str] = set()
    for index, raw in enumerate(pending):
        item = _keys(
            raw,
            f"pending_decisions[{index}]",
            {"decision_payload_sha256", "decision_card", "disposition"},
            errors,
        )
        digest = _sha(
            item.get("decision_payload_sha256"),
            f"pending_decisions[{index}].decision_payload_sha256",
            errors,
        )
        if digest in pending_payloads:
            errors.append(f"duplicate pending decision payload: {digest}")
        pending_payloads.add(digest)
        _resolve_ref(
            game_repo, item.get("decision_card"), f"pending_decisions[{index}].decision_card", errors
        )
        disposition = item.get("disposition")
        if disposition not in PENDING_DISPOSITIONS:
            errors.append(f"pending_decisions[{index}].disposition is unsupported")
        elif disposition == "SUPERSEDE_PENDING":
            superseded_payloads.add(digest)

    raw_deltas = payload.get("input_deltas")
    if not isinstance(raw_deltas, list) or not raw_deltas:
        errors.append("alignment input.input_deltas must be a non-empty array")
        raw_deltas = []
    delta_ids: set[str] = set()
    for index, raw in enumerate(raw_deltas):
        item = _keys(
            raw,
            f"input_deltas[{index}]",
            {
                "delta_id", "source_quote", "response_binding_ids",
                "classification", "target_authority_ids", "interpretation",
            },
            errors,
        )
        delta_id = _identifier(item.get("delta_id"), f"input_deltas[{index}].delta_id", errors)
        if delta_id in delta_ids:
            errors.append(f"duplicate delta_id: {delta_id}")
        delta_ids.add(delta_id)
        quote = _text(item.get("source_quote"), f"input_deltas[{index}].source_quote", errors)
        if quote and quote not in user_text:
            errors.append(f"input_deltas[{index}].source_quote is not exact user input text")
        delta_bindings = _string_list(
            item.get("response_binding_ids"),
            f"input_deltas[{index}].response_binding_ids",
            errors,
        )
        for binding_id in delta_bindings:
            if binding_id not in response_binding_ids:
                errors.append(
                    f"input_deltas[{index}] references unknown response binding_id {binding_id}"
                )
        if delta_bindings and quote not in {
            response_bindings[binding_id]["response_quote"]
            for binding_id in delta_bindings
            if binding_id in response_bindings
        }:
            errors.append(
                f"input_deltas[{index}].source_quote does not match its bound response"
            )
        if item.get("classification") not in DELTA_CLASSES:
            errors.append(f"input_deltas[{index}].classification is unsupported")
        targets = _string_list(
            item.get("target_authority_ids"),
            f"input_deltas[{index}].target_authority_ids",
            errors,
        )
        for target in targets:
            if target not in authority_ids:
                errors.append(f"input_deltas[{index}] references unknown authority_id {target}")
        _text(item.get("interpretation"), f"input_deltas[{index}].interpretation", errors)

    transition = payload.get("proposed_transition")
    if transition not in PROPOSED_TRANSITIONS:
        errors.append("alignment input.proposed_transition is unsupported")

    candidate = _keys(
        payload.get("candidate_output"),
        "alignment input.candidate_output",
        {"kind", "text", "sha256"},
        errors,
    )
    output_kind = candidate.get("kind", "")
    if output_kind not in OUTPUT_KINDS:
        errors.append("alignment input.candidate_output.kind is unsupported")
    output_text = _exact_text(
        candidate.get("text"), "alignment input.candidate_output.text", errors
    )
    output_sha = _sha(
        candidate.get("sha256"), "alignment input.candidate_output.sha256", errors
    )
    if output_text and output_sha and text_sha256(output_text) != output_sha:
        errors.append("alignment input candidate_output SHA does not match its exact text")

    claims = payload.get("output_claims")
    if not isinstance(claims, list) or not claims:
        errors.append("alignment input.output_claims must be a non-empty array")
        claims = []
    claim_ids: set[str] = set()
    claim_quotes: list[str] = []
    claims_by_id: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(claims):
        item = _keys(
            raw,
            f"output_claims[{index}]",
            {
                "claim_id", "output_quote", "provenance", "source_authority_ids",
                "source_response_binding_ids", "source_quotes",
            },
            errors,
        )
        claim_id = _identifier(item.get("claim_id"), f"output_claims[{index}].claim_id", errors)
        if claim_id in claim_ids:
            errors.append(f"duplicate output claim_id: {claim_id}")
        claim_ids.add(claim_id)
        quote = _text(item.get("output_quote"), f"output_claims[{index}].output_quote", errors)
        if quote and quote not in output_text:
            errors.append(f"output_claims[{index}].output_quote is not exact candidate output text")
        if quote:
            if "\n" in quote or "\r" in quote:
                errors.append(
                    f"output_claims[{index}].output_quote must be one exact candidate line"
                )
            claim_quotes.append(quote.strip())
        if claim_id:
            claims_by_id[claim_id] = item
        provenance = item.get("provenance")
        if provenance not in CLAIM_PROVENANCE:
            errors.append(f"output_claims[{index}].provenance is unsupported")
        source_ids = _string_list(
            item.get("source_authority_ids"),
            f"output_claims[{index}].source_authority_ids",
            errors,
        )
        for source_id in source_ids:
            if source_id not in authority_ids:
                errors.append(f"output_claims[{index}] references unknown authority_id {source_id}")
        source_binding_ids = _string_list(
            item.get("source_response_binding_ids"),
            f"output_claims[{index}].source_response_binding_ids",
            errors,
        )
        for binding_id in source_binding_ids:
            if binding_id not in response_binding_ids:
                errors.append(
                    f"output_claims[{index}] references unknown response binding_id {binding_id}"
                )
        source_quotes = _string_list(
            item.get("source_quotes"), f"output_claims[{index}].source_quotes", errors
        )
        authority_provenance = {
            "PRESERVED_AUTHORITY", "REPO_EVIDENCE", "REFERENCE_EVIDENCE"
        }
        if provenance in authority_provenance and not source_ids:
            errors.append(f"output_claims[{index}] requires a source authority")
        preserved_kinds = {
            "PRODUCT", "STUDIO_GAMEPLAY_SYSTEM", "GAMEPLAY_DECISION_CARD",
            "ACCEPTED_BASELINE",
        }
        if provenance == "PRESERVED_AUTHORITY" and source_ids and any(
            authority_kinds.get(source_id) not in preserved_kinds for source_id in source_ids
        ):
            errors.append(
                f"output_claims[{index}] PRESERVED_AUTHORITY must cite only active "
                "authority artifacts"
            )
        if provenance == "REPO_EVIDENCE" and source_ids and any(
            authority_kinds.get(source_id) != "REPO_EVIDENCE" for source_id in source_ids
        ):
            errors.append(
                f"output_claims[{index}] REPO_EVIDENCE must cite only REPO_EVIDENCE "
                "authorities"
            )
        if provenance == "REFERENCE_EVIDENCE":
            if source_ids and any(
                authority_kinds.get(source_id) != "REFERENCE_EVIDENCE"
                for source_id in source_ids
            ):
                errors.append(
                    f"output_claims[{index}] REFERENCE_EVIDENCE must cite only "
                    "REFERENCE_EVIDENCE authorities"
                )
            if not source_quotes:
                errors.append(
                    f"output_claims[{index}] REFERENCE_EVIDENCE requires exact source_quotes"
                )
        if provenance == "AI_SYNTHESIS" and not source_ids and not source_quotes:
            errors.append(
                f"output_claims[{index}] AI_SYNTHESIS requires the inputs it synthesizes"
            )
        if provenance == "NEW_USER_INPUT":
            if source_binding_ids:
                errors.append(
                    f"output_claims[{index}] NEW_USER_INPUT cannot cite a prior response binding"
                )
            if not source_quotes:
                errors.append(f"output_claims[{index}] requires exact user source_quotes")
            for source_quote in source_quotes:
                if source_quote not in user_text:
                    errors.append(
                        f"output_claims[{index}].source_quotes contains text absent from user input"
                    )
        if provenance == "BOUND_USER_RESPONSE":
            if not source_binding_ids:
                errors.append(
                    f"output_claims[{index}] BOUND_USER_RESPONSE requires a response binding"
                )
            required_quotes: set[str] = set()
            for binding_id in source_binding_ids:
                binding = response_bindings.get(binding_id)
                if binding is not None:
                    required_quotes.add(binding["response_quote"])
                    required_quotes.add(binding["selected_option_quote"])
            missing_quotes = sorted(required_quotes - set(source_quotes))
            if missing_quotes:
                errors.append(
                    f"output_claims[{index}] BOUND_USER_RESPONSE is missing exact "
                    "response/option source quotes: " + ", ".join(missing_quotes)
                )
        if provenance in authority_provenance:
            readable_sources: list[str] = []
            for source_id in source_ids:
                path = authority_paths.get(source_id)
                if path is not None:
                    try:
                        readable_sources.append(path.read_text(encoding="utf-8"))
                    except UnicodeDecodeError:
                        pass
            if source_quotes and not readable_sources:
                errors.append(
                    f"output_claims[{index}] source_quotes cannot be verified from its "
                    "cited authority artifacts"
                )
            for source_quote in source_quotes:
                if not any(
                    source_quote in source_text for source_text in readable_sources
                ):
                    errors.append(
                        f"output_claims[{index}].source_quotes contains text absent from "
                        "its cited authority artifacts"
                    )

    questions = payload.get("human_questions")
    if not isinstance(questions, list):
        errors.append("alignment input.human_questions must be an array")
        questions = []
    question_ids: set[str] = set()
    for index, raw in enumerate(questions):
        item = _keys(
            raw,
            f"human_questions[{index}]",
            {
                "question_id", "question_quote", "answer_options",
                "material_consequence", "searched_authority_ids", "why_unresolved",
            },
            errors,
        )
        question_id = _identifier(item.get("question_id"), f"human_questions[{index}].question_id", errors)
        if question_id in question_ids:
            errors.append(f"duplicate question_id: {question_id}")
        question_ids.add(question_id)
        quote = _text(item.get("question_quote"), f"human_questions[{index}].question_quote", errors)
        if quote and quote not in output_text:
            errors.append(f"human_questions[{index}].question_quote is not exact candidate output text")
        if quote and ("\n" in quote or "\r" in quote):
            errors.append(f"human_questions[{index}].question_quote must be one exact candidate line")
        output_lines = {line.strip() for line in output_text.splitlines() if line.strip()}
        if quote and quote.strip() not in output_lines:
            errors.append(f"human_questions[{index}].question_quote must cover a complete candidate line")
        options = item.get("answer_options")
        if not isinstance(options, list):
            errors.append(f"human_questions[{index}].answer_options must be an array")
            options = []
        option_ids: set[str] = set()
        option_tokens: set[str] = set()
        for option_index, raw_option in enumerate(options):
            option = _keys(
                raw_option,
                f"human_questions[{index}].answer_options[{option_index}]",
                {"option_id", "option_quote", "accepted_response_tokens"},
                errors,
            )
            option_id = _identifier(
                option.get("option_id"),
                f"human_questions[{index}].answer_options[{option_index}].option_id",
                errors,
            )
            if option_id in option_ids:
                errors.append(f"human_questions[{index}] has duplicate option_id {option_id}")
            option_ids.add(option_id)
            option_quote = _text(
                option.get("option_quote"),
                f"human_questions[{index}].answer_options[{option_index}].option_quote",
                errors,
            )
            if option_quote and option_quote not in output_lines:
                errors.append(
                    f"human_questions[{index}].answer_options[{option_index}].option_quote "
                    "must be one exact candidate line"
                )
            tokens = _string_list(
                option.get("accepted_response_tokens"),
                f"human_questions[{index}].answer_options[{option_index}].accepted_response_tokens",
                errors,
                allow_empty=False,
            )
            duplicates = option_tokens.intersection(tokens)
            if duplicates:
                errors.append(
                    f"human_questions[{index}] answer tokens select multiple options: "
                    + ", ".join(sorted(duplicates))
                )
            option_tokens.update(tokens)
        _text(item.get("material_consequence"), f"human_questions[{index}].material_consequence", errors)
        searched = _string_list(
            item.get("searched_authority_ids"),
            f"human_questions[{index}].searched_authority_ids",
            errors,
            allow_empty=False,
        )
        for source_id in searched:
            if source_id not in authority_ids:
                errors.append(f"human_questions[{index}] searched unknown authority_id {source_id}")
        _text(item.get("why_unresolved"), f"human_questions[{index}].why_unresolved", errors)

    if output_kind == "HUMAN_QUESTION" and not questions:
        errors.append("a HUMAN_QUESTION candidate must inventory its human question")
    if questions and transition != "REQUEST_HUMAN_RULING":
        errors.append("human questions require proposed_transition REQUEST_HUMAN_RULING")
    if transition == "REQUEST_HUMAN_RULING" and output_kind not in {
        "HUMAN_QUESTION", "DECISION_SURFACE"
    }:
        errors.append("REQUEST_HUMAN_RULING requires a human-facing question or decision surface")

    question_quotes = [
        str(item.get("question_quote", ""))
        for item in questions
        if isinstance(item, dict)
    ]
    uncovered_lines = [
        line
        for line in material_output_lines(output_text, question_quotes)
        if line not in claim_quotes
    ]
    for line in uncovered_lines:
        errors.append(
            "candidate output contains an uninventoried material line: " + line
        )
    duplicate_claim_quotes = {
        quote for quote in claim_quotes if claim_quotes.count(quote) > 1
    }
    for quote in sorted(duplicate_claim_quotes):
        errors.append("candidate material line has multiple provenance claims: " + quote)

    return {
        "interaction_id": interaction_id,
        "project_id": project_id,
        "author_context_id": author_context_id,
        "authority_ids": authority_ids,
        "response_binding_ids": response_binding_ids,
        "authority_change_ids": authority_change_ids,
        "authority_changes": authority_changes,
        "claim_ids": claim_ids,
        "claim_quotes": claim_quotes,
        "claims_by_id": claims_by_id,
        "candidate_output_kind": output_kind,
        "candidate_output_text": output_text,
        "candidate_output_sha256": output_sha,
        "human_questions": questions,
        "proposed_transition": transition,
        "superseded_payloads": superseded_payloads,
    }


def validate_alignment_review(
    game_repo: str | Path,
    alignment_input_path: str | Path,
    review_path: str | Path,
    *,
    expected_output_text: str | None = None,
    expected_output_kind: str | None = None,
    factory_revision: str | None = None,
) -> AlignmentValidationResult:
    repo = Path(game_repo).expanduser().resolve()
    if not repo.is_dir():
        raise AlignmentValidationError(f"game repo is not a directory: {repo}")
    revision = factory_revision or current_factory_revision()
    input_path = Path(alignment_input_path)
    if not input_path.is_absolute():
        input_path = repo / input_path
    review_file = Path(review_path)
    if not review_file.is_absolute():
        review_file = repo / review_file
    input_path = input_path.resolve()
    review_file = review_file.resolve()
    errors: list[str] = []
    alignment_input = _load_json(input_path, "semantic alignment input")
    parsed = _validate_alignment_input(
        repo, alignment_input, factory_revision=revision, errors=errors
    )

    review = _load_json(review_file, "semantic alignment review")
    required = {
        "schema_version", "review_id", "project_id", "factory_revision",
        "alignment_input", "reviewer_context_id", "reviewer_freshness",
        "checks", "independent_claim_inventory", "findings",
        "blocking_findings", "verdict", "reviewed_at",
    }
    _keys(review, "semantic alignment review", required, errors)
    if review.get("schema_version") != ALIGNMENT_REVIEW_VERSION:
        errors.append(
            f"semantic alignment review schema_version must be {ALIGNMENT_REVIEW_VERSION}"
        )
    _identifier(review.get("review_id"), "alignment review.review_id", errors)
    if review.get("project_id") != parsed.get("project_id"):
        errors.append("semantic alignment review project_id does not match input")
    if review.get("factory_revision") != revision:
        errors.append("semantic alignment review factory_revision does not match Factory HEAD")
    _, bound_input_path = _resolve_ref(
        repo, review.get("alignment_input"), "alignment review.alignment_input", errors
    )
    if bound_input_path is not None and bound_input_path != input_path:
        errors.append("semantic alignment review binds a different input artifact")
    reviewer = _identifier(
        review.get("reviewer_context_id"), "alignment review.reviewer_context_id", errors
    )
    if reviewer and reviewer == parsed.get("author_context_id"):
        errors.append("semantic alignment reviewer must be fresh from the candidate author")
    if review.get("reviewer_freshness") != "FRESH":
        errors.append("semantic alignment reviewer_freshness must be FRESH")
    _text(review.get("reviewed_at"), "alignment review.reviewed_at", errors)

    checks = _keys(
        review.get("checks"), "alignment review.checks", ALIGNMENT_CHECKS, errors
    )
    for check_id in ALIGNMENT_CHECKS:
        if checks.get(check_id) not in {"PASS", "BLOCK"}:
            errors.append(f"alignment review.checks.{check_id} must be PASS or BLOCK")

    inventory = review.get("independent_claim_inventory")
    if not isinstance(inventory, list) or not inventory:
        errors.append("alignment review.independent_claim_inventory must be a non-empty array")
        inventory = []
    candidate_material_lines = material_output_lines(
        parsed.get("candidate_output_text", ""),
        [
            str(item.get("question_quote", ""))
            for item in parsed.get("human_questions", [])
            if isinstance(item, dict)
        ],
    )
    claims_by_id = parsed.get("claims_by_id", {})
    inventory_ids: set[str] = set()
    inventory_quotes: list[str] = []
    blocked_inventory_ids: set[str] = set()
    for index, raw in enumerate(inventory):
        item = _keys(
            raw,
            f"alignment review.independent_claim_inventory[{index}]",
            {
                "review_claim_id", "candidate_output_quote", "author_claim_id",
                "assessed_provenance", "status", "rationale",
            },
            errors,
        )
        review_claim_id = _identifier(
            item.get("review_claim_id"),
            f"alignment review.independent_claim_inventory[{index}].review_claim_id",
            errors,
        )
        if review_claim_id in inventory_ids:
            errors.append(f"duplicate reviewer claim inventory id: {review_claim_id}")
        inventory_ids.add(review_claim_id)
        quote = _text(
            item.get("candidate_output_quote"),
            f"alignment review.independent_claim_inventory[{index}].candidate_output_quote",
            errors,
        )
        if quote and quote not in candidate_material_lines:
            errors.append(
                f"alignment review.independent_claim_inventory[{index}] must quote one "
                "complete material candidate line"
            )
        inventory_quotes.append(quote)
        author_claim_id = _identifier(
            item.get("author_claim_id"),
            f"alignment review.independent_claim_inventory[{index}].author_claim_id",
            errors,
        )
        author_claim = claims_by_id.get(author_claim_id)
        if author_claim is None:
            errors.append(
                f"alignment review.independent_claim_inventory[{index}] cites unknown "
                f"author claim {author_claim_id}"
            )
        elif author_claim.get("output_quote", "").strip() != quote:
            errors.append(
                f"alignment review.independent_claim_inventory[{index}] author claim "
                "does not cover the same complete candidate line"
            )
        assessed = item.get("assessed_provenance")
        if assessed not in CLAIM_PROVENANCE | {"MIXED_OR_UNCLEAR"}:
            errors.append(
                f"alignment review.independent_claim_inventory[{index}]."
                "assessed_provenance is unsupported"
            )
        status = item.get("status")
        if status not in {"PASS", "BLOCK"}:
            errors.append(
                f"alignment review.independent_claim_inventory[{index}].status is unsupported"
            )
        if status == "BLOCK":
            blocked_inventory_ids.add(review_claim_id)
        if (
            author_claim is not None
            and assessed in CLAIM_PROVENANCE
            and assessed != author_claim.get("provenance")
            and status != "BLOCK"
        ):
            errors.append(
                f"alignment review.independent_claim_inventory[{index}] disagrees with "
                "author provenance but is not BLOCK"
            )
        if assessed == "MIXED_OR_UNCLEAR" and status != "BLOCK":
            errors.append(
                f"alignment review.independent_claim_inventory[{index}] mixed provenance "
                "must BLOCK for candidate rewriting"
            )
        _text(
            item.get("rationale"),
            f"alignment review.independent_claim_inventory[{index}].rationale",
            errors,
        )
    if len(inventory_quotes) != len(set(inventory_quotes)):
        errors.append("alignment review independent claim inventory contains duplicate lines")
    missing_inventory_lines = set(candidate_material_lines) - set(inventory_quotes)
    extra_inventory_lines = set(inventory_quotes) - set(candidate_material_lines)
    for line in sorted(missing_inventory_lines):
        errors.append("reviewer omitted material candidate line: " + line)
    for line in sorted(extra_inventory_lines):
        errors.append("reviewer inventoried non-material candidate line: " + line)

    findings = review.get("findings")
    if not isinstance(findings, list) or not findings:
        errors.append("alignment review.findings must be a non-empty array")
        findings = []
    finding_ids: set[str] = set()
    blocked_finding_ids: set[str] = set()
    user_text = alignment_input.get("user_input", {}).get("text", "")
    candidate_text = parsed.get("candidate_output_text", "")
    authority_ids = set(parsed.get("authority_ids", set()))
    response_binding_ids = set(parsed.get("response_binding_ids", set()))
    authority_change_ids = set(parsed.get("authority_change_ids", set()))
    reviewed_binding_ids: set[str] = set()
    reviewed_change_ids: set[str] = set()
    for index, raw in enumerate(findings):
        item = _keys(
            raw,
            f"alignment review.findings[{index}]",
            {
                "finding_id", "status", "user_input_quote",
                "response_binding_ids", "authority_ids", "authority_change_ids",
                "candidate_output_quote", "rationale",
            },
            errors,
        )
        finding_id = _identifier(
            item.get("finding_id"), f"alignment review.findings[{index}].finding_id", errors
        )
        if finding_id in finding_ids:
            errors.append(f"duplicate alignment finding_id: {finding_id}")
        finding_ids.add(finding_id)
        status = item.get("status")
        if status not in {"PASS", "BLOCK"}:
            errors.append(f"alignment review.findings[{index}].status is unsupported")
        if status == "BLOCK":
            blocked_finding_ids.add(finding_id)
        user_quote = _text(
            item.get("user_input_quote"),
            f"alignment review.findings[{index}].user_input_quote",
            errors,
            allow_empty=status != "BLOCK",
        )
        if user_quote and user_quote not in user_text:
            errors.append(
                f"alignment review.findings[{index}].user_input_quote is not exact input text"
            )
        cited_bindings = _string_list(
            item.get("response_binding_ids"),
            f"alignment review.findings[{index}].response_binding_ids",
            errors,
        )
        for binding_id in cited_bindings:
            if binding_id not in response_binding_ids:
                errors.append(
                    f"alignment review.findings[{index}] cites unknown response binding_id "
                    f"{binding_id}"
                )
            else:
                reviewed_binding_ids.add(binding_id)
        cited_authorities = _string_list(
            item.get("authority_ids"),
            f"alignment review.findings[{index}].authority_ids",
            errors,
        )
        for authority_id in cited_authorities:
            if authority_id not in authority_ids:
                errors.append(
                    f"alignment review.findings[{index}] cites unknown authority_id {authority_id}"
                )
        cited_changes = _string_list(
            item.get("authority_change_ids"),
            f"alignment review.findings[{index}].authority_change_ids",
            errors,
        )
        for change_id in cited_changes:
            if change_id not in authority_change_ids:
                errors.append(
                    f"alignment review.findings[{index}] cites unknown authority change_id "
                    f"{change_id}"
                )
            else:
                reviewed_change_ids.add(change_id)
        output_quote = _text(
            item.get("candidate_output_quote"),
            f"alignment review.findings[{index}].candidate_output_quote",
            errors,
            allow_empty=status != "BLOCK",
        )
        if output_quote and output_quote not in candidate_text:
            errors.append(
                f"alignment review.findings[{index}].candidate_output_quote is not exact output text"
            )
        _text(item.get("rationale"), f"alignment review.findings[{index}].rationale", errors)

    for binding_id in sorted(response_binding_ids - reviewed_binding_ids):
        errors.append("alignment review omitted response binding: " + binding_id)
    for change_id in sorted(authority_change_ids - reviewed_change_ids):
        errors.append("alignment review omitted authority change: " + change_id)

    blockers = _string_list(
        review.get("blocking_findings"),
        "alignment review.blocking_findings",
        errors,
    )
    if set(blockers) != blocked_finding_ids:
        errors.append("alignment review.blocking_findings must name exactly every BLOCK finding")

    verdict = review.get("verdict", "")
    if verdict not in {
        PASS_ALIGNMENT, REVISE_BEFORE_USER, HUMAN_RULING_GENUINELY_REQUIRED
    }:
        errors.append("semantic alignment review verdict is unsupported")
    blocked_checks = {key for key, value in checks.items() if value == "BLOCK"}
    if blocked_inventory_ids and not blocked_checks.intersection(
        {"claim_provenance", "material_claim_coverage"}
    ):
        errors.append(
            "blocked independent claims require claim_provenance or "
            "material_claim_coverage BLOCK"
        )
    if not blocked_inventory_ids and checks.get("material_claim_coverage") == "BLOCK":
        errors.append(
            "material_claim_coverage BLOCK requires a blocked independent claim"
        )
    if verdict == REVISE_BEFORE_USER:
        if not blocked_checks or not blocked_finding_ids:
            errors.append("REVISE_BEFORE_USER requires BLOCK checks and findings")
    else:
        if blocked_checks or blocked_finding_ids:
            errors.append("a presentable alignment verdict cannot contain blockers")
    if verdict == HUMAN_RULING_GENUINELY_REQUIRED:
        if not parsed.get("human_questions"):
            errors.append("HUMAN_RULING_GENUINELY_REQUIRED requires an inventoried question")
        if parsed.get("proposed_transition") != "REQUEST_HUMAN_RULING":
            errors.append("human-ruling verdict requires REQUEST_HUMAN_RULING transition")

    if expected_output_text is not None and candidate_text != expected_output_text:
        errors.append("semantic alignment input does not bind the exact candidate output")
    if expected_output_kind is not None and parsed.get("candidate_output_kind") != expected_output_kind:
        errors.append("semantic alignment input candidate output kind is not the expected kind")

    status = verdict if not errors else REVISE_BEFORE_USER
    return AlignmentValidationResult(
        status=status,
        errors=errors,
        interaction_id=str(parsed.get("interaction_id", "")),
        project_id=str(parsed.get("project_id", "")),
        candidate_output_kind=str(parsed.get("candidate_output_kind", "")),
        candidate_output_sha256=str(parsed.get("candidate_output_sha256", "")),
        review_verdict=str(verdict),
        proposed_transition=str(parsed.get("proposed_transition", "")),
        authority_changes=list(parsed.get("authority_changes", [])),
    )


def _register_path(game_repo: Path) -> Path:
    return game_repo / DECISION_REGISTER_PATH


def _validate_register_payload(
    game_repo: Path,
    payload: dict[str, Any],
    errors: list[str],
) -> dict[str, dict[str, Any]]:
    _keys(
        payload,
        "Studio decision-card register",
        {"schema_version", "project_id", "entries", "updated_at"},
        errors,
    )
    if payload.get("schema_version") != DECISION_REGISTER_VERSION:
        errors.append(
            f"Studio decision-card register schema_version must be {DECISION_REGISTER_VERSION}"
        )
    _identifier(payload.get("project_id"), "decision register.project_id", errors)
    _text(payload.get("updated_at"), "decision register.updated_at", errors)
    entries = payload.get("entries")
    if not isinstance(entries, list):
        errors.append("decision register.entries must be an array")
        entries = []
    by_payload: dict[str, dict[str, Any]] = {}
    card_ids: set[str] = set()
    for index, raw in enumerate(entries):
        item = _keys(
            raw,
            f"decision register.entries[{index}]",
            {
                "card_id", "objective_id", "decision_payload_sha256",
                "decision_card", "state", "alignment_input", "alignment_review",
                "supersedes", "superseded_by", "recorded_at", "updated_at",
            },
            errors,
        )
        card_id = _identifier(item.get("card_id"), f"decision register.entries[{index}].card_id", errors)
        if card_id in card_ids:
            errors.append(f"duplicate registered card_id: {card_id}")
        card_ids.add(card_id)
        _identifier(item.get("objective_id"), f"decision register.entries[{index}].objective_id", errors)
        digest = _sha(
            item.get("decision_payload_sha256"),
            f"decision register.entries[{index}].decision_payload_sha256",
            errors,
        )
        if digest in by_payload:
            errors.append(f"duplicate registered decision payload: {digest}")
        by_payload[digest] = item
        _, card_path = _resolve_ref(
            game_repo, item.get("decision_card"), f"decision register.entries[{index}].decision_card", errors
        )
        _resolve_ref(
            game_repo, item.get("alignment_input"), f"decision register.entries[{index}].alignment_input", errors
        )
        _resolve_ref(
            game_repo, item.get("alignment_review"), f"decision register.entries[{index}].alignment_review", errors
        )
        state = item.get("state")
        if state not in REGISTER_STATES:
            errors.append(f"decision register.entries[{index}].state is unsupported")
        supersedes = _string_list(
            item.get("supersedes"), f"decision register.entries[{index}].supersedes", errors
        )
        for old_digest in supersedes:
            if SHA256_PATTERN.fullmatch(old_digest) is None:
                errors.append(f"decision register.entries[{index}].supersedes contains invalid SHA")
        superseded_by = _sha(
            item.get("superseded_by"),
            f"decision register.entries[{index}].superseded_by",
            errors,
            allow_empty=True,
        )
        if state == "SUPERSEDED" and not superseded_by:
            errors.append(f"decision register.entries[{index}] SUPERSEDED state requires superseded_by")
        if state != "SUPERSEDED" and superseded_by:
            errors.append(f"decision register.entries[{index}] non-superseded state cannot set superseded_by")
        _text(item.get("recorded_at"), f"decision register.entries[{index}].recorded_at", errors)
        _text(item.get("updated_at"), f"decision register.entries[{index}].updated_at", errors)
        if card_path is not None:
            try:
                card = _load_json(card_path, f"registered decision card {card_id}")
            except AlignmentValidationError as error:
                errors.append(str(error))
                card = {}
            if card.get("card_id") != card_id:
                errors.append(f"registered decision card {card_id} has a different card_id")
            if card.get("objective_id") != item.get("objective_id"):
                errors.append(f"registered decision card {card_id} has a different objective_id")
            if card.get("decision_payload_sha256") != digest:
                errors.append(f"registered decision card {card_id} has a different payload SHA")
            human_status = card.get("human_verdict", {}).get("status")
            if state == "PENDING" and human_status != "PENDING":
                errors.append(f"pending registered decision card {card_id} must have PENDING verdict")
            if state == "USER_APPROVED" and human_status != "USER_APPROVED":
                errors.append(f"approved registered decision card {card_id} lacks USER_APPROVED")
            if state == "USER_REJECTED" and human_status != "USER_REJECTED":
                errors.append(f"rejected registered decision card {card_id} lacks USER_REJECTED")

    for digest, item in by_payload.items():
        for old_digest in item.get("supersedes", []):
            old = by_payload.get(old_digest)
            if old is None:
                errors.append(f"decision payload {digest} supersedes unknown payload {old_digest}")
            elif old.get("state") != "SUPERSEDED" or old.get("superseded_by") != digest:
                errors.append(
                    f"decision payload {old_digest} is not symmetrically superseded by {digest}"
                )
        successor = item.get("superseded_by")
        if successor and successor not in by_payload:
            errors.append(f"decision payload {digest} points to unknown successor {successor}")

    for start in by_payload:
        seen: set[str] = set()
        cursor = start
        while cursor:
            if cursor in seen:
                errors.append(f"decision register supersession graph contains a cycle at {cursor}")
                break
            seen.add(cursor)
            next_item = by_payload.get(cursor)
            cursor = str(next_item.get("superseded_by", "")) if next_item else ""
    return by_payload


def load_decision_register(game_repo: str | Path) -> tuple[dict[str, Any], list[str]]:
    repo = Path(game_repo).expanduser().resolve()
    path = _register_path(repo)
    if not path.is_file():
        return {}, [f"Studio decision-card register is missing: {DECISION_REGISTER_PATH}"]
    try:
        payload = _load_json(path, "Studio decision-card register")
    except AlignmentValidationError as error:
        return {}, [str(error)]
    errors: list[str] = []
    _validate_register_payload(repo, payload, errors)
    return payload, errors


def require_registered_card(
    game_repo: str | Path,
    card_path: str | Path,
    *,
    required_state: str,
    errors: list[str],
) -> dict[str, Any]:
    repo = Path(game_repo).expanduser().resolve()
    card_file = Path(card_path)
    if not card_file.is_absolute():
        card_file = repo / card_file
    card_file = card_file.resolve()
    try:
        card = _load_json(card_file, "gameplay decision card")
    except AlignmentValidationError as error:
        errors.append(str(error))
        return {}
    payload, register_errors = load_decision_register(repo)
    errors.extend(register_errors)
    if register_errors:
        return {}
    by_payload = {
        item.get("decision_payload_sha256"): item
        for item in payload.get("entries", [])
        if isinstance(item, dict)
    }
    digest = card.get("decision_payload_sha256")
    entry = by_payload.get(digest)
    if entry is None:
        errors.append("Studio decision card is not present in the decision-card register")
        return {}
    if entry.get("state") != required_state:
        if entry.get("state") == "SUPERSEDED":
            errors.append(
                "Studio decision card payload is superseded by "
                + str(entry.get("superseded_by", ""))
            )
        else:
            errors.append(
                f"Studio decision card register state must be {required_state}, "
                f"not {entry.get('state')}"
            )
    registered_path = (repo / entry.get("decision_card", {}).get("path", "")).resolve()
    if registered_path != card_file:
        errors.append("Studio decision-card register points to a different card path")
    if entry.get("decision_card", {}).get("sha256") != file_sha256(card_file):
        errors.append("Studio decision-card register does not bind the current card bytes")
    return entry


def register_pending_card(
    game_repo: str | Path,
    card_path: str | Path,
    alignment_input_path: str | Path,
    alignment_review_path: str | Path,
    *,
    expected_output_text: str,
    supersede_payloads: list[str],
    recorded_at: str,
) -> Path:
    repo = Path(game_repo).expanduser().resolve()
    card_file = Path(card_path)
    if not card_file.is_absolute():
        card_file = repo / card_file
    input_file = Path(alignment_input_path)
    if not input_file.is_absolute():
        input_file = repo / input_file
    review_file = Path(alignment_review_path)
    if not review_file.is_absolute():
        review_file = repo / review_file
    card_file = card_file.resolve()
    input_file = input_file.resolve()
    review_file = review_file.resolve()
    card = _load_json(card_file, "gameplay decision card")
    if card.get("routing") != "STUDIO_WHOLE_GAME":
        raise AlignmentValidationError("only Studio whole-game cards use the Studio register")
    if card.get("human_verdict", {}).get("status") != "PENDING":
        raise AlignmentValidationError("a newly registered Studio decision card must be PENDING")
    revision = current_factory_revision()
    if card.get("factory_revision") != revision:
        raise AlignmentValidationError("decision card factory_revision does not match Factory HEAD")
    digest = str(card.get("decision_payload_sha256", ""))
    if SHA256_PATTERN.fullmatch(digest) is None:
        raise AlignmentValidationError("decision card has no valid decision payload SHA")
    result = validate_alignment_review(
        repo,
        input_file,
        review_file,
        expected_output_text=expected_output_text,
        expected_output_kind="DECISION_SURFACE",
        factory_revision=revision,
    )
    if result.errors or result.status != HUMAN_RULING_GENUINELY_REQUIRED:
        detail = "; ".join(result.errors) or (
            "decision surfaces require HUMAN_RULING_GENUINELY_REQUIRED alignment verdict"
        )
        raise AlignmentValidationError(detail)
    alignment_input = _load_json(input_file, "semantic alignment input")
    expected_supersedes = {
        item.get("decision_payload_sha256")
        for item in alignment_input.get("pending_decisions", [])
        if isinstance(item, dict) and item.get("disposition") == "SUPERSEDE_PENDING"
    }
    if set(supersede_payloads) != expected_supersedes:
        raise AlignmentValidationError(
            "register supersede payloads must exactly match alignment pending dispositions"
        )
    pending_by_payload = {
        item.get("decision_payload_sha256"): item
        for item in alignment_input.get("pending_decisions", [])
        if isinstance(item, dict)
    }

    register_path = _register_path(repo)
    if register_path.is_file():
        register = _load_json(register_path, "Studio decision-card register")
        errors: list[str] = []
        by_payload = _validate_register_payload(repo, register, errors)
        if errors:
            raise AlignmentValidationError("; ".join(errors))
        if register.get("project_id") != card.get("project_id"):
            raise AlignmentValidationError("decision register belongs to another project")
    else:
        register = {
            "schema_version": DECISION_REGISTER_VERSION,
            "project_id": card.get("project_id"),
            "entries": [],
            "updated_at": recorded_at,
        }
        by_payload = {}
    if digest in by_payload:
        raise AlignmentValidationError("decision payload is already registered")
    for old_digest in supersede_payloads:
        old = by_payload.get(old_digest)
        if old is None:
            pending_item = pending_by_payload.get(old_digest)
            if not isinstance(pending_item, dict):
                raise AlignmentValidationError(
                    f"cannot supersede unknown pending payload {old_digest}"
                )
            pending_ref = pending_item.get("decision_card", {})
            pending_path = (repo / str(pending_ref.get("path", ""))).resolve()
            pending_card = _load_json(pending_path, "pre-register pending decision card")
            if pending_card.get("decision_payload_sha256") != old_digest:
                raise AlignmentValidationError(
                    f"pre-register pending card does not match payload {old_digest}"
                )
            if pending_card.get("human_verdict", {}).get("status") != "PENDING":
                raise AlignmentValidationError(
                    f"only a PENDING pre-register card may be imported as superseded: {old_digest}"
                )
            old = {
                "card_id": pending_card.get("card_id"),
                "objective_id": pending_card.get("objective_id"),
                "decision_payload_sha256": old_digest,
                "decision_card": path_ref(repo, pending_path),
                "state": "SUPERSEDED",
                "alignment_input": path_ref(repo, input_file),
                "alignment_review": path_ref(repo, review_file),
                "supersedes": [],
                "superseded_by": digest,
                "recorded_at": recorded_at,
                "updated_at": recorded_at,
            }
            register["entries"].append(old)
            by_payload[old_digest] = old
            continue
        if old.get("state") != "PENDING":
            raise AlignmentValidationError(
                f"only PENDING payloads may be superseded; {old_digest} is {old.get('state')}"
            )
        old["state"] = "SUPERSEDED"
        old["superseded_by"] = digest
        old["updated_at"] = recorded_at
    register["entries"].append(
        {
            "card_id": card.get("card_id"),
            "objective_id": card.get("objective_id"),
            "decision_payload_sha256": digest,
            "decision_card": path_ref(repo, card_file),
            "state": "PENDING",
            "alignment_input": path_ref(repo, input_file),
            "alignment_review": path_ref(repo, review_file),
            "supersedes": list(supersede_payloads),
            "superseded_by": "",
            "recorded_at": recorded_at,
            "updated_at": recorded_at,
        }
    )
    register["updated_at"] = recorded_at
    errors = []
    _validate_register_payload(repo, register, errors)
    if errors:
        raise AlignmentValidationError("; ".join(errors))
    register_path.parent.mkdir(parents=True, exist_ok=True)
    register_path.write_text(
        json.dumps(register, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return register_path


def record_card_verdict(
    game_repo: str | Path,
    card_path: str | Path,
    *,
    verdict_token: str,
    recorded_at: str,
) -> Path:
    repo = Path(game_repo).expanduser().resolve()
    card_file = Path(card_path)
    if not card_file.is_absolute():
        card_file = repo / card_file
    card_file = card_file.resolve()
    card = _load_json(card_file, "gameplay decision card")
    digest = str(card.get("decision_payload_sha256", ""))
    parts = verdict_token.strip().split()
    if len(parts) != 2 or parts[0] not in {"USER_APPROVED", "USER_REJECTED"}:
        raise AlignmentValidationError(
            "verdict token must be USER_APPROVED or USER_REJECTED plus payload SHA"
        )
    if parts[1] != digest:
        raise AlignmentValidationError("verdict token does not bind this decision payload")
    register, errors = load_decision_register(repo)
    if errors:
        raise AlignmentValidationError("; ".join(errors))
    entry = next(
        (
            item for item in register.get("entries", [])
            if item.get("decision_payload_sha256") == digest
        ),
        None,
    )
    if entry is None:
        raise AlignmentValidationError("decision payload is not registered")
    if entry.get("state") != "PENDING":
        if entry.get("state") == "SUPERSEDED":
            raise AlignmentValidationError(
                "cannot record verdict for superseded payload; successor is "
                + str(entry.get("superseded_by", ""))
            )
        raise AlignmentValidationError(
            f"decision payload is not pending; current state is {entry.get('state')}"
        )
    card["human_verdict"] = {
        "status": parts[0],
        "source_text": verdict_token.strip(),
        "recorded_at": recorded_at,
    }
    card_file.write_text(
        json.dumps(card, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    entry["state"] = parts[0]
    entry["decision_card"] = path_ref(repo, card_file)
    entry["updated_at"] = recorded_at
    register["updated_at"] = recorded_at
    register_path = _register_path(repo)
    register_path.write_text(
        json.dumps(register, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    validation_errors: list[str] = []
    _validate_register_payload(repo, register, validation_errors)
    if validation_errors:
        raise AlignmentValidationError("; ".join(validation_errors))
    return card_file


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser(
        "validate", help="validate one authored turn and its fresh semantic review"
    )
    validate.add_argument("--game-repo", required=True)
    validate.add_argument("--input", required=True)
    validate.add_argument("--review", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "validate":
        try:
            result = validate_alignment_review(
                args.game_repo, args.input, args.review
            )
        except AlignmentValidationError as error:
            print(f"ERROR: {error}", file=sys.stderr)
            return 2
        print(result.status)
        for error in result.errors:
            print(f"- {error}")
        return 0 if not result.errors and result.status in PRESENTABLE_VERDICTS else 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
