# Joint initialization validation and adoption

2026-10-09. Based on the exact source tree at local c889905 / published 058b7daa.
The complete design received two fresh independent PASS reviews after repairs;
[review receipt](PROJECT_INITIALIZATION_REVIEWS.md). This is engineering evidence,
not a commercial-value verdict, game commission or USER acceptance.

## Final author-run checks

- Entry/setup: 71 passed, including 46 focused initialization cases
- Product: 43 passed, including 8 additional intent contracts
- Shared core: 109 passed
- Idea: 29 passed
- Gameplay: 207 passed
- Targeted Studio: 99 passed (authority, alignment, baseline, cycle, contracts,
  player-facing evidence)
- Total: 558 passing tests, plus Python compilation and clean `git diff --check`

Focused coverage includes a fresh empty Git repository, exact-byte rerun with
authored intent, interrupted/resumed writes, existing open/commissioned/partial/
archived Idea preservation, actual exploration continuation after intent edits,
real-source invalidation, valid exact artifact refs, new-source reconciliation,
v2/v3 context and dependency binding, standalone unversioned work, source-scoped
scenario hypotheses and refusal to treat intent as current-build value evidence.

Failure-path checks preserve the complete game tree (including Git metadata):
malformed JSON/context, stale refs plus malformed later fields, symlinks/path
aliases, regular-file parent obstructions, non-UTF-8 managed text, migration
journals, wrong selected checkout, writer-lock contention and truly read-only
preview. Thesis REPO_COMMITMENT cannot cite intent through normalized path aliases.

## Independent implementation verification

A fresh non-author verifier independently reproduced and reported four issues:
context shape hidden behind stale provenance; parent-path obstructions detected
only after partial writes; a v2 selected pointer silently replaced by init; and
invalid UTF-8 ignore text decoded only after a pointer write. These were repaired
and covered by focused regressions. Normalized intent-path authority bypasses were
also tested and rejected. Raw reports and execution logs are local run artifacts;
this source receipt retains the findings and reproducible checks.

Final independent verdict: bounded PASS with no remaining material defect in
exercised initialization behavior. The final combined matrix ran 396 tests:
394 passed and the same 2 display-dependent cases were blocked; 6 supplemental
independent probes also passed. These counts overlap the author matrix above.

The verifier's full shared-core rerun passed 109 tests with writable HOME/XDG
paths. Full Studio ran 144: 142 passed, 2 windowed capture/movie cases were blocked
by absent DISPLAY/Xvfb, matching the previously documented environment limitation.
No Asset/provider validation, windowed-gameplay success or CI PASS is inferred.

## Reproduce

Use Python 3 and the repository's development test dependencies (jsonschema for
schema conformance). Runtime initialization remains dependency-free.

```sh
export XDG_DATA_HOME=<writable>/data XDG_CACHE_HOME=<writable>/cache XDG_CONFIG_HOME=<writable>/config
mkdir -p "$XDG_DATA_HOME" "$XDG_CACHE_HOME" "$XDG_CONFIG_HOME"
for suite in tests product/tests factory_core/tests idea/tests gameplay/tests; do
  python3 -m unittest discover -s "$suite" -q
done
python3 -m unittest studio.tests.test_product studio.tests.test_alignment studio.tests.test_baseline studio.tests.test_cycle studio.tests.test_contracts studio.tests.test_player_surface -q
python3 -m py_compile setup.py product/*.py idea/idea.py factory_core/catalog.py factory_core/context.py factory_core/migration.py factory_core/migration_gpt6.py
git diff --check
```

A synthetic scenario-priced learning case demonstrates that a provisional buyer,
buying reason, adequacy hypothesis and smallest experiment can remain DRAFTED and
continue authorized work with no actual-build assessment, price adoption or value
PASS. This checks truthful workflow operation, not the quality of an AI's taste,
market inference, experiment design or a real game's buying reason.

## Compatibility and adoption

`setup.py init` now establishes routing + Idea + nonbinding Product intent.
`setup.py link` remains routing-only. Existing Idea-only games may use
`product/product.py start` at their chosen safe boundary without relinking,
migration, recommission or changes to existing authority/history. Initialization
will not replace a selected checkout; a deliberate relink is a separate action.

Relevant Factory code/schema/workflow changes invalidate affected dependency
fingerprints as designed. Do not rehash old reviews into renewed approval. Bind
used intent as an explicit input, reconcile changed Idea sources, and preserve
UNKNOWN/scenario context until it is actually resolved. Existing unlinked Idea
probes may already be stale after routing changes; preserve them and use normal
Idea checks rather than silently refreshing them. Consumer owners coordinate any
adoption; this change did not mutate E&U, the user's Mac, stable skills or main.

Publication contains authored source, schemas/templates, guidance, tests and
compact design/validation receipts. No new ignore exceptions, game-owned output,
raw review conversations, screenshots or execution logs are included. Historical
experimental evidence remains unchanged; no six-call protocol is activated.
