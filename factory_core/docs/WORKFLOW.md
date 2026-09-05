# Factory v2 — state and boundary contract

This is the sole v2 process authority. It applies only after explicit migration
activates `design/factory/PROJECT.json` version 2. Specialist methods own domain
judgment; project/user authorities outrank Factory defaults. Legacy records and
v1 CLI formats keep their meaning; neither this document nor migration renews
an approval. Ordinary language is enough to invoke a capability.

## Operate

1. `factory.py inspect --game-repo <root>` reads version, history, current work,
   blockers and the next legal action. Resolve explicit root -> current Git root;
   never scan sibling games. `MIGRATION_REQUIRED` means check/apply an explicit
   migration, not silently execute v2 or repair historical hashes.
2. `context --capability <name> --task <kind> [--task-id <id>]` returns current
   authorities in full, work and cited methods. Read the task-specific originals
   when judgment needs them. If a referenced limitation is unknown or authority
   conflicts, resolve it; do not truncate it to fit a token target.
3. Continue creative and production work in the same primary agent. Save full
   deliverables, not schema-filling substitutes. Checkpoint references and
   unresolved questions at meaningful boundaries or session changes. A new
   session resumes from the checked ledger, not assumed chat memory.
4. Freeze ONE complete design package (`factory_design.v2`). It references full
   source artifacts, inputs, decisions, project obligations, production paths and
   acceptance requirements. A Card is a checked projection of exact decision
   and consequence excerpts; a separate author must not rewrite the same spec.
5. Two fresh reviewers, different from author and one another, independently
   inspect the **same exact package and dependency fingerprint**. First-pass
   reviewers may not read one another's conclusions. `context --role
   intent_experience` and `--role completeness_project` omit work/review reports.
   Harness isolation is required: a JSON freshness declaration alone is not
   evidence that independent execution actually happened.
6. Intent/experience owns purpose, product causality, player work -> visible
   response -> carry-forward, two-lap difference, narrative emotion, voice and
   knowledge. Completeness/project owns every applicable rule, adopted project
   standard, composition artifacts, feasibility, decision-surface coverage,
   red lines and truthful claims. `rule_map.json` maps former gate obligations;
   project-specific requirement ids are also mandatory. Both reviewers inspect
   all bound project sources, not merely author-selected claims.
7. After both pass, present the checked human view. USER owns product adoption,
   material new-design approval and playtest verdicts. Preserve raw message role,
   wording, exact design and fingerprint in ruling evidence. `context --role human`
   emits an exact approval action; only its verbatim USER submission authorizes
   production. An ordinary-language reply can discuss/reject the proposal, but
   tools never reinterpret a quote (especially a rejection) as approval. No tool can authenticate a fabricated
   transcript; the operator must never author a USER verdict as if received.
8. Production adds execution details only within approved scope. An already
   authorized mechanical repair uses the same design/ruling and verified repair
   scope; no new design review merely for implementation failure. A new material
   decision, changed relevant rule/input, or unknown dependency reopens design.
9. Verify the latest actual outputs, not only the approved plan. Story requires
   exact-landed-output semantic/prose/locale QA; gameplay requires actual
   interaction and independent runtime acceptance. Failed output returns to
   production within scope, not an invented approval. Only specialist acceptance
   can close delivery; a checkpoint never certifies gameplay or a baseline.

## State ownership and causal boundaries

| Object | Owner | Allowed writes |
|---|---|---|
| Authority | USER / adopted project contracts | Explicit recorded decisions; never inferred from work |
| Work | primary agent via checkpoint tool | New immutable generation, exact predecessor, references/progress/questions |
| Context | derived tool output | Rebuild only; never approval or persisted source of truth |
| Evidence / accepted history | specialist evidence and admission tools | Exact execution/observation; no rewritten accepted predecessor |

Stages: DRAFT -> DESIGN_COMPLETE -> REVIEWED -> AUTHORIZED -> PRODUCING ->
EVIDENCE_READY -> specialist acceptance. Repeated stage checkpoints are allowed.
Changed design restarts at DRAFT. No stage skipping into authorization. A current
rejection/superseding checkpoint blocks reuse of an older authorized checkpoint.
Checkpoints are append-only and compare-and-swap on the previous file digest.
COMPLETE consumes the owning specialist: checked Studio baseline admission,
exact-output Story semantic acceptance, or successful Asset/Sound deliverables.
Provider completion remains technical, never gameplay or creative-quality
acceptance. Idea exploration may finish as an open/no-fit specialist result
without a completed design or manufactured product commission.

Relevant validity = content hashes of the complete declared input/design set,
mandatory project authorities, resolver/registry/core code, and capability
code/schema sets. Membership participates, so newly added validators invalidate.
Git revision is provenance, not v2 validity. Unrelated documents/tests do not
invalidate. Current implementation inputs that production will change must be
pinned in Git history, not treated as both immutable design input and live output.
Do not change an old hash to obtain a new PASS.

## Isolation that is not merged

- Blind observation receives only the existing Phase-A sanitized/attested
  player input. `context --role blind_observer` refuses generic context entirely.
  Run a fresh observer without inherited author/design context, then a different
  informed comparison on the sealed observation. Never pass expected answers,
  future knowledge or answer-bearing path/beat ids to Phase A.
- Story spoken-fluency remains a bounded clean-room technique when quoted text
  is newly authored/revised: separate fresh language context without design
  documents, mechanically extracted protected/banned forms and frozen beats,
  followed by canon-aware back-check. It does not take over chapter authorship
  or restore a worker for every step.
- Runtime tests, screenshots, AI reviews and execution success are evidence,
  not gameplay acceptance. New gameplay, exact-build USER playtest, predecessor
  regression and no blocking gap remain prerequisites for baseline promotion.

## Migration and concurrency

`migrate` defaults to read-only check. Apply requires its exact source digest.
It adds version metadata and changes only the owned routing span, with an
activation-last transaction receipt. Historical statuses and hashes remain
unchanged. A routing-only compatibility receipt proves the old adopted root
contract differs solely in that span; it never renews reviews. Other root-rule
changes still invalidate. Repeated migration and ordinary relink preserve v2.

Factory v2 writers and setup/relink participate in an OS advisory lock. Hashes
are checked before publishing; a durable transaction digest records the exact
write set and before/after hashes. Crash recovery recognizes only the same
transaction's already-exact outputs, not arbitrary existing files. External
editors that ignore the lock must not race the final atomic replacement; no
portable filesystem-wide transaction guarantee is claimed. Conflicts preserve
the competing file and remain blocked. There are no backup copies or branches.

## Cost and quality

`benchmark` uses fixed independent fixtures and accounts for author, reviewers,
failures and rework. Total = input + output; cached input is a separately
reported subset, reasoning is not added twice. Missing usage or missing quality
verdicts never counts as savings. Compare both rounds at equal deliverable and
quality requirements; creative quality needs USER confirmation. No predetermined
percentage and no shorter/poorer work as a shortcut.
