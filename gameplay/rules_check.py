#!/usr/bin/env python3
"""Executable rules-model check: invariants and worked-example consistency.

A gameplay design states rules in prose and illustrates them with worked
examples (laps, witness boards, mock frames). Prose and examples drift apart
silently: an example shows a move the rules forbid, or a state the rules can
never reach. This check makes the design ship a game-owned executable rules
model plus a command that exercises it, and records the command's report:

- invariants: properties that must hold in every reachable state (capacity never
  exceeded, currency never negative, a legal action always exists ...), each with
  the number of states/cases actually checked and the violations found;
- examples: every worked example the design relies on, replayed through the
  model and judged CONSISTENT or INCONSISTENT with the stated rules.

The Factory never decides which invariants a game needs or whether it is fun or
balanced; it checks that the evidence exists, is bound to the exact model, and
reports no violation. Reviewers judge whether the invariants and examples cover
the design. Required for studio/gameplay designs in the AUTONOMOUS authorship
mode; optional (validated when present) in COLLABORATIVE mode.

Usage (command after --, run from the game root):
  python3 gameplay/rules_check.py run --game-repo G --model rules/model.py \
      --output design/gameplay/RULES_CHECK.json -- python3 rules/model.py --report
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from factory_core.refs import FactoryError, confined, encoded, fail, read_json, reference, resolve_ref

REPORT_VERSION = "gameplay_rules_report.v1"
RECORD_VERSION = "gameplay_rules_check.v1"
EXAMPLE_STATUSES = ("CONSISTENT", "INCONSISTENT")
COVERED_CAPABILITIES = ("studio", "gameplay")
TIMEOUT_SECONDS = 1800


def _text(value, where):
    if not isinstance(value, str) or not value.strip():
        fail("INVALID_RULES_REPORT", f"{where}: nonempty text required")
    return value


def _count(value, where, minimum):
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        fail("INVALID_RULES_REPORT", f"{where}: integer >= {minimum} required")
    return value


def _shape(value, required, optional, where):
    if not isinstance(value, dict) or set(required) - set(value) or set(value) - set(required) - set(optional):
        fail("INVALID_RULES_REPORT", f"{where}: requires {sorted(required)}; optional {sorted(optional)}")


def validate_report(report: dict, where: str = "report") -> dict:
    """Shape of the command's stdout report; extra sections are owned by later checks."""
    _shape(report, {"schema_version", "invariants", "examples"}, {"balance_targets"}, where)
    if report["schema_version"] != REPORT_VERSION:
        fail("INVALID_RULES_REPORT", f"{where}: schema_version must be {REPORT_VERSION}")
    invariants = report["invariants"]
    if not isinstance(invariants, list) or not invariants:
        fail("INVALID_RULES_REPORT", f"{where}: at least one invariant required")
    seen = set()
    for index, item in enumerate(invariants):
        place = f"{where}.invariants[{index}]"
        _shape(item, {"id", "statement", "checked_cases", "violations"}, {"counterexample"}, place)
        identity = _text(item["id"], f"{place}.id")
        if identity in seen:
            fail("INVALID_RULES_REPORT", f"{where}: duplicate invariant {identity}")
        seen.add(identity)
        _text(item["statement"], f"{place}.statement")
        _count(item["checked_cases"], f"{place}.checked_cases", 1)
        if _count(item["violations"], f"{place}.violations", 0) and "counterexample" not in item:
            fail("INVALID_RULES_REPORT", f"{place}: a violation must carry its counterexample")
    examples = report["examples"]
    if not isinstance(examples, list):
        fail("INVALID_RULES_REPORT", f"{where}.examples must be a list")
    seen = set()
    for index, item in enumerate(examples):
        place = f"{where}.examples[{index}]"
        _shape(item, {"id", "statement", "status", "detail"}, (), place)
        identity = _text(item["id"], f"{place}.id")
        if identity in seen:
            fail("INVALID_RULES_REPORT", f"{where}: duplicate example {identity}")
        seen.add(identity)
        _text(item["statement"], f"{place}.statement")
        _text(item["detail"], f"{place}.detail")
        if item["status"] not in EXAMPLE_STATUSES:
            fail("INVALID_RULES_REPORT", f"{place}.status must be one of {EXAMPLE_STATUSES}")
    return report


