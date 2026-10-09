# Active separated judgment protocol

New whole-product assessments use product_value_assessment.v2. Early nonbinding
intent and ordinary authorized production are unchanged. Historical v1 artifacts
remain readable; they cannot mint a new receipt under this repaired process.

## Dispatch and seal actual calls

Create `design/product_value/<id>/judgment/CASE.json` using
`product_judgment_case.v1`: assessment_id, question, subject, offer, audience,
mode (retrospective or prospective_new_observation), exposure_note, sources and
conditions. Context shapes match the assessment. Sources are exact game/game_git
refs including every relevant contrary source and all mandatory authority. Each
condition is {id, text, source, quote}; text must equal the literal original
source quote. Interpretation and decomposition belong only in the frame.
Preserve the original question, compound conditions and scope. A case inventory
is not a reviewer-authored conclusion or a new authority. Withhold completed prior
worth-it reports; extract necessary original anchors with truthful provenance.
Frame and independent reviewers must challenge omissions against raw sources.

Run `python3 product/product.py judgment-packet --game-repo <GAME> --case <CASE>
--stage <STAGE>`. Launch a genuinely fresh non-inheriting model context with this
packet, this output contract and only its listed complete inputs. The operator
must retain the actual launch identity and exact packet/output outside authored
source. Files are shared; no tool-enforced sandbox or host-authenticated receipts
are claimed. Extra exposure invalidates the attempt. Do not supply expected
findings, old diagnoses, peer conclusions or an intended verdict.

Stages and dependencies:

- frame: case and complete raw sources
- evidence: those sources plus sealed frame
- independent_intent_experience and independent_completeness_project: case, raw
  sources and sealed frame only; parallel with evidence, no final report
- decision: case, raw sources, frame and evidence, only after both independent
  first passes are sealed; it gets their fingerprints, never their conclusions

