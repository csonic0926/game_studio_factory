# Player-text workflow validation — 2026-11-05

These results establish implementation behavior, not human comprehension,
literary quality, creative approval or game acceptance.

## Automated checks

| Command | Result |
| --- | --- |
| `python3 -m unittest player_text.tests.test_workflow -q` | 27 passed |
| `python3 -m unittest discover -s factory_core/tests -q` | 147 passed |
| `python3 -m unittest discover -s tests -q` | 83 passed |
| `python3 -m unittest discover -s ui/tests -q` | 30 passed |
| `python3 -m unittest discover -s product/tests -q` | 80 passed |

The new tests cover external non-Git invocation, JSON/CSV/text extraction,
multiline CSV and malformed rows, duplicate JSON keys, array-root/BOM catalogs,
mixed text kinds, blank/missing locale coverage, unchanged-item coverage,
source-discovery membership, protected forms/placeholders, source-key isolation,
author/reader/backchecker separation, failed or missing findings, exact runtime
and authority freshness, additional evidence freshness, path/symlink confinement,
write-once artifacts and the real v3 EVIDENCE_READY boundary. v2 requirements and
dependency membership remain distinct. Test reviews/rulings are explicitly
synthetic; no unit test claims another agent or USER actually approved a game.

The public skill passes the skill-creator validator using an isolated `uv`
environment with PyYAML. JSON Schema validation accepts a valid v3 declaration
and rejects missing applicability or NONE with a receipt path. `compileall` and
`git diff --check` pass. No runtime Python dependency was added.

## Independent external forward-test

An isolated evaluator used the published skill/contract in a temporary,
uninitialized, non-Git terminal-game project. It inventoried 30 strings across
English and Traditional Chinese (narration, dialogue, choices and functional
copy), repaired 13 and retained 17. A real fresh packet-only AI reader
(`/root/player_text_forward_test/reader_r1`) recorded all 30 interpretations.
A distinct informed reviewer checked coverage, original meaning and terminal
presentation. No synthetic unit-test verdict was used for this exercise.

The source-discovery hardening correctly invalidated the first receipt. The
updated run reused that actual first reading only after confirming identical
sanitized packet bytes/digest, and obtained a new isolated informed review
(`/root/player_text_forward_test/backcheck_r2`) without prior peer conclusions.
The new reviewer covered all 30 items and reproduced ten terminal transcripts.
All twenty final technical probes matched expectations, including sixteen
negative cases and the addition of a newly discovered source file. Restoring
the exact files restored validity. The primary agent independently reran verify.

Final receipt SHA-256:
`88a2bf25fb5f7340068150ff3386ace96b6d51c9652e193b3aef65e6b469b686`.
Its status is PLAYER_TEXT_EVIDENCE_VALID, ALL, en/zh-Hant, 30 texts, reader AI;
human_comprehension_proven and gameplay_accepted both remain false. Project
artifacts stay outside Factory in the temporary `player-text-forward-test.Y4rwAZ`
workspace, including `forward-test-report.json`,
`logs/final-technical-checks-r2.json` and `logs/harness-provenance-r2.json`.

No blocking defect was encountered. Field/selector-specific error messages and
a reader-packet persistence/digest helper remain minor usability follow-ups;
the documented manual procedure worked. The terminal exercise is not evidence
for graphical layout, audio, image text or arbitrary engines.

## Limits

JSON/CSV/text extraction is deterministic; other engines/media require audited
exports and actual-source bindings. Discovery globs detect changes within the
declared source universe, not an undeclared subsystem. Completeness of that
universe and correctness of meaning/presentation remain independent review
judgments. Context identifiers are provenance declarations, not authentication.
AI first readings must remain labelled AI; no readability score or automated
PASS substitutes for real player evidence.

No real game was migrated or edited, no global skill was installed/relinked,
and no main-branch consumer was changed.
