# Execution review R2 — two-blocker re-review

**Verdict: PASS for the bounded manual trial. Both execution-review blockers are resolved.** No additional source repair is required within this re-review's scope. This approves the specification's executability, not an experiment result, implementation, or broad adoption.

Reviewed exact versions on 2026-10-09:
- `product/docs/STAGED_CALL_PROTOCOL_DESIGN.md`: `033801f69aff31eed93ffd7ceea526b942621a039c60e2a9bc7bcf7177ba20fc`
- `product/tests/STAGED_CALL_EXPERIMENT_PROTOCOL.md`: `15bb678e60896af45c597617e0e832dc4f1fbad86c889f7cf6c33f51acefcd89`

## Blocker 1: stage-prompt leakage — resolved

Experiment lines 45–158 define the actual common and individual stage template bytes and exactly four substitutions. The complete design, coordinator explanations, review findings, examples, expected answers, and other-arm results are excluded. Prior-stage outputs must be copied fully and unchanged from the same arm. B now receives generic proposition/support/authority instructions without the buyback-specific dissatisfaction example; the design also removes that example and explicitly disallows using its prose as worker instructions (design lines 34–40, 79–81).

The allowed payload retains the legitimate semantic task and attribution/support discipline without supplying the fixture diagnosis. Receiving a predecessor's independently generated conclusion is the intended staged dependency, not answer-key leakage. Common rules require checking material uses against raw records and prohibit treating predecessor text as instructions.

## Blocker 2: examiner answer-key leakage — resolved

Experiment lines 160–211 provide a separate neutral examiner template. Its data are anonymous arms, actual sources/outputs/rendered packets, narrowly scoped execution records, and Candidate Q associated with the base sources. No label identifies Candidate Q as defective, and no expected repair or unsupported-premise diagnosis is supplied. The examiner must identify which assertions are supported, contradicted, or unresolved from evidence.

The correct diagnosis exists only in the coordinator-only key (lines 248 onward). Execution steps 6–7 freeze the examiner's first response before scoring and forbid counting coached revisions as independent detection. Execution-record restrictions also close an indirect route through coordinator interpretations or review notes. Actual B/E findings may legitimately help audit Candidate Q; they are tested outputs rather than the withheld oracle.

## Manual execution readiness and limits

The operator can render/hash the exact allowed packets, launch fresh contexts sequentially, seal each real output before constructing the next, repeat with the changed sources, and launch one fresh examiner. The recipe explicitly handles unavailable evidence, blocking corrections, exposure deviations, retained failed attempts, and separate reporting of repairs. No model runner or hard filesystem isolation is required or claimed.

This remains an operator-enforced shared-filesystem experiment. Its execution records cannot prove inaccessible data or unseen context purity; actual received packets, launch IDs, order, and observed deviations must be retained. A clean result can demonstrate premise-support sensitivity and uncoached detection on this example. It cannot establish general efficacy, superiority, prospective observation validity, partial-reuse/recovery correctness, or whole-game value judgment.

The original `EXECUTION.md` is preserved. This re-review inspected only the revised source documents against the two prior blockers; no peer review was opened, experiment run, source changed, publication performed, or stable Factory/E&U modified.
