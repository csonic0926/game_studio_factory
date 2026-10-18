# GPT-6 Factory — explicit workflow 3

Applies only to factory_project.v3 / workflow_version 3. v1/v2 remain their own
contracts. This file owns process; specialist documents own creative judgment.
Project USER authority outranks defaults. No model-name detection or automatic
upgrade. Git is provenance, not the validity test. No token-comparison gate.

## Operate, not perform a thinking ritual

Resolve the project's selected checkout and run factory.py inspect. Then request
context for the actual capability/task. Read current authority, complete applicable
requirements, work and unresolved questions. Method ids are optional tools for a
specific problem: context --method <id> expands them. Unclassified project
limitations stay in full; no token target permits dropping authority.

Continue authorship and production in the same primary agent. Create full works,
not summaries that fill a schema. Checkpoint references at meaningful boundaries
or interruption. On resume, inspect the checked ledger; chat memory is not state.
Author context reports checkpoint validity and the next legal action. A stale
checkpoint returns current authority plus explicit blockers, never a refreshed
fingerprint masquerading as the old authorization. Proposed designs must be
checkpointed as new drafts before their own review/production boundary.
No mandatory per-step workers, fixed paragraph sizes, intermediate handoff files,
generic review on each reply, or independent Card/spec authors. Former process
clauses in project-generated Factory documents are superseded, not their quality
or semantic obligations. The obligation map lives in knowledge.json and the
stable rule_map ids. Unknown/missing method or dependency blocks rather than
being silently dropped.

## Complete design and independent review

factory_design.v3 preserves the v2 identity, full artifacts/inputs, requirements,
production paths, acceptance and domain bindings. It adds methods (selected ids,
empty is valid) and decision_sections (exact authored source text + decision ids).
The human view contains those sections and the exact decision/consequence
excerpts; reviewers verify both omissions and expansion. No separate rewrite.
Gameplay keeps graph, actual-interaction and project-standard mechanical checks,
with native material sections instead of mandatory legacy Markdown extraction.

Freeze ONE exact design plus its relevant dependency closure. Two fresh reviewers,
different from author and each other, independently inspect that same version
without first-pass peer conclusions. Intent/experience covers purpose, player
work/response/carry-forward, two-lap change, emotion, voice, knowledge and meaning.
Completeness/project covers all applicable project/Factory requirements, sources,
composition, feasibility, red lines and the human decision surface. Both must
cover every bound project source, not just author-chosen requirements.

After a FAIL, continue revising within authority, preserving failed reports and
new versions. Rerun both on the exact revised version. Stop for a necessary USER
choice, unavailable source/tool, or a repeated blocker with no useful new repair;
report the exact checkpoint, not a fabricated PASS. Ordinary mechanical repairs
reuse existing authorized design/ruling and scope; materially changed design,
meaning, inputs or unknown dependencies reopen the design boundary.

After both pass, present the tool's checked human view. USER owns product adoption,
material design approval and playtest verdicts. Authorization still requires the
verbatim approval action emitted by context --role human, bound to raw USER role
and content. An operator cannot invent the action's USER submission or reinterpret
rejection, quoted approval, exploration or this context view as authorization.

## Authorship modes (USER-selected)

A v3 project runs in one of two modes, recorded at design/factory/AUTHORSHIP_MODE.json
(factory_authorship_mode.v1). Absent means COLLABORATIVE. Only a raw USER message
selects or changes it (`factory.py mode --set ... --source ... --quote ...`); never
infer it from a model name or switch it on your own.

- COLLABORATIVE (human + AI): the current process. Per-idea Idea inquiry remains
  required guidance; the present USER is its check. idea_coverage is optional and,
  when recorded, only its shape is validated; OPEN judgments/questions may travel.
- AUTONOMOUS (AI with full delegation): skipping Idea is not allowed. A studio or
  gameplay design must carry idea_coverage: game-owned idea_inquiry.v1 records bound
  as design inputs, and every decision id classified as relying on inquired ideas or
  as not a design idea (with a reason). Relied-on ideas must be ADOPT. Every open
  question needs a disposition: ANSWERED (answer), HYPOTHESIS (falsification and
  test stage) or DEFERRED (reason and revisit point). Both reviewers additionally
  judge `idea.per_idea_inquiry_substantive`: that the inquiry is real reasoning,
  that no material mechanism hides behind a not_a_design_idea label, and that
  coupled whole-game consequences were considered.

- CLOSED_BETA (full delegation to a closed beta): AUTONOMOUS obligations plus the
  USER's named seats (`delegation.seats`: DESIGN_APPROVAL, INTERNAL_PLAYTEST_VERDICT)
  for the named product. The Director approves reviewed designs with an AI_DIRECTOR
  ruling bound to its DESIGN_APPROVAL note; such rulings are never USER rulings and
  are invalid in any other mode, so revoking the mode stops their authorizations.
  The USER first plays the delivered closed-beta build; that verdict binds.

In AUTONOMOUS and CLOSED_BETA the orchestrator is the Director
(`factory_core/docs/DIRECTOR_ROLE.md`): it plays, judges fun and direction, and records
a `factory_director_note.v1` at DESIGN_COMPLETE, PRODUCING, EVIDENCE_READY and (CLOSED_BETA)
AUTHORIZED. A boundary advances only on the Director's CONTINUE; the latest STOP or KILL
blocks production stages. The Factory checks that the judgment exists, played and decided;
never whether it is right.

