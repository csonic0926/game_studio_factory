# Product Factory: whole-product value gate

Design for independent review, 2026-10-09. Base: gpt-6-adaptation
b3eb3ae9ec4379e92be687780f92cf0851f1f3e3. No implementation is authorized by
this document itself. This is reusable Factory work, not a game-owned approval.

## 1. Intent and ownership

Idea Factory asks what coherent product should be commissioned. Product Factory
asks whether the experienced whole product gives its intended buyer a convincing
reason to pay the stated price. A good premise, a functioning loop, polished art,
long playtime, feature count, or technical release readiness alone does not answer
that question. Product value is a contextual model/human judgment supported by
experience, not a score inferred by Python.

The value proposition can rest on mastery/replay, a short authored experience,
aesthetic expression, distinctive interaction, comfort/convenience, or a coherent
combination. Deliberate smallness and a definitive ending may be strengths. Art,
audio, interface, surrounding features and support for the intended play situation
matter through what they contribute to the purchase, not as additive checkboxes.
No universal dollars-per-hour, minimum content quantity, premium-art requirement,
replay mandate, or mandatory feature inventory is introduced.

Idea keeps product promise, audience relationship, commercial shape, experience,
replay/retention thesis, differentiation, scope, sacrifices and commission.
Gameplay/Story/Asset/Sound keep production expertise. Studio keeps orchestration,
product activation/archive and accepted playable baseline admission. Product
Factory owns the evidence-grounded value assessment and its claim gate. It cannot
change the price, audience, promise, constraints, game, or user acceptance to make
its own assessment pass.

## 2. What Idea actually does, and what transfers

Source references below are at the base commit, not claims about uninspected
future versions.

- `idea/docs/PRODUCT_DEFINITION_WORKFLOW.md` and `idea/idea.py:377-435`:
  start binds one game root; existing complete canonical authority is checked,
  partial authority blocks overwrite, and explicit reopen preserves the old
  authority. A bounded probe is a study aid, never semantic authority.
- `idea/idea.py:545-626,650-848,915-972`: evidence/probe validation and exact
  derived exploration checking preserve OPEN, REFERENCE_NO_FIT,
  LIVE_DIRECTIONS and DIRECTION_EMERGED. Even an emerged direction is non-binding.
  Reference no-fit is a valid answer; schema filling must not manufacture one.
- `idea/idea.py:974-1071,1073-1351`: commission binds exact exploration bytes,
  one emerged direction, checked view, repository state and authorization quote.
  USER_FIXED, REPO_COMMITMENT and scoped AI_DELEGATED decisions can bind;
  AI_RECOMMENDED material decisions require resolution and validation hypotheses
  cannot become constraints. The quote fields are auditable operator assertions,
  not authentication or a proof that the user genuinely commissioned the work.
- `idea/idea.py:1513-1630`: compile preflights every canonical output, refuses
  differing authority, is idempotent for identical bytes, and check recomputes
  the exact handoff. It proves provenance/consistency, not good judgment or fun.
  Completed authority can survive later unrelated repo commits (`start` checks
  it without imposing the original exploratory snapshot as perpetual validity).
- `factory_core/docs/WORKFLOW_GPT6.md` and `factory_core/state.py:225-317`:
  two fresh non-author/non-peer contexts review one sealed complete design and
  dependency closure. FAIL requires revision and fresh reviews of the new
  version; current rejection/new draft prevents falling back to old approval.
  The exact USER ruling is a separate boundary. These are shared v2/v3 process
  contracts, not reviews executed by `idea.py`. Declared fresh IDs are checked;
  the harness/operator remains responsible for actual context isolation.
- `factory_core/state.py:319-396` and `factory_core/context.py:90-171`:
  append-only stages, compare-and-swap predecessors and exact references keep
  stale work from being rehashed into current authorization. Blind runtime
  observation cannot use generic informed context.
- `studio/product.py:269-328,535-768` and
  `studio/docs/PRODUCT_AUTHORITY_LIFECYCLE.md`: activation/archive belongs to
  Studio. NO_ACTIVE_PRODUCT_AUTHORITY overrides surviving code and old
  baselines. Archiving preserves history and never fabricates user rejection.

Transfer: honest open/negative outcomes, evidence versus hypotheses, explicit
scope/authority, exact dependency invalidation, independent judgment, immutable
reviewed outputs and a gate that refuses a stronger claim than the evidence.
Do not transfer: a new product commission for each assessment, automatic proof of
fun/value, forced convergence, a duplicate product-authority register, or generic
production permission from an assessment. Do not conflate a recorded negative
assessment with a failed tool execution.

## 3. User-facing operating behavior

1. Resolve one explicit game. Read its current authority and known intended offer.
   Discover actual target price/platform/region/audience from authoritative
   material; separate current offer, user-proposed offer and AI scenario. Missing
   price/audience stays explicit. Do not silently use a released price as the
   selected redesign price.