def run(game_repo: str, model: str, command: list[str], output: str) -> dict:
    """Execute the game-owned command and publish a record bound to the exact model."""
    game = Path(game_repo).resolve()
    if not command:
        fail("INVALID_RULES_COMMAND", "give the command after --")
    model_ref = reference(game, model)
    completed = subprocess.run(command, cwd=game, text=True, capture_output=True, timeout=TIMEOUT_SECONDS)
    if completed.returncode:
        fail("RULES_COMMAND_FAILED", f"exit {completed.returncode}: {completed.stderr.strip()[-2000:]}")
    try:
        report = json.loads(completed.stdout)
    except ValueError as error:
        fail("INVALID_RULES_REPORT", f"stdout must be one {REPORT_VERSION} JSON object: {error}")
    validate_report(report)
    if reference(game, model) != model_ref:
        fail("RULES_MODEL_CHANGED", "the model changed while the command ran; rerun")
    record = {"schema_version": RECORD_VERSION, "model": model_ref, "command": command, "report": report}
    path = confined(game, output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encoded(record))
    return {"status": "RULES_CHECK_RECORDED", "record": reference(game, output), **summary(report)}


def summary(report: dict) -> dict:
    return {"invariants": len(report["invariants"]),
            "violations": sum(item["violations"] for item in report["invariants"]),
            "examples": len(report["examples"]),
            "inconsistent_examples": [item["id"] for item in report["examples"] if item["status"] != "CONSISTENT"]}


def validate_design(roots: dict, design: dict, mode: str) -> None:
    """Design gate: bound, current, violation-free; mandatory in AUTONOMOUS mode."""
    ref = design.get("rules_check")
    autonomous = mode == "AUTONOMOUS"
    if ref is None:
        if autonomous and design["capability"] in COVERED_CAPABILITIES:
            fail("RULES_CHECK_REQUIRED", "AUTONOMOUS mode: bind an executable rules-model check (invariants and worked examples)")
        return
    if not isinstance(ref, dict) or ref.get("scope") != "game" or ref not in design["inputs"]:
        fail("INVALID_RULES_CHECK", "rules_check must be a game-owned design input so it is sealed in the review closure")
    record = read_json(resolve_ref(roots, ref))
    _shape(record, {"schema_version", "model", "command", "report"}, (), "rules_check")
    if record["schema_version"] != RECORD_VERSION:
        fail("INVALID_RULES_CHECK", f"schema_version must be {RECORD_VERSION}; record it with gameplay/rules_check.py run")
    if not isinstance(record["command"], list) or not record["command"] or not all(isinstance(x, str) and x for x in record["command"]):
        fail("INVALID_RULES_CHECK", "command must be the exact argument list that produced the report")
    model = record["model"]
    if not isinstance(model, dict) or model.get("scope") != "game" or model not in design["inputs"] + design["artifacts"]:
        fail("INVALID_RULES_CHECK", "the rules model must itself be a sealed design input or artifact")
    try:
        resolve_ref(roots, model)
    except FactoryError:
        fail("STALE_RULES_CHECK", "the rules model changed after its check; rerun gameplay/rules_check.py")
    report = validate_report(record["report"], "rules_check.report")
    counts = summary(report)
    if counts["violations"]:
        broken = [item["id"] for item in report["invariants"] if item["violations"]]
        fail("RULES_INVARIANT_VIOLATED", f"invariants with violations: {broken}")
    if counts["inconsistent_examples"]:
        fail("RULES_EXAMPLE_INCONSISTENT", f"worked examples contradict the rules: {counts['inconsistent_examples']}")
    if autonomous and not report["examples"]:
        fail("RULES_EXAMPLES_REQUIRED", "AUTONOMOUS mode: replay every worked example the design relies on")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="action", required=True)
    cmd = sub.add_parser("run")
    cmd.add_argument("--game-repo", required=True)
    cmd.add_argument("--model", required=True, help="game-relative path of the executable rules model")
    cmd.add_argument("--output", required=True, help="game-relative path of the record to publish")
    cmd.add_argument("command", nargs=argparse.REMAINDER, help="-- then the command that prints the report")
    args = parser.parse_args(argv)
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    try:
        result = run(args.game_repo, args.model, command, args.output)
    except (FactoryError, OSError, subprocess.TimeoutExpired) as error:
        print(json.dumps({"status": getattr(error, "code", "RULES_COMMAND_FAILED"), "message": str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not result["violations"] and not result["inconsistent_examples"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
