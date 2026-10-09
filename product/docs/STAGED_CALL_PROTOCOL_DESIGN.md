# Product staged-call protocol — proposed design

Status: revised design proposal, 2026-10-09. Not implemented or an active consumer
rule. Independent intent review permits only a bounded functional trial; the
execution-prompt repair below still requires execution re-review.
This document and its experiment specification are additive. They do not change
the nine-file causal-discrimination freeze or any historical result/review.

## Purpose and actual execution capability

Prevent a finished recommendation from supplying its own premises. A later
judgment must consume earlier, separately produced evidence/claim decisions;
another heading in one response or another Python validation is not a model call.
Outputs are concise source observations, claims, decisions and dependencies, not
private chain-of-thought transcripts. No architecture guarantees correct taste,
truth, demand or willingness to pay.

The available host can launch a fresh native agent with `fork_turns: "none"`,
give it a bounded prompt, await its result and obtain its context ID. Those agents
share the filesystem and available tools. There is no demonstrated per-agent
filesystem/tool allowlist, sealed sandbox, or host-authenticated call-receipt API.
Use operator-enforced context packets and record this limit explicitly. Do not
build an elaborate security runner or claim hard isolation from prompt discipline.

The operator launches each required call only after the preceding output is
sealed, passes the specified packet without the original author's transcript,
and asks it not to read other files or tools. For the bounded experiment, place
the complete small packet in the prompt; no repository reading is needed. A
source request pauses that stage for a documented packet revision. Accidental
extra exposure invalidates that attempt; keep it, and rerun with a fresh context.
Record observed tool use where visible; absence of observed misuse is not proof
of inaccessible data. Use the same model/settings across stages and trial arms.

This design's explanations are for the coordinator/reviewers, not worker prompts.
For the experiment, use only the exact neutral templates in the experiment file
plus their specified data substitutions. Never give a tested worker this complete
document, the experiment document, a rationale/example explaining the fixture's
failure, expected findings, or the other arm. The examiner has its own separate
neutral template; the coordinator's expected findings are withheld until the
examiner's response is frozen. Freeze the exact rendered packets before launch.

## Granularity comes from Idea's existing judgments

Idea currently puts anchors, reference relations, directions and frontier in one
`IDEA_EXPLORATION.json`; these are conceptual units, not existing isolated calls.
See `idea/docs/PRODUCT_DEFINITION_WORKFLOW.md:35–108`. Its commission boundary
changes authority. Product's assessment boundary does not commission a product.

The following stage types separate those units. They are not a universal quota
of paragraphs, alternatives, evidence or repeat playthroughs. A stage can finish
with uncertainty/no-fit; a decision-changing missing source may stop the process.

### A — Preserve source anchors

- Input: exact task, applicable USER/adopted authority and bounded original
  source packet. No completed assessment, prior rationale or examiner guide.
- Job: faithfully preserve who said what or which event was recorded. Separate
  adopted decisions, source assertions, observations and explicit proposals.
  Do not judge whether an assertion establishes a customer need or recommend.
- Output: source ID/location, exact short excerpt or event, attribution, scope
  and explicit ambiguities. A faithful quote proves that it was said, not true.
- Admission: references/excerpts exist; attribution and scope are present. A
  missing record stays missing; the operator must not add interpretive coaching.
- Why a separate call: the source inventory is fixed before anyone constructs a
  desired buying reason. Mechanical extraction could replace this call only when
  it actually preserves the required information without semantic inference.

### B — Determine support and relevance

- Input: sealed A and its complete raw sources, task and applicable authority.
- Job: decide what propositions those sources support, contradict, leave unknown
  or do not address. Preserve contradictions and population/build/time limits.
- Output: claim ID, proposition, `supported / contradicted / unresolved`, source
  anchor IDs, bounded scope, and a short explanation of the support relation.
  Authority/adoption is a separate property from empirical support.
- Admission: every asserted factual claim names evidence; citations resolve.
  Whether the evidence actually entails the proposition is B's semantic job,
  not something the validator claims to prove.
- Why separate from A: preserving an attributable statement and judging what it
  establishes are different jobs. B receives no proposed final recommendation
  to rationalize.

