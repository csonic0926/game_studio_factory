# AI caller landing — Asset Game AI Factory

This is the first stop for an AI agent working in another repo that wants to
use the Asset specialist under Game Studio Factory.

## Decide the path

| Caller need | Do this |
| --- | --- |
| Generate PNG deliverables with a spec-based factory workflow | Call the CLI from this repo with a spec file. |
| Clean AI-generated, pixel-looking PNGs into a real grid with a small palette | Use [pixel-snap cleanup](#pixel-snap-cleanup): a single PNG or directory; no spec or provider. |
| Make editable vector art/icons/type, or layer-compose/refine raster art (including generated images) | Use VectorCraft / PhotoCraft via `craft_asset_workflow_v1`; read [`CRAFT_ASSET_WORKFLOW.md`](CRAFT_ASSET_WORKFLOW.md). |
| Re-skin an existing geometrically-correct tile/autotile set | Use `tile_reskin_workflow_v1`. |
| Generate engineering-validated prop/object sprites | Use `prop_asset_workflow_v1`. |
| Generate/validate floor or wall reference-pair tiles | Use `reference_pair_workflow_v1` or the wall helper. |
| Need the factory to add a capability, schema field, validator, adapter, or example | File a request in `requirement_from_other_repo/` using `REQUEST_TEMPLATE.md`. |

Do not file a cross-repo request if the existing CLI/specs already satisfy the
job. File a request only when the factory itself must change.

## Basic calling contract

For player-visible words embedded in images/vector assets, use the shared
[player-text clarity workflow](../../player_text/WORKFLOW.md), with transcripts
bound to the exact rendered asset. Do not count an image pipeline PASS as text
comprehension. This is required by explicit v3 player-text applicability;
external/v1/v2 callers can invoke it independently without migration. Non-text
art can declare reviewed NONE rather than inventing text work.

Resolve `$STUDIO_ROOT` from the linked game repo's
`design/STUDIO_FACTORY.local.md` (legacy `design/AI_FACTORY.local.md` remains a
fallback), then run commands from the specialist folder:

```bash
cd "$STUDIO_ROOT/asset"
python3 -m pip install -r requirements.txt
python3 itf.py --help
```

Use absolute paths in specs when the source repo and factory repo differ. Keep
source-repo output expectations in the spec when supported, for example
`target_project_folder` in prop specs.

For a safe offline smoke test, prefer `provider.name = "mock"` or the workflow's
`--provider mock` override. For real GPT Image generation from a Codex-capable
agent, prefer `agent_handoff` / native `image_gen.imagegen`; use `cliproxyapi`
only as the non-agent/headless fallback.

## Common workflows

### Pixel-snap cleanup

Use `itf.py pixel-snap` when a generated scene, sprite or icon has uneven pixels,
soft edges or many near-duplicate colours. It is an **opt-in still-PNG tool**,
not a generation provider or an automatic prop/tile/wall/floor step.

From `$STUDIO_ROOT/asset`, use the normal Python/Pillow setup above. Only this
tool also needs **Node.js ≥20.3, npm and the pinned Sharp 0.34.5**:

```bash
npm ci --prefix pipeline/pixel_snap --include=optional

# Keep the logical canvas size; write one new PNG at the explicit destination.
python3 itf.py pixel-snap --input /game/raw/icon.png --out /game/export/icon.png

# Write native-grid textures. Redirect stdout if you want to keep the JSON receipt.
python3 itf.py pixel-snap --input /game/raw/customers --out /game/export/customer-grid \
  --profile chunky --scale 4 --true-grid
```

| Profile | Grid scale | Palette target | When to use it |
| --- | ---: | ---: | --- |
| `conservative` (default) | 2 | 24–42 | Small icons and sprites where thin details matter. |
| `balanced` | 3 | 20–36 | Mid-size illustrations; keep recognisable features with fewer cells. |
| `chunky` | 4 | 18–32 | Coarse scenes and large props with broad shapes. |
| `auto` | by size | selected preset | Mixed batches: conservative if short side ≤128 **or** long side ≤256; otherwise chunky if long side ≥768, balanced otherwise. |

- By default the optimized grid is enlarged with nearest-neighbour sampling to
  the original canvas. `--true-grid` writes the cells directly, **instead of**
  the enlargement. Each grid dimension is `max(1, round(source / scale))`
  (halves round up); `--scale N` overrides just the preset scale (`N ≥ 1`).
  For small textures keep the logical draw size and normalized pivot in the
  caller; no anchors, atlas rectangles or engine settings are edited.
- Alpha ≤24 is treated as transparent; the silhouette/fringe pass emits binary
  alpha. Fully opaque inputs stay opaque. Inspect fine outlines at game size;
  existing geometry/anchor checks still apply to the delivered art.
- A directory is processed in sorted filename order, **not recursively**, into
  a separate directory with the same basenames. Hidden files, names beginning
  with `_` and `*_snapped.png` are skipped. An explicit single PNG may use any
  basename. Output parents can be created, but existing files are never replaced.
- A successful JSON receipt lists one `files[]` record per PNG: input/output
  paths, source `width/height`, written `outputWidth/outputHeight`, resolved
  `profile`, `targetScale`, `gridW/gridH`, `finalColors` (palette slots, not a
  count of distinct output RGBs), and `sourceUniqueColors` (distinct input RGBA
  values above the alpha threshold). A failed batch exits nonzero; any records
  already completed remain listed. No metadata sidecar or caller-repo import is implicit.

Use `PIXEL_SNAP_NODE` to select a Node executable if it isn't on the caller's
PATH. To verify the installation, run `npm --prefix pipeline/pixel_snap test`;
the [regression fixtures](../pipeline/pixel_snap/test/README.md) need no game checkout.

### Editable vector/raster art

VectorCraft and PhotoCraft are production editors, not image-generation providers.
Use either a new document or declared existing inputs, including prior generated
PNGs. The Factory launches a private, file-scoped headless MCP session; it never
repoints another project's configured editor or touches its desktop document.

```bash
python3 itf.py craft-commands --editor vectorcraft --filter shape.rectangle
python3 itf.py craft-commands --editor photocraft --filter layer.newAdjustmentLayer
python3 itf.py run-craft-assets --spec /absolute/game/design/art/order.spec.json
```

Set `VECTORCRAFT_CLI` / `PHOTOCRAFT_CLI`, put the CLIs on PATH, or pass `--cli`.
Delivery keeps `.vectorcraft` / `.pcraft` source, PNG (optional SVG/JPG/WebP),
input hashes, command logs and engineering validation. Inspect `artifact_status.json`
first, then `source/`, previews, warnings and `deliverables/`. Edited assets still
need the original prop/tile/geometry validators and fresh visual acceptance.
Read the [calling contract and examples](CRAFT_ASSET_WORKFLOW.md).

### Prop/object assets

Use this when the target repo needs transparent game sprites with validated
canvas, anchor, alpha, manifest, and handoff metadata.

```bash
python3 itf.py generate-prop-assets \
  --spec examples/prop_asset_workflow/flame_relay_brazier_pair.spec.json

python3 itf.py validate-prop-assets \
  --run-root output/prop_asset_runs/imt_flame_relay_brazier_pair
```

Real provider examples:

```bash
python3 itf.py generate-prop-assets \
  --spec examples/prop_asset_workflow/flame_relay_brazier_pair.gpt_image.spec.json \
  --provider gpt_image

python3 itf.py generate-prop-assets \
  --spec examples/prop_asset_workflow/flame_relay_brazier_pair.gemini_pro.spec.json \
  --provider gemini_cli \
  --model nano-banana-pro
```

Inspect:

- `deliverables/*.png`
- `deliverables/prop_asset_manifest.json`
- `deliverables/validation_summary.json`
- `deliverables/preview_sheet.png`
- `deliverables/imt_prop_handoff.json` when present

Read more: [`docs/PROP_ASSET_WORKFLOW.md`](PROP_ASSET_WORKFLOW.md).

### Tile re-skin

Use this when the target repo already has geometrically-correct tiles/autotiles
and only needs a new material look while preserving connectivity.

```bash
python3 itf.py prepare-tile-reskin \
  --spec examples/tile_reskin_workflow/village_road.spec.json

python3 itf.py generate-tile-reskin \
  --spec examples/tile_reskin_workflow/village_road.spec.json

python3 itf.py generate-tile-reskin \
  --spec examples/tile_reskin_workflow/village_road.spec.json \
  --provider mock
```

Inspect the run's `deliverables/` folder and `artifact_status.json`.

Read more: [`docs/TILE_RESKIN_WORKFLOW.md`](TILE_RESKIN_WORKFLOW.md).

### Reference-pair floor/wall tiles

Use this when the target repo needs reference-guided floor or wall tile
generation and geometry validation.

```bash
python3 itf.py prepare-reference-pair \
  --spec examples/reference_pair_workflow/pixel_grass_demo.spec.json

python3 itf.py generate-reference-pair \
  --spec examples/reference_pair_workflow/pixel_grass_demo.spec.json

python3 itf.py validate-reference-pair \
  --run-root /absolute/path/to/run_root

python3 itf.py select-reference-pair-variant \
  --run-root /absolute/path/to/run_root \
  --variant full
```

Wall helper:

```bash
python3 itf.py generate-wall-reference-pair --height 2
python3 itf.py generate-wall-reference-pair --height 2 --variant left
python3 itf.py generate-wall-reference-pair --provider agent_handoff --model gpt-image-2
python3 itf.py generate-wall-reference-pair --provider gemini_cli --model nano-banana-pro
python3 itf.py generate-wall-reference-pair --provider cliproxyapi --model gpt-image-2
python3 itf.py generate-wall-reference-pair --provider cliproxyapi --model gpt-image-2 --ensure-proxy
```

Codex-agent GPT Image handoff:

1. Prepare a handoff run with `provider.name=agent_handoff` or
   `generate-wall-reference-pair --provider agent_handoff --model gpt-image-2`.
2. Open `<run_root>/request/imagegen_handoff.json`.
3. For each task, run the provided `codex_exec_shell_command` or manually call
   `image_gen.imagegen`; do not hand-draw with code.
4. Write the actual image bytes to
   `<run_root>/agent_handoff/step_1_raw/<variant>.png` and verify with `ls -la`.
5. Resume with `python3 itf.py generate-reference-pair --spec <same spec>`.

Use one Codex/imagegen session per variant. If you cannot use Codex handoff,
the fallback is local `cliproxyapi`: health check
`curl -s -m4 http://127.0.0.1:8317/v1/models`; if it is down, start
`/opt/homebrew/bin/cliproxyapi --config ~/.cli-proxy-api/config.yaml`.

Inspect:

- `artifact_status.json`
- `step_1_raw/`
- `step_3_cleanup_pool/`
- `step_4_gate/`
- `step_6_mapping/`
- `step_7_selection/`
- `deliverables/`

Read more:

- [`docs/REFERENCE_PAIR_WORKFLOW.md`](REFERENCE_PAIR_WORKFLOW.md)
- [`docs/FLOOR_REFERENCE_PAIR_WORKFLOW.md`](FLOOR_REFERENCE_PAIR_WORKFLOW.md)
- [`docs/WALL_REFERENCE_PAIR_WORKFLOW.md`](WALL_REFERENCE_PAIR_WORKFLOW.md)

## When the existing tools are not enough

Create one request file in:

```text
requirement_from_other_repo/
```

Use:

- [`requirement_from_other_repo/README.md`](../requirement_from_other_repo/README.md)
- [`requirement_from_other_repo/REQUEST_TEMPLATE.md`](../requirement_from_other_repo/REQUEST_TEMPLATE.md)

The request should include the source repo, target workflow, exact deliverables,
canvas/anchor/transparency rules, provider/model constraints, references, and
pass/fail criteria.

After the factory handles it, the factory-side agent appends status, changed
files, commands, outputs, and blockers to that same request file.

## Minimal source-repo agent checklist

1. Identify whether the job is pixel-snap cleanup, editable vector/raster art, prop, tile re-skin, reference-pair tile, or a new
   factory capability.
2. Call `python3 itf.py ...` from the factory repo. For pixel-snap pass explicit
   input/output paths; for spec-based orders create or reuse a spec.
3. For pixel-snap inspect the JSON receipt and named PNGs; for orders start from
   `artifact_status.json`, then inspect `deliverables/`.
4. Copy or import only validated deliverables into the source repo; for Craft
   orders retain the editable `source/` too. Technical validation is not creative acceptance.
5. If blocked by missing factory behavior, file a request under
   `requirement_from_other_repo/` instead of making ad hoc source-repo guesses.
