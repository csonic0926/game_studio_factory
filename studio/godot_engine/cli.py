"""Unified v1-compatible and v2 automation command line."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from typing import Any

from . import v1
from .api import GodotSession, serve_jsonl
from .bridge import BridgePlan, bridge_check, bridge_install, bridge_remove, bridge_upgrade, profile_validate
from .build import run_build
from .common import GodotAutomationError, OperationResult, load_json, resolve_game_repo, resolve_in_repo
from .doctor import run_doctor
from .evidence import recover_evidence, verify_evidence
from .scenario import replay_scenario, run_scenario, validate_scenario_file
from .visual import compare_visual


LEGACY_COMMANDS = {"probe", "import-check", "run", "export"}


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--game-repo", required=True)
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--godot-bin", default=None)


def _scenario_run_args(parser: argparse.ArgumentParser) -> None:
    _common(parser)
    parser.add_argument("--operation-id", required=True)
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--profile", default=None)
    parser.add_argument("--runtime-kind", choices=("editor", "debug_export", "release_export"), default="editor")
    parser.add_argument("--build", default=None)
    parser.add_argument("--timeout-seconds", type=float, default=120.0)
    parser.add_argument("--windowed", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    doctor = commands.add_parser("doctor")
    _common(doctor)
    doctor.add_argument("--operation-id", required=True)
    doctor.add_argument("--profile", default=None)
    doctor.add_argument("--require-evidence", action="append", default=[])
    doctor.add_argument("--require-capability", action="append", default=[])

    bridge = commands.add_parser("bridge")
    bridge_commands = bridge.add_subparsers(dest="bridge_command", required=True)
    for name in ("check", "install", "upgrade", "remove"):
        child = bridge_commands.add_parser(name)
        child.add_argument("--game-repo", required=True)
        child.add_argument("--project-dir", default=".")
        if name in {"install", "upgrade", "remove"}:
            child.add_argument("--apply", action="store_true")
            child.add_argument("--operation-id", default=None)
        if name == "install":
            child.add_argument("--autoload", action="store_true")
    profile = bridge_commands.add_parser("profile-validate")
    profile.add_argument("--profile", required=True)

    scenario = commands.add_parser("scenario")
    scenario_commands = scenario.add_subparsers(dest="scenario_command", required=True)
    validate = scenario_commands.add_parser("validate")
    validate.add_argument("--scenario", required=True)
    scenario_run = scenario_commands.add_parser("run")
    _scenario_run_args(scenario_run)
    replay = scenario_commands.add_parser("replay")
    _scenario_run_args(replay)
    replay.add_argument("--reference-trace", required=True)

    session = commands.add_parser("session")
    session_commands = session.add_subparsers(dest="session_command", required=True)
    serve = session_commands.add_parser("serve")
    _common(serve)
    serve.add_argument("--operation-id", required=True)
    serve.add_argument("--profile", default=None)
    serve.add_argument("--runtime-kind", choices=("editor", "debug_export"), default="editor")
    serve.add_argument("--build", default=None)
    serve.add_argument("--windowed", action="store_true")
    serve.add_argument("--fixed-fps", type=int, default=60)
    serve.add_argument("--seed", type=int, default=None)
    serve.add_argument("--initial-checkpoint", default=None)

    visual = commands.add_parser("visual")
    visual_commands = visual.add_subparsers(dest="visual_command", required=True)
    compare = visual_commands.add_parser("compare")
    _common(compare)
    compare.add_argument("--operation-id", required=True)
    compare.add_argument("--baseline", required=True)
    compare.add_argument("--actual-image", required=True)
    compare.add_argument("--actual-structure", required=True)
    compare.add_argument("--actual-environment", required=True, help="strict JSON file")
    compare.add_argument("--timeout-seconds", type=float, default=60.0)

    build = commands.add_parser("build")
    build_commands = build.add_subparsers(dest="build_command", required=True)
    run = build_commands.add_parser("run")
    _common(run)
    run.add_argument("--operation-id", required=True)
    run.add_argument("--build", required=True)
    run.add_argument("--mode", choices=("debug", "release"), required=True)
    run.add_argument("--argument", action="append", default=[])
    run.add_argument("--timeout-seconds", type=float, default=30.0)
    run.add_argument("--expected-exit-code", type=int, default=0)
    run.add_argument("--expect-output", action="append", default=[])

    evidence = commands.add_parser("evidence")
    evidence_commands = evidence.add_subparsers(dest="evidence_command", required=True)
    verify = evidence_commands.add_parser("verify")
    verify.add_argument("--game-repo", required=True)
    verify.add_argument("--evidence", required=True)
    recover = evidence_commands.add_parser("recover")
    recover.add_argument("--game-repo", required=True)
    recover.add_argument("--operation-id", required=True)
    return parser


def _public_result(result: Any) -> dict[str, Any]:
    if isinstance(result, BridgePlan):
        return result.public()
    if isinstance(result, (OperationResult, v1.GodotAdapterResult)):
        return {"status": result.status, "artifact_path": result.artifact_path, "artifact_sha256": result.artifact_sha256}
    if isinstance(result, dict):
        return result
    raise TypeError(f"unsupported CLI result: {type(result).__name__}")


def _dispatch(args: argparse.Namespace) -> Any:
    if args.command == "doctor":
        return run_doctor(args.game_repo, operation_id=args.operation_id, project_dir_text=args.project_dir, godot_bin=args.godot_bin, profile_text=args.profile, required_evidence_paths=args.require_evidence, required_capabilities=args.require_capability)
    if args.command == "bridge":
        if args.bridge_command == "check":
            return bridge_check(args.game_repo, project_dir_text=args.project_dir)
        if args.bridge_command == "install":
            return bridge_install(args.game_repo, project_dir_text=args.project_dir, apply=args.apply, autoload=args.autoload, operation_id=args.operation_id)
        if args.bridge_command == "upgrade":
            return bridge_upgrade(args.game_repo, project_dir_text=args.project_dir, apply=args.apply, operation_id=args.operation_id)
        if args.bridge_command == "remove":
            return bridge_remove(args.game_repo, project_dir_text=args.project_dir, apply=args.apply, operation_id=args.operation_id)
        return profile_validate(args.profile)
    if args.command == "scenario":
        if args.scenario_command == "validate":
            return validate_scenario_file(args.scenario)
        kwargs: dict[str, Any] = {
            "operation_id": args.operation_id,
            "scenario_text": args.scenario,
            "project_dir_text": args.project_dir,
            "profile_text": args.profile,
            "godot_bin": args.godot_bin,
            "runtime_kind": args.runtime_kind,
            "build_text": args.build,
            "timeout_seconds": args.timeout_seconds,
            "windowed": args.windowed,
        }
        if args.scenario_command == "replay":
            kwargs["reference_trace_text"] = args.reference_trace
            return replay_scenario(args.game_repo, **kwargs)
        return run_scenario(args.game_repo, **kwargs)
    if args.command == "session":
        session = GodotSession(args.game_repo, operation_id=args.operation_id, project_dir=args.project_dir, profile=args.profile, godot_bin=args.godot_bin, runtime_kind=args.runtime_kind, build=args.build, windowed=args.windowed, fixed_fps=args.fixed_fps, seed=args.seed, initial_checkpoint=args.initial_checkpoint)
        return serve_jsonl(session)
    if args.command == "visual":
        game_repo = resolve_game_repo(args.game_repo)
        environment_path = resolve_in_repo(game_repo, args.actual_environment, must_exist=True, kind="file")
        environment = load_json(environment_path)
        return compare_visual(game_repo, operation_id=args.operation_id, baseline_text=args.baseline, actual_image_text=args.actual_image, actual_structure_text=args.actual_structure, actual_environment=environment, project_dir_text=args.project_dir, godot_bin=args.godot_bin, timeout_seconds=args.timeout_seconds)
    if args.command == "build":
        return run_build(args.game_repo, operation_id=args.operation_id, build_text=args.build, mode=args.mode, project_dir_text=args.project_dir, godot_bin=args.godot_bin, arguments=args.argument, timeout_seconds=args.timeout_seconds, expected_exit_code=args.expected_exit_code, expected_output=args.expect_output)
    if args.evidence_command == "verify":
        return verify_evidence(args.game_repo, args.evidence)
    return recover_evidence(args.game_repo, args.operation_id)


def main(argv: Sequence[str] | None = None) -> int:
    values = list(argv) if argv is not None else sys.argv[1:]
    if values and values[0] in LEGACY_COMMANDS:
        return v1.main(values)
    args = build_parser().parse_args(values)
    try:
        result = _dispatch(args)
    except (GodotAutomationError, v1.GodotAdapterError) as error:
        print(f"GODOT_ADAPTER_ERROR: {error}", file=sys.stderr)
        return 2
    public = _public_result(result)
    print(json.dumps(public, ensure_ascii=False, sort_keys=True))
    return 0 if public.get("status") in {"PASS", "READY"} else 2
