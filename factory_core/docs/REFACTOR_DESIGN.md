# Factory v2 design boundary

Baseline: `9e35392b954d627a451e010e8b51d8b93f8ff32c` on `main`.
User intent: continuous primary-agent authorship, tool-owned state, on-demand
expertise, independent boundary reviews; measure total task cost, not brevity.
No provider/model API executor, scheduler, game content changes, backup copies,
or extra branches. Benchmark fixtures are new isolated cases, not game copies.

## Objects and transitions

- A: external authority (user decisions, project rules, approved designs).
  Factory never promotes a context summary, exploration, or checkpoint into A.
- W_t: immutable, versioned work checkpoint with artifact references, stage,
  unresolved questions, task identity and exact predecessor digest.
- C(A,W,role): rebuildable context view. Author and each reviewer receive all
  applicable constraints, no silent truncation. First-pass reviewers receive
  the same design digest and no other review. Blind observers use a separate
  sanitized player-input protocol; generic context refuses this role.
- E: execution/observation/acceptance evidence and accepted history. Only the
  existing specialist evidence and baseline validators may establish runtime
  acceptance. v2 checkpoints cannot declare a baseline or human approval.
- D: exact complete design package, including all project-required composition,
  cycle/two-lap, interaction, narrative, UI, implementation and decision-surface
  obligations as applicable. Human Card = references/excerpts from D with a
  coverage map; no second independent spec author. Production plan adds only
  execution details within D.
- F(D): content fingerprint over complete relevant tool/rule/schema dependency
  closure, project authorities, inputs and D. Git revision is provenance only.
  Unknown closure fails closed; adding/removing a relevant file is a change.

Continuous authoring -> D -> two fresh independent reviews of F(D) -> exact
human ruling if required -> production -> specialist evidence + acceptance.
Intent/experience review owns semantic fidelity, causal player work, story
emotion/voice/knowledge. Completeness/project review owns all mapped rules,
project standards, feasibility, coverage and truthful decision surfaces.
Review reports bind the same D and F; different from author and each other;
first-pass peer conclusions forbidden. Repairs under explicit existing scope
reuse the frozen design/ruling, verify the repair scope, and do not reopen it.
Changes to relevant authority or design invalidate reviews; history is never
rehashed or automatically reapproved. Runtime blind observation and informed
comparison remain different fresh contexts; human playtest remains mandatory.

## Implementation boundaries

`factory.py` provides inspect/context/checkpoint/migrate/benchmark with stable
JSON diagnostics and nonzero blocked exit codes. `factory_core/` owns path
safety, content references, dependency closure, append-only work transitions,
read-only legacy inventory, idempotent optimistic migration and usage parsing.
Specialists keep CLI names/arguments and own domain validators. v2 authoring
is selected only by explicit project migration; unmigrated projects return
MIGRATION_REQUIRED through new routes. Legacy CLIs/records retain historical
semantics and are not made current by changing hashes. Old workflows remain
readable as explicitly versioned compatibility material, never simultaneously
active with v2 process rules. Existing project semantic requirements still bind.

Project metadata: `design/factory/PROJECT.json`; immutable checkpoints:
`design/factory/checkpoints/<task>/<generation>.json`. Migration is additive
except its owned routing block, performs complete preflight and source digest
checks before writes, uses a cooperative exclusive lock, exclusive new-file
creation and atomic replacement, and leaves no success marker for partial
work. Recovery reconciles only already-exact transaction outputs; concurrent
changes abort without overwriting. No backup files. Initial migration stores
historical references/statuses but creates no work, review, verdict or baseline.

Context uses explicit dependency refs plus a capability-specific mandatory
rule/authority inventory (including nested project AGENTS and declared inputs).
It returns full authority and relevant work, plus cited methods for optional
reading; never substitutes a token limit for valid restrictions. Unknown
reference/version reports a blocker rather than assuming applicability.

## Verification and release

Capture original tests; add adversarial transition, stale/unknown dependency,
path/symlink, race/retry, role isolation, legacy history and non-convergence
cases. Exercise Story craft checkers, mock Asset/Sound and isolated Godot
technical/UI/state/regression evidence without claiming human acceptance.
Benchmark four fixed tasks x old/new x two rounds, pinned Astra/settings/input
hashes/requirements/permissions. Parse every author/reviewer/failure/rework
JSONL: input + output, cached input separate, reasoning a subset of output.
Missing usage, failed attempts without usage, unmatched variants or no human
creative-quality verdict => incomplete, never token-saving success.
Banner: preview first, change integration/process rules only, retain untracked
files and exact approved/rejected/pending history, no content/baseline writes.
Completion requires passing capability/quality gates and lower total tokens in
both rounds. Implemented mechanisms are not that empirical completion claim.

## Resolved boundary details (revision 2)

