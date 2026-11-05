#!/usr/bin/env python3
"""Standalone player-text clarity workflow. No Factory link, Git or migration required."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from factory_core.refs import FactoryError, confined, exclusive_json
from player_text import workflow as w


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "seal", "reader-packet", "check", "verify"):
        command = sub.add_parser(name)
        command.add_argument("--project-root", "--game-repo", dest="root", required=True)
        if name == "prepare": command.add_argument("--inventory", required=True)
        if name == "seal":
            command.add_argument("--packet", required=True)
            command.add_argument("--producer-context", action="append", required=True)
        if name in ("reader-packet", "check"): command.add_argument("--candidate", required=True)
        if name == "check":
            command.add_argument("--reading", required=True)
            command.add_argument("--backcheck", required=True)
        if name == "verify": command.add_argument("--receipt", required=True)
        if name in ("prepare", "seal", "check"):
            command.add_argument("--out", required=name != "check", help="new project-relative evidence path; never overwritten")
    args = parser.parse_args(argv)
    try:
        root = w.project_root(args.root)
        if args.command == "prepare": result = w.prepare(root, args.inventory)
        elif args.command == "seal": result = w.seal(root, args.packet, args.producer_context)
        elif args.command == "reader-packet": result = w.reading_packet(w.candidate(root, args.candidate)[1])
        elif args.command == "check": result = w.check(root, args.candidate, args.reading, args.backcheck)
        else: result = w.verify(root, args.receipt)
        if getattr(args, "out", None): exclusive_json(confined(root, args.out), result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (FactoryError, OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        print(json.dumps({"status": getattr(exc, "code", "INVALID_INPUT"), "message": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
