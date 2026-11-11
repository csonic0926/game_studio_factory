"""Tiny synthetic protocol fixtures. No real USER, game or comprehension proof."""
import copy
import struct
import subprocess
import zlib

from factory_core.refs import encoded, reference
from ui.experience import KINDS


def png(width=100, height=100, color=(80, 90, 100)):
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    pixels = b"".join(b"\x00" + bytes(color) * width for _ in range(height))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(pixels)) + chunk(b"IEND", b"")


def write_bytes(test, path, data):
    target = test.game / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return reference(test.game, path)


def element(identity, bounds=None, **kwargs):
    return dict(element_id=identity, bounds=bounds or [40, 40, 20, 20], visible=True,
                enabled=True, fact_ids=[], color=None, points=[], overlay_group=None, **kwargs)


def bundle(test, *, origin="RUNTIME", name="capture", elements=None):
    image = write_bytes(test, f"evidence/{name}.png", png())
    exporter = reference(test.roots["factory"], "ui/godot_engine/capture.gd", "factory")
    runner = test.game / "tests/synthetic_ui_runner.gd"
    if not runner.exists():
        runner.parent.mkdir(parents=True, exist_ok=True)
        runner.write_text("extends SceneTree\n# Synthetic protocol fixture, not real runtime evidence.\n")
        project = test.game / "project.godot"
        if not project.exists(): project.write_text("config_version=5\n")
        subprocess.run(["git", "-C", str(test.game), "add", "project.godot", "tests/synthetic_ui_runner.gd"], check=True)
        subprocess.run(["git", "-C", str(test.game), "-c", "user.name=Synthetic", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "Synthetic capture sources"], check=True)
    from ui.visual import build_manifest
    manifest = build_manifest(test.roots, ["project.godot", "tests/synthetic_ui_runner.gd"], "tests/synthetic_ui_runner.gd")
    build = test.write("evidence/build.json", manifest)
    return dict(schema_version="ui_runtime_capture.v1", origin=origin, game_revision=manifest["game_revision"],
                build_id=build["sha256"], build_artifact=build, exporter=exporter,
                scenario_id="decision", state_id="ready", surface_id="board", locale="en", viewport=[100, 100],
                frames=[dict(frame_id=0, time_ms=0, image=image, elements=elements if elements is not None else [element("advance")], overlays_complete=True)])


def experience(test, design, preview):
    return dict(schema_version="ui_experience_contract.v1",
        scenarios=[dict(scenario_id="decision", surface_id="board", state_id="ready", viewport=[100, 100], locale="en", step_ids=sorted(test.steps))],
        checks=[dict(check_id="primary", kind="PRIMARY", scenario_ids=["decision"], parameters=dict(element_id="advance", flow_id="next", anchor=[0.5, 0.5], tolerance=0.05))],
        not_applicable={kind: "Synthetic fixture has no such presentation; semantic review remains required." for kind in KINDS if kind != "PRIMARY"},
        probes=[dict(probe_id="understand", scenario_ids=["decision"], chain_id="chain.a", fact_ids=["fact.first-target", "fact.guard-hit"],
                     criterion="Observer uses the shown target and identifies the guarded response without prompts.", falsifier="Observer cannot attribute the guarded hit or determine the shown target.")],
        genre=dict(profile="NONE", reason="Synthetic interaction protocol fixture, not an auto-battler.", items=[]),
        design_captures=[preview], feedback_inputs=[],
        visual_decisions=[dict(decision_id=item["id"], excerpt=item["excerpt"], consequence=item["consequence"], before=None, after=preview, risk="Synthetic protocol example; human experience is unproven.") for item in design["decisions"]],
        receipt_path="design/ui/unit-one/READINESS.json")


def attach(test, design, design_ref):
    preview = test.write("design/ui/unit-one/PREVIEW.json", bundle(test, origin="DESIGN_PREVIEW", name="preview"))
    value = experience(test, design, preview)
    contract_ref = test.write("design/ui/unit-one/EXPERIENCE.json", value)
    design["ui"]["experience"] = contract_ref
    design["artifacts"].append(contract_ref)
    design["inputs"].append(preview)
    design["production_scope"].extend([value["receipt_path"], "design/ui/unit-one/ACCEPTANCE.json", "design/ui/unit-one/feedback/current.json"])
    fresh = test.write(design_ref["path"], design)
    design_ref.clear()
    design_ref.update(fresh)
    return value


def rehash_tree(test, value):
    """Refresh synthetic nested file refs after deliberately editing test pixels."""
    if isinstance(value, dict):
        if "path" in value and "sha256" in value:
            return {**value, "sha256": reference(test.game, value["path"])["sha256"]}
        return {key: rehash_tree(test, item) for key, item in value.items()}
    if isinstance(value, list):
        return [rehash_tree(test, item) for item in value]
    return value
