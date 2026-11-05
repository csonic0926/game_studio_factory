# Standalone calling contract

Run from any working directory. All input/output arguments are relative to the
explicit project root; absolute paths, traversal and symlinks are rejected.
No Git, Factory metadata, Story profile or network service is required.
The tool never edits game text. New evidence paths are write-once; use a new
revision path after repairs. An absent/incomplete review is not a PASS.

```sh
python3 /FACTORY/player_text/player_text.py prepare --project-root /GAME \
  --inventory design/player_text/inventory.json --out design/player_text/before-r1.json
# The caller treats every item and merges authorized text edits.
python3 /FACTORY/player_text/player_text.py seal --project-root /GAME \
  --packet design/player_text/before-r1.json --producer-context actual-author \
  --producer-context actual-language-editor --out design/player_text/candidate-r1.json
python3 /FACTORY/player_text/player_text.py reader-packet --project-root /GAME \
  --candidate design/player_text/candidate-r1.json
# Give ONLY that output to a fresh reader. Then a separate informed backcheck.
python3 /FACTORY/player_text/player_text.py check --project-root /GAME \
  --candidate design/player_text/candidate-r1.json \
  --reading design/player_text/reading-r1.json --backcheck design/player_text/backcheck-r1.json \
  --out design/player_text/receipt-r1.json
python3 /FACTORY/player_text/player_text.py verify --project-root /GAME \
  --receipt design/player_text/receipt-r1.json
```

The same functions are importable from `player_text.workflow`. The standalone
CLI validates the root; Python callers must call `project_root()` first.
`--game-repo` aliases `--project-root`. Exit 2 means invalid, stale or incomplete
evidence. Exit 0 means the requested technical operation succeeded, not that
the game or its language has been accepted. `check` without `--out` is read-only.

## Inventory: player_text_inventory.v1

`ref` below means exactly `{ "scope": "game", "path": "project-relative-path",
"sha256": "actual 64-character SHA-256" }`, never an unverified example hash.
Use `factory_core.refs.reference(root, path)` or hash the actual file bytes.

Required fields:

- `schema_version`: `player_text_inventory.v1`.
- `scope`: `ALL` or `CHANGED` (see WORKFLOW.md; empty work is not an inventory).
- `locales`: unique nonempty list of every shipped locale.
- `locale_authority`: ref to the project's actual locale declaration.
- `context_sources`: list of refs to applicable rules, canon, terminology,
  frozen meaning, authority and delivery requirements; never source-of-truth
  copies invented by the language editor.
- `coverage_notes`: nonempty list explaining discovery, scope, source loaders,
  exclusions and unsupported/dynamic surfaces. These claims need review.
- `runtime_paths`: unique list of current build/scene/media/render-case/evidence
  paths that affect comprehension. May be empty for an explicitly draft-only
  standalone task; the backcheck must not then claim runtime testing.
- `sources`: nonempty list of collections, with unique `id`.
- `discovery_globs`: required and nonempty for ALL; optional for CHANGED.
  Project-relative patterns such as `locales/**/*.json`, `scenes/**/*.tscn`,
  `scripts/*.py` and `assets/signs/*` bind the source-discovery universe. Each
  pattern must match files. Their membership and bytes are checked even when
  a matched file is not a text collection. Adding/removing a source requires
  a new inventory/packet; editing one after sealing stales the receipt. Use
  source-specific patterns that exclude evidence outputs, `.git` and caches.
  The coverage reviewer must independently check for undeclared source locations.

Each source requires `id`, `path`, `format`, `locale`, `kind`, `context`.
`kind` is dialogue/narration/description/lore/choice/functional. `context` is
plain, player-legitimate reading context and presentation order, not intended
answers or future reveals. Mixed files use per-key overrides.

Formats:

- `json`: recursively extracts every string leaf, addressed by RFC-6901-style
  pointers, e.g. `/menu/start`. Optional `options: {"pointer": "/menu"}` selects
  that subtree; coverage review must justify omitted subtrees.
- `csv`: requires `options: {"key_column": "key", "text_column": "en"}`.
  Declare one source per shipped language column. Reject duplicate keys/headers
  and malformed row widths. Selectors are exact row keys.
- `text`: the full UTF-8 file is one passage, with selector `""`.

Optional source fields:

