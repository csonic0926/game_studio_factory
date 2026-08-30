# Godot Engine Adapter

The Studio Godot adapter is an **evidence-only automation platform** for desktop
Godot 4 projects. It supports bounded legacy CLI operations, frame-bound
scenarios, authenticated live agent sessions, structural and pixel regression,
and debug/release build smoke verification.

It never decides whether gameplay is good, substitutes for an exact-build human
playtest, issues a gameplay verdict, or promotes an Accepted Playable Baseline.
Every v2 terminal record retains:

```json
{
  "acceptance_authority": "EVIDENCE_ONLY",
  "gameplay_verdict": "NOT_ISSUED"
}
```

## Architecture

```text
studio/godot_adapter.py             compatibility CLI and Python exports
studio/godot_engine/
  common.py                         safety, hashing, repo binding
  discovery.py                      Git/project/engine discovery interface
  process.py                        bounded sanitized process interface
  capability.py                     capability negotiation
  evidence.py                       atomic/recoverable immutable operations
  bridge.py                         vendor addon lifecycle and profile checks
  protocol.py                       loopback length-prefixed JSON protocol
  scenario.py                       frame-bound execution and replay
  api.py                            GodotSession and JSONL harness
  visual.py + image_metrics.gd      structural-first image comparison
  build.py                          debug/release build launcher
  doctor.py                         fail-closed capability diagnosis
  addon/                            versioned runtime bridge vendor source
```

The game repository owns installed instrumentation, profiles, scenarios,
baselines, and generated evidence. This Factory repository owns only reusable
code, schemas, templates, tests, and documentation.

## Compatibility

The v1 CLI and Python imports remain valid and continue writing the unchanged
v1 schemas and artifact layout:

```bash
python3 <STUDIO_ROOT>/studio/godot_adapter.py probe --game-repo <GAME_REPO>
python3 <STUDIO_ROOT>/studio/godot_adapter.py import-check \
  --game-repo <GAME_REPO> --operation-id import.before-unit
python3 <STUDIO_ROOT>/studio/godot_adapter.py run \
  --game-repo <GAME_REPO> --operation-id run.unit-smoke \
  --scene res://path/to/scene.tscn --fixed-fps 60 --quit-after 120 \
  --expect-output UNIT_SMOKE_READY
python3 <STUDIO_ROOT>/studio/godot_adapter.py export \
  --game-repo <GAME_REPO> --operation-id export.debug \
  --mode debug --preset macOS --output builds/game.zip
```

`probe_godot`, `import_check_godot`, `run_godot`, `export_godot`, constants,
and result types are re-exported from `studio.godot_adapter`.

## Doctor

Doctor binds the local Godot version, bridge/profile state, declared evidence
paths, project observability, required capabilities, and windowed/Xvfb support.
Missing game-specific observation is `BLOCKED`; Doctor never injects it.
Official CI support covers the latest patches in the two current minor lines,
Godot 4.6.x and 4.7.x. Other Godot 4 versions fail closed in Doctor while the
legacy capability probe remains available.

```bash
python3 <STUDIO_ROOT>/studio/godot_adapter.py doctor \
  --game-repo <GAME_REPO> --operation-id doctor.ci \
  --require-capability PROJECT_OBSERVATION \
  --require-evidence design/gameplay/expected-evidence.json
```

## Runtime bridge lifecycle

Installation is always a dry run unless `--apply` is present. `--apply`
requires a unique operation id and is the only adapter lifecycle allowed to
mutate project source.

```bash
python3 <STUDIO_ROOT>/studio/godot_adapter.py bridge install \
  --game-repo <GAME_REPO> --autoload

python3 <STUDIO_ROOT>/studio/godot_adapter.py bridge install \
  --game-repo <GAME_REPO> --autoload --apply \
  --operation-id bridge.install-1

python3 <STUDIO_ROOT>/studio/godot_adapter.py bridge check \
  --game-repo <GAME_REPO>
python3 <STUDIO_ROOT>/studio/godot_adapter.py bridge upgrade \
  --game-repo <GAME_REPO> --apply --operation-id bridge.upgrade-1
python3 <STUDIO_ROOT>/studio/godot_adapter.py bridge remove \
  --game-repo <GAME_REPO> --apply --operation-id bridge.remove-1
```

The installer copies versioned files to
`addons/game_studio_godot_bridge/`; it never uses a symlink. The optional
autoload is `GameStudioGodotBridge`. Upgrade/remove verify every vendor hash
and the complete vendor file set before changing anything. Manual vendor drift
is refused without making a backup branch or file. The project-owned profile
and provider are never created, overwritten, upgraded, or removed.

The bridge remains inert unless all gates hold:

1. explicit `--studio-adapter-enabled` user argument;
2. editor or debug build (`OS.is_debug_build()`); release builds are refused;
3. a 256-bit session token;
4. a `127.0.0.1` TCP port and successful protocol handshake.

