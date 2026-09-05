# Factory v2 validation record

Comparison baseline: `main` at
`9e35392b954d627a451e010e8b51d8b93f8ff32c`.

## Mechanisms and compatibility

Baseline verification found 25 entry/setup, 144 Studio, 207 Gameplay, 29 Idea,
and 37 Asset tests passing (442 tests; Asset also reports 11 subtests).
The v2 suite adds transition/restart, independent-review identity, exact USER
approval, authority/source closure, routing-only migration, concurrent-source
and destination conflicts, crash recovery, historical readability, visual
source references, Story locale/knowledge/clean-room applicability, provider
result/trim mocks, and complete benchmark accounting/rework/resume tests.

Reproduce from the Factory root:

```sh
python3 -m unittest discover -s tests
python3 -m unittest discover -s factory_core/tests
python3 -m unittest discover -s studio/tests
python3 -m unittest discover -s gameplay/tests
python3 -m unittest discover -s idea/tests
PYTHONPATH=asset python3 -m pytest asset/tests -q
```

Real Godot cases run when the installed engine is available. The v2 integration
case advances a synthetic reviewed/authorized design into actual scoped Godot
production, verifies UI/state observations and a repeated regression run, then
saves evidence without marking gameplay accepted. Existing Studio real-engine
scenario/replay/live-session and visual-comparison contracts remain exercised.
Fixture review/ruling records are synthetic test data, never new USER verdicts.
Image/audio generation providers are unchanged; provider mocks verify routing
and engineering-result consumption without spending generation calls.

## Independent refactor reviews

Separate intent/experience and completeness/project agents independently
reviewed the same refactor design, without reading peer conclusions. Their
counterexamples were converted into `test_regressions.py`,
`test_story_provider.py` and `test_benchmark.py`. Both final targeted rechecks
returned PASS for the previously blocking ownership, migration, review-version,
immutable-fixture and Story applicability defects. This does not substitute for
human creative-quality evaluation or the complete token experiment.

## Measurement boundary

The fixed suite uses Astra/high and the official Codex JSONL usage fields.
The first live trial encountered `usage_limit_exceeded` after measured author
and reviewer turns. The rejected request had no usage event. Its log is retained
as unmetered; a refill/resume cannot silently turn it into zero tokens.
The resumable harness retains completed work and all previous attempts, and
revalidates exact fixtures/sources before continuing. Output completion,
equal-quality human judgment, complete metering and lower totals in both rounds
are separate conditions. No savings percentage or complete-refactor acceptance
has been established by document length, unit tests or AI review alone.
