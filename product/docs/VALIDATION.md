# Product Factory engineering validation — 2026-10-09

Implementation verification in the isolated adaptation worktree, based on
b3eb3ae. This is engineering evidence, not proof of player value or USER acceptance.
The exact design received two fresh independent PASS reviews after repair;
see DESIGN_REVIEW_HISTORY.md. Original failed findings remain preserved.

## Executed checks

- Product contract/integration: 32 passed, including full v2 and v3 ledger paths,
  source/offer/build invalidation, actual prior evidence-ready output binding,
  authority lifecycle distinctions and negative assessment completion
- Entry/setup: 25 passed, including both new public skills and routing
- Factory core: 109 passed, including shared Story profile/acceptance, v2/v3
  compatibility, Sound/provider results and real headless Godot gameplay cases
- Studio: 142 passed; 2 windowed-Godot cases environment-blocked
- Gameplay: 207 passed
- Idea: 29 passed
- Asset unittest-compatible cases: 35 methods run, 32 passed; 2 floor-reference
  methods and 1 wall-reference method (4 subcases) blocked by missing pre-existing
  generated PNG reference assets
- Python compilation and git diff whitespace check passed

544 passing regular tests before the additional 32 passing Asset methods.
This is not a full-suite PASS. No existing expectation was loosened. The public
skill inventory expectation was updated for the deliberately added skills.

## Environment limits

The cloud shell has no DISPLAY or Xvfb. These same two Studio cases were blocked
on the unchanged base: test_live_jsonl_capture_disconnect_and_process_failure_are_bounded
and test_windowed_capture_and_movie_are_hashed_artifacts. Headless real-Godot
cases pass using isolated writable XDG data/cache/config directories. The initial
base invocation without those directories failed to create Godot's home cache;
that environment error was resolved without changing test code.

The base checkout lacks asset/output/png's generated 001/002 floor and 101/102
wall references. The read-only reference-root option was tried; no reference was
invented or substituted. The two pytest-style Asset cases could not run because
pytest is absent. The documented uv dependency-isolated route was attempted,
but PyPI requests timed out after three retries. The other 35 Asset methods were
run directly through unittest. No Asset/Sound implementation files changed.

## Reproduction

```sh
export XDG_DATA_HOME=<writable>/data XDG_CACHE_HOME=<writable>/cache XDG_CONFIG_HOME=<writable>/config
mkdir -p "$XDG_DATA_HOME" "$XDG_CACHE_HOME" "$XDG_CONFIG_HOME"
for suite in product/tests tests factory_core/tests studio/tests gameplay/tests idea/tests; do
  python3 -m unittest discover -s "$suite" -q
done
FACTORY_ASSET_REFERENCE_ROOT=<actual-generated-reference-directory> PYTHONPATH=asset:asset/tests \
  python3 -m unittest test_prop_asset_workflow test_reference_pair_workflow_provider \
  test_variant_selector_floor_mapping test_variant_selector_wall_validation -q
```

The Product schema conformance test additionally uses jsonschema in the development
interpreter; the production CLI has no third-party dependencies. Asset tests need
Pillow, and their pytest-only cases need pytest. Product/tests/SEMANTIC_SCENARIOS.md
is a separate qualitative operating exercise for a fresh reviewer; executable
fixtures deliberately label their judgments/reviews as synthetic contract data.

No real game was migrated/relinked or given new approval. The running E&U Factory
checkout remains clean at b3eb3ae. Publication, current real-product assessment,
and independent implementation/qualitative exercise results are separate checks.