Transport is one client, loopback only, little-endian 32-bit length-prefixed
UTF-8 JSON, maximum 1 MiB per strict message. The token is redacted from
commands, logs, traces, and manifests. There is no eval, shell command,
arbitrary method call, or arbitrary property mutation.

## Project profile and provider

Start from `studio/templates/GODOT_BRIDGE_PROFILE.json` and validate it:

```bash
python3 <STUDIO_ROOT>/studio/godot_adapter.py bridge profile-validate \
  --profile <GAME_REPO>/design/studio/engine/godot/GODOT_BRIDGE_PROFILE.json
```

The profile allowlists input actions, keycodes, mouse buttons, named project
commands, observations, checkpoints, and exact structural nodes/facts. Its
`provider_autoload` may implement only the fixed entry methods:

```gdscript
func studio_bridge_command(name: String, arguments: Dictionary):
func studio_bridge_observe(name: String):
func studio_bridge_checkpoint(name: String, arguments: Dictionary):
func studio_bridge_mechanical_snapshot():
```

A command or checkpoint handler reports a technical failure by returning
`{"ok": false, "error": "..."}`; any other JSON-compatible value is treated as
the successful result. Scenario/profile allowlist mismatches are blocked before
launch.

Project code may call
`GameStudioGodotBridge.record_project_resolved_action(name, payload)` to record
a **project-owned resolved action**. This is deliberately separate from the
bridge's `INJECTED_INPUT` record; the adapter never infers gameplay meaning from
its own key/action/mouse injection.

Generic observations are limited to `bridge.frame`, `bridge.scene`,
`bridge.viewport`, and `bridge.input_map`. Structural capture is limited to the
profile's allowlisted class, visibility, focus, position/bounds, Theme,
StyleBox, text, and disabled facts.

## Scenarios and replay

`godot_scenario.v1` is a strict tagged-step contract. It supports:

- `wait_frames` and deadline-bound `wait_until`;
- allowlisted action, key, mouse-button, and mouse-motion injection;
- named project commands and checkpoints;
- observable and project-owned mechanical snapshots;
- strict assertions;
- structural capture, PNG capture, and Movie Maker markers;
- a final `finish` and declared expected exit mode.

The Python adapter strictly validates the whole scenario before launch; the
autoload then preloads it before the main scene's `_ready` lifecycle and
advances it by engine process frame. Network latency therefore does not
schedule scripted steps.

```bash
python3 <STUDIO_ROOT>/studio/godot_adapter.py scenario validate \
  --scenario <GAME_REPO>/design/studio/engine/godot/scenarios/smoke.json

python3 <STUDIO_ROOT>/studio/godot_adapter.py scenario run \
  --game-repo <GAME_REPO> --operation-id scenario.smoke-1 \
  --scenario design/studio/engine/godot/scenarios/smoke.json

python3 <STUDIO_ROOT>/studio/godot_adapter.py scenario replay \
  --game-repo <GAME_REPO> --operation-id scenario.replay-1 \
  --scenario design/studio/engine/godot/scenarios/smoke.json \
  --reference-trace \
  design/studio/engine/godot/evidence_v2/scenario.smoke-1/session_trace.jsonl
```

Replay compares normalized frame/input/resolved-action/snapshot/assertion and
capture hashes. A different seed/checkpoint or missing reference metadata is
`INCONCLUSIVE`; a state/frame/response difference is `DIVERGED`; only an exact
normalized replay is `MATCH`.

Use `--runtime-kind debug_export --build <repo-relative-executable>` for an
exported debug build. `release_export` is always blocked for bridge operations.

## Live sessions

The JSONL harness reads one request per stdin line and writes one response per
stdout line:

```bash
python3 <STUDIO_ROOT>/studio/godot_adapter.py session serve \
  --game-repo <GAME_REPO> --operation-id session.agent-1 \
  --seed 42 --initial-checkpoint clean-room
```

Request fields are exactly `id` and `command`; the command uses the same
allowlisted command model as a scenario. Commands queue to the next safe engine
frame and return an ACK.

Python callers use the synchronous context manager:

```python
from studio.godot_adapter import GodotSession

with GodotSession(game_repo, operation_id="session.agent-1") as session:
    session.input_action("ui_accept", True)
    session.input_action("ui_accept", False)
    state = session.snapshot("menu", "menu.state")
```

Context shutdown is bounded and finalizes evidence for a clean exit, crash,
timeout, or exception.

Live traces retain full declared command payloads, safe-frame ACKs, and optional
seed/initial-checkpoint bindings. They can therefore serve as a reference for a
subsequent `scenario replay` once an equivalent strict scenario is supplied.
If the live run omitted the same seed/checkpoint, replay remains
`INCONCLUSIVE`; command, frame, response, or state differences are
`DIVERGED` rather than silently accepted.

## Visual and capture evidence