- `exclude`: object mapping an exact extracted selector to a nonempty reason
  it is not player text; unknown selectors and exclusion/override overlaps fail.
- `protected_forms`: exact terms/tokens whose existing occurrence counts must
  survive. Applicable glossary forms must be extracted from the owning authority.
- `overrides`: selector -> object with optional `kind`, `context`,
  `protected_forms`. No fields for new canon or rules.
- `rendered_paths`: current engine/asset/audio/source files that this exported
  collection represents. Mandatory by workflow when the source is an export,
  not enforced by guessing file extensions.

Missing/blank active translations fail; explicitly non-player empty fields may
be excluded. Source identity, keys and locale membership cannot change between
prepare and seal: additions/deletions require a new inventory/before packet.
Simple `{name}`, `${name}` and printf placeholders are checked mechanically;
full template/markup structure and semantics remain backcheck obligations.

## Generated before/candidate/reading packet

`prepare` emits `player_text_packet.v1`: exact inventory ref, scope/locales,
workflow fingerprint, captured text and source-file digests. Old source digests
are historical capture metadata, not live references to files about to be edited.

`seal` emits `player_text_candidate.v1`: exact packet/inventory refs, current
output refs, all producer context ids and current items with opaque ids and
UNCHANGED/REWRITTEN dispositions. No quality verdict is generated.

`reader-packet` emits `player_text_reading_packet.v1`. Only id, locale, kind,
player context and current text survive. The packet digest is
`factory_core.refs.digest(packet)` (canonical sorted-key, indented UTF-8 JSON
plus newline), not a hash of arbitrarily formatted stdout. Source keys, paths,
originals, protected forms and intended meanings must not reach the reader.

## First reading: player_text_reading.v1

```text
schema_version: player_text_reading.v1
packet_sha256: digest of the sanitized reading packet
reader_context_id: actual independent execution identity
reader_kind: AI or HUMAN
fresh: true
sources_read: [the same packet digest]   # no other input
results: [
  {id: exact opaque id, understood: reader's own interpretation,
   status: PASS or REVISE, rationale: concrete language judgment}
]
```

Every item, including unchanged text and short labels, needs one result. Read
the surrounding group, not disconnected labels. Record language difficulty,
not inability to solve an intentionally unanswered story question. Never write
this record as if another reader ran when no isolated execution occurred.

## Informed backcheck: player_text_backcheck.v1

```text
schema_version: player_text_backcheck.v1
candidate: exact candidate ref
reading: exact immutable first-reading ref
reviewer_context_id: actual distinct non-author/non-reader execution
fresh: true
coverage:
  status: PASS or REVISE
  rationale: independent scope/locales/exclusions/export-fidelity judgment
  evidence: [inventory ref, locale authority ref, every context source ref,
             every candidate output ref, any additional exact review evidence]
results: [
  {id: exact opaque id, meaning: PASS or REVISE, language: PASS or REVISE,
   presentation: PASS or REVISE, rationale: concrete comparison and evidence}
]
```

`presentation` covers the declared actual form. Draft-only external work must
state that boundary in its rationale; it is not runtime proof. Runtime claims
need actual render/play/audio evidence in `coverage.evidence`. Preserve these
evidence references: `verify` rejects changed external evidence as well as text.
All results must pass for a receipt. Unknown, skipped or unresolved work remains
incomplete rather than being represented by invented text or blanket PASS.

## Receipt and Factory binding

`player_text_receipt.v1` is generated only after checking actual supplied
reading/backcheck records. Status `PLAYER_TEXT_EVIDENCE_VALID` certifies their
mechanical coverage and current bindings. It explicitly reports
`human_comprehension_proven: false` and `gameplay_accepted: false`, even when a
human supplied the reading. It does not generalize one reader to every player.

v3 player-content producers bind this object in their complete design:

```json
{"player_text": {
  "scope": "CHANGED",
  "scope_evidence": "REPLACE WITH AN EXACT REF IN design.artifacts",
  "receipt_path": "design/player_text/receipt-r1.json"
}}
```

`receipt_path` must be an authorized production path and an exact artifact of
EVIDENCE_READY/COMPLETE. Declare the actual text edits and evidence paths in the
normal production scope. `NONE` uses `receipt_path: null` and an exact reviewed
scope artifact explaining the absence of player-facing text/context changes.
`ALL` is needed for whole-game coverage; CHANGED cannot stand in for it.