Write each call's output to a draft path and call `judgment-seal --game-repo
<GAME> --case <CASE> --stage <STAGE> --input <DRAFT>`. The immutable stage is owned
under judgment/<stage>.json. A repeated identical seal is harmless; a different
output must use a new assessment ID. On reopening, preserve failed attempts,
repair the earliest owning stage in a fresh call and regenerate its descendants.
Reuse unaffected raw sources, not stale packet digests. No unresolved reopening
request can be admitted. New experience still follows sanitized Studio observation.
The CLI is a dispatcher contract/admission checker; the operator launches calls.

## Output contract

Each stage output contains exactly schema_version: product_judgment_stage.v1,
stage, context_id (actual context), packet_digest (from packet), extra_exposure
(array), reopen_requests (array), findings. The two arrays must be empty for
admission; do not erase real contamination or a reopening request to make it pass.
All findings contain conditions, one per unchanged case id and exact text.

Frame condition fields: id, text, meaning, benefit, buyer_cost, sufficiency,
falsifier, basis, scope (all meaningful text), obligations. Obligations are
{id, proposition, kind: EXPERIENTIAL or EVALUATIVE}. Decompose compound conditions
into their actual parts, retaining quantifiers, temporal scope and whole-purchase
sufficiency. Express experiential obligations as affirmative premises whose truth
would satisfy that part of the condition. A negatively worded original falsifier
remains quoted unchanged; its framed satisfaction premise preserves the exact
negation/quantifier (not-mostly is different from not-wholly). claim_ids name
necessary affirmative premises, not every incidental counterclaim in the packet. Do not collapse “mostly administrative OR too unrewarding as a whole”
into “some real choices.” Findings also contain whole_purchase_question (exactly the case question) and
external_conditions, an array
of {condition, source, basis}. Each is an independently specified external
offer/buyer scenario condition grounded in a raw source. Empty is valid. Never
condition the answer on the original sufficiency requirement being true or on
this buyer finding the price worthwhile. These conditions are fixed before the
verdict; the decision cannot add an essential taste premise of its own.

Evidence condition fields: id, text, claims, benefits, costs, shared_evidence,
discriminators, material_unknowns, obligations. The four narrative fields explain
actual support/cost, not labels. Each claim is {id, proposition, status: SUPPORTED /
CONTRADICTED / UNRESOLVED, scope, evidence: [raw refs], support_relation}. A status
belongs to exactly the written proposition; unknown truth and absent support are
different statements. material_unknowns is an array of concrete decision-changing
questions with opposing outcomes and the smallest observation/access blocker.
Findings also contain experience_scope. Each obligation copies frame id,
proposition and kind plus status, reason and claim_ids (the exact necessary factual-premise IDs in
that condition). EXPERIENTIAL obligations require nonempty dependencies; SUPPORTED
cannot consume an unresolved or contradicted premise. EVALUATIVE dependencies may
be empty because evidence cannot decide their value. EXPERIENTIAL statuses are SUPPORTED,
CONTRADICTED or UNRESOLVED; EVALUATIVE obligations have EVALUATIVE status because
evidence does not itself settle worth. No unsupported world fact is promoted by
removing an objection.

Decision and independent-first-pass conditions contain id, text, disposition:
MET / NOT_MET / UNRESOLVED / CONDITIONAL, positive_case, strongest_objection,
sufficiency_reason, assumptions, material_unknowns, evidence and obligations.
Narratives must connect the experienced whole benefit, full cost and same buyer's
reason to choose. Arrays preserve essential truth conditions and unresolved
questions. Obligations copy frame id/proposition/kind, plus status (same four
value dispositions) and reason. MET requires every original obligation MET.
CONDITIONAL cannot contain an unresolved or failed obligation, and an EVALUATIVE
obligation cannot be CONDITIONAL. An independently specified external condition
(such as a scenario price) differs from a circular preference such as “if this
buyer finds these few runs worth the price.” The latter does not answer the same
question and cannot support stopping the original work. Ungrounded taste or an
unexplained inference stays UNRESOLVED. Global offer/scenario conditionality may
qualify an otherwise grounded judgment without making its causal inference circular.
“Some people could prefer this” does not establish this buyer's whole-product case.

Independent findings also contain frame_fidelity: {omitted_or_weakened_obligations:
[], reason}. Independently reconstruct the question and scrutinize external_conditions from raw
authority, including circular taste/value conditions; list actual
omissions and request reopening, rather than merely endorsing the chosen frame.

Decision findings also contain judgment, whole_purchase_reason, material_unknowns,
conditionality and next_move. All condition assumptions and material unknowns
propagate to the verdict. conditionality exactly matches the frame
external_conditions in order; condition assumptions must be drawn from that
list. Changing this scope reopens the frame and independent first passes. The decision cannot remove evidence-stage material
unknowns: a changed relevance judgment reopens the evidence owner. SUPPORTED
requires MET/CONDITIONAL original conditions and no material unknowns. VALUE_GAP
is a valid finished assessment. EVIDENCE_INSUFFICIENT names a missing observation;
JUDGMENT_UNRESOLVED identifies a still-unsound inference/criterion and repairs the
argument without automatically requesting play. CONTEXT_UNRESOLVED retains its
existing use. There is no programmatic taste threshold, replay/hours/feature floor,
forced binary verdict or demand for human willingness-to-pay proof.

## Final report and independent comparison

The decision context authors the report and assessment v2, binding deliberation:
{case, frame, evidence, decision} exact refs. Subject/offer/audience and verdict,
material_unknowns and conditionality exactly match sealed work. `prepare` binds
this package. The report may explain these findings; it cannot add a new premise,
weaken an obligation or remove a material issue. Reopen instead.

Return each original independent reviewer its own first pass and the complete
prepared assessment closure. Do not expose its peer's first pass or review. These
are informed reviewers, not blind players. Write product_value_review.v2 with the
existing review fields, plus independent_first_pass (own exact ref) and
condition_comparison. Each comparison has id, exact text,
original_meaning_preserved (boolean), independent_disposition,
decision_disposition, resolution (SAME_FINDING / JUSTIFIED_CHANGE / UNRESOLVED),
reason. A changed view needs a concrete same-question experiential/causal reason;
“defensible weighting,” formal validity, or agreement alone cannot close it.
Check individual obligations and report prose, not only top-level dispositions.
Both final reviewers retain all existing whole-assessment responsibilities.

A false original_meaning_preserved, unresolved disagreement, missing first pass,
stale packet, non-distinct context or silently dropped unknown blocks admission.
Admit only after actual semantic review. An honest REVISE is useful work; retain
it and repair the earliest affected output. `record/check/gate` still separate
assessment completion, scoped value-claim eligibility and USER/gameplay acceptance.
`semantic_success_proven: false` is deliberate: receipts attest formal consistency,
not the truth of a taste judgment or proven superiority of this workflow.