- `gameplay/design_gate.py` dispatches only an explicit `factory_checkpoint.v2`
  ref through `gameplay/v2.py`. It reuses full-objective material extraction,
  graph causality, project standard/composition and concrete interaction checks.
  Every material statement projects into the human view. The plan validator
  additionally forbids paths outside approved production scope. v1 paths retain
  their original authorship/review/revision checks.
- `studio/baseline.py` dispatches `factory_gameplay_acceptance_input.v2` through
  `studio/v2.py`: current evidence-ready checkpoint, content closure, full graph,
  observed two-lap change and unchanged blind/runtime/comparison validator.
  Outer v4 acceptance review retains exact USER playtest token. Existing
  reconstruction/promotion/regression/gap/runnable-build checks remain in force.
  A v2 input's recorded Git revision is provenance; exact content closure is
  its validity test. No old review is adapted by inventing another identity.
- Stages and field contracts live in `factory_core/state.py` and schemas.
  A changed design restarts at DRAFT. Current checkpoint supersedes old execution
  eligibility, not historical truth. COMPLETE consumes specialist acceptance;
  provider completion remains technical, not artistic or gameplay acceptance.
- The v2 routing receipt records exact before/after AGENTS digests and a digest
  of everything outside the managed span. Only this exact routing-only change
  can satisfy an old adopted standard's collaboration reference; old hashes
  remain untouched. Relink uses the activated version, preserves the span and
  participates in the same lock. A later semantic edit still fails closed.
- Lock scope is participating Factory v2 writers/setup. The durable transaction
  identifies project, authority paths, full source set, desired output digests
  and activation metadata. Recovery accepts only before or that transaction's
  exact after hashes. Hash checks minimize nonparticipating-editor races but do
  not claim OS-wide isolation against writers ignoring the advisory lock.
- `catalog.py` is the versioned dependency registry: mandatory root/nested
  AGENTS, active product authority, adopted domain adapters and explicit extra
  project authorities; complete capability code/schema membership, registry,
  resolver, core rules and task methods. JSON file references expand transitively;
  empty optional refs are absent, partial/missing/stale refs block. Historical
  register entries are inventoried, not made current. Git-pinned implementation
  inputs are read directly from ordinary Git history, never copied to backups.
- Story keeps the separate bounded clean-room spoken-fluency technique with
  protected/banned forms, frozen beat/information/voice and canon-aware back-check.
  It does not replace the continuing primary author. `story/v2.py` consumes
  independent latest-landed-output semantic QA: knowledge order, branch/route
  meaning, all-channel emotion, full prose, voice, every shipped locale, style,
  staging, glossary, twin/sync and USER gates, with exact output/evidence refs.
- `factory_core/benchmarks/suite.json` fixes four synthetic tasks, fixtures,
  output/quality requirements, old/new source paths, stage sequences, model,
  reasoning, permissions and two rounds. Old sources come from `git show` at the
  recorded main baseline; no game repo is copied. The finite harness launches
  Codex CLI sessions, not a model API service. Session logs and failures are
  retained; missing or unaccounted child usage blocks any savings claim.
  Its protocol must still pass the equal-work/quality audit before measured
  numbers can establish completion. Human creative-quality confirmation is
  external and cannot be supplied by either design or implementation reviewers.

The historical contracts are **moved** to explicitly named v1 compatibility
references (not backup copies). Their domain detail remains available; only
explicitly superseded process topology changes. No older accepted, rejected or
pending Banner artifact is reissued by the integration migration.

## Revision 3 — reproduced failures become invariant tests

The third implementation audit adds exact reviewed-surface approval actions
(rejection text cannot authorize); DRAFT -> complete and changed-design restart;
all declared migration sources and destination conflicts preflighted; recovery
must reproduce the prepared routing digest; partial transitive references fail;
Asset Blender validators join the execution closure. Generic production cannot
write specialist work/register/baseline objects. V2 gameplay dispatch preserves
project identity, well-formed provenance and cycle binding.

Story resolves the explicit adopted profile then registry/canonical location,
uses its actual STORY_ROOT sovereignty and shipped locales, and consumes typed
technical, clean-room packet/output and separate canon-back-check evidence.
Tests retain source/locale/voice/knowledge failures rather than hiding them in
schema-only acceptance.

The matched-workflow benchmark now declares both variant stage sequences,
includes bounded bilingual clean-room/back-check and latest-output Story QA,
keeps mechanical repair outside new-design reviews in both variants, and resumes
the new primary author. All independent reviews at a boundary see the same
candidate before findings return to the author; repairs rerun the whole boundary.
Source bytes freeze once; each attempt binds source/fixture/settings and logs;
unknown/orphan cost and changed final outputs block acceptance. Process success
alone does not pass a semantic review. USER equal-quality comparison binds exact
final artifacts and the complete usage ledger. These remain synthetic capability
trials, not new Banner acceptance or independent proof of creative quality.
