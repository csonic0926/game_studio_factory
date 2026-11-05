# Editable art — VectorCraft / PhotoCraft

`craft_asset_workflow_v1` adds **production editors**, not new image-generation
providers. It follows Sound Factory's SoundCraft pattern: a private headless MCP
session, explicit operations, an editable native project and exported assets.
Existing prop, reference-pair, tile re-skin and imagegen contracts are unchanged.

## Choose the tool

| Need | Tool |
| --- | --- |
| Precise icons, vector illustrations, paths, shapes, typography, scalable SVG | VectorCraft |
| Layer composition, masks, adjustments, raster cleanup, editing an existing generated image | PhotoCraft |
| New generated illustration/texture | Existing image-generation path, then optionally either editor |
| Tile geometry, anchor, connectivity, prop engineering acceptance | Existing owning workflow's validators, **after** editing |

Both editors can start from a new document or open an input file. Neither
automatically recovers original layers from a flattened generated image, and
placing a raster in VectorCraft does not by itself make it vector artwork.
Do not overwrite raw generation evidence or carry its approval to edited bytes.

## Environment and discovery

Install the appropriate upstream CLI separately, or use an existing installation:

```bash
export VECTORCRAFT_CLI=/absolute/path/to/vectorcraft-cli
export PHOTOCRAFT_CLI=/absolute/path/to/photocraft-cli
cd "$STUDIO_ROOT/asset"
python3 itf.py craft-commands --editor vectorcraft --filter file.new
python3 itf.py craft-commands --editor vectorcraft --filter shape.rectangle
python3 itf.py craft-commands --editor photocraft --filter layer.newAdjustmentLayer
```

Executable resolution: `--cli` → the editor's `*_CLI` variable → PATH →
`~/.local/bin`. An invalid explicit executable is an error, not permission to
silently select another one. No auto-download, paid generation, global MCP
registration or consumer relink. Python dependencies remain Pillow + stdlib.

Discovery queries the **installed** engine's command catalogue; parameters are
editor-native, not guessed or maintained as a second catalogue in this repo.
PhotoCraft commands may report `needsDocument` during discovery: this is normal
because discovery opens no document. Narrow `--filter` to avoid huge catalogues.