### C — Develop live explanations or directions

- Input: sealed A/B, exact question and product context. Raw sources remain
  available within the packet; no later result or prior answer.
- Job: construct the live causal explanations/value hypotheses that fit B,
  including inconvenient observations. State what player/buyer action or change
  could produce what benefit/cost. No fixed number of alternatives.
- Output: explanation IDs, dependencies on B, explicitly new creative hypotheses,
  incompatible observations and observable distinctions where these matter.
- Admission: unsupported premises remain hypotheses; rejection/no-fit is valid.
  Creating a hypothesis is allowed without pretending it has external evidence.
- Why separate: no mechanism can retrospectively upgrade its needed customer
  premise; an unusual working mechanism is not yet a worthwhile purchase.

### D — Identify the frontier and decision conditions

- Input: sealed A–C and the exact buyer/offer/question. State which experience
  sources have already been seen by earlier stages and by this stage.
- Job: identify the material unresolved distinction, whether available evidence
  already suffices, and what would change the bounded recommendation. For a
  whole-game value task, frame adequacy in the whole experience, price, buyer,
  occasion, alternatives and consequential sacrifices, not feature totals.
- Output: current frontier, decision conditions, minimal next observation if
  needed, and mode `retrospective` or `prospective_new_observation` with the exact
  evidence boundary. Do not request research solely to fill a slot.
- Admission: retrospective use of existing observations is never called
  preregistration. Prospective conditions are sealed before a genuinely new
  observation; they do not erase exposure to earlier related observations.
- Why separate: the decision conditions are visible before the final judgment,
  and before new evidence when possible. This reduces moving goalposts without
  pretending retrospective criteria were blind or permanently authoritative.

### Observation boundary — only when needed

Reuse trustworthy exact-build evidence that reaches the material claim. Do not
replay merely to create a new call. New player observation uses the existing
sanitized Studio Phase-A protocol; it receives normal player information, not
D's expected answers. Honest unavailable experience remains a valid blocker.
General source research is similarly bounded by D's question, not a demand study
required for every artistic idea. Preserve raw findings before interpretation.

### E — Resolve what the evidence establishes

- Input: sealed A–D and exact existing/new observations. No final value verdict.
- Job: distinguish shared observations from discriminators, resolve disputed
  factual causal claims and describe what actual experience was reached.
- Output: explanation disposition, exact evidence citations, retained/refuted
  claims and remaining decision-changing unknowns. Observer reactions remain
  evidence about that observer, not population preference.
- Admission: no invisible play, unobserved outcome or changed buyer/build.
  If new evidence invalidates B, request reopening B (A too if new raw anchors
  are required), rather than repairing the premise only inside E's prose.
- Why separate: discovering that order changes battle outcomes cannot itself
  decide that the experienced whole earns the price. For a non-runtime business
  question, this stage evaluates the available business evidence instead.

### F — Make the bounded whole-product decision

- Input: sealed prior outputs and raw relevant evidence, exact offer/buyer and
  D's declared mode/conditions. No old final answer or peer conclusion.
- Job: make the coherent benefit/cost/alternative tradeoff at this offer. Make a
  recommendation/rejection when justified, or name the precise uncertainty.
  Aesthetic value, closure, replay, comfort and removal can matter; no required
  customer-pain thesis, population study or content expansion is introduced.
- Output: concise report, judgment/confidence/conditions/next move, plus the
  material claims actually used with IDs and declared use: `established_fact`
  linked to B/E, `conditional_hypothesis` linked to C, or `value_judgment` with
  its evidence dependencies. These declarations do not determine their truth.
- Admission: unknown IDs, or a declared `established_fact` linked to an unresolved
  claim, fail mechanically. A reference cannot mechanically prove that prose or
  a paraphrase preserves its declared type, scope or meaning.
  Any newly needed factual premise requests upstream work, not self-approval.
- Why separate: this call can weigh established experience but cannot author
  its own facts to make that weighting pass. It may challenge the frame through
  an explicit reopen request when new material evidence warrants it.

