# Godot Engine Adapter

The Studio Godot adapter is an evidence-only execution layer for Godot 4
projects. It discovers the local editor, binds the exact target project and Git
working tree, runs bounded engine operations, and writes hashed logs/evidence
into the target game repo.

It does **not** decide whether gameplay is good, satisfy a human playtest gate,
or promote an Accepted Playable Baseline.

## Supported v1 operations

```bash
python3 <STUDIO_ROOT>/studio/godot_adapter.py probe \
  --game-repo <GAME_REPO>

python3 <STUDIO_ROOT>/studio/godot_adapter.py import-check \
  --game-repo <GAME_REPO> \
  --operation-id import.before-unit

python3 <STUDIO_ROOT>/studio/godot_adapter.py run \
  --game-repo <GAME_REPO> \
  --operation-id run.unit-smoke \
  --scene res://path/to/scene.tscn \
  --fixed-fps 60 \
  --quit-after 120 \
  --expect-output UNIT_SMOKE_READY

python3 <STUDIO_ROOT>/studio/godot_adapter.py export \
  --game-repo <GAME_REPO> \
  --operation-id export.debug \
  --mode debug \
  --preset "macOS" \
  --output builds/game.zip
```

Use `--project-dir <repo-relative-path>` when `project.godot` is below the game
repo root. Binary discovery checks `GODOT_BIN`, `godot`, `godot4`,
`godot-mono`, and the standard macOS application path. `--godot-bin` is the
explicit override.

The command surface follows Godot's documented CLI contracts for `--path`,
`--headless`, `--import`, `--quit-after`, `--scene`, `--fixed-fps`,
`--export-debug`, and `--export-release`:

- <https://docs.godotengine.org/en/latest/tutorials/editor/command_line_tutorial.html>
- <https://docs.godotengine.org/en/stable/tutorials/export/exporting_projects.html>

## Game-owned outputs

```text
design/studio/engine/godot/
  GODOT_ENGINE_CAPABILITY_MANIFEST.json
  evidence/<operation_id>/
    GODOT_ENGINE_EVIDENCE.json
    stdout.log
    stderr.log
    godot.log
```

The manifest is a current machine/project capability observation. Operation
evidence is immutable by `operation_id`; rerunning the same id is rejected.
Each evidence record binds:

- Factory revision;
- project file hash;
- source Git revision, dirty paths, and dirty-byte hash before and after;
- Godot version and non-machine-specific binary locator;
- sanitized exact command, timeout, exit, and termination state;
- engine/script errors, expected-output assertions, and artifact hashes.

Adapter paths cannot escape the game repo. Absolute developer paths are not
persisted in manifests or evidence. Unexpected project-source mutation makes
an operation fail even when Godot exits zero. This matters because a first
Godot import may create script UID files or normalize source formatting; those
changes must be reviewed and committed before the validation run is treated as
stable evidence.

## Capability boundary

v1 implements:

- project and engine discovery;
- headless import validation;
- bounded project/scene runs;
- stdout/stderr/Godot-log capture;
- output-marker assertions;
- debug/release export evidence.

v1 does not implement:

- input injection or replay;
- structured live runtime state;
- validated screenshots or visual regression;
- deterministic condition-based stepping;
- editor scene mutation.

These gaps appear explicitly in the capability manifest. Do not replace them
with ad-hoc game scripts and do not translate a passing process run into a
gameplay-acceptance claim.

## Acceptance placement

The legal relationship is:

```text
candidate game revision
  -> Godot adapter technical/runtime evidence
  -> fresh gameplay acceptance + human playtest + predecessor regression
  -> baseline admission
```

The adapter can support the evidence inputs of acceptance and regression. It
never owns the later verdict or promotion.
