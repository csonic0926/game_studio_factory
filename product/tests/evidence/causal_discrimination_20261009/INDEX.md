# Causal-discrimination guidance: publication evidence, 2026-10-09

The nine-file guidance package is frozen by `FROZEN_MANIFEST.json`. Its historical
`independent_review: pending` and `publication: held` fields describe freeze time,
not this later review. The matching VALIDATION.md wording is also historical.
`INDEPENDENT_REVIEW.md` is a newly performed exact-byte publication examination;
it must not be described as approval that existed at the original freeze.
`PUBLICATION_REVIEW.md` independently reaches the same bounded publication result
and reruns the 169 affected tests; its post-verdict disclosure chronology is retained.

`AMBIGUOUS_FIRST_PASS.md` is the preserved original qualitative application to
three fictional observations. The new review finds no blocking guidance issue
and accepts the bounded arguments while retaining a nonblocking R2 precision
finding: the walking has movement inputs, despite the first pass's shorthand
“noninteractive.” The original output is intentionally not rewritten.

On 2026-10-09 the publishing operator reran Product 35, entry/setup 25 and shared
core 109 tests: all 169 passed with writable XDG data/cache/config directories.
An initial invocation without those directories hit the already documented two
Godot cache/data environment failures; the documented environment correction
resolved them without code changes. `git diff --check` passed. These are focused
contract/integration checks, not semantic accuracy or a new full-suite PASS.

Reproduce affected regression from the repository root:

```sh
export XDG_DATA_HOME="$(mktemp -d)" XDG_CACHE_HOME="$(mktemp -d)" XDG_CONFIG_HOME="$(mktemp -d)"
for suite in product/tests tests factory_core/tests; do
  python3 -m unittest discover -s "$suite" -q || exit
done
git diff --check
```

The receipt records exact source hashes and the original review scope. Historical
workspace/context identifiers are provenance, not portable paths or proof of
hard context isolation. No runtime, schema, ledger, game, consumer linkage or
production staged-call adoption is added by this node. Three fictional judgments
and reviewer agreement establish neither general semantic efficacy, correct
pricing, human taste, sales demand, nor USER acceptance.
