# Staged-call trial: first-pass execution record

2026-10-09. Twelve semantic stage calls completed; the required examiner was not
launched. This report is an execution/intermediate-results record, not a semantic
PASS, completed original trial, comparative efficacy claim or general adoption.

## Preserved result differences

- X/B5–B6 and X/F treat the colleague's suggestion as a hypothesis without an
  established competitive-advantage case. X/F recommends defining an evaluation,
  not adopting or rejecting the untested substantive merits.
- Y/B3–B4 and Y/E recognize the three completed choices and the sellers' stated
  $40 reason as bounded evidence of local price relevance. Y/F retains that
  evidence while keeping transfer to our changed offer, profitability and
  durability unresolved. Its ultimate adoption recommendation remains conditional.
- These are descriptions of actual frozen outputs. There was no coached semantic
  revision, no replay of a failed stage and no externally executed pricing action.
  Independent semantic examination of the outputs is still missing.

## Execution and limitations

- Actual semantic calls: 12, each a new native context with no inherited turns;
  requested settings gpt-6-astra / xhigh. Context identities are the host-returned
  canonical task names in STATE.json. No opaque provider conversation ID or actual
  token telemetry was returned.
- Actual additional coordination calls: one mechanical launch helper. It did not
  launch an examiner. There are no examiner findings or invocation receipt.
- The coordinator observed no extra tool/exposure event from semantic workers;
  native child tool transcripts were not exposed. This is operator-enforced
  context discipline on a shared filesystem, not proof of zero unseen tools or
  hard isolation. Output hashes bind stored visible final text with terminal LF.
- All first outputs, exact rendered prompts, original source versions and actual
  launch records are retained. The input mutation marked old descendants stale
  for the new source version; it did not rewrite the old outputs.

## Negative finding: repeated context made the original examination impractical

Unique raw source text across the two arms is 748 UTF-8 bytes. The twelve stage
prompts total 110,221 bytes; their outputs total 37,745 bytes. X prompt size grew
from 1,589 bytes at A to 15,733 at F; Y grew from 2,077 to 19,859. These byte counts
are not tokens, API costs or a comparison with an alternative workflow.

The unchanged reviewed examiner packet is 158,582 bytes, SHA-256
54d16b72d9ec1855236602902100cd488372c59b6ffd07482aa68ba3d91a38aa. It repeats all stage
prompts in addition to sources and outputs. The mechanical helper verified the
whole file programmatically but its returned text was truncated; it could not
faithfully emit the full inline spawn payload within its response budget. It
stopped without an examiner invocation. No host size rejection occurred. Its
rough token estimate is not measured token usage.

The recorded stage wall interval was 1,097.898 seconds (about 18 minutes 18 seconds)
from the operator's first launch record to last seal. This includes manual
coordination and serialization delays; it is not pure model inference latency.
STAGE_METRICS.json preserves every stage's byte counts and recorded intervals.

## Proposed next revision, not applied to the first pass

1. Keep each raw source and each stage output once in a canonical artifact set,
   with IDs, scope, source spans, contradictions and exact hashes. Preserve the
   whole raw contrary source, not just a flattering extracted claim.
2. Render a stage from its actual dependency closure and relevant raw evidence;
   do not blindly append the entire predecessor transcript chain. A/B support
   links and C–E decision artifacts should reference stable prior IDs rather than
   repeat the same findings in prose. Maintain transparent optional source access.
3. For examiner execution audit, carry one copy of common/stage templates plus
   exact source/prerequisite mappings and records, rather than all expanded
   rendered prompts. Mechanically reconstruct each original prompt and compare
   bytes/hashes. Retain the original expanded prompts for provenance.
4. Independently review that changed examiner representation before use. A later
   reduced-payload examination can audit these frozen outputs but is a recorded
   protocol amendment, not successful execution of the unchanged original packet.
5. Do not infer that six calls improved accuracy. Matched simpler-workflow tests,
   misleading upstream-support recovery and actual whole-product value judgments
   remain separate future work. The present cost is evidence against treating the
   six-stage full-transcript recipe as a justified general minimum.

No Factory runtime implementation, publication, stable consumer or E&U pointer
change was performed. The reviewed design/protocol and nine-file freeze remain
unchanged. Examiner-dependent scoring remains pending.