2. Understand the purchase promise and the likely buyer's actual experience.
   Study/play the available exact build. Reuse trustworthy exact runtime/media
   evidence; supplement it where the current value claim is untested. Inspect
   pixels/audio when those qualities matter. A screenshot's existence or
   non-overlapping controls is not aesthetic polish or purchase desirability.
3. Write one concise but complete value case: why this coherent experience might
   justify this offer, what is actually delivered, its strongest contrary
   evidence, important tradeoffs/omissions, what remains unknown, and the next
   decisive test or recommendation. Use comparisons only when they discriminate
   the real question, with current primary sources and explicit comparability
   limits. No comparison quota or feature extraction obligation.
4. At a concluded assessment boundary, get two fresh independent reviews of the
   same exact assessment/evidence package: intent/experience (does the causal
   value case hold?) and completeness/project (is evidence/authority/scope honest
   and sufficient?). Neither sees the peer's first-pass conclusions. Preserve
   disagreements and revise/review a new version; never average them into PASS.
   Existing sanitized blind observations stay blind; these value reviewers are
   explicitly informed and cannot be represented as blind players.
5. Record a supported, gap, insufficient-evidence or unresolved-context judgment.
   Deliver the useful verdict in ordinary language with price/audience/build
   qualifiers. A gap can recommend better integration, removal, refinement,
   audience/price reconsideration, or no further investment. Adding features or
   hours is never the default repair. Material promise/price/audience changes
   return to the user/Idea; execution goes to the owning factory within authority.

Product assessment is permitted before a complete build; the honest result can
be EVIDENCE_INSUFFICIENT. It does not block learning prototypes or accepted-slice
work. It gates the assertion that an integrated product's offer is worth buying.

## 4. Minimal module and contracts

Add `product/` with AGENTS, README, caller landing, `product-factory` skill,
one value-assessment workflow, reviewer guidance, schemas/templates, a small
Python CLI and focused tests. All filled game artifacts go under
`design/product_value/<assessment_id>/` in the game, distinct from canonical
`design/product/` commission/lifecycle authority.

The standalone CLI is additive and can assess a legacy game without migration,
relinking, reissuing old approvals or claiming it follows v3. Its result records
that it is a standalone assessment; explicit v2/v3 design work still uses the
selected project's shared process. A study/assessment is not authorization to
alter the product. Existing callable CLIs remain unchanged.

CLI surface:

- `inspect --game-repo`: read-only current authority/inventory and available
  Product results; no price inference and no generated thesis.
- `prepare --game-repo --input`: validate one assessment; return its exact
  reference, dependency fingerprint and review requirements. No writes, PASS,
  acceptance, or demand that missing evidence be invented.
- `record --game-repo --input --review <path> --review <path>`: validate both
  exact independent reviews and publish one immutable deterministic result at
  the assessment's owned location. Repeating identical output is idempotent;
  differing output requires a new assessment id. Negative/unknown judgments
  are legitimate recorded results.
- `check --game-repo --result`: verify exact source closure, current mandatory
  authority membership and all review bindings, retaining the semantic verdict.
- `gate --game-repo --result --build <path>`: additionally require the exact
  build/manifest requested by the consumer, grounded offer context and a
  supported judgment. Any gap, unknown, hypothetical-only context, stale source
  or rejected review fails closed. Return a value-claim status only, never a
  gameplay/baseline/user-acceptance status.

`product_value_assessment.v1` is a bounded evidence index plus authored prose:
identity, author context, subject/build ref (nullable if unavailable), offer
(price amount/currency/platform/region and provenance, current/proposed/scenario
qualification), audience and provenance, evidence records with exact refs,
runtime evidence tied to subject build, full value-case report ref, judgment,
open questions/limitations and next move. Price/audience use explicit grounded,
hypothesis or unknown states; unknowns cannot yield an unconditional supported
claim. Proposed offers can be reviewed but remain clearly conditional; a
scenario cannot silently become the active price. No scores, category weights,
minimum playtime or mandatory replay count.

The full report remains human prose and supplies purchase promise, experiential
case, coherence/tradeoffs, counterevidence, price/audience reasoning and limits.
The validator checks references and declared relationships, not whether prose
is persuasive. Coverage of relevant art/audio, surrounding product affordances,
replay or satisfying closure and deliberate exclusions is the reviewers' job;
these are judgment lenses, not six compulsory feature quotas.

`product_value_review.v1`: role, reviewer context, declared fresh/peer-isolated
status, exact assessment reference and dependency fingerprint, AGREE/REVISE,
reasoned findings/evidence and complete bound-source coverage. AGREE means the
assessment is sound, including a well-supported negative or unknown conclusion;
it does not mean the product passes. At least one actual build-bound experiential
source is mechanically required for a SUPPORTED judgment. Reviewers determine
whether the experience is representative and sufficient; a test log alone can
never fill this field. Every review checks the whole assessment, not just a
partition that lets contrary evidence fall between roles.

`product_value_result.v1`: exact input/review refs, full dependency references
and fingerprint, semantic judgment, explicit conditionality, mechanical check
status, value-claim eligibility and fixed `user_accepted:false`,
`delivery_eligible:false`. Current outputs preserve all review evidence, never
manufacture a human verdict. The reviewed source package is immutable; new
claims/evidence/revised judgments produce a new assessment id/version.

