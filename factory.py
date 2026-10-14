#!/usr/bin/env python3
"""Versioned Factory shared entry (v2 / explicit GPT-6 v3); specialist CLIs remain independently callable."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from factory_core.catalog import CAPABILITIES
from factory_core.refs import FactoryError, game_root, read_json, reference

ROOT = Path(__file__).resolve().parent


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    for name in ("inspect", "context", "checkpoint", "migrate"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--game-repo", "--project-root", dest="game_repo", default=".")
        if name in ("inspect", "context"):
            cmd.add_argument("--task-id")
        if name == "inspect":
            cmd.add_argument("--result", help="existing Asset/Sound status path inside game")
        if name == "context":
            cmd.add_argument("--capability", choices=CAPABILITIES, required=True)
            cmd.add_argument("--task", required=True)
            cmd.add_argument("--role", default="author", choices=["author", "human", "intent_experience", "completeness_project", "blind_observer"])
            cmd.add_argument("--design", help="complete design package path inside game")
            cmd.add_argument("--method", action="append", default=[], help="expand an optional method id (GPT-6 workflow only)")
        if name == "checkpoint":
            cmd.add_argument("--input", required=True, help="checkpoint request JSON")
        if name == "migrate":
            modes = cmd.add_mutually_exclusive_group()
            modes.add_argument("--check", action="store_true")
            modes.add_argument("--apply", action="store_true")
            cmd.add_argument("--project-id", required=True)
            cmd.add_argument("--expected", help="exact preview source digest; required for --apply")
            cmd.add_argument("--authority", action="append", default=[], help="additional adopted authority path, repeatable")
            cmd.add_argument("--workflow", choices=("v2", "gpt6"), default="v2", help="explicit contract selection; never inferred from model name")
    cmd = sub.add_parser("mode", help="show or set the USER-selected authorship mode (v3 only)")
    cmd.add_argument("--game-repo", "--project-root", dest="game_repo", default=".")
    cmd.add_argument("--set", choices=("collaborative", "autonomous", "closed_beta"), help="requires --source and --quote from a raw USER message")
    cmd.add_argument("--product", help="closed_beta: the product the USER delegates to the closed beta")
    cmd.add_argument("--seat", action="append", default=[], help="closed_beta: delegated seat (DESIGN_APPROVAL, INTERNAL_PLAYTEST_VERDICT); default both")
    cmd.add_argument("--source", help="game-owned JSON of the raw USER message: {\"role\": \"user\", \"content\": ...}")
    cmd.add_argument("--quote", help="exact USER words selecting the mode")
    cmd = sub.add_parser("benchmark")
    cmd.add_argument("--suite", default=str(ROOT / "factory_core/benchmarks/suite.json"))
    cmd.add_argument("--output-root", required=True)
    modes=cmd.add_mutually_exclusive_group()
    modes.add_argument("--run", action="store_true")
    modes.add_argument("--resume", action="store_true", help="resume the exact interrupted trial; retain all failed attempts")
    cmd.add_argument("--human-quality")
    cmd.add_argument("--report", action="store_true", help="render a full-output anonymous view after the fixed schedule finishes")
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "benchmark":
            from factory_core.benchmark import run, summarize
            suite = read_json(Path(args.suite))
            output = Path(args.output_root).expanduser().resolve()
            result = run(suite, ROOT, output, resume=args.resume) if args.run or args.resume else summarize(suite, output,
                read_json(Path(args.human_quality)) if args.human_quality else None)
            if args.report:
                from factory_core.benchmark_report import render
                result['reports']=render(suite,output)
        else:
            game = game_root(args.game_repo, ROOT)
            roots = {"game": game, "factory": ROOT}
            if args.command == "inspect":
                from factory_core.context import inspect, provider_result
                result = provider_result(roots, args.result) if args.result else inspect(roots, args.task_id)
            elif args.command == "context":
                from factory_core.context import context
                result = context(roots, args.capability, args.task, args.role, args.task_id,
                                 reference(game, args.design) if args.design else None, methods=args.method)
            elif args.command == "mode":
                from factory_core.authorship import mode, set_mode
                from factory_core.state import project
                if project(game)["workflow_version"] != 3:
                    raise FactoryError("MIGRATION_REQUIRED", "authorship modes belong to the explicit v3 workflow")
                if args.set:
                    if not args.source or not args.quote:
                        raise FactoryError("HUMAN_RULING_REQUIRED", "--set needs the raw USER message (--source) and exact --quote")
                    result = set_mode(roots, args.set, args.source, args.quote, args.product, args.seat or None)
                else:
                    result = {"status": "MODE", "mode": mode(roots)}
            elif args.command == "checkpoint":
                from factory_core.state import checkpoint
                result = checkpoint(roots, read_json(Path(args.input)))
            else:
                from factory_core.migration import preview, apply
                if args.apply and not args.expected:
                    raise FactoryError("PREVIEW_REQUIRED", "--apply requires the reviewed --expected source digest")
                if args.workflow == "gpt6":
                    from factory_core.migration_gpt6 import preview, apply
                result = apply(game, ROOT, args.project_id, args.expected, args.authority) if args.apply else preview(game, ROOT, args.project_id, args.authority)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        blocked = bool(result.get("blockers")) or result.get("ok") is False or result.get("status", "").endswith(("REQUIRED", "INVALID", "INCOMPLETE", "NOT_MET", "NOT_RUN"))
        return 2 if blocked else 0
    except (FactoryError, OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        print(json.dumps({"status": getattr(exc, "code", "INVALID_INPUT"), "message": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
