# Staged-call synthetic evidence, 2026-10-09

**Current status: bounded trial and one targeted repair completed; residual
semantic defects remain. No chain-wide PASS, production adoption, general efficacy
or commercial-assessment validation is claimed.**

Start with [first-trial findings](TRIAL_REPORT.md) and
[bounded repair findings](repair_v1/REPORT.md). The final checker found the bounded
recommendation grounded while identifying two unresolved upstream errors. The
exercise is closed after that one repair pass; this bundle does not schedule more
fixtures or modify a stable consumer.

## Historical specifications and approval scope

The [design](../../../docs/STAGED_CALL_PROTOCOL_DESIGN.md) and
[experiment specification](../../STAGED_CALL_EXPERIMENT_PROTOCOL.md) retain their
exact reviewed bytes. Their proposed/not-executed/pending-review headings describe
when those snapshots were written. They are **historical specifications**, not the
current execution status. This dated index and the result reports establish what
subsequently ran. No wording or hash was retrospectively repaired into approval.

[Initial execution review](design_reviews/EXECUTION.md) required neutral tested
prompts and removal of examiner answer-key leakage. [R2](design_reviews/EXECUTION_R2.md)
passed that bounded specification, while [intent review](design_reviews/INTENT.md)
explicitly withheld broad adoption/efficacy. These reviews do not establish approval
of the separate nine-file causal-discrimination refinement node.

The original inline examiner delivery did not launch. Its exact expanded packet
and failed helper result remain under examiner/. A declared deduplicated delivery
revision was reviewed before a fresh examiner ran; see examiner_revision_1/.
No original semantic output was rerun to improve that report. The later general
scope repair is separately versioned under repair_v1/, including exact invalidation,
all first outputs, launch wrappers and the fresh checker's remaining findings.

## What is included

Synthetic source records, neutral templates, exact first stage prompts/outputs,
Candidate Q, actual call/input hashes and chronology, the failed delivery, the
lossless packaging revision, independent reports, the one targeted repair and
its remaining defects. Coordinator-only keys are explicitly labeled in the frozen
experiment/design artifacts; they were not allowed stage or examiner inputs.

No SAB gameplay/screenshots, private chat transcript, raw personal conversation,
credentials, machine cache or unrelated project content is included. Canonical
native task IDs and some absolute packet-loading paths are preserved only as
historical call provenance. They are not hard context-isolation evidence and are
not commands to run against a new machine. Requested model settings are not provider
attestation. Stored response hashes bind visible text with a terminal LF.

## Portable integrity and rendering check

From the repository root, run:

```sh
python product/tests/evidence/staged_call_20261009/verify_bundle.py
```

This uses only Python's standard library and reads this bundle. It verifies the
manifest's exact file bytes, reconstructs all 12 original stage packets and all
five repair packets, and checks their recorded hashes. It does not invoke models,
rerun the experiment, assert semantic correctness, or change files. The manifest
also binds the two historical spec snapshots at their repository-relative paths.

The original process had 12 semantic stages, one semantic examiner, a failed
mechanical launch helper and a delivery execution reviewer. The repair added five
semantic stages and one checker, totaling 21 native contexts across the synthetic
trial generations. Design reviews are extra. Context grew even after the repair's
anti-repetition instruction; do not present this as an efficient or validated
mandatory six-call architecture.