Verified with VectorCraft **0.18.0** and PhotoCraft **0.17.0**, 2026-11-05. Other
versions require discovery and a smoke run; they are not automatically certified.
Primary references: [VectorCraft MCP](https://github.com/storytold/vectorcraft/blob/main/docs/mcp.md),
[PhotoCraft MCP](https://github.com/storytold/photocraft/blob/main/docs/mcp.md).

### Native agent MCP versus the recipe runner

An agent may use an already-connected, correctly scoped editor MCP to inspect or
explore: `command_list` → edits → `doc_inspect` / `render_preview`. VectorCraft
also offers `draw_shape`, `draw_path`, `add_text`; PhotoCraft offers `doc_place`,
layer tools and adjustments through commands. Inspect the tool schemas first.

For a recorded Factory delivery, express the chosen operations as a recipe and
run the CLI below. A native MCP session alone does **not** produce a Factory
validation result. Never repoint another project's MCP or use its output folder
as a workaround. The runner launches its own session and does not attach to the
desktop app, even when a bridge is configured in the environment.

## Run an order

```bash
python3 itf.py run-craft-assets --spec /absolute/game/design/art/badge.spec.json
# Optional: a different fresh complete run directory; per-request deadline:
python3 itf.py run-craft-assets --spec /absolute/game/design/art/badge.spec.json \
  --out /absolute/game/design/art_runs/badge_v2 --timeout 180
```

Small smoke recipes (scratch only, no model/API calls):

```bash
python3 itf.py run-craft-assets --spec examples/craft_asset_workflow/vector_badge.spec.json
python3 itf.py run-craft-assets --spec examples/craft_asset_workflow/photo_panel.spec.json
# Reads the vector_badge PNG from the first run; preserves its alpha:
python3 itf.py run-craft-assets --spec examples/craft_asset_workflow/photo_refine.spec.json
```

These examples write to `/tmp/asset_factory_craft_runs`. Real orders belong in
the **target game repo**, never this checkout. Existing run directories are
refused, including failed runs; use a new `run_id` or `--out`, not an overwrite.
Relative spec paths resolve from the spec's directory; `--out` resolves from the
calling shell's working directory. Use absolute paths across repos.

### Spec contract

```json
{
  "schema_version": "craft_asset_workflow_v1",
  "run_id": "sprite_refined_v1",
  "output_root": "/absolute/game/design/art_runs",
  "editor": "photocraft",
  "inputs": {"base": "/absolute/game/design/generation/step_1_raw/sprite.png"},
  "document": {"input": "base"},
  "steps": [
    {"command": "layer.newAdjustmentLayer.brightnessContrast",
     "params": {"brightness": 15, "contrast": 8}}
  ],
  "exports": [
    {"name": "sprite.png", "width": 128, "height": 256, "alpha": "transparent"}
  ]
}
```

- `editor`: `vectorcraft` or `photocraft`. No `provider` field or mock production mode.
- `document`: exactly one of `input` (a key in `inputs`) or `new` (editor-native
  new-document params with integer `width` / `height`). VectorCraft uses
  `file.new` (`backgroundContents`, `units`); PhotoCraft uses `doc_new`
  (`background`, `mode`, `depth`). Their parameter names are **not interchangeable**.
- `inputs`: optional named files (IDs must also be unique ignoring case). The runner snapshots and hashes each file into
  `inputs/`; the originals are never writable by the editor. Commands can use the
  exact string `"$input.base"` for its staged absolute path. Declare every external
  input: no automatic grant of the source's parent directory. Linked assets must
  be embedded or explicitly staged/placed; a copied native document with missing
  external links is not a complete portable delivery.
- `steps`: ordered `{"command": "engine.id", "params": {...}}`. Empty permits
  conversion. Every edit runs synchronously and failure stops the order. Use an
  exact string `"$step.0.id"` to address a previous result (zero-based steps; dot
  traversal supports object keys and array indices). This preserves numeric IDs.
  Unknown/forward references fail; no shell or string interpolation.
- `exports`: PNG/JPG/WebP for either editor; SVG additionally for VectorCraft.
  Names are unique filenames, not paths. **At least one PNG** is mandatory for
  review. Every raster declares expected `width`, `height` (1–16384), and optional
  `alpha`: `any` (default), `transparent` (some fully transparent pixels plus
  visible content), or `opaque` (all alpha 255). Size assertions do not resize
  images; set the document or export scale correctly. PNG is the preferred game
  handoff; JPG cannot have transparency.
- Export `params` pass through to the native export tool, e.g. VectorCraft
  `{"scale": 2, "artboard": 0}` or `{"outlineText": true}` for SVG; PhotoCraft
  `{"quality": 85}` for JPEG/WebP. They cannot override output path, format,
  document index or request multi-file ranges. SVG assertions use its companion
  PNG, not width/height/alpha fields on the SVG entry.
- The runner owns document save and export: do not write the reserved native or
  export filenames in `steps`. Extra files an operation writes remain work files,
  not automatically validated deliverables. One final native document per run;
  multiple exports/artboards may be declared individually.

Engine APIs use different opacity scales and coordinate units. Read discovery
output. Prefer an adjustable layer/mask over destructive edits when feasible;
retain native vectors and live text even when an outlined/flattened export is
needed by the game. Inspect typography, colour, alpha edges and actual game scale.

## Isolation and artifacts

Each run grants the editor **one read root: the run directory**, and **one write
root: `work/`**. PhotoCraft does not accept repeated read-root flags. Staging avoids
widening access to a common ancestor of unrelated inputs. Preferences get a
private home; inherited Craft bridge/root variables are removed. These file
capabilities supplement, not replace, host sandbox/permission rules. Never widen
them to bypass denied access; obtain the required approval instead.

```text
artifact_status.json                 # read first; false on any failure
request/spec.json, inputs.json       # normalized recipe, input paths and hashes
request/editor.json                  # actual executable + MCP server version
inputs/                              # input snapshots (not generated evidence)
work/                                # editor-only writes, partial/debug outputs
logs/calls.jsonl, editor.stderr.log   # actual requests, responses, warnings/errors
logs/document.before_save.json       # editable state before native save
logs/document.reopened.json          # state after native reopen
logs/validation_summary.json         # validation result, including failure
source/<run_id>.vectorcraft|.pcraft   # retained editable source, on success
deliverables/<declared files>
deliverables/craft_asset_manifest.json
deliverables/validation_summary.json
```

The runner saves native, reopens it, then exports from that reopened document.
It checks nonempty regular files, decodable format, exact raster dimensions,
alpha policy and SVG XML structure. It rejects fully transparent rasters,
escaping artifacts, engine errors, unfinished jobs, EOF and request timeouts.
Partial output is not a successful handoff. Logs retain import/export warnings;
flattening a PNG does not mean the native source lost its layers.

**This is engineering validation, not an art-direction or gameplay verdict.**
`creative_acceptance` stays `not_assessed`; review is always required. Native
reopen is not a proof of full layer/font/colour fidelity: compare the saved
inspection and preview, and investigate warnings. SVG XML validation is not a
sanitizer or a vector-purity check. Use the target engine's safe asset-import path.
Keep both `source/` and `deliverables/` in the game project, not only the PNG.

## Continue an existing generation run

1. Choose an input from the existing run without modifying its raw evidence.
2. Create a **new** Craft spec/run with that file in `inputs` and a `document.input`,
   or place it into a new document using a discovered engine command and `$input`.
3. Inspect `artifact_status.json`, warnings, the native layer/object tree and PNG.
4. Route the exported bytes back through the owning workflow's validation. For
   example, prop/ref-pair CLIs accept `--image asset_id=/absolute/refined.png` or
   `--image variant=/absolute/refined.png` respectively; use the original exact
   canvas/anchor requirements. Do not replace reference geometry/alpha merely to
   make a picture attractive. Tile connectivity/geometry rules still apply.
5. Treat downstream validation and visual/USER acceptance as fresh decisions for
   these exact bytes. Craft does not alter old approvals, baselines or v2/v3 state.

VectorCraft PNG/SVG can also be an input to a later PhotoCraft run (as the smoke
examples demonstrate). A PhotoCraft PNG can be placed in VectorCraft for vector
overlays/typography. Pass file paths through declared inputs, not global sessions.

## Regression checks

From `$STUDIO_ROOT/asset`, with a Python environment containing Pillow and pytest:

```bash
PYTHONPATH=. python3 -m pytest tests/test_craft_asset_workflow.py
# Explicit opt-in; both *_CLI executables must be available. Temporary runs only.
FACTORY_CRAFT_LIVE_TESTS=1 PYTHONPATH=. python3 -m pytest tests/test_craft_editors_integration.py
```

The live tests exercise both new-document routes, VectorCraft → PNG → PhotoCraft,
native-layer reopen, alpha preservation, and rejected out-of-scope reads/writes.
Without explicit opt-in they are skipped, not replaced by a mock provider.
The complete existing asset suite also requires its Blender reference fixtures;
see `FACTORY_ASSET_REFERENCE_ROOT` in [`REPO_MEMORY.md`](REPO_MEMORY.md).
