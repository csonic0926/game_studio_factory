"""Structural-first visual regression using Godot's Image metrics API."""

from __future__ import annotations

import copy
import platform
import re
from pathlib import Path
from typing import Any

from .common import (
    GodotAutomationError,
    OperationResult,
    load_json,
    probe_engine,
    repo_relative,
    resolve_game_repo,
    resolve_in_repo,
    resolve_project_dir,
    run_process,
    sanitize_command,
    sha256_file,
)
from .evidence import EvidenceTransaction
from .schema import exact_object, validate_evidence_ref


METRICS_SCRIPT = Path(__file__).resolve().parent / "image_metrics.gd"
EXACT_TOLERANCES = {
    "max": 0.0,
    "mean": 0.0,
    "rmse": 0.0,
    "min_psnr": 10_000_000_000.0,
    "changed_pixel_ratio": 0.0,
}


def _environment(value: Any, context: str) -> dict[str, Any]:
    item = exact_object(
        value,
        required={"godot_version", "platform", "renderer", "viewport", "locale", "scale"},
        context=context,
    )
    if not all(isinstance(item[field], str) and item[field] for field in ("godot_version", "platform", "renderer", "locale")):
        raise GodotAutomationError(f"{context} string fields must be non-empty")
    if not isinstance(item["viewport"], list) or len(item["viewport"]) != 2 or any(not isinstance(v, int) or v < 1 for v in item["viewport"]):
        raise GodotAutomationError(f"{context}.viewport must be [positive width, positive height]")
    if not isinstance(item["scale"], (int, float)) or isinstance(item["scale"], bool) or item["scale"] <= 0:
        raise GodotAutomationError(f"{context}.scale must be positive")
    return item


def validate_visual_baseline(payload: Any) -> dict[str, Any]:
    baseline = exact_object(
        payload,
        required={"schema_version", "baseline_id", "environment", "source_revision", "image", "structure", "approval_evidence"},
        optional={"tolerances"},
        context="visual baseline",
    )
    if baseline["schema_version"] != "godot_visual_baseline.v1":
        raise GodotAutomationError("visual baseline schema_version must be godot_visual_baseline.v1")
    if not isinstance(baseline["baseline_id"], str) or not baseline["baseline_id"]:
        raise GodotAutomationError("visual baseline_id must be non-empty")
    if not isinstance(baseline["source_revision"], str) or re.fullmatch(r"[0-9a-f]{7,64}", baseline["source_revision"]) is None:
        raise GodotAutomationError("visual baseline source_revision must be a Git revision")
    _environment(baseline["environment"], "visual baseline environment")
    for field in ("image", "structure", "approval_evidence"):
        validate_evidence_ref(baseline[field], context=f"visual baseline {field}")
    tolerances = baseline.get("tolerances", EXACT_TOLERANCES)
    exact_object(tolerances, required=set(EXACT_TOLERANCES), context="visual tolerances")
    for field in ("max", "mean", "rmse", "changed_pixel_ratio"):
        if not isinstance(tolerances[field], (int, float)) or tolerances[field] < 0:
            raise GodotAutomationError(f"visual tolerance {field} must be non-negative")
    if not isinstance(tolerances["min_psnr"], (int, float)):
        raise GodotAutomationError("visual tolerance min_psnr must be numeric")
    return baseline


def _verify_bound_file(game_repo: Path, reference: dict[str, str], context: str) -> Path:
    path = resolve_in_repo(game_repo, reference["path"], must_exist=True, kind="file")
    if sha256_file(path) != reference["sha256"]:
        raise GodotAutomationError(f"{context} hash does not match visual baseline binding")
    return path


