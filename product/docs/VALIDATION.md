# Product Factory engineering validation — 2026-10-09

Implementation verification in the isolated adaptation worktree, based on
b3eb3ae. This is engineering evidence, not proof of player value or USER acceptance.
The exact design received two fresh independent PASS reviews after repair;
see DESIGN_REVIEW_HISTORY.md. Original failed findings remain preserved.

## Executed checks

- Product contract/integration: 35 passed, including full v2 and v3 ledger paths,
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

547 passing regular tests before the additional 32 passing Asset methods.
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

## Repair after the first implementation audit

The independent audit of 9ba6009 reproduced a legacy-authority closure hole:
canonical PRODUCT_THESIS_INPUT.json and IDEA_FACTORY_RESULT.json were omitted
without an active register. The full REVISE report is retained in
IMPLEMENTATION_REVIEW_9ba6009.md. Product now directly binds all existing canonical
commission artifacts, including partial states, without migration. Added mutation,
removal/new-presence and symlink regressions for both omitted artifacts pass.

The independent qualitative exercise found sensible judgments for all eight
stipulated scenarios but caught a caller trigger gap. Studio's current skill and
v2/v3 workflows now invoke Product at whole-product done/polished/final-handoff
stopping claims, while exempting bounded prototype/slice/checkpoint claims and
avoiding per-edit reviews. This is faithful to the reviewed design, not a new
release checklist. All six unittest suites above were rerun after these repairs;
the same two windowed Studio environment cases remain blocked. Asset code and
its prior stated limitations are unchanged.

## Final independent verification and real protocol exercise

A fresh verifier gave a bounded PASS for 1eefd615. It independently ran 297 tests
(Product35, entry25, core109, targeted Studio99, Idea29) and 26 additional
mutation/substitution probes, all passing/rejecting as intended. Its complete
scope and judgment limits are retained in IMPLEMENTATION_VERIFICATION_1eefd615.md.
The separate eight-scenario qualitative exercise and its original trigger finding
are retained in SEMANTIC_EXERCISE_9ba6009.md; the trigger was repaired afterward.

The real SAB candidate exercise then used the repaired tool, two fresh actual
independent informed reviews, source-bound candidate evidence and refreshed public
price context. Both reviewers agreed with the qualified EVIDENCE_INSUFFICIENT
assessment. Record/check succeeded; the exact-build current-offer gate correctly
blocked the conditional scenario with exit2 and retained false USER-acceptance
and delivery flags. This demonstrates truthful negative/conditional operation,
not that SAB is good/bad value or that the framework computes value. Filled
reports, reviews and receipts remain in the target game, outside Factory source.
No real game was migrated, relinked, changed or adopted by this exercise.
