# Godot Engine Adapter changelog

## godot_automation.v1 / game_studio_godot_bridge.v1

- Preserves `godot_cli_adapter.v1` compatibility.
- Adds crash-recoverable immutable v2 evidence operations.
- Adds dry-run/apply bridge install, upgrade, remove, profile validation, hash
  drift refusal, opt-in autoload, debug-only activation, and strict loopback
  token protocol.
- Adds `godot_scenario.v1`, deterministic replay, and `GodotSession`/JSONL live
  control using one allowlisted command model.
- Separates injected input from project-owned resolved actions.
- Adds observation/checkpoint/snapshot/assertion/structure/PNG/Movie Maker and
  benchmark evidence.
- Adds structural-first `Image.compute_image_metrics()` regression with exact
  defaults, environment-bound approved baselines, diff/bbox, and no automatic
  approval.
- Adds debug/release build smoke, with release bridge activation forbidden.
- Adds Doctor, offline v1/v2 verification, ABORTED recovery, strict schemas,
  synthetic Godot fixtures, and a macOS/Linux/Windows CI matrix configuration.