def _approval_is_accepted(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    if payload.get("status") in {"ACCEPTED_PLAYABLE_BASELINE", "HUMAN_PLAYTEST_ACCEPTED", "USER_APPROVED"}:
        return True
    if payload.get("human_verdict", {}).get("status") == "HUMAN_PLAYTEST_ACCEPTED":
        return True
    if payload.get("state") == "USER_APPROVED" or payload.get("verdict") == "USER_APPROVED":
        return True
    return False


def _normalize_structure(payload: Any) -> Any:
    value = copy.deepcopy(payload)
    if isinstance(value, dict):
        value.pop("frame", None)
        return {key: _normalize_structure(item) for key, item in sorted(value.items())}
    if isinstance(value, list):
        return [_normalize_structure(item) for item in value]
    return value


def _threshold_assertions(metrics: dict[str, Any], tolerances: dict[str, float]) -> list[dict[str, Any]]:
    checks = [
        ("visual.max", metrics["max"] <= tolerances["max"], tolerances["max"], metrics["max"], "maximum channel delta"),
        ("visual.mean", metrics["mean"] <= tolerances["mean"], tolerances["mean"], metrics["mean"], "mean channel delta"),
        ("visual.rmse", metrics["rmse"] <= tolerances["rmse"], tolerances["rmse"], metrics["rmse"], "root mean squared error"),
        ("visual.psnr", metrics["psnr"] >= tolerances["min_psnr"], tolerances["min_psnr"], metrics["psnr"], "minimum peak signal-to-noise ratio"),
        ("visual.changed_pixel_ratio", metrics["changed_pixel_ratio"] <= tolerances["changed_pixel_ratio"], tolerances["changed_pixel_ratio"], metrics["changed_pixel_ratio"], "changed-pixel ratio"),
    ]
    return [
        {"assertion_id": name, "status": "PASS" if passed else "FAIL", "expected": expected, "actual": actual, "detail": detail}
        for name, passed, expected, actual, detail in checks
    ]


def compare_visual(
    game_repo_text: str | Path,
    *,
    operation_id: str,
    baseline_text: str | Path,
    actual_image_text: str | Path,
    actual_structure_text: str | Path,
    actual_environment: dict[str, Any],
    project_dir_text: str | Path = ".",
    godot_bin: str | None = None,
    timeout_seconds: float = 60.0,
) -> OperationResult:
    game_repo = resolve_game_repo(game_repo_text)
    project_dir = resolve_project_dir(game_repo, project_dir_text)
    engine = probe_engine(godot_bin)
    actual_environment = _environment(actual_environment, "actual visual environment")
    baseline_path = resolve_in_repo(game_repo, baseline_text)
    actual_image = resolve_in_repo(game_repo, actual_image_text)
    actual_structure = resolve_in_repo(game_repo, actual_structure_text)
    transaction = EvidenceTransaction(
        game_repo,
        operation_id=operation_id,
        operation_type="VISUAL_COMPARE",
        project_dir=project_dir,
        engine=engine,
        automation_manifest={
            "baseline": {"path": repo_relative(game_repo, baseline_path)},
            "actual_image": {"path": repo_relative(game_repo, actual_image)},
            "actual_structure": {"path": repo_relative(game_repo, actual_structure)},
            "actual_environment": actual_environment,
        },
    )
    missing = [repo_relative(game_repo, path) for path in (baseline_path, actual_image, actual_structure) if not path.is_file()]
    if missing:
        return transaction.finalize(
            status="BLOCKED",
            invocation={"pixel_comparison_executed": False},
            result={"blockers": ["missing visual input: " + value for value in missing]},
        )
    try:
        baseline = validate_visual_baseline(load_json(baseline_path))
        baseline_image = _verify_bound_file(game_repo, baseline["image"], "baseline image")
        baseline_structure = _verify_bound_file(game_repo, baseline["structure"], "baseline structure")
        approval = _verify_bound_file(game_repo, baseline["approval_evidence"], "baseline approval evidence")
    except GodotAutomationError as error:
        return transaction.finalize(
            status="BLOCKED",
            invocation={"pixel_comparison_executed": False},
            result={"blockers": [str(error)]},
        )
    transaction.automation_manifest["baseline"].update(
        {"sha256": sha256_file(baseline_path), "baseline_id": baseline["baseline_id"]}
    )
    transaction.automation_manifest["actual_image"]["sha256"] = sha256_file(actual_image)
    transaction.automation_manifest["actual_structure"]["sha256"] = sha256_file(actual_structure)
    comparison_path = transaction.path("visual_comparison.json")
    environment_compatible = baseline["environment"] == actual_environment
    approval_ok = _approval_is_accepted(load_json(approval))
    structural_equal = _normalize_structure(load_json(baseline_structure)) == _normalize_structure(load_json(actual_structure))
    structural_assertion = {
        "assertion_id": "visual.structure",
        "status": "PASS" if structural_equal else "FAIL",
        "expected": _normalize_structure(load_json(baseline_structure)),
        "actual": _normalize_structure(load_json(actual_structure)),
        "detail": "allowlisted structural facts are compared before pixels",
    }
    if not environment_compatible or not approval_ok or not structural_equal:
        status = "BLOCKED" if not environment_compatible or not approval_ok else "FAIL"
        report = {
            "schema_version": "godot_visual_comparison.v1",
            "status": status,
            "environment_compatible": environment_compatible,
            "structural_status": structural_assertion["status"],
            "image_status": "INCONCLUSIVE",
            "metrics": None,
            "changed_bbox": None,
            "diff_image": None,
            "acceptance_authority": "EVIDENCE_ONLY",
            "gameplay_verdict": "NOT_ISSUED",
        }
        transaction.write_json("visual_comparison.json", report, "VISUAL_COMPARISON")
        return transaction.finalize(
            status=status,
            invocation={"pixel_comparison_executed": False},
            result={"visual": report, "approval_evidence_accepted": approval_ok},
            assertions=[structural_assertion],
        )
    diff_path = transaction.path("visual_diff.png")
    metrics_path = transaction.path("image_metrics.json")
    stdout_path = transaction.path("stdout.log")
    stderr_path = transaction.path("stderr.log")
    godot_log_path = transaction.path("godot.log")
    command = [
        str(engine.executable), "--headless", "--log-file", str(godot_log_path),
        "--script", str(METRICS_SCRIPT), "--",
        str(baseline_image), str(actual_image), str(diff_path), str(metrics_path),
    ]
    capture = run_process(command, cwd=project_dir, timeout_seconds=timeout_seconds)
    stdout_path.write_text(transaction.scrub_text(capture.stdout), encoding="utf-8")
    stderr_path.write_text(transaction.scrub_text(capture.stderr), encoding="utf-8")
    transaction.register(stdout_path, "STDOUT_LOG")
    transaction.register(stderr_path, "STDERR_LOG")
    if godot_log_path.exists():
        transaction.scrub_text_file(godot_log_path)
        transaction.register(godot_log_path, "GODOT_LOG")
    if metrics_path.exists():
        transaction.register(metrics_path, "IMAGE_METRICS")
    if diff_path.exists():
        transaction.register(diff_path, "VISUAL_DIFF")
    metric_report = load_json(metrics_path) if metrics_path.exists() else {"status": "FAIL", "error": "metrics report missing"}
    if capture.timed_out:
        status = "TIMEOUT"
        image_status = "INCONCLUSIVE"
        assertions = [structural_assertion]
    elif capture.exit_code != 0 or metric_report.get("status") != "PASS":
        status = "FAIL"
        image_status = "FAIL"
        assertions = [structural_assertion]
    else:
        tolerances = baseline.get("tolerances", EXACT_TOLERANCES)
        metric_assertions = _threshold_assertions(metric_report["metrics"], tolerances)
        image_status = "PASS" if all(item["status"] == "PASS" for item in metric_assertions) else "FAIL"
        status = image_status
        assertions = [structural_assertion, *metric_assertions]
    report = {
        "schema_version": "godot_visual_comparison.v1",
        "status": status,
        "environment_compatible": True,
        "structural_status": "PASS",
        "image_status": image_status,
        "metrics": metric_report.get("metrics"),
        "changed_bbox": metric_report.get("changed_bbox"),
        "diff_image": {"path": repo_relative(game_repo, diff_path), "sha256": sha256_file(diff_path)} if diff_path.exists() else None,
        "acceptance_authority": "EVIDENCE_ONLY",
        "gameplay_verdict": "NOT_ISSUED",
    }
    transaction.write_json("visual_comparison.json", report, "VISUAL_COMPARISON")
    return transaction.finalize(
        status=status,
        invocation={
            "command": sanitize_command(command, game_repo=game_repo, binary=engine.executable, binary_name=engine.command_name),
            "working_directory": repo_relative(game_repo, project_dir),
            "timeout_seconds": timeout_seconds,
        },
        result={"visual": report, "engine_metrics_api": "Image.compute_image_metrics"},
        assertions=assertions,
    )


def default_environment(
    *, godot_version: str, renderer: str, viewport: tuple[int, int], locale: str, scale: float
) -> dict[str, Any]:
    return {
        "godot_version": godot_version,
        "platform": platform.system(),
        "renderer": renderer,
        "viewport": list(viewport),
        "locale": locale,
        "scale": scale,
    }
