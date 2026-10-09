#!/usr/bin/env python3
"""Product Factory evidence/claim CLI. Qualitative value judgments are not computed."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from factory_core.refs import FactoryError, game_root
from product import intent, value


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    for name in ("start", "inspect", "prepare", "record", "check", "gate"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--game-repo", "--project-root", dest="game_repo", required=True)
        if name == "start":
            cmd.add_argument("--dry-run", action="store_true")
        if name in ("prepare", "record"):
            cmd.add_argument("--input", required=True)
        if name == "record":
            cmd.add_argument("--review", action="append", required=True)
        if name in ("check", "gate"):
            cmd.add_argument("--result", required=True)
        if name == "gate":
            cmd.add_argument("--build", required=True)
    args = p.parse_args(argv)
    try:
        roots = {"game": game_root(args.game_repo, value.ROOT), "factory": value.ROOT}
        if args.command == "start":
            out = intent.start(roots, dry_run=args.dry_run)
        elif args.command == "inspect":
            out = value.inspect(roots)
        elif args.command == "prepare":
            out = value.prepare(roots, args.input)
        elif args.command == "record":
            out = value.record(roots, args.input, args.review)
        elif args.command == "check":
            out = value.check(roots, args.result)
        else:
            out = value.gate(roots, args.result, args.build)
        print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))
        return 2 if out.get("ok") is False else 0
    except (FactoryError, OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        print(json.dumps({"status": getattr(exc, "code", "INVALID_PRODUCT_INPUT"), "message": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
