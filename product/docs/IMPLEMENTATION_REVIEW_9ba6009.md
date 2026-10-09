# Independent implementation audit: Product Factory

Target: frozen commit `9ba6009bd09bfd97af36bc4024e048d3112d28cf` in the isolated Product Factory worktree.

## Verdict: REVISE — one reproduced blocking authority-closure defect

### P1: Legacy canonical commission sources can change without invalidating the value claim

`product/value.py:103–111` collects mandatory authority through `factory_core/catalog.py:107–111`. Without an active lifecycle register, that catalog binds `PRODUCT_THESIS.md` and `FACTORY_CONSTRAINTS.json`, but omits the existing canonical `design/product/idea/PRODUCT_THESIS_INPUT.json` and `IDEA_FACTORY_RESULT.json`.

`studio/product.py:279–284` still recognizes all four files as `LEGACY_ACTIVE_PRODUCT_AUTHORITY`. Consequently, changing either omitted file leaves both the authority status and the reviewed fingerprint unchanged. The old result continues passing `gate` as `PRODUCT_VALUE_CLAIM_SUPPORTED`.

The real Idea constraints renderer uses `source_input_path` / `source_input_sha256` (`idea/idea.py:1493–1498`), while `expand_references` recognizes objects with `path` / `sha256`. It therefore does not indirectly close this gap. The reproduction uses those real legacy field names; it is not relying only on the original test fixture's abbreviated constraints shape.

Observed reproduction:

- Record a reviewed SUPPORTED assessment with complete canonical authority but no lifecycle register
- Both input and Idea result are absent from the sealed dependency set
- Change the canonical thesis input after review: gate still SUPPORTED
- Change the canonical Idea result after review: gate still SUPPORTED

This defeats the promised stale-authority boundary and lets an assessment continue asserting current paid value without re-reviewing changed commission evidence. It also means mandatory source coverage never required reviewers to encounter those omitted sources. Existing complete-file presence is not a substitute for exact content closure.

Suggested repair: include every existing canonical Product authority artifact needed for current legacy commission, with confined exact references, without introducing a forced migration or rewriting authority. Regression tests should cover modifications, removal, new presence, and unsafe paths for each canonical input/result under the no-register legacy case. Ensure the selected normal register/archive behavior remains intact.

Runnable reproduction and captured output are in sibling files `reproduce_legacy_authority_gap.py` and `reproduction.txt`. They modify only a disposable synthetic Git game.

## What the implementation does establish

- CURRENT_OFFER / ADOPTED_OFFER versus proposal/scenario distinctions are represented in the claim and enforced at the gate
- Adopted offers require a raw USER-source quote; adoption meaning remains explicitly entrusted to independent judgment, not authenticated by Python
- SUPPORTED requires build-bound EXPERIENCE rather than technical tests alone, and refuses declared material unknowns
- Gate retains exact offer/audience/build context; neither a result nor COMPLETE grants USER acceptance or delivery
- Author/self-review, duplicate reviewer contexts, declared peer contamination, stale fingerprints, incomplete source coverage and REVISE verdicts are blocked
- Ordinary input/evidence/report/build changes invalidate existing reviewed results; active-register archive invalidates old current results and blocks new active claims
- Result publication uses the shared advisory lock, exclusive immutable publication, and a second package read; ordinary unsafe/symlink paths are rejected. This is not filesystem-wide adversarial isolation and the implementation explicitly does not claim that
- Shared Product completion checks the actual preceding EVIDENCE_READY ledger entry, its exact design and prior digest; required current outputs must exist in both EVIDENCE_READY and COMPLETE
- Result identity, subject, offer/audience and required output scope are bound to the sealed design. Valid unrelated results cannot substitute, and late COMPLETE-only outputs cannot close the task
- Additive v2/v3 integration preserves the real USER ruling boundary; standalone legacy assessment does not migrate/relink a project

## Product-purpose judgment

The operating workflow is genuinely whole-product/value oriented. It follows the purchase promise, coherent contribution of art/audio/interaction/comfort, decisive contrary experience, meaningful sacrifices and smallest valuable next move. It does not turn short premium work, a small cheap game, or a deliberately finite experience into a feature/hours checklist. Negative and uncertain assessments are treated as useful outcomes. The code is appropriately a consistency gate, not a claim to compute fun or willingness to pay.

That sound framing does not remove the authority defect. Nor do passing synthetic cases establish that any actual game is worth its price. The implementation's source declarations, observed sessions and reviewer isolation still require honest operation. No real-product assessment or USER acceptance was performed here.

## Independently executed checks

- Product contract/integration suite: 32/32 passed
- Entry/setup suite: 25/25 passed (only temporary installation fixture paths)
- Factory core suite: 109/109 passed with isolated writable XDG directories
- Changed-commit whitespace check: passed
- Additional legacy authority mutation reproduction: confirms the defect above

166 existing tests passed. This is bounded implementation review, not a new full-suite PASS: Studio, Gameplay, Idea, Asset/Sound full suites and real runtime/UI/media judgment were not rerun by this reviewer. Prior engineering test reports were read as context, not adopted as independent results.

No frozen source file, active E&U checkout, global installation, consumer pointer, real game authority or user approval was changed.