Use existing confined refs, SHA-256 closure, advisory project lock and exclusive
publication helpers. Bind current mandatory root/product authority, Factory
Product contracts and selected experiential/build/context sources. Do not use
Git HEAD as a universal freshness test. A frozen old build assessment can remain
historically valid, but cannot pass a gate for a different build. Changed build,
price/audience source, media/evidence, report, relevant rules or authority makes
the current claim stale; no rehash-in-place of old reviews. All references are
root-confined; external facts are recorded with source URL/date in game-owned
source artifacts before use. Concurrent edits are rechecked before publication.

## 5. Integration and compatibility

- Add `product` to capability catalog and additive v2/v3 design/checkpoint enums;
  expose Product context/docs and a few named Product review obligations without
  changing the meanings of existing capability rules or historical formats.
- Product material design/remediation plans can use the existing v2/v3 shared
  design-review/ruling chain. Standalone read-only assessment does not force the
  user to approve a study plan or a negative conclusion. An optional Product
  ledger task closes only with a checked exact Product result; completion means
  assessment completed, not product supported. Result files must be among that
  task's actual outputs. No generic PASS becomes specialist acceptance.
- Update root caller index, architecture and setup-generated specialist routing.
  Existing automatic skill discovery finds the new skill. Do not run install,
  relink or migration on any real consumer.
- Add a small read-only `check-value` consumer to `studio/product.py` that calls
  Product's exact-build gate. Existing activate/archive behavior is untouched.
  Update Studio docs/skill: invoke Product before asserting whole-product paid
  value; use its gaps to choose the next authorized work. Existing baseline
  admission remains a separate gameplay/exact-human/regression boundary. A
  baseline is not retroactively invalidated or converted into value acceptance.
- Existing v1 command/schema/history tests, v2 contracts and explicit v3 opt-in
  must remain readable/operable. Using this changed checkout can correctly stale
  dependencies; no existing consumer is silently pointed to it. E&U's active
  b3eb3ae checkout and all pointers remain byte-for-byte unchanged.

## 6. Behavioral and engineering verification

Two test layers must remain distinct. Python proves contract/control-flow
behavior on labelled synthetic fixtures. It does not prove that a real game is
fun or good value. Fresh reviewers also evaluate these scenario narratives for
whether the workflow would make the right contextual judgment:

1. Good functioning idea, weak purchased experience: meaningful core decisions
   work but buyer-facing appeal/finish and repeat/closure promise lack evidence.
   VALUE_GAP or EVIDENCE_INSUFFICIENT is legal; runnable/Idea-approved is no pass.
2. Expensive art cannot compensate: exquisite presentation plus empty or tedious
   promised interaction. No summed aesthetic score can cover the central gap.
3. Short high-value work: a brief complete expressive experience fulfills a
   grounded premium niche promise; no required padding/replay loop blocks support.
4. Low-price small game: a coherent limited affordable offer delivers its honest
   promise. It may pass without more modes/content or AAA polish.
5. Unknown target price/audience: remains CONTEXT_UNRESOLVED; cannot infer a price,
   import the released price as redesign adoption, or issue unconditional support.
6. Hypothetical different price/audience: conditionally reasoned scenario does not
   overwrite authority or pass the current-offer gate.
7. Pure build/QA success, screenshots, time counters or feature totals do not
   substitute for exact experiential evidence or sound reviewer judgment.
8. Reviewer disagreement, author/self-review, peer contamination, incomplete
   source coverage, changed input/build/price/rules and reused stale reviews block
   publication/gate. Negative record publication itself succeeds honestly.
9. Idempotence, all-output preflight, symlink/path escape, concurrent edits,
   current authority archive and build mismatch fail closed without partial
   authority writes, history edits or product/game mutation.
10. Additive capability routing/context/checkpoint/acceptance works on explicit
    v2/v3 fixtures; legacy standalone assessment needs no migration. Existing
    Studio activate/archive, Idea no-fit/commission and baseline behavior remains.

Run focused Product tests then full entry/setup, factory_core, Studio, Gameplay,
Idea suites, plus Asset/Sound regressions affected by shared routing. Separate
passed, failed, skipped and unavailable runtime checks in the final report.

After implementation review, exercise the contract on current SAB evidence at
the exact available build and actual current offer. This is a concrete honest
assessment, not a benchmark score or preordained failure. Missing redesigned
price/target evidence stays missing. Do not alter SAB content or E&U to make a
fixture pass. The exercise's positive/negative result is not USER acceptance.

## 7. Workspace/publication boundary

GitHub branch head was checked through the GitHub connector and matches b3eb3ae.
Development uses a new detached active worktree of that head because the named
adaptation branch is already checked out by a live consumer. This creates no
backup branch/repository and does not switch or reset the active checkout.
After review/verification, commit the work on the authorized adaptation line;
any publication must target only gpt-6-adaptation and first recheck its head.
No main merge, consumer relink, global skill installation, or game migration.