## Semantic leakage, backtracking and final review

An F author can still hide a new premise in fluent prose or falsely label it as a
valuation. The required claim links make this inspectable, not impossible.
Existing fresh whole-assessment reviewers must compare every material factual
assertion in the actual report with B/E and raw evidence, including unlisted
assertions and scope expansion. A correctly spelled claim ID is insufficient.
The experimental independent examiner performs that check against a deliberately
persuasive, unsupported rationale as well. This is a fallible semantic check;
schema checks do not understand entailment. Final review supplements upstream
prevention and does not replace A–E.

The operator records the earliest affected stage and exact defect, reopens it
with the new raw evidence or neutral question, and marks dependent outputs stale.
No downstream rewrite of an upstream output, retroactive receipt or silent
reuse of an old verdict is allowed. Source changes affect their descendants;
price-only changes normally affect D/F and dependent review, not same-build raw
observations. C/E may also need rerun if their questions actually depend on price.
Reused output is identified by exact inputs, never just by stage name. Preserve
rejected attempts. A repeated blocker without useful new evidence stops honestly.

## Minimal records and implementation seam

Start with the manual host recipe above and the bounded experiment below before
writing a model runner. A lightweight CLI can subsequently validate records:

- `prepare-stage`: validate predecessor references and emit a stage packet plus
  next legal action. It does not launch a model or certify source completeness.
- `seal-stage`: bind the output, input packet and operator-observed context ID;
  compare-and-swap the predecessor and publish an immutable receipt.
- `inspect-session`: report current stages, stale dependencies and next action.
- `reopen-stage`: append the new generation/reason and invalidate descendants.

One session manifest carries protocol/version, exact task/scope, stage order,
input/output refs, reuse/exposure declarations, and execution records. Each
execution record carries the actual host context ID, packet/output hashes,
launch/completion order and `context_assurance: operator_enforced_shared_fs`.
The operator takes IDs from real tool results; model-written IDs do not establish
execution. These records are auditable assertions, not signed host attestations.
The tool can enforce shape/order/ref/CAS checks, not tool access or semantic truth.

After the trial, opt-in implementation can add `product_value_assessment.v2` and
result support with an exact session reference while preserving v1 readers.
For shared tasks, add a versioned optional protocol binding inside the Product
binding and require the exact session among reviewed scope/outputs; a task that
selects it cannot close using a legacy result. No silent project migration.
The selected process documents need an explicit narrow exception to v2/v3's
continuous-author/no-mandatory-handoff clauses. Keep one continuing coordinator;
do not split every creative paragraph or restore old independent Card authors.

Historical proofs retain their old meaning. New rules must not refresh old hashes.
Stable consumers, global skills, E&U and other project pointers remain unchanged.
Product judgments still do not change Idea commission, Studio lifecycle or USER
playtest/approval. A recommendation to change material scope follows its existing
authority path. The current reusable-Factory design review practice is two fresh
reviews, not a fabricated game-owned USER-ruling record; see
`DESIGN_REVIEW_HISTORY.md`. This proposal is pending that review. No additional
USER approval ritual is created by this document.

## Bounded first trial and cost

Run `product/tests/STAGED_CALL_EXPERIMENT_PROTOCOL.md`: one small raw buyback
question, one evidence mutation, fresh stages and an independent examiner.
This tests premise integrity/backtracking, not true market advantage or game value.
It does not establish that the staging improved judgment or that six calls are a
generally useful minimum. Before broad adoption, compare matched raw inputs under
the current simpler workflow and the staged workflow with blinded independent
evaluation and full cost accounting. Add a separately labeled recovery stress
case with persuasive but mistaken upstream support, plus an actual bounded
whole-game/price case where experience is sufficient and value weighting is hard.
Test whether A/E add useful work there; preserve only justified separate judgment
boundaries. A small comparison remains exploratory, not commercial validation.
Keep those later tests separate. Calls are sequential only where outputs
depend on predecessors; parallel source collection and exact reuse remain valid.
Measure full calls/tokens/time/rework. No call is justified solely by a heading,
file count, chain-of-thought length or a target token-saving percentage.