The mode file joins every design closure, so switching modes invalidates earlier
reviews; continue through a new draft. COLLABORATIVE and AUTONOMOUS do not change USER
ownership of commission, material design approval or playtest verdicts; CLOSED_BETA
delegates only the seats the USER names.

## Persistent state and production

The existing factory_checkpoint.v2 / factory_review.v2 / factory_ruling.v2 record
shapes remain the shared protocol; v3 designs select new behavior, not a duplicate
ledger engine. Stages remain DRAFT -> DESIGN_COMPLETE -> REVIEWED -> AUTHORIZED ->
PRODUCING -> EVIDENCE_READY -> specialist COMPLETE. A current rejection or new
draft blocks older authorization. No stage skipping. Checkpoints are append-only
and compare-and-swap on the predecessor; approved history never gets rehashed.

Authority is USER/adopted contracts. Work is tool-owned checkpoints. Context is a
rebuildable view. Evidence/accepted history is exact execution and specialist
acceptance. Production cannot overwrite authority, work state, accepted history,
or live immutable design inputs. Pin current implementation input in Git when it
will be changed. Plans add bounded execution details, not unapproved decisions.

Related code/schema/rule membership, mandatory project authority, complete input
closure and selected method contents determine validity. Unused method *contents*
are not dependencies. Changing selected method ids/content restarts design.
Method catalog changes are conservative resolver changes and require revalidation.
Unknown references and concurrent edits fail closed.

## Non-merged acceptance boundaries

Runtime blind observation receives only the existing sanitized player packet;
generic context refuses the blind role before opening project data. A separate
informed comparison reads the immutable observation and design afterward.

Story retains bounded clean-room spoken fluency, canon-aware backcheck and fresh
latest-output semantic QA in every shipped locale. No-dialogue and no-runtime
scopes must be explicit in the reviewed design/profile, not invented at QA.
Asset/Sound completion proves technical pipeline output, not creative acceptance.

Gameplay uses factory_gameplay_acceptance_input.v2 through studio/v2.py and the
existing baseline admission/human/runtime contracts. The production plan bridge
still consumes factory_checkpoint.v2, verifies its v3 design and exact authorized
output scope. Tests, screenshots, engine success and AI PASS do not authorize or
accept gameplay. Promotion requires new-play acceptance, exact-build USER verdict,
applicable predecessor regression and no blocking gap. With no predecessor,
record absence honestly and use initial reconstruction admission; never invent one.
Independent Story completion needs no product commission or playable baseline.

## Opt-in and recovery

migrate --workflow gpt6 defaults to check; apply needs the exact preview digest.
v1/unversioned and v2 may migrate to v3. Identity and existing adopted authorities
cannot be dropped. Repeating exact v3 opt-in is a no-op; implicit downgrade is
forbidden. Routing/pointer/ignore/receipt are preflighted, metadata activates last,
and an interrupted transaction blocks project use until exact recovery. OS lock
plus source/target hash checks protect cooperating writers; no universal atomicity
against external editors is claimed. No backup copies or branches.

Old checkpoints/reviews/rulings retain their original schema and meaning. A v2
task on a v3 project is HISTORICAL_WORKFLOW_REQUIRED, not newly valid authorization.
Continue through a new task/design checkpoint citing the old sources; do not
rewrite the old chain, manufacture fresh reviews, or re-ask settled product intent.
Routing-only compatibility receipts preserve prior proofs, never renew reviews.

### Explicit unchanged-contract production continuation

For a collaborative v3 task whose latest checkpoint is already PRODUCING, an
explicit USER instruction may preserve its original design approval while moving
to a different Factory checkout. Use `factory.py continuation --task-id <id>
--check`; publication additionally requires `--apply --expected <preview digest>
--source <raw USER JSON> --quote <exact submission> --summary <progress>`.
The source must preserve the actual USER message and the operator must retain the
preceding compatibility request as provenance. This selects compatibility handling,
not a new design approval, new review, changed product, or gameplay acceptance.

The independent append-only continuation ledger preserves the checkpoint, original
dependency fingerprint, exact historical Factory Git bytes, reviews and USER ruling.
It rejects altered project inputs/authority/design, newly discovered project inputs,
changed applicable review-rule membership, changed mode, archived authority, unavailable
historical bytes and a later task checkpoint. Current design parsing must also pass.
Both current resolver closure and original contract are bound and rechecked; future
Factory changes invalidate the receipt. Historical output artifacts are not revived.
Use repeated apply with approved `--artifact` paths to record new exact outputs.

Inspect/context identify this as HISTORICAL_CONTRACT_CONTINUATION, never CURRENT_CHECKPOINT
or refreshed authorization. Normal checkpoint/review/acceptance validators remain
unchanged. The continuation permits only original-scope PRODUCING; it cannot publish
COMPLETE, accept gameplay, or promote a baseline. New material design and final
acceptance retain their own normal boundaries. A receipt is not a blanket exemption
from newly applicable rules; incompatibility fails closed for a specific resolution.