Visual regression is a two-layer gate:

1. compare allowlisted structural facts;
2. only after structure passes, compare PNG pixels through Godot
   `Image.compute_image_metrics()`.

The report contains max, mean, mean-squared, RMSE, PSNR, changed-pixel ratio,
changed bounding box, and a PNG diff. Missing tolerances mean exact comparison.
A baseline is hash-bound to Godot version, platform, renderer, viewport,
locale, scale, source revision, and an existing accepted/user-approved evidence
record. Environment mismatches are `BLOCKED`; baselines are never created,
approved, overwritten, or relaxed by the adapter.

```bash
python3 <STUDIO_ROOT>/studio/godot_adapter.py visual compare \
  --game-repo <GAME_REPO> --operation-id visual.hud-1 \
  --baseline design/studio/engine/godot/baselines/hud.json \
  --actual-image design/studio/engine/godot/captures/hud.png \
  --actual-structure design/studio/engine/godot/captures/hud.structure.json \
  --actual-environment design/studio/engine/godot/captures/environment.json
```

Scenario PNG and Movie Maker capture require a real windowed renderer. On
Linux the adapter uses an existing display or Xvfb. `--headless` uses Godot's
dummy display/audio path and is never represented as valid visual evidence.
Movie artifacts may contain Godot-recorded audio; markers remain separate trace
facts.

## Build verification

Debug builds may use scenario/session bridge control. Release builds only
receive bounded launch/crash/log smoke verification:

```bash
python3 <STUDIO_ROOT>/studio/godot_adapter.py build run \
  --game-repo <GAME_REPO> --operation-id build.release-smoke-1 \
  --build builds/game --mode release --expect-output GAME_READY
```

Release smoke rejects every bridge activation/token argument. A passing release
smoke does not prove visual correctness or gameplay acceptance.

## Evidence transactions

v2 operations write once under:

```text
design/studio/engine/godot/evidence_v2/<operation_id>/
  OPERATION_PENDING.json
  GODOT_AUTOMATION_EVIDENCE.json
  stdout.log
  stderr.log
  session_trace.jsonl
  snapshots / structures / captures / movie / benchmark / diff
```

The operation states are `PASS | FAIL | TIMEOUT | BLOCKED | ABORTED`;
assertions are `PASS | FAIL | INCONCLUSIVE`; replay is
`MATCH | DIVERGED | INCONCLUSIVE`. An operation id is never reused.
`GODOT_AUTOMATION_EVIDENCE.json` is written only at terminal finalization and
hashes every registered raw artifact, invocation, engine, Factory revision,
profile/scenario, project gameplay-evidence refs, and source binding before and
after. Unexpected source mutation converts a prospective pass into failure.

A hard interruption leaves `OPERATION_PENDING.json`. Only recovery may seal it:

```bash
python3 <STUDIO_ROOT>/studio/godot_adapter.py evidence recover \
  --game-repo <GAME_REPO> --operation-id scenario.crashed-1
```

Recovered evidence is always `ABORTED`. Offline verification supports v1 and
v2 without rewriting the original operation:

```bash
python3 <STUDIO_ROOT>/studio/godot_adapter.py evidence verify \
  --game-repo <GAME_REPO> \
  --evidence design/studio/engine/godot/evidence_v2/<id>/GODOT_AUTOMATION_EVIDENCE.json
```

## Factory acceptance placement

```text
candidate revision/build
  -> Adapter technical evidence hash
  -> Gameplay Observation Adapter semantic mapping and resolved actions
  -> fresh gameplay acceptance + exact-build human playtest
  -> predecessor regression
  -> Studio baseline admission
```

Studio/Gameplay artifacts reference the adapter evidence path and SHA-256. They
do not copy its process status into a gameplay verdict. Doctor reports missing
observability as `BLOCKED`; it does not add game-specific logging or handlers.

## Scope boundary

Supported: desktop editor runs, debug exports, and release smoke on macOS,
Linux/Xvfb, and Windows; deterministic scripted and live control; structured,
capture, performance, visual, and hashed evidence.

Excluded: scene/resource authoring, automated game-content mutation, automatic
visual-baseline approval, production telemetry or remote control, Mobile, Web,
console, and any claim that synthetic fixtures constitute a named game-repo
pilot.

Engine behavior follows the official Godot CLI, Movie Maker, Input, Image,
TCPServer, and StreamPeerTCP documentation:

- <https://docs.godotengine.org/en/stable/tutorials/editor/command_line_tutorial.html>
- <https://docs.godotengine.org/en/stable/tutorials/animation/creating_movies.html>
- <https://docs.godotengine.org/en/stable/classes/class_input.html>
- <https://docs.godotengine.org/en/stable/classes/class_image.html>
- <https://docs.godotengine.org/en/stable/classes/class_tcpserver.html>
- <https://docs.godotengine.org/en/stable/classes/class_streampeertcp.html>
